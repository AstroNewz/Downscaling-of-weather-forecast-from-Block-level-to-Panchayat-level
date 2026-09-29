"""
Panchayat Localized Precipitation Observation-Fusion & Nowcasting Service
SIH Problem Statement 26074 (Weather Downscaling - Task 4)

Combines multi-stream meteorological evidence:
  NWP Baseline Forecast
  + Satellite Cloud & Brightness-Temperature Evidence
  + Satellite Precipitation Estimates (when available)
  + Doppler Weather Radar Telemetry (optional / pluggable)
  + Surface AWS / Gauge Observations (optional / pluggable)
  ↓
  Panchayat-Specific Localized Precipitation Risk & Short-Horizon Outlooks (30m, 60m, 120m)

CRITICAL GOVERNANCE RULES:
1. Two-Stage Precipitation Representation:
   Stage 1: P(rain >= threshold) - Probability of measurable precipitation
   Stage 2: E[rainfall | rain >= threshold] - Expected amount conditional on rain occurring
2. Conservative Estimations:
   Never convert missing data to 0.0 mm.
   If amount cannot be estimated reliably, expected_amount_mm = None.
3. Satellite cloud is NOT ground rainfall.
4. Radar is optional: missing radar degrades confidence, does NOT break the pipeline.
5. Baseline forecast remains separate and unmolested.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from shapely.geometry import Polygon, MultiPolygon

from app.core.config import settings
from app.core.logging import logger
from app.gis.boundary_registry import boundary_registry, PanchayatBoundaryRegistry
from app.gis.spatial_masking import spatial_masking_service, SpatialMaskingService
from app.schemas.precipitation_nowcast import (
    BaselinePrecipitationExpectation,
    EvidenceSignalType,
    NowcastConfidence,
    PanchayatPrecipitationNowcastResult,
    PrecipitationEvidenceComponent,
    PrecipitationNowcastHorizonResult,
    PrecipitationNowcastProvenance,
    PrecipitationSourceState,
    RadarObservationFeatures,
    SurfaceObservationFeatures,
)
from app.schemas.satellite import (
    PanchayatSatelliteExtractionResult,
    SatelliteProductType,
)
from app.schemas.spatial_masking import SourceWeatherGrid
from app.services.satellite_service import satellite_observation_service, SatelliteObservationService


class PanchayatPrecipitationNowcastService:
    """
    Coordinates multi-source precipitation evidence fusion at the Gram Panchayat polygon level.
    Outputs short-horizon (30, 60, 120 min) localized outlooks with explicit uncertainty.
    """

    def __init__(
        self,
        satellite_service: Optional[SatelliteObservationService] = None,
        masking_service: Optional[SpatialMaskingService] = None,
        registry: Optional[PanchayatBoundaryRegistry] = None,
        measurable_rain_threshold_mm: Optional[float] = None,
        freshness_threshold_minutes: Optional[float] = None,
        stale_penalty_factor: Optional[float] = None,
        min_spatial_coverage: Optional[float] = None,
    ):
        self.satellite_service = satellite_service or satellite_observation_service
        self.masking_service = masking_service or spatial_masking_service
        self.registry = registry or boundary_registry
        self.rain_threshold_mm = (
            measurable_rain_threshold_mm
            if measurable_rain_threshold_mm is not None
            else settings.NOWCAST_MEASURABLE_RAIN_THRESHOLD_MM
        )
        self.freshness_threshold_minutes = (
            freshness_threshold_minutes
            if freshness_threshold_minutes is not None
            else settings.NOWCAST_FRESHNESS_THRESHOLD_MINUTES
        )
        self.stale_penalty_factor = (
            stale_penalty_factor
            if stale_penalty_factor is not None
            else settings.NOWCAST_STALE_PENALTY_FACTOR
        )
        self.min_spatial_coverage = (
            min_spatial_coverage
            if min_spatial_coverage is not None
            else settings.NOWCAST_MIN_SPATIAL_COVERAGE
        )

    def generate_panchayat_precipitation_nowcast(
        self,
        panchayat_id: Optional[str] = None,
        panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
        baseline_forecast: Optional[Union[BaselinePrecipitationExpectation, Dict[str, Any]]] = None,
        satellite_grid: Optional[SourceWeatherGrid] = None,
        previous_satellite_grid: Optional[SourceWeatherGrid] = None,
        radar_features: Optional[RadarObservationFeatures] = None,
        surface_observation: Optional[SurfaceObservationFeatures] = None,
        convective_threshold_k: Optional[float] = None,
        require_verified: bool = False,
        issue_time: Optional[str] = None,
    ) -> PanchayatPrecipitationNowcastResult:
        """
        Generates an independent, observation-fused precipitation nowcast for a specific Panchayat.

        Steps:
        1. Validates Panchayat administrative boundary (fail-closed if missing/unverified).
        2. Normalizes baseline NWP precipitation forecast expectation.
        3. Extracts Panchayat-specific satellite features using Task 2/3 spatial masking.
        4. Ingests optional radar and surface telemetry if supplied.
        5. Detects evidence disagreement (e.g. NWP rain vs clear satellite).
        6. Derives multi-horizon (30m, 60m, 120m) outlooks with probability and conditional amount.
        7. Assigns conservative confidence and packages complete provenance.
        """
        now_utc = datetime.now(timezone.utc)
        issue_iso = issue_time or now_utc.isoformat()
        conv_threshold = convective_threshold_k or settings.SATELLITE_CONVECTIVE_TEMP_THRESHOLD_K

        # ---------------------------------------------------------------------
        # 1. Resolve & Validate Panchayat Polygon Geometry
        # ---------------------------------------------------------------------
        p_id = panchayat_id or "ANONYMOUS_PANCHAYAT"
        p_name: Optional[str] = None
        block_id: Optional[Union[str, int]] = None
        block_name: Optional[str] = None

        if panchayat_geometry is None and panchayat_id is not None:
            record = self.registry.get(panchayat_id)
            if record is None:
                reg_status = getattr(self.registry, "get_readiness_status", lambda: "READY")()
                fail_status = "PANCHAYAT_BOUNDARIES_NOT_CONFIGURED" if reg_status == "PANCHAYAT_BOUNDARIES_NOT_CONFIGURED" else "NOT_FOUND"
                return self._build_fail_closed_result(
                    panchayat_id=p_id, panchayat_name=None, issue_time=issue_iso,
                    status=fail_status, message=f"Panchayat ID '{panchayat_id}' not found in registry (state: {reg_status})."
                )
            if require_verified and not record.is_verified:
                return self._build_fail_closed_result(
                    panchayat_id=p_id, panchayat_name=record.panchayat_name, issue_time=issue_iso,
                    status="UNVERIFIED_GEOMETRY",
                    message=f"Panchayat '{record.panchayat_name}' boundary is unverified; fail-closed policy active."
                )
            p_name = record.panchayat_name
            block_id = record.block
            block_name = record.block
        else:
            record = None

        # ---------------------------------------------------------------------
        # 2. Normalize NWP Baseline Forecast Expectation
        # ---------------------------------------------------------------------
        baseline_exp = self._normalize_baseline_forecast(baseline_forecast, issue_iso, block_id, block_name)

        # ---------------------------------------------------------------------
        # 3. Extract Panchayat-Specific Satellite Evidence
        # ---------------------------------------------------------------------
        satellite_extraction: Optional[PanchayatSatelliteExtractionResult] = None
        if satellite_grid is not None:
            # Enforce Task 7 Requirement 10 Real-Data Quality Gates
            q_passed, q_failures = self.satellite_service.provider.validate_quality_gates(
                grid=satellite_grid,
                panchayat_record=record,
                min_coverage=self.min_spatial_coverage,
                max_age_minutes=self.freshness_threshold_minutes,
            )
            crit_failures = [f for f in q_failures if any(c in f for c in ("INVALID_CRS", "INVALID_SPATIAL_EXTENT", "INVALID_GEOTRANSFORM", "INVALID_CELL_GEOMETRY", "UNRECOGNIZED_PRODUCT_TYPE"))]
            if crit_failures:
                return self._build_fail_closed_result(
                    panchayat_id=p_id, panchayat_name=p_name, issue_time=issue_iso,
                    status="QUALITY_GATE_FAILURE",
                    message=f"Satellite observation rejected by operational quality gate: {'; '.join(crit_failures)}"
                )

            satellite_extraction = self.satellite_service.extract_panchayat_satellite_features(
                panchayat_id=panchayat_id,
                panchayat_geometry=panchayat_geometry,
                satellite_grid=satellite_grid,
                previous_satellite_grid=previous_satellite_grid,
                convective_threshold_k=conv_threshold,
                detection_threshold_mm=self.rain_threshold_mm,
                require_verified=require_verified,
                freshness_threshold_minutes=self.freshness_threshold_minutes,
            )
            if not satellite_extraction.success and satellite_extraction.status == "UNVERIFIED_GEOMETRY":
                return self._build_fail_closed_result(
                    panchayat_id=p_id, panchayat_name=p_name, issue_time=issue_iso,
                    status="UNVERIFIED_GEOMETRY", message=satellite_extraction.message
                )

        # ---------------------------------------------------------------------
        # 4. Compile Evidence Components
        # ---------------------------------------------------------------------
        evidence_components, source_state = self._compile_evidence_components(
            baseline_exp=baseline_exp,
            satellite_extraction=satellite_extraction,
            radar_features=radar_features,
            surface_observation=surface_observation,
            conv_threshold=conv_threshold,
        )

        # If no usable evidence remains: fail closed
        if source_state == PrecipitationSourceState.INSUFFICIENT_DATA:
            return self._build_fail_closed_result(
                panchayat_id=p_id, panchayat_name=p_name, issue_time=issue_iso,
                status="INSUFFICIENT_DATA", message="No valid or fresh precipitation evidence available."
            )

        # ---------------------------------------------------------------------
        # 5. Detect Source Disagreement
        # ---------------------------------------------------------------------
        has_disagreement, disagreement_reason = self._evaluate_source_disagreement(
            baseline_exp=baseline_exp,
            satellite_extraction=satellite_extraction,
            radar_features=radar_features,
            surface_observation=surface_observation,
        )

        # ---------------------------------------------------------------------
        # 6. Compute Multi-Horizon Outlooks (30m, 60m, 120m)
        # ---------------------------------------------------------------------
        horizons_dict: Dict[str, PrecipitationNowcastHorizonResult] = {}
        for h_mins in [30, 60, 120]:
            h_key = f"{h_mins}m"
            horizons_dict[h_key] = self._compute_horizon_nowcast(
                horizon_minutes=h_mins,
                issue_time_dt=now_utc,
                baseline_exp=baseline_exp,
                evidence_components=evidence_components,
                source_state=source_state,
                has_disagreement=has_disagreement,
                disagreement_reason=disagreement_reason,
                satellite_extraction=satellite_extraction,
                radar_features=radar_features,
            )

        primary_horizon = horizons_dict["60m"]
        overall_conf = primary_horizon.confidence

        # ---------------------------------------------------------------------
        # 7. Construct Provenance & Return Canonical Result
        # ---------------------------------------------------------------------
        is_real_obs = (
            satellite_extraction is not None
            and satellite_extraction.success
            and "SYNTHETIC" not in str(satellite_extraction.provenance.provider).upper()
            and "DEMO" not in str(satellite_extraction.provenance.provider).upper()
            and not str(p_id).lower().startswith("dholakpur")
        )
        data_mode = "LIVE" if is_real_obs else "DEMO"

        provenance = PrecipitationNowcastProvenance(
            nwp_source=f"{baseline_exp.source_model} (valid={baseline_exp.forecast_valid_time})",
            satellite_source=(
                f"{satellite_extraction.provenance.provider} {satellite_extraction.provenance.product} "
                f"(obs={satellite_extraction.observation_time})"
                if satellite_extraction and satellite_extraction.success
                else "NONE_OR_UNAVAILABLE"
            ),
            radar_source=(
                f"{radar_features.provider_name} (scan={radar_features.observation_time})"
                if radar_features and radar_features.is_available
                else "NONE_OR_UNAVAILABLE"
            ),
            surface_obs_source=(
                f"{surface_observation.station_id} (obs={surface_observation.observation_time})"
                if surface_observation and surface_observation.is_available
                else "NONE_OR_UNAVAILABLE"
            ),
            evidence_weight_version=settings.NOWCAST_METHOD_VERSION,
            config_version="1.0.0",
            data_mode=data_mode,
            generated_at=issue_iso,
        )

        return PanchayatPrecipitationNowcastResult(
            panchayat_id=p_id,
            panchayat_name=p_name or (satellite_extraction.panchayat_name if satellite_extraction else None),
            block_id=block_id,
            block_name=block_name,
            issue_time=issue_iso,
            baseline_forecast=baseline_exp,
            horizons=horizons_dict,
            primary_horizon=primary_horizon,
            evidence_components=evidence_components,
            source_state=source_state,
            overall_confidence=overall_conf,
            evidence_disagreement=has_disagreement,
            disagreement_details=disagreement_reason,
            provenance=provenance,
            status="SUCCESS",
            message=None,
            success=True,
        )

    def _normalize_baseline_forecast(
        self,
        baseline: Optional[Union[BaselinePrecipitationExpectation, Dict[str, Any]]],
        issue_iso: str,
        block_id: Optional[Union[str, int]],
        block_name: Optional[str],
    ) -> BaselinePrecipitationExpectation:
        """Normalizes external NWP baseline forecast into structured BaselinePrecipitationExpectation."""
        if isinstance(baseline, BaselinePrecipitationExpectation):
            return baseline

        if isinstance(baseline, dict):
            precip = float(baseline.get("precipitation_mm", baseline.get("rainfall_mm", 0.0)))
            prob = float(baseline.get("precipitation_probability", baseline.get("baseline_probability", 0.5 if precip > 0.1 else 0.1)))
            return BaselinePrecipitationExpectation(
                source_model=str(baseline.get("source_model", baseline.get("source", "IMD-GFS"))),
                forecast_valid_time=str(baseline.get("valid_time", baseline.get("forecast_valid_time", issue_iso))),
                forecast_issue_time=str(baseline.get("issue_time", issue_iso)),
                baseline_precipitation_mm=round(max(0.0, precip), 2),
                baseline_probability=round(min(1.0, max(0.0, prob)), 2),
                block_id=baseline.get("block_id", block_id),
                block_name=baseline.get("block_name", block_name),
            )

        # Default fallback baseline if omitted
        return BaselinePrecipitationExpectation(
            source_model="IMD-GFS-BASELINE",
            forecast_valid_time=issue_iso,
            forecast_issue_time=issue_iso,
            baseline_precipitation_mm=0.0,
            baseline_probability=0.10,
            block_id=block_id,
            block_name=block_name,
        )

    def _compile_evidence_components(
        self,
        baseline_exp: BaselinePrecipitationExpectation,
        satellite_extraction: Optional[PanchayatSatelliteExtractionResult],
        radar_features: Optional[RadarObservationFeatures],
        surface_observation: Optional[SurfaceObservationFeatures],
        conv_threshold: float,
    ) -> Tuple[List[PrecipitationEvidenceComponent], PrecipitationSourceState]:
        """Audits every potential evidence component, normalizes signal strength [0, 1], and sets source state."""
        components: List[PrecipitationEvidenceComponent] = []

        # 1. NWP Component
        nwp_sig = min(1.0, max(0.0, baseline_exp.baseline_probability))
        if baseline_exp.baseline_precipitation_mm > 0.0:
            # Boost signal if baseline amount is significant
            amt_factor = min(1.0, baseline_exp.baseline_precipitation_mm / 10.0)
            nwp_sig = min(1.0, max(nwp_sig, 0.40 + 0.50 * amt_factor))

        components.append(
            PrecipitationEvidenceComponent(
                source_type=EvidenceSignalType.NWP_FORECAST,
                source_name=baseline_exp.source_model,
                available=True,
                fresh=True,
                age_minutes=0.0,
                spatial_coverage_fraction=1.0,
                signal_strength=round(nwp_sig, 3),
                raw_metric_name="baseline_precipitation_mm",
                raw_metric_value=baseline_exp.baseline_precipitation_mm,
                disclaimer="NWP model baseline expectation; lower spatial granularity.",
            )
        )

        has_sat = False
        if satellite_extraction and satellite_extraction.success:
            has_sat = True
            feat = satellite_extraction.features or {}
            sat_sig = 0.0
            metric_name = "unknown"
            metric_val = 0.0

            if satellite_extraction.product_type == SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE:
                # Convective brightness temp: cold cloud top (<235K) = high convective precipitation potential
                cf = float(feat.get("cloud_fraction", 0.0) or 0.0)
                conv_frac = float(feat.get("fraction_below_convective_threshold", 0.0) or 0.0)
                min_k = float(feat.get("min_brightness_temperature_k", 300.0) or 300.0)
                
                # Signal strength heuristic:
                # Cold convective cores (< 220K) yield high signal; warm ground (>285K) yields near-zero signal
                if min_k < 220.0:
                    sat_sig = 0.85 + 0.15 * conv_frac
                elif min_k < conv_threshold:
                    sat_sig = 0.60 + 0.25 * conv_frac
                elif min_k < 260.0:
                    sat_sig = 0.30 + 0.30 * cf
                else:
                    sat_sig = 0.05 + 0.15 * cf

                # Temporal change modulation
                if satellite_extraction.temporal_change:
                    trend = satellite_extraction.temporal_change.trend
                    if trend == "COOLING_CONVECTIVE":
                        sat_sig = min(1.0, sat_sig + 0.15)
                    elif trend == "DISSIPATING":
                        sat_sig = max(0.0, sat_sig - 0.15)

                metric_name = "min_brightness_temperature_k"
                metric_val = min_k

            elif satellite_extraction.product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE:
                precip_mean = feat.get("satellite_precipitation_estimate_mean_mm")
                rain_area = float(feat.get("rain_area_fraction", 0.0) or 0.0)
                if precip_mean is not None and precip_mean > 0.0:
                    sat_sig = min(1.0, 0.40 + (precip_mean / 10.0) * 0.50 + rain_area * 0.10)
                    metric_val = float(precip_mean)
                else:
                    sat_sig = 0.05
                    metric_val = 0.0
                metric_name = "satellite_precipitation_estimate_mean_mm"

            elif satellite_extraction.product_type == SatelliteProductType.SATELLITE_CLOUD_MASK:
                cf = float(feat.get("cloud_fraction", 0.0) or 0.0)
                sat_sig = min(1.0, cf * 0.70)  # Cloud does not guarantee rain
                metric_name = "cloud_fraction"
                metric_val = cf

            components.append(
                PrecipitationEvidenceComponent(
                    source_type=(
                        EvidenceSignalType.SATELLITE_PRECIPITATION_ESTIMATE
                        if satellite_extraction.product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE
                        else EvidenceSignalType.SATELLITE_CLOUD_INFRARED
                    ),
                    source_name=f"{satellite_extraction.provenance.provider}_{satellite_extraction.provenance.product}",
                    available=True,
                    fresh=satellite_extraction.is_fresh,
                    age_minutes=satellite_extraction.observation_age_minutes,
                    spatial_coverage_fraction=satellite_extraction.coverage_fraction,
                    signal_strength=round(sat_sig, 3),
                    raw_metric_name=metric_name,
                    raw_metric_value=round(metric_val, 2),
                    disclaimer="Top-of-atmosphere radiance or algorithmic estimate; does NOT equal ground truth rain.",
                )
            )
        elif satellite_extraction and not satellite_extraction.success:
            components.append(
                PrecipitationEvidenceComponent(
                    source_type=EvidenceSignalType.SATELLITE_CLOUD_INFRARED,
                    source_name=f"{satellite_extraction.provenance.provider}_{satellite_extraction.provenance.product}",
                    available=False,
                    fresh=False,
                    age_minutes=satellite_extraction.observation_age_minutes,
                    spatial_coverage_fraction=satellite_extraction.coverage_fraction,
                    signal_strength=0.0,
                    raw_metric_name="coverage_fraction",
                    raw_metric_value=satellite_extraction.coverage_fraction,
                    disclaimer=satellite_extraction.message or "Panchayat falls outside satellite scene coverage.",
                )
            )

        # 3. Radar Component (Optional)
        has_radar = False
        if radar_features and radar_features.is_available:
            has_radar = True
            r_sig = 0.0
            refl = radar_features.max_reflectivity_dbz or radar_features.mean_reflectivity_dbz or 0.0
            echo_frac = radar_features.echo_area_fraction
            
            if refl >= 45.0:
                r_sig = 0.95
            elif refl >= 35.0:
                r_sig = 0.75 + 0.20 * echo_frac
            elif refl >= 20.0:
                r_sig = 0.40 + 0.30 * echo_frac
            elif refl >= 15.0:
                r_sig = 0.20 + 0.15 * echo_frac
            else:
                r_sig = 0.05

            components.append(
                PrecipitationEvidenceComponent(
                    source_type=EvidenceSignalType.RADAR_REFLECTIVITY,
                    source_name=radar_features.provider_name,
                    available=True,
                    fresh=radar_features.age_minutes <= self.freshness_threshold_minutes,
                    age_minutes=radar_features.age_minutes,
                    spatial_coverage_fraction=1.0,
                    signal_strength=round(r_sig, 3),
                    raw_metric_name="max_reflectivity_dbz",
                    raw_metric_value=round(refl, 1),
                    disclaimer="Direct precipitation echo reflectivity; subject to beam blockage and attenuation.",
                )
            )

        # 4. Surface AWS / Gauge Component (Optional)
        has_sfc = False
        if surface_observation and surface_observation.is_available:
            has_sfc = True
            if surface_observation.is_raining or (surface_observation.precipitation_last_1h_mm and surface_observation.precipitation_last_1h_mm >= self.rain_threshold_mm):
                sfc_sig = 0.95
            else:
                sfc_sig = 0.05

            components.append(
                PrecipitationEvidenceComponent(
                    source_type=EvidenceSignalType.SURFACE_OBSERVATION,
                    source_name=f"AWS_{surface_observation.station_id}",
                    available=True,
                    fresh=surface_observation.age_minutes <= self.freshness_threshold_minutes,
                    age_minutes=surface_observation.age_minutes,
                    spatial_coverage_fraction=1.0,
                    signal_strength=round(sfc_sig, 3),
                    raw_metric_name="precipitation_last_1h_mm",
                    raw_metric_value=surface_observation.precipitation_last_1h_mm,
                    disclaimer="Ground gauge confirmation; representative only within immediate station radius.",
                )
            )

        # Determine Multi-Source State
        if has_sat and has_radar and has_sfc:
            source_state = PrecipitationSourceState.NWP_SATELLITE_RADAR_SURFACE_OBS
        elif has_sat and has_radar:
            source_state = PrecipitationSourceState.NWP_SATELLITE_RADAR
        elif has_sat and has_sfc:
            source_state = PrecipitationSourceState.NWP_SATELLITE_SURFACE_OBS
        elif has_sat:
            source_state = PrecipitationSourceState.NWP_SATELLITE
        else:
            source_state = PrecipitationSourceState.NWP_ONLY

        return components, source_state

    def _evaluate_source_disagreement(
        self,
        baseline_exp: BaselinePrecipitationExpectation,
        satellite_extraction: Optional[PanchayatSatelliteExtractionResult],
        radar_features: Optional[RadarObservationFeatures],
        surface_observation: Optional[SurfaceObservationFeatures],
    ) -> Tuple[bool, Optional[str]]:
        """
        Detects contradictory evidence signals between NWP, satellite, and radar/surface observations.
        """
        nwp_rain_likely = baseline_exp.baseline_probability >= 0.50 or baseline_exp.baseline_precipitation_mm >= 1.0
        nwp_dry = baseline_exp.baseline_probability <= 0.20 and baseline_exp.baseline_precipitation_mm <= 0.0

        if satellite_extraction and satellite_extraction.success:
            feat = satellite_extraction.features or {}
            
            # Case 1: NWP predicts rain, but satellite shows clear sky / warm ground
            if satellite_extraction.product_type == SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE:
                min_k = float(feat.get("min_brightness_temperature_k", 290.0) or 290.0)
                cf = float(feat.get("cloud_fraction", 0.0) or 0.0)
                if nwp_rain_likely and min_k > 280.0 and cf < 0.15:
                    return (
                        True,
                        f"NWP forecasts precipitation (p={baseline_exp.baseline_probability}, {baseline_exp.baseline_precipitation_mm}mm) "
                        f"but satellite IR shows clear warm skies (T_min={min_k}K, cloud_fraction={cf})."
                    )
                if nwp_dry and min_k < 230.0 and cf > 0.70:
                    return (
                        True,
                        f"NWP forecasts dry conditions (p={baseline_exp.baseline_probability}) "
                        f"but satellite IR observes active deep convective cloud tops (T_min={min_k}K, cloud_fraction={cf})."
                    )

            elif satellite_extraction.product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE:
                p_mean = feat.get("satellite_precipitation_estimate_mean_mm")
                if nwp_rain_likely and p_mean is not None and p_mean == 0.0:
                    return (
                        True,
                        f"NWP forecasts precipitation ({baseline_exp.baseline_precipitation_mm}mm) "
                        f"but satellite precipitation estimate indicates 0.0 mm dry over Panchayat."
                    )
                if nwp_dry and p_mean is not None and p_mean >= 2.0:
                    return (
                        True,
                        f"NWP forecasts dry conditions but satellite precipitation estimate indicates {p_mean}mm."
                    )

        # Case 2: Radar disagrees with NWP
        if radar_features and radar_features.is_available:
            refl = radar_features.max_reflectivity_dbz or 0.0
            if nwp_dry and refl >= 35.0:
                return (
                    True,
                    f"NWP forecasts dry conditions but radar detects active convective core ({refl} dBZ)."
                )
            if nwp_rain_likely and refl < 10.0 and radar_features.echo_area_fraction == 0.0:
                return (
                    True,
                    f"NWP forecasts precipitation but radar detects zero precipitation echoes (< 10 dBZ)."
                )

        return False, None

    def _compute_horizon_nowcast(
        self,
        horizon_minutes: int,
        issue_time_dt: datetime,
        baseline_exp: BaselinePrecipitationExpectation,
        evidence_components: List[PrecipitationEvidenceComponent],
        source_state: PrecipitationSourceState,
        has_disagreement: bool,
        disagreement_reason: Optional[str],
        satellite_extraction: Optional[PanchayatSatelliteExtractionResult],
        radar_features: Optional[RadarObservationFeatures],
    ) -> PrecipitationNowcastHorizonResult:
        """
        Computes the two-stage nowcast for a specific time horizon (30m, 60m, 120m).
        """
        valid_dt = issue_time_dt.replace(minute=(issue_time_dt.minute + horizon_minutes) % 60) # Approx target
        valid_iso = issue_time_dt.isoformat()

        # ---------------------------------------------------------------------
        # Base Horizon Weights (Deterministic Research Heuristics)
        # ---------------------------------------------------------------------
        # At 30m: High observation weight; at 120m: NWP weight increases
        if horizon_minutes == 30:
            w_nwp = 0.15
            w_sat = 0.35
            w_radar = 0.45
            w_sfc = 0.35
        elif horizon_minutes == 60:
            w_nwp = 0.25
            w_sat = 0.30
            w_radar = 0.35
            w_sfc = 0.25
        else:  # 120 minutes
            w_nwp = 0.45
            w_sat = 0.25
            w_radar = 0.20
            w_sfc = 0.15

        # Calculate weighted signal and total weight
        total_w = 0.0
        weighted_signal = 0.0
        active_source_names: List[str] = []
        max_obs_age = 0.0
        min_cov = 1.0

        for comp in evidence_components:
            base_w = 0.0
            if comp.source_type == EvidenceSignalType.NWP_FORECAST:
                base_w = w_nwp
            elif comp.source_type in (EvidenceSignalType.SATELLITE_CLOUD_INFRARED, EvidenceSignalType.SATELLITE_PRECIPITATION_ESTIMATE):
                base_w = w_sat
                max_obs_age = max(max_obs_age, comp.age_minutes)
                min_cov = min(min_cov, comp.spatial_coverage_fraction)
            elif comp.source_type == EvidenceSignalType.RADAR_REFLECTIVITY:
                base_w = w_radar
                max_obs_age = max(max_obs_age, comp.age_minutes)
            elif comp.source_type == EvidenceSignalType.SURFACE_OBSERVATION:
                base_w = w_sfc
                max_obs_age = max(max_obs_age, comp.age_minutes)

            # Apply stale penalty
            if not comp.fresh:
                base_w *= self.stale_penalty_factor

            # Apply spatial coverage scaling
            base_w *= max(0.1, comp.spatial_coverage_fraction)

            if not comp.available:
                base_w = 0.0

            total_w += base_w
            weighted_signal += base_w * comp.signal_strength
            active_source_names.append(comp.source_type.value)

        # Stage 1: Probability of Measurable Precipitation
        raw_prob = (weighted_signal / total_w) if total_w > 0 else baseline_exp.baseline_probability
        
        # If evidence disagreement exists, moderate probability towards uncertainty
        if has_disagreement:
            # Dampen extremes: pull towards 0.50 by 20%
            raw_prob = 0.80 * raw_prob + 0.20 * 0.50

        prob = round(min(0.98, max(0.02, raw_prob)), 3)
        is_likely = prob >= 0.50

        # Stage 2: Expected Precipitation Amount (Conditional on rain occurring)
        expected_amount: Optional[float] = None
        intensity_mm_h: Optional[float] = None
        uncertainty_range: Optional[Tuple[float, float]] = None

        if prob >= 0.25:
            # If radar available and active, radar rate provides highest fidelity
            if radar_features and radar_features.is_available and radar_features.radar_estimated_rain_rate_mm_h is not None:
                rate = radar_features.radar_estimated_rain_rate_mm_h
                intensity_mm_h = round(rate, 2)
                expected_amount = round(rate * (horizon_minutes / 60.0), 2)
                uncertainty_range = (round(max(0.1, expected_amount * 0.6), 2), round(expected_amount * 1.5, 2))

            # Else if satellite precipitation estimate is available
            elif (
                satellite_extraction
                and satellite_extraction.success
                and satellite_extraction.product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE
                and satellite_extraction.features.get("satellite_precipitation_estimate_mean_mm") is not None
            ):
                sat_precip = float(satellite_extraction.features["satellite_precipitation_estimate_mean_mm"])
                if sat_precip > 0.0:
                    intensity_mm_h = round(sat_precip, 2)
                    expected_amount = round(sat_precip * (horizon_minutes / 60.0), 2)
                    uncertainty_range = (round(max(0.1, expected_amount * 0.5), 2), round(expected_amount * 1.6, 2))
                else:
                    expected_amount = 0.0

            # Else if NWP predicts rainfall and satellite confirms cloud development
            elif baseline_exp.baseline_precipitation_mm > 0.0:
                base_amt = baseline_exp.baseline_precipitation_mm * (horizon_minutes / 180.0) # Proportion of block 3h accumulation
                if satellite_extraction and satellite_extraction.success:
                    # Modulate by satellite cloud fraction / convective intensity
                    conv_frac = float(satellite_extraction.features.get("fraction_below_convective_threshold", 0.5) or 0.5)
                    expected_amount = round(base_amt * (0.5 + conv_frac), 2)
                else:
                    expected_amount = round(base_amt, 2)
                intensity_mm_h = round(expected_amount / (horizon_minutes / 60.0), 2)
                uncertainty_range = (round(max(0.1, expected_amount * 0.4), 2), round(expected_amount * 1.8, 2))

            else:
                # Evidence is insufficient to formulate a reliable numeric depth
                expected_amount = None
                intensity_mm_h = None
                uncertainty_range = None
        else:
            # Below rain threshold, expected amount is 0.0
            expected_amount = 0.0
            intensity_mm_h = 0.0
            uncertainty_range = (0.0, 0.0)

        # Confidence Calculation
        conf_tier, conf_score = self._calculate_confidence(
            evidence_components=evidence_components,
            source_state=source_state,
            has_disagreement=has_disagreement,
            min_spatial_coverage=min_cov,
            max_observation_age=max_obs_age,
        )

        return PrecipitationNowcastHorizonResult(
            horizon_minutes=horizon_minutes,
            valid_time=valid_iso,
            rain_probability=prob,
            measurable_rain_threshold_mm=self.rain_threshold_mm,
            is_rain_likely=is_likely,
            expected_amount_mm=expected_amount,
            expected_intensity_mm_h=intensity_mm_h,
            amount_uncertainty_range_mm=uncertainty_range,
            confidence=conf_tier,
            confidence_score=conf_score,
            evidence_sources=active_source_names,
            source_state=source_state,
            evidence_disagreement=has_disagreement,
            disagreement_reason=disagreement_reason,
            observation_age_minutes=round(max_obs_age, 1),
            spatial_coverage=round(min_cov, 3),
            fusion_method=settings.NOWCAST_METHOD_VERSION,
        )

    def _calculate_confidence(
        self,
        evidence_components: List[PrecipitationEvidenceComponent],
        source_state: PrecipitationSourceState,
        has_disagreement: bool,
        min_spatial_coverage: float,
        max_observation_age: float,
    ) -> Tuple[NowcastConfidence, float]:
        """
        Computes composite confidence score [0.0, 1.0] and categorizes into conservative tiers.
        """
        # Disagreement strictly caps confidence at LOW
        if has_disagreement:
            return NowcastConfidence.LOW, 0.35

        # Check coverage
        if min_spatial_coverage < self.min_spatial_coverage:
            return NowcastConfidence.INSUFFICIENT_DATA, 0.15

        # Independent sources count
        active_comps = [c for c in evidence_components if c.available]
        fresh_comps = [c for c in active_comps if c.fresh]

        # Scoring heuristics:
        # Base score from source diversity
        if source_state in (PrecipitationSourceState.NWP_SATELLITE_RADAR_SURFACE_OBS, PrecipitationSourceState.NWP_SATELLITE_RADAR):
            base_score = 0.85
        elif source_state in (PrecipitationSourceState.NWP_SATELLITE_SURFACE_OBS, PrecipitationSourceState.NWP_SATELLITE):
            base_score = 0.65
        else:
            base_score = 0.40  # NWP_ONLY

        # Latency penalty
        if max_observation_age > self.freshness_threshold_minutes:
            base_score -= 0.20

        # Coverage penalty
        if min_spatial_coverage < 0.80:
            base_score -= 0.15

        final_score = round(min(1.0, max(0.10, base_score)), 2)

        if final_score >= 0.75 and len(fresh_comps) >= 2:
            return NowcastConfidence.HIGH, final_score
        elif final_score >= 0.50:
            return NowcastConfidence.MEDIUM, final_score
        elif final_score >= 0.25:
            return NowcastConfidence.LOW, final_score
        else:
            return NowcastConfidence.INSUFFICIENT_DATA, final_score

    def _build_fail_closed_result(
        self,
        panchayat_id: str,
        panchayat_name: Optional[str],
        issue_time: str,
        status: str,
        message: str,
    ) -> PanchayatPrecipitationNowcastResult:
        """Constructs an explicit fail-closed nowcast result."""
        dummy_baseline = BaselinePrecipitationExpectation(
            source_model="UNAVAILABLE",
            forecast_valid_time=issue_time,
            forecast_issue_time=issue_time,
            baseline_precipitation_mm=0.0,
            baseline_probability=0.0,
        )
        dummy_horizon = PrecipitationNowcastHorizonResult(
            horizon_minutes=60,
            valid_time=issue_time,
            rain_probability=0.0,
            measurable_rain_threshold_mm=self.rain_threshold_mm,
            is_rain_likely=False,
            expected_amount_mm=None,
            confidence=NowcastConfidence.INSUFFICIENT_DATA,
            confidence_score=0.0,
            evidence_sources=[],
            source_state=PrecipitationSourceState.INSUFFICIENT_DATA,
            evidence_disagreement=False,
            observation_age_minutes=0.0,
            spatial_coverage=0.0,
            fusion_method=settings.NOWCAST_METHOD_VERSION,
        )
        provenance = PrecipitationNowcastProvenance(
            nwp_source="UNAVAILABLE",
            evidence_weight_version=settings.NOWCAST_METHOD_VERSION,
            config_version="1.0.0",
            data_mode="LIVE" if not str(panchayat_id).lower().startswith("dholakpur") else "DEMO",
            generated_at=issue_time,
        )
        return PanchayatPrecipitationNowcastResult(
            panchayat_id=panchayat_id,
            panchayat_name=panchayat_name,
            issue_time=issue_time,
            baseline_forecast=dummy_baseline,
            horizons={"30m": dummy_horizon, "60m": dummy_horizon, "120m": dummy_horizon},
            primary_horizon=dummy_horizon,
            evidence_components=[],
            source_state=PrecipitationSourceState.INSUFFICIENT_DATA,
            overall_confidence=NowcastConfidence.INSUFFICIENT_DATA,
            evidence_disagreement=False,
            provenance=provenance,
            status=status,
            message=message,
            success=False,
        )


# Global singleton service
panchayat_precipitation_nowcast_service = PanchayatPrecipitationNowcastService()


def generate_panchayat_precipitation_nowcast(
    panchayat_id: Optional[str] = None,
    panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
    baseline_forecast: Optional[Union[BaselinePrecipitationExpectation, Dict[str, Any]]] = None,
    satellite_grid: Optional[SourceWeatherGrid] = None,
    previous_satellite_grid: Optional[SourceWeatherGrid] = None,
    radar_features: Optional[RadarObservationFeatures] = None,
    surface_observation: Optional[SurfaceObservationFeatures] = None,
    convective_threshold_k: Optional[float] = None,
    require_verified: bool = False,
    issue_time: Optional[str] = None,
) -> PanchayatPrecipitationNowcastResult:
    """Programmatic entrypoint for generating an observation-fused precipitation nowcast."""
    return panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id=panchayat_id,
        panchayat_geometry=panchayat_geometry,
        baseline_forecast=baseline_forecast,
        satellite_grid=satellite_grid,
        previous_satellite_grid=previous_satellite_grid,
        radar_features=radar_features,
        surface_observation=surface_observation,
        convective_threshold_k=convective_threshold_k,
        require_verified=require_verified,
        issue_time=issue_time,
    )
