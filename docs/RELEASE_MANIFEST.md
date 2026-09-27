# SIH Official Final Release Manifest

| Field | Value / Certified Status |
|---|---|
| **RELEASE_TAG** | `v1.0.0-sih-production-candidate` |
| **AUDIT_EXPERIMENT** | `EXP_PRODUCTION_BASELINE_PHASE24_FINAL_AUDIT` |
| **PRODUCTION_BASELINE_STATUS** | **CERTIFIED_FOR_SIH_PRODUCTION-CANDIDATE_DEPLOYMENT** |
| **CHALLENGER_XGBOOST_STATUS** | **RESEARCH_ONLY (Rejected for production deployment)** |
| **CERTIFIED_PRODUCTION_FORMULATION** | $T_{\text{calibrated}} = T_{\text{coarse\_ERA5}} + 0.7351\ ^\circ\text{C}$ |
| **CALIBRATION_COEFFICIENT** | `+0.7351 °C` (Fitted on Train Jun 1–Jul 25, $N = 14,418$) |
| **CALIBRATION_ARTIFACT_PATH** | `backend/models/production_baseline/baseline_calibration.json` |
| **CALIBRATION_ARTIFACT_SHA256** | `3dcad5fbfd060d47ad9cbf1ec9cbe0df8c99da050e0d5a3ef2c3f76906ea1941` |
| **XGBOOST_MODEL_PATH** | `backend/models/candidates/temperature_residual/phase21_candidate_20260917/` |
| **XGBOOST_MODEL_SHA256** | `48ca2a9dba5a42b87ad18a51f4cc9a43ff19cf11c678a44ef20e86f52f1ed891` |
| **GENUINE_OBSERVATIONS** | `23,949` synchronous ground-truth observations (0 synthetic) |
| **STATIONS_EVALUATED** | `17` genuine WMO surface stations across 11 States/UTs |
| **PHYSIOGRAPHIC_REGIMES** | `6` distinct regimes across India |
| **TEMPORAL_EVALUATION_PERIOD** | `2024-06-01` to `2024-08-31` (Kharif monsoon) |
| **FROZEN_TEST_WINDOW** | `2024-08-11` to `2024-08-31` ($N = 5,288$ synchronous pairs) |
| **FROZEN_TEST_RAW_ERA5_MAE** | `1.5907 °C` (RMSE: 1.9922°C, R²: 0.6134, Bias: -1.1378°C) |
| **FROZEN_TEST_CALIBRATED_MAE** | `1.2661 °C` (RMSE: 1.6842°C, R²: 0.7237, Bias: -0.4026°C) |
| **FROZEN_TEST_DELTA_MAE** | **-0.3246 °C** (20.4% error reduction; R² increases +0.1103) |
| **EMPIRICAL_ERROR_P80** | `1.9649 °C` (80.18% actual empirical test coverage) |
| **EMPIRICAL_ERROR_P95** | `3.4649 °C` (95.10% actual empirical test coverage) |
| **17-FOLD_LOSO_IMPROVEMENT** | `12 of 17 stations (70.6%)` |
| **6-FOLD_LORO_HOLDOUT_TRANSFER** | `6 of 6 regions (100.0%)` |
| **GIS_METRIC_CRS** | Dynamic Local UTM (e.g. `EPSG:32644` for Varanasi/Ayodhya) |
| **GEOGRAPHIC_OUTPUT_CRS** | `EPSG:4326` (WGS84) |
| **DISPLAY_CRS** | `EPSG:3857` (Web Mercator; strictly display-only) |
| **PANCHAYAT_AGGREGATION** | Area-weighted polygon intersection on 1,000m × 1,000m grid |
| **GRACEFUL_DEGRADATION** | Validated Calibrated -> Validated Raw -> INSUFFICIENT_DATA |
| **TEST_SUITE_STATUS** | **76+ PASSED, 0 FAILED** |
| **SIH_JUDGE_WALKTHROUGH** | Fully operational on `/judge` |
| **TIMESTAMP_UTC** | `2026-09-17T13:30:00Z` |

---

## Component Architecture & Governance Verification

### 1. Production Baseline Deployment
- **Directory**: `backend/models/production_baseline/`
- **Integrity**: Contains certified `baseline_calibration.json` ($B = +0.7351\ ^\circ\text{C}$) and `metadata.json`.
- **Operational Dependencies**: Requires only coarse 2m temperature + static DEM metadata. Real-time telemetry dependencies eliminated.

### 2. Research Challenger Isolation
- **Directory**: `backend/models/candidates/temperature_residual/phase21_candidate_20260917/`
- **Status**: Quarantined as `RESEARCH_ONLY`.
- **Governance Finding**: XGBoost incremental gain was only $0.0724\ ^\circ\text{C}$ over simple calibration, which failed the practical complexity threshold ($0.1000\ ^\circ\text{C}$) and exhibited spatial extrapolation risks. Production deployment was formally rejected.

### 3. Data Lineage & Cryptography
- **NOAA ISD-Lite**: 17 raw observation files verified with SHA-256 sidecars.
- **ERA5 Atmospheric Reanalysis**: 17 hourly files verified with SHA-256 sidecars.
- **Zero Leakage**: Temporal partitions strictly disjoint; target residuals quarantined from feature vectors.
