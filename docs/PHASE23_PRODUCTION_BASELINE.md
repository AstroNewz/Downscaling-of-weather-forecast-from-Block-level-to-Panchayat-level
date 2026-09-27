# Phase 23: Production Baseline Specification & Scientific Formulation

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE23`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Baseline Status**: **PRODUCTION_BASELINE_CERTIFIED**  
**Challenger Status**: **XGBOOST = RESEARCH_ONLY**  
**Certified Offset**: $B_{\text{national}} = +0.7351\ ^\circ\text{C}$  

---

## 1. Executive Summary & Formulation Rationale

Following the Phase 22 certification audit where the XGBoost machine learning candidate was retained for research due to insufficient incremental benefit ($0.0724\ ^\circ\text{C} < 0.1000\ ^\circ\text{C}$ threshold) and spatial extrapolation vulnerability, Phase 23 formally specifies and certifies the **Operational Production Baseline**.

The production system demands:
- **Scientific Validity**: Verified on genuine ground-truth observations across 17 WMO stations and 6 physiographic regimes.
- **Deterministic Simplicity**: Analytical formulation with zero stochastic inference or hidden states.
- **Operational Availability**: Zero dependency on unobserved real-time surface parameters (humidity, pressure, dynamic lapse rate).
- **Graceful Degradation**: Predictable, fail-safe degradation hierarchy without synthetic imputation.
- **Explicit Uncertainty**: Quantified confidence intervals and expected error bounds delivered alongside every temperature estimate.

### Mathematical Formulation
$$\hat{T}_{\text{panchayat}, t} = T_{\text{coarse\_ERA5}, t} + B_{\text{national}}$$

where:
$$B_{\text{national}} = \frac{1}{N_{\text{train}}} \sum_{i=1}^{N_{\text{train}}} \left(T_{\text{obs}, i} - T_{\text{coarse}, i}\right) = +0.7351\ ^\circ\text{C}$$
- **Fitted Period**: Strictly on 14,418 training observations from June 1 to July 25, 2024.
- **Zero Leakage**: Exactly zero test (Aug 11–31) or validation (Jul 26–Aug 10) observations influenced $B_{\text{national}}$.
- **Panchayat Scale**: Applied deterministically to coarse reanalysis forecasts over 1-km metric grid cells before area-weighted aggregation into Gram Panchayat boundaries.

---

## 2. Benchmark Performance Summary

### Frozen Chronological Test Set ($N = 5,288$, August 11–31, 2024)

| Metric | Raw ERA5 Reanalysis | Certified Production Baseline | Total Improvement (Δ) |
|---|---|---|---|
| **Mean Absolute Error (MAE)** | 1.5907 °C | **1.2661 °C** | **-0.3246 °C** (20.4% error reduction) |
| **Root Mean Squared Error (RMSE)** | 1.9922 °C | **1.6842 °C** | **-0.3080 °C** |
| **Coefficient of Determination ($R^2$)** | 0.6134 | **0.7237** | **+0.1103** |
| **Mean Forecast Bias** | -1.1378 °C | **-0.4026 °C** | **+0.7352 °C** |
| **Median Absolute Error** | 1.4000 °C | **0.9649 °C** | **-0.4351 °C** |
| **95th Percentile Error** | 3.9000 °C | **3.4649 °C** | **-0.4351 °C** |
| **Stations Improved** | — | **14 of 17 stations (82.4%)** | — |
| **Regions Improved** | — | **6 of 6 regions (100.0%)** | — |

---

## 3. Physical Directory Separation Architecture

Strict physical and operational isolation is maintained between production and research artifacts:

```
backend/models/
├── production_baseline/              # [CERTIFIED OPERATIONAL]
│   ├── baseline_calibration.json     # Parameter B = +0.7351°C, metadata, metrics
│   └── metadata.json                 # Production schema and error bounds
├── candidates/                       # [FROZEN EXPERIMENTAL CANDIDATES]
│   ├── candidate_v1_20260916T210904Z/
│   ├── candidate_v2_20260916T212349Z/
│   ├── candidate_v3_20260916T213422Z/
│   └── phase21_candidate_20260917/   # 120-tree XGBoost booster (Retained for research)
├── research/                         # [RESEARCH REGISTRY & TRACKING]
│   └── xgboost_research_manifest.json# Explicit research-only declaration
└── temperature_residual/             # [LEGACY PRODUCTION PATH]
    └── .gitkeep                      # Intentionally empty (No uncertified ML models)
```

**Safety Invariant**: The production pipeline imports from `models/production_baseline/`. The research booster in `models/candidates/` cannot be executed by production advisory services.
