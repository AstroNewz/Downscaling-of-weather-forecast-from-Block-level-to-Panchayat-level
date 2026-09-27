# Data Provenance & Source Traceability Matrix

**Project**: Agroweather-Downscaling — SIH Problem Statement 26074  
**Date**: 2026-09-17  
**Release**: SIH_PHASE20_FINAL  
**Scope**: Varanasi Pilot Area & Regional Ground Stations, Uttar Pradesh, India  

---

## Overview

This document provides complete, transparent scientific attribution, licensing, temporal/spatial specifications, and known physical limitations for all external datasets ingested into the Agroweather-Downscaling system.

> **CRITICAL SCIENTIFIC DISTINCTION**:
> - Reanalysis data (ERA5) is a physical numerical model reconstruction and is **NOT** ground-truth station observation.
> - Station observations (NOAA ISD) represent thermometer measurements at discrete sensor locations.
> - Remote sensing products (SRTM, WorldCover) represent space-borne radar and optical satellite observations.
> - OpenStreetMap boundaries are community-sourced geospatial polygons and do **NOT** constitute official Survey of India / Local Government Directory (LGD) legal cadastral boundaries.

---

## Dataset Provenance Records

### 1. NOAA Integrated Surface Database (ISD) Ground Observations

| Field | Specification |
|---|---|
| **Source** | National Oceanic and Atmospheric Administration (NOAA) / National Centers for Environmental Information (NCEI) |
| **Physical Classification** | `OBSERVATION` |
| **Station Identifiers** | 424790 (Babatpur Airport), 424830 (Varanasi Synoptic), 424820 (Ghazipur), 424750 (Allahabad Airport) |
| **Measured Variables** | Dry-bulb 2m Air Temperature (°C), Dewpoint (°C), Wind Speed (m/s), Wind Direction (°), Sea-Level Pressure (hPa) |
| **Spatial Resolution** | Discrete point stations (lat/lon point coordinates) |
| **Temporal Resolution** | Hourly continuous (Babatpur 424790); 3-hourly to daily synoptic reports (424830, 424820, 424750) |
| **Dataset Period** | 2024-06-01T00:00:00Z through 2024-08-31T23:00:00Z (92 days, Kharif season) |
| **Total Valid Observations** | 2,635 matched records (1,944 at 424790; 434 at 424830; 132 at 424820; 125 at 424750) |
| **License** | US Government Open Data (Public Domain / Unrestricted Reuse) |
| **Access Method** | HTTP REST API / NCEI ISD archive downloads |
| **Local File Artifacts** | `backend/data/raw/india/pilot/noaa_isd_424790_2024.json`<br>`backend/data/raw/india/pilot/noaa_isd_424830_2024.json`<br>`backend/data/raw/india/pilot/noaa_isd_424820_2024.json`<br>`backend/data/raw/india/pilot/noaa_isd_424750_2024.json` |
| **Validation Status** | **VALIDATED** (100% genuine physical ground observations; 0 synthetic records) |
| **Scientific Limitations** | Station density is sparse across the Gangetic Plain (>15,000 km² region covered by only 4 reporting stations, with only 1 station reporting continuous hourly observations). |

---

### 2. ECMWF ERA5 Atmospheric Reanalysis

| Field | Specification |
|---|---|
| **Source** | European Centre for Medium-Range Weather Forecasts (ECMWF) / Copernicus Climate Change Service (C3S) via Open-Meteo Historical Archive |
| **Physical Classification** | `REANALYSIS` (Coarse physical model assimilation — **NOT ground truth**) |
| **Variables Ingested** | 2m Air Temperature (°C), Relative Humidity (%), Total Precipitation (mm), 10m Wind Speed (m/s), Wind Direction (°), Cloud Cover (%) |
| **Spatial Resolution** | 0.25° × 0.25° regular grid (~31 km × 31 km) |
| **Temporal Resolution** | Hourly continuous |
| **Dataset Period** | 2024-06-01T00:00:00Z through 2024-08-31T23:00:00Z (2,208 timesteps per grid cell) |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) / Copernicus Open Access Terms |
| **Access Method** | Open-Meteo Historical Reanalysis API (ECMWF ERA5 data store) |
| **Local File Artifacts** | `backend/data/raw/india/pilot/openmeteo_era5_varanasi_2024.json`<br>`backend/data/raw/india/pilot/openmeteo_era5_varanasi_2024.json.provenance.json` |
| **Validation Status** | **VALIDATED** (100% complete hourly records, zero missing timesteps across pilot period) |
| **Operational Role** | Serves as the coarse model input and the **validated operational baseline** for all agroweather advisories. |
| **Scientific Limitations** | Coarse 31-km resolution cannot resolve localized convective thunderstorm cooling, urban heat islands, or village-level microclimates. |

---

### 3. NASA Shuttle Radar Topography Mission (SRTM) 30m DEM

| Field | Specification |
|---|---|
| **Source** | NASA / USGS / National Geospatial-Intelligence Agency (NGA) via AWS Open Data Registry (`s3://elevation-tiles-prod/skadi/`) |
| **Physical Classification** | `REMOTE_SENSING` |
| **Product Version** | SRTMGL1 Version 003 (1 arc-second) |
| **Variables Derived** | Digital Elevation (m MSL), Topographic Slope (°), Aspect (°), Cyclic Aspect ($\sin, \cos$), Terrain Roughness (m) |
| **Spatial Resolution** | 1 arc-second (~30 m at the equator) |
| **Temporal Resolution** | Static topographic snapshot (February 2000 mission) |
| **Tiles Ingested** | `N25E082.hgt.gz` (SHA-256: `e4db6d8c1bc860cb...`)<br>`N25E083.hgt.gz` (SHA-256: `77cd2d021919d848...`) |
| **Pilot Grid Coverage** | 3,844 of 3,844 grid cells (100.0%) within 62 × 62 AOI grid |
| **License** | NASA Open Data Policy (Public Domain / USGS open access) |
| **Access Method** | S3 Open Data direct download via AWS elevation tiles |
| **Local File Artifacts** | `backend/data/raw/india/pilot/N25E082.hgt.gz`<br>`backend/data/raw/india/pilot/N25E083.hgt.gz`<br>`backend/data/raw/india/pilot/srtm_varanasi_terrain.json` |
| **Validation Status** | **VALIDATED** (Checksums verified; bilinear interpolation for station coordinates; UTM Zone 44N metric projections) |
| **Scientific Limitations** | The Varanasi pilot area lies in the flat alluvial Gangetic plain (elevation 80m to 98m across stations). Topographic slope is less than 0.5° everywhere, yielding a theoretical lapse rate shift under 0.12°C. |

---

### 4. ESA WorldCover 10m 2021 Land Cover

| Field | Specification |
|---|---|
| **Source** | European Space Agency (ESA) / VITO Remote Sensing |
| **Physical Classification** | `REMOTE_SENSING` |
| **Variables Ingested** | Land Cover Class: Cropland (40), Forest (10), Urban/Built-up (50), Water (80), Barren (60), Grassland (30) |
| **Spatial Resolution** | 10 m × 10 m (Sentinel-1 and Sentinel-2 derived) |
| **Temporal Resolution** | Static baseline (2021 annual classification) |
| **Tile Ingested** | `ESA_WorldCover_10m_2021_v200_N24E081_Map.tif` (126.7 MB) |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Access Method** | Direct HTTPS download from AWS S3 ESA WorldCover repository |
| **Local File Artifacts** | `backend/data/raw/india/pilot/ESA_WorldCover_10m_2021_v200_N24E081_Map.tif`<br>`backend/data/raw/india/pilot/ESA_WorldCover_10m_2021_v200_N24E081_Map.tif.provenance.json` |
| **Validation Status** | **VALIDATED** (SHA-256 verified: `c55e245d83af125c...`) |
| **Scientific Limitations** | Land cover is based on 2021 satellite passes; seasonal within-year crop rotation shifts are not dynamically tracked. |

---

### 5. ISRIC SoilGrids 2.0

| Field | Specification |
|---|---|
| **Source** | ISRIC — World Soil Information |
| **Physical Classification** | `DERIVED` (Machine-learning spatial interpolation from soil profile databases) |
| **Variables Ingested** | Sand (g/kg), Silt (g/kg), Clay (g/kg), Soil Organic Carbon (dg/kg), pH ($H_2O$), Available Water Capacity |
| **Spatial Resolution** | 250 m |
| **Temporal Resolution** | Static |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Access Method** | ISRIC REST API point queries |
| **Local File Artifacts** | `backend/data/raw/india/pilot/soilgrids_varanasi_pilot_points.json`<br>`backend/data/raw/india/pilot/soilgrids_varanasi_pilot_points.json.provenance.json` |
| **Validation Status** | **VALIDATED** (Points queried for pilot centroids; default textures validated against ICAR regional soil surveys) |
| **Scientific Limitations** | Represents regional pedological estimates; does not substitute for laboratory soil testing in individual farm plots. |

---

### 6. Administrative Boundaries (OpenStreetMap / Demonstration)

| Field | Specification |
|---|---|
| **Source** | OpenStreetMap (OSM) contributors via Overpass API / SIH Demonstration Fixtures |
| **Physical Classification** | `ADMINISTRATIVE` (Crowdsourced geospatial boundary — **NOT official legal cadastral boundary**) |
| **Variables Ingested** | Polygon geometries, block names, village centroids |
| **Spatial Resolution** | Variable polygon vectors |
| **License** | Open Data Commons Open Database License (ODbL) |
| **Access Method** | Overpass QL API query |
| **Local File Artifacts** | `backend/data/raw/india/pilot/admin_boundaries_varanasi_osm.json`<br>`backend/data/raw/india/pilot/admin_boundaries_varanasi_osm.json.provenance.json` |
| **Validation Status** | **NON-OPERATIONAL / DEMONSTRATION ONLY** |
| **Scientific Limitations** | OSM administrative boundaries in rural India often lack legal revenue village demarcation. Official government deployment requires cadastral integration via the Ministry of Panchayati Raj / Local Government Directory (LGD). |

---

## Provenance Integrity Summary

- **Real Observation Records**: 2,635 matched rows
- **Synthetic Ground Records**: 0
- **Source Labels**: 100% verified (NOAA = `OBSERVATION`, ERA5 = `REANALYSIS`, SRTM/WorldCover = `REMOTE_SENSING`, SoilGrids = `DERIVED`)
- **Leakage Safeguards**: Quarantined audit fields, chronological disjoint splitting, and Leave-One-Station-Out cross-validation enforced across all data loaders.
