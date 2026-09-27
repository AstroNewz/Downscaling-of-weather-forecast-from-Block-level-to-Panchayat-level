"""
Operational Safeguards Engine — Dynamic Residual Model v2
SIH Problem Statement 26074 (Weather Downscaling)

Implements multi-stage runtime verification for Controlled Production:
1. Feature Completeness Validation (AVAILABLE, MISSING, INVALID, STALE)
2. Out-of-Distribution (OOD) Domain Check against Kharif 2024 training envelope
3. Residual Safety Guardrail (-8.0°C <= ΔT <= +8.0°C; NO silent clipping)
4. Runtime Telemetry Tracking (Zero credential/PII leakage)
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger


class FeatureCompletenessResult:
    def __init__(
        self,
        is_eligible: bool,
        feature_states: Dict[str, str],
        unmet_reasons: List[str],
    ):
        self.is_eligible = is_eligible
        self.feature_states = feature_states
        self.unmet_reasons = unmet_reasons

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_eligible": self.is_eligible,
            "feature_states": self.feature_states,
            "unmet_reasons": self.unmet_reasons,
        }


class OODCheckResult:
    def __init__(
        self,
        is_within_range: bool,
        ood_status: str,
        out_of_range_features: List[Dict[str, Any]],
    ):
        self.is_within_range = is_within_range
        self.ood_status = ood_status  # "WITHIN_TRAINING_RANGE" or "OUT_OF_DISTRIBUTION"
        self.out_of_range_features = out_of_range_features

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_within_range": self.is_within_range,
            "ood_status": self.ood_status,
            "out_of_range_features": self.out_of_range_features,
        }


class ResidualSafetyResult:
    def __init__(
        self,
        safety_status: str,  # "PASS" or "FAILED"
        raw_residual_c: float,
        bounds: Tuple[float, float],
        failure_reason: Optional[str] = None,
    ):
        self.safety_status = safety_status
        self.raw_residual_c = raw_residual_c
        self.bounds = bounds
        self.failure_reason = failure_reason

    @property
    def is_safe(self) -> bool:
        return self.safety_status == "PASS"

    @property
    def reason(self) -> Optional[str]:
        return self.failure_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "safety_status": self.safety_status,
            "raw_residual_c": self.raw_residual_c,
            "bounds": list(self.bounds),
            "failure_reason": self.failure_reason,
        }


class OperationalSafeguardsEngine:
    """
    Validates live inference suitability for Dynamic Residual Model v2.
    Ensures safe, deterministic fallback to the certified baseline if any check fails.
    """

    @classmethod
    def validate_feature_completeness(
        cls,
        temperature_c: Optional[float],
        relative_humidity_pct: Optional[float],
        wind_speed_mps: Optional[float],
        wind_direction_deg: Optional[float],
        precipitation_mm: Optional[float],
        elevation_m: Optional[float] = None,
        slope_deg: Optional[float] = None,
        aspect_deg: Optional[float] = None,
    ) -> FeatureCompletenessResult:
        """
        Validates whether required dynamic and static features are AVAILABLE and valid.
        """
        states: Dict[str, str] = {}
        unmet: List[str] = []

        # Temperature
        if temperature_c is None:
            states["temperature_2m"] = "MISSING"
            unmet.append("temperature_2m is missing")
        elif not (-15.0 <= temperature_c <= 60.0):
            states["temperature_2m"] = "INVALID"
            unmet.append(f"temperature_2m ({temperature_c}°C) is outside physical range")
        else:
            states["temperature_2m"] = "AVAILABLE"

        # Relative humidity
        if relative_humidity_pct is None:
            states["relative_humidity_2m"] = "MISSING"
            unmet.append("relative_humidity_2m is missing")
        elif not (0.0 <= relative_humidity_pct <= 100.0):
            states["relative_humidity_2m"] = "INVALID"
            unmet.append(f"relative_humidity_2m ({relative_humidity_pct}%) is outside range 0-100%")
        else:
            states["relative_humidity_2m"] = "AVAILABLE"

        # Wind speed
        if wind_speed_mps is None:
            states["wind_speed_10m"] = "MISSING"
            unmet.append("wind_speed_10m is missing")
        elif not (0.0 <= wind_speed_mps <= 60.0):
            states["wind_speed_10m"] = "INVALID"
            unmet.append(f"wind_speed_10m ({wind_speed_mps} m/s) is outside physical range")
        else:
            states["wind_speed_10m"] = "AVAILABLE"

        # Wind direction
        if wind_direction_deg is None:
            states["wind_direction_10m"] = "MISSING"
            unmet.append("wind_direction_10m is missing")
        elif not (0.0 <= wind_direction_deg <= 360.0):
            states["wind_direction_10m"] = "INVALID"
            unmet.append(f"wind_direction_10m ({wind_direction_deg}°) is outside range 0-360°")
        else:
            states["wind_direction_10m"] = "AVAILABLE"

        # Precipitation
        if precipitation_mm is None:
            states["precipitation"] = "MISSING"
            unmet.append("precipitation is missing")
        elif precipitation_mm < 0.0:
            states["precipitation"] = "INVALID"
            unmet.append(f"precipitation ({precipitation_mm} mm) is negative")
        else:
            states["precipitation"] = "AVAILABLE"

        # Static / GIS features
        states["elevation"] = "AVAILABLE" if elevation_m is not None else "AVAILABLE_DEFAULT"
        states["slope"] = "AVAILABLE" if slope_deg is not None else "AVAILABLE_DEFAULT"
        states["aspect"] = "AVAILABLE" if aspect_deg is not None else "AVAILABLE_DEFAULT"

        is_eligible = len(unmet) == 0
        return FeatureCompletenessResult(
            is_eligible=is_eligible,
            feature_states=states,
            unmet_reasons=unmet,
        )

    @classmethod
    def check_out_of_distribution(
        cls,
        temperature_c: float,
        relative_humidity_pct: float,
        wind_speed_mps: float,
        elevation_m: float,
        slope_deg: float,
    ) -> OODCheckResult:
        """
        Verifies whether live features are within the validated Kharif 2024 training domain.
        Prevents uncontrolled extrapolation.
        """
        oor = []

        if not (settings.TRAINING_TEMP_MIN_C <= temperature_c <= settings.TRAINING_TEMP_MAX_C):
            oor.append({
                "feature": "temperature_c",
                "observed": round(temperature_c, 2),
                "training_domain": [settings.TRAINING_TEMP_MIN_C, settings.TRAINING_TEMP_MAX_C],
                "unit": "°C",
            })

        if not (settings.TRAINING_RH_MIN_PCT <= relative_humidity_pct <= settings.TRAINING_RH_MAX_PCT):
            oor.append({
                "feature": "relative_humidity_pct",
                "observed": round(relative_humidity_pct, 1),
                "training_domain": [settings.TRAINING_RH_MIN_PCT, settings.TRAINING_RH_MAX_PCT],
                "unit": "%",
            })

        if wind_speed_mps > settings.TRAINING_WIND_MAX_MPS:
            oor.append({
                "feature": "wind_speed_mps",
                "observed": round(wind_speed_mps, 2),
                "training_domain": [0.0, settings.TRAINING_WIND_MAX_MPS],
                "unit": "m/s",
            })

        if elevation_m > settings.TRAINING_ELEV_MAX_M:
            oor.append({
                "feature": "elevation_m",
                "observed": round(elevation_m, 1),
                "training_domain": [0.0, settings.TRAINING_ELEV_MAX_M],
                "unit": "m",
            })

        if slope_deg > settings.TRAINING_SLOPE_MAX_DEG:
            oor.append({
                "feature": "slope_deg",
                "observed": round(slope_deg, 1),
                "training_domain": [0.0, settings.TRAINING_SLOPE_MAX_DEG],
                "unit": "deg",
            })

        is_within = len(oor) == 0
        ood_status = "WITHIN_TRAINING_RANGE" if is_within else "OUT_OF_DISTRIBUTION"
        return OODCheckResult(
            is_within_range=is_within,
            ood_status=ood_status,
            out_of_range_features=oor,
        )

    @classmethod
    def check_residual_safety(cls, raw_residual_c: float) -> ResidualSafetyResult:
        """
        Validates model residual against physical safety bounds [-8.0°C, +8.0°C].
        DOES NOT silently clip: violation explicitly triggers baseline fallback.
        """
        lo = settings.DYNAMIC_RESIDUAL_SAFETY_MIN
        hi = settings.DYNAMIC_RESIDUAL_SAFETY_MAX

        if lo <= raw_residual_c <= hi:
            return ResidualSafetyResult(
                safety_status="PASS",
                raw_residual_c=round(raw_residual_c, 4),
                bounds=(lo, hi),
            )
        else:
            reason = (
                f"Model residual {raw_residual_c:+.4f}°C violates physical safety bounds "
                f"[{lo:+.1f}°C, {hi:+.1f}°C]. Triggering automatic certified baseline fallback."
            )
            logger.warning("Dynamic residual safety violation: %s", reason)
            return ResidualSafetyResult(
                safety_status="FAILED",
                raw_residual_c=round(raw_residual_c, 4),
                bounds=(lo, hi),
                failure_reason=reason,
            )

    @classmethod
    def validate_residual_safety(cls, raw_residual_c: float) -> ResidualSafetyResult:
        """Alias for check_residual_safety."""
        return cls.check_residual_safety(raw_residual_c)


class RuntimeTelemetryTracker:
    """
    Thread-safe operational telemetry tracker for Controlled Production.
    Tracks execution counts, fallback triggers, and safety checks without logging credentials.
    """

    _instance: Optional["RuntimeTelemetryTracker"] = None
    _METRIC_ALIASES = {
        "dynamic_fallback": "baseline_fallback",
        "feature_missing": "missing_feature",
        "qc_failure": "invalid_data",
        "freshness_failure": "stale_data",
        "live_provider_failure": "provider_failure",
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics = {
            "dynamic_success": 0,
            "baseline_fallback": 0,
            "missing_feature": 0,
            "ood_failure": 0,
            "safety_failure": 0,
            "stale_data": 0,
            "provider_failure": 0,
            "invalid_data": 0,
            "baseline_success": 0,
        }

    @classmethod
    def get_instance(cls) -> "RuntimeTelemetryTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def increment(self, metric: str) -> None:
        canonical = self._METRIC_ALIASES.get(metric, metric)
        with self._lock:
            if canonical in self._metrics:
                self._metrics[canonical] += 1

    def get_snapshot(self) -> Dict[str, int]:
        with self._lock:
            snap = dict(self._metrics)
            # Expose legacy alias keys for backwards compatibility
            snap["dynamic_fallback"] = snap["baseline_fallback"]
            snap["feature_missing"] = snap["missing_feature"]
            snap["qc_failure"] = snap["invalid_data"]
            snap["freshness_failure"] = snap["stale_data"]
            snap["live_provider_failure"] = snap["provider_failure"]
            return snap

    def reset(self) -> None:
        with self._lock:
            for k in self._metrics:
                self._metrics[k] = 0


runtime_telemetry = RuntimeTelemetryTracker.get_instance()
