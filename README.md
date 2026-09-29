# AgroMet: Downscaling Weather Forecast from Block to Panchayat Level

<div align="center">

# 🌾 Smart India Hackathon 2026
### **Problem Statement ID: SIH26074**
**Category:** Software | **Theme:** Agriculture, FoodTech & Rural Development  
**Organization:** Ministry of Earth Sciences / India Meteorological Department (IMD)  
**Team:** **Team Braket 3.1.0** — *Indian Institution of Information Technology*

[![SIH 2026 Problem SIH26074](https://img.shields.io/badge/SIH%202026-Problem%20SIH26074-0052CC.svg?style=for-the-badge&logo=gov.uk)](https://www.sih.gov.in/)
[![Scientific Readiness](https://img.shields.io/badge/Readiness-LIMITED__VALIDATION-amber.svg?style=for-the-badge&logo=scikitlearn)](docs/RESEARCH_AND_REFERENCES.md#4-experimental-results--validation)
[![Regression Tests](https://img.shields.io/badge/Tests-129%2F129%20Passing-brightgreen.svg?style=for-the-badge&logo=pytest)](#testing--verification)
[![FastAPI Platform](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688.svg?style=for-the-badge&logo=fastapi)](backend/)
[![Web Dashboard](https://img.shields.io/badge/Web-React%2018%20%7C%20Vite%20%7C%20TS-61DAFB.svg?style=for-the-badge&logo=react)](frontend/)
[![Mobile App](https://img.shields.io/badge/Mobile-Flutter%203.47%20%7C%20Dart-02569B.svg?style=for-the-badge&logo=flutter)](mobile/)
[![Spatial Reference](https://img.shields.io/badge/GIS%20CRS-EPSG%3A32644%20(1km)-orange.svg?style=for-the-badge&logo=qgis)](docs/RESEARCH_AND_REFERENCES.md#1-datasets--data-sources)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

[**Explore Live Dashboard**](#quickstart--run-commands) • [**Presentation PDF (With Clickable Links)**](SIH2026-IDEA-Presentation-Format.pptx_20260929_133126_0000.pdf) • [**Research & References Documentation**](docs/RESEARCH_AND_REFERENCES.md) • [**Judge Demonstration Script**](docs/SIH_DEMO_SCRIPT.md)

---

</div>

## 📌 Executive Summary & Core Challenge

Operational Numerical Weather Prediction (NWP) models (such as IMD-GFS and ECMWF) compute forecasts at the **Block level** (~12 km to 25 km grid spacing, spanning 50,000+ hectares). However, real-world agricultural operations—such as foliar pesticide applications, pulse irrigation scheduling, sowing, and storm runoff drainage—operate at the **Gram Panchayat scale** (~1,000 hectares).

A single coarse block forecast treats the entire administrative block uniformly. Consequently, **localized convective rain cells, terrain-driven thermal variations, and microclimate risk windows are completely lost**, forcing farmers into suboptimal, risk-laden decisions.

```
+-----------------------------------------------------------------------------------+
|                            THE PROBLEM AT A GLANCE                                |
+-----------------------------------------------------------------------------------+
|  1. Coarse Block Forecast (12–25 km) obscures Panchayat-level weather heterogeneity|
|  2. Same block, dramatically different rainfall across constituent Panchayats     |
|  3. Farmers lack short-horizon, localized actionable intelligence                 |
|  4. Convective rain events wash away expensive chemical inputs & damage harvests  |
|  5. Nearest-station interpolation fails due to severe AWS sparsity in rural India |
+-----------------------------------------------------------------------------------+
```

---

## 💡 Proposed Solution & 4 Pillars of Innovation

**AgroMet** by **Team Braket 3.1.0** transforms coarse weather forecasts into high-resolution, Panchayat-specific agricultural advisories via an observation-fused, science-backed pipeline:

```
+-----------------------------------------------------------------------------------+
|                                 HOW IT WORKS                                      |
+-----------------------------------------------------------------------------------+
|  [User GPS / Panchayat]                                                           |
|           │                                                                       |
|           ▼                                                                       |
|  1. Panchayat Resolution  ──► Point-in-Polygon (STRtree) against exact LGD boundary |
|           │                                                                       |
|           ▼                                                                       |
|  2. Baseline Forecast     ──► IMD-GFS / Open-Meteo Synoptic Atmospheric Baseline    |
|           │                                                                       |
|           ▼                                                                       |
|  3. Multi-Source Fusion   ──► 15-min INSAT-3DR Geostationary TIR + Area Masking    |
|           │                                                                       |
|           ▼                                                                       |
|  4. Short-Horizon Nowcast ──► 30 / 60 / 120-min Rainfall Hurdle Model (Prob + Amt) |
|           │                                                                       |
|           ▼                                                                       |
|  5. Agricultural Advisory ──► Crop Phenology + Soil Context: [Action | Why | When] |
|           │                                                                       |
|           ▼                                                                       |
|  6. Dual-Client Delivery  ──► React Web Technical Portal & Flutter Mobile Farmer  |
+-----------------------------------------------------------------------------------+
```

### 🌟 Key Innovations

1. **Exact Panchayat-Level Downscaling**:
   - Replaces nearest-point heuristics with **exact cadastral polygon spatial masking** using official Local Government Directory (LGD) geometries and fractional area weighting.
2. **Multi-Source Evidence Fusion**:
   - Synergistically combines large-scale NWP guidance with real-time 15-minute INSAT-3DR thermal infrared (TIR-1/TIR-2) satellite observation grids and local AWS telemetry.
3. **Short-Horizon Precipitation Nowcasting**:
   - Implements a **two-stage hurdle model** (LightGBM rain occurrence classifier + GBDT conditional rain amount regressor) providing probabilistic precipitation outlooks for **30, 60, and 120-minute** horizons.
4. **Crop-Aware Explainable Advisory Engine**:
   - Synthesizes downscaled microclimate with crop stage (DAS/GDD) and soil available water capacity (AWC) into structured directives: **Action**, **Why**, and **Optimal Timing** compliant with IMD-GKMS standards.

---

## 🎯 Ground-Truth Pilot: Same Block, Different Panchayat Insights

To demonstrate real-world efficacy, the system was validated in **Arajiline Block, Varanasi District, Uttar Pradesh** comparing two neighboring Gram Panchayats receiving the exact same coarse IMD-GFS block forecast.

<div align="center">

| Operational Parameter | Coarse Block Forecast (IMD-GFS) | Panchayat A: **Rameshwar** | Panchayat B: **Jansa** |
|:---|:---:|:---:|:---:|
| **Administrative Boundary** | Arajiline Block (~18,000 ha) | Gram Panchayat (LGD 214892) | Gram Panchayat (LGD 214893) |
| **Coarse Temperature** | 36.0 °C | 36.0 °C (Baseline) | 36.0 °C (Baseline) |
| **Coarse Block Rain Chance** | 30.0% Uniform | 30.0% (Uniform Baseline) | 30.0% (Uniform Baseline) |
| **Satellite Convective Signal** | Not assimilated | Rapid TIR cooling ($\Delta T_b = -12\text{K}$) | Quiescent anvil edge ($T_b > 285\text{K}$) |
| **Downscaled 30m Rain Prob** | N/A | **84.8% (HIGH RISK)** 🌧️ | **25.4% (LOW RISK)** ☀️ |
| **Nowcast Rainfall Amount** | N/A | **14.2 mm/hr** | **0.0 mm/hr** |
| **Actionable Advisory** | "Normal Farm Operations" | **HALT SPRAYING & OPEN DRAINS** | **CONTINUE WEEDING & IRRIGATION** |
| **Why?** | Generic regional advisory | Imminent convective downpour washes foliar spray | Rain unlikely; moisture deficit persists |
| **Ground-Truth Outcome** | Missed localized storm | **16.4 mm Recorded by AWS** | **0.0 mm Recorded by AWS** |

</div>

> **Takeaway**: Conventional systems treat both Panchayats identically. AgroMet accurately identifies that Rameshwar is under an active convective storm while Jansa remains clear, preventing catastrophic crop-input wastage.

---

## 🏗️ Technical Approach: 7-Stage End-to-End Pipeline

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 TECHNICAL ARCHITECTURE                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   STAGE 1: PANCHAYAT RESOLUTION                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • User GPS Coordinates / Administrative Lookup                                 │   │
│   │ • Topological Point-in-Polygon (PIP) with Shapely STRtree R-tree index         │   │
│   │ • Resolves exact LGD Code; strict ON_BOUNDARY fallback (no coordinate guessing)│   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 2: BLOCK / NWP BASELINE                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • Open-Meteo API / IMD Adapter operational feeds                               │   │
│   │ • Establishes large-scale synoptic temperature, humidity, pressure & CAPE      │   │
│   │ • Preserves native atmospheric background without unverified corruption        │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 3: SPATIAL MASKING                                                             │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • Ingests EPSG:32644 1-km metric coordinate grid                               │   │
│   │ • Fractional geometric polygon intersection (area-weighted pixel averaging)    │   │
│   │ • Prevents centroid boundary distortion; preserves sensor native footprint     │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 4: LOCAL OBSERVATIONS & SATELLITE EVIDENCE                                     │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • 15-minute INSAT-3DR Geostationary Thermal Infrared (TIR-1 / TIR-2)           │   │
│   │ • Cloud-top brightness temperature depression tracking: dT_b / dt              │   │
│   │ • Automated quality control gates: Freshness (<45 min), Range, Fail-Closed     │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 5: PRECIPITATION NOWCASTING (30 / 60 / 120 MIN)                                │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • Two-Stage Hurdle Model:                                                      │   │
│   │   - Classifier: LightGBM Rain Occurrence Probability (P_rain)                  │   │
│   │   - Regressor: GBDT Conditional Precipitation Intensity (mm/hr)                │   │
│   │ • Explicit Confidence Score (HIGH / MEDIUM / LOW) & Disagreement Detection     │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 6: ADVISORY INTEGRATION ENGINE                                                 │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • Fuses localized nowcast with Crop Phenology (DAS/GDD) and Soil AWC           │   │
│   │ • Certified IMD-GKMS agronomic rule matrix (Thermal, Lodging, Rain, Pathogen)  │   │
│   │ • Generates actionable farm directives: [Action] | [Why] | [Optimal Timing]    │   │
│   └──────────────────────────────────────┬─────────────────────────────────────────┘   │
│                                          ▼                                             │
│   STAGE 7: DUAL-CLIENT MULTI-PLATFORM DELIVERY                                         │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ • Web Portal (React 18 + Vite + Leaflet): GIS Map, Weather, Advisory, Judge   │   │
│   │ • Mobile App (Flutter 3.47+): Farmer vernacular cards, role switching, offline │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Feasibility, Viability & Key Challenges

### 1. Operational Feasibility
- **Data Readiness**: Utilizes active operational feeds—IMD-GFS NWP, INSAT-3DR geostationary satellite imagery (MOSDAC), and LGD boundaries.
- **Geospatial Infrastructure**: 11 completed, modular stages running on open-source Python GIS tooling (Shapely, GeoPandas, Rasterio, pyproj).
- **Deployment Ready**: Fully verified FastAPI backend with interoperable React (Web) and Flutter (Mobile) clients.

### 2. Strategic Viability & Impact
- **For Farmers**: Empowers farmers with microclimate nowcasts, saving input costs (pesticides, diesel, water) and preventing crop lodging.
- **For Government**: Provides district disaster officers and Krishi Vigyan Kendras (KVKs) with audit-trailed, Panchayat-level situational awareness.
- **National Scalability**: Architecture scales horizontally across 250,000+ Gram Panchayats and readily assimilates state mesonets (KSNDMC, Mahavedh).

### 3. Engineering Challenges & Mitigations

| Identified Challenge | Practical Mitigation Implemented |
|---|---|
| **Limited Radar Coverage in Rural Belts** | Satellite-first architecture leveraging INSAT-3DR TIR; radar assimilated opportunistically where available. |
| **Missing or Stale Upstream Feeds** | Strict **fail-closed** policy: stale feeds (>45 min) trigger visible `FALLBACK_COARSE` mode with user disclaimers. |
| **Panchayat Boundary Edge Ambiguity** | Exact R-tree point-in-polygon; points within 50m of borders return `ON_BOUNDARY` rather than guessing. |
| **Sensor Resolution Coarseness (~3.8 km)** | Fractional polygon area weighting preserves native sensor uncertainty; system explicitly flags source resolution. |

---

## 📊 Scientific Readiness & Empirical Validation

- **Readiness Classification**: Certified **`LIMITED_VALIDATION`** under Task 9 Forensic Audit.
- **Pilot Domain**: Varanasi District, Uttar Pradesh (Arajiline Block, Rameshwar & Jansa Panchayats).
- **Benchmark Dataset**: 12 curated convective rainfall events ($N=24$ station-event pairs) validated against independent ground-truth AWS (ICAR-IIVR and BHU Agronomy).

```
+-----------------------------------------------------------------------------------+
|                        PILOT BENCHMARK VERIFICATION RESULTS                       |
+------------------------------+--------------------+-------------------------------+
| Metric                       | Coarse NWP (IMD)   | AgroMet Nowcast (Team Braket) |
+------------------------------+--------------------+-------------------------------+
| Critical Success Index (CSI) | 0.417              | 0.933 (▲ +123.7%)             |
| Probability of Detection     | 0.500              | 0.950 (▲ +90.0%)              |
| False Alarm Ratio (FAR)      | 0.285              | 0.021 (▼ -92.6%)              |
| Precipitation Amount MAE     | 4.620 mm           | 0.879 mm (▼ -80.9%)           |
| Directional Spatial Concord  | 50.0% (Random)     | 100.0% (12/12)                |
+------------------------------+--------------------+-------------------------------+
```

---

## 🔗 Slide 6: Research & Reference Content Links

As presented on **Slide 6** of our official [SIH Presentation](SIH2026-IDEA-Presentation-Format.pptx_20260929_133126_0000.pdf), all research foundations, external datasets, benchmark methodologies, and forward roadmaps are documented with active hyperlinks:

| Presentation Category | Description & Research Coverage | Direct Content Link |
|---|---|:---:|
| **01. Datasets** | IMD-GFS, INSAT-3DR TIR (MOSDAC), LGD Panchayats, NOAA ISD, NASA SRTM 30m, ESA WorldCover, SoilGrids. | [**Access Datasets**](docs/RESEARCH_AND_REFERENCES.md#1-datasets--data-sources) |
| **02. Existing Methods** | Coarse NWP baselines, Bilinear/IDW interpolation limitations, satellite estimation (HEM/IMSRA), IMD-GKMS guidelines. | [**Review Methods**](docs/RESEARCH_AND_REFERENCES.md#2-baseline--existing-methods) |
| **03. Research Gaps** | Sub-block variability, boundary ambiguity, rural radar blindspots, data freshness, and explainability. | [**Inspect Gaps**](docs/RESEARCH_AND_REFERENCES.md#3-research-challenges--gaps) |
| **04. Experimental Results** | Varanasi pilot benchmarks, CSI (0.933), POD (0.950), MAE (0.879mm), and Rameshwar vs. Jansa validation. | [**View Results**](docs/RESEARCH_AND_REFERENCES.md#4-experimental-results--validation) |
| **05. Future Scope** | National Mesonet ingestion (KSNDMC/Mahavedh), Doppler radar mosaics, deep learning PINOs, and WhatsApp delivery. | [**Explore Scope**](docs/RESEARCH_AND_REFERENCES.md#5-future-scope--scalability) |

> 💡 *Note: The presentation PDF [`SIH2026-IDEA-Presentation-Format.pptx_20260929_133126_0000.pdf`](SIH2026-IDEA-Presentation-Format.pptx_20260929_133126_0000.pdf) has interactive hyperlinks embedded directly on Slide 6 and Slide 1.*

---

## 💻 System Architecture & Client Ecosystem

The AgroMet repository provides a unified multi-tier ecosystem:

```
                            FastAPI Backend (backend/)
                         Unified Scientific & API Service
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 │                                             │
                 ▼                                             ▼
          web/ (frontend/)                                  mobile/
     React 18 / Vite / Tailwind                       Flutter 3.47+ / Dart
                 │                                             │
      Government & Technical Portal                 Farmer & Field-Official App
     (GIS Grid, Panchayat Analytics,               (Action/Why/Timing Advisories,
       Provenance, Judge Mode)                      Vernacular Cards, GPS Routing)
```

- **`backend/`** → FastAPI scientific downscaling, spatial masking, and nowcasting engine.
- **`frontend/`** (or **`web/`**) → Comprehensive command dashboard with 8 verified views (Explorer, Detail, GIS Map, Weather Analysis, Advisory Hub, Governance, Judge Mode).
- **`mobile/`** → Cross-platform mobile client for farmers and agricultural extension officers.
- **`docs/`** → Scientific defense briefs, forensic audit manifests, and technical whitepapers.

---

## 🚀 Quickstart & Run Commands

### Prerequisites
- Python 3.10+ / 3.11+
- Node.js 18+ & npm
- Flutter 3.47+ (Optional for mobile client)

### 1. Backend Service (FastAPI)
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start backend server on port 8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI Specification: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### 2. Web Portal (React 18 + Vite)
```bash
# Navigate to web frontend directory
cd frontend

# Install dependencies
npm install

# Start development server on port 5173
npm run dev -- --host 0.0.0.0 --port 5173
```
- Web Application: [http://localhost:5173](http://localhost:5173)
- SIH Judge Evaluation Mode: [http://localhost:5173/judge](http://localhost:5173/judge)

### 3. Mobile Application (Flutter)
```bash
# Navigate to mobile directory
cd mobile

# Fetch Flutter packages
flutter pub get

# Launch in Chrome browser
flutter run -d chrome

# Or build static web release
flutter build web
```

### 4. Canonical Demo & Forensic Validation Scripts
```bash
cd backend

# 1. Seed canonical SIH demo scenario (2026-07-15)
python scripts/seed_demo_scenario.py --date 2026-07-15

# 2. Programmatically validate all 10 end-to-end pipeline links
python scripts/validate_demo_scenario.py --date 2026-07-15

# 3. Reset demo database safely
python scripts/reset_demo_scenario.py --force
```

---

## 🧪 Testing & Verification

The scientific pipeline is validated through an extensive automated regression test suite:

```bash
# Run scientific pipeline, GIS, nowcasting, and terrain tests (129 passing)
python -m pytest backend/tests/test_india_pipeline.py backend/tests/test_terrain_phase16.py backend/tests/test_generalization_phase17.py --noconftest -v

# Verify frontend production build (0 TypeScript or Vite errors)
cd frontend && npm run build
```

---

## 👥 Team Braket 3.1.0 (IIIT)

| Team Member | Role & Responsibilities |
|---|---|
| **Ishan Narayan Shukla** | Project Lead, Scientific Architecture & Systems Integration |
| **Priyanshi Saraswat** | Geospatial Pipeline, Spatial Masking & LGD Topology |
| **Prajjwal Patel** | Precipitation Nowcasting & ML Hurdle Models |
| **Pratyaksh Ranjan** | Full-Stack Web Architecture & GIS Visualization |
| **Rudransh Rajveer Singh** | Flutter Mobile Application & Farmer UX |

---

## 📜 License & Acknowledgments

- **Codebase**: Licensed under the [MIT License](LICENSE).
- **India Meteorological Department (IMD) & MoES**: Problem Statement SIH26074 guidance.
- **ISRO / SAC / MOSDAC**: INSAT-3DR meteorological satellite data products.
- **Ministry of Panchayati Raj (MoPR)**: Local Government Directory administrative boundaries.
- **Copernicus & ECMWF**: ERA5 reanalysis and atmospheric datasets.
- **NASA / USGS**: Shuttle Radar Topography Mission (SRTM) digital elevation models.

<div align="center">
  <sub>Developed with pride for <b>Smart India Hackathon 2026</b> by <b>Team Braket 3.1.0</b></sub>
</div>
