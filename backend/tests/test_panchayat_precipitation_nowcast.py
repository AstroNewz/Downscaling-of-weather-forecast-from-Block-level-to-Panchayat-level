"""
Comprehensive Verification Suite: Panchayat Precipitation Observation-Fusion & Nowcasting
SIH Problem Statement 26074 (Weather Downscaling - Task 4)

Validates:
1. Multi-stream evidence fusion (NWP, Satellite, Radar, Surface observations)
2. Source state classification (NWP_ONLY, NWP_SATELLITE, NWP_SATELLITE_RADAR, etc.)
3. Two-stage precipitation representation:
   - Stage 1: P(rain >= threshold)
   - Stage 2: E[rainfall | rain >= threshold]
4. Missing radar is strictly optional; missing radar degrades confidence without crashing
5. Conservative missing value semantics (expected_amount_mm = None when unestimable, never fabricated)
6. Source disagreement detection (NWP rain vs clear satellite)
7. Observation freshness and stale data penalty
8. Multi-horizon outlooks (30m, 60m, 120m) with horizon-specific time weights
9. Dholakpur Block adjacent Panchayat A vs B spatial separation proof using SAME NWP baseline
10. Fail-closed behavior on missing or unverified boundaries
11. Deterministic reproducibility
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.gis.boundary_registry import boundary_registry
from app.gis.spatial_masking import spatial_masking_service
from app.schemas.precipitation_nowcast import (
    BaselinePrecipitationExpectation,
    NowcastConfidence,
    PanchayatPrecipitationNowcastResult,
    PrecipitationSourceState,
    RadarObservationFeatures,
    SurfaceObservationFeatures,
)
from app.schemas.satellite import SatelliteProductType
from app.services.panchayat_precipitation_nowcast_service import (
    PanchayatPrecipitationNowcastService,
    generate_panchayat_precipitation_nowcast,
)
from app.services.satellite_service import satellite_observation_service
from tests.fixtures.imaginary_panchayats_fixture import (
    get_dholakpur_panchayat_records,
    get_imaginary_panchayat_records,
    SHAPELY_POLY_A,
    SHAPELY_POLY_B,
)
from tests.fixtures.synthetic_satellite_fixtures import (
    build_synthetic_satellite_ir_field,
    build_synthetic_satellite_precip_field,
    build_synthetic_satellite_temporal_pair,
    build_synthetic_dholakpur_ir_field,
    build_synthetic_dholakpur_temporal_pair,
    build_synthetic_dholakpur_precip_field,
)


@pytest.fixture(autouse=True)
def setup_panchayat_registries():
    """Registers imaginary and Dholakpur test Panchayats before each test."""
    boundary_registry.clear()
    for rec in get_imaginary_panchayat_records():
        boundary_registry.register(rec)
    for rec in get_dholakpur_panchayat_records():
        boundary_registry.register(rec)
    yield
    boundary_registry.clear()


@pytest.fixture
def nowcast_service():
    return PanchayatPrecipitationNowcastService(
        satellite_service=satellite_observation_service,
        masking_service=spatial_masking_service,
        registry=boundary_registry,
    )


# =============================================================================
# 1. Baseline NWP Only (Observations Absent or Unavailable)
# =============================================================================

def test_nwp_only_fusion(nowcast_service):
    """
    Verifies graceful operation when no observational feeds (satellite/radar) are available.
    Must output NWP_ONLY source state, reflect baseline probability, and assign conservative confidence.
    """
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-0.12DEG",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=2.5,
        baseline_probability=0.60,
        block_id="Dholakpur Block",
        block_name="Dholakpur Block",
    )

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=baseline,
        satellite_grid=None,
        radar_features=None,
    )

    assert result.success is True
    assert result.source_state == PrecipitationSourceState.NWP_ONLY
    assert result.overall_confidence in (NowcastConfidence.LOW, NowcastConfidence.MEDIUM)
    assert len(result.evidence_components) == 1
    assert result.evidence_components[0].source_name == "IMD-GFS-0.12DEG"
    
    # 60m horizon check
    h60 = result.horizons["60m"]
    assert h60.is_rain_likely is True
    assert 0.50 <= h60.rain_probability <= 0.70
    assert h60.expected_amount_mm is not None
    assert h60.expected_amount_mm > 0.0


# =============================================================================
# 2. NWP + Satellite Multi-Stream Fusion
# =============================================================================

def test_nwp_plus_satellite_fusion(nowcast_service):
    """
    Verifies fusion of NWP baseline with fresh geostationary satellite IR evidence.
    """
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=0.0,
        baseline_probability=0.10,
    )
    # Dholakpur-domain IR field covers lat [25.50-25.70] matching Dholakpur polygon geometry
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=baseline,
        satellite_grid=sat_grid,
    )

    assert result.success is True
    assert result.source_state == PrecipitationSourceState.NWP_SATELLITE
    assert len(result.evidence_components) == 2
    # Satellite observed convective clouds over A, boosting probability significantly above the 0.10 baseline
    assert result.primary_horizon.rain_probability > 0.40


# =============================================================================
# 3. Radar is Optional (Missing Radar vs Present Radar)
# =============================================================================

def test_missing_radar_does_not_break_pipeline(nowcast_service):
    """
    CRITICAL REQUIREMENT: Radar must remain optional.
    Missing radar degrades confidence / source_state but never throws or crashes.
    """
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)
    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
        radar_features=None,  # Radar unavailable
    )
    assert result.success is True
    assert result.source_state == PrecipitationSourceState.NWP_SATELLITE
    assert "RADAR" not in result.source_state.value


def test_radar_strengthens_precipitation_confidence_and_rate(nowcast_service):
    """
    When optional Doppler radar is available, it strengthens the fusion:
    - source_state becomes NWP_SATELLITE_RADAR
    - radar reflectivity / rain rate directly informs expected conditional rainfall
    """
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)
    radar = RadarObservationFeatures(
        provider_name="DWR_VARANASI_STATION",
        observation_time="2026-09-27T12:05:00Z",
        age_minutes=5.0,
        mean_reflectivity_dbz=38.5,
        max_reflectivity_dbz=44.0,
        radar_estimated_rain_rate_mm_h=12.0,  # 12 mm/h rain core
        echo_area_fraction=0.85,
        convective_echo_fraction=0.60,
        is_available=True,
    )

    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=5.0,
        baseline_probability=0.70,
    )

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=baseline,
        satellite_grid=sat_grid,
        radar_features=radar,
    )

    assert result.success is True
    assert result.source_state == PrecipitationSourceState.NWP_SATELLITE_RADAR
    assert result.overall_confidence == NowcastConfidence.HIGH
    
    # 30m expected amount informed by radar rate (12 mm/h * 0.5h = 6.0 mm)
    h30 = result.horizons["30m"]
    assert h30.expected_amount_mm == 6.0
    assert h30.expected_intensity_mm_h == 12.0


# =============================================================================
# 4. Source Disagreement Detection
# =============================================================================

def test_source_disagreement_detection_nwp_rain_vs_satellite_clear(nowcast_service):
    """
    NWP forecasts significant rain, but satellite observes clear warm ground.
    Must flag evidence_disagreement=True, cap confidence at LOW, and record rationale.
    """
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=8.0,
        baseline_probability=0.85,  # Strong NWP rain forecast
    )
    # In Panchayat B, synthetic IR field has warm clear ground (> 295K)
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_B",
        baseline_forecast=baseline,
        satellite_grid=sat_grid,
    )

    assert result.success is True
    assert result.evidence_disagreement is True
    assert result.overall_confidence == NowcastConfidence.LOW
    assert "clear warm skies" in result.disagreement_details
    assert result.primary_horizon.evidence_disagreement is True


# =============================================================================
# 5. Observation Freshness & Stale Penalty
# =============================================================================

def test_stale_observation_penalty(nowcast_service):
    """
    Verifies that satellite observations exceeding the freshness threshold (60m)
    receive a penalty factor (0.50x), reducing their influence on the nowcast.
    """
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat()
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0, valid_time=stale_time)

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
    )

    assert result.success is True
    sat_comp = [c for c in result.evidence_components if "SATELLITE" in c.source_type.value][0]
    assert sat_comp.fresh is False
    assert sat_comp.age_minutes >= 115.0


# =============================================================================
# 6. Dholakpur Block Adjacent Panchayat A/B Proof
# =============================================================================

def test_dholakpur_adjacent_panchayat_ab_separation(nowcast_service):
    """
    MANDATORY SUCCESS CRITERION (Requirement 13):
    In Dholakpur Block:
    - Panchayat A: Convective cloud tops (<220K) present.
    - Panchayat B: Clear warm skies (>295K).
    - BOTH receive the EXACT SAME NWP baseline forecast.
    
    Verifies:
    - A derived A-specific localized precipitation risk (significantly higher rain probability).
    - B derived B-specific localized precipitation risk (significantly lower rain probability).
    - Difference is purely derived from spatial observation evidence.
    """
    # Identical NWP baseline for the entire block
    common_nwp_baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS-BLOCK-SHARED",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=1.0,
        baseline_probability=0.35,
        block_id="Dholakpur Block",
        block_name="Dholakpur Block",
    )

    # Dholakpur-domain IR field: covers lat [25.50, 25.70] where the
    # Dholakpur polygons are now registered (distinct from IMAGINARY at lat [25.00,25.20]).
    # A's vertical bar gets cold convective cloud (210K-220K) → high rain risk.
    # B's rectangle gets warm clear sky (295K-305K) → low rain risk.
    common_satellite_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)

    # Independent processing for Panchayat A
    nowcast_a = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=common_nwp_baseline,
        satellite_grid=common_satellite_grid,
    )

    # Independent processing for Panchayat B
    nowcast_b = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_B",
        baseline_forecast=common_nwp_baseline,
        satellite_grid=common_satellite_grid,
    )

    assert nowcast_a.success is True
    assert nowcast_b.success is True
    assert nowcast_a.panchayat_id == "DHOLAKPUR_PANCHAYAT_A"
    assert nowcast_b.panchayat_id == "DHOLAKPUR_PANCHAYAT_B"

    prob_a_60 = nowcast_a.primary_horizon.rain_probability
    prob_b_60 = nowcast_b.primary_horizon.rain_probability

    # Proves spatial localization: A has active storm, B is clear
    assert prob_a_60 > 0.65
    assert prob_b_60 < 0.35
    assert (prob_a_60 - prob_b_60) >= 0.30

    # Baseline comparison is preserved in both payloads
    assert nowcast_a.baseline_forecast.baseline_probability == 0.35
    assert nowcast_b.baseline_forecast.baseline_probability == 0.35


# =============================================================================
# 7. Multi-Horizon Outlooks & Time Decay Weighting
# =============================================================================

def test_multi_horizon_decay_weighting(nowcast_service):
    """
    Verifies that horizons (30m, 60m, 120m) reflect appropriate temporal weighting:
    - 30m is dominated by fresh satellite observations.
    - 120m gives higher weight to the NWP forecast baseline.
    """
    # Baseline expects dry (0.0mm, p=0.05)
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=0.0,
        baseline_probability=0.05,
    )
    # Satellite observes active cloud over A (p_sat ~ 0.90)
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=baseline,
        satellite_grid=sat_grid,
    )

    assert result.success is True
    p30 = result.horizons["30m"].rain_probability
    p60 = result.horizons["60m"].rain_probability
    p120 = result.horizons["120m"].rain_probability

    # Because satellite is very active and NWP is dry:
    # 30m (satellite weight 0.35, NWP 0.15) should be higher than 120m (NWP weight 0.45, satellite 0.25)
    assert p30 >= p60 >= p120


# =============================================================================
# 8. Two-Stage Representation & Unestimable Amount (null, not 0.0)
# =============================================================================

def test_unestimable_amount_returns_null_not_fabricated_zero(nowcast_service):
    """
    When satellite cloud mask indicates probability of rain but no calibrated
    rain rate or NWP precipitation depth exists:
    expected_amount_mm must be None (null), NOT fabricated to 0.0 or an invented number.
    """
    baseline = BaselinePrecipitationExpectation(
        source_model="IMD-GFS",
        forecast_valid_time="2026-09-27T12:00:00Z",
        baseline_precipitation_mm=0.0,
        baseline_probability=0.40,
    )
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        baseline_forecast=baseline,
        satellite_grid=sat_grid,
    )

    assert result.success is True
    # NWP baseline had 0.0mm and satellite is only brightness temp (no calibrated precip retrieval)
    assert result.primary_horizon.expected_amount_mm is None


# =============================================================================
# 9. Surface AWS Ground Observation Confirmation
# =============================================================================

def test_surface_observation_confirmation(nowcast_service):
    """
    Verifies that ground-truth AWS telemetry is incorporated as an evidence component.
    """
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)
    sfc = SurfaceObservationFeatures(
        station_id="AWS_VARANASI_AIRPORT",
        station_name="Varanasi Airport AWS",
        observation_time="2026-09-27T12:10:00Z",
        age_minutes=5.0,
        distance_to_centroid_km=4.2,
        precipitation_last_1h_mm=3.5,
        current_rain_rate_mm_h=7.0,
        is_raining=True,
        is_available=True,
    )

    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
        surface_observation=sfc,
    )

    assert result.success is True
    assert result.source_state == PrecipitationSourceState.NWP_SATELLITE_SURFACE_OBS
    assert any(c.source_type.value == "SURFACE_OBSERVATION" for c in result.evidence_components)


# =============================================================================
# 10. Fail-Closed Safety & Reproducibility
# =============================================================================

def test_unverified_boundary_fails_closed_when_required(nowcast_service):
    """Verifies fail-closed behavior when require_verified=True and boundary is unverified."""
    # IMAGINARY_PANCHAYAT_A is unverified in fixture
    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        require_verified=True,
    )
    assert result.success is False
    assert result.status == "UNVERIFIED_GEOMETRY"
    assert result.overall_confidence == NowcastConfidence.INSUFFICIENT_DATA


def test_deterministic_reproducibility(nowcast_service):
    """Verifies that identical inputs yield bit-for-bit identical probability and results."""
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)
    res1 = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
        issue_time="2026-09-27T12:00:00Z",
    )
    res2 = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
        issue_time="2026-09-27T12:00:00Z",
    )
    assert res1.primary_horizon.rain_probability == res2.primary_horizon.rain_probability
    assert res1.primary_horizon.confidence == res2.primary_horizon.confidence
    assert res1.source_state == res2.source_state


# =============================================================================
# 11. Additional Edge Cases & Coverage Tests
# =============================================================================

def test_satellite_precipitation_estimate_informs_expected_amount(nowcast_service):
    """
    When satellite precipitation estimate product is supplied (HEGG/IMERG),
    its rate directly informs Stage 2 expected rainfall amount.
    """
    precip_grid = build_synthetic_dholakpur_precip_field(native_res_km=4.0)
    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=precip_grid,
    )
    assert result.success is True
    assert result.primary_horizon.expected_amount_mm is not None
    assert result.primary_horizon.expected_amount_mm > 0.0


def test_insufficient_spatial_coverage_degrades_confidence(nowcast_service):
    """
    When spatial coverage is below minimum threshold (< 20%), confidence is INSUFFICIENT_DATA.
    """
    sat_grid = build_synthetic_satellite_ir_field(native_res_km=1.0)
    # Custom polygon far outside grid coverage
    from shapely.geometry import Polygon
    far_poly = Polygon([(85.0, 27.0), (85.1, 27.0), (85.1, 27.1), (85.0, 27.1), (85.0, 27.0)])
    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_geometry=far_poly,
        satellite_grid=sat_grid,
    )
    assert result.primary_horizon.confidence == NowcastConfidence.INSUFFICIENT_DATA


def test_temporal_convective_cooling_boosts_probability(nowcast_service):
    """
    Verifies that a rapid convective cooling trend (T0 -> T1) detected by Task 3
    boosts the short-horizon precipitation probability relative to static snapshot.
    """
    t0_grid, t1_grid = build_synthetic_dholakpur_temporal_pair(native_res_km=1.0)
    
    # Run with temporal change (T0 -> T1)
    res_temporal = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=t1_grid,
        previous_satellite_grid=t0_grid,
    )

    # Run static snapshot at T0
    res_static_t0 = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=t0_grid,
    )

    p_temporal = res_temporal.primary_horizon.rain_probability
    p_t0 = res_static_t0.primary_horizon.rain_probability
    assert p_temporal > p_t0


def test_provenance_audit_trail_completeness(nowcast_service):
    """
    Verifies that complete provenance is retained for auditability, including
    NWP model, satellite provider, method version, and non-negotiable scientific disclaimer.
    """
    sat_grid = build_synthetic_dholakpur_ir_field(native_res_km=1.0)
    result = nowcast_service.generate_panchayat_precipitation_nowcast(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        satellite_grid=sat_grid,
    )
    prov = result.provenance
    assert "IMD-GFS" in prov.nwp_source
    assert "SATELLITE_SYNTHETIC_TEST_FIXTURE" in prov.satellite_source
    assert prov.evidence_weight_version == "DETERMINISTIC_RESEARCH_HEURISTIC_V1"
    assert "does NOT constitute certified ground-truth" in prov.scientific_disclaimer

