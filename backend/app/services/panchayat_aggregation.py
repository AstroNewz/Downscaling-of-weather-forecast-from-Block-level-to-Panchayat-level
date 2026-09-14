"""
Panchayat Weather Spatial Aggregation Service
SIH Problem Statement 26074 (Weather Downscaling)

Aggregates Phase 7 1-km downscaled temperature fields into administrative Gram Panchayat
boundaries using area-weighted spatial polygon intersection in metric projected coordinate systems.
"""
import uuid
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from shapely import wkt, wkb
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import transform as shapely_transform
import pyproj

from app.core.config import settings
from app.core.logging import logger
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import PanchayatWeather
from app.services.spatial_inference import SpatialTemperatureInferenceService
from app.gis.grid import SpatialGridGenerator
from app.gis.spatial_features import SpatialFeatureExtractor
from app.ml.schemas import FEATURE_SCHEMA_VERSION
from app.schemas.panchayat_weather import (
    PanchayatWeatherSummary,
    PanchayatWeatherAggregateRequest,
    PanchayatWeatherAggregateResponse,
)


class PanchayatWeatherAggregationService:
    """
    Spatial aggregation engine converting high-resolution 1-km grid fields into
    Gram Panchayat-level weather statistics and quality diagnostics.
    """

    # Coverage classification thresholds
    COMPLETE_COVERAGE_THRESHOLD_PCT: float = 95.0
    PARTIAL_COVERAGE_MIN_PCT: float = 1.0

    def __init__(self, db: Session):
        self.db = db
        self.spatial_inference_service = SpatialTemperatureInferenceService(db=db)

    @staticmethod
    def _parse_geometry(raw_geom: Any) -> Optional[Union[Polygon, MultiPolygon]]:
        """Parses WKBElement, WKTElement, string, or dict into a Shapely geometry."""
        if raw_geom is None:
            return None
        if hasattr(raw_geom, "data"):
            return wkb.loads(bytes(raw_geom.data))
        if hasattr(raw_geom, "desc"):
            return wkt.loads(str(raw_geom.desc))
        if isinstance(raw_geom, str):
            clean = raw_geom.split(";", 1)[1] if "SRID=" in raw_geom and ";" in raw_geom else raw_geom
            return wkt.loads(clean)
        if isinstance(raw_geom, dict):
            return shape(raw_geom)
        if isinstance(raw_geom, (Polygon, MultiPolygon)):
            return raw_geom
        return None

    def aggregate_block_panchayats(
        self,
        block_id: int,
        forecast_valid_time: datetime,
        forecast_issue_time: Optional[datetime] = None,
        source_model: Optional[str] = "IMD-GFS",
        model_version: Optional[str] = None,
        grid_resolution_km: float = 1.0,
        panchayat_id: Optional[int] = None,
        persist_to_db: bool = True
    ) -> PanchayatWeatherAggregateResponse:
        """
        Executes area-weighted spatial aggregation for all (or single) Panchayats in a Block.
        """
        aggregation_id = str(uuid.uuid4())
        target_model_version = model_version or settings.TEMPERATURE_MODEL_VERSION

        logger.info(
            f"Starting Phase 8 Panchayat weather aggregation [ID: {aggregation_id}] "
            f"for Block ID {block_id} at valid time {forecast_valid_time.isoformat()}..."
        )

        # 1. Retrieve Block and Child Panchayats
        block = self.db.scalar(select(Block).where(Block.id == block_id))
        if not block:
            raise ValueError(f"Block with ID {block_id} not found in database.")

        panchayat_stmt = select(Panchayat).where(Panchayat.block_id == block_id)
        if panchayat_id is not None:
            panchayat_stmt = panchayat_stmt.where(Panchayat.id == panchayat_id)

        panchayats = self.db.scalars(panchayat_stmt).all()
        if not panchayats:
            raise ValueError(f"No Panchayats found for Block '{block.name}' (ID: {block_id}).")

        # 2. Retrieve / Generate Phase 7 1-km Downscaled Weather Grid
        grid_response = self.spatial_inference_service.run_spatial_downscaling(
            block_id=block_id,
            forecast_valid_time=forecast_valid_time,
            forecast_issue_time=forecast_issue_time,
            source_model=source_model,
            model_version=target_model_version,
            grid_resolution_km=grid_resolution_km,
            persist_to_db=persist_to_db,
            export_geoparquet=False,
            include_cell_payload=True
        )

        grid_cells = grid_response.grid_cells or []
        projected_crs_str = grid_response.projected_crs
        has_valid_grid = grid_response.quality_summary.successful_predictions > 0

        # 3. Setup Coordinate Reference System Transformers
        to_projected = pyproj.Transformer.from_crs("EPSG:4326", projected_crs_str, always_xy=True).transform

        # 4. Convert 1-km Grid Cells to Projected Geometries
        projected_cells = []
        for cell in grid_cells:
            cell_poly_wgs84 = shape(cell.geometry_geojson) if cell.geometry_geojson else Point(cell.longitude, cell.latitude).buffer(0.005)
            cell_poly_proj = shapely_transform(to_projected, cell_poly_wgs84)
            projected_cells.append({
                "cell": cell,
                "poly_proj": cell_poly_proj,
                "area_sqm": cell_poly_proj.area,
            })

        # 5. Execute Spatial Intersection and Area-Weighted Aggregation for Each Panchayat
        panchayat_summaries: List[PanchayatWeatherSummary] = []
        complete_count = 0
        partial_count = 0
        unavailable_count = 0
        total_covered_area_sum = 0.0
        total_panchayat_area_sum = 0.0

        for p in panchayats:
            p_geom_wgs84 = self._parse_geometry(p.geometry)
            p_flags: List[str] = []

            # Centroid buffer fallback if polygon boundary is missing
            if p_geom_wgs84 is None or p_geom_wgs84.is_empty:
                c_lat, c_lon = SpatialFeatureExtractor.extract_centroid_coordinates(p.centroid)
                if c_lat is not None and c_lon is not None:
                    p_geom_wgs84 = Point(c_lon, c_lat).buffer(0.015)  # ~1.5km radius buffer
                    p_flags.append("CENTROID_BUFFER_FALLBACK")
                else:
                    p_geom_wgs84 = Point(75.0, 22.0).buffer(0.01)
                    p_flags.append("DEFAULT_LOCATION_FALLBACK")

            # Project Panchayat geometry to metric CRS
            p_geom_proj = shapely_transform(to_projected, p_geom_wgs84)
            p_area_sqm = p_geom_proj.area
            p_area_sqkm = max(0.01, p_area_sqm / 1_000_000.0)
            total_panchayat_area_sum += p_area_sqkm

            # If grid has no valid predictions
            if not has_valid_grid or len(projected_cells) == 0:
                summary = PanchayatWeatherSummary(
                    panchayat_id=p.id,
                    panchayat_name=p.name,
                    lgd_code=p.lgd_code,
                    block_id=block.id,
                    block_name=block.name,
                    forecast_valid_time=forecast_valid_time.isoformat(),
                    forecast_issue_time=grid_response.forecast_issue_time,
                    source_model=grid_response.source_model,
                    model_version=target_model_version,
                    grid_resolution_km=grid_resolution_km,
                    mean_temperature_c=0.0,
                    min_temperature_c=0.0,
                    max_temperature_c=0.0,
                    total_panchayat_area_sqkm=round(p_area_sqkm, 2),
                    covered_area_sqkm=0.0,
                    coverage_percentage=0.0,
                    contributing_grid_cells=0,
                    valid_grid_cells=0,
                    quality_status="UNAVAILABLE",
                    quality_flags=["NO_VALID_GRID_CELLS"],
                    aggregation_method="AREA_WEIGHTED",
                    aggregation_crs=projected_crs_str
                )
                panchayat_summaries.append(summary)
                unavailable_count += 1
                continue

            # Find all intersecting grid cells and calculate area weights
            contributing_cells_count = 0
            valid_temps: List[float] = []
            valid_residuals: List[float] = []
            valid_weights: List[float] = []
            valid_covered_area_sqm = 0.0

            for cell_info in projected_cells:
                cell_poly = cell_info["poly_proj"]
                cell_record = cell_info["cell"]

                if p_geom_proj.intersects(cell_poly):
                    contributing_cells_count += 1
                    intersection = p_geom_proj.intersection(cell_poly)
                    intersect_area_sqm = intersection.area

                    if intersect_area_sqm > 1.0:  # Minimum 1 m² intersection threshold
                        if cell_record.downscaled_temperature_c is not None and cell_record.quality_flag != "UNAVAILABLE":
                            weight = intersect_area_sqm / p_area_sqm
                            valid_weights.append(weight)
                            valid_temps.append(cell_record.downscaled_temperature_c)
                            if cell_record.predicted_residual_c is not None:
                                valid_residuals.append(cell_record.predicted_residual_c)
                            valid_covered_area_sqm += intersect_area_sqm

                            if "CLAMPED" in cell_record.quality_flag:
                                if "RESIDUAL_CLAMPED" not in p_flags:
                                    p_flags.append("RESIDUAL_CLAMPED")

            valid_count = len(valid_temps)
            covered_area_sqkm = valid_covered_area_sqm / 1_000_000.0
            total_covered_area_sum += covered_area_sqkm

            coverage_pct = min(100.0, max(0.0, (valid_covered_area_sqm / p_area_sqm) * 100.0))

            if valid_count > 0 and sum(valid_weights) > 1e-9:
                sum_w = sum(valid_weights)
                norm_weights = [w / sum_w for w in valid_weights]

                # Weighted Mean Temperature: T_mean = sum(w_i * T_i) / sum(w_i)
                weighted_mean_t = float(sum(w * t for w, t in zip(norm_weights, valid_temps)))
                min_t = float(min(valid_temps))
                max_t = float(max(valid_temps))
                median_t = float(np.median(valid_temps))
                p10_t = float(np.percentile(valid_temps, 10))
                p90_t = float(np.percentile(valid_temps, 90))

                # Weighted Variance and Standard Deviation
                weighted_var = float(sum(w * ((t - weighted_mean_t) ** 2) for w, t in zip(norm_weights, valid_temps)))
                std_t = float(math.sqrt(max(0.0, weighted_var)))

                # Weighted Mean Residual
                mean_res = float(sum(w * r for w, r in zip(norm_weights, valid_residuals))) if valid_residuals else None

                # Quality Status Classification
                if coverage_pct >= self.COMPLETE_COVERAGE_THRESHOLD_PCT:
                    q_status = "COMPLETE"
                    complete_count += 1
                elif coverage_pct >= self.PARTIAL_COVERAGE_MIN_PCT:
                    q_status = "PARTIAL"
                    p_flags.append("PARTIAL_COVERAGE")
                    partial_count += 1
                else:
                    q_status = "UNAVAILABLE"
                    p_flags.append("INSUFFICIENT_COVERAGE")
                    unavailable_count += 1

                if std_t > 3.0:
                    p_flags.append("HIGH_SPATIAL_VARIABILITY")

                summary = PanchayatWeatherSummary(
                    panchayat_id=p.id,
                    panchayat_name=p.name,
                    lgd_code=p.lgd_code,
                    block_id=block.id,
                    block_name=block.name,
                    forecast_valid_time=forecast_valid_time.isoformat(),
                    forecast_issue_time=grid_response.forecast_issue_time,
                    source_model=grid_response.source_model,
                    model_version=target_model_version,
                    grid_resolution_km=grid_resolution_km,
                    mean_temperature_c=round(weighted_mean_t, 2),
                    min_temperature_c=round(min_t, 2),
                    max_temperature_c=round(max_t, 2),
                    median_temperature_c=round(median_t, 2),
                    temperature_stddev_c=round(std_t, 3),
                    temperature_p10_c=round(p10_t, 2),
                    temperature_p90_c=round(p90_t, 2),
                    mean_residual_c=round(mean_res, 3) if mean_res is not None else None,
                    total_panchayat_area_sqkm=round(p_area_sqkm, 2),
                    covered_area_sqkm=round(covered_area_sqkm, 2),
                    coverage_percentage=round(coverage_pct, 2),
                    contributing_grid_cells=contributing_cells_count,
                    valid_grid_cells=valid_count,
                    quality_status=q_status,
                    quality_flags=p_flags,
                    aggregation_method="AREA_WEIGHTED",
                    aggregation_crs=projected_crs_str,
                    cropland_weighted_mean_temp_c=round(weighted_mean_t, 2)  # Base cropland estimate
                )
            else:
                summary = PanchayatWeatherSummary(
                    panchayat_id=p.id,
                    panchayat_name=p.name,
                    lgd_code=p.lgd_code,
                    block_id=block.id,
                    block_name=block.name,
                    forecast_valid_time=forecast_valid_time.isoformat(),
                    forecast_issue_time=grid_response.forecast_issue_time,
                    source_model=grid_response.source_model,
                    model_version=target_model_version,
                    grid_resolution_km=grid_resolution_km,
                    mean_temperature_c=0.0,
                    min_temperature_c=0.0,
                    max_temperature_c=0.0,
                    total_panchayat_area_sqkm=round(p_area_sqkm, 2),
                    covered_area_sqkm=0.0,
                    coverage_percentage=0.0,
                    contributing_grid_cells=contributing_cells_count,
                    valid_grid_cells=0,
                    quality_status="UNAVAILABLE",
                    quality_flags=["NO_INTERSECTING_VALID_CELLS"],
                    aggregation_method="AREA_WEIGHTED",
                    aggregation_crs=projected_crs_str
                )
                unavailable_count += 1

            panchayat_summaries.append(summary)

            # 6. Database Upsert / Persistence (PanchayatWeather)
            if persist_to_db and summary.valid_grid_cells > 0:
                existing_record = self.db.scalar(
                    select(PanchayatWeather).where(
                        PanchayatWeather.panchayat_id == p.id,
                        PanchayatWeather.forecast_date == forecast_valid_time,
                        PanchayatWeather.source_model == grid_response.source_model,
                        PanchayatWeather.model_version == target_model_version
                    )
                )
                if existing_record:
                    # Update existing record
                    existing_record.mean_temp_c = summary.mean_temperature_c
                    existing_record.min_temp_c = summary.min_temperature_c
                    existing_record.max_temp_c = summary.max_temperature_c
                    existing_record.median_temp_c = summary.median_temperature_c
                    existing_record.temp_stddev_c = summary.temperature_stddev_c
                    existing_record.temp_p10_c = summary.temperature_p10_c
                    existing_record.temp_p90_c = summary.temperature_p90_c
                    existing_record.mean_residual_c = summary.mean_residual_c
                    existing_record.total_panchayat_area_sqkm = summary.total_panchayat_area_sqkm
                    existing_record.covered_area_sqkm = summary.covered_area_sqkm
                    existing_record.coverage_pct = summary.coverage_percentage
                    existing_record.contributing_grid_cells = summary.contributing_grid_cells
                    existing_record.valid_grid_cells = summary.valid_grid_cells
                    existing_record.quality_status = summary.quality_status
                    existing_record.quality_flags = summary.quality_flags
                    existing_record.aggregation_crs = summary.aggregation_crs
                    existing_record.cropland_weighted_mean_temp_c = summary.cropland_weighted_mean_temp_c
                else:
                    # Create new record
                    issue_dt = datetime.fromisoformat(grid_response.forecast_issue_time)
                    db_record = PanchayatWeather(
                        panchayat_id=p.id,
                        block_id=block.id,
                        forecast_date=forecast_valid_time,
                        issue_time=issue_dt,
                        source_model=grid_response.source_model,
                        model_version=target_model_version,
                        feature_schema_version=FEATURE_SCHEMA_VERSION,
                        grid_resolution_km=grid_resolution_km,
                        mean_temp_c=summary.mean_temperature_c,
                        min_temp_c=summary.min_temperature_c,
                        max_temp_c=summary.max_temperature_c,
                        median_temp_c=summary.median_temperature_c,
                        temp_stddev_c=summary.temperature_stddev_c,
                        temp_p10_c=summary.temperature_p10_c,
                        temp_p90_c=summary.temperature_p90_c,
                        mean_residual_c=summary.mean_residual_c,
                        total_panchayat_area_sqkm=summary.total_panchayat_area_sqkm,
                        covered_area_sqkm=summary.covered_area_sqkm,
                        coverage_pct=summary.coverage_percentage,
                        contributing_grid_cells=summary.contributing_grid_cells,
                        valid_grid_cells=summary.valid_grid_cells,
                        quality_status=summary.quality_status,
                        quality_flags=summary.quality_flags,
                        aggregation_method=summary.aggregation_method,
                        aggregation_crs=summary.aggregation_crs,
                        cropland_weighted_mean_temp_c=summary.cropland_weighted_mean_temp_c,
                        aggregation_metadata={
                            "aggregation_id": aggregation_id,
                            "block_name": block.name,
                            "panchayat_name": p.name,
                        }
                    )
                    self.db.add(db_record)

        if persist_to_db:
            self.db.commit()
            logger.info(f"Persisted {len(panchayat_summaries)} Panchayat weather records to database.")

        overall_block_cov = (
            (total_covered_area_sum / total_panchayat_area_sum * 100.0)
            if total_panchayat_area_sum > 0 else 0.0
        )

        return PanchayatWeatherAggregateResponse(
            aggregation_id=aggregation_id,
            block_id=block.id,
            block_name=block.name,
            district_name=block.district_name,
            state_name=block.state_name,
            forecast_valid_time=forecast_valid_time.isoformat(),
            forecast_issue_time=grid_response.forecast_issue_time,
            source_model=grid_response.source_model,
            model_version=target_model_version,
            grid_resolution_km=grid_resolution_km,
            total_panchayats_in_block=len(panchayats),
            aggregated_panchayats_count=len(panchayat_summaries),
            complete_coverage_count=complete_count,
            partial_coverage_count=partial_count,
            unavailable_count=unavailable_count,
            overall_block_coverage_pct=round(overall_block_cov, 2),
            panchayat_weather=panchayat_summaries,
            aggregation_timestamp=datetime.utcnow().isoformat()
        )
