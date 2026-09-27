# Phase 22: Reproducibility & Audit Protocol

**Experiment ID**: `EXP_INDIA_PRODUCTION_CERTIFICATION_PHASE22`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Certification Protocol**: Final Scientific Production Certification & SIH Scientific Freeze  
**Execution Timestamp**: 2026-09-17  
**Deterministic Status**: PASS (Identical across consecutive runs)  

---

## 1. System & Environment Specifications

- **Operating System**: macOS (POSIX compliant)
- **Python Runtime**: Python 3.11+
- **Core Library Dependencies**:
  - `xgboost >= 2.0.0`
  - `scikit-learn >= 1.5.0`
  - `scipy >= 1.13.0`
  - `numpy >= 1.26.0`
  - `pandas >= 2.2.0`
- **Pseudorandom Seed**: `42` (Fixed across NumPy, SciPy bootstrap resamplings, and XGBoost booster inference)
- **Floating-point Rounding**: Standard IEEE 754 64-bit float precision; metrics reported to 4 decimal places.

---

## 2. Cryptographic Checksums & Artifact Provenance

All source inputs are anchored by immutable cryptographic SHA-256 hashes generated during ingestion and validation.

| Artifact / Dataset | File System Path | SHA-256 Checksum | Description |
|---|---|---|---|
| **NOAA ISD Raw Directory** | `backend/data/raw/india/phase21/isd_*_2024.json` | *See individual sidecars* | 17 genuine WMO surface stations (23,949 records) |
| **ERA5 Raw Directory** | `backend/data/raw/india/phase21/era5_*_2024.json` | *See individual sidecars* | ECMWF hourly reanalysis for matching coords |
| **Candidate Model Tree** | `backend/models/candidates/temperature_residual/phase21_candidate_20260917/model.json` | `f8793b827e852ca2e646274e1d16790a98f1fdb9e273a5a75cfddf1f70513d78` | 120-tree gradient boosted decision ensemble |
| **Candidate Metadata** | `backend/models/candidates/temperature_residual/phase21_candidate_20260917/metadata.json` | `6b97621c97a552f44778be8d523675e8ef8013e2f4f224976451e06d99723ec0` | Schema and feature configuration specification |
| **Phase 22 Results JSON** | `backend/data/processed/india/phase22/phase22_certification_results.json` | *Generated Deterministically* | 3-way evaluation, paired tests, 14 gates |

---

## 3. Station Manifest & Regional Registry

Exactly 17 genuine WMO ground stations across 11 States/UTs and 6 distinct physiographic regimes:

| Station ID | Station Name | State / UT | Physiographic Regime | Elevation (m) |
|---|---|---|---|---|
| `42182099999` | New Delhi Safdarjung | Delhi | Indo-Gangetic Plain | 216.0 |
| `42369099999` | Lucknow Amausi | Uttar Pradesh | Indo-Gangetic Plain | 128.0 |
| `42475099999` | Varanasi Babatpur | Uttar Pradesh | Indo-Gangetic Plain | 85.0 |
| `42492099999` | Patna Airport | Bihar | Indo-Gangetic Plain | 53.0 |
| `42071099999` | Amritsar Rajasansi | Punjab | Indo-Gangetic Plain | 234.0 |
| `42101099999` | Patiala Aerodrome | Punjab | Indo-Gangetic Plain | 251.0 |
| `42809099999` | Kolkata Dum Dum | West Bengal | East Delta-Plain | 6.0 |
| `42971099999` | Bhubaneswar Airport | Odisha | East Delta-Plain | 46.0 |
| `42647099999` | Ahmedabad Airport | Gujarat | West / Arid-SemiArid | 55.0 |
| `42348099999` | Jaipur Sanganer | Rajasthan | West / Arid-SemiArid | 390.0 |
| `42452099999` | Kota Aerodrome | Rajasthan | West / Arid-SemiArid | 274.0 |
| `42410099999` | Guwahati Borjhar | Assam | Northeast Hills | 54.0 |
| `42724099999` | Agartala Aerodrome | Tripura | Northeast Hills | 16.0 |
| `42027099999` | Srinagar Airport | Jammu & Kashmir | North / Himalayan | 1587.0 |
| `42083099999` | Shimla Simla | Himachal Pradesh | North / Himalayan | 2202.0 |
| `42674099999` | Jabalpur Airport | Madhya Pradesh | Central Plateau | 497.0 |
| `42867099999` | Nagpur Sonegaon | Maharashtra | Central Plateau | 310.0 |

---

## 4. Chronological & Spatial Partitioning

### 4.1 Chronological Partitions (Time-Isolated)
- **Train Window**: `2024-06-01` to `2024-07-25` ($N = 14,418$ observations, 60.2%)
- **Validation Window**: `2024-07-26` to `2024-08-10` ($N = 4,243$ observations, 17.7%)
- **Frozen Test Window**: `2024-08-11` to `2024-08-31` ($N = 5,288$ observations, 22.1%)
- **Strict Leakage Prevention**: Features are computed strictly using contemporaneous and static physiographic attributes. Ground-truth ISD thermometer observations and target residuals are quarantined from all feature pipelines.

### 4.2 Leave-One-Station-Out (LOSO) Spatial CV
- **Folds**: Exactly 17 folds.
- **Holdout Unit**: One full station held out per fold across the entire Kharif season.
- **Denominator**: Exactly 17 (no obsolete 26-fold denominator).

### 4.3 Leave-One-Region-Out (LORO) Spatial CV
- **Folds**: Exactly 6 folds corresponding to the 6 physiographic regimes.
- **Holdout Unit**: All stations within the specified macro-region held out simultaneously from training.

---

## 5. Algorithmic Implementations

### 5.1 Training-Only Mean Bias Correction
$$\text{Bias}_{\text{train}} = \frac{1}{N_{\text{train}}} \sum_{i=1}^{N_{\text{train}}} \left(T_{\text{obs}, i} - T_{\text{era5}, i}\right) = +0.7351\ ^\circ\text{C}$$
$$\hat{T}_{\text{bias\_corr}, j} = T_{\text{era5}, j} + \text{Bias}_{\text{train}} \quad \forall j \in \text{test}$$
*Note*: This scalar adjustment requires zero additional operational features, zero inference infrastructure, and cannot overfit complex spatial topographies.

### 5.2 XGBoost Residual Downscaling Candidate
$$\hat{\Delta T}_j = f_{\text{XGBoost}}(\mathbf{x}_j)$$
$$\hat{T}_{\text{xgb}, j} = T_{\text{era5}, j} + \hat{\Delta T}_j$$
- Booster specification: 120 estimators, max depth = 4, learning rate = 0.08, subsample = 0.85, colsample = 0.85.

### 5.3 Paired Statistical Hypothesis Testing
- Paired absolute errors: $e_{\text{method}, j} = |\hat{T}_{\text{method}, j} - T_{\text{obs}, j}|$
- Difference: $d_j = e_{\text{xgb}, j} - e_{\text{bias}, j}$
- Two-tailed paired Student's $t$-test (`scipy.stats.ttest_rel`)
- Non-parametric Wilcoxon signed-rank test (`scipy.stats.wilcoxon`)
- 95% Confidence Interval via 5,000 paired bootstrap resamplings (`np.random.default_rng(42)`)
- Effect Size: Cohen's $d = \frac{\bar{d}}{\sigma_d}$

---

## 6. Deterministic Reproduction Protocol

To reproduce all tables, paired statistics, and gate evaluations from scratch:

```bash
# Step 1: Execute certification pipeline
python3 backend/data_pipeline/scripts/run_phase22_certification.py

# Step 2: Execute automated regression suite verifying all 20 certification properties
python3 -m pytest backend/tests/test_phase22_certification.py -v

# Step 3: Verify execution stability (identical rerun)
python3 backend/data_pipeline/scripts/run_phase22_certification.py
git diff backend/data/processed/india/phase22/phase22_certification_results.json
```
*Expected diff*: Empty (zero byte deviation).

---

## 7. Numerical Verification Targets

The reproduction is considered **CERTIFIED IDENTICAL** if and only if the following outputs match exactly:

| Metric | Raw ERA5 | Train Bias-Corrected | XGBoost Candidate |
|---|---|---|---|
| **Test N** | 5,288 | 5,288 | 5,288 |
| **MAE (°C)** | 1.5907 | 1.2661 | 1.1937 |
| **RMSE (°C)** | 1.9922 | 1.6842 | 1.5882 |
| **R²** | 0.6134 | 0.7237 | 0.7543 |
| **Bias (°C)** | -1.1378 | -0.4026 | -0.2333 |
| **Median AE (°C)** | 1.4000 | 0.9649 | 0.9101 |
| **95th Percentile AE (°C)** | 3.9000 | 3.4649 | 3.2797 |

- **Bias Correction Share of Raw MAE Improvement**: `81.76%`
- **XGBoost Incremental Share**: `18.24%`
- **Incremental MAE Gain ($\Delta\text{MAE}$)**: `0.0724 °C`
- **Paired $t$-test $p$-value (Bias vs XGB)**: `1.09e-13`
- **Paired 95% Bootstrap CI**: `[-0.0921 °C, -0.0541 °C]`
- **Model Promotion Decision**: `RETAIN_FOR_RESEARCH`
- **Production Directory State**: `backend/models/temperature_residual/` (**INTENTIONALLY UNMODIFIED & ABSENT**)
