# Phase 23: Reproducibility Guide & Verification Protocol

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE23`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Status**: AUDITED & DETERMINISTICALLY REPRODUCIBLE  

---

## 1. System & Environment Specifications

- **Operating System**: macOS / POSIX compliant
- **Python Version**: Python 3.11+ / 3.12 / 3.13
- **Core Dependencies**:
  - `numpy >= 1.26.0`
  - `scipy >= 1.13.0`
  - `pandas >= 2.2.0`
  - `pytest >= 8.0.0`
- **Global Random Seed**: `42`
- **Floating Point Precision**: IEEE 754 64-bit float; metrics rounded to 4 decimal places.

---

## 2. Reproduction Commands

To reproduce the Phase 23 calibration, validation, cross-validation, frozen test, and uncertainty quantification:

```bash
# 1. Run Phase 23 Production Baseline Pipeline
python3 backend/data_pipeline/scripts/run_phase23_baseline_certification.py

# 2. Run Complete Phase 23 Verification Test Suite (20 tests)
python3 -m pytest backend/tests/test_phase23_production_baseline.py -v

# 3. Verify Deterministic Rerun Invariance
python3 backend/data_pipeline/scripts/run_phase23_baseline_certification.py
git diff backend/models/production_baseline/baseline_calibration.json
```
*Expected diff*: Zero bytes deviation.

---

## 3. Cryptographic Artifact Hashes

| Artifact File | Path | Description |
|---|---|---|
| **Production Baseline Model** | `backend/models/production_baseline/baseline_calibration.json` | Certified parameter $B = +0.7351\ ^\circ\text{C}$ and uncertainty |
| **Production Metadata** | `backend/models/production_baseline/metadata.json` | Production schema, bounds, and research pointers |
| **Research Manifest** | `backend/models/research/xgboost_research_manifest.json` | Quarantined XGBoost challenger audit documentation |
| **Phase 23 Results** | `backend/data/processed/india/phase23/phase23_baseline_results.json` | Complete benchmark metrics, LOSO, and LORO results |

---

## 4. Key Numerical Verification Targets

| Metric | Target Value | Evaluation Period |
|---|---|---|
| **Total Aligned Records** | 23,949 | June 1 – August 31, 2024 |
| **Train Observations ($N_{\text{train}}$)** | 14,418 | June 1 – July 25, 2024 |
| **Validation Observations ($N_{\text{val}}$)** | 4,243 | July 26 – August 10, 2024 |
| **Frozen Test Observations ($N_{\text{test}}$)** | 5,288 | August 11 – August 31, 2024 |
| **Certified National Calibration ($B$)** | **+0.7351 °C** | Fitted strictly on $N_{\text{train}}$ |
| **Validation Raw ERA5 MAE** | 1.3943 °C | Validation partition |
| **Validation Calibrated ERA5 MAE** | 1.1431 °C | Validation partition ($\Delta\text{MAE} = -0.2512\ ^\circ\text{C}$) |
| **Frozen Test Raw ERA5 MAE** | 1.5907 °C | Frozen test partition |
| **Frozen Test Calibrated ERA5 MAE** | **1.2661 °C** | Frozen test partition ($\Delta\text{MAE} = -0.3246\ ^\circ\text{C}$) |
| **Frozen Test $R^2$** | **0.7237** | Frozen test partition (Raw: 0.6134) |
| **Uncertainty Residual Std Dev** | **±1.6354 °C** | Frozen test residuals |
| **Uncertainty 80th Percentile Bound** | **±1.9649 °C** | Recommended advisory tolerance |
| **Uncertainty 95th Percentile Bound** | **±3.4649 °C** | Maximum empirical error envelope |
| **17-Fold LOSO Generalization Rate** | 12 of 17 stations (70.6%) | Leave-One-Station-Out CV |
| **6-Fold LORO Generalization Rate** | 6 of 6 regions (100.0%) | Leave-One-Region-Out CV |
