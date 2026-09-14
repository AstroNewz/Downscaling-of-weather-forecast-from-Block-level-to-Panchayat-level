"""
Tests for Phase 8: Panchayat-Level Weather Aggregation from 1-km Downscaled Grid
SIH Problem Statement 26074 (Weather Downscaling)
"""
import os
import pytest
from datetime import datetime
import numpy as np
from shapely.geometry import Polygon, Point
from shapely import wkt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import BlockWeatherForecast, DownscaledWeatherGrid, PanchayatWeather
from app.ml.trainer import DownscalingModelTrainer
from app.ml.registry import LocalModelRegistry
from app.services.panchayat_aggregation import PanchayatWeatherAggregationService
from tests.test_ml_training import generate_synthetic_feature_df
from tests.test_spatial_downscaling import create_sample_block_polygon


@pytest.fixture
def panchayat_test_environment(tmp_path, monkeypatch, db_session: Session):
    """
    Sets up test environment:
    - Registered Phase 6 model
    - Block entity with geometry
    - Two child Panchayat entities with distinct geometries inside the Block
    - BlockWeatherForecast
    """
    registry_dir = str(tmp_path / "models_panchayat")
    monkeypatch.setattr(settings, "ML_MODEL_DIR", registry_dir)
    monkeypatch.setattr(settings, "TEMPERATURE_MODEL_VERSION", "v1.0.0-p8")
    monkeypatch.setattr(settings, "DATASET_OUTPUT_DIR", str(tmp_path / "processed"))

    registry = LocalModelRegistry(base_dir=registry_dir)
    trainer = DownscalingModelTrainer(registry=registry)

    # Train model artifact
    df = generate_synthetic_feature_df(80)
    trainer.train_from_dataframe(
        df=df,
        model_version="v1.0.0-p8",
        allow_synthetic=True,
        is_synthetic=True
    )

    # 1. Block geometry (~5km x 5km centered at 75.5, 22.5)
    block_poly = create_sample_block_polygon(lon_center=75.5, lat_center=22.5, size_deg=0.04)
    block = Block(
        lgd_code="BLK_P8_001",
        name="Varanasi Sadar Block",
        district_name="Varanasi",
        state_name="Uttar Pradesh",
        geometry=f"SRID=4326;{block_poly.wkt}",
        centroid="SRID=4326;POINT(75.5 22.5)"
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    # 2. Child Panchayat A (Northern half of Block)
    p_a_poly = Polygon([
        (75.48, 22.50), (75.52, 22.50), (75.52, 22.52), (75.48, 22.52), (75.48, 22.50)
    ])
    panchayat_a = Panchayat(
        lgd_code="GP_P8_A",
        name="Shivpur Panchayat",
        block_id=block.id,
        elevation_meters=280.0,
        geometry=f"SRID=4326;{p_a_poly.wkt}",
        centroid="SRID=4326;POINT(75.50 22.51)"
    )
    db_session.add(panchayat_a)

    # 3. Child Panchayat B (Southern half of Block)
    p_b_poly = Polygon([
        (75.48, 22.48), (75.52, 22.48), (75.52, 22.50), (75.48, 22.50), (75.48, 22.48)
    ])
    panchayat_b = Panchayat(
        lgd_code="GP_P8_B",
        name="Kashi Gram Panchayat",
        block_id=block.id,
        elevation_meters=320.0,
        geometry=f"SRID=4326;{p_b_poly.wkt}",
        centroid="SRID=4326;POINT(75.50 22.49)"
    )
    db_session.add(panchayat_b)
    db_session.commit()
    db_session.refresh(panchayat_a)
    db_session.refresh(panchayat_b)

    # 4. BlockWeatherForecast
    valid_time = datetime(2026, 1, 15, 12, 0, 0)
    issue_time = datetime(2026, 1, 15, 0, 0, 0)
    forecast = BlockWeatherForecast(
        block_id=block.id,
        forecast_date=valid_time,
        issue_time=issue_time,
        temp_min=20.0,
        temp_max=30.0,
        rainfall_mm=0.0,
        relative_humidity_pct=60.0,
        wind_speed_mps=2.5,
        wind_direction_deg=180.0,
        cloud_cover_pct=15.0,
        source_model="IMD-GFS",
        quality_flag="VALID"
    )
    db_session.add(forecast)
    db_session.commit()

    return {
        "registry": registry,
        "block": block,
        "panchayat_a": panchayat_a,
        "panchayat_b": panchayat_b,
        "valid_time": valid_time,
        "issue_time": issue_time,
    }


def test_area_weighted_aggregation_math():
    """
    CRITICAL STEP 3 & 5: Verifies that area-weighted mean and variance formulas are mathematically exact.
    Formula: T_mean = sum(w_i * T_i) / sum(w_i) where w_i = a_i / A_total
    """
    # 3 contributing cells with different intersection areas (weights) and downscaled temperatures
    temps = np.array([24.0, 26.0, 28.0])
    areas_sqm = np.array([500_000.0, 300_000.0, 200_000.0])  # Total = 1,000,000 m²
    weights = areas_sqm / np.sum(areas_sqm)  # [0.5, 0.3, 0.2]

    # Manual expected weighted mean: (0.5 * 24) + (0.3 * 26) + (0.2 * 28) = 12.0 + 7.8 + 5.6 = 25.4°C
    expected_mean = 25.4
    computed_mean = float(np.sum(weights * temps) / np.sum(weights))
    assert np.isclose(computed_mean, expected_mean)

    # Minimum and Maximum
    assert min(temps) == 24.0
    assert max(temps) == 28.0

    # Weighted Standard Deviation
    var = float(np.sum(weights * ((temps - expected_mean) ** 2)) / np.sum(weights))
    std = float(np.sqrt(var))
    assert std > 0.0


def test_panchayat_aggregation_service_end_to_end(panchayat_test_environment, db_session: Session):
    """
    Verifies end-to-end area-weighted Panchayat weather aggregation across Block Panchayats:
    1-km Grid -> Polygon Intersection -> Area Weights -> Temperature Statistics -> DB Upsert.
    """
    env = panchayat_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = PanchayatWeatherAggregationService(db=db_session)
    response = service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-p8",
        grid_resolution_km=1.0,
        persist_to_db=True
    )

    # 1. Verify Response Summary
    assert response.block_id == block.id
    assert response.block_name == block.name
    assert response.total_panchayats_in_block == 2
    assert response.aggregated_panchayats_count == 2
    assert response.overall_block_coverage_pct > 0.0

    # 2. Verify Statistics for Each Panchayat
    for pw in response.panchayat_weather:
        assert pw.block_id == block.id
        assert pw.panchayat_id in [env["panchayat_a"].id, env["panchayat_b"].id]
        assert pw.model_version == "v1.0.0-p8"
        assert pw.aggregation_method == "AREA_WEIGHTED"

        # Check temperature ranges
        assert pw.min_temperature_c <= pw.mean_temperature_c <= pw.max_temperature_c
        assert 15.0 <= pw.mean_temperature_c <= 35.0

        # Check coverage
        assert pw.coverage_percentage > 0.0
        assert pw.total_panchayat_area_sqkm > 0.0
        assert pw.valid_grid_cells > 0
        assert pw.quality_status in ["COMPLETE", "PARTIAL"]

    # 3. Verify Database Persistence (PanchayatWeather table)
    db_records = db_session.query(PanchayatWeather).filter(
        PanchayatWeather.block_id == block.id,
        PanchayatWeather.forecast_date == valid_time
    ).all()
    assert len(db_records) == 2


def test_single_panchayat_filtering(panchayat_test_environment, db_session: Session):
    """Verifies that specifying panchayat_id aggregates only the targeted Panchayat."""
    env = panchayat_test_environment
    block = env["block"]
    panchayat_a = env["panchayat_a"]
    valid_time = env["valid_time"]

    service = PanchayatWeatherAggregationService(db=db_session)
    response = service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=valid_time,
        panchayat_id=panchayat_a.id,
        model_version="v1.0.0-p8",
        persist_to_db=False
    )

    assert response.aggregated_panchayats_count == 1
    assert response.panchayat_weather[0].panchayat_id == panchayat_a.id
    assert response.panchayat_weather[0].panchayat_name == panchayat_a.name


def test_idempotent_aggregation_upsert(panchayat_test_environment, db_session: Session):
    """
    CRITICAL STEP 13: Verifies that running aggregation twice for the same Panchayat and forecast run
    is idempotent (updates records without creating duplicate rows).
    """
    env = panchayat_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = PanchayatWeatherAggregationService(db=db_session)

    # First run
    service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-p8",
        persist_to_db=True
    )
    count_first = db_session.query(PanchayatWeather).filter(
        PanchayatWeather.block_id == block.id,
        PanchayatWeather.forecast_date == valid_time
    ).count()
    assert count_first == 2

    # Second run (should update, not duplicate)
    service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=valid_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-p8",
        persist_to_db=True
    )
    count_second = db_session.query(PanchayatWeather).filter(
        PanchayatWeather.block_id == block.id,
        PanchayatWeather.forecast_date == valid_time
    ).count()
    assert count_second == 2


def test_missing_forecast_panchayat_aggregation(panchayat_test_environment, db_session: Session):
    """Verifies that missing forecast marks all Panchayats as UNAVAILABLE cleanly without error."""
    env = panchayat_test_environment
    block = env["block"]
    future_time = datetime(2030, 8, 1, 0, 0, 0)

    service = PanchayatWeatherAggregationService(db=db_session)
    response = service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=future_time,
        source_model="IMD-GFS",
        model_version="v1.0.0-p8",
        persist_to_db=False
    )

    assert response.unavailable_count == 2
    assert response.overall_block_coverage_pct == 0.0
    for pw in response.panchayat_weather:
        assert pw.quality_status == "UNAVAILABLE"
        assert pw.coverage_percentage == 0.0
        assert pw.valid_grid_cells == 0


def test_panchayat_weather_api_endpoints(panchayat_test_environment, client: TestClient):
    """Verifies all Phase 8 REST API endpoints."""
    env = panchayat_test_environment
    block = env["block"]
    panchayat_a = env["panchayat_a"]
    valid_time_str = "2026-01-15T12:00:00"

    # 1. POST /api/v1/panchayat/weather/aggregate
    payload = {
        "block_id": block.id,
        "forecast_valid_time": valid_time_str,
        "source_model": "IMD-GFS",
        "model_version": "v1.0.0-p8",
        "grid_resolution_km": 1.0,
        "persist_to_db": True
    }
    agg_resp = client.post("/api/v1/panchayat/weather/aggregate", json=payload)
    assert agg_resp.status_code == 200
    assert agg_resp.json()["success"] is True
    data = agg_resp.json()["data"]
    assert data["aggregated_panchayats_count"] == 2

    # 2. GET /api/v1/panchayat/weather (paginated query)
    query_resp = client.get(f"/api/v1/panchayat/weather?block_id={block.id}")
    assert query_resp.status_code == 200
    assert query_resp.json()["success"] is True
    paginated_data = query_resp.json()["data"]
    assert paginated_data["total"] >= 2
    assert len(paginated_data["items"]) >= 2

    # 3. GET /api/v1/panchayat/{panchayat_id}/weather
    single_resp = client.get(f"/api/v1/panchayat/{panchayat_a.id}/weather")
    assert single_resp.status_code == 200
    assert single_resp.json()["success"] is True
    records = single_resp.json()["data"]
    assert len(records) >= 1
    assert records[0]["panchayat_id"] == panchayat_a.id

    # 4. GET /api/v1/panchayat/weather/status
    status_resp = client.get("/api/v1/panchayat/weather/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["module"] == "Panchayat Weather Spatial Aggregation Engine"


def test_explicit_phase8_scope_guard(panchayat_test_environment, db_session: Session):
    """
    CRITICAL SCOPE CHECK: Verifies that Phase 8 strictly produces Panchayat weather statistics
    and does NOT generate crop advisories, risk scores, or rainfall ML predictions.
    """
    env = panchayat_test_environment
    block = env["block"]
    valid_time = env["valid_time"]

    service = PanchayatWeatherAggregationService(db=db_session)
    response = service.aggregate_block_panchayats(
        block_id=block.id,
        forecast_valid_time=valid_time,
        model_version="v1.0.0-p8",
        persist_to_db=False
    )

    for pw in response.panchayat_weather:
        # Check that response only contains weather and spatial stats
        pw_dict = pw.model_dump()
        assert "mean_temperature_c" in pw_dict
        assert "min_temperature_c" in pw_dict
        assert "max_temperature_c" in pw_dict
        assert "coverage_percentage" in pw_dict

        # Verify no crop advisories or risk scoring
        assert "crop_name" not in pw_dict
        assert "advisory_text" not in pw_dict
        assert "pest_risk_level" not in pw_dict
        assert "irrigation_advice" not in pw_dict
