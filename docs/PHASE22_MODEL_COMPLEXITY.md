# Phase 22: Model Complexity vs. Incremental Benefit Assessment

**Experiment**: `EXP_INDIA_PRODUCTION_CERTIFICATION_PHASE22`  
**SIH Problem Statement**: 26074 — Agro-Meteorological Downscaling  
**Date**: 2026-09-17  
**Status**: AUDITED TECHNICAL ASSESSMENT  

---

## 1. System Complexity Specification

| Architectural Dimension | Method B: Scalar Bias Correction | Method C: XGBoost Residual Downscaling |
|---|---|---|
| **Mathematical Formulation** | $\hat{T}(t) = T_{\text{coarse}}(t) + \bar{\beta}_{\text{train}}$ | $\hat{T}(t, x) = T_{\text{coarse}}(t) + \sum_{m=1}^M f_m(\mathbf{x}_{t, x})$ |
| **Learned Parameters** | Exactly 1 floating-point scalar ($+0.7351\ ^\circ\text{C}$) | 120 gradient-boosted decision trees (maximum depth 5; 3,720 split nodes) |
| **Input Features Required** | 1 variable: $T_{\text{coarse}}$ | 16 features across 4 heterogeneous domains |
| **Feature Domains** | Atmospheric temperature only | Atmospheric, Diurnal Harmonics, Topography, Geographic Coordinates |
| **Model Artifact Size** | 8 bytes (single float) | 332,247 bytes (`model.json` JSON tree structure) |
| **Inference Time per 10,000 Cells** | < 0.2 milliseconds (vector addition) | ~14.8 milliseconds (multi-tree path traversal) |
| **External Runtime Dependencies** | None (pure NumPy / Python arithmetic) | XGBoost C++ runtime library, OpenMP |
| **Failure Modes** | Fails only if coarse temperature is missing | Fails on NaN/missing in any of 16 features, unhandled categorical encoding, out-of-distribution coordinate extrapolation |

---

## 2. Feature Pipeline & Operational Availability Audit

| Feature Name | Category | Source Pipeline | Real-Time Availability | Operational Latency | Missing Data Fallback | Operational Status |
|---|---|---|---|---|---|---|
| `f_coarse_temp` | Atmospheric | IMD / ECMWF NWP | High | 1–3 hours | Reject (Abort inference) | **PRODUCTION READY** |
| `f_coarse_rh` | Atmospheric | IMD / ECMWF NWP | High | 1–3 hours | Impute regional mean (65%) | **PRODUCTION READY** |
| `f_coarse_pres` | Atmospheric | IMD / ECMWF NWP | High | 1–3 hours | Impute standard sea-level (1013 hPa) | **PRODUCTION READY** |
| `f_coarse_wspd` | Atmospheric | IMD / ECMWF NWP | High | 1–3 hours | Impute calm (2.5 m/s) | **PRODUCTION READY** |
| `f_coarse_cloud` | Atmospheric | IMD / ECMWF NWP | Moderate | 2–4 hours | Impute seasonal climatology | **CONDITIONAL** |
| `f_sin_hour`, `f_cos_hour` | Diurnal | System UTC Clock | Guaranteed | Instantaneous | Pure mathematical deterministic function | **PRODUCTION READY** |
| `f_sin_doy`, `f_cos_doy` | Seasonal | System UTC Calendar | Guaranteed | Instantaneous | Pure mathematical deterministic function | **PRODUCTION READY** |
| `f_obs_elevation` | Topographic | SRTM 30m / DEM | High (Static) | Offline raster lookup | Bilinear sample from DEM cache | **PRODUCTION READY** |
| `f_era5_elevation` | Topographic | NWP Model Orpgraphy | High (Static) | Offline raster lookup | NWP grid orography table | **PRODUCTION READY** |
| `f_elevation_diff` | Topographic | Derived ($\Delta z$) | High (Static) | Instantaneous subtraction | Set to 0.0 m | **PRODUCTION READY** |
| `f_lapse_rate_adj` | Topographic | Physical Adiabatic | High (Static) | Instantaneous multiplication | Set to 0.0 °C | **PRODUCTION READY** |
| `f_high_relief` | Topographic | Binary Indicator | High (Static) | Deterministic rule | Set to 0.0 | **PRODUCTION READY** |
| `f_latitude`, `f_longitude` | Spatial | Cadastral Centroid | High (Static) | LGD database | Infeasible if location undefined | **PRODUCTION READY** |

---

## 3. Quantitative Complexity vs. Incremental Benefit Trade-Off

| Evaluation Metric | Raw ERA5 Baseline | Scalar Bias Correction | XGBoost Residual Candidate | Incremental XGBoost Benefit |
|---|---|---|---|---|
| **Mean Absolute Error (MAE)** | 1.5907 °C | 1.2661 °C | 1.1937 °C | **-0.0724 °C** |
| **Root Mean Squared Error (RMSE)** | 1.9922 °C | 1.6842 °C | 1.5882 °C | **-0.0960 °C** |
| **Coefficient of Determination (R²)** | 0.6134 | 0.7237 | 0.7543 | **+0.0306** |
| **Mean Forecast Bias** | -1.1378 °C | -0.4026 °C | -0.2333 °C | **+0.1693 °C** |
| **Median Absolute Error** | 1.3400 °C | 1.0501 °C | 0.9749 °C | **-0.0752 °C** |
| **95th Percentile Absolute Error** | 3.6500 °C | 3.1200 °C | 2.9772 °C | **-0.1428 °C** |
| **Computational Footprint** | 0 operations | 1 scalar addition | 120 trees $\times$ 16 features | **120x Tree Overhead** |
| **Out-of-Region Transfer Rate** | N/A | High (Global scalar) | 66.7% (Degrades in 2/6 regions) | **Substantial Extrapolation Risk** |

---

## 4. Assessment Summary

1. **Marginal Magnitude**:
   The incremental MAE reduction achieved by deploying 120 decision trees over a single training scalar is $0.0724\ ^\circ\text{C}$. This is less than standard agricultural thermometer precision ($\pm 0.2\ ^\circ\text{C}$) and below the pre-specified $0.1000\ ^\circ\text{C}$ threshold.
2. **Explaining Variance**:
   The primary physical contribution of XGBoost is diurnal day/night shape correction and lapse-rate elevation alignment, which yields a $+0.0306$ gain in $R^2$.
3. **Operational Decision**:
   In an operational production environment serving hundreds of thousands of Gram Panchayats, maintaining a 16-feature live streaming pipeline with tree inference introduces engineering latency and failure points that are not justified by a $0.0724\ ^\circ\text{C}$ margin.
4. **Recommendation**:
   Retain the XGBoost residual architecture for continued research and localized pilot studies, while keeping simple bias-corrected or calibrated NWP as the resilient production operational baseline.
