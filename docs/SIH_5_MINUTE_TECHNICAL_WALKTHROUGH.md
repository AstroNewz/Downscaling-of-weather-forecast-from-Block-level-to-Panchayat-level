# 5-Minute Technical Walkthrough Script — SIH Hackathon Jury Presentation

**Project**: Agroweather-Downscaling — SIH Problem Statement 26074  
**Date**: 2026-09-17  
**Release**: SIH_PHASE20_FINAL  
**Live Demo Route**: `http://127.0.0.1:5173/judge`  

---

## Presentation Timing & Narrative Breakdown

### [0:00 – 0:30] Problem: The Resolution Gap in Agricultural Weather
- **Narrative**:  
  "Respected Judges, numerical weather prediction models like IMD-GFS and ECMWF ERA5 operate at a coarse scale of 12 to 31 km. While this forecasts regional rain bands, it completely averages out local microclimates. A single 25-km block grid covers both upland fields and river floodplains, yet agricultural vulnerability happens at the Panchayat and field level. A farmer's rice crop at the flowering stage suffers irreversible pollen sterility if temperatures exceed 35°C for even two hours. Coarse models report 33°C, completely missing the 36.5°C canopy heat shock. Our platform solves this by downscaling weather forecasts to 1-km resolution and integrating crop phenology and soil moisture to generate actionable advisories."

---

### [0:30 – 1:15] System Architecture
- **Narrative**:  
  "Our architecture consists of a full-stack, modular, leakage-controlled pipeline:
  1. **Weather Ingestion**: Ingests numerical reanalyses and ground station observations.
  2. **Topographic Engine**: Bilinearly interpolates 30m NASA SRTM radar elevation, slope, aspect, and roughness.
  3. **Downscaling Research Layer**: Trains residual gradient-boosted trees ($T_{\text{downscaled}} = T_{\text{coarse}} + \Delta T$).
  4. **GIS Spatial Intersector**: Constructs 1000m × 1000m metric grids in local UTM Zone 44N and performs area-weighted polygon intersections.
  5. **Cropland Mask**: Applies ESA WorldCover 10m satellite classification to exclude rivers, forests, and roads from farm advisories.
  6. **Agronomic Risk Engine**: Correlates microclimate with crop stage (DAS, flowering, tasseling) and soil available water capacity (AWC).
  7. **User Interface**: React/Vite dashboard featuring an interactive Leaflet map, What-If simulator, and dedicated Judge Mode."

---

### [1:15 – 2:00] Weather Downscaling Methodology
- **Narrative**:  
  "We employ a residual learning paradigm rather than directly predicting absolute temperature:
  $$\Delta T = T_{\text{observation}} - T_{\text{coarse reanalysis}}$$
  $$\hat{T}_{\text{downscaled}} = T_{\text{coarse}} + \hat{\Delta T}_{\text{XGBoost}}$$
  Our model uses 40 leakage-controlled features including ERA5 3h/6h/12h/24h rolling reanalysis statistics, diurnal solar cyclic encodings, NASA SRTM elevation, finite-difference slope, cyclic aspect, and ESA WorldCover land use fractions.
  Crucially, all rolling lag features are computed exclusively backwards in time using coarse reanalysis data — zero observation data enters the feature matrix."

---

### [2:00 – 2:45] GIS Pipeline & 1-km Metric Grid
- **Narrative**:  
  *(Demonstrating `/map` on screen)*  
  "In GIS processing, using Web Mercator (EPSG:3857) introduces up to 10% scale distortion across Uttar Pradesh. We dynamically compute the local metric UTM zone — EPSG:32644 (UTM Zone 44N) — ensuring that every grid cell is physically 1,000 meters by 1,000 meters.
  We then apply the ESA WorldCover 10m raster mask to extract exact cropland fractions. When aggregating downscaled grid values to Gram Panchayat polygons, we use area-weighted spatial intersection, weighting each grid cell by its exact agricultural hectare footprint within the Panchayat boundary."

---

### [2:45 – 3:30] Panchayat & Crop Phenology Context
- **Narrative**:  
  *(Demonstrating `/panchayats/1` on screen)*  
  "Weather alone does not create an agricultural risk. Risk is the intersection of a weather hazard, crop vulnerability, and soil buffer:
  $$\text{Risk} = f(\text{Hazard}_{\text{weather}}, \text{Vulnerability}_{\text{stage}}, \text{Buffer}_{\text{soil}})$$
  In our canonical demonstration in Maya Bazar Panchayat:
  - We track **Rice (Paddy)** at the critical **Flowering / Anthesis** stage (75 Days After Sowing).
  - We track **Maize** at the **Tasseling** stage.
  - The soil is an Alluvial Silt Loam with an Available Water Capacity of 145 mm/m.
  Because rice is flowering, it is hypersensitive to temperatures above 35°C."

---

### [3:30 – 4:15] Agronomic Risk Engine & Explainable Advisories
- **Narrative**:  
  *(Demonstrating `/advisories` on screen)*  
  "Our risk engine evaluates deterministic agronomic rules:
  1. **Heat Stress Detection**: Downscaled maximum temperature reaches 37.8°C, exceeding the 35.0°C threshold by 2.8°C. A `CRITICAL` priority advisory is generated.
  2. **Explainable Action Plan**: Rather than vague advice, it provides concrete, timed steps:
     - Apply light surface irrigation between 05:00 and 08:00 IST for canopy evaporative cooling.
     - Strictly avoid foliar pesticide spraying during 11:00–15:30 IST to prevent leaf scorch.
     - Maintain a 3–5 cm water buffer in paddy basins.
  3. **Safety & Guardrails**: Our engine never prescribes chemical dosages, never diagnoses diseases from weather alone, and checks for multi-hazard trade-offs."

---

### [4:15 – 4:45] Scientific Validation & Leakage Controls
- **Narrative**:  
  *(Demonstrating `/system-status` on screen)*  
  "Unlike black-box demonstrations, our system was audited with rigorous scientific controls:
  - **Data**: 2,635 genuine NOAA ISD observations across 4 stations (Babatpur Airport, Varanasi Synoptic, Ghazipur, Allahabad Airport) spanning the 92-day Kharif season. Exactly 0 synthetic records.
  - **Leakage Controls**: Strict chronological train/val/test splitting ($\text{Train} < \text{Val} < \text{Test}$).
  - **Leave-One-Station-Out (LOSO)**: Evaluated across all 4 stations to test spatial transferability.
  - **Automated Tests**: 129 automated unit and integration tests passing with 0 failures."

---

### [4:45 – 5:00] Scientific Transparency & Model Decision
- **Narrative**:  
  "We adhere to strict scientific honesty:
  In the Varanasi alluvial plain, the elevation range across all stations is only 18 meters (80m to 98m), resulting in an adiabatic lapse rate effect of under 0.12°C. While our research model captures diurnal timing corrections, it does not outperform the raw ERA5 reanalysis baseline on the frozen temporal holdout.
  Therefore, our formal scientific decision is:
  - **Candidate V3 is RETAINED FOR RESEARCH and REJECTED FOR PRODUCTION.**
  - **Raw ERA5 remains our operational baseline.**
  - Operational nationwide downscaling certification requires high-density automated weather station networks and topographically diverse foothill terrain.
  Thank you, and we welcome your questions."
