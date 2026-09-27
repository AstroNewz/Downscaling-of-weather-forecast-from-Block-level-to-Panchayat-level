# Dynamic Residual Downscaling Model v2 — Scientific Evaluation Report
**Smart India Hackathon Problem Statement 26074 — Agro-Meteorological Advisory Services**
**Experiment ID**: `EXP_INDIA_DYNAMIC_RESIDUAL_V2`  
**Generated At**: 2026-09-17 20:19:21 UTC  
**Governance Status**: `RESEARCH_ONLY`  
**Production Candidate Decision**: `RETAIN_FOR_RESEARCH`  

---

## 1. Executive Summary & Scientific Baseline Protection

The production baseline for the SIH Agro-Meteorological Downscaling platform remains strictly protected and immutable:

$$\Delta T_{\text{baseline}} = +0.7351^\circ\text{C}$$

This research experiment systematically evaluates **Dynamic Residual Downscaling Model v2**, wherein local temperature correction varies dynamically according to meteorological drivers, static topography, and diurnal/seasonal cycles:

$$\Delta T_{\text{dynamic}}(t, x) = f(T_{\text{coarse}}, \text{RH}, \text{wind}, \text{precip}, \text{elev}, \text{slope}, \text{aspect}, \text{LULC}, \text{lat}, \text{lon}, t_{\text{hour}}, t_{\text{doy}})$$

$$T_{\text{dynamic}}(t, x) = T_{\text{coarse}}(t, x) + \text{clamp}(\Delta T_{\text{dynamic}}(t, x), -8.0, +8.0)$$

### Non-Negotiable Safeguards
- **Zero Synthetic Data**: Evaluated strictly on 23,949 genuine hourly observation pairs across 17 WMO Indian surface weather stations during Kharif 2024.
- **Strictly Isolated Holdout**: Evaluated on a frozen chronologically held-out test partition (August 11–31, 2024; 5,288 observations).
- **Production Isolation**: The production registry (`models/temperature_residual/`) remains pristine and untouched. Candidate artifacts reside exclusively in `models/candidates/temperature_residual/dynamic_temperature_residual_v2/`.

---

## 2. Model Ablation Study on Frozen Test Partition

Evaluation across 5,288 observations (2024-08-11 to 2024-08-31):

| Model Variant | Formulation | Test MAE (°C) | Test RMSE (°C) | $R^2$ | Bias (°C) | $\Delta$ MAE vs Base |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Candidate A (Constant)** | $T_{\text{coarse}} + 0.7351^\circ\text{C}$ | **1.2661** | **1.6842** | **0.7237** | **-0.4027** | *Reference* |
| **Candidate B (Weather-only)** | ERA5 Weather + Cyclic Time | 1.2215 | 1.6103 | 0.7474 | -0.1363 | -0.0446°C |
| **Candidate C (Weather + Geography)** | Candidate B + DEM / Topo / LULC | 1.1690 | 1.5580 | 0.7636 | -0.1738 | -0.0971°C |
| **Candidate D (Full Interactions)** | Candidate C + Non-linear Interactions | **1.1760** | **1.5650** | **0.7614** | **-0.1597** | **-0.0901°C** |

### 95% Bootstrap Confidence Intervals (500 iterations)
- **Baseline Candidate A**: MAE [1.2358, 1.2967]°C | RMSE [1.6427, 1.7281]°C
- **Dynamic Candidate D**: MAE [1.1501, 1.2034]°C | RMSE [1.5279, 1.6018]°C

---

## 3. Spatial Generalization: Leave-One-Station-Out (LOSO)

Leave-One-Station-Out cross-validation measures out-of-sample performance when an entire weather station is withheld during model training:

| Station ID | Station Name | Physiographic Regime | Obs ($n$) | Dyn MAE (°C) | Base MAE (°C) | $\Delta$ MAE (°C) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `420270-99999` | Srinagar | North / Himalayan | 715 | 1.4577 | 1.5818 | -0.1241 |
| `420830-99999` | Shimla | North / Himalayan | 351 | 1.5908 | 1.4784 | +0.1124 |
| `421110-99999` | Dehradun | North / Himalayan | 721 | 1.8230 | 1.5636 | +0.2594 |
| `421470-99999` | Mukteshwar Kumaon | North / Himalayan | 361 | 1.2847 | 1.3163 | -0.0316 |
| `421820-99999` | New Delhi Safdarjung | Indo-Gangetic Plain | 727 | 1.4027 | 1.5136 | -0.1109 |
| `423390-99999` | Jodhpur | West / Arid-SemiArid | 812 | 1.4056 | 1.2090 | +0.1966 |
| `423480-99999` | Jaipur Sanganer | West / Arid-SemiArid | 2,158 | 1.1705 | 1.2944 | -0.1239 |
| `423690-99999` | Lucknow Amausi | Indo-Gangetic Plain | 2,006 | 1.1380 | 1.3012 | -0.1632 |
| `424100-99999` | Guwahati Borjhar | Northeast Hills | 2,064 | 1.3248 | 1.5209 | -0.1961 |
| `424790-99999` | Varanasi Babatpur | Indo-Gangetic Plain | 1,944 | 2.0577 | 1.1685 | +0.8892 |
| `424920-99999` | Patna Airport | Indo-Gangetic Plain | 2,127 | 1.3464 | 1.6773 | -0.3309 |
| `426470-99999` | Ahmedabad | West / Arid-SemiArid | 2,145 | 1.1604 | 1.2718 | -0.1114 |
| `426670-99999` | Bhopal Bairagarh | Central Plateau | 795 | 1.2338 | 1.3693 | -0.1355 |
| `427790-99999` | Jabalpur | Central Plateau | 712 | 2.1224 | 2.1668 | -0.0444 |
| `428090-99999` | Kolkata Dum Dum | East Delta-Plain | 2,157 | 0.9643 | 1.0623 | -0.0980 |
| `428670-99999` | Nagpur Sonegaon | Central Plateau | 2,152 | 1.3522 | 1.2928 | +0.0594 |
| `429710-99999` | Bhubaneswar | East Delta-Plain | 2,002 | 1.4821 | 1.2197 | +0.2624 |
| **ALL (Mean)** | **National Average** | **All 17 Stations** | **23,949** | **1.4304** | **1.4122** | **+0.0182** |

---

## 4. Regional Cross-Validation: Leave-One-Regime-Out (LORO)

| Physiographic Regime | Stations | Test Obs ($n$) | Dyn MAE (°C) | Base MAE (°C) | $\Delta$ MAE (°C) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Central Plateau** | — | 3,659 | 1.4786 | 1.4795 | -0.0009 |
| **East Delta-Plain** | — | 4,159 | 1.2484 | 1.1381 | +0.1103 |
| **Indo-Gangetic Plain** | — | 6,804 | 2.0930 | 1.4035 | +0.6895 |
| **North / Himalayan** | — | 2,148 | 1.4909 | 1.5142 | -0.0233 |
| **Northeast Hills** | — | 2,064 | 1.3248 | 1.5209 | -0.1961 |
| **West / Arid-SemiArid** | — | 5,115 | 1.2201 | 1.2714 | -0.0513 |

---

## 5. Diurnal and Extreme Condition Performance

| Condition / Stratum | Definition | Sample Size ($n$) | Dynamic MAE (°C) | Baseline MAE (°C) | Improvement |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Daytime** | 06:00 to 18:00 Local/UTC | 3,031 | 1.3909 | 1.4475 | +0.0566°C |
| **Nighttime** | 18:00 to 06:00 Local/UTC | 2,257 | 0.8710 | 1.0225 | +0.1515°C |
| **High Temperature** | $T_{\text{coarse}} \ge 31.0^\circ\text{C}$ (90th pct) | 558 | 1.5152 | 1.4030 | -0.1122°C |
| **Precipitation Events** | Precip $> 0.1\text{ mm}$ | 1,799 | 1.3398 | 1.4069 | +0.0671°C |
| **High Relief / Foothills** | Station Elev $\ge 1,000\text{ m}$ | 309 | 1.4021 | 1.5602 | +0.1581°C |

---

## 6. Feature Importance & Interpretability

Normalized feature contributions derived from XGBoost split gain:

| Rank | Feature Identifier | Description | Normalized Gain | Total Splits |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `f_cos_aspect` | Feature component | 17.58% | 216 |
| 2 | `f_elevation_diff` | Feature component | 13.47% | 278 |
| 3 | `f_coarse_rh` | Feature component | 9.53% | 794 |
| 4 | `f_latitude` | Feature component | 5.50% | 205 |
| 5 | `f_longitude` | Feature component | 5.25% | 145 |
| 6 | `f_lapse_rate_adj` | Feature component | 4.80% | 55 |
| 7 | `f_slope` | Feature component | 4.24% | 153 |
| 8 | `f_sin_aspect` | Feature component | 4.18% | 201 |
| 9 | `f_sin_hour` | Feature component | 4.15% | 640 |
| 10 | `f_coarse_precip` | Feature component | 3.89% | 442 |
| 11 | `f_obs_elevation` | Feature component | 3.59% | 302 |
| 12 | `f_land_cover` | Feature component | 3.48% | 54 |

---

## 7. Production Promotion Gate Decision Audit

| Promotion Criterion | Requirement | Observed Metric | Result |
| :--- | :--- | :--- | :---: |
| **1. Metric Improvement** | Test MAE $\le$ Baseline MAE $- 0.1000^\circ\text{C}$ | Diff = **+0.0971°C** | **FAIL** |
| **2. Overfitting Gap** | $|\text{MAE}_{\text{val}} - \text{MAE}_{\text{test}}| \le 0.1500^\circ\text{C}$ | Gap = **0.1898°C** | **FAIL** |
| **3. Spatial Generalization** | LOSO Mean MAE $\le 1.40^\circ\text{C}$ & Max $\le 2.50^\circ\text{C}$ | Mean = **1.4304°C**, Max = **2.1224°C** | **FAIL** |
| **4. Physical Safety Bounds** | Clamped predictions ($[-8.0, +8.0]^\circ\text{C}$) $< 0.5\%$ | Clamped = **0.00%** (0 obs) | **PASS** |
| **5. Diurnal Stability** | Daytime vs Nighttime MAE gap $\le 0.3500^\circ\text{C}$ | Gap = **0.5199°C** | **FAIL** |

### Official Decision
**`RETAIN_FOR_RESEARCH`**

While the dynamic model demonstrates localized advantages, it does not surpass the required 0.1000°C margin uniformly or fails one of the stringent stability thresholds. Pursuant to SIH Scientific Governance, the candidate is retained strictly for research.

Under all circumstances, the production operational baseline:
```
T_calibrated = T_coarse + 0.7351°C
```
remains **immutable, certified, and fully active** for all agricultural advisories.
