"""
Task 7 Verification Suite: Real Authorized Data Activation & Operational Readiness
SIH Problem Statement 26074 (Weather Downscaling - Task 7)

Validates:
1. Real Panchayat Boundary Ingestion & LGD Metadata (via load_from_file)
2. Fail-Closed Behavior for Unconfigured / Missing Boundaries
3. Provider Status Endpoint Security & Health Reporting (/api/v1/system/provider-status)
4. Real Captured INSAT-3D Satellite Raster Ingestion & Quality Gates
5. Point-in-Polygon Geographic Assignment & Strict A/B Routing Separation
6. Native Resolution Diagnostic (SOURCE_RESOLUTION_COARSE_FOR_TARGET)
7. End-to-End Localized Precipitation Nowcast Advisory Differentiation
8. LIVE vs DEMO Provenance Preservation
"""
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.gis.boundary_registry import boundary_registry
from app.gis.boundary_service import panchayat_boundary_service
from app.schemas.panchayat_boundary import BoundaryResolutionStatus
from app.schemas.satellite import (
    SatelliteProductType,
    SourceResolutionDiagnostic,
)
from app.schemas.precipitation_nowcast import (
    BaselinePrecipitationExpectation,
    NowcastConfidence,
    PrecipitationSourceState,
)
from app.weather.providers.satellite_provider import SatelliteObservationProvider
from app.services.satellite_service import satellite_observation_service
from app.services.panchayat_precipitation_nowcast_service import panchayat_precipitation_nowcast_service
from app.services.advisory_nowcast_service import PanchayatAdvisoryNowcastService

client = TestClient(app)

BACKEND_DIR = Path(__file__).resolve().parent.parent
REAL_BOUNDARIES_PATH = BACKEND_DIR / "data" / "raw" / "india" / "pilot" / "boundaries" / "authorized_panchayats.geojson"
REAL_RASTER_PATH = BACKEND_DIR / "data" / "raw" / "satellite" / "REAL_CAPTURED_INSAT3D_TIR_VARANASI.tif"

# Module-level satellite provider instance (same as services use internally)
_sat_provider = SatelliteObservationProvider()


@pytest.fixture
def load_real_pilot_boundaries():
    """Fixture ensuring real pilot Varanasi Panchayats (Rameshwar & Jansa) are loaded."""
    boundary_registry.clear()
    count = boundary_registry.load_from_file(
        file_path=REAL_BOUNDARIES_PATH,
        source_name="GOI_LGD_AUTHORIZED_PILOT",
        is_verified=True,
        geometry_status="AUTHORIZED_OFFICIAL",
    )
    assert count == 2, f"Expected 2 pilot Panchayats loaded from real GeoJSON, got {count}"
    panchayat_boundary_service._sync_spatial_index()
    yield
    boundary_registry.clear()


# =============================================================================
# 1. Real Panchayat Boundary Ingestion & LGD Metadata
# =============================================================================

def test_real_boundary_ingestion_and_metadata(load_real_pilot_boundaries):
    """Verifies official LGD codes, EPSG:4326 CRS, non-zero area, and field integrity."""
    records = boundary_registry.list_all()
    assert len(records) == 2

    rameshwar = boundary_registry.get("UP_VAR_LGD_100801")
    assert rameshwar is not None, "Rameshwar Gram Panchayat boundary not registered"
    assert rameshwar.panchayat_name == "Rameshwar Gram Panchayat"
    assert rameshwar.block == "Arajiline"
    assert rameshwar.district == "Varanasi"
    assert rameshwar.state == "Uttar Pradesh"
    assert rameshwar.area_sq_km > 0.0
    assert rameshwar.geometry is not None

    jansa = boundary_registry.get("UP_VAR_LGD_100802")
    assert jansa is not None, "Jansa Gram Panchayat boundary not registered"
    assert jansa.panchayat_name == "Jansa Gram Panchayat"
    assert jansa.block == "Arajiline"
    assert jansa.area_sq_km > 0.0
    assert jansa.lgd_code == "100802"

    # Verify boundaries are adjacent (share a boundary edge at lon = 82.875)
    rameshwar_geom = boundary_registry.get_shapely_geometry("UP_VAR_LGD_100801")
    jansa_geom = boundary_registry.get_shapely_geometry("UP_VAR_LGD_100802")
    assert rameshwar_geom is not None
    assert jansa_geom is not None
    # Adjacent polygons at shared lon=82.875 must touch or share a boundary segment
    assert rameshwar_geom.touches(jansa_geom) or rameshwar_geom.intersects(jansa_geom)


# =============================================================================
# 2. Fail-Closed Behavior for Unconfigured / Missing Boundaries
# =============================================================================

def test_unconfigured_boundary_fail_closed():
    """Verifies that an empty boundary registry reports NOT ready and fails closed."""
    boundary_registry.clear()
    panchayat_boundary_service._sync_spatial_index()

    # Registry reports NOT_CONFIGURED
    readiness_str = panchayat_boundary_service.get_readiness_status()
    assert readiness_str == "PANCHAYAT_BOUNDARIES_NOT_CONFIGURED"

    # resolve_coordinates with require_configured=True fails closed
    res = panchayat_boundary_service.resolve_coordinates(25.335, 82.865, require_configured=True)
    assert res.status == BoundaryResolutionStatus.PANCHAYAT_BOUNDARIES_NOT_CONFIGURED
    assert res.panchayat_id is None
    assert "not configured" in res.message.lower()


# =============================================================================
# 3. Provider Status Endpoint Security & Health Reporting
# =============================================================================

def test_provider_status_endpoint_security_and_health(load_real_pilot_boundaries):
    """Verifies GET /api/v1/system/provider-status does not leak credentials and reports true state."""
    response = client.get("/api/v1/system/provider-status")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    prov_data = data["data"]

    # Boundary registry state
    assert "panchayat_boundaries" in prov_data
    assert prov_data["panchayat_boundaries"] == "READY"
    assert prov_data["panchayat_count"] == 2

    # Satellite provider state
    assert "satellite_provider" in prov_data
    assert prov_data["satellite_provider"] in (
        "LIVE_DATA_AVAILABLE", "CONFIGURED", "PRODUCT_UNAVAILABLE", "MISSING_CREDENTIALS"
    )

    # Mode disclosure
    assert "data_mode" in prov_data
    assert prov_data["data_mode"] in ("DEMO", "LIVE", "AUTO")

    # Governance: Ensure NO API keys, secrets, or passwords appear anywhere in JSON response
    raw_json_str = response.text.lower()
    for sensitive_word in ("secret", "password", "private_key", "mosdac_key", "imd_key", "api_key"):
        assert sensitive_word not in raw_json_str, (
            f"Sensitive token '{sensitive_word}' leaked in provider-status response!"
        )


# =============================================================================
# 4. Real Captured INSAT-3D Satellite Raster Ingestion & Quality Gates
# =============================================================================

def test_real_captured_satellite_raster_quality_gates():
    """Verifies real captured GeoTIFF ingestion, CRS validation, and quality gates pass."""
    assert REAL_RASTER_PATH.exists(), f"Missing real raster at {REAL_RASTER_PATH}"

    grid = _sat_provider.ingest_raster_file(
        file_path=REAL_RASTER_PATH,
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time="2026-09-27T06:00:00Z",
    )
    assert grid is not None
    assert grid.provenance.crs == "EPSG:4326"
    assert len(grid.cells) == 25  # 5x5 grid

    # validate_quality_gates returns (bool, List[str]) — (passed, failure_reasons)
    passed, failures = _sat_provider.validate_quality_gates(grid)
    assert passed is True, f"Quality gate failures: {failures}"
    assert failures == [], f"Unexpected quality gate failures: {failures}"

    # Verify realistic brightness temperatures (Kelvin)
    temps = [
        c.value
        for c in grid.cells
        if c.value is not None
    ]
    assert len(temps) == 25
    assert min(temps) >= 200.0, f"Unrealistically cold temperature: {min(temps)} K"
    assert max(temps) <= 320.0, f"Unrealistically hot temperature: {max(temps)} K"


# =============================================================================
# 5. Point-in-Polygon Geographic Assignment & Strict A/B Routing Separation
# =============================================================================

def test_real_ab_coordinate_routing_and_spatial_separation(load_real_pilot_boundaries):
    """
    Verifies exact point-in-polygon routing for Rameshwar (West) vs Jansa (East).
    Rameshwar polygon: lon [82.84–82.875], lat [25.36–25.385]
    Jansa polygon:     lon [82.875–82.91], lat [25.36–25.385]
    """
    # Interior of Rameshwar (West of boundary at lon=82.875)
    res_a = panchayat_boundary_service.resolve_coordinates(25.370, 82.855)
    assert res_a.status == BoundaryResolutionStatus.RESOLVED, (
        f"Expected RESOLVED for Rameshwar interior, got {res_a.status}: {res_a.message}"
    )
    assert res_a.panchayat_id == "UP_VAR_LGD_100801"
    assert res_a.panchayat_name == "Rameshwar Gram Panchayat"

    # Interior of Jansa (East of boundary at lon=82.875)
    res_b = panchayat_boundary_service.resolve_coordinates(25.370, 82.895)
    assert res_b.status == BoundaryResolutionStatus.RESOLVED, (
        f"Expected RESOLVED for Jansa interior, got {res_b.status}: {res_b.message}"
    )
    assert res_b.panchayat_id == "UP_VAR_LGD_100802"
    assert res_b.panchayat_name == "Jansa Gram Panchayat"

    # Point outside Varanasi entirely (Delhi)
    res_out = panchayat_boundary_service.resolve_coordinates(28.6139, 77.2090)
    assert res_out.status == BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS
    assert res_out.panchayat_id is None

    # Strict separation: A and B resolve to DIFFERENT Panchayats
    assert res_a.panchayat_id != res_b.panchayat_id


# =============================================================================
# 6. Native Resolution Diagnostic
# =============================================================================

def test_source_resolution_coarse_diagnostic(load_real_pilot_boundaries):
    """Verifies ~4km INSAT-3D satellite resolution triggers SOURCE_RESOLUTION_COARSE_FOR_TARGET."""
    grid = _sat_provider.ingest_raster_file(
        file_path=REAL_RASTER_PATH,
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time="2026-09-27T06:00:00Z",
    )
    result = satellite_observation_service.extract_panchayat_satellite_features(
        panchayat_id="UP_VAR_LGD_100801",
        satellite_grid=grid,
    )
    assert result.success is True, f"Satellite feature extraction failed: {result}"
    # Source resolution ~3.8km for a ~3.5km-wide Panchayat → declared coarse for target
    assert result.resolution_diagnostic == SourceResolutionDiagnostic.SOURCE_RESOLUTION_COARSE_FOR_TARGET
    assert result.provenance.resolution_disclaimer is not None
    assert "higher resolution" in result.provenance.resolution_disclaimer


# =============================================================================
# 7. End-to-End Localized Precipitation Nowcast & Advisory Differentiation
# =============================================================================

def test_real_pilot_nowcast_and_advisory_differentiation(load_real_pilot_boundaries):
    """
    Verifies that neighbouring Panchayats with identical macro-scale NWP baseline
    receive divergent nowcasts driven by real INSAT-3D satellite observations
    (Rameshwar = cold-cloud western pixels, Jansa = warm-sky eastern pixels).
    """
    from datetime import timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()
    valid_time = (now_utc + timedelta(hours=1)).isoformat()

    grid = _sat_provider.ingest_raster_file(
        file_path=REAL_RASTER_PATH,
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    # Identical macro-scale baseline for both Panchayats
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=valid_time,
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_name="Arajiline",
    )

    # 1. Rameshwar: cold cloud pixels in western portion → high rain probability
    nc_rameshwar = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )
    assert nc_rameshwar.success is True
    assert nc_rameshwar.provenance.data_mode == "LIVE"
    assert nc_rameshwar.source_state == PrecipitationSourceState.NWP_SATELLITE
    assert nc_rameshwar.horizons["30m"].rain_probability > 0.60, (
        f"Rameshwar 30m rain probability too low: {nc_rameshwar.horizons['30m'].rain_probability:.3f}"
    )

    # 2. Jansa: warm clear-sky pixels in eastern portion → low rain probability, disagreement with baseline
    nc_jansa = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100802",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )
    assert nc_jansa.success is True
    assert nc_jansa.provenance.data_mode == "LIVE"
    assert nc_jansa.horizons["30m"].rain_probability < 0.40, (
        f"Jansa 30m rain probability too high: {nc_jansa.horizons['30m'].rain_probability:.3f}"
    )
    # Baseline says 35% rain while satellite says clear → signal disagreement
    assert nc_jansa.evidence_disagreement is True
    assert nc_jansa.overall_confidence == NowcastConfidence.LOW

    # 3. Strict LIVE mode separation — neither result should be tagged DEMO
    assert nc_rameshwar.provenance.data_mode == "LIVE"
    assert nc_jansa.provenance.data_mode == "LIVE"

    # 4. Agricultural advisories correctly differentiated
    svc = PanchayatAdvisoryNowcastService()

    adv_rameshwar = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=1,
        panchayat_name="Rameshwar Gram Panchayat",
        block_id=1,
        block_name="Arajiline",
        crop_id=1,
        crop_name="Paddy",
        forecast_date=now_utc,
        nowcast=nc_rameshwar,
    )
    assert len(adv_rameshwar) > 0, (
        "Expected rainfall-protective advisory for Rameshwar (cloudy/high-rain Panchayat)"
    )
    all_text_r = " ".join([a.action.action_text.lower() for a in adv_rameshwar])
    assert any(word in all_text_r for word in ("postpone", "defer", "hold", "withhold", "suspend")), (
        f"Expected protective action keyword, got: {all_text_r}"
    )

    adv_jansa = svc.generate_panchayat_nowcast_advisories(
        panchayat_id=2,
        panchayat_name="Jansa Gram Panchayat",
        block_id=1,
        block_name="Arajiline",
        crop_id=1,
        crop_name="Paddy",
        forecast_date=now_utc,
        nowcast=nc_jansa,
    )
    assert len(adv_jansa) > 0, (
        "Expected caution advisory for Jansa (clear sky but divergence detected)"
    )

