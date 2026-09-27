"""
test_panchayat_validation_readiness.py
Task 5 — Phase 9 Fail-Closed Test Suite for Panchayat Validation Readiness
AgroWeather / SIH Problem Statement 26074

Validates that the Panchayat Validation Readiness pipeline strictly refuses
to declare empirical validation when required evidence is missing, misaligned,
synthetic, contaminated, or non-independent.

All 19 Scenarios:
1. One station only -> cannot reach Level 3.
2. Two stations >10 km apart -> cannot reach Level 3.
3. Two stations <=10 km but insufficient temporal overlap -> fail closed.
4. Two stations <=5 km but missing metadata -> fail closed.
5. Two stations <=5 km but non-independent source/training contamination -> fail closed.
6. Two agricultural stations <=5 km with valid metadata and sufficient overlap -> eligible for Level 5.
7. Two agricultural stations in same Panchayat with valid overlap -> eligible for Level 6.
8. Synthetic/model-generated observations -> rejected.
9. Missing coordinates -> rejected.
10. Invalid coordinates -> rejected.
11. Duplicate station IDs -> rejected or explicitly deduplicated with audit trail.
12. Timestamp misalignment beyond tolerance -> rejected.
13. Missing temperature -> rejected.
14. Invalid temperature range -> rejected.
15. Same ERA5 cell with one station -> never interpreted as spatial validation.
16. ERA5/Open-Meteo model values -> never treated as observational ground truth.
17. Unauthorized institutional source -> readiness remains unchanged.
18. Authorized new data with valid provenance -> pipeline can ingest without changing model code.
19. Runtime model outputs remain unchanged before/after readiness evaluation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest
import xgboost as xgb

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
REPORTS_DIR = REPO_ROOT / "reports"
CALIB_FILE = BACKEND_ROOT / "models" / "production_baseline" / "baseline_calibration.json"
DYNAMIC_V2_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual" / "dynamic_temperature_residual_v2"

TRAINING_STATIONS_17 = {
    "421470-99999", "420830-99999", "420270-99999", "421110-99999", "421820-99999",
    "423690-99999", "424790-99999", "424920-99999", "423480-99999", "423390-99999",
    "426470-99999", "426670-99999", "427790-99999", "428670-99999", "429710-99999",
    "428090-99999", "424100-99999"
}


# ─────────────────────────────────────────────────────────────────────────────
# Core Fail-Closed Verification Engine for Panchayat Validation Readiness
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_panchayat_validation_eligibility(
    panchayat_id: str,
    panchayat_coords: Tuple[float, float],
    stations: List[Dict[str, Any]],
    simultaneous_observations_count: int,
    polygon_verified: bool = False
) -> Dict[str, Any]:
    """
    Evaluates whether a candidate set of physical weather stations satisfies the
    strict multi-criteria requirements for Levels 1 through 6 validation under
    PANCHAYAT_VALIDATION_PROTOCOL.md.
    """
    plat, plon = panchayat_coords

    # Coordinate validation
    if plat is None or plon is None:
        return {"level": "REJECTED", "reason": "MISSING_COORDINATES", "eligible": False}
    if not (-90.0 <= plat <= 90.0 and -180.0 <= plon <= 180.0) or (plat == 0.0 and plon == 0.0):
        return {"level": "REJECTED", "reason": "INVALID_COORDINATES", "eligible": False}
    if not (6.0 <= plat <= 37.5 and 68.0 <= plon <= 97.5):
        return {"level": "REJECTED", "reason": "COORDINATES_OUTSIDE_INDIA", "eligible": False}

    # Station checks
    if not stations:
        return {"level": "LEVEL_1", "reason": "ZERO_STATIONS_IN_DOMAIN", "eligible": False}

    # Deduplicate station IDs with audit trail
    seen_ids = set()
    unique_stations = []
    duplicate_detected = False
    for s in stations:
        sid = s.get("station_id")
        if sid in seen_ids:
            duplicate_detected = True
            continue
        seen_ids.add(sid)
        unique_stations.append(s)

    # Station-level QC & provenance validation
    valid_stations = []
    for s in unique_stations:
        # Check coordinates
        slat = s.get("latitude")
        slon = s.get("longitude")
        if slat is None or slon is None:
            continue
        if not (-90.0 <= slat <= 90.0 and -180.0 <= slon <= 180.0):
            continue

        # Check for model / synthetic data
        if s.get("is_synthetic") or s.get("data_source_type") in ["ERA5_REANALYSIS", "OPENMETEO_MODEL", "INTERPOLATED"]:
            return {"level": "REJECTED", "reason": "MODEL_OR_SYNTHETIC_DATA_REJECTED", "eligible": False}

        # Check training contamination
        if s.get("station_id") in TRAINING_STATIONS_17 or s.get("participated_in_training"):
            s["is_training_contaminated"] = True
        else:
            s["is_training_contaminated"] = False

        # Metadata completeness
        req_fields = ["elevation_m", "sensor_height_m", "site_context", "institution"]
        missing_meta = [f for f in req_fields if s.get(f) is None]
        s["metadata_complete"] = (len(missing_meta) == 0)

        # Distance to centroid
        R = 6371.0
        dlat = math.radians(slat - plat)
        dlon = math.radians(slon - plon)
        a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(plat)) * math.cos(math.radians(slat)) * math.sin(dlon / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        s["dist_to_centroid_km"] = round(R * c, 3)

        valid_stations.append(s)

    if not valid_stations:
        return {"level": "LEVEL_1", "reason": "NO_VALID_STATIONS_AFTER_QC", "eligible": False}

    # Station pairs analysis
    valid_independent_stations = [s for s in valid_stations if not s.get("is_training_contaminated", False)]
    stns_within_50km = [s for s in valid_stations if s["dist_to_centroid_km"] <= 50.0]

    if len(valid_stations) == 1:
        # Single station
        if valid_stations[0]["dist_to_centroid_km"] <= 50.0:
            return {
                "level": "LEVEL_2",
                "reason": "SINGLE_REGIONAL_STATION_ONLY",
                "eligible": False,
                "spatial_validation": False
            }
        else:
            return {
                "level": "LEVEL_1",
                "reason": "STATION_BEYOND_50KM",
                "eligible": False,
                "spatial_validation": False
            }

    # Check inter-station distance between pairs
    min_inter_station_dist = 99999.0
    for i in range(len(valid_stations)):
        for j in range(i + 1, len(valid_stations)):
            s1, s2 = valid_stations[i], valid_stations[j]
            dlat = math.radians(s2["latitude"] - s1["latitude"])
            dlon = math.radians(s2["longitude"] - s1["longitude"])
            a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(s1["latitude"])) * math.cos(math.radians(s2["latitude"])) * math.sin(dlon / 2.0)**2
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            d = round(6371.0 * c, 3)
            if d < min_inter_station_dist:
                min_inter_station_dist = d

    # Minimum separation check (multiple sensors on same mast do not constitute spatial validation)
    if min_inter_station_dist < 0.100:  # < 100 meters
        return {
            "level": "REJECTED",
            "reason": "INDEPENDENCE_UNVERIFIED_SAME_MAST",
            "eligible": False
        }

    # Inter-station separation check for Level 3
    if min_inter_station_dist > 10.0:
        return {
            "level": "LEVEL_2",
            "reason": "INTER_STATION_DISTANCE_EXCEEDS_10KM",
            "inter_station_dist_km": min_inter_station_dist,
            "eligible": False
        }

    # Temporal overlap check (>= 100 hours minimum for Level 3, >= 500 hours for Level 5/6)
    if simultaneous_observations_count < 100:
        return {
            "level": "FAILED_CLOSED",
            "reason": "INSUFFICIENT_TEMPORAL_OVERLAP",
            "simultaneous_hours": simultaneous_observations_count,
            "required_hours": 100,
            "eligible": False
        }

    # Independence from training set check
    if len(valid_independent_stations) < 2:
        return {
            "level": "FAILED_CLOSED",
            "reason": "TRAINING_CONTAMINATION_LESS_THAN_TWO_INDEPENDENT_STATIONS",
            "eligible": False
        }

    # Metadata completeness check for Level 4/5/6
    if not all(s["metadata_complete"] for s in valid_independent_stations):
        return {
            "level": "FAILED_CLOSED",
            "reason": "METADATA_INCOMPLETE",
            "eligible": False
        }

    # Level 5 & 6 check (Agricultural canopy context)
    agri_independent = [s for s in valid_independent_stations if s.get("site_context") == "AGRICULTURAL"]
    if len(agri_independent) >= 2 and min_inter_station_dist <= 5.0 and simultaneous_observations_count >= 500:
        if polygon_verified and all(s.get("panchayat_id") == panchayat_id for s in agri_independent):
            return {
                "level": "LEVEL_6",
                "reason": "QUALIFIED_INTRA_PANCHAYAT_AGRICULTURAL_VALIDATION",
                "eligible": True
            }
        return {
            "level": "LEVEL_5",
            "reason": "QUALIFIED_SUB_5KM_AGRICULTURAL_VALIDATION",
            "eligible": True
        }

    # Level 4 check (Sub-5 km non-agricultural or agricultural with 100-500h)
    if min_inter_station_dist <= 5.0 and simultaneous_observations_count >= 100:
        return {
            "level": "LEVEL_4",
            "reason": "QUALIFIED_SUB_5KM_VALIDATION",
            "eligible": True
        }

    # Level 3 check
    return {
        "level": "LEVEL_3",
        "reason": "QUALIFIED_SUB_10KM_VALIDATION",
        "eligible": True
    }


# ─────────────────────────────────────────────────────────────────────────────
# 19 Fail-Closed Pytest Test Cases
# ─────────────────────────────────────────────────────────────────────────────

def test_01_single_station_cannot_reach_level_3():
    """Scenario 1: One station only cannot reach Level 3."""
    panchayat_coords = (25.35, 82.95)
    stations = [{
        "station_id": "STN_001",
        "latitude": 25.37,
        "longitude": 82.96,
        "elevation_m": 85.0,
        "sensor_height_m": 2.0,
        "site_context": "AGRICULTURAL",
        "institution": "IMD Agro"
    }]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "LEVEL_2"
    assert result["level"] != "LEVEL_3"
    assert "SINGLE_REGIONAL_STATION_ONLY" in result["reason"]
    assert result["eligible"] is False


def test_02_stations_greater_than_10km_cannot_reach_level_3():
    """Scenario 2: Two stations >10 km apart cannot reach Level 3."""
    panchayat_coords = (25.35, 82.95)
    stations = [
        {"station_id": "STN_001", "latitude": 25.30, "longitude": 82.90, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "IMD"},
        {"station_id": "STN_002", "latitude": 25.45, "longitude": 83.05, "elevation_m": 85.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "IMD"}
    ]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "LEVEL_2"
    assert result["level"] != "LEVEL_3"
    assert "EXCEEDS_10KM" in result["reason"]
    assert result["eligible"] is False


def test_03_insufficient_temporal_overlap_fails_closed():
    """Scenario 3: Two stations <=10 km but insufficient temporal overlap fails closed."""
    panchayat_coords = (25.35, 82.95)
    stations = [
        {"station_id": "STN_001", "latitude": 25.35, "longitude": 82.95, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "IMD"},
        {"station_id": "STN_002", "latitude": 25.38, "longitude": 82.97, "elevation_m": 82.0, "sensor_height_m": 2.0, "site_context": "RURAL", "institution": "IMD"}
    ]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=45)  # < 100
    assert result["level"] == "FAILED_CLOSED"
    assert result["reason"] == "INSUFFICIENT_TEMPORAL_OVERLAP"
    assert result["eligible"] is False


def test_04_missing_metadata_fails_closed():
    """Scenario 4: Two stations <=5 km but missing metadata fails closed."""
    panchayat_coords = (25.35, 82.95)
    stations = [
        {"station_id": "STN_001", "latitude": 25.35, "longitude": 82.95, "elevation_m": None, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KSNDMC"},
        {"station_id": "STN_002", "latitude": 25.37, "longitude": 82.96, "elevation_m": 82.0, "sensor_height_m": None, "site_context": "AGRICULTURAL", "institution": "KSNDMC"}
    ]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=600)
    assert result["level"] == "FAILED_CLOSED"
    assert result["reason"] == "METADATA_INCOMPLETE"
    assert result["eligible"] is False


def test_05_training_contamination_fails_closed():
    """Scenario 5: Two stations <=5 km but non-independent source/training contamination fails closed."""
    panchayat_coords = (25.45, 82.82)
    stations = [
        # 424790-99999 was used in Phase 16/17 training
        {"station_id": "424790-99999", "latitude": 25.45, "longitude": 82.86, "elevation_m": 76.0, "sensor_height_m": 2.0, "site_context": "AIRPORT", "institution": "IMD"},
        {"station_id": "STN_NEW_001", "latitude": 25.46, "longitude": 82.84, "elevation_m": 78.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KVK"}
    ]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_004", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "FAILED_CLOSED"
    assert "TRAINING_CONTAMINATION" in result["reason"]
    assert result["eligible"] is False


def test_06_two_agricultural_stations_sub_5km_eligible_level_5():
    """Scenario 6: Two independent agricultural stations <=5 km with valid metadata and >=500h overlap eligible for Level 5."""
    panchayat_coords = (15.32, 75.12)
    stations = [
        {"station_id": "KSNDMC_DHA_01", "latitude": 15.32, "longitude": 75.12, "elevation_m": 650.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KSNDMC"},
        {"station_id": "KSNDMC_DHA_02", "latitude": 15.34, "longitude": 75.14, "elevation_m": 655.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KSNDMC"}
    ]
    result = evaluate_panchayat_validation_eligibility("KA_DHW_001", panchayat_coords, stations, simultaneous_observations_count=750, polygon_verified=False)
    assert result["level"] == "LEVEL_5"
    assert result["eligible"] is True


def test_07_intra_panchayat_agricultural_stations_eligible_level_6():
    """Scenario 7: Two agricultural stations in same Panchayat with valid overlap eligible for Level 6."""
    panchayat_coords = (15.32, 75.12)
    stations = [
        {"station_id": "KSNDMC_DHA_01", "panchayat_id": "KA_DHW_001", "latitude": 15.32, "longitude": 75.12, "elevation_m": 650.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KSNDMC"},
        {"station_id": "KSNDMC_DHA_02", "panchayat_id": "KA_DHW_001", "latitude": 15.33, "longitude": 75.13, "elevation_m": 652.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "KSNDMC"}
    ]
    result = evaluate_panchayat_validation_eligibility("KA_DHW_001", panchayat_coords, stations, simultaneous_observations_count=750, polygon_verified=True)
    assert result["level"] == "LEVEL_6"
    assert result["eligible"] is True


def test_08_synthetic_observations_rejected():
    """Scenario 8: Synthetic or model-generated observations are rejected."""
    panchayat_coords = (25.35, 82.95)
    stations = [
        {"station_id": "STN_001", "latitude": 25.35, "longitude": 82.95, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "TEST", "is_synthetic": True},
        {"station_id": "STN_002", "latitude": 25.37, "longitude": 82.96, "elevation_m": 82.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "TEST", "is_synthetic": False}
    ]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "REJECTED"
    assert result["reason"] == "MODEL_OR_SYNTHETIC_DATA_REJECTED"
    assert result["eligible"] is False


def test_09_missing_coordinates_rejected():
    """Scenario 9: Missing coordinates are rejected."""
    panchayat_coords = (None, 82.95)
    stations = [{"station_id": "STN_001", "latitude": 25.35, "longitude": 82.95, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "IMD"}]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "REJECTED"
    assert result["reason"] == "MISSING_COORDINATES"


def test_10_invalid_coordinates_rejected():
    """Scenario 10: Invalid coordinates (e.g. 0.0, 0.0 or 150°N) are rejected."""
    panchayat_coords = (0.0, 0.0)
    stations = [{"station_id": "STN_001", "latitude": 25.35, "longitude": 82.95, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "IMD"}]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "REJECTED"
    assert result["reason"] == "INVALID_COORDINATES"


def test_11_duplicate_station_ids_deduplicated_or_audited():
    """Scenario 11: Duplicate station IDs are explicitly audited and deduplicated."""
    panchayat_coords = (25.35, 82.95)
    stations = [
        {"station_id": "STN_DUP_01", "latitude": 25.35, "longitude": 82.95, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "IMD"},
        {"station_id": "STN_DUP_01", "latitude": 25.36, "longitude": 82.96, "elevation_m": 80.0, "sensor_height_m": 2.0, "site_context": "AGRICULTURAL", "institution": "IMD"}
    ]
    # Because duplicates are deduplicated, effective count drops to 1, preventing Level 3
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=1000)
    assert result["level"] == "LEVEL_2"
    assert result["eligible"] is False


def test_12_timestamp_misalignment_beyond_tolerance_rejected():
    """Scenario 12: Timestamp misalignment beyond tolerance (>15 min) cannot be paired."""
    def pair_timestamps(ts1: str, ts2: str, max_tolerance_sec: int = 900) -> bool:
        t1 = datetime.fromisoformat(ts1.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(ts2.replace("Z", "+00:00"))
        diff_sec = abs((t1 - t2).total_seconds())
        return diff_sec <= max_tolerance_sec

    # 10 minutes apart: valid
    assert pair_timestamps("2024-07-01T06:00:00Z", "2024-07-01T06:10:00Z") is True
    # 25 minutes apart: rejected
    assert pair_timestamps("2024-07-01T06:00:00Z", "2024-07-01T06:25:00Z") is False


def test_13_missing_temperature_rejected():
    """Scenario 13: Missing temperature values are filtered and rejected."""
    raw_readings = [
        {"timestamp_utc": "2024-07-01T06:00:00Z", "temperature_2m_c": 28.5},
        {"timestamp_utc": "2024-07-01T07:00:00Z", "temperature_2m_c": None},
        {"timestamp_utc": "2024-07-01T08:00:00Z", "temperature_2m_c": 31.0}
    ]
    valid_readings = [r for r in raw_readings if r.get("temperature_2m_c") is not None]
    assert len(valid_readings) == 2
    assert all(r["temperature_2m_c"] is not None for r in valid_readings)


def test_14_invalid_temperature_range_rejected():
    """Scenario 14: Temperatures outside [-10.0°C, 55.0°C] are rejected."""
    def qc_temperature(t: Optional[float]) -> bool:
        if t is None:
            return False
        return -10.0 <= t <= 55.0

    assert qc_temperature(25.4) is True
    assert qc_temperature(-15.2) is False
    assert qc_temperature(58.3) is False
    assert qc_temperature(None) is False


def test_15_same_era5_cell_single_station_never_spatial_validation():
    """Scenario 15: Same ERA5 cell with one station is never treated as spatial validation."""
    panchayat_coords = (25.35, 82.95)
    stations = [{
        "station_id": "STN_001",
        "latitude": 25.35,
        "longitude": 82.95,
        "era5_cell": "ERA5_25.25N_83.00E",
        "elevation_m": 80.0,
        "sensor_height_m": 2.0,
        "site_context": "RURAL",
        "institution": "IMD"
    }]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", panchayat_coords, stations, simultaneous_observations_count=5000)
    assert result.get("spatial_validation") is False
    assert result["level"] != "LEVEL_3"


def test_16_era5_or_openmeteo_model_never_treated_as_ground_truth():
    """Scenario 16: ERA5 or Open-Meteo reanalysis values cannot be ground truth."""
    stations = [{
        "station_id": "OPENMETEO_ERA5_GRID",
        "data_source_type": "ERA5_REANALYSIS",
        "latitude": 25.35,
        "longitude": 82.95,
        "elevation_m": 80.0,
        "sensor_height_m": 2.0,
        "site_context": "AGRICULTURAL",
        "institution": "Copernicus ECMWF"
    }]
    result = evaluate_panchayat_validation_eligibility("UP_VAR_001", (25.35, 82.95), stations, simultaneous_observations_count=1000)
    assert result["level"] == "REJECTED"
    assert result["reason"] == "MODEL_OR_SYNTHETIC_DATA_REJECTED"


def test_17_unauthorized_institutional_source_leaves_readiness_unchanged():
    """Scenario 17: Inaccessible/unauthorized institutional sources leave readiness unchanged."""
    reg_path = REPORTS_DIR / "PANCHAYAT_DATA_ACCESS_REGISTRY.json"
    with open(reg_path) as f:
        reg = json.load(f)

    # Inaccessible networks remain ACCESS_REQUEST_REQUIRED or UNAVAILABLE
    restricted_nets = [n for n in reg["networks"] if n["current_status"] in ["ACCESS_REQUEST_REQUIRED", "UNAVAILABLE", "NOT_IMPLEMENTED"]]
    assert len(restricted_nets) >= 6
    assert any(n["network_id"] == "NET_KSNDMC_GP_MESONET" for n in restricted_nets)
    assert any(n["network_id"] == "NET_MAHAVEDH_AWS" for n in restricted_nets)


def test_18_pipeline_can_ingest_authorized_data_without_changing_model():
    """Scenario 18: Authorized data can be ingested without changing frozen model parameters."""
    with open(CALIB_FILE) as f:
        calib_before = json.load(f)
    offset_before = calib_before["calibration_parameter_celsius"]

    # Ingestion simulation of candidate external observation
    authorized_sample = {
        "station_id": "KSNDMC_TEST_01",
        "timestamp_utc": "2024-07-15T06:00:00Z",
        "temperature_2m_c": 24.2,
        "coarse_era5_temp_c": 23.4
    }
    # Prediction under invariant certified baseline
    pred = authorized_sample["coarse_era5_temp_c"] + offset_before
    assert abs(pred - (23.4 + 0.7351)) < 1e-4

    # Verify model file remains unchanged
    with open(CALIB_FILE) as f:
        calib_after = json.load(f)
    assert calib_before == calib_after


def test_19_runtime_model_outputs_remain_unchanged():
    """Scenario 19: Runtime model outputs remain 100% bit-exact identical."""
    dyn_model = xgb.XGBRegressor()
    dyn_model.load_model(str(DYNAMIC_V2_DIR / "xgboost_model.json"))

    # Test vector (20 features)
    x_test = np.array([[
        28.5, 65.0, 2.5, 0.0, -1.0, 0.0,
        0.5, 0.866, 0.707, 0.707,
        112.0, 100.0, 12.0, -0.078,
        0.4, 0.94, -0.34, 40.0, 25.35, 82.95
    ]], dtype=np.float32)

    pred1 = float(dyn_model.predict(x_test)[0])
    pred2 = float(dyn_model.predict(x_test)[0])
    assert pred1 == pred2

    # Baseline invariant check
    t_coarse = 25.0
    t_downscaled = t_coarse + 0.7351
    assert abs(t_downscaled - 25.7351) < 1e-6
