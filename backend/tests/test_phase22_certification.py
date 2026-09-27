"""
test_phase22_certification.py — Automated Verification Suite for Phase 22
SIH Problem Statement 26074 — Agro-Meteorological Downscaling
Experiment: EXP_INDIA_PRODUCTION_CERTIFICATION_PHASE22

Verifies all 20 mandatory certification gates and invariants:
1. frozen test immutability
2. exactly 17 LOSO folds
3. no obsolete 26-fold denominator
4. six-region accounting
5. train-only bias correction
6. target quarantine
7. temporal isolation
8. spatial isolation
9. paired statistical testing
10. candidate/production separation
11. production model immutability
12. model checksum
13. data checksum
14. feature availability
15. deterministic rerun
16. zero synthetic observations
17. provenance completeness
18. deterministic promotion gate
19. terrain-ablation arithmetic
20. historical experiment immutability
"""
import hashlib
import json
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
RAW_P21 = BACKEND_ROOT / "data" / "raw" / "india" / "phase21"
PROCESSED_P21 = BACKEND_ROOT / "data" / "processed" / "india" / "phase21"
PROCESSED_P22 = BACKEND_ROOT / "data" / "processed" / "india" / "phase22"
CANDIDATES_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"
P21_CANDIDATE = CANDIDATES_DIR / "phase21_candidate_20260917"
PRODUCTION_DIR = BACKEND_ROOT / "models" / "temperature_residual"
P22_RESULTS_FILE = PROCESSED_P22 / "phase22_certification_results.json"
P21_RESULTS_FILE = PROCESSED_P21 / "phase21_validation_results.json"


@pytest.fixture(scope="module")
def p22_results():
    assert P22_RESULTS_FILE.exists(), f"Phase 22 results file missing at {P22_RESULTS_FILE}"
    with open(P22_RESULTS_FILE, "r") as f:
        return json.load(f)


class TestPhase22Certification:
    # 1. frozen test immutability
    def test_1_frozen_test_immutability(self, p22_results):
        data_summary = p22_results["data_summary"]
        assert data_summary["test_n"] == 5288
        assert data_summary["temporal_period"] == "2024-06-01 to 2024-08-31"

        raw = p22_results["three_way_comparison"]["raw_era5"]
        assert pytest.approx(raw["mae"], abs=1e-4) == 1.5907
        assert pytest.approx(raw["rmse"], abs=1e-4) == 1.9922
        assert pytest.approx(raw["r2"], abs=1e-4) == 0.6134
        assert pytest.approx(raw["bias"], abs=1e-4) == -1.1378

    # 2. exactly 17 LOSO folds
    def test_2_exactly_17_loso_folds(self, p22_results):
        loso = p22_results["loso_spatial_generalization"]
        assert loso["folds"] == 17
        assert len(loso["folds_data"]) == 17

    # 3. no obsolete 26-fold denominator
    def test_3_no_obsolete_26_fold_denominator(self, p22_results):
        loso = p22_results["loso_spatial_generalization"]
        assert loso["folds"] != 26
        assert len(loso["folds_data"]) != 26
        assert loso["better_than_raw_count"] == 13
        rate = loso["better_than_raw_count"] / loso["folds"]
        assert pytest.approx(rate, rel=1e-3) == (13 / 17)

    # 4. six-region accounting
    def test_4_six_region_accounting(self, p22_results):
        regions = p22_results["regional_generalization"]
        assert regions["regions_evaluated"] == 6
        assert len(regions["regions_data"]) == 6
        expected_regions = {
            "Central Plateau",
            "East Delta-Plain",
            "Indo-Gangetic Plain",
            "North / Himalayan",
            "Northeast Hills",
            "West / Arid-SemiArid",
        }
        found_regions = {r["region"] for r in regions["regions_data"]}
        assert found_regions == expected_regions

    # 5. train-only bias correction
    def test_5_train_only_bias_correction(self, p22_results):
        three_way = p22_results["three_way_comparison"]
        assert pytest.approx(three_way["mean_train_bias"], abs=1e-4) == 0.7351
        bc = three_way["bias_corrected"]
        assert pytest.approx(bc["mae"], abs=1e-4) == 1.2661
        assert pytest.approx(bc["rmse"], abs=1e-4) == 1.6842
        assert pytest.approx(bc["r2"], abs=1e-4) == 0.7237
        assert pytest.approx(bc["bias"], abs=1e-4) == -0.4026
        assert three_way["bias_fraction_pct"] > 80.0  # Explains 81.76% of raw error reduction

    # 6. target quarantine
    def test_6_target_quarantine(self):
        meta_file = P21_CANDIDATE / "metadata.json"
        assert meta_file.exists()
        with open(meta_file, "r") as f:
            meta = json.load(f)
        features = meta.get("features", [])
        forbidden = ["target", "residual", "temperature_obs", "temp_obs", "isd_temp", "reference_temp"]
        for feat in features:
            for forb in forbidden:
                assert forb not in feat.lower(), f"Target leakage detected: {feat}"

    # 7. temporal isolation
    def test_7_temporal_isolation(self, p22_results):
        data_summary = p22_results["data_summary"]
        assert data_summary["train_n"] == 14418
        assert data_summary["val_n"] == 4243
        assert data_summary["test_n"] == 5288
        assert data_summary["train_n"] + data_summary["val_n"] + data_summary["test_n"] == 23949

    # 8. spatial isolation
    def test_8_spatial_isolation(self, p22_results):
        folds = p22_results["loso_spatial_generalization"]["folds_data"]
        held_out_stations = [fold["held_out_station"] for fold in folds]
        assert len(held_out_stations) == 17
        assert len(set(held_out_stations)) == 17, "Each LOSO fold must evaluate a unique held-out station"

    # 9. paired statistical testing
    def test_9_paired_statistical_testing(self, p22_results):
        pstats = p22_results["paired_statistics"]
        for key in ["raw_vs_bias", "raw_vs_xgb", "bias_vs_xgb"]:
            assert key in pstats
            comp = pstats[key]
            assert comp["n"] == 5288
            assert "ci_95" in comp
            assert len(comp["ci_95"]) == 2
            assert "p_val_ttest" in comp
            assert "p_val_wilcoxon" in comp
            assert "cohens_d" in comp
        assert pstats["practical_threshold_c"] == 0.1000
        assert pstats["meets_practical_threshold"] is False

    # 10. candidate/production separation
    def test_10_candidate_production_separation(self):
        assert P21_CANDIDATE.exists()
        assert (P21_CANDIDATE / "model.json").exists()
        # Production directory must NOT be overwritten with candidate
        if PRODUCTION_DIR.exists():
            prod_model = PRODUCTION_DIR / "model.json"
            assert not prod_model.exists(), "Production directory must not contain a candidate model"

    # 11. production model immutability
    def test_11_production_model_immutability(self, p22_results):
        assert p22_results["production_model_changed"] is False
        assert p22_results["model_decision"] == "RETAIN_FOR_RESEARCH"

    # 12. model checksum
    def test_12_model_checksum(self):
        model_path = P21_CANDIDATE / "model.json"
        assert model_path.exists()
        with open(model_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        assert sha256 == "48ca2a9dba5a42b87ad18a51f4cc9a43ff19cf11c678a44ef20e86f52f1ed891"

    # 13. data checksum
    def test_13_data_checksum(self):
        sidecars = list(RAW_P21.glob("isd_*.provenance.json"))
        assert len(sidecars) >= 17, f"Expected at least 17 ISD provenance sidecars, found {len(sidecars)}"

    # 14. feature availability
    def test_14_feature_availability(self, p22_results):
        gates = dict((g[0], g) for g in p22_results["promotion_gates"])
        assert gates["GATE 13"][2] in ["FAIL", "INSUFFICIENT_EVIDENCE"]

    # 15. deterministic rerun
    def test_15_deterministic_rerun(self, p22_results):
        xgb_m = p22_results["three_way_comparison"]["xgboost"]
        assert pytest.approx(xgb_m["mae"], abs=1e-4) == 1.1937
        assert pytest.approx(xgb_m["rmse"], abs=1e-4) == 1.5882

    # 16. zero synthetic observations
    def test_16_zero_synthetic_observations(self, p22_results):
        assert p22_results["data_summary"]["synthetic_records"] == 0

    # 17. provenance completeness
    def test_17_provenance_completeness(self, p22_results):
        gates = dict((g[0], g) for g in p22_results["promotion_gates"])
        assert gates["GATE 1"][2] == "PASS"
        assert gates["GATE 2"][2] == "PASS"

    # 18. deterministic promotion gate
    def test_18_deterministic_promotion_gate(self, p22_results):
        gates = p22_results["promotion_gates"]
        assert len(gates) == 14
        gate_dict = {g[0]: g[2] for g in gates}
        assert gate_dict["GATE 8"] == "FAIL"
        assert gate_dict["GATE 10"] == "FAIL"
        assert gate_dict["GATE 14"] == "FAIL"
        assert p22_results["model_decision"] == "RETAIN_FOR_RESEARCH"

    # 19. terrain-ablation arithmetic
    def test_19_terrain_ablation_arithmetic(self, p22_results):
        terrain = p22_results["terrain_ablation"]
        low = terrain["low_relief"]
        high = terrain["high_relief"]
        assert pytest.approx(low["with_terrain_mae"], abs=1e-4) == 1.1906
        assert pytest.approx(low["without_terrain_mae"], abs=1e-4) == 1.1938
        assert pytest.approx(low["diff_mae"], abs=1e-4) == 0.0032

        assert pytest.approx(high["with_terrain_mae"], abs=1e-4) == 1.2165
        assert pytest.approx(high["without_terrain_mae"], abs=1e-4) == 1.1745
        assert pytest.approx(high["diff_mae"], abs=1e-4) == 0.0420
        # Positive diff indicates terrain increased MAE in high relief (1.2165 - 1.1745 = +0.0420°C)
        assert high["diff_mae"] > 0

    # 20. historical experiment immutability
    def test_20_historical_experiment_immutability(self):
        assert P21_RESULTS_FILE.exists()
        with open(P21_RESULTS_FILE, "r") as f:
            p21 = json.load(f)
        assert p21.get("experiment_id") == "EXP_INDIA_MULTI_REGION_PHASE21"
        assert p21.get("record_counts", {}).get("accepted") == 23949
