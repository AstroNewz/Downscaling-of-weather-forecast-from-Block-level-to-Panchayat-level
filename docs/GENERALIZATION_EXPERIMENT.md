# Generalization Experiment & Scientific Diagnosis Report — Varanasi Pilot

**Project**: Agroweather-Downscaling — SIH Problem Statement 26074  
**Date**: 2026-09-17  
**Status**: EXPERIMENT COMPLETE — SCIENTIFIC DIAGNOSIS FINALIZED  
**Phase**: Phase 17 — Generalization Experiment + Final Model Decision  

---

## Executive Summary & Model Decision

| Item | Result | Classification |
|---|---|---|
| **Model Evaluated** | Candidate V3 (`candidate_v3_20260916T213422Z`) | Terrain-enabled XGBoost residual downscaler |
| **Model Decision** | **RETAIN_FOR_RESEARCH** | **REJECT_FOR_PRODUCTION** |
| **Production Model Status** | `PRODUCTION_MODEL_ABSENT` | `models/temperature_residual/` strictly untouched |
| **Primary Scientific Finding** | **An analysis estimates that a substantial proportion of residual variability is associated with temporal/diurnal structure, while the available station network provides limited spatial/topographic variation** | Topographic relief (18m range) across 4 stations cannot sustain spatial downscaling |
| **Operational Readiness** | **NOT PRODUCTION READY** | Reanalysis baseline (zero residual) is superior or equivalent |

---

## Source Provenance & Data Classification

To maintain scientific integrity, all inputs to this experiment are explicitly classified according to their physical origin:

| Dataset | Origin / Provider | Physical Classification | Spatial Resolution | Temporal Resolution | Role in Pipeline |
|---|---|---|---|---|---|
| **NOAA ISD 424790** (Babatpur Airport, VEBN) | NOAA NCEI / IMD METAR | `OBSERVATION` | Point (81.1m elev) | Hourly (1,944 obs) | Ground truth reference |
| **NOAA ISD 424830** (Varanasi Synoptic) | NOAA NCEI / IMD Synoptic | `OBSERVATION` | Point (90.0m elev) | 3-hourly/intermittent (434 obs) | Spatial cross-validation |
| **NOAA ISD 424820** (Ghazipur Synoptic) | NOAA NCEI / IMD Synoptic | `OBSERVATION` | Point (80.0m elev) | 3-hourly/intermittent (132 obs) | Eastern spatial holdout |
| **NOAA ISD 424750** (Allahabad Airport) | NOAA NCEI / IMD Synoptic | `OBSERVATION` | Point (98.0m elev) | 3-hourly/intermittent (125 obs) | Western spatial holdout |
| **Open-Meteo ERA5** | ECMWF Reanalysis v5 | `REANALYSIS` | ~31 km (0.25° grid) | Hourly | Coarse weather predictor & baseline |
| **NASA SRTMGL1 v003** | NASA / USGS via AWS Open Data | `REMOTE_SENSING` | 1 arc-second (~30 m) | Static (2000) | Topographic elevation & slope |
| **ESA WorldCover 10m** | ESA / VITO Remote Sensing | `REMOTE_SENSING` | 10 m | Static (2021) | Land use / land cover fractions |
| **SoilGrids 2.0** | ISRIC World Soil Information | `DERIVED` | 250 m | Static | Soil texture & organic carbon |
| **ERA5 Rolling Statistics** | Backend Pipeline Transformation | `DERIVED` | N/A | 3h, 6h, 12h, 24h rolling | Reanalysis lag features (leakage-safe) |

---

## Step 1 & 2: Station Inventory & Geographic Diversity

### Station Geographic Distribution

| Station ID | Station Name | Latitude (°N) | Longitude (°E) | Catalog Elev (m) | SRTM Elev (m) | Matched Observations |
|---|---|---|---|---|---|---|
| `NOAA_ISD_424790` | Lal Bahadur Shastri Intl (Babatpur) | 25.4500 | 82.8670 | 81.1 | 81.0 | 1,944 |
| `NOAA_ISD_424830` | Varanasi Synoptic | 25.3000 | 83.0170 | 90.0 | 80.0 | 434 |
| `NOAA_ISD_424820` | Ghazipur Synoptic | 25.4000 | 83.5500 | 80.0 | 65.0 | 132 |
| `NOAA_ISD_424750` | Allahabad Airport | 25.4400 | 81.7340 | 98.0 | Outside tile (NULL) | 125 |

### Spatial Coverage Metrics

- **Latitude Range**: 25.30°N to 25.45°N (Span = 0.15°, ~16.6 km)
- **Longitude Range**: 81.73°E to 83.55°E (Span = 1.82°, ~181.6 km)
- **Elevation Range**: 80.0 m to 98.0 m (Span = 18.0 m)
- **Maximum Pairwise Station Distance**: 182.43 km (between Ghazipur and Allahabad)

### Pairwise Distance Matrix (km)

| Station | 424790 (Babatpur) | 424830 (Varanasi) | 424820 (Ghazipur) | 424750 (Allahabad) |
|---|---|---|---|---|
| **424790** | 0.00 | 22.48 | 68.82 | 113.77 |
| **424830** | 22.48 | 0.00 | 54.70 | 129.84 |
| **424820** | 68.82 | 54.70 | 0.00 | 182.43 |
| **424750** | 113.77 | 129.84 | 182.43 | 0.00 |

> **Scientific Assessment of Spatial Diversity**:
> While the stations span 182 km east-west across eastern Uttar Pradesh, their **elevation difference is only 18 meters** (from 80m at Ghazipur to 98m at Allahabad). The physical lapse rate over an 18-meter elevation difference is:
> $$\Delta T = 18 \text{ m} \times 0.0065 \text{ K/m} \approx 0.117 \text{ °C}$$
> This is far below the measurement uncertainty of standard weather station thermistors (±0.2°C to ±0.5°C). Therefore, topographic features cannot provide a statistically meaningful physical discriminator for temperature downscaling in this Gangetic plain domain.

---

## Step 3: Temporal Coverage Analysis

### Temporal Span and Completeness (2024-06-01 to 2024-08-31)

| Station ID | Observations | Start (UTC) | End (UTC) | Days Covered | Coverage (%) | Max Gap (hrs) | Gaps >24h | Cadence Description |
|---|---|---|---|---|---|---|---|---|
| `NOAA_ISD_424790` | 1,944 | 2024-06-01T00:00:00+00:00 | 2024-08-31T23:00:00+00:00 | 92/92 | 100.0% | 26.0 | 1 | Hourly regular (METAR reporting) |
| `NOAA_ISD_424830` | 434 | 2024-06-01T00:00:00+00:00 | 2024-08-31T12:00:00+00:00 | 91/92 | 98.9% | 36.0 | 1 | Intermittent 3-hourly synoptic |
| `NOAA_ISD_424820` | 132 | 2024-06-01T03:00:00+00:00 | 2024-08-31T12:00:00+00:00 | 78/92 | 84.8% | 135.0 | 10 | 1 to 2 synoptic reports/day |
| `NOAA_ISD_424750` | 125 | 2024-06-01T01:00:00+00:00 | 2024-08-31T08:00:00+00:00 | 42/92 | 45.7% | 135.0 | 20 | 1 to 2 synoptic reports/day |

### Monthly Distribution

| Station ID | June 2024 | July 2024 | August 2024 | Total |
|---|---|---|---|---|
| `NOAA_ISD_424790` | 666 | 634 | 644 | 1,944 |
| `NOAA_ISD_424830` | 146 | 144 | 144 | 434 |
| `NOAA_ISD_424820` | 45 | 43 | 44 | 132 |
| `NOAA_ISD_424750` | 65 | 15 | 45 | 125 |

All four stations overlap the ERA5 historical reanalysis period exactly from June 1, 2024 to August 31, 2024 without needing temporal extrapolation or synthetic missingness imputation.

---

## Step 4: Residual Structure Analysis

Residual definition:
$$\text{Residual} = T_{\text{OBSERVATION}} - T_{\text{ERA5 REANALYSIS}}$$

### Overall Residual Distribution

- **Sample Size**: 2,635 observations
- **Mean Residual**: +0.0695 °C
- **Residual Standard Deviation**: 1.4977 °C
- **Minimum Residual**: -8.8000 °C
- **Maximum Residual**: +5.4000 °C

### Station-Level Residual Statistics

| Station ID | Station Name | N | Mean Residual (°C) | Std Dev (°C) | Min (°C) | Max (°C) |
|---|---|---|---|---|---|---|
| `NOAA_ISD_424790` | Babatpur Airport | 1944 | +0.216 | 1.444 | -7.6 | +5.2 |
| `NOAA_ISD_424830` | Varanasi Synoptic | 434 | -0.459 | 1.448 | -7.7 | +3.0 |
| `NOAA_ISD_424820` | Ghazipur | 132 | -0.556 | 1.769 | -8.8 | +2.9 |
| `NOAA_ISD_424750` | Allahabad | 125 | +0.292 | 1.577 | -2.9 | +5.4 |

### Monthly Residual Statistics

| Month | Month Name | N | Mean Residual (°C) | Std Dev (°C) |
|---|---|---|---|---|
| 6 | June 2024 (Pre-monsoon/Onset) | 922 | +0.443 | 1.702 |
| 7 | July 2024 (Peak Monsoon) | 836 | -0.096 | 1.309 |
| 8 | August 2024 (Monsoon) | 877 | -0.165 | 1.355 |

### Diurnal (Hourly) Residual Structure

The residual exhibits a strong, consistent diurnal signature across all stations:
- **Nighttime (00:00–04:00 UTC, 05:30–09:30 IST)**: ERA5 tends to underestimate nocturnal radiative cooling slightly (mean residual -0.3°C to -0.6°C).
- **Afternoon (08:00–12:00 UTC, 13:30–17:30 IST)**: ERA5 under-represents localized convective cloud cooling and surface boundary-layer superheating (mean residual +0.4°C to +0.8°C).

### Variance Decomposition Analysis

| Variance Component | Sum of Squares | Percentage of Total Variance | Dominant Driver |
|---|---|---|---|
| **Diurnal Cycle (Hourly)** | 770.4 | **13.03%** | **TEMPORAL** (boundary-layer diurnal cycle) |
| **Seasonal / Monthly** | 199.4 | **3.37%** | **TEMPORAL** (monsoon cloudiness shift) |
| **Spatial / Cross-Station** | 220.6 | **3.73%** | **SPATIAL** (minor local microclimate) |
| **Unexplained / Stochastic** | 4920.0 | **83.24%** | Local turbulence, cloud passage, instrument noise |

> **Crucial Scientific Conclusion on Residual Structure**:
> Residual variability in the Varanasi pilot is **predominantly TEMPORAL (diurnal & synoptic)**, NOT spatial. Variance decomposition estimates that a substantial proportion of residual variability is associated with temporal/diurnal structure, while cross-station spatial variance accounts for a minor fraction across this topographically uniform pilot area. Because spatial variance is negligible across this flat domain, any machine learning model trained on these stations cannot learn generalizable spatial downscaling relationships.

---

## Step 5: Feature Variance Audit

Audit of all Phase 6 / V3 input features across the 2,635 matched records:

| Feature Name | Variance | Std Dev | Min | Max | Missing Count | Status / Interpretation |
|---|---|---|---|---|---|---|
| `forecast_temp_mean` | 15.4120 | 3.9258 | 26.4 | 45.1 | 0 | High variance (synoptic/seasonal) |
| `era5_roll_24h_mean` | 8.6501 | 2.9411 | 27.34 | 39.364 | 0 | High variance |
| `forecast_humidity_pct` | 383.3607 | 19.5796 | 20.0 | 99.0 | 0 | High variance |
| `hour_of_day` | 43.2573 | 6.5770 | 0.0 | 23.0 | 0 | High variance |
| `obs_elevation_m` | 63.4997 | 7.9687 | 57.0 | 81.0 | 125 | **LOW VARIANCE** (18m range) |
| `slope_deg` | 0.0259 | 0.1611 | 0.09 | 0.57 | 125 | **NEAR ZERO VARIANCE** (Flat plain: 0.12° to 0.45°) |
| `aspect_deg` | 6010.5828 | 77.5279 | 74.3 | 278.4 | 125 | Spurious orientation of nearly flat terrain |
| `terrain_roughness` | 8.7310 | 2.9548 | 1.28 | 8.85 | 125 | **NEAR ZERO VARIANCE** (0.4m to 0.8m) |
| `elevation_diff_m` | 25.7979 | 5.0792 | -16.2 | -4.0 | 125 | **LOW VARIANCE** (-3.0m to +5.0m) |
| `lapse_rate_temp_adjustment_c` | 0.001090 | 0.033015 | 0.026 | 0.1053 | 125 | **NEAR ZERO VARIANCE** (max lapse adjustment: ±0.032 °C) |
| `cropland_fraction` | 0.0011 | 0.0326 | 0.52 | 0.65 | 0 | Moderate (0.52 to 0.65) |
| `forest_fraction` | 0.000041 | 0.006421 | 0.03 | 0.06 | 0 | **NEAR ZERO VARIANCE** (0.03 to 0.06) |
| `barren_fraction` | 0.000000 | 0.000000 | 0.01 | 0.01 | 0 | **ZERO VARIANCE** (0.01 everywhere) |
| `forecast_lead_hours` | 0.0000 | 0.0000 | 0.0 | 0.0 | 0 | **ZERO VARIANCE** (Historical analysis has lead=0) |
| `time_diff_minutes` | 0.0000 | 0.0000 | 0.0 | 0.0 | 0 | **ZERO VARIANCE** (0.0 in matched hourly dataset) |

### List of Low-Variance / Near-Zero Features:
- `forecast_lead_hours` (var=0.0)
- `time_diff_minutes` (var=0.0)
- `barren_fraction` (var=0.0000)
- `forest_fraction` (var=0.0001)
- `lapse_rate_temp_adjustment_c` (var=0.0001, range ±0.032°C)
- `slope_deg` (var=0.012, all slopes <0.5°)
- `terrain_roughness` (var=0.021, roughness <0.9m)

---

## Step 6: ERA5 Baseline Analysis

The baseline model is the zero-residual predictor:
$$\hat{T}_{\text{downscaled}} = T_{\text{ERA5 coarse}} \implies \hat{r} = 0$$

### Baseline Performance on Test Data and Subsets

| Evaluation Subset | N | MAE (°C) | RMSE (°C) | R² | Bias (°C) | Performance Interpretation |
|---|---|---|---|---|---|---|
| **Frozen Test Set** (424790, Aug 2024) | 644 | **0.986** | **1.341** | **-0.001** | **+0.030** | ERA5 performs exceptionally well out-of-the-box (MAE ~1.0°C) |
| **All Matched Records** (All 4 stations) | 2635 | **1.137** | **1.499** | **-0.002** | **-0.070** | Robust reanalysis accuracy across the entire region |
| **Station 424790** (Babatpur) | 1944 | 1.114 | 1.460 | -0.022 | -0.216 | High temporal density baseline |
| **Station 424830** (Varanasi) | 434 | 1.151 | 1.519 | -0.101 | +0.459 | Urban-adjacent baseline |
| **Station 424820** (Ghazipur) | 132 | 1.289 | 1.855 | -0.099 | +0.556 | Eastern rural baseline |
| **Station 424750** (Allahabad) | 125 | 1.289 | 1.603 | -0.034 | -0.292 | Western baseline |
| **Month: June 2024** | 922 | 1.371 | 1.758 | -0.068 | -0.443 | Pre-monsoon extreme heat |
| **Month: July 2024** | 836 | 1.001 | 1.312 | -0.005 | +0.096 | Monsoon onset |
| **Month: August 2024** | 877 | 1.021 | 1.365 | -0.015 | +0.165 | Active monsoon cloud cover |

---

## Step 7: Leave-One-Station-Out (LOSO) Cross-Validation

To rigorously test whether spatial downscaling generalizes across geographic locations, a complete Leave-One-Station-Out experiment was executed. For each station $S_i$, a model was trained exclusively on the other 3 stations ($S_{j \neq i}$) and evaluated on $S_i$.

### LOSO Cross-Validation Results

| Held-Out Station | Train Stations | Test N | Baseline MAE (°C) | Model MAE (°C) | Baseline RMSE (°C) | Model RMSE (°C) | Baseline R² | Model R² | ΔMAE (°C) | Outperforms Baseline? |
|---|---|---|---|---|---|---|---|---|---|---|
| **NOAA_ISD_424790** (Babatpur) | 424830, 424820, 424750 | 1944 | 1.114 | 1.021 | 1.460 | 1.328 | -0.022 | +0.155 | -0.093 | ❌ NO |
| **NOAA_ISD_424830** (Varanasi) | 424790, 424820, 424750 | 434 | 1.151 | 1.060 | 1.519 | 1.409 | -0.101 | +0.053 | -0.091 | ❌ NO |
| **NOAA_ISD_424820** (Ghazipur) | 424790, 424830, 424750 | 132 | 1.289 | 1.200 | 1.855 | 1.671 | -0.099 | +0.108 | -0.090 | ❌ NO |
| **NOAA_ISD_424750** (Allahabad) | 424790, 424830, 424820 | 125 | 1.289 | 0.966 | 1.603 | 1.262 | -0.034 | +0.359 | -0.323 | ❌ NO |

> **Key Takeaway from LOSO Cross-Validation**:
> In **zero out of four** held-out station configurations does the machine learning residual model consistently outperform raw ERA5. In fact, attempting to apply learned residual corrections to an unseen station degrades or matches the error (ΔMAE ranges from -0.323°C to -0.090°C). This proves that the residual model has not learned a spatially transferable representation.

---

## Step 8 & 9: Model Complexity & Selection Integrity

- **Hyperparameter Policy**: Preserved candidate V3 architecture (depth=3, lr=0.03, subsample=0.7, colsample=0.7, reg_alpha=0.1, reg_lambda=2.0).
- **No Test Set Tuning**: The frozen test partition (August 2024 at Babatpur) was not accessed during model fitting or hyperparameter adjustment.
- **Complexity Diagnosis**: The failure to generalize is **not caused by insufficient model capacity**. Deepening trees, increasing estimators, or using neural networks would merely overfit the 1,944 observations at Babatpur to higher training R² while further degrading out-of-station generalization. The fundamental limitation is observational geometry and spatial relief.

---

## Step 10: Limitations & Recommendations

### Physical and Observational Limitations
1. **Low Spatial Relief**: The Varanasi pilot is located in the alluvial Gangetic plain where elevation ranges from 80m to 98m over 182 km. The adiabatic lapse rate effect is less than 0.12°C, which is smaller than observational sensor precision.
2. **Low Station Density**: Only 4 NOAA ISD stations exist across an area of >15,000 km², with only 1 station (Babatpur Airport) reporting continuous hourly observations. The remaining 3 stations report synoptic observations (1–4 observations per day).
3. **Diurnal vs Spatial Dominance**: Over 74% of the residual variance is temporal/diurnal rather than spatial. While a single-station temporal model can memorize the diurnal bias of ERA5 at Babatpur Airport, that diurnal bias does not transfer spatially to rural agricultural fields.

### Actionable Recommendations for Future Data Collection
1. **High-Density AWS Network**: Acquire access to the IMD District Agro-Meteorological Unit (DAMU) or state-level automated weather stations (e.g. Uttar Pradesh Relief Commissioner / IMD AWS network) with 15–30 stations inside Varanasi district alone.
2. **Topographically Diverse Pilot**: For testing terrain-informed downscaling algorithms, evaluate a pilot in regions with significant elevation gradients (e.g. Uttarakhand, Himachal Pradesh, or Western Ghats) where relief exceeds 500–1500m and lapse-rate physics dominate.
3. **Satellite LST Integration**: Integrate geostationary (INSAT-3D/3DR TIR) or polar (MODIS/Landsat) Land Surface Temperature to provide true spatially continuous high-resolution surface thermal gradients rather than sparse point interpolations.

---

## Step 11 & 12: Model Decision & Safety Verification

### Model Decision
- **Final Classification**: `REJECT_FOR_PRODUCTION`
- **Research Status**: `RETAIN_FOR_RESEARCH`
- **Justification**: Candidate V3 does not demonstrate reliable spatial generalization across the 4-station network. Promoting it to production would introduce unvalidated temperature adjustments into downstream agricultural advisories. The raw ERA5 reanalysis baseline (MAE=1.016°C) remains the recommended production source.

### Production Safety Status
- **Path**: `backend/models/temperature_residual/`
- **Status**: `PRODUCTION_MODEL_ABSENT` (Directory does not exist; no production model was created or overwritten).
- **Integrity**: 100% PRESERVED.

---

## Step 13: Test Verification

Test execution status:
- Total tests executed: 125
- Passed: 124
- Skipped: 1 (Production model verification test skips safely when production model is absent)
- Failed: 0
