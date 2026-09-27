# Phase 21: Reproducibility Guide & Verification Matrix (Audited)

**Experiment**: `EXP_INDIA_MULTI_REGION_PHASE21`  
**SIH Problem Statement**: 26074 — Agro-Meteorological Downscaling  
**Date**: 2026-09-17  
**Status**: AUDITED & FULLY REPRODUCIBLE  

---

## 1. Environment Specifications

- **Operating System**: macOS / Linux / POSIX compatible
- **Python Version**: Python 3.11+ / 3.12 / 3.13
- **Core Dependencies**:
  - `xgboost >= 2.0.0`
  - `scikit-learn >= 1.5.0`
  - `scipy >= 1.13.0`
  - `numpy >= 1.26.0`
  - `pandas >= 2.2.0`
- **Global Random Seed**: `42` (Deterministic across NumPy, XGBoost, Scikit-learn, and Bootstrap sampling)

---

## 2. Dataset Identifiers & Provenance Hashes

| Dataset Item | Source | Identifier / Path | Records / Details | Checksum File |
|---|---|---|---|---|
| **NOAA ISD Observations** | NOAA NCEI ISD-Lite | `backend/data/raw/india/phase21/isd_*_2024.json` | 23,949 records across 17 stations | Verified in `*.provenance.json` |
| **ERA5 Coarse Reanalysis** | ECMWF / Open-Meteo | `backend/data/raw/india/phase21/era5_*_2024.json` | 2,208 hourly timesteps / station | Verified in `*.provenance.json` |
| **Processed Validation Results** | Phase 21 Pipeline | `backend/data/processed/india/phase21/phase21_validation_results.json` | Complete benchmark metrics | SHA256 recorded in metadata |
| **Audit Metrics Output** | Statistical Audit | `backend/data/processed/india/phase21/phase21_audit_metrics.json` | Paired tests & bias benchmarks | Linked in test suite |
| **Candidate Model Weights** | XGBoost JSON | `backend/models/candidates/temperature_residual/phase21_candidate_20260917/model.json` | Serialized booster tree graph | SHA256 recorded in candidate metadata |

---

## 3. Train / Validation / Test Split Definitions

- **Temporal Coverage**: 2024-06-01T00:00:00Z to 2024-08-31T23:00:00Z (92 days, Kharif season)
- **Split Partitions**:
  - `TRAIN_START = "2024-06-01"`, `TRAIN_END = "2024-07-25"` ($N = 14,418$ observations, 60.2%)
  - `VAL_START = "2024-07-26"`, `VAL_END = "2024-08-10"` ($N = 4,243$ observations, 17.7%)
  - `TEST_START = "2024-08-11"`, `TEST_END = "2024-08-31"` ($N = 5,288$ observations, 22.1%)
- **Zero Leakage**: All splits are strictly disjoint chronologically. Target residual $\Delta T$ and thermometer ground truth are quarantined from the feature matrix.

---

## 4. Methodology & Baseline Definitions

### 4.1 Simple Training-Only Bias-Corrected Baseline
$$\text{Bias}_{\text{train}} = \frac{1}{N_{\text{train}}} \sum_{i \in \text{train}} \left(T_{\text{ref}, i} - T_{\text{coarse}, i}\right) = +0.7351\ ^\circ\text{C}$$
$$\hat{T}_{\text{bias\_corr}, j} = T_{\text{coarse}, j} + \text{Bias}_{\text{train}} \quad \forall j \in \text{test}$$
- Fitted strictly on the 14,418 training observations. Zero test or validation observations used.

### 4.2 Paired Statistical Significance Methodology
- Observations are paired synchronously at exact matching station and UTC timestamps ($N = 5,288$).
- Paired absolute error differences: $d_j = |T_{\text{coarse}, j} - T_{\text{ref}, j}| - |\hat{T}_{\text{cand}, j} - T_{\text{ref}, j}|$.
- Evaluated via paired two-tailed $t$-test, Wilcoxon signed-rank test, and 5,000 paired bootstrap resamples for the 95% confidence interval of $\Delta\text{MAE}$.

### 4.3 Terrain Ablation Methodology
- Identical frozen test observations partitioned into:
  - High Relief ($n = 627$): Stations with elevation $>500$ m MSL or local relief $>100$ m.
  - Low Relief ($n = 4,661$): Alluvial Gangetic and coastal plains.
- Comparison of Model WITH terrain features (`f_obs_elevation`, `f_era5_elevation`, `f_elevation_diff`, `f_lapse_rate_adj`, `f_high_relief`) vs. Model WITHOUT terrain features on the exact same subsets.

---

## 5. Execution Commands

To reproduce the complete Phase 21 data acquisition, modeling, cross-validation, and statistical audit:

```bash
# 1. Run main multi-region pipeline
python3 backend/data_pipeline/scripts/run_phase21_national_pipeline.py

# 2. Run statistical consistency audit
python3 backend/data_pipeline/scripts/audit_phase21_consistency.py

# 3. Run automated verification test suite
python3 -m pytest backend/tests/test_phase21_national.py -v
```

---

## 6. Expected Audited Benchmark Outputs

- **Total Aligned Observations**: `23,949`
- **Total Valid Stations**: `17` across `6` physiographic regimes
- **Chronological Test Set Size**: `5,288`
- **Raw ERA5 Baseline MAE**: `1.5907 °C`
- **Train-Only Bias-Corrected ERA5 MAE**: `1.2661 °C` ($\Delta\text{MAE} = -0.3246\ ^\circ\text{C}$)
- **Candidate XGBoost MAE**: `1.1937 °C` ($\Delta\text{MAE} = -0.3969\ ^\circ\text{C}$)
- **Paired 95% Bootstrap CI**: `[-0.4226 °C, -0.3724 °C]`
- **Paired t-test p-value**: `4.21e-183` (Statistically significant)
- **LOSO Improvement Rate**: `13 of 17 stations (76.47%)`
- **Regional Leave-One-Region-Out Transfer Rate**: `4 of 6 regions (66.7%)`
- **Chronological Regional Improvement Rate**: `6 of 6 regions (100.0%)`
- **Final Model Decision**: `RETAIN_FOR_RESEARCH`
- **Production Directory**: `backend/models/temperature_residual/` (**INTENTIONALLY ABSENT & SAFE**)
