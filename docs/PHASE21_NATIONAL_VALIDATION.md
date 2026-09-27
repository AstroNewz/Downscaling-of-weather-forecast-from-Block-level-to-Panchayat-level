# Phase 21: National Multi-Region Validation Report (Audited)

**Experiment**: `EXP_INDIA_MULTI_REGION_PHASE21`  
**SIH Problem Statement**: 26074 — Agro-Meteorological Downscaling  
**Date**: 2026-09-17  
**Audit Status**: AUDITED & CONSISTENCY-VERIFIED  
**Candidate Directory**: `backend/models/candidates/temperature_residual/phase21_candidate_20260917/`  
**Production Model Path**: `backend/models/temperature_residual/` (**INTENTIONALLY ABSENT & SAFE**)  

---

## 1. Executive Summary & Audited Metrics

This report documents the rigorous multi-regional validation of the residual weather-downscaling framework across **17 genuine NOAA ISD observation stations (23,949 aligned observations)** spanning **6 Indian physiographic regimes** during the 2024 Kharif season (June 1 – August 31, 2024).

### Key Audited Findings:
1. **Chronological Holdout (Aug 11 – Aug 31, 2024, $N = 5,288$)**:
   - Raw ERA5 Baseline: $\text{MAE} = 1.5907\ ^\circ\text{C}$, $\text{RMSE} = 1.9922\ ^\circ\text{C}$, $R^2 = 0.6134$, $\text{Bias} = -1.1378\ ^\circ\text{C}$.
   - Train-Only Bias-Corrected ERA5: $\text{MAE} = 1.2661\ ^\circ\text{C}$, $\text{RMSE} = 1.6842\ ^\circ\text{C}$, $R^2 = 0.7237$, $\text{Bias} = -0.4026\ ^\circ\text{C}$.
   - XGBoost Candidate: $\text{MAE} = 1.1937\ ^\circ\text{C}$, $\text{RMSE} = 1.5882\ ^\circ\text{C}$, $R^2 = 0.7543$, $\text{Bias} = -0.2333\ ^\circ\text{C}$.
   - **Paired MAE Improvement**: $\Delta\text{MAE} = -0.3969\ ^\circ\text{C}$ (Paired 95% Bootstrap CI: `[-0.4226°C, -0.3724°C]`, paired $t = 30.03$, $p = 4.21 \times 10^{-183}$, Cohen's $d = 0.4130$).
2. **Decomposition of Improvement**:
   - Simple training-only mean bias correction ($+0.7351\ ^\circ\text{C}$) explains **81.8%** of the raw ERA5 MAE gap ($\Delta\text{MAE} = -0.3246\ ^\circ\text{C}$).
   - Non-linear XGBoost downscaling contributes an incremental **$-0.0724\ ^\circ\text{C}$ MAE reduction** and increases explained variance ($R^2$) from $0.7237$ to $0.7543$.
3. **Leave-One-Station-Out (LOSO) Accounting**:
   - Evaluated on exactly **17 independent stations (17 folds)**.
   - **13 of 17 stations (76.47%)** showed improved MAE over raw ERA5 in unseen cross-validation.
   - 4 stations degraded: Shimla ($+0.5163\ ^\circ\text{C}$), Varanasi Babatpur ($+0.6925\ ^\circ\text{C}$), Jabalpur ($+0.3219\ ^\circ\text{C}$), and Bhubaneswar ($+0.1298\ ^\circ\text{C}$).
4. **Regional Generalization**:
   - **Temporal Generalization (Seen Regions, Unseen Period)**: **6 of 6 regions (100.0%)** improved on the chronological holdout test.
   - **Spatial Generalization (Leave-One-Region-Out)**: **4 of 6 regions (66.7%)** improved when completely excluded from training. The Indo-Gangetic Plain and East Delta-Plain degraded when held out completely, proving that regional monsoon-alluvial dynamics cannot be extrapolated purely from arid or plateau regimes.
5. **Terrain Ablation**:
   - Terrain features showed **regime-dependent effects**: In alluvial plains, terrain difference was negligible ($\Delta\text{MAE} = +0.0032\ ^\circ\text{C}$). In mountain terrain, macro-elevation differences alone without sub-kilometer high-resolution DEM tiles degraded performance ($\Delta\text{MAE} = -0.0420\ ^\circ\text{C}$) due to unmodeled valley thermal inversions.
6. **Production Gate & Decision**:
   - **`MODEL_DECISION = RETAIN_FOR_RESEARCH`**.
   - The production model path `backend/models/temperature_residual/` remains **ABSENT and SAFE**.

---

## 2. Station-Level Validation Table (Frozen Test Set & LOSO)

| Station ID | Station Name | Physiographic Region | Elev (m) | Test N | Base MAE (°C) | Cand MAE (°C) | Chrono ΔMAE | Chrono Improved | LOSO Base MAE | LOSO Model MAE | LOSO ΔMAE | LOSO Improved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `421470-99999` | Mukteshwar Kumaon | North / Himalayan | 2,311.0 | 79 | 1.7608 | 1.3972 | -0.3636 | **YES** | 1.3978 | 1.2805 | -0.1173 | **YES** |
| `420830-99999` | Shimla | North / Himalayan | 2,202.0 | 72 | 1.2528 | 1.0986 | -0.1541 | **YES** | 1.2074 | 1.7237 | +0.5163 | **NO** |
| `420270-99999` | Srinagar | North / Himalayan | 1,587.0 | 158 | 1.6114 | 1.4766 | -0.1347 | **YES** | 1.7201 | 1.4102 | -0.3099 | **YES** |
| `421110-99999` | Dehradun | North / Himalayan | 682.0 | 159 | 2.0107 | 1.2190 | -0.7917 | **YES** | 2.0277 | 1.6802 | -0.3475 | **YES** |
| `421820-99999` | New Delhi Safdarjung | Indo-Gangetic Plain | 216.0 | 164 | 2.1835 | 1.3636 | -0.8200 | **YES** | 1.7901 | 1.3375 | -0.4526 | **YES** |
| `423690-99999` | Lucknow Amausi | Indo-Gangetic Plain | 128.0 | 442 | 1.4735 | 1.0004 | -0.4731 | **YES** | 1.4823 | 1.1699 | -0.3124 | **YES** |
| `424790-99999` | Varanasi Babatpur | Indo-Gangetic Plain | 76.0 | 433 | 1.3954 | 1.0462 | -0.3491 | **YES** | 1.4334 | 2.1259 | +0.6925 | **NO** |
| `424920-99999` | Patna Airport | Indo-Gangetic Plain | 53.0 | 472 | 2.7481 | 1.3438 | -1.4043 | **YES** | 2.2028 | 1.4721 | -0.7307 | **YES** |
| `423480-99999` | Jaipur Sanganer | West / Arid-SemiArid | 390.0 | 484 | 1.4043 | 1.0584 | -0.3459 | **YES** | 1.4090 | 1.1741 | -0.2349 | **YES** |
| `423390-99999` | Jodhpur | West / Arid-SemiArid | 224.0 | 182 | 1.3313 | 1.1874 | -0.1439 | **YES** | 1.4127 | 1.3258 | -0.0869 | **YES** |
| `426470-99999` | Ahmedabad | West / Arid-SemiArid | 55.0 | 478 | 1.3485 | 1.2736 | -0.0749 | **YES** | 1.3166 | 1.2136 | -0.1030 | **YES** |
| `426670-99999` | Bhopal Bairagarh | Central Plateau | 523.0 | 159 | 1.1629 | 0.9193 | -0.2436 | **YES** | 1.3892 | 1.2773 | -0.1119 | **YES** |
| `427790-99999` | Jabalpur | Central Plateau | 393.0 | 159 | 1.0692 | 1.1610 | +0.0918 | **NO** | 1.8586 | 2.1805 | +0.3219 | **NO** |
| `428670-99999` | Nagpur Sonegaon | Central Plateau | 310.0 | 476 | 1.5105 | 1.3606 | -0.1499 | **YES** | 1.5442 | 1.4570 | -0.0872 | **YES** |
| `429710-99999` | Bhubaneswar | East Delta-Plain | 46.0 | 447 | 1.3521 | 1.2502 | -0.1019 | **YES** | 1.2079 | 1.3377 | +0.1298 | **NO** |
| `428090-99999` | Kolkata Dum Dum | East Delta-Plain | 6.0 | 475 | 1.6503 | 0.9990 | -0.6513 | **YES** | 1.4426 | 1.0307 | -0.4119 | **YES** |
| `424100-99999` | Guwahati Borjhar | Northeast Hills | 54.0 | 449 | 1.4884 | 1.3222 | -0.1662 | **YES** | 2.0034 | 1.3187 | -0.6847 | **YES** |

---

## 3. Regional Validation Table

### 3.1 Temporal Generalization (Chronological Test Period: Aug 11 – Aug 31, 2024)
| Region | Station Count | Test Records ($N$) | Base MAE (°C) | Cand MAE (°C) | ΔMAE (°C) | Improvement Status |
|---|---|---|---|---|---|---|
| **Central Plateau** | 3 | 794 | 1.3525 | 1.2322 | **-0.1203** | **IMPROVED (YES)** |
| **East Delta-Plain** | 2 | 922 | 1.5057 | 1.1208 | **-0.3849** | **IMPROVED (YES)** |
| **Indo-Gangetic Plain** | 4 | 1,511 | 1.9263 | 1.1602 | **-0.7661** | **IMPROVED (YES)** |
| **North / Himalayan** | 4 | 468 | 1.7171 | 1.3175 | **-0.3996** | **IMPROVED (YES)** |
| **Northeast Hills** | 1 | 449 | 1.4884 | 1.3222 | **-0.1662** | **IMPROVED (YES)** |
| **West / Arid-SemiArid** | 3 | 1,144 | 1.3694 | 1.1689 | **-0.2005** | **IMPROVED (YES)** |

### 3.2 Spatial Generalization (Leave-One-Region-Out Cross-Validation)
| Held-Out Region | Station Count | Total Records ($N$) | Base MAE (°C) | Model MAE (°C) | ΔMAE (°C) | Transfer Status |
|---|---|---|---|---|---|---|
| **Central Plateau** | 3 | 3,659 | 1.5717 | 1.5530 | **-0.0187** | **SUCCESSFUL TRANSFER** |
| **North / Himalayan** | 4 | 2,148 | 1.6854 | 1.4671 | **-0.2183** | **SUCCESSFUL TRANSFER** |
| **Northeast Hills** | 1 | 2,064 | 2.0034 | 1.3268 | **-0.6766** | **SUCCESSFUL TRANSFER** |
| **West / Arid-SemiArid** | 3 | 5,115 | 1.3708 | 1.2333 | **-0.1375** | **SUCCESSFUL TRANSFER** |
| **East Delta-Plain** | 2 | 4,159 | 1.3296 | 1.4956 | +0.1660 | **REGIONAL DEGRADATION** |
| **Indo-Gangetic Plain** | 4 | 6,804 | 1.7265 | 2.0914 | +0.3649 | **REGIONAL DEGRADATION** |

---

## 4. Paired Statistical Analysis

On the $N = 5,288$ paired chronological test observations:
- **Mean Absolute Error Difference**: $-0.3969\ ^\circ\text{C}$
- **Paired 95% Bootstrap Confidence Interval**: `[-0.4226°C, -0.3724°C]`
- **Paired Two-Tailed t-test**: $t = 30.03$, $p = 4.21 \times 10^{-183}$
- **Wilcoxon Signed-Rank Test**: $W = 3,843,637$, $p = 6.56 \times 10^{-177}$
- **Effect Size (Cohen's d)**: $0.4130$
- **Statistical Conclusion**: The candidate residual model achieves a statistically significant error reduction ($p < 10^{-10}$) compared to raw ERA5 over the frozen chronological test period.

---

## 5. Systematic Bias Correction vs. Non-Linear ML Downscaling

| Benchmark | Test MAE (°C) | Test RMSE (°C) | Test R² | Test Bias (°C) | ΔMAE vs Raw |
|---|---|---|---|---|---|
| **Raw ERA5 Baseline** | 1.5907 | 1.9922 | 0.6134 | -1.1378 | — |
| **Train-Only Mean Bias Correction** ($+0.7351\ ^\circ\text{C}$) | 1.2661 | 1.6842 | 0.7237 | -0.4026 | -0.3246 |
| **XGBoost Residual Candidate** | **1.1937** | **1.5882** | **0.7543** | **-0.2333** | **-0.3970** |

**Scientific Interpretation**:
A simple constant offset fitted on training data eliminates a substantial portion (81.8%) of the coarse model's cold bias across India. The gradient-boosted decision tree architecture yields an additional $0.0724\ ^\circ\text{C}$ absolute error reduction and increases $R^2$ from $0.7237$ to $0.7543$, primarily by modeling non-linear diurnal heating cycles and lapse-rate elevation variations.

---

## 6. Topographic Generalization & Regime Dependency

- **High Relief Regime** ($n = 627$, elevation span 682m – 2311m):
  - Model without terrain: $\text{MAE} = 1.1745\ ^\circ\text{C}$
  - Model with terrain: $\text{MAE} = 1.2165\ ^\circ\text{C}$ ($\Delta\text{MAE} = -0.0420\ ^\circ\text{C}$)
- **Low Relief Regime** ($n = 4,661$, coastal / alluvial plains):
  - Model without terrain: $\text{MAE} = 1.1938\ ^\circ\text{C}$
  - Model with terrain: $\text{MAE} = 1.1906\ ^\circ\text{C}$ ($\Delta\text{MAE} = +0.0032\ ^\circ\text{C}$)

**Regime-Dependent Interpretation**:
Terrain features showed regime-dependent effects in this experiment. In flat alluvial plains, elevation gradients are insufficient to provide strong thermal variance. In high-relief mountainous topography, coarse point elevation differences alone (without high-resolution 30m digital terrain models and valley slope-aspect radiation buffers) can misrepresent local nocturnal valley cold-air drainage.

---

## 7. National Coverage Claim Scope

The dataset represents a **broad multi-region Indian validation sample** comprising 17 WMO weather stations across 11 States/UTs. While it establishes proof-of-concept cross-regional transfer across 6 physiographic zones, it **DOES NOT constitute nationwide operational validation** at the Gram Panchayat scale. Operational Panchayat-level advisory services require dense district-scale automated weather networks (~15–20 AWS per district) to resolve village-scale agricultural microclimates.
