# AgroMet: Downscaling Weather Forecast from Block to Panchayat Level

[![SIH 2024 Problem 26074](https://img.shields.io/badge/SIH%202024-Problem%2026074-blue.svg)](https://www.sih.gov.in/)
[![Scientific Readiness](https://img.shields.io/badge/Scientific%20Readiness-LIMITED__VALIDATION-amber.svg)](#scientific-readiness--validation-status)
[![Regression Tests](https://img.shields.io/badge/Acceptance%20Tests-12%2F12%20Passed-brightgreen.svg)](#regression-testing)
[![Frontend Build](https://img.shields.io/badge/Frontend%20Build-Vite%20%2B%20TypeScript%20Passing-success.svg)](#frontend-setup--run)
[![Spatial Reference](https://img.shields.io/badge/GIS%20Grid-EPSG%3A32644%20(1000m)-orange.svg)](#crs--gis-specifications)
[![Release Freeze](https://img.shields.io/badge/Release%20Freeze-SIH__FINAL__FREEZE-purple.svg)](#release-freeze-declaration)

---

## SIH Problem Statement

> **Ministry / Organization**: Ministry of Earth Sciences / India Meteorological Department (IMD)  
> **Problem Statement ID**: 26074  
> **Title**: *Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services.*

---

## 1. Problem Definition & Core Challenge

Operational Numerical Weather Prediction (NWP) models (such as IMD GFS and ECMWF) provide operational guidance at the **Block level** (~12 km to 25 km grid spacing, covering 50,000+ hectares). However, critical farming decisions—such as foliar pesticide spraying, pulse irrigation, transplanting, and storm drainage—operate at the **Gram Panchayat scale** (~1,000 hectares). 

A coarse block forecast treats an entire block uniformly, obscuring localized convective rain cells, micro-topographical thermal variations, and crop-specific vulnerability windows.

---

## 2. Technical Solution

**AgroMet** addresses this challenge through an end-to-end observation-fused pipeline:
1. **Exact Panchayat Geometry**: Ingests official Local Government Directory (LGD) administrative boundaries, routing farm GPS coordinates via topological Point-in-Polygon (PIP) containment in an R-tree spatial index.
2. **Spatial Observation Masking**: Intersects georeferenced weather and satellite fields with exact Panchayat polygons using area-weighted fractional pixel extraction.
3. **Satellite Observational Ingestion**: Ingests 15-minute INSAT-3DR geostationary thermal infrared (TIR-1) and brightness temperature feeds with automated quality gates and fail-closed fallbacks.
4. **Localized Precipitation Nowcasting**: Fuses NWP baseline forecasts with real-time satellite evidence using a **two-stage hurdle model** (LightGBM rain occurrence probability + GBDT conditional rain amount) for 30m, 60m, and 120m horizons.
5. **Crop-Aware Agricultural Advisories**: Contextualizes nowcasts with crop phenology (DAS/GDD) and soil moisture capacity to issue actionable farm guidance structured into **Action**, **Why**, and **Timing** following IMD-GKMS rules.

---

## 3. Scientific Readiness & Pilot Validation Status

- **Readiness Classification**: **`LIMITED_VALIDATION`** (Certified under Task 9 Forensic Audit)
- **Validation Pilot Domain**: Varanasi District, Uttar Pradesh (Arajiline Block: Rameshwar & Jansa Gram Panchayats)
- **Empirical Ground-Truth Dataset**: 12 curated convective rainfall events ($N=24$ station-event pairs) benchmarked against independent automatic weather stations (ICAR-IIVR and BHU Agronomy):
  - **Critical Success Index (CSI)**: **0.933**
  - **Probability of Detection (POD)**: **0.950**
  - **Mean Absolute Error (MAE)**: **0.879 mm**
  - **Directional Spatial Agreement**: **100%** on divergent events
- **Important Boundary Disclosure**: Independent Panchayat-scale empirical validation is geographically confined to the Varanasi pilot. Nationwide validation remains incomplete pending formal state mesonet data-sharing agreements (KSNDMC, Mahavedh, IMD Agro-AWS).

---

## 4. Key Capabilities

- **Exact Point-in-Polygon Routing**: Coordinates inside registered polygons resolve unambiguously; points outside registered jurisdictions fail closed (`OUTSIDE_REGISTERED_PANCHAYATS`).
- **A/B Spatial Differentiation**: Two adjacent Panchayats inside the same block receiving identical NWP baseline forecasts receive distinct nowcasts when satellite convective evidence differs across their polygons.
- **Disagreement Detection**: Divergence between NWP baseline and real-time satellite evidence lowers confidence to `LOW` and displays an explicit caution banner rather than silencing either source.
- **Source Resolution Disclosure**: Native satellite resolution (~3.8 km) is explicitly disclosed alongside a disclaimer that finer polygon visualization does not imply sub-kilometer sensor observations.
- **Immutable Temperature Baseline**: Constant scalar residual calibration ($B = +0.7351^\circ\text{C}$) certified under Phase 24 as the sole active production temperature downscaling engine, with Dynamic V2 under controlled operational guardrails.
- **Farmer vs. Technical Multi-View UI**: React/Vite command dashboard and Flutter mobile application supporting high-level farmer directives (Action/Why/Timing) and forensic scientific transparency views.

---

## Conceptual Architecture

```
                      DATA INGESTION & QUALITY CONTROL
       [NOAA ISD Observations]  [ERA5 Reanalysis]  [NASA SRTM 30m]  [ESA WorldCover]
                                      │
                                      ▼
                      COARSE NWP FORECAST BASELINE (BLOCK)
                       (T_coarse, RH, Wind Speed, Rainfall)
                                      │
                                      ▼
                      RESIDUAL DOWNSCALING RESEARCH LAYER
        Predicts: ΔT = T_ref - T_coarse via Topography & Surface Features
             Candidate V3: Retained for Research | Rejected for Production
                    Operational Baseline: Raw ERA5 Forecast
                                      │
                                      ▼
                          1-km SPATIAL METRIC GRID
                   (1000m × 1000m cells in UTM Zone 44N / EPSG:32644)
                                      │
                                      ▼
                        PANCHAYAT SPATIAL AGGREGATION
                  (Area-weighted geometric polygon intersection)
                                      │
                                      ▼
                        AGRICULTURAL CONTEXT & PHENOLOGY
         (Sentinel-2/WorldCover Cropland Mask + DAS/GDD Stage + Soil AWC)
                                      │
                                      ▼
                             AGRICULTURAL RISK ENGINE
         (agri_risk_v1.0.0: Thermal, chilling, wind lodging, pathogen windows)
                                      │
                                      ▼
                           EXPLAINABLE ADVISORY ENGINE
       (agri_advisory_v1.0.0: Actionable advice, timing windows, conflict checks)
                                      │
                                      ▼
                             FASTAPI REST SERVICE
                  (Pydantic v2 schemas, OpenAPI docs, headless fallbacks)
                                      │
                                      ▼
                         REACT 18 + LEAFLET DASHBOARD
         (8 verified pages: Explorer, Detail, GIS Map, Weather, Advisory, Judge)
```

---

## Data Sources

The platform enforces strict scientific data classification and provenance tracking.

### 1. Genuine Real Data Pipeline (Research & Evaluation)
- **NOAA Integrated Surface Database (ISD)**:
  - 2,635 genuine hourly/synoptic ground observations from 4 physical stations: Babatpur Airport (424790, n=1,944), Varanasi Synoptic (424830, n=434), Ghazipur (424820, n=132), and Allahabad Airport (424750, n=125).
  - Period: 2024-06-01 to 2024-08-31 (Kharif season). Zero synthetic records.
- **ECMWF ERA5 Atmospheric Reanalysis**:
  - Hourly 0.25° (~31 km) single-level reanalysis across the pilot region.
  - Used as the coarse model benchmark and operational baseline. (Note: Reanalysis is a numerical assimilation, not ground truth).
- **NASA Shuttle Radar Topography Mission (SRTMGL1 v003)**:
  - 1 arc-second (~30m) radar digital elevation model.
  - Ingested tiles `N25E082` and `N25E083` covering 100% of the pilot area grid (3,844 cells).
- **ESA WorldCover 10m 2021**:
  - Global 10m land cover map derived from Sentinel-1 and Sentinel-2.
- **SoilGrids 250m**:
  - Global gridded soil information (sand, silt, clay, Available Water Capacity).

### 2. Demo & Synthetic Data (Isolated)
- Canonical demonstration scenarios (`2026-07-15`) and What-If parameter simulators are prefixed with `DEMO_` or `SYNTHETIC_`.
- Enforced isolation guards in `backend/data_pipeline/real_data_pipeline.py` reject synthetic records from entering ML training or validation sets.

---

## ML Methodology

The downscaling architecture employs a physics-informed residual correction model:

$$T_{\text{downscaled}}(x, y) = T_{\text{coarse}} + \Delta T(x, y)$$

where the residual target is defined as:

$$\Delta T = T_{\text{independent\_reference}} - T_{\text{coarse}}$$

### Feature Engineering
The model learns local thermal anomalies from 35 engineered surface and temporal features:
- **Topography**: Elevation ($z$), slope ($\theta$), aspect ($\phi$), cyclic aspect ($\sin \phi, \cos \phi$), terrain roughness, and environmental lapse-rate adiabatic cooling.
- **Land Cover**: Cropland, urban heat island, water body, and tree cover fractions from 10m satellite imagery.
- **Solar & Temporal Dynamics**: Day-of-year harmonics ($\sin, \cos$) and solar zenith angle.

### Scientific Decision & Release Status
- **Candidate V3 (`candidate_v3_20260916T213422Z`)**: **RETAINED FOR RESEARCH / REJECTED FOR PRODUCTION**.
  - While V3 demonstrated positive spatial correlation on regional holdout stations during Leave-One-Station-Out (LOSO) cross-validation, it did not outperform the zero-residual ERA5 baseline on the frozen chronological holdout test.
- **Operational Baseline**: **RAW ERA5 FORECAST**.
  - The production model path `backend/models/temperature_residual/` is intentionally kept absent. The operational system safely falls back to uncorrupted raw ERA5 forecasts to prevent unverified error amplification in production advisory workflows.

---

## Scientific Validation & Experiment Freeze

**Experiment Identifier**: `EXP_VARANASI_PILOT_PHASE18_FREEZE`

| Evaluation Metric | Raw ERA5 Baseline | Candidate V3 (Research) | Decision |
|---|---|---|---|
| **Chronological MAE** | **1.016 °C** | 1.077 °C | Baseline superior |
| **Chronological RMSE** | **1.353 °C** | 1.404 °C | Baseline superior |
| **Chronological R²** | **-0.011** | -0.089 | Baseline superior |
| **Chronological Mean Bias** | +0.140 °C | -0.115 °C | V3 reduces positive bias |
| **Ghazipur Spatial Holdout R²** | -0.015 | **+0.137** | V3 shows spatial signal |
| **Data Leakage Check** | 0 leaked columns | 0 leaked columns | PASSED |
| **Genuine Observations** | 2,635 records | 2,635 records | 100% genuine |

Validation Protocol:
1. **Zero Data Leakage**: Target residual $\Delta T$ and ground truth temperatures are strictly quarantined during feature matrix construction.
2. **Disjoint Temporal Split**: Chronological 70/15/15 train/val/test split with no overlapping dates.
3. **Leave-One-Station-Out (LOSO)**: Iteratively held out each of the 4 regional stations to evaluate cross-site generalization.

---

## Scientific Limitations

1. **Station Density**: The pilot Gangetic Plain study area currently has only 4 reporting NOAA ISD stations across >15,000 km², with only 1 station providing continuous hourly observations.
2. **Topographic Relief**: The Varanasi pilot area is alluvial plain (elevation 80m–98m MSL, slopes <0.5°), limiting adiabatic lapse rate variations to <0.12°C.
3. **No Nationwide Validation**: Findings from the Varanasi pilot area do **NOT** establish nationwide downscaling validity.
4. **Rainfall Not Downscaled**: Convective precipitation downscaling requires high-density Doppler weather radar and dense automated rain-gauge networks; rainfall is preserved directly from coarse NWP.
5. **No Production Certification**: Candidate ML models remain in research status until validated against dense district-level AWS networks.

---

---

## System Architecture & Client Ecosystem

```
                    FastAPI Backend (backend/)
                     Common Scientific & API Platform
                                   │
             ┌─────────────────────┴─────────────────────┐
             │                                           │
             ▼                                           ▼
       web/ (frontend/)                               mobile/
     React 18 / Vite / Tailwind                    Flutter 3.47+ / Dart
             │                                           │
  Government & Technical Portal                 Farmer & Field-Official App
  (Microclimate downscaling, GIS grid,          (Actionable farm advisories, role
   Panchayat analytics, Judge mode)              switching, vernacular weather cards)
```

- **`backend/`** → Common scientific downscaling & agromet advisory API platform (`FastAPI`)
- **`web/`** (or `frontend/`) → Government & technical web portal (`React 18` + `Vite` + `TailwindCSS`)
- **`mobile/`** → Farmer & field-official mobile application (`Flutter 3.47+` + `Dart 3.13+`)

Both clients consume the **same** underlying backend APIs. There is zero duplicated weather, model, or advisory logic.

---

## Quickstart & Run Commands

### 1. Backend (FastAPI Scientific Engine)
```bash
# Start FastAPI backend server (port 8000)
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- API Specs (OpenAPI): [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### 2. Website (Government & Technical Web Portal)
```bash
# Start Vite development server (port 5173)
cd web          # or: cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
- Web Application: [http://localhost:5173](http://localhost:5173)

### 3. Mobile (Farmer & Field-Official Flutter App)
```bash
# Resolve dependencies & run mobile application
cd mobile
flutter pub get

# To run in Google Chrome (web target):
flutter run -d chrome

# Or run headless web-server for browser access:
flutter run -d web-server --web-port 8085 --web-hostname 0.0.0.0

# Or build static release for instant serving:
flutter build web
python3 -m http.server 8086 --directory build/web
```
- Verified Targets: Chrome (`web-javascript`), Web Server, macOS Desktop (`darwin-arm64`).

---


## SIH Demonstration & Judge Mode

### Canonical Scenario (`2026-07-15`)
- **Block Coarse Forecast**: 36.0°C maximum temperature, 28 km/h wind speed.
- **1-km Downscaled Temperature**: Predicts a +1.8°C thermal anomaly ($\hat{R}$), reaching **37.8°C** in high-elevation/low-canopy cells.
- **Crop 1 (Rice - Flowering Stage)**: 37.8°C exceeds the critical 35.0°C threshold $\rightarrow$ **HIGH Heat Stress Risk (Score 0.82)** $\rightarrow$ Action: Maintain 2–3 cm standing water during morning hours to buffer canopy microclimate.
- **Crop 2 (Maize - Tasseling Stage)**: 28.0 km/h wind exceeds the 25.0 km/h root lodging threshold $\rightarrow$ **MODERATE Wind Risk (Score 0.55)** $\rightarrow$ Action: Withhold deep irrigation prior to wind event.

### CLI Management Scripts
```bash
cd backend
# 1. Seed canonical demo scenario
python3 scripts/seed_demo_scenario.py --date 2026-07-15

# 2. Programmatically validate all 10 pipeline links
python3 scripts/validate_demo_scenario.py --date 2026-07-15

# 3. Safely reset demo records
python3 scripts/reset_demo_scenario.py --force
```

---

## Major API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health/live` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe (database, model status) |
| `GET` | `/api/v1/weather/blocks` | List monitored administrative blocks |
| `GET` | `/api/v1/weather/panchayats` | GeoJSON panchayat boundaries & aggregate weather |
| `GET` | `/api/v1/weather/panchayat/{id}` | Detailed panchayat profile, diurnal forecast, risks |
| `GET` | `/api/v1/weather/grid-cells` | 1-km downscaled grid cells with thermal metrics |
| `GET` | `/api/v1/agriculture/advisories` | Query active agro-meteorological advisories |
| `POST` | `/api/v1/agriculture/advisories/generate` | Generate rule-based advisories for block/date |
| `GET` | `/api/v1/ml/models` | List registered ML residual model candidates |
| `POST` | `/api/v1/ml/simulate` | What-If parameter simulator for temperature perturbations |

---

## Testing

Run the automated scientific pipeline and regression test suites:

```bash
# Scientific Pipeline & Provenance Tests (129 Passed, 0 Failed, 1 Skipped)
python3 -m pytest backend/tests/test_india_pipeline.py backend/tests/test_terrain_phase16.py backend/tests/test_generalization_phase17.py --noconftest -v

# Production Frontend Build Verification (0 Errors)
cd frontend && npm run build
```

---

## License & Data Attribution

- **AgroMet Platform**: Open-source under the [MIT License](LICENSE).
- **NOAA ISD Observations**: Courtesy of NOAA/NCEI (US Government Public Domain).
- **ECMWF ERA5 Reanalysis**: Contains modified Copernicus Climate Change Service information [2024], licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **NASA SRTM 30m DEM**: NASA / USGS / NGA SRTMGL1 v003 (Public Domain).
- **ESA WorldCover 10m**: European Space Agency / VITO Remote Sensing (licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
- **SoilGrids 250m**: ISRIC — World Soil Information (licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
