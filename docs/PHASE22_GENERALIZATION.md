# Phase 22: Spatial, Temporal & Topographic Generalization Audit

**Experiment**: `EXP_INDIA_PRODUCTION_CERTIFICATION_PHASE22`  
**SIH Problem Statement**: 26074 — Agro-Meteorological Downscaling  
**Date**: 2026-09-17  
**Status**: AUDITED GENERALIZATION BENCHMARK  

---

## 1. Overview

This document presents the complete cross-validation and stratification benchmarks assessing whether the XGBoost residual downscaling candidate generalizes reliably across spatial, temporal, and topographic dimensions without memorizing localized training stations.

---

## 2. Leave-One-Station-Out (LOSO) Cross-Validation (17 Independent Folds)

In each fold, exactly one station's complete observation record was quarantined. The model was trained on the remaining 16 stations and evaluated strictly on the unseen held-out station.

| Fold # | Held-Out Station ID | Station Name | Physiographic Region | Station N | Raw ERA5 MAE | Bias-Corrected MAE | XGBoost Model MAE | Raw→XGB Δ | Bias→XGB Δ | Better than Raw | Better than Bias |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `421470-99999` | Mukteshwar Kumaon | North / Himalayan | 361 | 1.3978 | 1.3283 | **1.2805** | -0.1173 | **-0.0478** | **YES** | **YES** |
| 2 | `420830-99999` | Shimla | North / Himalayan | 351 | **1.2074** | 1.5530 | 1.7237 | +0.5163 | +0.1707 | NO | NO |
| 3 | `420270-99999` | Srinagar | North / Himalayan | 715 | 1.7201 | 1.5825 | **1.4102** | -0.3099 | **-0.1723** | **YES** | **YES** |
| 4 | `421110-99999` | Dehradun | North / Himalayan | 721 | 2.0277 | **1.5178** | 1.6802 | -0.3475 | +0.1623 | **YES** | NO |
| 5 | `421820-99999` | New Delhi Safdarjung | Indo-Gangetic Plain | 727 | 1.7901 | 1.4865 | **1.3375** | -0.4526 | **-0.1490** | **YES** | **YES** |
| 6 | `423690-99999` | Lucknow Amausi | Indo-Gangetic Plain | 2,006 | 1.4823 | 1.2927 | **1.1699** | -0.3124 | **-0.1228** | **YES** | **YES** |
| 7 | `424790-99999` | Varanasi Babatpur | Indo-Gangetic Plain | 1,944 | 1.4334 | **1.1551** | 2.1259 | +0.6925 | +0.9708 | NO | NO |
| 8 | `424920-99999` | Patna Airport | Indo-Gangetic Plain | 2,127 | 2.2028 | 1.6729 | **1.4721** | -0.7307 | **-0.2008** | **YES** | **YES** |
| 9 | `423480-99999` | Jaipur Sanganer | West / Arid-SemiArid | 2,158 | 1.4090 | 1.3023 | **1.1741** | -0.2349 | **-0.1282** | **YES** | **YES** |
| 10 | `423390-99999` | Jodhpur | West / Arid-SemiArid | 812 | 1.4127 | **1.2052** | 1.3258 | -0.0869 | +0.1205 | **YES** | NO |
| 11 | `426470-99999` | Ahmedabad | West / Arid-SemiArid | 2,145 | 1.3166 | 1.3023 | **1.2136** | -0.1030 | **-0.0888** | **YES** | **YES** |
| 12 | `426670-99999` | Bhopal Bairagarh | Central Plateau | 795 | 1.3892 | 1.4037 | **1.2773** | -0.1119 | **-0.1265** | **YES** | **YES** |
| 13 | `427790-99999` | Jabalpur | Central Plateau | 712 | **1.8586** | 2.2689 | 2.1805 | +0.3219 | **-0.0884** | NO | **YES** |
| 14 | `428670-99999` | Nagpur Sonegaon | Central Plateau | 2,152 | 1.5442 | **1.2840** | 1.4570 | -0.0872 | +0.1729 | **YES** | NO |
| 15 | `429710-99999` | Bhubaneswar | East Delta-Plain | 2,002 | **1.2079** | 1.2713 | 1.3377 | +0.1298 | +0.0664 | NO | NO |
| 16 | `428090-99999` | Kolkata Dum Dum | East Delta-Plain | 2,157 | 1.4426 | 1.0339 | **1.0307** | -0.4119 | **-0.0032** | **YES** | **YES** |
| 17 | `424100-99999` | Guwahati Borjhar | Northeast Hills | 2,064 | 2.0034 | 1.5067 | **1.3187** | -0.6847 | **-0.1881** | **YES** | **YES** |

### LOSO Performance Statistics:
- **Improvement Rate vs. Raw ERA5**: **13 of 17 stations (76.5%)**
- **Improvement Rate vs. Scalar Bias Correction**: **11 of 17 stations (64.7%)**
- **Mean Incremental Delta (Bias $\rightarrow$ XGB)**: $+0.0205\ ^\circ\text{C}$ (Average across folds showed slight net degradation due to extreme outliers)
- **Median Incremental Delta**: **$-0.0884\ ^\circ\text{C}$**
- **Best Incremental Improvement**: **$-0.2008\ ^\circ\text{C}$** (Patna Airport)
- **Worst Incremental Degradation**: **$+0.9708\ ^\circ\text{C}$** (Varanasi Babatpur)

---

## 3. Leave-One-Region-Out Spatial Cross-Validation (6 Regimes)

Evaluates whether the system can transfer to an entirely unseen physiographic region without any training observations from that territory.

| Held-Out Region | Station Count | Held-Out N | Raw ERA5 MAE | Bias-Corrected MAE | XGBoost Model MAE | Raw→XGB Δ | Bias→XGB Δ | Transfer Result |
|---|---|---|---|---|---|---|---|---|
| **Central Plateau** | 3 | 794 | 1.3525 | **1.1770** | 1.2671 | -0.0854 | +0.0902 | Successful vs Raw / Worse than Bias |
| **East Delta-Plain** | 2 | 922 | 1.5057 | **1.0909** | 1.2052 | -0.3005 | +0.1144 | Successful vs Raw / Worse than Bias |
| **Indo-Gangetic Plain** | 4 | 1,511 | 1.9263 | **1.4626** | 1.7347 | -0.1916 | +0.2722 | Successful vs Raw / Worse than Bias |
| **North / Himalayan** | 4 | 468 | 1.7171 | 1.4877 | **1.4079** | -0.3092 | **-0.0798** | **Full Transfer Success** |
| **Northeast Hills** | 1 | 449 | **1.4884** | **1.1544** | 1.5487 | +0.0603 | +0.3943 | Regional Degradation |
| **West / Arid-SemiArid** | 3 | 1,144 | 1.3694 | 1.1387 | **1.1199** | -0.2495 | **-0.0188** | **Full Transfer Success** |

### Key Regional Finding:
- While XGBoost improved upon Raw ERA5 in 5 of 6 held-out regions, it beat simple scalar Bias Correction in **only 2 of 6 regions** (North/Himalayan and West/Arid).
- In the humid alluvial Gangetic and deltaic plains, simple scalar bias correction generalized far more safely than non-linear decision trees trained on arid or plateau stations.

---

## 4. Error Stratification Analysis

### 4.1 Elevation Strata Breakdown (Frozen Test Set)
| Elevation Band | Test Observations ($N$) | Raw ERA5 MAE | Bias-Corrected MAE | XGBoost MAE | Incremental XGB Benefit |
|---|---|---|---|---|---|
| **< 100 m MSL** (Alluvial / Delta) | 2,274 | 1.8398 °C | 1.3837 °C | **1.1636 °C** | **-0.2201 °C** |
| **100 m – 500 m MSL** (Plain / Low Plateau) | 1,907 | 1.5653 °C | **1.1963 °C** | 1.2185 °C | +0.0222 °C |
| **500 m – 1,500 m MSL** (Highland / Foothill) | 318 | 1.5868 °C | 1.1392 °C | **1.0691 °C** | **-0.0701 °C** |
| **> 1,500 m MSL** (Himalayan Ridge) | 309 | 1.5661 °C | 1.4215 °C | **1.3683 °C** | **-0.0532 °C** |

### 4.2 Diurnal Breakdown (Day vs. Night)
| Diurnal Phase | Test Observations ($N$) | Raw ERA5 MAE | Bias-Corrected MAE | XGBoost MAE | Key Driver |
|---|---|---|---|---|---|
| **Daytime (06:00 – 18:00 UTC)** | 2,752 | 1.6322 °C | 1.3105 °C | **1.2184 °C** | Solar heating curve adjustment |
| **Nighttime (19:00 – 05:00 UTC)** | 2,536 | 1.5457 °C | 1.2180 °C | **1.1670 °C** | Radiational cooling offset |
