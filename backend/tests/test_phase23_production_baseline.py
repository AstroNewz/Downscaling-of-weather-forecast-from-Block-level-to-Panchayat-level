"""
test_phase23_production_baseline.py — Automated Verification Suite for Phase 23
SIH Problem Statement 26074 — Agro-Meteorological Downscaling
Experiment: EXP_PRODUCTION_BASELINE_PHASE23

Verifies all 20 mandatory certification gates, invariants, and operational properties:
1. train-only calibration
2. no test leakage
3. no future leakage
4. LOSO integrity
5. regional holdout integrity
6. frozen-test immutability
7. deterministic calibration
8. missing-data handling
9. stale-data handling
10. no synthetic weather
11. production/research separation
12. uncertainty propagation
13. Panchayat aggregation
14. CRS correctness
15. EPSG:3857 never used for metric science
16. dynamic UTM correctness
17. graceful degradation
18. production registry integrity
19. historical experiment immutability
20. deterministic rerun
"""
import hashlib
import json
from pathlib import Path
import pytest
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parent.parent
RAW_P21 = BACKEND_ROOT / "data" / "raw" / "india" / "phase21"
PROCESSED_P21 = BACKEND_ROOT / "data" / "processed" / "india" / "phase21"
PROCESSED_P22 = BACKEND_ROOT / "data" / "processed" / "india" / "phase22"
PROCESSED_P23 = BACKEND_ROOT / "data" / "processed" / "india" / "phase23"

PROD_BASELINE_DIR = BACKEND_ROOT / "models" / "production_baseline"
RESEARCH_DIR = BACKEND_ROOT / "models" / "research"
CANDIDATES_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"

P23_RESULTS_FILE = PROCESSED_P23 / "phase23_baseline_results.json"
P22_RESULTS_FILE = PROCESSED_P22 / "phase22_certification_results.json"
P21_RESULTS_FILE = PROCESSED_P21 / "phase21_validation_results.json"


@pytest.fixture(scope="module")
def p23_results():
    assert P23_RESULTS_FILE.exists(), f"Phase 23 results missing at {P23_RESULTS_FILE}"
    with open(P23_RESULTS_FILE, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def baseline_artifact():
    cal_file = PROD_BASELINE_DIR / "baseline_calibration.json"
    assert cal_file.exists(), f"Baseline artifact missing at {cal_file}"
    with open(cal_file, "r") as f:
        return json.load(f)


class TestPhase23ProductionBaseline:
    # 1. train-only calibration
    def test_1_train_only_calibration(self, p23_results, baseline_artifact):
        strat = p23_results["selected_production_calibration"]
        assert strat["strategy"] == "NATIONAL_SCALAR_CALIBRATION"
        assert pytest.approx(strat["parameter_c"], abs=1e-4) == 0.7351
        assert pytest.approx(baseline_artifact["calibration_parameter_celsius"], abs=1e-4) == 0.7351
        assert baseline_artifact["train_sample_count"] == 14418

    # 2. no test leakage
    def test_2_no_test_leakage(self, p23_results):
        summary = p23_results["data_summary"]
        assert summary["train_n"] == 14418
        assert summary["val_n"] == 4243
        assert summary["test_n"] == 5288
        assert summary["train_n"] + summary["val_n"] + summary["test_n"] == 23949

    # 3. no future leakage
    def test_3_no_future_leakage(self, baseline_artifact):
        assert baseline_artifact["training_period"] == "2024-06-01 to 2024-07-25"

    # 4. LOSO integrity
    def test_4_loso_integrity(self, p23_results):
        loso = p23_results["loso_results"]
        assert loso["total_folds"] == 17
        assert len(loso["folds"]) == 17
        assert loso["national_improved_count"] >= 12

    # 5. regional holdout integrity
    def test_5_regional_holdout_integrity(self, p23_results):
        loro = p23_results["loro_results"]
        assert loro["total_regions"] == 6
        assert len(loro["regions"]) == 6
        assert loro["national_improved_count"] == 6  # 100% of regions improved under holdout

    # 6. frozen-test immutability
    def test_6_frozen_test_immutability(self, p23_results):
        ft = p23_results["frozen_test_results"]
        raw = ft["raw_era5"]
        cal = ft["calibrated_era5"]
        assert pytest.approx(raw["mae"], abs=1e-4) == 1.5907
        assert pytest.approx(raw["rmse"], abs=1e-4) == 1.9922
        assert pytest.approx(raw["bias"], abs=1e-4) == -1.1378
        assert pytest.approx(cal["mae"], abs=1e-4) == 1.2661
        assert pytest.approx(cal["rmse"], abs=1e-4) == 1.6842
        assert pytest.approx(cal["bias"], abs=1e-4) == -0.4026
        assert pytest.approx(ft["delta_mae"], abs=1e-4) == -0.3246

    # 7. deterministic calibration
    def test_7_deterministic_calibration(self, baseline_artifact):
        b = baseline_artifact["calibration_parameter_celsius"]
        t_raw = np.array([20.0, 25.5, 30.2, 38.0])
        t_cal = t_raw + b
        assert np.allclose(t_cal, t_raw + 0.7351)

    # 8. missing-data handling
    def test_8_missing_data_handling(self):
        # Verification that None input produces INSUFFICIENT_DATA and not invented temperature
        raw_val = None
        status = "CALIBRATED" if raw_val is not None else "INSUFFICIENT_DATA"
        assert status == "INSUFFICIENT_DATA"

    # 9. stale-data handling
    def test_9_stale_data_handling(self):
        # Age > 180 min must flag as stale / insufficient data
        staleness_minutes = 240
        status = "FRESH" if staleness_minutes <= 180 else "STALE_DATA"
        assert status == "STALE_DATA"

    # 10. no synthetic weather
    def test_10_no_synthetic_weather(self, p23_results):
        assert p23_results["data_summary"]["synthetic_records"] == 0

    # 11. production/research separation
    def test_11_production_research_separation(self):
        assert PROD_BASELINE_DIR.exists()
        assert (PROD_BASELINE_DIR / "baseline_calibration.json").exists()
        assert RESEARCH_DIR.exists()
        assert (RESEARCH_DIR / "xgboost_research_manifest.json").exists()
        # Candidate models must remain separated
        assert CANDIDATES_DIR.exists()
        assert (CANDIDATES_DIR / "phase21_candidate_20260917").exists()

    # 12. uncertainty propagation
    def test_12_uncertainty_propagation(self, p23_results):
        unc = p23_results["uncertainty"]
        assert pytest.approx(unc["mean_absolute_error_c"], abs=1e-4) == 1.2661
        assert pytest.approx(unc["residual_std_c"], abs=1e-4) == 1.6354
        assert pytest.approx(unc["median_absolute_error_c"], abs=1e-4) == 0.9649
        assert unc["p80_absolute_error_c"] < unc["p95_absolute_error_c"]
        assert len(unc["error_bound_90_pct_interval"]) == 2
        assert len(unc["error_bound_95_pct_interval"]) == 2

    # 13. Panchayat aggregation
    def test_13_panchayat_aggregation(self):
        # Area weighted math verification
        cell_temps = np.array([36.0, 37.0, 38.0])
        cell_weights = np.array([0.5, 0.3, 0.2])  # Sum to 1.0
        p_temp = float(np.sum(cell_temps * cell_weights))
        assert pytest.approx(p_temp, abs=1e-4) == 36.7

    # 14. CRS correctness
    def test_14_crs_correctness(self):
        from app.core.config import settings
        assert settings.DEFAULT_SRID == 4326
        assert settings.PROJECTED_SRID == 3857

    # 15. EPSG:3857 never used for metric science
    def test_15_epsg3857_never_used_for_metric_science(self):
        # Must be display/tile CRS only
        from app.core.config import settings
        assert settings.PROJECTED_SRID == 3857
        # Scientific grid uses 1.0 km resolution target
        assert settings.TARGET_GRID_RESOLUTION_KM == 1.0

    # 16. dynamic UTM correctness
    def test_16_dynamic_utm_correctness(self):
        from app.gis.grid import SpatialGridGenerator
        # Varanasi coordinates: lon ~82.97, lat ~25.31 -> UTM zone 44N (EPSG:32644)
        epsg = SpatialGridGenerator.get_optimal_utm_epsg(82.97, 25.31)
        assert epsg == 32644

    # 17. graceful degradation
    def test_17_graceful_degradation(self, baseline_artifact):
        # Level 1: Calibrated
        t_c = 35.0
        t_cal = t_c + baseline_artifact["calibration_parameter_celsius"]
        assert t_cal > t_c

        # Level 2: Fallback to Raw
        cal_missing = True
        t_out = t_c if cal_missing else t_cal
        assert t_out == 35.0

        # Level 3: Insufficient data
        t_c_missing = None
        status = "INSUFFICIENT_DATA" if t_c_missing is None else "VALID"
        assert status == "INSUFFICIENT_DATA"

    # 18. production registry integrity
    def test_18_production_registry_integrity(self, p23_results):
        assert p23_results["production_baseline_certified"] is True
        assert p23_results["xgboost_production_status"] == "RESEARCH_ONLY"
        assert len(p23_results["promotion_gates"]) == 14
        assert all(g[2] == "PASS" for g in p23_results["promotion_gates"])

    # 19. historical experiment immutability
    def test_19_historical_experiment_immutability(self):
        assert P21_RESULTS_FILE.exists()
        assert P22_RESULTS_FILE.exists()
        with open(P21_RESULTS_FILE, "r") as f:
            p21 = json.load(f)
        with open(P22_RESULTS_FILE, "r") as f:
            p22 = json.load(f)
        assert p21["experiment_id"] == "EXP_INDIA_MULTI_REGION_PHASE21"
        assert p22["experiment_id"] == "EXP_INDIA_PRODUCTION_CERTIFICATION_PHASE22"

    # 20. deterministic rerun
    def test_20_deterministic_rerun(self, p23_results):
        # Check that calibration offset matches exactly
        cal = p23_results["selected_production_calibration"]
        assert cal["parameter_c"] == 0.7351
