# India Pilot Dataset — Varanasi, Uttar Pradesh

**Project**: Agroweather-Downscaling — SIH Problem Statement 26074  
**Pilot Location**: Varanasi District, Uttar Pradesh, India  
**Last updated**: 2026-09-17  

> **Important**: This document records the **actual data acquisition state** of the Varanasi pilot dataset. The existence of a download script does **not** mean data has been acquired. The existence of a download URL does **not** mean data has been validated. Each source is explicitly classified as one of:
> - `DOWNLOADED` — data files confirmed on disk
> - `SOURCE_ACCESS_REQUIRED` — download script exists but credentials/registration needed
> - `UNAVAILABLE` — source not accessible or not applicable

---

## Pilot Geography

| Field | Value |
|---|---|
| Country | India |
| State | Uttar Pradesh |
| District | Varanasi |
| Pilot AOI | Varanasi district, bounded by 25.10–25.60°N, 82.70–83.20°E |
| CRS (geographic) | EPSG:4326 (WGS84) |
| CRS (metric, dynamic) | EPSG:32644 — WGS 84 / UTM Zone 44N |
| Grid resolution | 1 km × 1 km |
| Pilot period | 2024-06-01 to 2024-08-31 (Kharif season) |

### Project Blocks

| Block | Notes |
|---|---|
| Varanasi Sadar | Primary block (headquarters) |
| Pindra | Candidate spatial holdout block |
| Arajiline | Pilot block |
| Cholapur | Pilot block |
| Kashi Vidyapeeth | Pilot block |
| Badagaon | Secondary pilot block |
| Sevapuri | Secondary pilot block |
| Harahua | Secondary pilot block |
| Chiraigaon | Secondary pilot block |

### AWS Station References

| Station ID | Name | Latitude | Longitude | Organization | Acquisition Status |
|---|---|---|---|---|---|
| AWS_BHU_001 | BHU Automatic Weather Station | 25.2677°N | 82.9913°E | BHU / IMD | **SOURCE_ACCESS_REQUIRED** |
| AWS_BABATPUR_002 | Babatpur Airport AWS | 25.4520°N | 82.8590°E | IMD / AAI | **SOURCE_ACCESS_REQUIRED** |

> These stations are configured in `india_pilot.yaml`. They have **not** been confirmed as downloaded. Station data requires a formal IMD data sharing agreement.

---

## Dataset Source Table

### 1. IMD Automatic Weather Station Network

| Field | Value |
|---|---|
| **Dataset** | IMD AWS Network — Varanasi stations |
| **Provider** | India Meteorological Department (IMD) |
| **Official URL** | https://mausam.imd.gov.in/ |
| **Documentation URL** | https://www.imd.gov.in/pages/services_data.php |
| **Source type** | `OBSERVATION` — direct physical measurements |
| **Spatial resolution** | Point station |
| **Temporal resolution** | Sub-hourly to hourly |
| **Variables** | Temperature (°C), Relative Humidity (%), Precipitation (mm), Wind speed (km/h), Wind direction (°) |
| **Time coverage** | Historical archive; 2024 Kharif season needed |
| **License / Access** | Government of India Open Data License (GODL) — **formal data sharing agreement required** |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** |
| **Action required** | Contact IMD for institutional data sharing agreement: https://www.imd.gov.in/pages/services_data.php |
| **Role in model** | **PRIMARY REFERENCE** — ground truth for target construction (`reference_temperature_c`) |

> **Critical**: IMD AWS is the preferred reference for station-observed validation. Without it, the model can only be evaluated against REANALYSIS-to-REANALYSIS targets (ERA5-Land vs ERA5), which is a lower-quality validation. IMD data access is the single most important data acquisition step.

---

### 2. ERA5 — Hourly Reanalysis on Single Levels

| Field | Value |
|---|---|
| **Dataset** | ERA5 Hourly Reanalysis |
| **Provider** | ECMWF / Copernicus Climate Change Service (C3S) |
| **Official URL** | https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels |
| **Documentation URL** | https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5 |
| **Source type** | `REANALYSIS` — **NOT an observation** |
| **Spatial resolution** | ~31 km (0.25°) |
| **Temporal resolution** | Hourly |
| **Variables** | 2m temperature (K), 2m dewpoint (K), 10m u/v wind (m/s), total precipitation (m), total cloud cover (fraction) |
| **Units note** | Temperature: K → subtract 273.15 for °C; Precipitation: m → multiply by 1000 for mm; Cloud cover: fraction → multiply by 100 for % |
| **Time coverage** | 1940–present (pilot period: 2024-06-01 to 2024-08-31) |
| **License / Access** | Copernicus Climate Change Service License — free for research; requires free CDS account and `~/.cdsapirc` configuration |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** (CDS account needed) |
| **Action required** | Register at https://cds.climate.copernicus.eu and configure `~/.cdsapirc` |
| **Role in model** | **COARSE INPUT (X)** — coarse weather predictor (`forecast_temp_min`, `forecast_temp_max`, `forecast_rainfall_mm`, etc.) |

> **Classification note**: ERA5 is `REANALYSIS`. It must **never** be classified as `OBSERVATION`. Using ERA5 as both the coarse input and the reference temperature simultaneously would cause `target = 0` (pure circular comparison) — this is enforced by `TargetBuilder` which raises `ValueError`.

---

### 3. ERA5-Land — Hourly Reanalysis

| Field | Value |
|---|---|
| **Dataset** | ERA5-Land Hourly Reanalysis |
| **Provider** | ECMWF / Copernicus Climate Change Service (C3S) |
| **Official URL** | https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land |
| **Documentation URL** | https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5-land |
| **Source type** | `REANALYSIS` — **NOT an observation** |
| **Spatial resolution** | ~9 km (0.1°) — finer than ERA5 |
| **Temporal resolution** | Hourly |
| **Variables** | 2m temperature (K), 2m dewpoint (K), 10m u/v wind (m/s), total precipitation (m), surface pressure (Pa) |
| **Time coverage** | 1950–present |
| **License / Access** | Copernicus Climate Change Service License — same CDS credentials as ERA5 |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** (same CDS account as ERA5) |
| **Role in model** | **REFERENCE TEMPERATURE FALLBACK** — used as `reference_temperature_c` **only if** IMD AWS data is unavailable. This gives REANALYSIS-to-REANALYSIS evaluation, explicitly labelled as such. |

> **Warning**: Using ERA5-Land as the reference produces a REANALYSIS-to-REANALYSIS downscaling comparison (ERA5 31 km → ERA5-Land 9 km). This is scientifically valid but must **never** be called "station-observed validation". The model is learning to bridge coarse and fine reanalysis grids, not to fit real station observations.

---

### 4. SRTM 30m Digital Elevation Model

| Field | Value |
|---|---|
| **Dataset** | SRTM 1 Arc-Second Global (SRTMGL1 v003) |
| **Provider** | NASA / USGS |
| **Official URL** | https://lpdaac.usgs.gov/products/srtmgl1v003/ |
| **Documentation URL** | https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm |
| **Source type** | `REMOTE_SENSING` — acquired Feb 2000 |
| **Spatial resolution** | 30 m (1 arc-second) |
| **Temporal resolution** | Static (single acquisition, February 11–22, 2000) |
| **Variables** | `elevation_m` (metres above mean sea level) |
| **Time coverage** | Static |
| **License / Access** | NASA/USGS — free for scientific use. Requires NASA Earthdata account for HTTP download |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** |
| **Tiles needed** | N25E082, N25E083 (for Varanasi AOI) |
| **Action required** | Register at https://urs.earthdata.nasa.gov/ and download via `download_dem.py` |
| **Role in model** | **SPATIAL PREDICTOR** — `obs_elevation_m`, `block_elevation_m`, `elevation_diff_m`, `slope_deg`, `aspect_deg`, `terrain_roughness`, `lapse_rate_temp_adjustment_c` |

---

### 5. Bhuvan LULC (National Land Use Land Cover)

| Field | Value |
|---|---|
| **Dataset** | National LULC Map 1:50,000 scale (India) |
| **Provider** | NRSC / ISRO (National Remote Sensing Centre) |
| **Official URL** | https://bhuvan.nrsc.gov.in/bhuvan_links.php |
| **Documentation URL** | https://bhuvan.nrsc.gov.in/ |
| **Source type** | `REMOTE_SENSING` |
| **Spatial resolution** | ~56 m (1:50,000 scale) |
| **Temporal resolution** | Biennial update |
| **Variables** | `lulc_class` (categorical: cropland, forest, urban, water, barren, etc.) |
| **License / Access** | NRSC Open Data Archive — non-commercial use; requires free Bhuvan account (`BHUVAN_USER`, `BHUVAN_PASS` environment variables) |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** |
| **Role in model** | **SPATIAL PREDICTOR (PRIMARY)** — `cropland_fraction`, `forest_fraction`, `urban_fraction`, `water_fraction`, `barren_fraction` — Indian authoritative LULC |

---

### 6. ESA WorldCover 10m

| Field | Value |
|---|---|
| **Dataset** | ESA WorldCover 10m v200 (2021) |
| **Provider** | ESA / VITO |
| **Official URL** | https://esa-worldcover.org/en |
| **Documentation URL** | https://esa-worldcover.org/en |
| **Source type** | `REMOTE_SENSING` |
| **Spatial resolution** | 10 m |
| **Temporal resolution** | Annual |
| **Variables** | `lulc_class` (categorical) |
| **Time coverage** | 2021 (static reference) |
| **License / Access** | CC BY 4.0 — open access, no credentials required |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** |
| **Tile needed** | N24E081 (for Varanasi) |
| **Role in model** | **SPATIAL PREDICTOR (FALLBACK)** — used if Bhuvan LULC unavailable |

---

### 7. SoilGrids 2.0

| Field | Value |
|---|---|
| **Dataset** | SoilGrids 2.0 |
| **Provider** | ISRIC — World Soil Information |
| **Official URL** | https://soilgrids.org/ |
| **Documentation URL** | https://www.isric.org/explore/soilgrids |
| **Source type** | `DERIVED` |
| **Spatial resolution** | 250 m |
| **Temporal resolution** | Static |
| **Variables** | `soc` (dg/kg), `phh2o` (pH×10), `clay` (g/kg), `sand` (g/kg), `silt` (g/kg), `bdod` (cg/cm³) |
| **License / Access** | CC BY 4.0 — open REST API, no credentials required |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** (rate-limited API) |
| **Role in model** | **AGRICULTURAL CONTEXT** — soil properties for advisory engine (not temperature ML features) |

---

### 8. LGD Administrative Boundaries

| Field | Value |
|---|---|
| **Dataset** | Local Government Directory (LGD) Administrative Boundaries |
| **Provider** | Ministry of Panchayati Raj / MoRD, Government of India |
| **Official URL** | https://lgdirectory.gov.in/ |
| **Documentation URL** | https://lgdirectory.gov.in/ |
| **Source type** | `ADMINISTRATIVE` |
| **Spatial resolution** | Cadastral-level (district, block, panchayat polygons) |
| **Temporal resolution** | Static (administrative) |
| **Variables** | district, block, panchayat polygons |
| **License / Access** | Government of India Open Data License (GODL) |
| **Acquisition status** | **SOURCE_ACCESS_REQUIRED** |
| **Role in model** | **SPATIAL AGGREGATION** — panchayat → block → district hierarchy for output delivery |

---

## Acquisition Status Summary

| Source | Type | Status |
|---|---|---|
| IMD AWS Stations | OBSERVATION | **SOURCE_ACCESS_REQUIRED** |
| ERA5 (hourly) | REANALYSIS | **SOURCE_ACCESS_REQUIRED** |
| ERA5-Land (hourly) | REANALYSIS | **SOURCE_ACCESS_REQUIRED** |
| SRTM 30m DEM | REMOTE_SENSING | **SOURCE_ACCESS_REQUIRED** |
| Bhuvan LULC 50K | REMOTE_SENSING | **SOURCE_ACCESS_REQUIRED** |
| ESA WorldCover 10m | REMOTE_SENSING | **SOURCE_ACCESS_REQUIRED** |
| SoilGrids 2.0 | DERIVED | **SOURCE_ACCESS_REQUIRED** |
| LGD Boundaries | ADMINISTRATIVE | **SOURCE_ACCESS_REQUIRED** |

---

## Current Pipeline Status

```
PIPELINE IMPLEMENTED      : YES  — all modules exist and are tested
REAL DATA ACQUIRED        : NO   — all sources require credential setup
REAL DATA VALIDATED       : NO   — no data files to validate yet
CANDIDATE MODEL TRAINED   : NO   — REAL_REFERENCE_DATA_REQUIRED
PRODUCTION MODEL          : UNCHANGED
```

### What "Pipeline Implemented" means

- Download scripts exist for all sources
- Validation module (`IndiaDataValidator`) is implemented
- Feature engineering module (`RealDataFeatureEngineer`) is implemented
- Target construction module (`TargetBuilder`) is implemented
- Chronological splitter is implemented
- Manifest writer is implemented
- Candidate training script is implemented
- Test suite is implemented (54 tests across 8 test classes)

### What still requires manual action

1. **ERA5 / ERA5-Land**: Register at https://cds.climate.copernicus.eu, configure `~/.cdsapirc`, run `download_era5.py`
2. **SRTM DEM**: Register at https://urs.earthdata.nasa.gov/, run `download_dem.py`
3. **IMD AWS** (most important): Contact IMD formally for data sharing agreement, then run `download_imd.py`
4. **Bhuvan LULC**: Register at https://bhuvan.nrsc.gov.in, set `BHUVAN_USER`/`BHUVAN_PASS`, run `download_lulc.py`
5. **ESA WorldCover**: Open access — run `download_lulc.py` with WorldCover option
6. **LGD Boundaries**: Run `download_india_boundaries.py`

---

## Important Classification Warnings

> **ERA5 and ERA5-Land are REANALYSIS, not OBSERVATION.**  
> They are model-assimilated historical reconstructions, not direct physical measurements.  
> Any report that calls ERA5-based metrics "station-observed validation" is scientifically incorrect.

> **A downloader script existing does not mean data was downloaded.**  
> Check `data_acquisition_status.json` (written by `utils/acquisition_status.py`) for actual status.

> **DEMO_DATA and SYNTHETIC_DATA are entirely separate from this real-data pipeline.**  
> They exist in separate directories and are rejected at the feature engineering, manifest, and training stages by code — not just convention.

---

*For pipeline architecture and implementation details, see [REAL_INDIA_DATA_PIPELINE.md](./REAL_INDIA_DATA_PIPELINE.md).*
