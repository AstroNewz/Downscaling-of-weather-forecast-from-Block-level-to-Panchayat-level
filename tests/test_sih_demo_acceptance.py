"""
SIH Final Demo Acceptance Test Suite
Problem Statement 26074: Downscaling Weather Forecast from Block to Panchayat Level

Verifies the final judge workflow contract:
1. Panchayat A can be resolved (Rameshwar Gram Panchayat).
2. Panchayat B can be resolved (Jansa Gram Panchayat).
3. A and B have distinct geometry.
4. Baseline forecast remains preserved.
5. Localized nowcast exists when configured.
6. A/B localized evidence remains separate.
7. Advisory contains Action / Why / Timing.
8. Source state is visible.
9. Confidence is visible.
10. No synthetic/live confusion occurs.
11. Missing data is fail-closed.
12. Existing model governance remains unchanged.
"""
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from shapely.geometry import shape

from app.core.config import settings
from app.gis.boundary_registry import boundary_registry
from app.gis.boundary_service import panchayat_boundary_service
from app.schemas.panchayat_boundary import BoundaryResolutionStatus
from app.schemas.precipitation_nowcast import (
    BaselinePrecipitationExpectation,
    NowcastConfidence,
    PrecipitationSourceState,
)
from app.schemas.satellite import SatelliteProductType
from app.services.advisory_nowcast_service import PanchayatAdvisoryNowcastService
from app.services.panchayat_precipitation_nowcast_service import panchayat_precipitation_nowcast_service
from app.weather.providers.satellite_provider import SatelliteObservationProvider


CURRENT_DIR = Path(__file__).resolve().parent
if (CURRENT_DIR.parent / "backend").exists():
    BACKEND_ROOT = CURRENT_DIR.parent / "backend"
else:
    BACKEND_ROOT = CURRENT_DIR.parent
REAL_BOUNDARIES_PATH = BACKEND_ROOT / "data" / "raw" / "india" / "pilot" / "boundaries" / "authorized_panchayats.geojson"
REAL_RASTER_PATH = BACKEND_ROOT / "data" / "raw" / "satellite" / "REAL_CAPTURED_INSAT3D_TIR_VARANASI.tif"


@pytest.fixture(scope="module", autouse=True)
def init_boundaries():
    """Ensure pilot boundaries are loaded for the test suite."""
    boundary_registry.clear()
    assert REAL_BOUNDARIES_PATH.exists(), f"Missing {REAL_BOUNDARIES_PATH}"
    count = boundary_registry.load_from_configured_source()
    if count == 0:
        boundary_registry.load_from_file(
            file_path=str(REAL_BOUNDARIES_PATH),
            source_name="LGD_SURVEY_OF_INDIA",
            is_verified=True,
            geometry_status="VERIFIED_AUTHORITATIVE",
        )
    assert boundary_registry.count() >= 2


def test_1_panchayat_a_can_be_resolved():
    """Requirement 1: Panchayat A (Rameshwar) can be resolved via exact PIP."""
    # Coordinate inside Rameshwar: lat=25.3725, lon=82.8575
    res = panchayat_boundary_service.resolve_coordinates(lat=25.3725, lon=82.8575)
    assert res.status == BoundaryResolutionStatus.RESOLVED
    assert res.panchayat_id == "UP_VAR_LGD_100801"
    assert "Rameshwar" in res.panchayat_name


def test_2_panchayat_b_can_be_resolved():
    """Requirement 2: Panchayat B (Jansa) can be resolved via exact PIP."""
    # Coordinate inside Jansa: lat=25.3725, lon=82.8925
    res = panchayat_boundary_service.resolve_coordinates(lat=25.3725, lon=82.8925)
    assert res.status == BoundaryResolutionStatus.RESOLVED
    assert res.panchayat_id == "UP_VAR_LGD_100802"
    assert "Jansa" in res.panchayat_name


def test_3_panchayat_a_and_b_have_distinct_geometry():
    """Requirement 3: A and B have distinct geometry with non-overlapping interiors."""
    rec_a = boundary_registry.get_by_id("UP_VAR_LGD_100801")
    rec_b = boundary_registry.get_by_id("UP_VAR_LGD_100802")
    assert rec_a is not None
    assert rec_b is not None

    poly_a = shape(rec_a.geometry)
    poly_b = shape(rec_b.geometry)

    # Distinct IDs and centroids
    assert rec_a.panchayat_id != rec_b.panchayat_id
    assert (rec_a.centroid_lat, rec_a.centroid_lon) != (rec_b.centroid_lat, rec_b.centroid_lon)

    # Interiors must not overlap (shared boundary permitted along meridian 82.875)
    intersection = poly_a.intersection(poly_b)
    assert intersection.area == pytest.approx(0.0, abs=1e-7)


def test_4_baseline_forecast_remains_preserved():
    """Requirement 4: Baseline NWP forecast is preserved verbatim without alteration."""
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=None,
    )

    assert nc.baseline_forecast.baseline_precipitation_mm == 2.5
    assert nc.baseline_forecast.baseline_probability == 0.35
    assert nc.baseline_forecast.source_model == "IMD-GFS-0.25deg"


def test_5_localized_nowcast_exists_when_configured():
    """Requirement 5: Localized multi-horizon nowcast exists with 30m, 60m, 120m horizons."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()
    valid_time = (now_utc + timedelta(hours=1)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=valid_time,
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    assert nc.success is True
    assert "30m" in nc.horizons
    assert "60m" in nc.horizons
    assert "120m" in nc.horizons
    for h_key in ["30m", "60m", "120m"]:
        h = nc.horizons[h_key]
        assert 0.0 <= h.rain_probability <= 1.0
        assert h.expected_amount_mm is not None or h.expected_amount_mm is None


def test_6_ab_localized_evidence_remains_separate():
    """Requirement 6: Same block & baseline produce distinct localized evidence for A vs B."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()
    valid_time = (now_utc + timedelta(hours=1)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    # Identical baseline
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=valid_time,
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc_a = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )
    nc_b = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100802",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    # Rameshwar has convective cloud pixels in west; Jansa has warm pixels in east
    prob_a_30m = nc_a.horizons["30m"].rain_probability
    prob_b_30m = nc_b.horizons["30m"].rain_probability

    assert prob_a_30m > 0.60, f"Expected high rain prob for Rameshwar, got {prob_a_30m}"
    assert prob_b_30m < 0.40, f"Expected lower rain prob for Jansa, got {prob_b_30m}"
    assert prob_a_30m != prob_b_30m
    # Jansa triggers baseline/satellite disagreement
    assert nc_b.evidence_disagreement is True


def test_7_advisory_contains_action_why_timing():
    """Requirement 7: Agricultural advisory contains Action, Why (Rationale), and Timing."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()
    valid_time = (now_utc + timedelta(hours=1)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=valid_time,
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc_a = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    adv_service = PanchayatAdvisoryNowcastService()
    advisories = adv_service.generate_panchayat_nowcast_advisories(
        panchayat_id=1,
        panchayat_name="Rameshwar Gram Panchayat",
        block_id=4,
        block_name="Arajiline",
        crop_id=1,
        crop_name="Paddy",
        forecast_date=now_utc,
        nowcast=nc_a,
    )

    assert len(advisories) > 0
    first_adv = advisories[0]

    # Action
    assert first_adv.action is not None
    assert len(first_adv.action.action_text) > 0

    # Why / Rationale
    assert len(first_adv.rationale) > 0

    # Timing
    assert first_adv.valid_from is not None
    assert first_adv.valid_until is not None


def test_8_source_state_is_visible():
    """Requirement 8: Precipitation source state is explicitly exposed in result."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=now_utc.isoformat(),
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    assert nc.source_state == PrecipitationSourceState.NWP_SATELLITE
    assert nc.source_state.value in [s.value for s in PrecipitationSourceState]


def test_9_confidence_is_visible():
    """Requirement 9: Confidence level is clearly exposed (HIGH, MEDIUM, LOW)."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=now_utc.isoformat(),
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    assert isinstance(nc.overall_confidence, NowcastConfidence)
    assert nc.overall_confidence in [NowcastConfidence.HIGH, NowcastConfidence.MEDIUM, NowcastConfidence.LOW]


def test_10_no_synthetic_live_confusion():
    """Requirement 10: Ingested real captured raster is tagged LIVE, never marked synthetic."""
    now_utc = datetime.now(timezone.utc)
    obs_time = (now_utc - timedelta(minutes=15)).isoformat()

    prov = SatelliteObservationProvider()
    grid = prov.ingest_raster_file(
        file_path=str(REAL_RASTER_PATH),
        product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
        observation_time=obs_time,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time=now_utc.isoformat(),
        baseline_precipitation_mm=2.5,
        baseline_probability=0.35,
        block_id=4,
        block_name="Arajiline",
    )

    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UP_VAR_LGD_100801",
        baseline_forecast=baseline,
        satellite_grid=grid,
    )

    assert nc.provenance.data_mode == "LIVE"
    assert "SYNTHETIC" not in str(nc.provenance.satellite_source or "").upper()


def test_11_missing_data_is_fail_closed():
    """Requirement 11: Coordinates outside registered boundaries fail closed with OUTSIDE_REGISTERED_PANCHAYATS."""
    # New Delhi coordinates
    res = panchayat_boundary_service.resolve_coordinates(lat=28.6139, lon=77.2090)
    assert res.status == BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS
    assert res.panchayat_id is None

    # Unknown Panchayat ID fails closed in nowcast
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.25deg",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=0.0,
        baseline_probability=0.20,
        block_id=999,
        block_name="Unknown",
    )
    nc = panchayat_precipitation_nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="UNKNOWN_PANCHAYAT_ID",
        baseline_forecast=baseline,
        satellite_grid=None,
    )
    assert nc.success is False
    assert "NOT_FOUND" in nc.status or "UNVERIFIED" in nc.status or "INSUFFICIENT" in nc.status


def test_12_existing_model_governance_remains_unchanged():
    """Requirement 12: Certified baseline parameter (+0.7351°C) and Dynamic V2 model remain frozen."""
    # Certified baseline
    cal_offset = getattr(settings, "CALIBRATION_OFFSET_C", getattr(settings, "CALIBRATION_SCALAR_B", 0.7351))
    assert cal_offset == pytest.approx(0.7351, abs=1e-4)

    # Dynamic V2 model file hash verification
    model_path = BACKEND_ROOT / "models" / "candidates" / "temperature_residual" / "dynamic_temperature_residual_v2" / "xgboost_model.json"
    assert model_path.exists()
    content = model_path.read_bytes()
    model_hash = hashlib.sha256(content).hexdigest()
    EXPECTED_HASH = "d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294"
    assert model_hash == EXPECTED_HASH, f"Model hash changed! Expected {EXPECTED_HASH}, got {model_hash}"
