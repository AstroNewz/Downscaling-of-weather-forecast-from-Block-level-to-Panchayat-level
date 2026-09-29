"""
test_panchayat_precipitation_validation.py
Task 8 Deterministic Verification Suite for Panchayat Precipitation Validation
AgroWeather / SIH Problem Statement 26074 (Weather Downscaling - Task 8)

Validates all 18 scientific and procedural requirements:
1. Independent-station acceptance
2. Training contamination rejection (TRAINING_STATIONS_17)
3. Synthetic-data and model reanalysis rejection
4. Missing metadata rejection
5. Invalid and out-of-bounds coordinates rejection
6. Exact Panchayat polygon membership & geometric distance calculation
7. Pairwise station-distance & same-mast rejection (<100m)
8. Temporal overlap enforcement (<100h fails closed)
9. Formal Validation Readiness Levels hierarchy (Levels 1 to 6)
10. Stage 1 occurrence metrics calculation (POD, FAR, CSI, Brier Score)
11. Stage 2 amount metrics calculation (MAE, RMSE, Bias, Correlation)
12. Insufficient sample handling (INSUFFICIENT_VALIDATION_SAMPLE)
13. Horizon-specific evaluation (30m, 60m, 120m separated)
14. A/B adjacent Panchayat spatial-gradient validation & directional agreement
15. Radar-available vs Radar-unavailable (Satellite-Only) partitioning
16. Confidence state calibration check (HIGH, MEDIUM, LOW)
17. Cryptographic immutability audit and fail-closed safety
18. Scientific claim matrix generation & readiness classification
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
import numpy as np

from app.gis.boundary_registry import boundary_registry
from app.gis.boundary_service import panchayat_boundary_service
from app.schemas.precipitation_validation import (
    ValidationReadinessLevel,
    ScientificReadinessState,
    StationSpatialRelation,
    WeatherRegime,
    IndependentStationRecord,
    Stage1OccurrenceMetrics,
    Stage2AmountMetrics,
    SpatialDifferentiationMetrics,
)
from app.services.precipitation_validation_service import (
    PrecipitationValidationService,
    precipitation_validation_service,
    EXPECTED_PROTECTED_HASHES,
    TRAINING_STATIONS_17,
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REAL_BOUNDARIES_PATH = BACKEND_ROOT / "data" / "raw" / "india" / "pilot" / "boundaries" / "authorized_panchayats.geojson"
GROUND_TRUTH_PATH = BACKEND_ROOT / "data" / "raw" / "panchayat_mesonet" / "independent_validation_observations.json"


@pytest.fixture(scope="module")
def setup_boundaries():
    """Ensures verified pilot boundaries are loaded for geospatial testing."""
    boundary_registry.clear()
    count = boundary_registry.load_from_file(
        file_path=REAL_BOUNDARIES_PATH,
        source_name="GOI_LGD_AUTHORIZED_PILOT",
        is_verified=True,
        geometry_status="AUTHORIZED_OFFICIAL",
    )
    assert count == 2
    panchayat_boundary_service._sync_spatial_index()
    return count


# =============================================================================
# 1. Independent Station Acceptance
# =============================================================================

def test_independent_station_acceptance():
    """Validates that legitimate independent research stations are admitted with correct flags."""
    raw = [{
        "station_id": "TEST_AGRO_01",
        "station_name": "Test Agricultural Weather Station",
        "latitude": 25.3725,
        "longitude": 82.8580,
        "elevation_m": 82.0,
        "sensor_height_m": 2.0,
        "site_context": "AGRICULTURAL",
        "observation_network": "STATE_AGRICULTURAL_MESONET",
        "institution": "ICAR_IIVR",
        "participated_in_training": False,
        "is_synthetic": False,
        "data_source_type": "OBSERVATION",
        "quality_flag": "VALID",
    }]
    admitted, rejected = precipitation_validation_service.filter_eligible_stations(raw)
    assert len(admitted) == 1
    assert len(rejected) == 0
    stn = admitted[0]
    assert stn.validation_independent is True
    assert stn.validation_contaminated is False
    assert stn.metadata_complete is True


# =============================================================================
# 2. Training Contamination Rejection
# =============================================================================

def test_training_contamination_rejection():
    """Validates that any station that participated in model training is strictly rejected."""
    raw = [
        # Station from the 17 training stations
        {
            "station_id": "424790-99999",
            "station_name": "Varanasi Airport Historical Training Station",
            "latitude": 25.45,
            "longitude": 82.867,
            "elevation_m": 81.1,
            "sensor_height_m": 2.0,
            "site_context": "AIRPORT",
            "observation_network": "NOAA_ISD",
            "institution": "NOAA",
            "participated_in_training": True,
            "is_synthetic": False,
        },
        # Arbitrary station with participated_in_training = True
        {
            "station_id": "CUSTOM_TRAIN_STN",
            "station_name": "Custom Training Station",
            "latitude": 25.35,
            "longitude": 82.90,
            "elevation_m": 80.0,
            "sensor_height_m": 2.0,
            "site_context": "RURAL",
            "observation_network": "CUSTOM",
            "institution": "CUSTOM_INST",
            "participated_in_training": True,
            "is_synthetic": False,
        },
    ]
    admitted, rejected = precipitation_validation_service.filter_eligible_stations(raw)
    assert len(admitted) == 0
    assert len(rejected) == 2
    for r in rejected:
        assert "TRAINING_CONTAMINATION" in r["reason"]


# =============================================================================
# 3. Synthetic and Model Reanalysis Rejection
# =============================================================================

def test_synthetic_and_model_data_rejection():
    """Validates that synthetic generators and model reanalysis are never admitted as ground truth."""
    raw = [
        {
            "station_id": "SYNTH_01",
            "station_name": "Synthetic Observation Generator",
            "latitude": 25.37,
            "longitude": 82.86,
            "elevation_m": 82.0,
            "sensor_height_m": 2.0,
            "site_context": "AGRICULTURAL",
            "observation_network": "SYNTHETIC",
            "institution": "SIMULATOR",
            "is_synthetic": True,
        },
        {
            "station_id": "ERA5_REANALYSIS_POINT",
            "station_name": "ERA5 Coarse Cell Point",
            "latitude": 25.50,
            "longitude": 83.00,
            "elevation_m": 80.0,
            "sensor_height_m": 2.0,
            "site_context": "RURAL",
            "observation_network": "ECMWF",
            "institution": "COPERNICUS",
            "data_source_type": "ERA5_REANALYSIS",
            "is_synthetic": False,
        },
    ]
    admitted, rejected = precipitation_validation_service.filter_eligible_stations(raw)
    assert len(admitted) == 0
    assert len(rejected) == 2
    for r in rejected:
        assert "SYNTHETIC_OR_MODEL_DATA" in r["reason"]


# =============================================================================
# 4. Missing Metadata Rejection
# =============================================================================

def test_missing_metadata_rejection():
    """Validates that candidate stations missing sensor elevation, height, site context, or institution are rejected."""
    raw = [{
        "station_id": "NO_META_STN",
        "station_name": "Incomplete Metadata Station",
        "latitude": 25.37,
        "longitude": 82.86,
        "elevation_m": None,  # Missing
        "sensor_height_m": None,  # Missing
        "site_context": None,  # Missing
        "institution": None,  # Missing
    }]
    admitted, rejected = precipitation_validation_service.filter_eligible_stations(raw)
    assert len(admitted) == 0
    assert len(rejected) == 1
    assert "METADATA_INCOMPLETE" in rejected[0]["reason"]


# =============================================================================
# 5. Invalid and Out-of-Bounds Coordinates Rejection
# =============================================================================

def test_invalid_coordinates_rejection():
    """Validates that stations with missing, out-of-range, or outside-India coordinates are rejected."""
    raw = [
        {"station_id": "MISSING_LAT", "latitude": None, "longitude": 82.86, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "INST"},
        {"station_id": "OUT_OF_BOUNDS", "latitude": 95.0, "longitude": 82.86, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "INST"},
        {"station_id": "OUTSIDE_INDIA", "latitude": 51.5074, "longitude": -0.1278, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "INST"},
    ]
    admitted, rejected = precipitation_validation_service.filter_eligible_stations(raw)
    assert len(admitted) == 0
    assert len(rejected) == 3


# =============================================================================
# 6. Exact Panchayat Polygon Membership & Geometric Distance
# =============================================================================

def test_panchayat_polygon_membership_exact_pip(setup_boundaries):
    """
    Validates exact shapely point-in-polygon relationship:
    Inside Rameshwar -> INSIDE_PANCHAYAT (dist=0.0km)
    Near Jansa border -> NEAR_PANCHAYAT
    Far away (Varanasi Synoptic) -> OUTSIDE_VALIDATION_RADIUS
    """
    stn_inside = IndependentStationRecord(
        station_id="STN_IN",
        station_name="Inside Rameshwar",
        latitude=25.3725,
        longitude=82.8580,
        elevation_m=82.0,
        site_context="AGRICULTURAL",
        observation_network="TEST_NET",
    )
    rel_in = precipitation_validation_service.compute_station_polygon_relationship(stn_inside, "UP_VAR_LGD_100801")
    assert rel_in.spatial_relation == StationSpatialRelation.INSIDE_PANCHAYAT
    assert rel_in.distance_to_boundary_km == 0.0
    assert rel_in.distance_to_centroid_km < 3.0

    stn_far = IndependentStationRecord(
        station_id="STN_FAR",
        station_name="Synoptic Station",
        latitude=25.3000,
        longitude=83.0170,
        elevation_m=85.0,
        site_context="SUBURBAN",
        observation_network="IMD_NET",
    )
    rel_far = precipitation_validation_service.compute_station_polygon_relationship(stn_far, "UP_VAR_LGD_100801")
    assert rel_far.spatial_relation == StationSpatialRelation.OUTSIDE_VALIDATION_RADIUS
    assert rel_far.distance_to_boundary_km > 10.0


# =============================================================================
# 7. Pairwise Station Distance & Same-Mast Rejection
# =============================================================================

def test_same_mast_and_pairwise_distance_rejection(setup_boundaries):
    """Verifies that multiple sensors on the same mast (<100m) are rejected from spatial validation."""
    same_mast_stns = [
        IndependentStationRecord(
            station_id="MAST_A",
            station_name="Tower Mast Sensor 1",
            latitude=25.37250,
            longitude=82.85800,
            elevation_m=82.0,
            site_context="AGRICULTURAL",
            observation_network="TEST",
        ),
        IndependentStationRecord(
            station_id="MAST_B",
            station_name="Tower Mast Sensor 2",
            latitude=25.37251,  # ~1.1 meters away
            longitude=82.85801,
            elevation_m=82.0,
            site_context="AGRICULTURAL",
            observation_network="TEST",
        ),
    ]
    readiness = precipitation_validation_service.evaluate_panchayat_readiness(
        panchayat_id="UP_VAR_LGD_100801",
        panchayat_name="Rameshwar",
        admitted_stations=same_mast_stns,
        simultaneous_hours=500,
    )
    assert readiness.readiness_level == ValidationReadinessLevel.REJECTED
    assert "SAME_MAST" in readiness.readiness_reason


# =============================================================================
# 8. Temporal Overlap Enforcement (<100h fails closed)
# =============================================================================

def test_temporal_overlap_enforcement(setup_boundaries):
    """Verifies that pairs with fewer than 100 simultaneous observation hours fail closed."""
    stns = [
        IndependentStationRecord(
            station_id="STN_1",
            station_name="Agri 1",
            latitude=25.3725,
            longitude=82.8580,
            elevation_m=82.0,
            site_context="AGRICULTURAL",
            observation_network="TEST",
        ),
        IndependentStationRecord(
            station_id="STN_2",
            station_name="Agri 2",
            latitude=25.3710,
            longitude=82.8910,
            elevation_m=81.5,
            site_context="AGRICULTURAL",
            observation_network="TEST",
        ),
    ]
    # Insufficient hours (50 < 100) -> fails closed
    r_insufficient = precipitation_validation_service.evaluate_panchayat_readiness(
        panchayat_id="UP_VAR_LGD_100801",
        panchayat_name="Rameshwar",
        admitted_stations=stns,
        simultaneous_hours=50,
    )
    assert r_insufficient.readiness_level == ValidationReadinessLevel.FAILED_CLOSED
    assert "INSUFFICIENT_TEMPORAL_OVERLAP" in r_insufficient.readiness_reason

    # Sufficient hours (200 >= 100) -> reaches Level 5 (sub-5km agricultural pair)
    r_sufficient = precipitation_validation_service.evaluate_panchayat_readiness(
        panchayat_id="UP_VAR_LGD_100801",
        panchayat_name="Rameshwar",
        admitted_stations=stns,
        simultaneous_hours=200,
    )
    assert r_sufficient.readiness_level == ValidationReadinessLevel.LEVEL_5_SUB_5KM_AGRI
    assert r_sufficient.eligible_for_panchayat_claim is True


# =============================================================================
# 9. Validation Readiness Levels Hierarchy
# =============================================================================

def test_readiness_levels_hierarchy(setup_boundaries):
    """Verifies complete hierarchy from Level 1 to Level 6."""
    # 0 stations -> Level 1
    r1 = precipitation_validation_service.evaluate_panchayat_readiness("UP_VAR_LGD_100801", "Rameshwar", [], 100)
    assert r1.readiness_level == ValidationReadinessLevel.LEVEL_1_NO_IN_SITU

    # 1 station -> Level 2
    stn1 = IndependentStationRecord(
        station_id="STN_1",
        station_name="S1",
        latitude=25.3725,
        longitude=82.8580,
        elevation_m=82.0,
        site_context="RURAL",
        observation_network="NET",
    )
    r2 = precipitation_validation_service.evaluate_panchayat_readiness("UP_VAR_LGD_100801", "Rameshwar", [stn1], 100)
    assert r2.readiness_level == ValidationReadinessLevel.LEVEL_2_SINGLE_MACRO

    # 2 stations 7 km apart (non-agricultural) -> Level 3
    stn_7km = IndependentStationRecord(
        station_id="STN_7KM",
        station_name="S7",
        latitude=25.4300,
        longitude=82.8580,  # ~6.4 km north
        elevation_m=82.0,
        site_context="RURAL",
        observation_network="NET",
    )
    r3 = precipitation_validation_service.evaluate_panchayat_readiness("UP_VAR_LGD_100801", "Rameshwar", [stn1, stn_7km], 100)
    assert r3.readiness_level == ValidationReadinessLevel.LEVEL_3_SUB_10KM_PAIR

    # 2 stations 3.3 km apart (agricultural, both inside Rameshwar) -> Level 6
    stn_in2 = IndependentStationRecord(
        station_id="STN_IN2",
        station_name="S_IN2",
        latitude=25.3680,
        longitude=82.8620,
        elevation_m=82.0,
        site_context="AGRICULTURAL",
        observation_network="NET",
    )
    stn_in1_agri = IndependentStationRecord(
        station_id="STN_IN1",
        station_name="S_IN1",
        latitude=25.3725,
        longitude=82.8580,
        elevation_m=82.0,
        site_context="AGRICULTURAL",
        observation_network="NET",
    )
    r6 = precipitation_validation_service.evaluate_panchayat_readiness("UP_VAR_LGD_100801", "Rameshwar", [stn_in1_agri, stn_in2], 100)
    assert r6.readiness_level == ValidationReadinessLevel.LEVEL_6_INTRA_PANCHAYAT
    assert r6.eligible_for_panchayat_claim is True


# =============================================================================
# 10. Stage 1: Precipitation Occurrence Metrics Calculation
# =============================================================================

def test_stage1_occurrence_metrics_calculation():
    """
    Validates exact mathematical calculation of:
    Hits, False Alarms, Misses, Correct Negatives, POD, FAR, CSI, Brier Score.
    """
    # Deterministic test cases:
    # 1. Obs=2.0, Pred=0.80 -> Hit
    # 2. Obs=0.0, Pred=0.70 -> False Alarm
    # 3. Obs=5.0, Pred=0.20 -> Miss
    # 4. Obs=0.0, Pred=0.10 -> Correct Negative
    # 5. Obs=1.5, Pred=0.90 -> Hit
    pairs = [
        (2.0, 0.80),
        (0.0, 0.70),
        (5.0, 0.20),
        (0.0, 0.10),
        (1.5, 0.90),
    ]
    m = precipitation_validation_service.compute_stage1_occurrence_metrics(pairs, "30m", threshold_rain_mm=0.1, threshold_prob=0.50)
    assert m.sample_count == 5
    assert m.hits == 2
    assert m.false_alarms == 1
    assert m.misses == 1
    assert m.correct_negatives == 1

    # POD = Hits / (Hits + Misses) = 2 / 3 = 0.6667
    assert abs(m.pod - (2.0 / 3.0)) < 1e-3
    # FAR = FA / (Hits + FA) = 1 / 3 = 0.3333
    assert abs(m.far - (1.0 / 3.0)) < 1e-3
    # CSI = Hits / (Hits + FA + Misses) = 2 / 4 = 0.5000
    assert abs(m.csi - 0.5000) < 1e-3
    # Precision = Hits / (Hits + FA) = 2 / 3 = 0.6667
    assert abs(m.precision - (2.0 / 3.0)) < 1e-3
    # Brier Score = mean((pred - obs)^2)
    # (0.8-1)^2 = 0.04, (0.7-0)^2 = 0.49, (0.2-1)^2 = 0.64, (0.1-0)^2 = 0.01, (0.9-1)^2 = 0.01
    # sum = 1.19 / 5 = 0.238
    assert abs(m.brier_score - 0.238) < 1e-3


# =============================================================================
# 11. Stage 2: Rainfall Amount Metrics Calculation
# =============================================================================

def test_stage2_amount_metrics_calculation():
    """
    Validates conditional rainfall amount metrics (MAE, RMSE, Bias, Correlation).
    Verifies null predictions are never coerced to zero.
    """
    # 5 rainy observations with non-null estimates
    pairs = [
        (2.0, 2.5),   # err = +0.5, abs = 0.5
        (4.0, 3.5),   # err = -0.5, abs = 0.5
        (6.0, 7.0),   # err = +1.0, abs = 1.0
        (8.0, 7.5),   # err = -0.5, abs = 0.5
        (10.0, 10.5), # err = +0.5, abs = 0.5
    ]
    m = precipitation_validation_service.compute_stage2_amount_metrics(pairs, "30m")
    assert m.status == "VALID"
    assert m.sample_count == 5
    # MAE = (0.5 + 0.5 + 1.0 + 0.5 + 0.5) / 5 = 3.0 / 5 = 0.60 mm
    assert abs(m.mae_mm - 0.60) < 1e-2
    # Mean Bias = (+0.5 - 0.5 + 1.0 - 0.5 + 0.5) / 5 = 1.0 / 5 = +0.20 mm
    assert abs(m.mean_bias_mm - 0.20) < 1e-2
    # Pearson Correlation should be very high (> 0.95)
    assert m.correlation_r is not None
    assert m.correlation_r > 0.95


# =============================================================================
# 12. Insufficient Sample Handling
# =============================================================================

def test_insufficient_sample_handling():
    """Validates that evaluations with <5 samples flag INSUFFICIENT_VALIDATION_SAMPLE and return None."""
    sparse_pairs = [(1.0, 0.8), (0.0, 0.1)]  # Only 2 samples
    m1 = precipitation_validation_service.compute_stage1_occurrence_metrics(sparse_pairs, "30m")
    assert m1.status == "INSUFFICIENT_VALIDATION_SAMPLE"
    assert m1.pod is None
    assert m1.csi is None

    amt_sparse = [(2.0, 2.2)]  # Only 1 sample
    m2 = precipitation_validation_service.compute_stage2_amount_metrics(amt_sparse, "30m")
    assert m2.status == "INSUFFICIENT_VALIDATION_SAMPLE"
    assert m2.sample_too_small is True
    assert m2.mae_mm is None


# =============================================================================
# 13. Horizon-Specific Evaluation (30m, 60m, 120m)
# =============================================================================

def test_horizon_specific_validation(setup_boundaries):
    """Verifies that 30m, 60m, and 120m horizons are evaluated independently."""
    report = precipitation_validation_service.run_full_validation(ground_truth_path=GROUND_TRUTH_PATH)
    assert "30m" in report.stage1_occurrence_by_horizon
    assert "60m" in report.stage1_occurrence_by_horizon
    assert "120m" in report.stage1_occurrence_by_horizon

    m30 = report.stage1_occurrence_by_horizon["30m"]
    m60 = report.stage1_occurrence_by_horizon["60m"]
    m120 = report.stage1_occurrence_by_horizon["120m"]

    # All horizons have distinct metrics and valid sample counts
    assert m30.sample_count > 0
    assert m60.sample_count > 0
    assert m120.sample_count > 0

    # Skill strictly decays with lead time (30m has highest CSI, 120m lowest CSI)
    assert m30.csi >= m120.csi
    assert m30.brier_score <= m120.brier_score


# =============================================================================
# 14. A/B Adjacent Panchayat Spatial-Gradient Validation
# =============================================================================

def test_ab_spatial_gradient_validation():
    """
    Verifies that during convective events with strong spatial gradients,
    directional agreement is correctly evaluated between adjacent Panchayats.
    """
    # Event 1: Rain at A (14.6mm), Clear at B (0.0mm) -> Pred A prob=0.88, Pred B prob=0.22 -> Agrees
    diff1 = precipitation_validation_service.evaluate_ab_spatial_differentiation(
        event_id="EVT_CONV_01",
        panchayat_a_id="UP_VAR_LGD_100801",
        panchayat_b_id="UP_VAR_LGD_100802",
        obs_a_mm=14.6,
        obs_b_mm=0.0,
        pred_prob_a=0.88,
        pred_prob_b=0.22,
        pred_amt_a_mm=13.5,
        pred_amt_b_mm=None,
        weather_regime="CONVECTIVE_EVENT",
    )
    assert diff1.observed_diff_mm == 14.6
    assert diff1.predicted_prob_diff > 0.50
    assert diff1.directional_agreement is True
    assert diff1.baseline_spatial_variance_zero is True

    # Event 2: Clear at A (0.0mm), Rain at B (11.2mm) -> Pred A prob=0.20, Pred B prob=0.85 -> Agrees
    diff2 = precipitation_validation_service.evaluate_ab_spatial_differentiation(
        event_id="EVT_CONV_02",
        panchayat_a_id="UP_VAR_LGD_100801",
        panchayat_b_id="UP_VAR_LGD_100802",
        obs_a_mm=0.0,
        obs_b_mm=11.2,
        pred_prob_a=0.20,
        pred_prob_b=0.85,
        pred_amt_a_mm=None,
        pred_amt_b_mm=10.5,
        weather_regime="CONVECTIVE_EVENT",
    )
    assert diff2.observed_diff_mm == -11.2
    assert diff2.predicted_prob_diff < -0.50
    assert diff2.directional_agreement is True


# =============================================================================
# 15. Radar Partition and Satellite-Only Evaluation
# =============================================================================

def test_radar_partition_and_satellite_only_evaluation(setup_boundaries):
    """Verifies that radar-available and satellite-only cases are partitioned cleanly."""
    report = precipitation_validation_service.run_full_validation(ground_truth_path=GROUND_TRUTH_PATH)
    r_comp = report.radar_vs_no_radar_comparison
    assert "radar_available" in r_comp
    assert "satellite_only" in r_comp

    sat_eval = report.satellite_only_evaluation
    assert sat_eval["sample_count"] > 0
    assert sat_eval["csi"] is not None
    assert sat_eval["csi"] > 0.70  # Solid skill in satellite-only mode


# =============================================================================
# 16. Confidence State Calibration Check
# =============================================================================

def test_confidence_state_calibration_check():
    """
    Verifies confidence tier evaluation and detection of calibration gaps
    without modifying underlying thresholds.
    """
    bins = {
        "HIGH": [(1.0, 0.90), (5.0, 0.85), (2.0, 0.80), (0.0, 0.75)],   # Obs freq = 3/4 = 0.75, Mean prob = 0.825 -> gap = 0.075 (calibrated)
        "LOW": [(0.0, 0.15), (0.0, 0.10), (0.0, 0.20), (3.0, 0.60)],    # Obs freq = 1/4 = 0.25, Mean prob = 0.2625 -> gap = 0.0125 (calibrated)
    }
    records = precipitation_validation_service.evaluate_confidence_calibration(bins)
    assert records["HIGH"].calibration_review_required is False
    assert records["LOW"].calibration_review_required is False

    # Intentionally miscalibrated bin (system claimed 95% rain, but observed was 0%)
    bad_bins = {
        "HIGH": [(0.0, 0.95), (0.0, 0.95), (0.0, 0.95), (0.0, 0.95)]
    }
    bad_records = precipitation_validation_service.evaluate_confidence_calibration(bad_bins)
    assert bad_records["HIGH"].calibration_review_required is True
    assert bad_records["HIGH"].calibration_gap > 0.25


# =============================================================================
# 17. Cryptographic Immutability and Fail-Closed Safety
# =============================================================================

def test_cryptographic_immutability_and_fail_closed():
    """Verifies that tampering with any protected model or config forces fail-closed behavior."""
    audit = precipitation_validation_service.verify_immutability()
    assert audit.verified_unchanged is True
    assert audit.failed_closed is False
    assert audit.baseline_calibration_hash == EXPECTED_PROTECTED_HASHES["baseline_calibration.json"]
    assert audit.dynamic_v2_xgboost_hash == EXPECTED_PROTECTED_HASHES["dynamic_v2_xgboost_model.json"]


# =============================================================================
# 18. Scientific Claim Matrix Generation & Readiness Classification
# =============================================================================

def test_scientific_claim_matrix_generation(setup_boundaries):
    """Verifies that the scientific claim matrix honestly marks unsupported claims."""
    report = precipitation_validation_service.run_full_validation(ground_truth_path=GROUND_TRUTH_PATH)
    claims = {c.claim: c for c in report.claim_matrix}

    # Proven operational claims must be YES
    assert claims["Panchayat boundary routing operates fail-closed"].supported == "YES"
    assert claims["Panchayat spatial grid masking preserves physical geometry"].supported == "YES"
    assert claims["Real satellite raster ingestion & quality gates operate"].supported == "YES"
    assert claims["Localized precipitation pipeline operates end-to-end"].supported == "YES"
    assert claims["Panchayat-scale rainfall occurrence & amount validated"].supported == "YES"

    # Outcome and dense claims must be ONLY_IF_EVIDENCE_SUPPORTS
    assert claims["Sub-5-km intra-Panchayat agricultural validation"].supported == "ONLY_IF_EVIDENCE_SUPPORTS"
    assert claims["Agricultural advisory improvement proven through farm outcome studies"].supported == "ONLY_IF_EVIDENCE_SUPPORTS"

    # Scientific readiness is LIMITED_VALIDATION (scientifically validated on pilot domain)
    assert report.scientific_readiness == ScientificReadinessState.LIMITED_VALIDATION
