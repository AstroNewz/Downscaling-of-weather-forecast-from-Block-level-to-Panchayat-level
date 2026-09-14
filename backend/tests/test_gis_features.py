import math
import numpy as np
import pytest
from datetime import datetime, timezone
from app.gis.dem import DEMTopographicEngine
from app.gis.landuse import LandUseExtractor
from app.gis.spatial_features import SpatialFeatureExtractor
from app.gis.schemas import TerrainFeatures, LandUseFeatures, EnvironmentalFeatureSet
from app.db.models.spatial import LandUseMask
from app.db.models.weather import BlockWeatherForecast, WeatherObservation
from app.ml.features import FeatureEngineer
from app.ml.schemas import FEATURE_SCHEMA_VERSION


def test_dem_slope_and_aspect_flat_terrain():
    """
    SYNTHETIC TEST DATA — NOT REAL ENVIRONMENTAL DATA
    Verifies slope is 0 degrees on a perfectly flat 3x3 synthetic elevation grid.
    """
    flat_window = np.array([
        [100.0, 100.0, 100.0],
        [100.0, 100.0, 100.0],
        [100.0, 100.0, 100.0]
    ], dtype=np.float64)

    slope, aspect, sin_asp, cos_asp = DEMTopographicEngine.compute_slope_and_aspect(flat_window, 30.0, 30.0)
    assert slope == 0.0
    assert aspect == 0.0
    assert sin_asp == 0.0
    assert cos_asp == 1.0


def test_dem_slope_and_aspect_east_slope():
    """
    SYNTHETIC TEST DATA — NOT REAL ENVIRONMENTAL DATA
    Verifies slope and aspect on an eastward inclined synthetic elevation grid (higher in West, lower in East).
    """
    east_slope_window = np.array([
        [120.0, 110.0, 100.0],
        [120.0, 110.0, 100.0],
        [120.0, 110.0, 100.0]
    ], dtype=np.float64)

    slope, aspect, sin_asp, cos_asp = DEMTopographicEngine.compute_slope_and_aspect(east_slope_window, 30.0, 30.0)
    assert slope > 0.0
    # Slope facing East -> aspect ~ 90°
    assert 85.0 <= aspect <= 95.0
    assert pytest.approx(sin_asp, 0.05) == 1.0
    assert pytest.approx(cos_asp, 0.05) == 0.0


def test_dem_terrain_roughness_index():
    """
    SYNTHETIC TEST DATA — NOT REAL ENVIRONMENTAL DATA
    Verifies TRI is 0 on flat terrain and positive on undulating terrain.
    """
    flat = np.full((3, 3), 150.0)
    assert DEMTopographicEngine.compute_terrain_roughness(flat) == 0.0

    rugged = np.array([
        [100.0, 120.0, 140.0],
        [110.0, 130.0, 150.0],
        [120.0, 140.0, 160.0]
    ])
    tri = DEMTopographicEngine.compute_terrain_roughness(rugged)
    assert tri > 0.0
    assert tri == pytest.approx(np.std(rugged), 0.01)


def test_lapse_rate_temperature_adjustment():
    """
    Verifies physical environmental lapse rate calculation: -6.5°C per 1,000m.
    Delta_z = +500m -> Delta_T = -3.25°C
    Delta_z = -200m -> Delta_T = +1.30°C
    """
    adj_up = DEMTopographicEngine.calculate_lapse_rate_adjustment(obs_elevation_m=700.0, block_elevation_m=200.0)
    assert adj_up == -3.25

    adj_down = DEMTopographicEngine.calculate_lapse_rate_adjustment(obs_elevation_m=100.0, block_elevation_m=300.0)
    assert adj_down == 1.30

    adj_none = DEMTopographicEngine.calculate_lapse_rate_adjustment(obs_elevation_m=None, block_elevation_m=300.0)
    assert adj_none is None


def test_land_use_fractions_extraction():
    """
    Verifies normalized land-use fractions calculation from LandUseMask entity.
    """
    mask = LandUseMask(
        id=1,
        panchayat_id=1,
        total_area_ha=1000.0,
        cropland_area_ha=650.0,
        forest_area_ha=150.0,
        urban_area_ha=100.0,
        water_area_ha=50.0,
        barren_area_ha=50.0,
        is_agricultural_eligible=True,
    )

    lu_features = LandUseExtractor.extract_from_mask_record(mask)
    assert lu_features.total_area_ha == 1000.0
    assert lu_features.cropland_fraction == 0.65
    assert lu_features.forest_fraction == 0.15
    assert lu_features.urban_fraction == 0.10
    assert lu_features.water_fraction == 0.05
    assert lu_features.barren_fraction == 0.05
    assert lu_features.is_agricultural_cropland is True


def test_spatial_distance_haversine():
    """Verifies Haversine great-circle distance calculation."""
    # Distance between New Delhi (28.6139, 77.2090) and Varanasi (25.3176, 82.9739) ~ 680 km
    dist = SpatialFeatureExtractor.haversine_distance_km(28.6139, 77.2090, 25.3176, 82.9739)
    assert 670.0 <= dist <= 690.0


def test_ml_feature_record_environmental_integration():
    """
    Verifies that FeatureEngineer integrates Phase 5 environmental predictors into EngineeredFeatureRecord.
    """
    obs = WeatherObservation(
        station_id="AWS_TEST",
        latitude=25.3,
        longitude=82.9,
        observation_time=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        temp_celsius=29.0
    )
    fc = BlockWeatherForecast(
        block_id=1,
        forecast_date=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        issue_time=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
        temp_min=22.0,
        temp_max=32.0,
        source_model="IMD-GFS"
    )

    env_set = EnvironmentalFeatureSet(
        latitude=25.3,
        longitude=82.9,
        block_id=1,
        terrain=TerrainFeatures(
            elevation_m=120.0,
            slope_deg=3.5,
            aspect_deg=180.0,
            sin_aspect=0.0,
            cos_aspect=-1.0,
            terrain_roughness=1.2,
            lapse_rate_temp_adjustment_c=-0.325,
        ),
        land_use=LandUseFeatures(
            total_area_ha=500.0,
            cropland_fraction=0.80,
            forest_fraction=0.10,
            urban_fraction=0.05,
            water_fraction=0.05,
            is_agricultural_cropland=True,
        )
    )

    record = FeatureEngineer.build_feature_record(
        obs=obs,
        forecast=fc,
        lead_hours=6.0,
        time_diff_min=0.0,
        spatial_data={"obs_latitude": 25.3, "obs_longitude": 82.9},
        environmental_features=env_set,
        dataset_version=FEATURE_SCHEMA_VERSION,
    )

    assert record is not None
    assert record.dataset_version == "v1.1.0"
    assert record.slope_deg == 3.5
    assert record.cos_aspect == -1.0
    assert record.lapse_rate_temp_adjustment_c == -0.325
    assert record.cropland_fraction == 0.80
    assert record.is_agricultural_cropland is True
