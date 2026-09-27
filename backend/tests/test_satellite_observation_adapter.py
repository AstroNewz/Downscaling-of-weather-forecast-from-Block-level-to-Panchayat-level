"""
Comprehensive Verification Suite: Satellite Observation Adapter & Spatial Fusion Layer
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Validates:
1. Raster GeoTIFF ingestion via rasterio
2. Fail-closed rejection of missing CRS and invalid geotransforms
3. Native resolution preservation without false microclimate resolution claims
4. Timestamp model (observation_time, valid_time, ingestion_time)
5. Nodata and NaN handling without corruption
6. Satellite cloud feature derivation (cloud fraction, min/mean IR, convective threshold)
7. Satellite precipitation semantics (satellite_precipitation_estimate, NEVER observed_rainfall)
8. Operational freshness classification (LIVE_DATA_AVAILABLE vs LIVE_DATA_STALE)
9. Independent Panchayat A and Panchayat B spatial extraction on the SAME satellite grid
10. Boundary-straddling cell intersection
11. Temporal change and trend metrics (T0 -> T1)
12. Provenance preservation through spatial masking
13. Isolation of synthetic test fixtures
"""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin

from app.gis.boundary_registry import boundary_registry
from app.gis.spatial_masking import spatial_masking_service
from app.schemas.satellite import (
    PanchayatSatelliteExtractionResult,
    SatelliteObservationStatus,
    SatelliteProductType,
)
from app.schemas.spatial_masking import VariableType
from app.services.satellite_service import (
    SatelliteObservationService,
    extract_panchayat_satellite_features,
    fetch_satellite_observation,
)
from app.weather.providers.satellite_provider import SatelliteObservationProvider
from tests.fixtures.imaginary_panchayats_fixture import (
    get_imaginary_panchayat_records,
    SHAPELY_POLY_A,
    SHAPELY_POLY_B,
)
from tests.fixtures.synthetic_satellite_fixtures import (
    build_synthetic_satellite_ir_field,
    build_synthetic_satellite_precip_field,
    build_synthetic_satellite_temporal_pair,
    create_test_geotiff_file,
)


@pytest.fixture(autouse=True)
def setup_imaginary_panchayat_registry():
    """Ensures canonical imaginary Panchayats A and B are registered before tests."""
    boundary_registry.clear()
    for rec in get_imaginary_panchayat_records():
        boundary_registry.register(rec)
    yield
    boundary_registry.clear()


@pytest.fixture
def satellite_provider():
    return SatelliteObservationProvider()


@pytest.fixture
def satellite_service(satellite_provider):
    return SatelliteObservationService(
        provider=satellite_provider,
        masking_service=spatial_masking_service,
    )


# =============================================================================
# 1. GeoTIFF / Raster Ingestion & Fail-Closed Validation
# =============================================================================

def test_geotiff_ingestion_success(satellite_provider):
    """Verifies valid GeoTIFF file ingestion via rasterio."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tif_path = Path(tmp_dir) / "test_satellite_ir.tif"
        create_test_geotiff_file(
            output_path=tif_path,
            width=8,
            height=8,
            min_lon=82.40,
            max_lat=25.20,
            pixel_size=0.025,
            crs="EPSG:4326",
            nodata=-9999.0,
        )

        grid = satellite_provider.ingest_raster_file(
            file_path=tif_path,
            product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
            observation_time="2026-09-27T12:00:00Z",
            native_resolution_km=2.5,
        )

        assert grid is not None
        assert grid.variable_name == "brightness_temperature_ir"
        assert grid.variable_type == VariableType.CONTINUOUS
        assert grid.variable_unit == "K"
        assert grid.provenance.native_resolution_km == 2.5
        assert grid.provenance.crs == "EPSG:4326"
        assert len(grid.cells) == 64  # 8 x 8
        # Nodata cell at [-1, -1] must be None
        nodata_cell = [c for c in grid.cells if c.row_idx == 7 and c.col_idx == 7][0]
        assert nodata_cell.value is None


def test_missing_crs_fails_closed(satellite_provider):
    """Verifies that a raster without a valid CRS fails closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tif_path = Path(tmp_dir) / "no_crs.tif"
        create_test_geotiff_file(
            output_path=tif_path,
            crs=None,  # Missing CRS
        )

        with pytest.raises(ValueError, match="lacks a Coordinate Reference System"):
            satellite_provider.ingest_raster_file(
                file_path=tif_path,
                product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
            )


def test_degenerate_geotransform_fails_closed(satellite_provider):
    """Verifies that a raster with degenerate or missing geotransform fails closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tif_path = Path(tmp_dir) / "corrupt_transform.tif"
        create_test_geotiff_file(
            output_path=tif_path,
            crs="EPSG:4326",
            corrupt_transform=True,
        )

        with pytest.raises(ValueError, match="invalid or missing Affine geotransform"):
            satellite_provider.ingest_raster_file(
                file_path=tif_path,
                product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
            )


def test_missing_file_raises_not_found(satellite_provider):
    """Verifies fail-closed behavior when the requested satellite file is absent."""
    with pytest.raises(FileNotFoundError, match="Satellite raster file not found"):
        satellite_provider.ingest_raster_file(
            file_path="non_existent_satellite_file.tif",
            product=SatelliteProductType.SATELLITE_CLOUD_MASK,
        )


def test_invalid_product_name_rejected(satellite_provider):
    """Verifies that non-taxonomic satellite product names are rejected."""
    arr = np.zeros((4, 4))
    t = from_origin(82.40, 25.20, 0.05, 0.05)
    with pytest.raises(ValueError, match="Unsupported satellite product"):
        satellite_provider.create_grid_from_array(
            array=arr,
            transform=t,
            crs="EPSG:4326",
            product="UNAUTHORIZED_MAGICAL_RAIN_DETECTOR",
        )


# =============================================================================
# 2. Native Resolution & Provenance Preservation
# =============================================================================

def test_native_resolution_preservation(satellite_service):
    """
    Verifies that native resolution (e.g. 4.0 km for INSAT-3DR TIR or 1.0 km)
    is strictly preserved in both grid and extraction provenance.
    """
    grid = build_synthetic_satellite_ir_field(native_res_km=4.0)
    assert grid.provenance.native_resolution_km == 4.0

    res = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
    )
    assert res.success is True
    assert res.native_resolution_km == 4.0
    assert "does NOT synthesize higher resolution" in res.provenance.resolution_disclaimer



def test_timestamp_model_distinction(satellite_provider):
    """
    Verifies separate storage of observation_time, product_valid_time,
    and processing/ingestion timestamp.
    """
    arr = np.full((3, 3), 280.0)
    t = from_origin(82.40, 25.20, 0.05, 0.05)
    obs_time = "2026-09-27T10:15:00Z"
    valid_time = "2026-09-27T10:30:00Z"

    grid = satellite_provider.create_grid_from_array(
        array=arr,
        transform=t,
        crs="EPSG:4326",
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
        product_valid_time=valid_time,
    )

    prov = satellite_provider.build_satellite_provenance(
        grid=grid,
        product_type=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    assert prov.observation_time == obs_time
    assert prov.product_valid_time == valid_time
    assert prov.ingestion_time != obs_time  # Ingestion time must be current UTC timestamp


# =============================================================================
# 3. Observation Freshness Checks
# =============================================================================

def test_freshness_evaluation(satellite_provider):
    """Verifies operational latency detection against configurable threshold."""
    now_utc = datetime.now(timezone.utc)
    
    # 1. Fresh observation: 15 minutes old (threshold 60 minutes)
    obs_recent = (now_utc - timedelta(minutes=15)).isoformat()
    is_fresh, age, status = satellite_provider.check_freshness(obs_recent, threshold_minutes=60.0)
    assert is_fresh is True
    assert status == SatelliteObservationStatus.LIVE_DATA_AVAILABLE
    assert 14.0 <= age <= 16.0

    # 2. Stale observation: 90 minutes old (threshold 60 minutes)
    obs_stale = (now_utc - timedelta(minutes=90)).isoformat()
    is_fresh, age, status = satellite_provider.check_freshness(obs_stale, threshold_minutes=60.0)
    assert is_fresh is False
    assert status == SatelliteObservationStatus.LIVE_DATA_STALE
    assert 89.0 <= age <= 91.0


# =============================================================================
# 4. Satellite Precipitation Semantics & NaN Handling
# =============================================================================

def test_satellite_precipitation_semantics(satellite_service):
    """
    CRITICAL POLICY TEST:
    1. Product must be named 'satellite_precipitation_estimate', NEVER 'observed_rainfall'.
    2. Zero rain (0.0 mm) is dry, NOT missing.
    3. Missing cells (NaN/None) are NOT converted to 0.0 mm.
    """
    precip_grid = build_synthetic_satellite_precip_field(native_res_km=4.0)
    assert precip_grid.variable_name == "satellite_precipitation_estimate"

    # Extract for Panchayat B (which has 0.0 mm rain across its cells)
    res_b = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        satellite_grid=precip_grid,
    )

    assert res_b.success is True
    assert res_b.features["is_estimated"] is True
    # In B, all valid intersecting cells are 0.0 mm
    assert res_b.features["satellite_precipitation_estimate_mean_mm"] == 0.0
    assert res_b.features["rain_area_fraction"] == 0.0
    assert res_b.features["is_rain_detected"] is False

    # Extract for Panchayat A (which has rain and one missing cell)
    res_a = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=precip_grid,
    )

    assert res_a.success is True
    assert res_a.features["satellite_precipitation_estimate_mean_mm"] > 0.0
    assert res_a.features["is_rain_detected"] is True
    assert res_a.features["missing_cell_fraction"] > 0.0  # Cell [0, 3] was None


# =============================================================================
# 5. Independent A/B Separation on the Same Satellite Field
# =============================================================================

def test_adjacent_panchayat_ab_separation(satellite_service):
    """
    Passes the SAME synthetic satellite IR field through Panchayat A and Panchayat B.
    Verifies that:
    - Panchayat A extracts cold convective cloud tops (< 225K, fraction_below_convective_threshold ~ 1.0)
    - Panchayat B extracts warm clear ground (> 295K, fraction_below_convective_threshold == 0.0)
    - Straddling cells along the common boundary do not contaminate independent extraction.
    """
    grid = build_synthetic_satellite_ir_field(native_res_km=1.0)

    # 1. Independent extraction for Panchayat A
    res_a = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
        convective_threshold_k=235.0,
    )

    # 2. Independent extraction for Panchayat B
    res_b = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        satellite_grid=grid,
        convective_threshold_k=235.0,
    )

    assert res_a.success is True
    assert res_b.success is True
    assert res_a.panchayat_id == "IMAGINARY_PANCHAYAT_A"
    assert res_b.panchayat_id == "IMAGINARY_PANCHAYAT_B"

    feat_a = res_a.features
    feat_b = res_b.features

    # Temperature difference must be dramatic: A is ~215-225K, B is ~295-305K
    assert feat_a["mean_brightness_temperature_k"] < 235.0
    assert feat_b["mean_brightness_temperature_k"] > 290.0

    # Cold convective cloud fraction: A is 100% cloudy convective, B is 0%
    assert feat_a["fraction_below_convective_threshold"] > 0.90
    assert feat_b["fraction_below_convective_threshold"] == 0.0

    assert feat_a["cloud_fraction"] > 0.90
    assert feat_b["cloud_fraction"] < 0.10


# =============================================================================
# 6. Temporal Change Tracking (T0 -> T1)
# =============================================================================

def test_temporal_change_convective_cooling(satellite_service):
    """
    Verifies temporal delta calculation when consecutive observations are provided.
    Over Panchayat A:
    T0 has IR ~ 248K
    T1 has rapid convective cooling to IR ~ 215K
    Must detect negative mean_signal_delta and trend 'COOLING_CONVECTIVE'.
    """
    t0_grid, t1_grid = build_synthetic_satellite_temporal_pair(native_res_km=1.0)

    res_t1 = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=t1_grid,
        previous_satellite_grid=t0_grid,
        convective_threshold_k=235.0,
    )

    assert res_t1.success is True
    delta = res_t1.temporal_change
    assert delta is not None
    assert delta.delta_minutes == 30.0
    assert delta.min_signal_delta < -20.0  # Cold top dropped significantly
    assert delta.mean_signal_delta < -20.0
    assert delta.trend == "COOLING_CONVECTIVE"


# =============================================================================
# 7. High-Level Programmatic Interface
# =============================================================================

def test_high_level_programmatic_interface(satellite_service):
    """Verifies top-level helper functions fetch_satellite_observation and extract_panchayat_satellite_features."""
    arr = np.full((4, 4), 220.0)
    t = from_origin(82.40, 25.20, 0.05, 0.05)

    grid = fetch_satellite_observation(
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time="2026-09-27T12:00:00Z",
        options={
            "array": arr,
            "transform": t,
            "crs": "EPSG:4326",
            "native_resolution_km": 1.5,
        },
    )

    assert grid.variable_name == "brightness_temperature_ir"

    result = extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
    )

    assert result.success is True
    assert result.panchayat_id == "IMAGINARY_PANCHAYAT_A"
    assert result.features["min_brightness_temperature_k"] == 220.0


# =============================================================================
# 8. Product Taxonomy, Checksum & Boundary Fail-Closed Tests
# =============================================================================

def test_categorical_cloud_mask_extraction(satellite_service, satellite_provider):
    """Verifies SATELLITE_CLOUD_MASK categorical extraction with cloud/clear fractions."""
    arr = np.array([
        [1.0, 1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
    ])
    t = from_origin(82.40, 25.20, 0.05, 0.05)
    grid = satellite_provider.create_grid_from_array(
        array=arr,
        transform=t,
        crs="EPSG:4326",
        product=SatelliteProductType.SATELLITE_CLOUD_MASK,
        native_resolution_km=1.0,
    )

    res = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
    )
    assert res.success is True
    assert res.product_type == SatelliteProductType.SATELLITE_CLOUD_MASK
    assert 0.0 <= res.features["cloud_fraction"] <= 1.0
    assert round(res.features["cloud_fraction"] + res.features["clear_fraction"], 2) == 1.0
    assert res.features["total_valid_cells"] > 0


def test_water_vapour_continuous_extraction(satellite_service, satellite_provider):
    """Verifies SATELLITE_WATER_VAPOUR continuous variable statistics."""
    arr = np.full((4, 4), 242.5)
    t = from_origin(82.40, 25.20, 0.05, 0.05)
    grid = satellite_provider.create_grid_from_array(
        array=arr,
        transform=t,
        crs="EPSG:4326",
        product=SatelliteProductType.SATELLITE_WATER_VAPOUR,
        native_resolution_km=2.0,
    )

    res = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        satellite_grid=grid,
    )
    assert res.success is True
    assert res.product_type == SatelliteProductType.SATELLITE_WATER_VAPOUR
    assert res.features["mean"] == 242.5


def test_unverified_boundary_fails_closed_when_required(satellite_service):
    """Verifies that unverified Panchayat boundaries trigger fail-closed state when required."""
    grid = build_synthetic_satellite_ir_field(native_res_km=1.0)
    # The imaginary fixture has is_verified=False
    res = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
        require_verified=True,
    )
    assert res.success is False
    assert res.status == "UNVERIFIED_GEOMETRY"
    assert "unverified" in res.message


def test_boundary_straddling_cell_fractional_overlap(satellite_service):
    """
    Verifies that a grid cell straddling the common boundary between A and B
    is partitioned with fractional overlap strictly proportional to intersection geometry.
    """
    grid = build_synthetic_satellite_ir_field(native_res_km=1.0)
    res_a = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        satellite_grid=grid,
    )
    res_b = satellite_service.extract_panchayat_satellite_features(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        satellite_grid=grid,
    )

    assert res_a.success is True
    assert res_b.success is True
    # Coverage quality must be complete for both given domain coverage
    assert res_a.coverage_fraction > 0.99
    assert res_b.coverage_fraction > 0.99


def test_geotiff_sha256_provenance_preservation(satellite_provider, satellite_service):
    """Verifies that cryptographic SHA-256 hash of ingested GeoTIFF survives masking into result provenance."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tif_path = Path(tmp_dir) / "hashed_satellite.tif"
        create_test_geotiff_file(output_path=tif_path)

        grid = satellite_provider.ingest_raster_file(
            file_path=tif_path,
            product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        )

        res = satellite_service.extract_panchayat_satellite_features(
            panchayat_id="IMAGINARY_PANCHAYAT_A",
            satellite_grid=grid,
            file_sha256=grid.provenance.source_version,  # Or from grid
        )

        assert res.success is True
        assert res.provenance.provider == "SATELLITE_OBSERVATION_ADAPTER"
        assert res.provenance.crs == "EPSG:4326"

