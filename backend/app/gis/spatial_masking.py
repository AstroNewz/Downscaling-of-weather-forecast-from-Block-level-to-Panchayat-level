"""
Panchayat Spatial Masking Service
SIH Problem Statement 26074 (Weather Downscaling - Task 2)

Performs exact geometric polygon-to-grid cell intersection, fractional
overlap calculation, and area-weighted meteorological feature extraction.
Guarantees administrative separation (Panchayat A vs B) and preserves
native source resolution without false claims of hyper-resolution.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pyproj
from shapely.geometry import shape, mapping, box, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from app.core.logging import logger
from app.gis.boundary_registry import PanchayatBoundaryRegistry, boundary_registry
from app.schemas.spatial_masking import (
    CellIntersectionResult,
    ContinuousVariableFeatures,
    CoverageQuality,
    PanchayatSpatialExtractionResult,
    PrecipitationVariableFeatures,
    SourceGridCell,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)


class SpatialMaskingService:
    """
    Reusable spatial-masking engine for intersecting administrative boundaries
    with gridded weather and observation fields.

    Core Scientific Mandates:
    1. Independent Panchayat Processing: Each Panchayat polygon acts as an isolated
       spatial mask; neighboring Panchayats derive statistics solely from cells
       intersecting their respective geometric boundaries.
    2. Area-Weighted Aggregation: Continuous variables account for fractional cell
       coverage area rather than assuming uniform cell center weighting.
    3. Semantic Separation: Precipitation amounts, intensities, rain-area fractions,
       and detection flags are computed with explicit meteorological semantics.
    4. Missing Value Strictness: NaN / missing cells are excluded from weight
       denominators and reported; zero precipitation (0.0 mm) is never confused with NaN.
    5. Native Resolution Preservation: Full provenance is maintained; masking does
       NOT claim to synthesize higher-resolution atmospheric information.
    """

    def __init__(self, registry: Optional[PanchayatBoundaryRegistry] = None):
        self.registry = registry or boundary_registry
        self.geod = pyproj.Geod(ellps="WGS84")

    def _calculate_geodesic_area_sq_km(self, geom: BaseGeometry) -> float:
        """Computes true ellipsoidal surface area in square kilometers."""
        if geom is None or geom.is_empty:
            return 0.0
        try:
            area_m2, _ = self.geod.geometry_area_perimeter(geom)
            return round(abs(float(area_m2)) / 1e6, 6)
        except Exception:
            return 0.0

    def extract_panchayat_spatial_features(
        self,
        panchayat_id: Optional[str] = None,
        panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
        source_grid: SourceWeatherGrid = ...,
        valid_time: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        require_verified: bool = False,
        include_cell_details: bool = True,
        detection_threshold_mm: float = 0.1,
    ) -> PanchayatSpatialExtractionResult:
        """
        Executes exact polygon-cell intersection and extracts Panchayat-specific spatial features.

        Parameters:
            panchayat_id: Target Panchayat ID to resolve from canonical registry
            panchayat_geometry: Direct Shapely Polygon/MultiPolygon or GeoJSON dict (overrides registry)
            source_grid: Georeferenced weather/observation grid containing cells and values
            valid_time: Optional validity timestamp override
            source_metadata: Optional supplementary source metadata
            require_verified: If True, fails closed when Panchayat geometry is unverified
            include_cell_details: If True, populates per-cell intersection breakdown
            detection_threshold_mm: Rainfall threshold in mm for rain area fraction
        """
        process_ts = datetime.now(timezone.utc).isoformat()
        target_valid_time = valid_time or source_grid.provenance.valid_time

        # ---------------------------------------------------------------------
        # 1. Resolve & Validate Panchayat Polygon Geometry
        # ---------------------------------------------------------------------
        poly: Optional[BaseGeometry] = None
        p_name: Optional[str] = None
        p_id = panchayat_id or "ANONYMOUS_PANCHAYAT"
        panchayat_area_sq_km = 0.0

        if panchayat_geometry is not None:
            if isinstance(panchayat_geometry, dict):
                try:
                    poly = shape(panchayat_geometry)
                except Exception as e:
                    return self._build_fail_closed_result(
                        p_id=p_id, p_name=None, source_grid=source_grid, valid_time=target_valid_time,
                        status="INVALID_GEOMETRY", message=f"Failed to parse geometry dictionary: {e}",
                        process_ts=process_ts
                    )
            elif isinstance(panchayat_geometry, (Polygon, MultiPolygon)):
                poly = panchayat_geometry
            else:
                return self._build_fail_closed_result(
                    p_id=p_id, p_name=None, source_grid=source_grid, valid_time=target_valid_time,
                    status="INVALID_GEOMETRY", message="Supplied geometry must be a Polygon or MultiPolygon.",
                    process_ts=process_ts
                )

            if not poly.is_valid:
                poly = make_valid(poly)

            if not isinstance(poly, (Polygon, MultiPolygon)):
                return self._build_fail_closed_result(
                    p_id=p_id, p_name=None, source_grid=source_grid, valid_time=target_valid_time,
                    status="INVALID_GEOMETRY", message=f"Supplied geometry must be a Polygon or MultiPolygon. Received {poly.geom_type}.",
                    process_ts=process_ts
                )

            panchayat_area_sq_km = self._calculate_geodesic_area_sq_km(poly)


        elif panchayat_id is not None:
            rec = self.registry.get_by_id(panchayat_id) or self.registry.get_by_lgd_code(panchayat_id)
            if not rec:
                return self._build_fail_closed_result(
                    p_id=p_id, p_name=None, source_grid=source_grid, valid_time=target_valid_time,
                    status="PANCHAYAT_NOT_FOUND", message=f"Panchayat ID '{panchayat_id}' not found in canonical boundary registry.",
                    process_ts=process_ts
                )
            if require_verified and not rec.is_verified:
                return self._build_fail_closed_result(
                    p_id=p_id, p_name=rec.panchayat_name, source_grid=source_grid, valid_time=target_valid_time,
                    status="UNVERIFIED_GEOMETRY", message=f"Panchayat '{rec.panchayat_name}' boundary is unverified; fail-closed policy active.",
                    process_ts=process_ts
                )
            poly = self.registry.get_shapely_geometry(rec.panchayat_id)
            p_name = rec.panchayat_name
            p_id = rec.panchayat_id
            panchayat_area_sq_km = rec.area_sq_km
        else:
            return self._build_fail_closed_result(
                p_id="UNKNOWN", p_name=None, source_grid=source_grid, valid_time=target_valid_time,
                status="MISSING_INPUT", message="Either panchayat_id or panchayat_geometry must be provided.",
                process_ts=process_ts
            )

        if poly is None or poly.is_empty:
            return self._build_fail_closed_result(
                p_id=p_id, p_name=p_name, source_grid=source_grid, valid_time=target_valid_time,
                status="EMPTY_GEOMETRY", message="Panchayat geometry is empty or degenerate.",
                process_ts=process_ts
            )

        # ---------------------------------------------------------------------
        # 2. Validate Source Weather Grid
        # ---------------------------------------------------------------------
        if not source_grid.cells:
            return self._build_fail_closed_result(
                p_id=p_id, p_name=p_name, source_grid=source_grid, valid_time=target_valid_time,
                status="EMPTY_SOURCE_GRID", message="Source weather grid contains zero cells.",
                process_ts=process_ts, panchayat_area_sq_km=panchayat_area_sq_km
            )

        if source_grid.provenance.crs and "4326" not in source_grid.provenance.crs:
            return self._build_fail_closed_result(
                p_id=p_id, p_name=p_name, source_grid=source_grid, valid_time=target_valid_time,
                status="INVALID_CRS", message=f"Unsupported CRS '{source_grid.provenance.crs}'. Internal pipeline requires EPSG:4326.",
                process_ts=process_ts, panchayat_area_sq_km=panchayat_area_sq_km
            )

        # ---------------------------------------------------------------------
        # 3. Geometric Intersection & Fractional Overlap Calculation
        # ---------------------------------------------------------------------
        poly_minx, poly_miny, poly_maxx, poly_maxy = poly.bounds
        poly_bbox = box(poly_minx, poly_miny, poly_maxx, poly_maxy)

        cell_intersections: List[CellIntersectionResult] = []
        valid_cell_values: List[float] = []
        valid_cell_weights: List[float] = []
        all_intersecting_areas: List[float] = []
        total_cells_considered = 0

        for cell in source_grid.cells:
            total_cells_considered += 1
            try:
                cell_geom = shape(cell.geometry)
            except Exception:
                continue

            # Bounding box candidate optimization
            cell_minx, cell_miny, cell_maxx, cell_maxy = cell_geom.bounds
            if not (
                poly_minx <= cell_maxx and poly_maxx >= cell_minx and
                poly_miny <= cell_maxy and poly_maxy >= cell_miny
            ):
                continue

            # Exact geometric intersection
            intersection = poly.intersection(cell_geom)
            if intersection.is_empty:
                continue

            inter_area_sq_km = self._calculate_geodesic_area_sq_km(intersection)
            if inter_area_sq_km <= 1e-9:
                continue

            cell_area_sq_km = cell.area_sq_km or self._calculate_geodesic_area_sq_km(cell_geom)
            cell_area_sq_km = max(1e-9, cell_area_sq_km)

            overlap_frac_cell = min(1.0, max(0.0, inter_area_sq_km / cell_area_sq_km))
            overlap_frac_panchayat = min(1.0, max(0.0, inter_area_sq_km / max(1e-6, panchayat_area_sq_km)))

            raw_val = cell.value
            is_valid = raw_val is not None and np.isfinite(raw_val)

            inter_res = CellIntersectionResult(
                cell_id=cell.cell_id,
                source_value=float(raw_val) if is_valid else None,
                cell_area_sq_km=round(cell_area_sq_km, 6),
                intersection_area_sq_km=round(inter_area_sq_km, 6),
                overlap_fraction_of_cell=round(overlap_frac_cell, 4),
                overlap_fraction_of_panchayat=round(overlap_frac_panchayat, 4),
                is_valid_value=is_valid,
            )
            cell_intersections.append(inter_res)
            all_intersecting_areas.append(inter_area_sq_km)

            if is_valid:
                valid_cell_values.append(float(raw_val))
                valid_cell_weights.append(inter_area_sq_km)

        # ---------------------------------------------------------------------
        # 4. Evaluate Coverage & Quality
        # ---------------------------------------------------------------------
        cells_intersecting = len(cell_intersections)
        valid_cells_intersecting = len(valid_cell_values)
        total_inter_area = sum(all_intersecting_areas)
        valid_inter_area = sum(valid_cell_weights)

        coverage_frac = min(1.0, total_inter_area / max(1e-6, panchayat_area_sq_km))
        valid_coverage_frac = min(1.0, valid_inter_area / max(1e-6, panchayat_area_sq_km))

        if cells_intersecting == 0:
            return self._build_fail_closed_result(
                p_id=p_id, p_name=p_name, source_grid=source_grid, valid_time=target_valid_time,
                status="NO_INTERSECTING_CELLS",
                message="Zero source grid cells intersect the Panchayat polygon.",
                process_ts=process_ts, panchayat_area_sq_km=panchayat_area_sq_km
            )

        if valid_cells_intersecting == 0:
            return self._build_fail_closed_result(
                p_id=p_id, p_name=p_name, source_grid=source_grid, valid_time=target_valid_time,
                status="ALL_VALUES_MISSING",
                message=f"All {cells_intersecting} intersecting source grid cells contain missing (NaN) values.",
                process_ts=process_ts, panchayat_area_sq_km=panchayat_area_sq_km,
                cells_considered=total_cells_considered, cells_intersecting=cells_intersecting,
                inter_area_sq_km=total_inter_area, coverage_fraction=coverage_frac
            )

        # Quality tier assignment
        if valid_coverage_frac >= 0.95:
            quality = CoverageQuality.COMPLETE
        elif valid_coverage_frac >= 0.80:
            quality = CoverageQuality.HIGH
        elif valid_coverage_frac >= 0.50:
            quality = CoverageQuality.MODERATE
        elif valid_coverage_frac >= 0.20:
            quality = CoverageQuality.PARTIAL
        else:
            quality = CoverageQuality.INSUFFICIENT

        # ---------------------------------------------------------------------
        # 5. Variable-Specific Feature Computation
        # ---------------------------------------------------------------------
        vtype = source_grid.variable_type
        features_dict: Dict[str, Any] = {}

        if vtype in (
            VariableType.PRECIPITATION_ACCUMULATION,
            VariableType.PRECIPITATION_INTENSITY,
        ):
            features_dict = self._compute_precipitation_features(
                values=valid_cell_values,
                weights=valid_cell_weights,
                total_valid_weight=valid_inter_area,
                detection_threshold_mm=detection_threshold_mm,
                is_intensity=(vtype == VariableType.PRECIPITATION_INTENSITY),
            )
        else:
            # Continuous default (Temperature, Humidity, etc.)
            features_dict = self._compute_continuous_features(
                values=valid_cell_values,
                weights=valid_cell_weights,
                total_valid_weight=valid_inter_area,
            )

        # ---------------------------------------------------------------------
        # 6. Build Deterministic Output Result
        # ---------------------------------------------------------------------
        prov = SourceResolutionProvenance(
            source_name=source_grid.provenance.source_name,
            source_product=source_grid.provenance.source_product,
            native_resolution_km=source_grid.provenance.native_resolution_km,
            processing_resolution_km=source_grid.provenance.processing_resolution_km,
            visualization_resolution_km=source_grid.provenance.visualization_resolution_km,
            crs=source_grid.provenance.crs,
            spatial_extent=source_grid.provenance.spatial_extent,
            valid_time=target_valid_time,
            processing_timestamp=process_ts,
            source_version=source_grid.provenance.source_version,
            resolution_disclaimer=source_grid.provenance.resolution_disclaimer,
        )

        return PanchayatSpatialExtractionResult(
            panchayat_id=p_id,
            panchayat_name=p_name,
            variable_name=source_grid.variable_name,
            variable_unit=source_grid.variable_unit,
            variable_type=source_grid.variable_type,
            source_name=source_grid.provenance.source_name,
            valid_time=target_valid_time,
            native_resolution_km=source_grid.provenance.native_resolution_km,
            cells_considered=total_cells_considered,
            cells_intersecting=cells_intersecting,
            valid_cells_intersecting=valid_cells_intersecting,
            panchayat_area_sq_km=round(panchayat_area_sq_km, 4),
            intersecting_area_sq_km=round(total_inter_area, 4),
            coverage_fraction=round(coverage_frac, 4),
            valid_coverage_fraction=round(valid_coverage_frac, 4),
            coverage_quality=quality,
            features=features_dict,
            cell_intersections=cell_intersections if include_cell_details else None,
            provenance=prov,
            status="SUCCESS",
            message=f"Extracted {valid_cells_intersecting} valid intersecting cells covering {coverage_frac * 100:.1f}% of Panchayat.",
            success=True,
        )

    def _compute_continuous_features(
        self,
        values: List[float],
        weights: List[float],
        total_valid_weight: float,
    ) -> Dict[str, Any]:
        """Calculates area-weighted and descriptive statistics for continuous fields."""
        val_arr = np.array(values, dtype=float)
        wt_arr = np.array(weights, dtype=float)

        weighted_mean = float(np.sum(val_arr * wt_arr) / total_valid_weight) if total_valid_weight > 0 else float(np.mean(val_arr))
        unweighted_mean = float(np.mean(val_arr))
        min_val = float(np.min(val_arr))
        max_val = float(np.max(val_arr))
        std_val = float(np.std(val_arr, ddof=1)) if len(val_arr) > 1 else 0.0
        median_val = float(np.median(val_arr))
        p10_val = float(np.percentile(val_arr, 10))
        p90_val = float(np.percentile(val_arr, 90))

        feat = ContinuousVariableFeatures(
            weighted_mean=round(weighted_mean, 4),
            mean=round(unweighted_mean, 4),
            min=round(min_val, 4),
            max=round(max_val, 4),
            std=round(std_val, 4),
            median=round(median_val, 4),
            p10=round(p10_val, 4),
            p90=round(p90_val, 4),
        )
        return feat.model_dump()

    def _compute_precipitation_features(
        self,
        values: List[float],
        weights: List[float],
        total_valid_weight: float,
        detection_threshold_mm: float,
        is_intensity: bool,
    ) -> Dict[str, Any]:
        """Calculates area-weighted precipitation metrics preserving semantic distinctions."""
        val_arr = np.array(values, dtype=float)
        wt_arr = np.array(weights, dtype=float)

        weighted_mean = float(np.sum(val_arr * wt_arr) / total_valid_weight) if total_valid_weight > 0 else float(np.mean(val_arr))
        unweighted_mean = float(np.mean(val_arr))
        max_val = float(np.max(val_arr))
        min_val = float(np.min(val_arr))

        # Rain area fraction: fraction of valid area where precipitation >= detection_threshold
        rainy_mask = val_arr >= detection_threshold_mm
        rainy_weight = float(np.sum(wt_arr[rainy_mask])) if np.any(rainy_mask) else 0.0
        rain_area_fraction = min(1.0, max(0.0, rainy_weight / total_valid_weight)) if total_valid_weight > 0 else 0.0
        is_detected = bool(np.any(rainy_mask))

        feat = PrecipitationVariableFeatures(
            weighted_mean_amount_mm=round(weighted_mean, 4),
            max_amount_mm=round(max_val, 4),
            min_amount_mm=round(min_val, 4),
            intensity_mm_per_hr=round(weighted_mean, 4) if is_intensity else None,
            accumulated_precipitation_mm=round(weighted_mean, 4) if not is_intensity else None,
            rain_area_fraction=round(rain_area_fraction, 4),
            is_rain_detected=is_detected,
            detection_threshold_mm=detection_threshold_mm,
            unweighted_mean_amount_mm=round(unweighted_mean, 4),
        )
        return feat.model_dump()

    def _build_fail_closed_result(
        self,
        p_id: str,
        p_name: Optional[str],
        source_grid: SourceWeatherGrid,
        valid_time: str,
        status: str,
        message: str,
        process_ts: str,
        panchayat_area_sq_km: float = 0.0,
        cells_considered: int = 0,
        cells_intersecting: int = 0,
        inter_area_sq_km: float = 0.0,
        coverage_fraction: float = 0.0,
    ) -> PanchayatSpatialExtractionResult:
        """Constructs a deterministic fail-closed result payload."""
        prov = SourceResolutionProvenance(
            source_name=source_grid.provenance.source_name,
            source_product=source_grid.provenance.source_product,
            native_resolution_km=source_grid.provenance.native_resolution_km,
            processing_resolution_km=source_grid.provenance.processing_resolution_km,
            visualization_resolution_km=source_grid.provenance.visualization_resolution_km,
            crs=source_grid.provenance.crs,
            spatial_extent=source_grid.provenance.spatial_extent,
            valid_time=valid_time,
            processing_timestamp=process_ts,
            source_version=source_grid.provenance.source_version,
            resolution_disclaimer=source_grid.provenance.resolution_disclaimer,
        )

        return PanchayatSpatialExtractionResult(
            panchayat_id=p_id,
            panchayat_name=p_name,
            variable_name=source_grid.variable_name,
            variable_unit=source_grid.variable_unit,
            variable_type=source_grid.variable_type,
            source_name=source_grid.provenance.source_name,
            valid_time=valid_time,
            native_resolution_km=source_grid.provenance.native_resolution_km,
            cells_considered=cells_considered,
            cells_intersecting=cells_intersecting,
            valid_cells_intersecting=0,
            panchayat_area_sq_km=round(panchayat_area_sq_km, 4),
            intersecting_area_sq_km=round(inter_area_sq_km, 4),
            coverage_fraction=round(coverage_fraction, 4),
            valid_coverage_fraction=0.0,
            coverage_quality=CoverageQuality.ZERO_COVERAGE if cells_intersecting == 0 else CoverageQuality.INSUFFICIENT,
            features={},
            cell_intersections=None,
            provenance=prov,
            status=status,
            message=message,
            success=False,
        )


# Global singleton service instance
spatial_masking_service = SpatialMaskingService()


def extract_panchayat_spatial_features(
    panchayat_id: Optional[str] = None,
    panchayat_geometry: Optional[Union[Polygon, MultiPolygon, Dict[str, Any]]] = None,
    source_grid: SourceWeatherGrid = ...,
    valid_time: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
    require_verified: bool = False,
    include_cell_details: bool = True,
    detection_threshold_mm: float = 0.1,
) -> PanchayatSpatialExtractionResult:
    """
    Standard programmatic interface for spatial feature extraction.
    Usable as an upstream primitive for weather observation and satellite/radar fusion.
    """
    return spatial_masking_service.extract_panchayat_spatial_features(
        panchayat_id=panchayat_id,
        panchayat_geometry=panchayat_geometry,
        source_grid=source_grid,
        valid_time=valid_time,
        source_metadata=source_metadata,
        require_verified=require_verified,
        include_cell_details=include_cell_details,
        detection_threshold_mm=detection_threshold_mm,
    )
