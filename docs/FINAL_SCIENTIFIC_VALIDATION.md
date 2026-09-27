# Final Scientific Validation & Project Freeze Document — Varanasi Pilot

**Project**: Agroweather-Downscaling — SIH Problem Statement 26074  
**Date**: 2026-09-17  
**Status**: VALIDATED, AUDITED & SCIENTIFICALLY FROZEN  
**Phase**: Phase 18 — Final Scientific Validation, Reproducibility & Project Freeze  

---

## Executive Status & Boundary Summary

| Component | Status / Classification | Description |
|---|---|---|
| **Research Model** | **RETAINED FOR RESEARCH** | `candidate_v3_20260916T213422Z` (XGBoost terrain-enabled residual model) |
| **Production Model** | **NOT PROMOTED** | `models/temperature_residual/` strictly absent/frozen (safe state) |
| **Operational Baseline** | **RAW ERA5** | Zero-residual reanalysis predictor (MAE=0.986°C test / 1.016°C overall) |
| **Experiment Freeze** | **FROZEN** | Experiment ID: `EXP_VARANASI_PILOT_PHASE18_FREEZE` |
| **Test Suite** | **PASS (100%)** | 129+ automated verification tests passing |

---

## 1. Problem Statement

Smart India Hackathon (SIH) Problem Statement 26074 addresses high-resolution agroweather downscaling for precision agriculture in India. Coarse global weather reanalyses (such as ECMWF ERA5 at ~31 km resolution) do not directly capture block-level and panchayat-level microclimates influenced by local topography, canopy, and surface boundary-layer dynamics. The goal of this research pilot is to evaluate whether machine learning residual models trained on real ground weather stations and high-resolution terrain (NASA SRTM 30m) can reliably downscale coarse reanalysis temperatures to 1 km resolution.

---

## 2. Varanasi Pilot Scope

- **Geographic Area**: Varanasi District and immediate environs, Uttar Pradesh, India.
- **Bounding Box**: 25.10°N – 25.60°N latitude, 82.70°E – 83.20°E longitude.
- **Topographic Context**: Alluvial Indo-Gangetic Plain. Minimal elevation relief (80m to 98m above sea level across all ground stations).
- **Target Resolution**: 1 km × 1 km regular Cartesian grid in metric UTM coordinates.
- **Administrative Entities**: 8 Blocks / 100+ Gram Panchayats (Varanasi Sadar, Pindra, Arajiline, Cholapur, Kashi Vidyapeeth, Harahua, Sevapuri, Baragaon).

---

## 3. Real Data Sources

To maintain strict scientific integrity, all data sources are explicitly classified by physical origin:

| Dataset | Provider / Source | Physical Classification | Spatial Resolution | Temporal Resolution | Description / Verification |
|---|---|---|---|---|---|
| **NOAA ISD Weather Observations** | NOAA NCEI / IMD Stations | `OBSERVATION` | Point coordinates | Hourly to 3-hourly | Ground truth reference thermometer measurements |
| **Open-Meteo ERA5 Reanalysis** | ECMWF Reanalysis v5 | `REANALYSIS` | ~31 km (0.25° grid) | Hourly continuous | Coarse historical weather reconstruction (NOT station data) |
| **NASA SRTMGL1 v003** | NASA / USGS via AWS Open Data | `REMOTE_SENSING` | 1 arc-second (~30 m) | Static (2000) | Space Shuttle radar topographic elevation |
| **ESA WorldCover 10m 2021** | ESA / VITO Remote Sensing | `REMOTE_SENSING` | 10 m | Static (2021) | Sentinel-1/2 derived land cover fractions |
| **SoilGrids 2.0** | ISRIC World Soil Information | `DERIVED` | 250 m | Static | Machine-learning mapped soil properties |
| **ERA5 Rolling Statistics** | Transformation Pipeline | `DERIVED` | Grid point | 3h, 6h, 12h, 24h lag | Reanalysis-only moving window statistics (leakage-free) |

---

## 4. Dataset Period

- **Temporal Extent**: 2024-06-01T00:00:00Z through 2024-08-31T23:00:00Z (92 continuous days).
- **Seasonal Context**: Kharif season in Northern India (Pre-monsoon heatwave, monsoon onset, and active monsoon precipitation).
- **Temporal Alignment**: 100% temporal overlap between ground observations and ERA5 reanalysis. 0 synthetic records. 0 extrapolated records.

---

## 5. Station Inventory

Four genuine ground stations from the NOAA Integrated Surface Database (ISD) were acquired and verified:

| Station Identifier | Station Name | Latitude (°N) | Longitude (°E) | Elevation (m) | Matched Records | Sampling Characteristics |
|---|---|---|---|---|---|---|
| `NOAA_ISD_424790` | Lal Bahadur Shastri Intl Airport (Babatpur) | 25.4500 | 82.8670 | 81.1 | 1,944 | Continuous hourly METAR reporting |
| `NOAA_ISD_424830` | Varanasi Synoptic | 25.3000 | 83.0170 | 90.0 | 434 | 3-hourly synoptic reporting |
| `NOAA_ISD_424820` | Ghazipur Synoptic | 25.4000 | 83.5500 | 80.0 | 132 | 1–2 synoptic reports/day (East holdout) |
| `NOAA_ISD_424750` | Allahabad Airport | 25.4400 | 81.7340 | 98.0 | 125 | 1–2 synoptic reports/day (West holdout) |
| **Total** | — | — | — | — | **2,635** | **100% Genuine Physical Observations** |

---

## 6. ERA5 Baseline Formulation

The operational baseline model is the raw ERA5 reanalysis prediction without residual modification (zero residual predictor):
$$\hat{T}_{\text{baseline}} = T_{\text{coarse ERA5}} \implies \hat{r} = 0$$

Performance on the frozen held-out test partition (August 2024 at Babatpur Airport, $n=644$):
- **MAE**: 0.986°C (0.9862°C)
- **RMSE**: 1.341°C (1.3414°C)
- **$R^2$**: -0.001 (-0.0005)
- **Bias**: +0.030°C (+0.0297°C)

---

## 7. Residual Target Formulation

The downscaling target is defined strictly according to physical principles:
$$r = T_{\text{reference observation}} - T_{\text{coarse reanalysis}}$$
$$\hat{T}_{\text{downscaled}} = T_{\text{coarse reanalysis}} + \hat{r}_{\text{model}}$$

Constraints verified:
- The target is calculated exclusively after temporal matching.
- The target is strictly excluded from the input feature matrix $X$ (`_target_temperature_residual_c` prefixed with underscore).
- No predicted values or future observations enter target computation.

---

## 8. Feature Engineering

The feature vector contains 40 input columns across 6 distinct categories:
1. **Coarse Reanalysis Weather (REANALYSIS)**: `forecast_temp_min`, `forecast_temp_max`, `forecast_temp_mean`, `forecast_rainfall_mm`, `forecast_humidity_pct`, `forecast_wind_speed_mps`, `forecast_wind_direction_deg`, `forecast_cloud_cover_pct`.
2. **Reanalysis Rolling Statistics (DERIVED from REANALYSIS)**: `era5_roll_3h_mean`, `era5_roll_6h_mean`, `era5_roll_12h_mean`, `era5_roll_24h_mean`, `era5_diurnal_range_24h`.
3. **Temporal Features (DERIVED)**: `hour_of_day`, `sin_hour`, `cos_hour`, `day_of_year`, `sin_day_of_year`, `cos_day_of_year`, `month`, `sin_month`, `cos_month`.
4. **Spatial Geometry (DERIVED)**: `obs_latitude`, `obs_longitude`.
5. **High-Resolution Topography (REMOTE_SENSING)**: `obs_elevation_m`, `block_elevation_m`, `elevation_diff_m`, `slope_deg`, `aspect_deg`, `sin_aspect`, `cos_aspect`, `terrain_roughness`, `lapse_rate_temp_adjustment_c`.
6. **Land Cover Fractions (REMOTE_SENSING)**: `cropland_fraction`, `forest_fraction`, `urban_fraction`, `water_fraction`, `barren_fraction`.

---

## 9. Leakage Controls

Rigorous multi-layer leakage safeguards were validated:
- **Target Leakage**: Audit columns (`_reference_temperature_c`, `_coarse_temperature_c`, `_target_temperature_residual_c`) are strictly omitted from $X$.
- **Temporal Leakage**: Chronological splitting enforces that $\max(t_{\text{train}}) < \min(t_{\text{val}}) \le \max(t_{\text{val}}) < \min(t_{\text{test}})$. Future records cannot inform past predictions.
- **Rolling Feature Leakage**: Moving statistics are computed backwards in time using only ERA5 reanalysis history, never ground observations.
- **Spatial Leakage**: Spatially held-out stations are isolated completely from training partitions during Leave-One-Station-Out evaluations.
- **Preprocessing Leakage**: No global normalization or feature scaling parameters are shared across splits.

---

## 10. Leave-One-Station-Out (LOSO) Methodology

To assess cross-station spatial generalization across the Gangetic Plain, an exhaustive 4-fold Leave-One-Station-Out experiment was executed. In each fold, all observations from one station were completely withheld as the test set, while the residual model was trained on the remaining three stations:

| Held-Out Station | Baseline MAE (°C) | Model MAE (°C) | Baseline RMSE (°C) | Model RMSE (°C) | Baseline $R^2$ | Model $R^2$ | $\Delta$MAE (°C) |
|---|---|---|---|---|---|---|---|
| `NOAA_ISD_424790` (Babatpur) | 1.114 | 1.021 | 1.461 | 1.328 | -0.022 | +0.155 | -0.093 |
| `NOAA_ISD_424830` (Varanasi) | 1.151 | 1.060 | 1.519 | 1.409 | -0.101 | +0.053 | -0.091 |
| `NOAA_ISD_424820` (Ghazipur) | 1.289 | 1.200 | 1.855 | 1.671 | -0.099 | +0.108 | -0.090 |
| `NOAA_ISD_424750` (Allahabad) | 1.289 | 0.966 | 1.604 | 1.262 | -0.034 | +0.359 | -0.323 |

---

## 11. Frozen Test Methodology

The chronological test set partition (2024-08-01 to 2024-08-31 at Babatpur Airport, $n=644$) was frozen prior to model evaluations. No hyperparameter searches, feature modifications, or model selection steps were permitted to adapt to this test partition.

---

## 12. Topography & SRTM Methodology

- **Source**: NASA SRTMGL1 v003 (1 arc-second, ~30 m resolution).
- **Tiles**: `N25E082.hgt.gz` and `N25E083.hgt.gz` downloaded directly from AWS Open Data (`s3://elevation-tiles-prod/skadi/`).
- **Grid Coverage**: 3,844 of 3,844 pilot grid cells (100.0%) covered.
- **Observation Coverage**: 95.3% of matched observation rows have full terrain parameters. Station 424750 (Allahabad, 81.734°E) is outside tile `N25E082` and has its terrain features explicitly set to `None`/`NaN` (never fabricated).

---

## 13. Map Projections & CRS Methodology

- **Metric Operations**: UTM Zone 44N (`EPSG:32644`) dynamically determined from pilot centroid ($25.35^\circ\text{N}, 82.95^\circ\text{E}$).
- **Prohibited Projections**: Web Mercator (`EPSG:3857`) is strictly prohibited for metric operations due to severe scale distortion (~10% at $25^\circ\text{N}$).
- **Geographic Output**: WGS84 (`EPSG:4326`) used solely for standard GeoJSON and API response representations.
- **Pyproj Strictness**: All coordinate transformations enforce `always_xy=True`.

---

## 14. Validation Results Summary

1. **Temporal Baseline**: Raw ERA5 exhibits strong baseline performance across eastern Uttar Pradesh (MAE ~0.99°C to 1.15°C).
2. **Diurnal Pattern**: An analysis estimates that a substantial proportion of residual variability is associated with temporal/diurnal structure, while the available station network provides limited spatial/topographic variation.
3. **Topographic Influence**: Due to the flat nature of the Indo-Gangetic Plain (total station elevation difference of only 18 meters, yielding a theoretical lapse rate shift of only 0.117°C), terrain features provide negligible physical discrimination in this pilot.

---

## 15. Scientific Limitations

1. **Topographic Homogeneity**: The Varanasi pilot cannot validate terrain-driven downscaling physics because the study area contains no significant hills, ridges, or valleys.
2. **Observational Sparsity**: Four stations across ~15,000 km² is inadequate to resolve microscale surface boundary layers or agricultural canopy effects.
3. **No Nationwide Generalization**: Results in Varanasi cannot be extrapolated to the Western Ghats, Himalayas, or arid zones of India.

---

## 16. Final Model Decision

- **Research Classification**: **RETAIN_FOR_RESEARCH**  
  The candidate model (`candidate_v3_20260916T213422Z`) is retained as an experimental artifact demonstrating the integration of NASA SRTM terrain, ESA WorldCover, and NOAA ISD station pipelines.
- **Production Classification**: **REJECT_FOR_PRODUCTION**  
  The candidate model is NOT approved for operational production deployment. It does not outperform the raw ERA5 reanalysis baseline on the frozen chronological test set and cannot guarantee reliable spatial downscaling.
- **Operational Source**: **RAW ERA5**  
  Downstream agricultural advisory pipelines must utilize raw ERA5 reanalysis temperature data directly.

---

## 17. Reproducibility Instructions

To deterministically reproduce this entire validation pipeline from scratch:
```bash
# 1. Verify environment and install required libraries
pip install -r backend/requirements.txt

# 2. Run the complete data verification and build pipeline
python3 backend/data_pipeline/scripts/build_and_train_v3.py

# 3. Execute the Leave-One-Station-Out generalization experiment
python3 backend/data_pipeline/scripts/run_generalization_experiment.py

# 4. Run automated test suite
python3 -m pytest backend/tests/test_india_pipeline.py backend/tests/test_terrain_phase16.py backend/tests/test_generalization_phase17.py --noconftest -v
```

---

## 18. Production Safety Statement

The production model path `backend/models/temperature_residual/` remains absent and untouched. No automated CI/CD pipeline, API endpoint, or simulator function can promote research candidates to production without explicit manual override.

---

## 19. Future Data Requirements for Operational Downscaling

To scientifically justify operational ML-based temperature downscaling in India:
1. **High-Density AWS Network**: Continuous hourly observations from 20+ automated weather stations within a single district.
2. **High-Relief Pilot**: Evaluation in an area with >500 m elevation gradient (e.g. Dehradun / Solan).
3. **Satellite LST**: Assimilation of INSAT-3D/3DR or Landsat/MODIS thermal infrared land surface temperatures.
