"""
Panchayat Satellite Observation Service
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Integrates the SatelliteObservationProvider with the Task 2 SpatialMaskingService.
Provides independent Panchayat-specific satellite feature extraction (A vs B),
temporal change tracking, freshness classification, and strict provenance preservation.

CRITICAL POLICY:
- Satellite cloud data is NOT automatically rainfall.
- Satellite precipitation estimates remain explicitly labeled as estimates.
- Preserves native resolution without false microclimate resolution claims.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from shapely.geometry import Polygon, MultiPolygon

from app.core.config import settings
from app.core.logging import logger
from app.gis.boundary_registry import boundary_registry
from app.gis.spatial_masking import spatial_masking_service, SpatialMaskingService
from app.schemas.satellite import (
    ObservationFreshnessTier,
    PanchayatSatelliteExtractionResult,
    SatelliteCloudFeatures,
    SatelliteObservationStatus,
    SatelliteProductType,
    SatelliteProvenance,
    SatelliteTemporalDelta,
    SourceResolutionDiagnostic,
)
from app.schemas.spatial_masking import (
    CoverageQuality,
    PanchayatSpatialExtractionResult,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)
from app.weather.providers.satellite_provider import SatelliteObservationProvider


class SatelliteObservationService:
    """
    Coordinates ingestion, spatial masking, and meteorological feature extraction
    for authorized satellite products at the Panchayat administrative level.
    """

    def __init__(
        self,
        provider: Optional[SatelliteObservationProvider] = None,
        masking_service: Optional[SpatialMaskingService] = None,
    ):
        self.provider = provider or SatelliteObservationProvider()
        self.masking_service = masking_service or spatial_masking_service

    def fetch_satellite_observation(
        self,
        product: Union[SatelliteProductType, str],
        observation_time: Optional[Union[datetime, str]] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> SourceWeatherGrid:
        """
        Retrieves or ingests an authorized satellite product as a georeferenced SourceWeatherGrid.
        """
        prod_str = product.value if isinstance(product, SatelliteProductType) else str(product)
        return self.provider.fetch_observation(
            product=prod_str,
            observation_time=observation_time,
            bounding_box=bounding_box,
            options=options,
        )

    def extract_panchayat_satellite_features(
        self,
        panchayat_id: Optional[str] = None,
        panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
        satellite_grid: SourceWeatherGrid = ...,
        previous_satellite_grid: Optional[SourceWeatherGrid] = None,
        convective_threshold_k: Optional[float] = None,
        detection_threshold_mm: float = 0.1,
        require_verified: bool = False,
        freshness_threshold_minutes: Optional[float] = None,
        source_url: Optional[str] = None,
        file_sha256: Optional[str] = None,
    ) -> PanchayatSatelliteExtractionResult:
        """
        Extracts independent Panchayat-specific satellite features using the Task 2 spatial-masking layer.

        Steps:
        1. Executes exact polygon-cell intersection via Task 2 SpatialMaskingService.
        2. Derives mathematically and scientifically defensible cloud / precipitation features.
        3. Computes temporal deltas if previous_satellite_grid is provided.
        4. Assesses observation freshness against operational threshold.
        5. Preserves full provenance and native sensor resolution.
        """
        conv_threshold = (
            convective_threshold_k
            if convective_threshold_k is not None
            else self.provider.convective_threshold_k
        )
        fresh_thresh = (
            freshness_threshold_minutes
            if freshness_threshold_minutes is not None
            else self.provider.freshness_threshold_minutes
        )

        # ---------------------------------------------------------------------
        # 1. Delegate Spatial Intersection to Task 2 SpatialMaskingService
        # ---------------------------------------------------------------------
        base_extraction: PanchayatSpatialExtractionResult = self.masking_service.extract_panchayat_spatial_features(
            panchayat_id=panchayat_id,
            panchayat_geometry=panchayat_geometry,
            source_grid=satellite_grid,
            require_verified=require_verified,
            include_cell_details=True,
            detection_threshold_mm=detection_threshold_mm,
        )

        # Parse product taxonomy
        prod_name = satellite_grid.provenance.source_product or "SATELLITE_GENERIC"
        try:
            prod_type = SatelliteProductType(prod_name)
        except ValueError:
            # Fall back by checking variable_name
            if "precipitation" in satellite_grid.variable_name.lower():
                prod_type = SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE
            elif "brightness" in satellite_grid.variable_name.lower() or "ir" in satellite_grid.variable_name.lower():
                prod_type = SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE
            elif "cloud" in satellite_grid.variable_name.lower():
                prod_type = SatelliteProductType.SATELLITE_CLOUD_MASK
            elif "vapour" in satellite_grid.variable_name.lower() or "vapor" in satellite_grid.variable_name.lower():
                prod_type = SatelliteProductType.SATELLITE_WATER_VAPOUR
            elif "visible" in satellite_grid.variable_name.lower():
                prod_type = SatelliteProductType.SATELLITE_VISIBLE_REFLECTANCE
            else:
                prod_type = SatelliteProductType.SATELLITE_CLOUD_MASK

        # Build SatelliteProvenance
        obs_time = satellite_grid.provenance.valid_time
        provenance = self.provider.build_satellite_provenance(
            grid=satellite_grid,
            product_type=prod_type,
            observation_time=obs_time,
            file_sha256=file_sha256,
            source_url=source_url,
            source_identifier=satellite_grid.provenance.source_product,
        )

        # ---------------------------------------------------------------------
        # 2. Freshness Check
        # ---------------------------------------------------------------------
        is_fresh, age_mins, fresh_status = self.provider.check_freshness(
            observation_time=obs_time,
            threshold_minutes=fresh_thresh,
        )

        # ---------------------------------------------------------------------
        # 3. Handle Fail-Closed Base Results
        # ---------------------------------------------------------------------
        if not base_extraction.success:
            return PanchayatSatelliteExtractionResult(
                panchayat_id=base_extraction.panchayat_id,
                panchayat_name=base_extraction.panchayat_name,
                source="SATELLITE",
                product=prod_type.value,
                product_type=prod_type,
                observation_time=obs_time,
                product_valid_time=satellite_grid.provenance.valid_time,
                native_resolution_km=satellite_grid.provenance.native_resolution_km,
                features={},
                temporal_change=None,
                coverage_quality=base_extraction.coverage_quality,
                coverage_fraction=base_extraction.coverage_fraction,
                cells_intersecting=base_extraction.cells_intersecting,
                valid_cells_intersecting=base_extraction.valid_cells_intersecting,
                observation_age_minutes=age_mins,
                is_fresh=is_fresh,
                freshness_status=fresh_status,
                provenance=provenance,
                status=base_extraction.status,
                message=base_extraction.message,
                success=False,
            )

        # ---------------------------------------------------------------------
        # 4. Domain-Specific Feature Computation
        # ---------------------------------------------------------------------
        features: Dict[str, Any] = {}
        intersections = base_extraction.cell_intersections or []
        valid_intersections = [ci for ci in intersections if ci.is_valid_value and ci.source_value is not None]

        if prod_type == SatelliteProductType.SATELLITE_CLOUD_MASK:
            # Categorical cloud mask (1.0 = cloudy, 0.0 = clear)
            if valid_intersections:
                cloud_cells = [ci for ci in valid_intersections if ci.source_value >= 0.5]
                cloud_area = sum(ci.intersection_area_sq_km for ci in cloud_cells)
                total_valid_area = sum(ci.intersection_area_sq_km for ci in valid_intersections)
                cf = round(cloud_area / total_valid_area, 4) if total_valid_area > 0 else 0.0
                clr = round(1.0 - cf, 4)
                cloud_feats = SatelliteCloudFeatures(
                    cloud_fraction=cf,
                    clear_fraction=clr,
                    cloud_cells_intersecting=len(cloud_cells),
                    total_valid_cells=len(valid_intersections),
                )
                features = cloud_feats.model_dump()
            else:
                features = SatelliteCloudFeatures(
                    cloud_fraction=None, clear_fraction=None,
                    cloud_cells_intersecting=0, total_valid_cells=0
                ).model_dump()

        elif prod_type == SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE:
            # Thermal IR Brightness Temperature (Kelvin)
            if valid_intersections:
                vals = [float(ci.source_value) for ci in valid_intersections]
                weights = [ci.intersection_area_sq_km for ci in valid_intersections]
                total_weight = sum(weights)

                if total_weight > 0:
                    weighted_mean_k = sum(v * w for v, w in zip(vals, weights)) / total_weight
                else:
                    weighted_mean_k = sum(vals) / len(vals)

                min_k = min(vals)
                std_k = math.sqrt(sum((v - weighted_mean_k) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0.0

                # Cells colder than convective threshold
                cold_cells = [ci for ci in valid_intersections if float(ci.source_value) < conv_threshold]
                cold_area = sum(ci.intersection_area_sq_km for ci in cold_cells)
                frac_conv = round(cold_area / total_weight, 4) if total_weight > 0 else 0.0

                # Cloud fraction estimate: IR < 273.15 K (0°C level) or below convective threshold
                cloud_cells = [ci for ci in valid_intersections if float(ci.source_value) < 273.15]
                cloud_area = sum(ci.intersection_area_sq_km for ci in cloud_cells)
                cf = round(cloud_area / total_weight, 4) if total_weight > 0 else 0.0
                clr = round(1.0 - cf, 4)

                gradient = round(std_k / (weighted_mean_k if weighted_mean_k > 0 else 1.0), 5)

                cloud_feats = SatelliteCloudFeatures(
                    cloud_fraction=cf,
                    clear_fraction=clr,
                    mean_brightness_temperature_k=round(weighted_mean_k, 2),
                    min_brightness_temperature_k=round(min_k, 2),
                    fraction_below_convective_threshold=frac_conv,
                    convective_threshold_k=conv_threshold,
                    spatial_std_k=round(std_k, 2),
                    spatial_gradient=gradient,
                    cloud_cells_intersecting=len(cold_cells),
                    total_valid_cells=len(valid_intersections),
                )
                features = cloud_feats.model_dump()
            else:
                features = SatelliteCloudFeatures(
                    cloud_fraction=None, clear_fraction=None,
                    convective_threshold_k=conv_threshold,
                    cloud_cells_intersecting=0, total_valid_cells=0
                ).model_dump()

        elif prod_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE:
            # Satellite precipitation estimate (MUST NOT BE NAMED observed_rainfall)
            # Reuses base continuous/precipitation extraction from Task 2
            precip_stats = base_extraction.features.copy() if base_extraction.features else {}
            
            p_mean = precip_stats.get("weighted_mean_amount_mm")
            if p_mean is None:
                p_mean = precip_stats.get("accumulated_precipitation_mm")
            if p_mean is None:
                p_mean = precip_stats.get("weighted_mean")
            if p_mean is None:
                p_mean = precip_stats.get("mean_rate_mm_h")

            p_max = precip_stats.get("max_amount_mm")
            if p_max is None:
                p_max = precip_stats.get("max")
            if p_max is None:
                p_max = precip_stats.get("max_intensity_mm_h")

            p_min = precip_stats.get("min_amount_mm")
            if p_min is None:
                p_min = precip_stats.get("min")

            # Explicitly label semantics
            features = {
                "satellite_precipitation_estimate_mean_mm": p_mean,
                "satellite_precipitation_estimate_max_mm": p_max,
                "satellite_precipitation_estimate_min_mm": p_min,
                "rain_area_fraction": precip_stats.get("rain_area_fraction", 0.0),
                "is_rain_detected": precip_stats.get("is_rain_detected", False),
                "detection_threshold_mm": detection_threshold_mm,
                "valid_cell_fraction": round(len(valid_intersections) / len(intersections), 4) if intersections else 0.0,
                "missing_cell_fraction": round((len(intersections) - len(valid_intersections)) / len(intersections), 4) if intersections else 0.0,
                "is_estimated": True,
            }

        else:
            # Water Vapour or Visible Reflectance
            features = base_extraction.features.copy() if base_extraction.features else {}

        # ---------------------------------------------------------------------
        # 5. Temporal Change Metrics (T0 -> T1)
        # ---------------------------------------------------------------------
        temporal_delta: Optional[SatelliteTemporalDelta] = None
        if previous_satellite_grid is not None:
            temporal_delta = self._compute_temporal_delta(
                panchayat_id=panchayat_id,
                panchayat_geometry=panchayat_geometry,
                t0_grid=previous_satellite_grid,
                t1_grid=satellite_grid,
                t1_features=features,
                panchayat_area_sq_km=base_extraction.panchayat_area_sq_km,
                conv_threshold=conv_threshold,
                detection_threshold_mm=detection_threshold_mm,
            )

        # Operational Freshness Classification (Task 7 Requirement 8)
        if age_mins is None or math.isnan(age_mins):
            fresh_tier = ObservationFreshnessTier.UNAVAILABLE
        elif age_mins <= fresh_thresh:
            fresh_tier = ObservationFreshnessTier.FRESH
        elif age_mins <= 180.0:
            fresh_tier = ObservationFreshnessTier.AGING
        else:
            fresh_tier = ObservationFreshnessTier.STALE

        # Product Resolution Validation Diagnostic (Task 7 Requirement 6)
        poly_area = base_extraction.panchayat_area_sq_km
        native_res = satellite_grid.provenance.native_resolution_km
        if poly_area and poly_area > 0 and native_res and native_res > 0:
            target_scale = math.sqrt(poly_area)
            if native_res > target_scale:
                res_diag = SourceResolutionDiagnostic.SOURCE_RESOLUTION_COARSE_FOR_TARGET
            else:
                res_diag = SourceResolutionDiagnostic.SOURCE_RESOLUTION_ADEQUATE_FOR_TARGET
        else:
            res_diag = SourceResolutionDiagnostic.SOURCE_RESOLUTION_UNKNOWN

        return PanchayatSatelliteExtractionResult(
            panchayat_id=base_extraction.panchayat_id,
            panchayat_name=base_extraction.panchayat_name,
            source="SATELLITE",
            product=prod_type.value,
            product_type=prod_type,
            observation_time=obs_time,
            product_valid_time=satellite_grid.provenance.valid_time,
            native_resolution_km=satellite_grid.provenance.native_resolution_km,
            features=features,
            temporal_change=temporal_delta,
            coverage_quality=base_extraction.coverage_quality,
            coverage_fraction=base_extraction.coverage_fraction,
            cells_intersecting=base_extraction.cells_intersecting,
            valid_cells_intersecting=base_extraction.valid_cells_intersecting,
            observation_age_minutes=age_mins,
            is_fresh=is_fresh,
            freshness_status=fresh_status,
            freshness_tier=fresh_tier,
            resolution_diagnostic=res_diag,
            provenance=provenance,
            status="SUCCESS",
            message=None,
            success=True,
        )

    def _compute_temporal_delta(
        self,
        panchayat_id: Optional[str],
        panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]],
        t0_grid: SourceWeatherGrid,
        t1_grid: SourceWeatherGrid,
        t1_features: Dict[str, Any],
        panchayat_area_sq_km: float,
        conv_threshold: float,
        detection_threshold_mm: float,
    ) -> Optional[SatelliteTemporalDelta]:
        """Calculates deterministic empirical changes between observations at T0 and T1."""
        t0_obs_time = t0_grid.provenance.valid_time
        t1_obs_time = t1_grid.provenance.valid_time

        try:
            dt0 = datetime.fromisoformat(t0_obs_time.replace("Z", "+00:00"))
            dt1 = datetime.fromisoformat(t1_obs_time.replace("Z", "+00:00"))
            delta_mins = max(0.0, round((dt1 - dt0).total_seconds() / 60.0, 1))
        except Exception:
            delta_mins = 0.0

        # Extract T0 features on the same polygon
        t0_res = self.extract_panchayat_satellite_features(
            panchayat_id=panchayat_id,
            panchayat_geometry=panchayat_geometry,
            satellite_grid=t0_grid,
            previous_satellite_grid=None,
            convective_threshold_k=conv_threshold,
            detection_threshold_mm=detection_threshold_mm,
        )

        if not t0_res.success:
            return None

        t0_feat = t0_res.features or {}
        
        # Calculate deltas
        cf0 = t0_feat.get("cloud_fraction")
        cf1 = t1_features.get("cloud_fraction")
        cf_delta = round(cf1 - cf0, 4) if (cf0 is not None and cf1 is not None) else None

        # Mean signal delta
        mean0 = t0_feat.get("mean_brightness_temperature_k") or t0_feat.get("satellite_precipitation_estimate_mean_mm") or t0_feat.get("weighted_mean")
        mean1 = t1_features.get("mean_brightness_temperature_k") or t1_features.get("satellite_precipitation_estimate_mean_mm") or t1_features.get("weighted_mean")
        mean_delta = round(mean1 - mean0, 3) if (mean0 is not None and mean1 is not None) else None

        min0 = t0_feat.get("min_brightness_temperature_k")
        min1 = t1_features.get("min_brightness_temperature_k")
        min_delta = round(min1 - min0, 3) if (min0 is not None and min1 is not None) else None

        area_delta = round(cf_delta * panchayat_area_sq_km, 3) if cf_delta is not None else None

        # Empirical trend classifier
        if min_delta is not None and min_delta <= -5.0:
            trend = "COOLING_CONVECTIVE"
        elif cf_delta is not None and cf_delta >= 0.10:
            trend = "EXPANDING"
        elif cf_delta is not None and cf_delta <= -0.10:
            trend = "DISSIPATING"
        elif mean_delta is not None and mean_delta >= 5.0:
            trend = "WARMING"
        else:
            trend = "STEADY"

        return SatelliteTemporalDelta(
            t0_observation_time=t0_obs_time,
            t1_observation_time=t1_obs_time,
            delta_minutes=delta_mins,
            cloud_fraction_delta=cf_delta,
            mean_signal_delta=mean_delta,
            min_signal_delta=min_delta,
            cloud_area_change_sq_km=area_delta,
            trend=trend,
        )


# Global singleton instance
satellite_observation_service = SatelliteObservationService()


def fetch_satellite_observation(
    product: Union[SatelliteProductType, str],
    observation_time: Optional[Union[datetime, str]] = None,
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> SourceWeatherGrid:
    """Programmatic entrypoint to fetch or ingest a satellite SourceWeatherGrid."""
    return satellite_observation_service.fetch_satellite_observation(
        product=product,
        observation_time=observation_time,
        bounding_box=bounding_box,
        options=options,
    )


def extract_panchayat_satellite_features(
    panchayat_id: Optional[str] = None,
    panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
    satellite_grid: SourceWeatherGrid = ...,
    previous_satellite_grid: Optional[SourceWeatherGrid] = None,
    convective_threshold_k: Optional[float] = None,
    detection_threshold_mm: float = 0.1,
    require_verified: bool = False,
    freshness_threshold_minutes: Optional[float] = None,
) -> PanchayatSatelliteExtractionResult:
    """Programmatic entrypoint for independent Panchayat satellite feature extraction."""
    return satellite_observation_service.extract_panchayat_satellite_features(
        panchayat_id=panchayat_id,
        panchayat_geometry=panchayat_geometry,
        satellite_grid=satellite_grid,
        previous_satellite_grid=previous_satellite_grid,
        convective_threshold_k=convective_threshold_k,
        detection_threshold_mm=detection_threshold_mm,
        require_verified=require_verified,
        freshness_threshold_minutes=freshness_threshold_minutes,
    )
