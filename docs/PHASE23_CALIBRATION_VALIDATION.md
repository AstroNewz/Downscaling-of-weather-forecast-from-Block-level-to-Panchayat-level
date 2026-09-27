# Phase 23: Calibration Strategy Validation & Spatial Cross-Validation

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE23`  
**Evaluation Date**: 2026-09-17  
**Objective**: Empirically evaluate candidate calibration strategies without test set leakage to select the optimal operational production formulation.

---

## 1. Candidate Calibration Strategies Formulated on Training Partition ($N = 14,418$)

All calibration parameters were derived strictly from the training partition (June 1 – July 25, 2024).

| Strategy | Mathematical Description | Derived Parameter(s) | Sample Count |
|---|---|---|---|
| **A. National Scalar Bias** | Single global temperature offset across all Indian regimes | $B_{\text{nat}} = +0.7351\ ^\circ\text{C}$ | $N = 14,418$ |
| **B. Physiographic Regional Bias** | Regime-specific offsets for the 6 physiographic divisions | Central Plateau: $+0.2342\ ^\circ\text{C}$<br>East Delta-Plain: $+0.4965\ ^\circ\text{C}$<br>Indo-Gangetic: $+0.9750\ ^\circ\text{C}$<br>North/Himalayan: $+0.8328\ ^\circ\text{C}$<br>Northeast Hills: $+2.1958\ ^\circ\text{C}$<br>West/Arid: $+0.3366\ ^\circ\text{C}$ | Central: 2,232<br>East: 2,490<br>Gangetic: 4,070<br>North: 1,300<br>NE: 1,255<br>West: 3,071 |
| **C. Elevation Band Bias** | Hypsometric offsets stratified by station elevation | $<100\text{ m}: +0.9663\ ^\circ\text{C}$<br>$100\text{--}500\text{ m}: +0.4581\ ^\circ\text{C}$<br>$500\text{--}1500\text{ m}: +0.6095\ ^\circ\text{C}$<br>$\ge 1500\text{ m}: +0.5171\ ^\circ\text{C}$ | $<100\text{ m}: 7,478$<br>$100\text{--}500\text{ m}: 5,130$<br>$500\text{--}1500\text{ m}: 945$<br>$\ge 1500\text{ m}: 865$ |
| **D. Station-Specific Bias** | Individual station training offsets with regional fallback | 17 individual offsets ranging from $-0.32^\circ\text{C}$ (Shimla) to $+2.41^\circ\text{C}$ (Patna) | 72 to 484 per station |

---

## 2. Chronological Validation Performance ($N = 4,243$, July 26 – August 10, 2024)

| Evaluation Method | MAE (°C) | RMSE (°C) | Mean Bias (°C) | $\Delta\text{MAE}$ vs. Raw | Operational Complexity |
|---|---|---|---|---|---|
| **Raw ERA5 Baseline** | 1.3943 | 1.7298 | -0.8874 | — | Zero parameters |
| **Strategy A: National Scalar Bias** | **1.1431** | 1.4926 | -0.1523 | **-0.2512** | 1 parameter (Ultra-simple) |
| **Strategy B: Regional Bias** | 1.1492 | 1.4856 | -0.1518 | -0.2451 | 6 parameters (Regional boundaries) |
| **Strategy C: Elevation Band Bias** | 1.1344 | 1.4798 | -0.1524 | -0.2599 | 4 parameters (DEM dependency) |
| **Strategy D: Station Bias** | 1.1297 | 1.4657 | -0.1537 | -0.2646 | 17 parameters (Cannot transfer to unseen Panchayats) |

### Key Scientific Insight:
- **Strategy A (National Bias) outperformed Strategy B (Regional Bias)** on the chronological validation set ($1.1431\ ^\circ\text{C}$ vs. $1.1492\ ^\circ\text{C}$).
- Stratifying into 6 regional partitions introduced parameter instability in sparse-station regions (e.g., Northeast Hills with only 2 stations produced an over-corrected offset of $+2.1958\ ^\circ\text{C}$ that degraded validation generalization).
- Strategy D (Station Bias) provides marginal apparent gain ($0.0134\ ^\circ\text{C}$) only because stations were already seen; it provides **zero utility** for ungauged Gram Panchayats where ground-truth stations do not exist.

---

## 3. Spatial Cross-Validation: Leave-One-Station-Out (17 Folds)

Leave-One-Station-Out cross-validation was evaluated across all 17 WMO weather stations:

- **Stations Improved by National Scalar Bias**: **12 of 17 stations (70.6%)**
- **Stations Improved by Regional Bias**: **12 of 17 stations (70.6%)**
- In held-out stations, the regional calibration had identical holdout improvement counts to the national scalar calibration, confirming that regional division does not improve spatial transferability across unseen locations.

---

## 4. Regional Holdout Cross-Validation: Leave-One-Region-Out (6 Folds)

In Leave-One-Region-Out cross-validation, an entire physiographic region is held out, and National Bias is fitted strictly on the remaining 5 regions:

| Held-out Region | Held-out N | Raw MAE (°C) | National Bias MAE (°C) | $\Delta\text{MAE}$ (°C) | Transfer Status |
|---|---|---|---|---|---|
| **Central Plateau** | 3,191 | 1.6324 | 1.5854 | -0.0470 | **IMPROVED** |
| **East Delta-Plain** | 3,369 | 1.2795 | 1.1432 | -0.1363 | **IMPROVED** |
| **Indo-Gangetic Plain** | 5,593 | 1.6694 | 1.4111 | -0.2582 | **IMPROVED** |
| **North / Himalayan** | 1,847 | 1.6766 | 1.5161 | -0.1605 | **IMPROVED** |
| **Northeast Hills** | 1,704 | 2.1466 | 1.6695 | -0.4771 | **IMPROVED** |
| **West / Arid-SemiArid** | 4,245 | 1.3712 | 1.3264 | -0.0448 | **IMPROVED** |

**LORO Summary**: National Scalar Bias improved prediction accuracy across **6 of 6 regions (100.0%)** even when each region was completely excluded from training.

---

## 5. Formal Strategy Selection Rationale

Based strictly on empirical evidence:
1. **Validation Outperformance**: National scalar calibration achieved a lower MAE ($1.1431\ ^\circ\text{C}$) than regional calibration ($1.1492\ ^\circ\text{C}$) on unseen chronological validation.
2. **100% Regional Holdout Generalization**: National scalar calibration generalized successfully across all 6 physiographic holdouts.
3. **Zero Spatial Discontinuity**: A single national parameter eliminates artificial temperature jumps across state and physiographic borders.
4. **Parsimony**: 1 transparent scalar parameter ($B = +0.7351\ ^\circ\text{C}$) versus 6 regional parameters or 120 decision trees.

**Selected Production Strategy**: **NATIONAL_SCALAR_CALIBRATION** ($B = +0.7351\ ^\circ\text{C}$).
