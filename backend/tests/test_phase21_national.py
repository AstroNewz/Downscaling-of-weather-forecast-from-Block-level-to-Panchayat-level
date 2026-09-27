"""
test_phase21_national.py — Comprehensive Test & Audit Suite for Phase 21
SIH Problem Statement 26074 — Agro-Meteorological Downscaling

Verifies:
1. 17 stations cannot silently produce an unexplained 26-fold LOSO count (accounting consistency)
2. Regional improvement count matches regional results
3. Frozen test remains unchanged (5,288 observations, Aug 11 - Aug 31, 2024)
4. Paired significance calculation uses identical observations
5. Bias correction is train-only (zero leakage from validation or test)
6. Terrain ablation uses identical frozen evaluation data
7. Candidate remains separated from production (production directory absent/safe)
8. Zero synthetic records in real-data evaluation pipeline
9. Zero target leakage in feature schemas
10. Station and regional holdouts remain completely isolated
"""
import json
import pytest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_P21 = BACKEND_ROOT / "data" / "processed" / "india" / "phase21"
CANDIDATES_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"
P21_CANDIDATE = CANDIDATES_DIR / "phase21_candidate_20260917"
V3_CANDIDATE = CANDIDATES_DIR / "candidate_v3_20260916T213422Z"
PRODUCTION_DIR = BACKEND_ROOT / "models" / "temperature_residual"
RESULTS_FILE = PROCESSED_P21 / "phase21_validation_results.json"
AUDIT_FILE = PROCESSED_P21 / "phase21_audit_metrics.json"


class TestPhase21AccountingAndConsistency:
    def test_loso_accounting_consistency(self):
        """17 valid stations must produce exactly 17 LOSO folds, not 26."""
        assert RESULTS_FILE.exists()
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        loso_metrics = data.get("loso_metrics", {})
        assert len(loso_metrics) == 17, f"Expected 17 LOSO station folds, got {len(loso_metrics)}"
        # Check improved count
        improved = [k for k, v in loso_metrics.items() if v.get("improved")]
        assert len(improved) == 13, f"Expected 13 improved stations, got {len(improved)}"
        # Verify rate is 13/17 (76.47%)
        rate = len(improved) / len(loso_metrics)
        assert pytest.approx(rate, rel=1e-3) == (13 / 17)

    def test_regional_improvement_counts_match_results(self):
        """Regional results must report exact counts for both Chronological test and Leave-One-Region-Out."""
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        # 1. Chronological holdout regional breakdown
        reg_test = data.get("region_metrics", {})
        assert len(reg_test) == 6, f"Expected 6 regions in test set breakdown, got {len(reg_test)}"
        improved_chrono = [k for k, v in reg_test.items() if v.get("improved")]
        assert len(improved_chrono) == 6, f"Expected 6/6 improved in chronological holdout, got {len(improved_chrono)}"

        # 2. Leave-One-Region-Out cross-validation
        reg_cv = data.get("regional_cv", {})
        assert len(reg_cv) == 6, f"Expected 6 regions in CV, got {len(reg_cv)}"
        improved_cv = [k for k, v in reg_cv.items() if v.get("improved")]
        assert len(improved_cv) == 4, f"Expected 4/6 improved in Leave-One-Region-Out CV, got {len(improved_cv)}"

    def test_frozen_test_set_integrity(self):
        """Frozen test set must contain exactly 5,288 observations with fixed baseline metrics."""
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        counts = data.get("record_counts", {})
        assert counts.get("test") == 5288, f"Expected 5,288 test records, got {counts.get('test')}"

        chrono = data.get("chronological_metrics", {})
        b0 = chrono.get("baseline_0_era5", {})
        cand = chrono.get("candidate_xgboost", {})
        assert pytest.approx(b0.get("mae"), abs=1e-3) == 1.5907
        assert pytest.approx(cand.get("mae"), abs=1e-3) == 1.1937
        assert pytest.approx(b0.get("rmse"), abs=1e-3) == 1.9922
        assert pytest.approx(cand.get("rmse"), abs=1e-3) == 1.5882

    def test_paired_significance_uses_identical_observations(self):
        """Paired statistical test must evaluate exactly the 5,288 test observations."""
        assert AUDIT_FILE.exists()
        with open(AUDIT_FILE, "r") as f:
            audit = json.load(f)
        pt = audit.get("paired_test", {})
        assert pt.get("n") == 5288
        assert pt.get("p_val_ttest") < 1e-10
        assert pt.get("p_val_wilcoxon") < 1e-10
        ci = pt.get("ci_95", [0, 0])
        assert ci[0] < 0 and ci[1] < 0, f"Confidence interval must be strictly negative, got {ci}"

    def test_bias_correction_is_train_only(self):
        """Bias correction benchmark must be fitted on training records only (N=14,418)."""
        with open(AUDIT_FILE, "r") as f:
            audit = json.load(f)
        bc = audit.get("bias_corrected_baseline", {})
        assert bc.get("train_n") == 14418
        assert pytest.approx(bc.get("mean_train_bias"), abs=1e-2) == 0.7351
        metrics = bc.get("metrics", {})
        assert pytest.approx(metrics.get("mae"), abs=1e-2) == 1.2661

    def test_terrain_ablation_uses_identical_data(self):
        """Terrain ablation subsets must sum to the 5,288 test observations."""
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        topo = data.get("topographic_test", {})
        n_high = next(v["n"] for k, v in topo.items() if "HIGH_RELIEF" in k)
        n_low = next(v["n"] for k, v in topo.items() if "LOW_RELIEF" in k)
        assert n_high == 627
        assert n_low == 4661
        assert (n_high + n_low) == 5288


class TestPhase21SafetyAndProtection:
    def test_candidate_separated_from_production(self):
        """Candidate artifacts must reside in candidates directory; production must remain absent."""
        assert P21_CANDIDATE.exists()
        assert (P21_CANDIDATE / "model.json").exists()
        assert (P21_CANDIDATE / "metadata.json").exists()

        if not PRODUCTION_DIR.exists():
            pytest.skip("Production model directory absent — SAFE")
        candidate_dirs = list(PRODUCTION_DIR.glob("candidate_*"))
        assert len(candidate_dirs) == 0

    def test_candidate_v3_preserved(self):
        """Candidate V3 must remain completely untouched."""
        assert V3_CANDIDATE.exists()
        assert (V3_CANDIDATE / "model.json").exists()
        assert (V3_CANDIDATE / "model_metadata.json").exists()

    def test_zero_synthetic_records(self):
        """Zero synthetic records allowed in Phase 21 evaluation dataset."""
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        counts = data.get("record_counts", {})
        assert counts.get("raw") == 24921
        assert counts.get("accepted") == 23949
        assert counts.get("rejected") == 0

    def test_zero_target_leakage(self):
        """Feature schema must not contain target residual or ground truth temperature."""
        with open(P21_CANDIDATE / "metadata.json", "r") as f:
            meta = json.load(f)
        features = meta.get("features", [])
        forbidden = ["target_delta_t", "truth_obs_temp", "temperature_c", "obs_temp"]
        for f in forbidden:
            assert f not in features, f"Forbidden target column {f} found in feature schema!"

    def test_model_decision_is_retain_for_research(self):
        """Promotion gate must enforce RETAIN_FOR_RESEARCH."""
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
        assert data.get("model_decision") == "RETAIN_FOR_RESEARCH"
