"""
Tests for Phase 7: 1-km Spatial Weather Downscaling & Inference Engine
SIH Problem Statement 26074 (Weather Downscaling)
"""
import os
import pytest
from datetime import datetime
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely import wkt
import geopandas as gpd
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, DownscaledWeatherGrid
from app.gis.grid import SpatialGridGenerator, GridCellRecord, SpatialGridDomainResult
from app.ml.feature_manifest import ALL_PREDICTOR_FEATURES
from app.ml.trainer import DownscalingModelTrainer
from app.ml.registry import LocalModelRegistry
from app.services.spatial_inference import SpatialTemperatureInferenceService
from tests.test_ml_training import generate_synthetic_feature_df


def create_sample_block_polygon(lon_center: float = 75.0, lat_center: float = 22.0, size_deg: float = 0.05) -> Polygon:
    """Creates a sample square polygon in WGS84 coordinates (~5km x 5km)."""
    half = size_deg / 2.0
    return Polygon([
        (lon_center - half, lat_center - half),
        (lon_center + half, lat_center - half),
        (lon_center + half, lat_center + half),
        (lon_center - half, lat_center + half),
        (lon_center - half, lat_center - half)
    ])


@pytest.fixture
def spatial_test_environment(tmp_path, monkeypatch, db_session: Session):
    """
    Sets up a temporary test environment:
    - Custom model registry with trained v1.0.0-spatial model
    - Block entity in database with valid geometry
    - BlockWeatherForecast in database
    """
    registry_dir = str(tmp_path / "models_spatial")
    grid_out_dir = str(tmp_path / "grids_out")
    monkeypatch.setattr(settings, "ML_MODEL_DIR", registry_dir)
    monkeypatch.setattr(settings, "TEMPERATURE_MODEL_VERSION", "v1.0.0-spatial")
    monkeypatch.setattr(settings, "DATASET_OUTPUT_DIR", str(tmp_path / "processed"))

    registry = LocalModelRegistry(base_dir=registry_dir)
    trainer = DownscalingModelTrainer(registry=registry)

    # Train test model artifact
    df = generate_synthetic_feature_df(100)
    trainer.train_from_dataframe(
        df=df,
        model_version="v1.0.0-spatial",
        allow_synthetic=True,
        is_synthetic=True
    )

    # Insert test Block into database
    poly = create_sample_block_polygon(lon_center=75.5, lat_center=22.5, size_deg=0.04)
    block = Block(
        lgd_code="BLK_TEST_007",
        name="Test Downscale Block",
        district_name="Agri District",
        state_name="Agri State",
        geometry=f"SRID=4326;{poly.wkt}",
        centroid=f"SRID=4326;POINT(75.5 22.5)"
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    # Insert BlockWeatherForecast into database
    valid_time = datetime(2026, 1, 15, 12, 0, 0)
    issue_time = datetime(2026, 1, 15, 0, 0, 0)
    forecast = BlockWeatherForecast(
        block_id=block.id,
        forecast_date=valid_time,
        issue_time=issue_time,
        temp_min=22.0,
        temp_max=32.0,
        rainfall_mm=2.5,
        relative_humidity_pct=55.0,
        wind_speed_mps=3.2,
        wind_direction_deg=190.0,
        cloud_cover_pct=25.0,
        source_model="IMD-GFS",
        quality_flag="VALID"
    )
    db_session.add(forecast)
    db_session.commit()

    return {
        "registry": registry,
        "block": block,
        "forecast": forecast,
        "valid_time": valid_time,
        "issue_time": issue_time,
    }


def test_utm_crs_selection():
    """Verifies that optimal UTM EPSG codes are calculated accurately across longitudes."""
    # 75°E in Northern Hemisphere -> UTM Zone 43N (EPSG:32643)
    epsg_india = SpatialGridGenerator.get_optimal_utm_epsg(lon=75.0, lat=22.0)
    assert epsg_india == 32643

    # 85°E in Northern Hemisphere -> UTM Zone 45N (EPSG:32645)
    epsg_east = SpatialGridGenerator.get_optimal_utm_epsg(lon=85.0, lat=26.0)
    assert epsg_east == 32645

    # 75°W in Northern Hemisphere -> UTM Zone 18N (EPSG:32618)
    epsg_us = SpatialGridGenerator.get_optimal_utm_epsg(lon=-75.0, lat=40.0)
    assert epsg_us == 32618


def test_1km_grid_generation_and_actual_dimensions():
    """
    CRITICAL STEP 21: Verifies actual 1-km (1000m x 1000m) projected cell dimensions
    and geometry validity.
    """
    poly = create_sample_block_polygon(lon_center=75.0, lat_center=22.0, size_deg=0.04)
    result = SpatialGridGenerator.generate_grid_for_polygon(
        polygon_geom=poly,
        resolution_km=1.0,
        boundary_rule="center_inside_block",
        block_id=101
    )

    assert result.total_cells > 0
    assert result.requested_resolution_m == 1000.0
    assert np.isclose(result.actual_resolution_m, 1000.0, atol=1e-3)
    assert result.projected_crs == "EPSG:32643"
    assert result.boundary_rule == "center_inside_block"

    # Verify all generated cell geometries
    grid_ids = set()
    for cell in result.cells:
        assert cell.grid_id.startswith("grid_b101_")
        assert cell.grid_id not in grid_ids, "Duplicate grid_id detected!"
        grid_ids.add(cell.grid_id)

        assert cell.resolution_m == 1000.0
        assert -90.0 <= cell.center_latitude <= 90.0
        assert -180.0 <= cell.center_longitude <= 180.0

        # Validate polygon geometry in WGS84
        geom = wkt.loads(cell.geometry_wkt)
        assert geom.is_valid is True
        assert isinstance(geom, Polygon)
        assert len(geom.exterior.coords) == 5  # Closed ring of square


def test_grid_generation_fallback_for_tiny_block():
    """Verifies that narrow or sub-kilometer blocks generate a representative centroid cell."""
    # Extremely small block polygon (0.001 deg ~ 100m)
    tiny_poly = Polygon([(75.0, 22.0), (75.001, 22.0), (75.001, 22.001), (75.0, 22.001), (75.0, 22.0)])
    result = SpatialGridGenerator.generate_grid_for_polygon(
        polygon_geom=tiny_poly,
        resolution_km=1.0,
        block_id=999
    )
    assert result.total_cells >= 1
    assert result.cells[0].grid_id == "grid_b999_000_000"


def test_spatial_downscaling_service_end_to_end(spatial_test_environment, db_session: Session):
    """
    Verifies end-to-end 1-km spatial downscaling:
    Block geometry -> 1-km grid -> Coarse forecast matching -> DEM/LULC features ->
    XGBoost batch inference -> Fine temperature calculation -> Persistence & GeoParquet export.
    """
    env = spatial_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = SpatialTemperatureInferenceService(
        db=db_session,
        registry=env["registry"]
    )

    response = service.run_spatial_downscaling(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-spatial",
        grid_resolution_km=1.0,
        persist_to_db=True,
        export_geoparquet=True,
        include_cell_payload=True
    )

    # 1. Verify Top-level Response Metadata
    assert response.block_id == block.id
    assert response.block_name == block.name
    assert response.model_version == "v1.0.0-spatial"
    assert response.feature_schema_version == "v1.1.0"
    assert response.grid_resolution_km == 1.0
    assert np.isclose(response.actual_resolution_m, 1000.0)

    # 2. Verify Spatial Quality Summary
    summary = response.quality_summary
    assert summary.total_grid_cells > 0
    assert summary.successful_predictions == summary.total_grid_cells
    assert summary.unavailable_predictions == 0
    assert summary.spatial_coverage_pct == 100.0
    assert summary.diagnostics_passed is True

    # 3. Verify Temperature Statistics
    assert summary.min_temperature_c is not None
    assert summary.max_temperature_c is not None
    assert summary.mean_temperature_c is not None
    assert summary.min_temperature_c <= summary.mean_temperature_c <= summary.max_temperature_c

    # 4. Verify Grid Cells Math: T_downscaled = T_coarse + residual
    assert response.grid_cells is not None
    for cell in response.grid_cells:
        assert cell.coarse_temperature_c == 27.0  # (22 + 32) / 2
        assert cell.predicted_residual_c is not None
        assert np.isclose(
            cell.downscaled_temperature_c,
            round(cell.coarse_temperature_c + cell.predicted_residual_c, 2)
        )
        assert cell.quality_flag in ["VALID", "CLAMPED"]
        assert cell.cropland_fraction is not None
        assert cell.is_agricultural_cropland is True

    # 5. Verify Database Records
    db_records = db_session.query(DownscaledWeatherGrid).filter(
        DownscaledWeatherGrid.block_id == block.id,
        DownscaledWeatherGrid.forecast_date == valid_time
    ).all()
    assert len(db_records) == summary.successful_predictions

    # 6. Verify GeoParquet and GeoJSON Exports
    assert response.geoparquet_path is not None
    assert os.path.exists(response.geoparquet_path)
    gdf_parquet = gpd.read_parquet(response.geoparquet_path)
    assert len(gdf_parquet) == summary.total_grid_cells
    assert "downscaled_temp_c" in gdf_parquet.columns
    assert "predicted_residual_c" in gdf_parquet.columns

    assert response.geojson_path is not None
    assert os.path.exists(response.geojson_path)


def test_spatial_downscaling_missing_forecast(spatial_test_environment, db_session: Session):
    """Verifies that missing forecast for a block returns UNAVAILABLE status cleanly without crash."""
    env = spatial_test_environment
    block = env["block"]
    missing_time = datetime(2028, 5, 20, 0, 0, 0)  # Future date with no forecast

    service = SpatialTemperatureInferenceService(
        db=db_session,
        registry=env["registry"]
    )

    response = service.run_spatial_downscaling(
        block_id=block.id,
        forecast_valid_time=missing_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-spatial"
    )

    assert response.quality_summary.successful_predictions == 0
    assert response.quality_summary.unavailable_predictions == response.quality_summary.total_grid_cells
    assert response.quality_summary.spatial_coverage_pct == 0.0
    assert response.quality_summary.diagnostics_passed is False


def test_spatial_downscaling_reproducibility(spatial_test_environment, db_session: Session):
    """Verifies deterministic reproducibility: identical inputs yield identical downscaled fields."""
    env = spatial_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = SpatialTemperatureInferenceService(
        db=db_session,
        registry=env["registry"]
    )

    res1 = service.run_spatial_downscaling(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-spatial",
        persist_to_db=False,
        export_geoparquet=False
    )

    res2 = service.run_spatial_downscaling(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-spatial",
        persist_to_db=False,
        export_geoparquet=False
    )

    assert res1.quality_summary.mean_temperature_c == res2.quality_summary.mean_temperature_c
    assert res1.quality_summary.min_temperature_c == res2.quality_summary.min_temperature_c
    assert res1.quality_summary.max_temperature_c == res2.quality_summary.max_temperature_c


def test_spatial_grid_api_endpoints(spatial_test_environment, client: TestClient):
    """Verifies REST API endpoints for 1-km spatial grid downscaling."""
    env = spatial_test_environment
    block = env["block"]
    valid_time_str = "2026-01-15T12:00:00"

    # 1. GET /api/v1/ml/grid/status
    status_resp = client.get("/api/v1/ml/grid/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["success"] is True
    assert status_resp.json()["data"]["module"] == "1-km Spatial Downscaling Grid Engine"

    # 2. POST /api/v1/ml/predict/temperature/grid
    payload = {
        "block_id": block.id,
        "forecast_valid_time": valid_time_str,
        "source_model": "IMD-GFS",
        "model_version": "v1.0.0-spatial",
        "grid_resolution_km": 1.0,
        "persist_to_db": False,
        "export_geoparquet": True,
        "include_cell_payload": True
    }
    resp = client.post("/api/v1/ml/predict/temperature/grid", json=payload)
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert data["block_id"] == block.id
    assert data["grid_resolution_km"] == 1.0
    assert data["quality_summary"]["successful_predictions"] > 0
    assert "limitations_note" in data


def test_explicit_scope_verifications(spatial_test_environment, db_session: Session):
    """
    CRITICAL STEP 24 & 25: Explicit verification that Phase 7 does NOT implement
    Panchayat aggregation and does NOT downscale rainfall.
    """
    env = spatial_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = SpatialTemperatureInferenceService(
        db=db_session,
        registry=env["registry"]
    )

    response = service.run_spatial_downscaling(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-spatial",
        persist_to_db=False,
        export_geoparquet=False
    )

    # 1. Verify that output is 1-km Block field, not aggregated Panchayat records
    assert response.block_id == block.id
    assert "panchayat_id" not in response.model_dump()

    # 2. Verify that rainfall was not downscaled (carried coarse or unperturbed)
    # The output focuses purely on downscaled_temperature_c
    assert hasattr(response.quality_summary, "mean_temperature_c")
    assert not hasattr(response.quality_summary, "downscaled_rainfall_mm")
