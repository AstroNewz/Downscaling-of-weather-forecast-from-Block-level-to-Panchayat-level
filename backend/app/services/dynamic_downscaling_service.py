"""
Dynamic Residual Downscaling Service v2 — Research Candidate
SIH Problem Statement 26074 — Agro-Meteorological Downscaling

Strict Governance:
- Candidate model is strictly RESEARCH_ONLY.
- Production baseline T_calibrated = T_coarse + 0.7351°C remains authoritative.
- Clamped between -8.0°C and +8.0°C.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import xgboost as xgb

from app.core.logging import logger

CERTIFIED_BASELINE_OFFSET_C = 0.7351
GUARDRAIL_MIN_RESIDUAL_C = -8.0
GUARDRAIL_MAX_RESIDUAL_C = 8.0

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CANDIDATE_DIR = BASE_DIR / "models" / "candidates" / "temperature_residual" / "dynamic_temperature_residual_v2"


class DynamicDownscalingService:
    """
    Research-only inference service for the Dynamic Residual Downscaling Model v2.
    """

    _instance: Optional["DynamicDownscalingService"] = None

    def __init__(self):
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_schema: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self._load_candidate()

    @classmethod
    def get_instance(cls) -> "DynamicDownscalingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_candidate(self) -> None:
        model_path = CANDIDATE_DIR / "xgboost_model.json"
        schema_path = CANDIDATE_DIR / "feature_schema.json"
        meta_path = CANDIDATE_DIR / "metadata.json"

        if not model_path.exists():
            logger.warning("Dynamic Residual v2 model file not found at %s", model_path)
            return

        try:
            if schema_path.exists():
                with open(schema_path) as f:
                    self.feature_schema = json.load(f)

            if meta_path.exists():
                with open(meta_path) as f:
                    self.metadata = json.load(f)

            self.model = xgb.XGBRegressor()
            self.model.load_model(str(model_path))
            self.is_loaded = True
            logger.info("Dynamic Residual Model v2 loaded successfully from %s", model_path)
        except Exception as exc:
            logger.error("Failed to load Dynamic Residual Model v2: %s", exc)
            self.is_loaded = False

    def predict_residual(
        self,
        coarse_temp: float,
        coarse_rh: float = 65.0,
        coarse_wspd: float = 2.5,
        wind_direction_deg: float = 180.0,
        precipitation_mm: float = 0.0,
        hour_of_day: int = 12,
        day_of_year: int = 200,
        elevation_m: float = 100.0,
        coarse_elevation_m: Optional[float] = None,
        slope_deg: float = 1.0,
        aspect_deg: float = 180.0,
        land_cover_code: int = 40,
        latitude: float = 25.0,
        longitude: float = 82.0,
    ) -> Dict[str, Any]:
        """
        Executes dynamic downscaling inference with safety bounding.
        """
        coarse_elev = coarse_elevation_m if coarse_elevation_m is not None else elevation_m
        elev_diff = elevation_m - coarse_elev
        lapse_rate_adj = elev_diff * -0.0065

        sin_w_dir = math.sin(math.radians(wind_direction_deg))
        cos_w_dir = math.cos(math.radians(wind_direction_deg))
        sin_hr = math.sin(2.0 * math.pi * hour_of_day / 24.0)
        cos_hr = math.cos(2.0 * math.pi * hour_of_day / 24.0)
        sin_doy = math.sin(2.0 * math.pi * day_of_year / 365.25)
        cos_doy = math.cos(2.0 * math.pi * day_of_year / 365.25)
        sin_asp = math.sin(math.radians(aspect_deg))
        cos_asp = math.cos(math.radians(aspect_deg))

        feature_map = {
            "f_coarse_temp": float(coarse_temp),
            "f_coarse_rh": float(coarse_rh),
            "f_coarse_wspd": float(coarse_wspd),
            "f_sin_wind_dir": float(sin_w_dir),
            "f_cos_wind_dir": float(cos_w_dir),
            "f_coarse_precip": float(precipitation_mm),
            "f_sin_hour": float(sin_hr),
            "f_cos_hour": float(cos_hr),
            "f_sin_doy": float(sin_doy),
            "f_cos_doy": float(cos_doy),
            "f_obs_elevation": float(elevation_m),
            "f_era5_elevation": float(coarse_elev),
            "f_elevation_diff": float(elev_diff),
            "f_lapse_rate_adj": float(lapse_rate_adj),
            "f_slope": float(slope_deg),
            "f_sin_aspect": float(sin_asp),
            "f_cos_aspect": float(cos_asp),
            "f_land_cover": float(land_cover_code),
            "f_latitude": float(latitude),
            "f_longitude": float(longitude),
        }

        # Expected features in the exact schema order
        expected_features = [f["name"] for f in self.feature_schema.get("features", [])]
        if not expected_features:
            expected_features = list(feature_map.keys())

        if self.is_loaded and self.model is not None:
            vec = np.array([[feature_map.get(f, 0.0) for f in expected_features]], dtype=np.float32)
            raw_residual = float(self.model.predict(vec)[0])
        else:
            # Fallback estimation if model failed to load
            raw_residual = CERTIFIED_BASELINE_OFFSET_C + lapse_rate_adj

        # Physical safety guardrails
        is_clamped = raw_residual < GUARDRAIL_MIN_RESIDUAL_C or raw_residual > GUARDRAIL_MAX_RESIDUAL_C
        final_residual = max(GUARDRAIL_MIN_RESIDUAL_C, min(GUARDRAIL_MAX_RESIDUAL_C, raw_residual))
        guardrail_status = "CLAMPED" if is_clamped else "PASS"

        downscaled_temp = round(coarse_temp + final_residual, 2)
        baseline_temp = round(coarse_temp + CERTIFIED_BASELINE_OFFSET_C, 2)

        return {
            "status": "RESEARCH_ONLY",
            "candidate_id": "dynamic_temperature_residual_v2",
            "coarse_temperature_c": round(coarse_temp, 2),
            "raw_model_residual_c": round(raw_residual, 4),
            "final_residual_c": round(final_residual, 4),
            "downscaled_temperature_c": downscaled_temp,
            "guardrail_status": guardrail_status,
            "is_clamped": is_clamped,
            "guardrail_bounds": [-8.0, 8.0],
            "baseline_comparison": {
                "certified_baseline_offset_c": CERTIFIED_BASELINE_OFFSET_C,
                "certified_baseline_temp_c": baseline_temp,
                "delta_between_models_c": round(downscaled_temp - baseline_temp, 4),
            },
            "features_used": feature_map,
        }

    def get_diagnostic(self) -> Dict[str, Any]:
        """
        Returns scientific metadata, promotion gate audit results, and performance.
        """
        return {
            "is_loaded": self.is_loaded,
            "status": "RESEARCH_ONLY",
            "governance": {
                "policy": "Strictly research candidate. Production baseline (+0.7351°C) immutable.",
                "candidate_registry_path": str(CANDIDATE_DIR),
                "certified_production_baseline_offset_c": CERTIFIED_BASELINE_OFFSET_C,
            },
            "feature_schema": self.feature_schema,
            "metadata": self.metadata,
        }


dynamic_downscaling_service = DynamicDownscalingService.get_instance()
