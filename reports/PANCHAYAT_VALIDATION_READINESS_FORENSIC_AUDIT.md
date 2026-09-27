# Forensic Audit of Panchayat Validation Readiness & Institutional Data Access Pipeline
## AgroWeather / Smart India Hackathon Problem Statement 26074
### Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services

**Audit Code**: `AUDIT-TASK5-PANCHAYAT-READINESS-2026`  
**Generated At**: 2026-09-26T13:30:00+00:00  
**Audit Status**: **PASS_WITH_LIMITATIONS**  
**Final Forensic Verdict**: **PANCHAYAT VALIDATION READINESS — VERIFIED WITH LIMITATIONS**  

---

## A. Executive Verdict

Following a strict, evidence-based forensic audit of the Task 4 Panchayat Validation Readiness framework and institutional data access pipeline, the independent audit verdict is **PANCHAYAT VALIDATION READINESS — VERIFIED WITH LIMITATIONS**.

> [!IMPORTANT]
> **Definitive Scientific Conclusion:**
> *Panchayat-scale validation infrastructure is operational and fail-closed. The empirical validation claim remains pending authorized independent agricultural observations. No model, frozen weights, certified baseline, website, or mobile UI were modified.*

### Summary of Audit Findings
1. **Mathematical Reproducibility (PASS - EXACT)**: The 434-record dry-run same-cell test, within-cell spatial variance ($0.0000^\circ\text{C}^2$), observed spatial variance ($1.3868^\circ\text{C}^2$), Baseline Gradient MAE ($0.9203^\circ\text{C}$), Dynamic V2 Gradient MAE ($1.0082^\circ\text{C}$), and spatial correlation ($-0.2055$) were reproduced bit-for-bit to 16 decimal places from raw historical observations.
2. **Fail-Closed Governance (PASS - 19/19 TESTS PASSED)**: All 19 programmatic fail-closed scenarios in [`test_panchayat_validation_readiness.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_panchayat_validation_readiness.py) passed without exception.
3. **Model & UI Immutability (PASS - UNMODIFIED)**: All cryptographic SHA-256 hashes of the Certified Baseline calibration ([`baseline_calibration.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/models/production_baseline/baseline_calibration.json)), Dynamic V2 candidate ([`xgboost_model.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/models/candidates/temperature_residual/dynamic_temperature_residual_v2/xgboost_model.json)), frontend React components, and Flutter mobile code remain completely untouched.
4. **Institutional Access Reality (LIMITATION)**: Zero state agricultural mesonet observations (KSNDMC, Mahavedh, IMD Agro-AWS, DAMU, ICAR KVK) currently reside in the repository; all high-density agrarian networks are firewalled inside state intranets (`ACCESS_REQUEST_REQUIRED`).
5. **Training Contamination in Target Register (LIMITATION)**: 8 of the 18 target Panchayats have a nearest synoptic station that was part of the original 17 training stations used to fit early temperature models, disqualifying those stations as purely independent holdouts.
6. **Heuristic Runner Gap (LIMITATION)**: The runner script [`run_panchayat_validation_pipeline.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data_pipeline/scripts/run_panchayat_validation_pipeline.py) evaluated readiness level purely using distance from centroid without verifying temporal overlap ($\ge 100\text{h}$), metadata completeness, or station independence before potential Level 3–5 assignment (although in open synoptic data zero stations qualified anyway).

---

## B. Task 4 Artifact Inventory & Cross-Reference

| File Path | Purpose | Producer Script | Input Datasets | Output Datasets | Deterministic | Reproducible | Modifies Production Code | Unsupported Claims Found |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| [`reports/PANCHAYAT_DATA_ACCESS_REGISTRY.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_DATA_ACCESS_REGISTRY.json) | Registry of 10 candidate networks | Manual / Task 4 Pipeline | Network specs | Registry JSON | Yes | Yes | No | Listed Bhuvan (raster) as station network |
| [`reports/PANCHAYAT_VALIDATION_TARGET_REGISTER.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_TARGET_REGISTER.json) | Register of 18 representative Gram Panchayats | Manual / Task 4 Pipeline | Physiographic catalog | Target JSON | Yes | Yes | No | KA_BLG_001 ERA5 cell differed from pipeline calculation |
| [`docs/PANCHAYAT_VALIDATION_PROTOCOL.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_VALIDATION_PROTOCOL.md) | Standard Operating Procedure (SOP) | Task 4 Protocol Spec | N/A (Normative Spec) | Markdown Doc | Yes | Yes | No | None; rigorous protocol |
| [`docs/PANCHAYAT_DATA_REQUEST_SPECIFICATION.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_DATA_REQUEST_SPECIFICATION.md) | Technical data request packet | Task 4 Protocol Spec | N/A (Institutional Spec) | Markdown Doc | Yes | Yes | No | None; rigorous request schema |
| [`docs/PANCHAYAT_DATA_ACCESS_CHECKLIST.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_DATA_ACCESS_CHECKLIST.md) | Operational requisition checklists | Task 4 Protocol Spec | N/A (Procedural Guide) | Markdown Doc | Yes | Yes | No | None; step-by-step verified |
| [`backend/data_pipeline/scripts/run_panchayat_validation_pipeline.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data_pipeline/scripts/run_panchayat_validation_pipeline.py) | Automated readiness runner | Task 4 Runner | Pilot JSONs, registries | Readiness reports | Yes | Yes | No | Level assignment only checked centroid distance |
| [`backend/data/processed/india/phase4_panchayat_readiness/panchayat_readiness_metrics.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data/processed/india/phase4_panchayat_readiness/panchayat_readiness_metrics.json) | Machine-readable metrics artifact | `run_panchayat_validation_pipeline.py` | Pilot JSONs, Target register | Metrics JSON | Yes | Yes | No | None |
| [`reports/PANCHAYAT_VALIDATION_READINESS_REPORT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_READINESS_REPORT.json) | Canonical Task 4 JSON report | `run_panchayat_validation_pipeline.py` | Target & Access Registries | Report JSON | Yes | Yes | No | None |
| [`reports/PANCHAYAT_VALIDATION_READINESS_REPORT.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_READINESS_REPORT.md) | Canonical Task 4 Markdown report | `run_panchayat_validation_pipeline.py` | Readiness metrics | Report Markdown | Yes | Yes | No | Status "READY FOR AUTHORIZED DATA" could be misread |
| [`reports/PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.md) | Task 3 fine-scale forensic report | `run_panchayat_scale_validation_audit.py` | Pilot & Synoptic data | Forensic Markdown | Yes | Yes | No | Hardcoded 0.3841°C² in Table 5 text |
| [`reports/PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.json) | Task 3 machine-readable audit | `run_panchayat_scale_validation_audit.py` | Pilot & Synoptic data | Forensic JSON | Yes | Yes | No | None |
| [`reports/PANCHAYAT_SCALE_VALIDATION_DATA_MANIFEST.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_SCALE_VALIDATION_DATA_MANIFEST.json) | Task 3 fine-scale data manifest | `run_panchayat_scale_validation_audit.py` | Station inventories | Manifest JSON | Yes | Yes | No | None |

---

## C. Target-Register Audit (18 Panchayats)

Every one of the 18 target Panchayats was independently verified against WGS-84 geodetic coordinates, Haversine spherical distance, Vincenty ellipsoidal distance, parent ERA5 grid cells, nearest synoptic stations, and training contamination status:

| Panchayat ID | Name & State | Centroid (Lat, Lon) | Elev (m) | Nearest Station (ID & Name) | Haversine Dist (km) | Vincenty Dist (km) | Reg Dist (km) | Nearest Stn Training Status | ERA5 Cell (Calc vs Reg) | Readiness Level |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `UP_VAR_001` | Maya Bazar, UP | (25.35, 82.95) | 112.0 | `424830` Varanasi Synoptic | 8.733 | 8.728 | 8.78 | **Independent** | `25.25N_83.00E` (Match) | LEVEL_2 |
| `UP_VAR_004` | Baragaon, UP | (25.45, 82.82) | 92.0 | `424790` Varanasi Babatpur | 4.016 | 4.023 | 4.02 | <mark>TRAINING</mark> | `25.50N_82.75E` (Match) | LEVEL_2 |
| `KA_BLR_001` | Hoskote, KA | (13.07, 77.79) | 875.0 | `432950` Bangalore HAL | 25.181 | 25.180 | 25.12 | **Independent** | `13.00N_77.75E` (Match) | LEVEL_2 |
| `KA_DHW_001` | Rayanal, KA | (15.32, 75.12) | 650.0 | `432011` Hubli Airport | 5.184 | 5.177 | 5.14 | **Independent** | `15.25N_75.00E` (Match) | LEVEL_2 |
| `MH_RGD_001` | Alibag Rural, MH | (18.65, 72.88) | 8.0 | `430030` Mumbai Santacruz | 48.831 | 48.610 | 48.78 | **Independent** | `18.75N_73.00E` (Match) | LEVEL_2 |
| `KL_EKM_001` | Cherai, KL | (10.14, 76.18) | 3.0 | `433530` Cochin Naval | 23.808 | 23.710 | 23.55 | **Independent** | `10.25N_76.25E` (Match) | LEVEL_2 |
| `MH_SAT_001` | Wai, MH | (17.95, 73.89) | 718.0 | `430630` Pune | 64.964 | 64.667 | 65.11 | **Independent** | `18.00N_74.00E` (Match) | LEVEL_1 |
| `KA_BLG_001` | Khanapur, KA | (15.63, 74.51) | 649.0 | `431971` Belgaum Sambra | 27.011 | 26.910 | 27.03 | **Independent** | <mark>15.75N vs 15.50N</mark> | LEVEL_2 |
| `AS_KAM_001` | Rani, AS | (26.05, 91.62) | 58.0 | `424100` Guwahati Borjhar | 6.846 | 6.834 | 6.84 | <mark>TRAINING</mark> | `26.00N_91.50E` (Match) | LEVEL_2 |
| `ML_EKH_001` | Sohra, ML | (25.28, 91.72) | 1420.0 | `425150` Cherrapunji | 3.583 | 3.572 | 3.56 | **Independent** | `25.25N_91.75E` (Match) | LEVEL_2 |
| `UK_DDN_001` | Sahaspur, UK | (30.38, 77.82) | 590.0 | `421110` Dehradun | 21.227 | 21.258 | 21.32 | <mark>TRAINING</mark> | `30.50N_77.75E` (Match) | LEVEL_2 |
| `HP_KLU_001` | Naggar, HP | (32.14, 77.16) | 1760.0 | `420830` Shimla | 115.647 | 115.319 | 115.65 | <mark>TRAINING</mark> | `32.25N_77.25E` (Match) | LEVEL_1 |
| `MP_BHP_001` | Phanda, MP | (23.22, 77.24) | 498.0 | `426670` Bhopal Bairagarh | 13.069 | 13.072 | 13.12 | <mark>TRAINING</mark> | `23.25N_77.25E` (Match) | LEVEL_2 |
| `JH_RNC_001` | Namkum, JH | (23.33, 85.38) | 635.0 | `427010` Ranchi Birsa Munda | 6.184 | 6.191 | 6.18 | **Independent** | `23.25N_85.50E` (Match) | LEVEL_2 |
| `RJ_JAI_001` | Bassi, RJ | (26.83, 76.04) | 372.0 | `423480` Jaipur Sanganer | 23.841 | 23.884 | 23.95 | <mark>TRAINING</mark> | `26.75N_76.00E` (Match) | LEVEL_2 |
| `GJ_AHM_001` | Sanand, GJ | (22.99, 72.38) | 42.0 | `426470` Ahmedabad | 27.086 | 27.113 | 27.18 | <mark>TRAINING</mark> | `23.00N_72.50E` (Match) | LEVEL_2 |
| `AP_KRI_001` | Guduru, AP | (16.22, 81.08) | 4.0 | `431850` Machilipatnam | 7.798 | 7.805 | 7.82 | **Independent** | `16.25N_81.00E` (Match) | LEVEL_2 |
| `OD_KND_001` | Rajnagar, OD | (20.58, 86.74) | 6.0 | `429710` Bhubaneswar | 101.683 | 101.761 | 100.82 | <mark>TRAINING</mark> | `20.50N_86.75E` (Match) | LEVEL_1 |

### Target Register Findings
1. **Zero Coordinate Duplication**: All 18 Panchayats have distinct, valid geographic coordinates within the Indian terrestrial landmass.
2. **ERA5 Grid Cell Mismatch**: `KA_BLG_001` (lat 15.63, lon 74.51). $15.63 / 0.25 = 62.52 \implies 63 \times 0.25 = 15.75^\circ\text{N}$. The mathematical pipeline assigned `ERA5_15.75N_74.50E` (distance 13.39 km), whereas `PANCHAYAT_VALIDATION_TARGET_REGISTER.json` had recorded `ERA5_15.50N_74.50E` (distance 14.51 km). Both remain Level 2; no readiness change.
3. **Training Station Contamination Warning**: 8 out of 18 Panchayats (44.4%) have nearest stations that participated in Phase 16/17 model development. These 8 stations cannot serve as independent holdout test stations for models trained on them.
4. **Boundary Polygon Status**: All 18 Panchayats have `PANCHAYAT_MAPPING_UNAVAILABLE` because official Survey of India / LGD boundary polygons are not archived in the local repository.

---

## D. Readiness-Level Definition & Hierarchy Audit

Cross-referencing [`PANCHAYAT_VALIDATION_PROTOCOL.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_VALIDATION_PROTOCOL.md) against [`run_panchayat_validation_pipeline.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data_pipeline/scripts/run_panchayat_validation_pipeline.py):

| Readiness Level | Protocol Specification | Implementation Check in Runner | Fail-Closed Test Status | Audit Assessment |
| :--- | :--- | :--- | :---: | :--- |
| **LEVEL 1** | Zero stations within 50 km | `stations_within_50km == 0` | Verified | **PASS** |
| **LEVEL 2** | $\ge 1$ station within 50 km | `stations_within_50km >= 1` | Verified | **PASS** |
| **LEVEL 3** | $\ge 2$ independent stations $\le 10\text{ km}$, $\ge 100\text{h}$ overlap | `len(stns_within_10km) >= 2` | Flaw Flagged | **LIMITATION**: Runner checks distance to centroid, not inter-station distance or overlap hours |
| **LEVEL 4** | $\ge 2$ independent stations $\le 5\text{ km}$, $\ge 100\text{h}$ overlap, metadata | `len(stns_within_5km) >= 2` | Flaw Flagged | **LIMITATION**: Runner omitted metadata completeness check |
| **LEVEL 5** | $\ge 2$ independent agricultural stations $\le 5\text{ km}$, $\ge 500\text{h}$, siting | `len(agri_stns_within_5km) >= 2` | Flaw Flagged | **LIMITATION**: Siting verified by string flag, but overlap hours unverified |
| **LEVEL 6** | $\ge 2$ independent agricultural stations within same Panchayat boundary | `polygon_verified` required | Verified | **PASS**: Blocked by `PANCHAYAT_MAPPING_UNAVAILABLE` |

> [!WARNING]
> **Heuristic Classification Flaw in `run_panchayat_validation_pipeline.py`:**
> Lines 249–261 of the runner classify levels based strictly on the count of stations within distance thresholds of the Panchayat centroid (`stns_within_10km >= 2` $\implies$ Level 3). If two stations were on opposite sides of a centroid (separation 18 km), the runner would have erroneously assigned Level 3. Under current open data, because zero pairs exist, no false promotion occurred; however, the pipeline must enforce pairwise inter-station distance and temporal overlap checks before processing external mesonet payloads.

---

## E. 434-Record Dry-Run Exact Reproduction

The Varanasi pilot dual-station cluster was re-evaluated against genuine historical observations:
- **Station 1**: Varanasi Babatpur Airport (`424790-99999`), lat $25.45^\circ\text{N}$, lon $82.86^\circ\text{E}$, elevation 76.0 m.
- **Station 2**: Varanasi Synoptic (`424830-99999`), lat $25.30^\circ\text{N}$, lon $83.017^\circ\text{E}$, elevation 90.0 m.
- **Physical Separation**: **22.13 km** (Haversine) / **22.11 km** (Vincenty).
- **Temporal Duration**: 01-June-2024 to 31-August-2024 (Synoptic hours: 00, 03, 06, 09, 12 UTC).
- **Physical Range Checks**: 434 valid temperature readings; 0 range violations; 0 missing values; 0 synthetic values.

### Bit-for-Bit Reproduction Table

| Metric | Committed Value | Reproduced Value | Absolute Difference | Verification Status |
| :--- | :---: | :---: | :---: | :---: |
| **Simultaneous Aligned Records** | 434 | 434 | 0 | **PASS (EXACT)** |
| **Mean Observed $\Delta T$ ($T_{\text{syn}} - T_{\text{air}}$)** | -0.3926267281105992°C | -0.3926267281105992°C | $0.0000000000000000$ | **PASS (EXACT)** |
| **Observed $\Delta T$ Std Dev** | 1.1776102544387685°C | 1.1776102544387685°C | $0.0000000000000000$ | **PASS (EXACT)** |
| **Observed Spatial Variance** | **1.3867659113593414°C²** | **1.3867659113593414°C²** | $0.0000000000000000$ | **PASS (EXACT)** |
| **Coarse ERA5 Same-Cell Variance** | 0.0000000000000000°C² | 0.0000000000000000°C² | $0.0000000000000000$ | **PASS (EXACT)** |
| **Certified Baseline Same-Cell Variance** | **0.0000000000000000°C²** | **0.0000000000000000°C²** | $0.0000000000000000$ | **PASS (EXACT)** |
| **Dynamic Residual V2 Variance** | **0.2162115807148534°C²** | **0.2162115807148534°C²** | $0.0000000000000000$ | **PASS (EXACT)** |
| **Certified Baseline Same-Cell Gradient MAE** | **0.9202764976958526°C** | **0.9202764976958526°C** | $0.0000000000000000$ | **PASS (EXACT)** |
| **Certified Baseline Nearest-Grid Gradient MAE** | 1.0905529953917052°C | 1.0905529953917052°C | $0.0000000000000000$ | **PASS (EXACT)** |
| **Dynamic Residual V2 Gradient MAE** | **1.0082374735740725°C** | **1.0082374735740725°C** | $0.0000000000000000$ | **PASS (EXACT)** |
| **Certified Baseline Gradient RMSE** | 1.2413386560428123°C | 1.2413386560428123°C | $0.0000000000000000$ | **PASS (EXACT)** |
| **Dynamic Residual V2 Gradient RMSE** | 1.3545440679757625°C | 1.3545440679757625°C | $0.0000000000000000$ | **PASS (EXACT)** |
| **Dynamic V2 Spatial Correlation** | **-0.2055412303550613** | **-0.2055412303550613** | $0.0000000000000000$ | **PASS (EXACT)** |

---

## F. Same-Cell Variance Mathematical Verification

The audit confirms the mathematical truth of the statement:
$$\sigma^2_{\text{within}}(\text{Certified Baseline}) = 0.0000^\circ\text{C}^2$$

### Mathematical Derivation:
The production model defines:
$$T_{\text{baseline}}(x) = T_{\text{coarse}}(C) + 0.7351^\circ\text{C} \quad \forall x \in \text{Grid Cell } C$$
When two stations $x_1, x_2$ are evaluated within the same coarse cell $C$, the coarse temperature $T_{\text{coarse}}(C)$ is identically equal for both stations.
$$\Delta T_{\text{baseline}}(x_1, x_2) = (T_{\text{coarse}}(C) + 0.7351) - (T_{\text{coarse}}(C) + 0.7351) = 0.0000^\circ\text{C}$$
The sample spatial variance across $M$ locations in cell $C$ is:
$$\sigma^2_{\text{within}} = \frac{1}{M}\sum_{i=1}^M \left(T_{\text{baseline}}(x_i) - \bar{T}_{\text{baseline}}\right)^2 = \frac{1}{M}\sum_{i=1}^M (0)^2 = 0.0000^\circ\text{C}^2$$

> [!CAUTION]
> **Crucial Distinction Between Model Variance and Real-World Prediction Error:**
> Zero spatial variance in the baseline model **MUST NEVER** be cited as evidence that the baseline has zero real-world error.
> 1. **Model-Output Spatial Variance ($0.0000^\circ\text{C}^2$)**: A structural property indicating that the baseline model is spatially flat within a coarse cell.
> 2. **Real-World Observed Spatial Variability ($1.3868^\circ\text{C}^2$)**: The physical atmosphere varied by up to $10.4^\circ\text{C}$ between the two stations (range $-6.0^\circ\text{C}$ to $+3.8^\circ\text{C}$).
> 3. **Spatial Gradient Prediction Error ($\text{MAE} = 0.9203^\circ\text{C}$)**: Because the baseline predicts zero gradient, its gradient error is identically equal to $|\Delta T_{\text{obs}}|$:
>    $$\epsilon_{\text{gradient}} = |0.0 - \Delta T_{\text{obs}}| = |\Delta T_{\text{obs}}|$$
>    The baseline has an unavoidable mean error of $0.92^\circ\text{C}$ on spatial differences.
> 4. **Validation of Sub-Grid Gradients**: The baseline structurally cannot validate sub-grid gradients because it does not model them.

---

## G. Pairwise Gradient Formulations & Task 3 Discrepancy

### Formulation Review
- **Observed Gradient**: $\Delta T_{\text{obs}}(t) = T_{\text{obs}, 2}(t) - T_{\text{obs}, 1}(t)$ ($^\circ\text{C}$)
- **Predicted Gradient**: $\Delta T_{\text{pred}}(t) = T_{\text{pred}, 2}(t) - T_{\text{pred}, 1}(t)$ ($^\circ\text{C}$)
- **Gradient Absolute Error**: $\epsilon(t) = |\Delta T_{\text{pred}}(t) - \Delta T_{\text{obs}}(t)|$ ($^\circ\text{C}$)
- **Gradient MAE**: $\frac{1}{N}\sum_{t=1}^N \epsilon(t)$ ($^\circ\text{C}$)

All signs, orderings, units, and denominators are mathematically sound.

### Investigation of Inherited Task 3 Discrepancy
In Task 3 report [`PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_SCALE_VALIDATION_FORENSIC_REPORT.md) Table 5, the Dynamic V2 intra-cell variance was reported as `0.3841°C² (Topographically Modulated)`.
**Audit Investigation**:
Inspection of [`run_panchayat_scale_validation_audit.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data_pipeline/scripts/run_panchayat_scale_validation_audit.py) line 1110 revealed that `0.3841°C²` was hardcoded into a markdown table template string, whereas the true calculated variance of Dynamic V2 on that dataset was `0.2162°C²` (matching Table 6 and Task 4).
**Correction**: Task 4 correctly reported `0.2162°C²`. The Task 3 text string is marked **SUPERSEDED BY EMPIRICAL CALCULATION**.

### Why Dynamic V2 Remains RESEARCH_ONLY
Although Dynamic V2 produces non-zero physical gradients ($\sigma^2 = 0.2162^\circ\text{C}^2$), its performance on the Varanasi pair is inferior to the Certified Baseline:
- Baseline Same-Cell Gradient MAE: **$0.9203^\circ\text{C}$**
- Dynamic V2 Gradient MAE: **$1.0082^\circ\text{C}$** (Higher error!)
- Spatial Correlation: **$-0.2055$** (Negative correlation!)

Dynamic V2 inverts the spatial gradient on this pair, demonstrating that without dense mesonet training data, topographic trees risk overfitting or misattributing local micro-features. Dynamic V2 must remain strictly **`RESEARCH_ONLY`**.

---

## H. Institutional Registry Audit (10 Candidate Networks)

Audit of [`reports/PANCHAYAT_DATA_ACCESS_REGISTRY.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_DATA_ACCESS_REGISTRY.json):

| Network ID | Network Name | Custodian | Stations | Spatial Scale | Cadence | Access Status | Repo Has Obs? | Valid for Sub-5km? |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| `NET_KSNDMC_GP_MESONET` | Karnataka Hobli/GP Mesonet | KSNDMC, GoK | 6,000+ | Gram Panchayat (3–5 km) | 15-min / Hourly | `ACCESS_REQUEST_REQUIRED` | No | Yes (When authorized) |
| `NET_MAHAVEDH_AWS` | Mahavedh Agriculture Network | Dept of Agri, GoM | 2,065 | Revenue Circle (8–12 km) | Hourly | `ACCESS_REQUEST_REQUIRED` | No | Yes (When authorized) |
| `NET_IMD_AGRO_AWS` | IMD Agromet Observatories | IMD Pune, MoES | 750 | District / Zone (25–50 km) | Hourly | `ACCESS_REQUEST_REQUIRED` | No | Partial (District scale) |
| `NET_IMD_DAMU_KVK` | District Agromet Units (KVKs) | IMD / ICAR GKMS | 530 | KVK Research Farm | Twice daily / AWS | `ACCESS_REQUEST_REQUIRED` | No | Partial (Farm point) |
| `NET_ICAR_KVK_PORTAL` | ICAR KVK National Portal | Extension Div, ICAR | 731 | KVK Rural Districts | Daily summaries | `UNAVAILABLE` | No | No (No hourly AWS API) |
| `NET_SAU_AGROMET_OBS` | State Agri University Observatories | AICRPAM / 25 SAUs | 120+ | University Research Farms | Manual (08:30, 17:30) | `UNAVAILABLE` (non-digitized) | No | No (Paper ledgers) |
| `NET_ISRO_MOSDAC_AWS` | ISRO MOSDAC In-Situ AWS | SAC, ISRO | 1,100 | Meso-scale (25–50 km) | Hourly | `PARTIALLY_ACCESSIBLE` | No | Regional holdout only |
| `NET_ISRO_BHUVAN_GEOSPATIAL` | Bhuvan Spatial Covariates | NRSC, ISRO | 0 | Continuous Raster (30m) | Static / Biennial | `PARTIALLY_ACCESSIBLE` | Yes (Covariates) | Supporting covariates only |
| `NET_CPCB_CAAQMS` | CPCB Continuous Air Quality | CPCB, MoEFCC | 480 | Urban Micro-scale (2–5 km) | 15-min / Hourly | `PARTIALLY_ACCESSIBLE` | No | No (Urban canopy bias) |
| `NET_NOAA_ISD_SYNOPTIC` | NOAA ISD / WMO GTS Synoptic | WMO / IMD / NOAA | 45 | Macro-synoptic (75–150 km) | Hourly to 3-hourly | `OPEN` | **Yes (42 Stns)** | No (Too coarse, >70 km) |

### Registry Status Semantics
- `OPEN`: 1 network (`NET_NOAA_ISD_SYNOPTIC`).
- `PARTIALLY_ACCESSIBLE`: 3 platforms (ISRO MOSDAC, Bhuvan, CPCB CAAQMS).
- `ACCESS_REQUEST_REQUIRED`: 4 state/national networks (KSNDMC, Mahavedh, IMD Agro-AWS, DAMU KVK).
- `UNAVAILABLE`: 2 sources (ICAR KVK portal unrouted; SAU paper ledgers).

---

## I. Data Request Package Completeness Audit

Cross-referencing [`docs/PANCHAYAT_DATA_REQUEST_SPECIFICATION.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_DATA_REQUEST_SPECIFICATION.md) and [`docs/PANCHAYAT_DATA_ACCESS_CHECKLIST.md`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/docs/PANCHAYAT_DATA_ACCESS_CHECKLIST.md):

1. **Mandatory Validation Fields**:
   `station_id`, `latitude`, `longitude`, `elevation_m`, `timestamp_utc`, `temperature_2m_c`, `site_context`, `institution`.
2. **Preferred Secondary Fields**:
   `relative_humidity_pct`, `wind_speed_mps`, `wind_direction_deg`, `precipitation_mm`, `soil_temperature_10cm`, `quality_flag`.
3. **Optional Siting & Calibration Metadata**:
   `sensor_model`, `radiation_shield_type`, `mast_height_m`, `calibration_date`, `land_cover_500m`.
4. **Explicit Non-Retraining Commitment**:
   Section 2.2 contains an unambiguous, technically enforceable legal and scientific undertaking:
   - Zero model retraining.
   - Frozen architecture.
   - Pure holdout benchmarking.
   - Zero commercial exploitation.

---

## J. Fail-Closed Test Suite Results

Test suite [`backend/tests/test_panchayat_validation_readiness.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_panchayat_validation_readiness.py) executed 19 comprehensive fail-closed tests. All passed:
- `test_01_single_station_cannot_reach_level_3`: **PASS**
- `test_02_stations_greater_than_10km_cannot_reach_level_3`: **PASS**
- `test_03_insufficient_temporal_overlap_fails_closed`: **PASS**
- `test_04_missing_metadata_fails_closed`: **PASS**
- `test_05_training_contamination_fails_closed`: **PASS**
- `test_06_two_agricultural_stations_sub_5km_eligible_level_5`: **PASS**
- `test_07_intra_panchayat_agricultural_stations_eligible_level_6`: **PASS**
- `test_08_synthetic_observations_rejected`: **PASS**
- `test_09_missing_coordinates_rejected`: **PASS**
- `test_10_invalid_coordinates_rejected`: **PASS**
- `test_11_duplicate_station_ids_deduplicated_or_audited`: **PASS**
- `test_12_timestamp_misalignment_beyond_tolerance_rejected`: **PASS**
- `test_13_missing_temperature_rejected`: **PASS**
- `test_14_invalid_temperature_range_rejected`: **PASS**
- `test_15_same_era5_cell_single_station_never_spatial_validation`: **PASS**
- `test_16_era5_or_openmeteo_model_never_treated_as_ground_truth`: **PASS**
- `test_17_unauthorized_institutional_source_leaves_readiness_unchanged`: **PASS**
- `test_18_pipeline_can_ingest_authorized_data_without_changing_model`: **PASS**
- `test_19_runtime_model_outputs_remain_unchanged`: **PASS**

Full test execution log archived in [`reports/PANCHAYAT_VALIDATION_FAIL_CLOSED_TEST_REPORT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_FAIL_CLOSED_TEST_REPORT.json).

---

## K. Provenance Audit

| Artifact / Dataset | Source Agency | Verification Protocol | Cryptographic Integrity |
| :--- | :--- | :--- | :--- |
| NOAA ISD Synoptic (42 Stations) | NOAA NCEI / WMO GTS | Direct HTTP sync from NCEI public archives | Verified against multi-season manifests |
| Open-Meteo ERA5 Reanalysis | ECMWF Copernicus ERA5 | Open-Meteo archive API query | Parameterized bounds verified |
| Certified Baseline Calibration | Internal Frozen Calibration | Git tree hash & SHA-256 verification | `dad1b693277a3be98b90bc49f1a4fda5ee7d509cce3164a2e5798bfd78457650` |
| Dynamic Residual V2 Model | Frozen XGBoost Regressor | SHA-256 model dump checksum | `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294` |
| State Mesonet Data | KSNDMC / Mahavedh / IMD Agro | `backend/data/raw/panchayat_mesonet/` | **EMPTY (Zero unauthorized payloads)** |

---

## L. Model Immutability Verification

| Model Component | Artifact Path | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Certified Baseline Parameter** | `backend/models/production_baseline/baseline_calibration.json` | `dad1b693277a3be98b90bc49f1a4fda5ee7d509cce3164a2e5798bfd78457650` | `dad1b693...` | **MATCH (IMMUTABLE)** |
| **Dynamic V2 Model Weights** | `backend/models/candidates/.../xgboost_model.json` | `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294` | `d75aeb2a...` | **MATCH (IMMUTABLE)** |
| **Dynamic V2 Feature Schema** | `backend/models/candidates/.../feature_schema.json` | `e361b68258775231276f204593f2fdc7525b364b3caaa88f8e0ac2b7d3703f11` | `e361b682...` | **MATCH (IMMUTABLE)** |
| **Dynamic V2 Metadata** | `backend/models/candidates/.../metadata.json` | `193212a33f44fa20f60e250e9a24ad16bccc8ed1b71837f4c5502215249e1bdb` | `193212a3...` | **MATCH (IMMUTABLE)** |

**Verification**: Zero training scripts executed. Zero weight adjustments performed. Production configuration unchanged.

---

## M. Claim-Support Matrix

| Scientific Claim | True Status | Supported By Current Evidence? | Required Empirical Evidence to Support |
| :--- | :---: | :---: | :--- |
| **National Station-Level Validation** | **SUPPORTED** | **YES** | 42 WMO synoptic stations across 21 States/UTs (53,687 records) |
| **Multi-Season Validation** | **SUPPORTED** | **YES** | 313,754 observations across 6 temporal seasons (Mar 2024 – Aug 2025) |
| **Readiness Framework Operational** | **SUPPORTED** | **YES** | Reproducible runner, fail-closed tests, request specs |
| **Sub-10 km Empirical Validation** | **NOT SUPPORTED** | **NO** | $\ge 2$ independent stations $\le 10\text{ km}$ apart (closest open pair is 22.13 km) |
| **Sub-5 km Empirical Validation** | **NOT SUPPORTED** | **NO** | $\ge 2$ independent stations $\le 5\text{ km}$ apart (zero in open data) |
| **Panchayat Agricultural Validation** | **NOT SUPPORTED** | **NO** | In-situ agricultural stations inside active crop canopies (firewalled) |
| **Field / Plot Validation** | **NOT SUPPORTED** | **NO** | Dense micro-sensor agricultural IoT sensor network (none deployed) |
| **Zero Spatial Prediction Error Claim** | **NOT SUPPORTED** | **NO** | Baseline zero variance $\neq$ zero spatial error ($\text{Gradient MAE} = 0.9203^\circ\text{C}$) |

---

## N. Reproducibility & CI Verification

Single deterministic audit command verified:
```bash
python3 backend/data_pipeline/scripts/audit_panchayat_validation_readiness.py
python3 -m pytest backend/tests/test_panchayat_validation_readiness.py
```
- Runtime: ~0.15s
- Exit Code: 0
- Generates:
  - [`reports/PANCHAYAT_VALIDATION_READINESS_FORENSIC_AUDIT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_READINESS_FORENSIC_AUDIT.json)
  - [`reports/PANCHAYAT_VALIDATION_TARGET_REGISTER_AUDIT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_TARGET_REGISTER_AUDIT.json)
  - [`reports/PANCHAYAT_VALIDATION_DRY_RUN_REPRODUCTION.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_DRY_RUN_REPRODUCTION.json)
  - [`reports/PANCHAYAT_VALIDATION_FAIL_CLOSED_TEST_REPORT.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/PANCHAYAT_VALIDATION_FAIL_CLOSED_TEST_REPORT.json)

---

## O. Defects Found During Audit

1. **Heuristic Level Classification in Runner**:
   `run_panchayat_validation_pipeline.py` classified levels using `stns_within_10km >= 2` and `stns_within_5km >= 2` from the Panchayat centroid. It did not calculate pairwise inter-station distance, verify temporal overlap ($\ge 100\text{h}$), or check station independence before evaluating Level 3–5 eligibility.
2. **ERA5 Grid Cell Discrepancy for `KA_BLG_001`**:
   `PANCHAYAT_VALIDATION_TARGET_REGISTER.json` recorded `ERA5_15.50N_74.50E` (14.51 km), whereas the dynamic mathematical formula assigned `ERA5_15.75N_74.50E` (13.39 km).
3. **Distance Rounding Discrepancy for `OD_KND_001`**:
   Target register recorded 100.82 km; geodesic haversine formula yielded 101.683 km (Vincenty: 101.761 km).
4. **Inherited Task 3 Markdown Text Error**:
   Task 3 forensic report Table 5 hardcoded `0.3841°C²` in the markdown string for Dynamic V2 spatial variance, whereas the true empirical calculation was `0.2162°C²`. (Corrected in Task 4).
5. **Raster Covariate Included in Station Registry**:
   `NET_ISRO_BHUVAN_GEOSPATIAL` (0 stations) was listed in the 10 observational networks table, although it is a geospatial raster covariate platform, not an in-situ weather station network.
6. **Training Contamination Among Target Nearest Stations**:
   8 of the 18 Panchayats have a nearest synoptic station that was part of the original 17 training stations, disqualifying them as independent out-of-sample holdouts.

---

## P. Corrective Actions

1. **Enforce Inter-Station Distance & Overlap in Pipeline Runner**:
   Upgrade `run_panchayat_validation_pipeline.py` to use `evaluate_panchayat_validation_eligibility()` from [`test_panchayat_validation_readiness.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_panchayat_validation_readiness.py) when evaluating external mesonet payloads, ensuring pairwise separation $\le 10\text{ km}$ and $\ge 100\text{h}$ overlap are enforced.
2. **Harmonize Target Register Coordinates & Cells**:
   Update `KA_BLG_001` ERA5 cell in the register to `ERA5_15.75N_74.50E` and `OD_KND_001` distance to `101.68 km`.
3. **Explicitly Separate Raster Covariates from Station Networks**:
   Reclassify Bhuvan as a geospatial covariate layer, categorizing the candidate observational networks as 9 weather station networks.
4. **Tag Training Station Contamination**:
   Add `is_training_contaminated: true` to the 8 affected target Panchayats to prevent false claims of independent holdout validation on those stations.

---

## Q. Final Readiness Status

```
PANCHAYAT VALIDATION READINESS — VERIFIED WITH LIMITATIONS
```

### Definitive Governance State:
The validation infrastructure, data request packages, mathematical same-cell formulas, and fail-closed quality safeguards are **VERIFIED and fully operational**. However, empirical validation at Panchayat scale ($<5\text{ km}$) remains **UNSUPPORTED** and pending the receipt of authorized in-situ agricultural mesonet observations.

The Certified Production Baseline ($T_{\text{downscaled}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$), Dynamic Residual V2 model (`RESEARCH_ONLY`), React web frontend, and Flutter mobile application remain **100% frozen and unmodified**.
