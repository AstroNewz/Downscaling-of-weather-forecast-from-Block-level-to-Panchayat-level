# GraminKrishi-Mausam-Intelligence Backend

> **SIH Problem Statement 26074**: *Downscaling of weather forecast from Block level to Panchayat level: Inferring high-resolution plots/data/information from low-resolution plot/data/information/variables for agro-meteorological advisory services.*

---

## 🌾 Core Objective & Pipeline

This platform is an **Agro-Meteorological Advisory System** designed to bridge the gap between coarse numerical weather predictions (NWP at block level, ~12-25 km resolution) and actionable, high-resolution hyper-local advisories at the **Gram Panchayat level** (~1 km resolution).

```
Weather Forecast Data (Block level, NWP/IMD)
   │
   ▼
Data Ingestion & Quality Validation
   │
   ▼
Weather Preprocessing & Topographic Correction (Lapse rate, DEM slope/aspect, LULC)
   │
   ▼
AI/ML Weather Downscaling (XGBoost Regressor / Residual Formulation)
   │
   ▼
High-Resolution Weather Grid (1 km x 1 km)
   │
   ▼
Panchayat GIS Mapping (Area-Weighted Spatial Intersection & Zonal Aggregation)
   │
   ▼
Panchayat-Level Downscaled Weather
   │
   ▼
Cropland / Land-Use Mask (Strict filter: Urban / Forest / Water / Barren excluded)
   │
   ▼
Agricultural Context (Crop Type + Phenological Stage + Soil Texture & Moisture)
   │
   ▼
Agricultural Risk Detection Engine (Pest/Disease, Water Stress, Frost/Heat Shock)
   │
   ▼
Agro-Meteorological Advisory Generation (Tailored for Farmers & Agronomists)
   │
   ▼
REST API (FastAPI) ───► Web/Mobile Frontend (Farmers & Extension Officers)
```

---

## 🛠️ Technology Stack

* **Core Framework**: Python 3.11+, FastAPI, Uvicorn
* **Data Schemas & Settings**: Pydantic v2, Pydantic-Settings
* **Database & ORM**: PostgreSQL 16 + PostGIS, SQLAlchemy 2.x, GeoAlchemy2, Alembic
* **GIS & Spatial Intelligence**: GeoPandas, Shapely, Rasterio, PyProj
* **Scientific Computing & ML**: NumPy, Pandas, Scikit-learn, XGBoost, PyArrow
* **HTTP & Utilities**: HTTPX, python-dotenv, Rich
* **Testing**: Pytest, Pytest-Asyncio
* **Containerization**: Docker, Docker Compose

---

## 📁 Directory Architecture

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan, CORS, middleware
│   ├── core/
│   │   ├── config.py            # Pydantic v2 12-factor application settings
│   │   ├── logging.py           # Structured application logging
│   │   └── exceptions.py        # Centralized domain exception handlers
│   │
│   ├── api/
│   │   ├── router.py            # Central v1 route aggregator
│   │   └── v1/
│   │       ├── health.py        # Liveness & readiness health check probes
│   │       ├── weather.py       # Weather ingestion & downscaling endpoints
│   │       ├── panchayat.py     # Panchayat GIS, land-use & spatial weather aggregation
│   │       ├── agriculture.py   # Crop calendars, stages & soil endpoints
│   │       ├── advisory.py      # Agro-meteorological advisory endpoints
│   │       └── ml.py            # Model registry, inference & 1-km spatial grid endpoints
│   │
│   ├── db/
│   │   ├── session.py           # SQLAlchemy engine & session dependency
│   │   ├── base.py              # Declarative base class
│   │   └── models/              # PostGIS ORM entity definitions
│   │
│   ├── schemas/
│   │   ├── common.py            # Standard response envelopes & pagination
│   │   ├── health.py            # Health probe schemas
│   │   ├── weather.py           # Weather forecast & downscaling schemas
│   │   ├── panchayat.py         # Panchayat & land-use composition schemas
│   │   ├── panchayat_weather.py # Area-weighted Panchayat weather statistics & aggregation schemas
│   │   ├── agriculture.py       # Crop context, phenology & soil schemas
│   │   ├── advisory.py          # Risk detection & advisory action schemas
│   │   ├── ml.py                # ML model registry & inference schemas
│   │   └── spatial_grid.py      # 1-km spatial grid & quality diagnostic schemas
│   │
│   ├── gis/                     # Spatial boundary, grid & DEM/LULC engine
│   │   ├── grid.py              # 1-km metric grid generator in local projected UTM CRS
│   │   ├── dem.py               # Topographic slope, aspect, TRI, lapse rate
│   │   ├── landuse.py           # Land-use / land-cover fraction extraction
│   │   ├── raster.py            # GeoTIFF raster sampling with CRS transforms
│   │   └── feature_service.py   # Integrated GIS environmental feature pipeline
│   │
│   ├── ml/                      # Machine learning downscaling subsystem
│   │   ├── models/              # Abstract BaseDownscalingModel & XGBoost Regressor
│   │   ├── feature_manifest.py  # 35-predictor manifest & data leakage quarantine
│   │   ├── trainer.py           # Training orchestrator with early stopping
│   │   ├── evaluator.py         # Baseline comparison (MAE, RMSE, MBE, R², % gain)
│   │   ├── registry.py          # Local model registry (artifacts, metadata, metrics)
│   │   ├── predictor.py         # Low-latency point & batch inference service
│   │   ├── builder.py           # Temporal/spatial matching & Parquet builder
│   │   ├── features.py          # Cyclical time & environmental feature engineer
│   │   ├── splitting.py         # Chronological train/val/test splitting
│   │   └── baseline.py          # Naive coarse baseline evaluator
│   │
│   ├── services/
│   │   ├── spatial_inference.py     # 1-km Spatial Temperature Downscaling Service
│   │   └── panchayat_aggregation.py # Area-Weighted Panchayat Weather Aggregation Service
│   │
│   └── utils/                   # DateTime and spatial validation helpers
│
├── data/                        # Geospatial & weather data stores
│   ├── raw/                     # Raw NWP GRIB2/NetCDF, DEM & shapefiles
│   ├── processed/               # Interpolated weather rasters, Parquet & GeoParquet grids
│   │   └── grids/               # Exported 1-km spatial fields (*.parquet, *.geojson)
│   └── sample/                  # Mock/Sample test payloads
│
├── models/                      # Trained ML downscaling registry
│   └── temperature_residual/    # Versioned artifacts (model.json, metadata.json)
│
├── tests/                       # Automated unit and integration tests (60+ tests)
├── scripts/                     # CLI data ingestion, training, grid & aggregation tools
├── alembic/                     # Database migrations
├── .env.example                 # Environment variables specification
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image with GDAL/GEOS/PROJ
├── docker-compose.yml           # Local PostgreSQL/PostGIS & backend orchestration
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Create Python Virtual Environment

```bash
# Windows (PowerShell)
cd backend
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### 4. Start the FastAPI Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Interactive API Documentation

Once the server is running, open:

* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI JSON Spec**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🧪 Running Automated Tests

Run the full automated test suite (60+ unit and integration tests):

```bash
pytest -v
```

---

## 🏛️ Area-Weighted Panchayat Weather Aggregation (Phase 8)

```
BLOCK FORECAST
      │
      ▼
PHASE 6 XGBOOST
      │
      ▼
PHASE 7 1-km TEMPERATURE GRID
      │
      ▼
PANCHAYAT BOUNDARIES
      │
      ▼
SPATIAL INTERSECTION (Projected Metric CRS)
      │
      ▼
PANCHAYAT WEATHER STATISTICS (Area-Weighted Mean, Min, Max, StdDev)
      │
      ▼
PHASE 9 AGRICULTURAL CONTEXT
```

### 🔬 Aggregation & Quality Methodology:
* **Area-Weighted Formulation**:
  $$w_i = \frac{\text{Intersection Area}_i}{\text{Panchayat Area}}$$
  $$T_{\text{mean},P} = \frac{\sum_{i \in \text{Valid}} w_i \times T_i}{\sum_{i \in \text{Valid}} w_i}$$
* **Metric Area Calculations**: Polygons are projected into local projected metric coordinate systems (e.g. UTM `EPSG:32643`, a projected metric CRS suitable for local distance/area calculations) before computing intersection geometry areas in square meters.
* **Coverage Diagnostics**:
  - `COMPLETE`: Coverage $\ge 95\%$
  - `PARTIAL`: Coverage $> 0\%$ and $< 95\%$
  - `UNAVAILABLE`: Coverage $= 0\%$ (no valid cells)
* **Preservation of Micro-Climatic Extremes**: In addition to area-weighted mean, the engine calculates and preserves $T_{\min}$, $T_{\max}$, $T_{\text{median}}$, $T_{p10}$, $T_{p90}$, and spatial standard deviation $\sigma_T$ for agricultural risk analysis.
* **Idempotent Persistence**: Stores records in `panchayat_weather_records` table with unique constraint on `(panchayat_id, forecast_date, issue_time, source_model, model_version)`.

---

## 🌾 Panchayat Agricultural Context (Phase 9)

```
PANCHAYAT WEATHER (Phase 8)
            +
AGRICULTURAL ELIGIBILITY (LandUseMask)
            +
CROP MAPPING (PanchayatCropMapping)
            +
CROP PHENOLOGY STAGE (CropPhenologyStage)
            +
SOIL PROFILE (SoilProfile)
            ↓
PANCHAYAT AGRICULTURAL CONTEXT (PanchayatCropContext)
            ↓
PHASE 10: AGRICULTURAL RISK ENGINE
```

### 🔬 Scientific Methodology & Domain Isolation:
1. **Weather Domain vs Agricultural Domain**: Panchayat weather covers the geographic domain; crop and soil contexts apply exclusively to agricultural cropland verified via `LandUseMask.is_agricultural_eligible`.
2. **Crop Mapping Integrity**: Multi-crop Panchayats (e.g. Rice + Maize + Vegetables) produce distinct context snapshots per crop. Inactive mappings are excluded, and crops are never fabricated (`status = UNAVAILABLE` when unmapped).
3. **Deterministic Phenology Stage Resolution**:
   - **Priority 1**: Explicit observed stage in `PanchayatCropMapping.current_stage`.
   - **Priority 2**: Planting-date calculation (`days_since_planting = context_date - sowing_date`) evaluated against sequential crop stage day thresholds.
   - **Priority 3**: Seasonal crop calendar defaults (`Kharif` / `Rabi` month ranges).
   - **Fallback**: `UNKNOWN` / `UNAVAILABLE`. Crop stage is never inferred from ambient weather temperature.
4. **Soil Context & NULL Preservation**: Evaluates soil physical and hydrological properties (`soil_type`, `texture`, `drainage_class`, `water_holding_capacity_pct`, `ph_level`, `organic_carbon_pct`, N/P/K). Partial profiles are marked `PARTIAL`; missing numeric data strictly remains `None`/`NULL` and is never substituted with `0.0`.

---

## ⚠️ Agricultural Risk Engine (Phase 10)

```
PANCHAYAT WEATHER (Phase 8)
            +
PANCHAYAT AGRICULTURAL CONTEXT (Phase 9)
            ↓
DATA QUALITY GATES (Missing Input & Cropland Verification)
            ↓
VERSIONED RISK RULE REGISTRY (ICAR/IMD Standards, rule_version = "agri_risk_v1.0.0")
            ↓
MODULAR RISK EVALUATORS (Thermal, Cold, Hydrological, Wind, Pathological Environment)
            ↓
SEVERITY (NONE/LOW/MODERATE/HIGH/EXTREME) + CONFIDENCE + EXPLAINABLE EVIDENCE
            ↓
AGRICULTURAL RISK LOG (Database Persistence & Traceability)
            ↓
PHASE 11: AGRO-METEOROLOGICAL ADVISORY ENGINE [Upcoming]
```

### 🔬 Risk Evaluation Categories & Scope Boundaries:
1. **Thermal / Heat Stress (`HEAT_STRESS`)**: Evaluates crop/stage-specific maximum temperature thresholds (e.g., Rice flowering sterility $\ge 35^\circ\text{C}$, Maize silking $\ge 35^\circ\text{C}$, Wheat heading/grain fill $\ge 28^\circ\text{C}$).
2. **Cold / Chilling / Frost Stress (`COLD_STRESS`)**: Evaluates minimum temperature thresholds (e.g., Wheat heading frost injury $\le 2^\circ\text{C}$, Rice chilling $\le 15^\circ\text{C}$).
3. **Pathogen Environmental Window (`DISEASE_FAVORABLE_CONDITIONS`)**: Evaluates micro-climatic suitability for fungal/bacterial foliar proliferation (temp window $22\text{--}32^\circ\text{C}$). **Strict scope:** Indicates environmental favorability only, NOT confirmed disease presence.
4. **Hydrological Stress (`WATER_STRESS`, `EXCESS_RAIN`)**: Evaluates soil available water capacity and heavy forecast rainfall (>50 mm/day). Explicitly requires multi-day precipitation accumulation; single-day absence yields `INSUFFICIENT_DATA`.
5. **Wind Stress (`WIND_STRESS`)**: Evaluates mechanical lodging risk from convective gusts (>35 km/h).
6. **Data Quality & NULL Preservation**: Missing inputs trigger explicit `INSUFFICIENT_DATA` (never assumed as `NOT_DETECTED` or replaced with `0.0`).
7. **Strict Scope Preservation**:
   - No new weather ML retraining.
   - No rainfall downscaling.
   - No disease diagnosis or pesticide recommendations.
   - No farmer advisory generation (deferred to Phase 11+).

### 💻 Agricultural Risk Evaluation via CLI:
```bash
# Evaluate agricultural risks for all Panchayats in a Block (Dry-Run)
python scripts/evaluate_agricultural_risk.py --block-id 1 --date 2026-07-15 --dry-run

# Evaluate thermal risk for a single Panchayat with database persistence
python scripts/evaluate_agricultural_risk.py --panchayat-id 1 --date 2026-07-15 --risk-type HEAT_STRESS
```

### 📡 Phase 10 Agricultural Risk Endpoints:
* `POST /api/v1/agriculture/risk/evaluate` — Trigger agricultural risk evaluation across Block or Panchayat
* `GET /api/v1/agriculture/risk` — Query logged risk evaluations with spatial, temporal, risk type, and severity filtering
* `GET /api/v1/agriculture/panchayat/{panchayat_id}/risk` — Retrieve multi-crop risk assessment grouped by crop for a specific Panchayat
* `GET /api/v1/agriculture/risk/status` — Subsystem risk analytics (counts by risk type, severity, detected vs not detected)

---

## 📢 Agro-Meteorological Advisory Generation Engine (Phase 11)

```
PANCHAYAT WEATHER (Phase 8)
            +
AGRICULTURAL CONTEXT (Phase 9: Crop + Stage + Soil + LandUseMask)
            +
DETECTED AGRICULTURAL RISK (Phase 10 Source of Truth)
            ↓
ADVISORY RULE REGISTRY (ICAR/IMD Agromet Guidelines, advisory_rule_version = "agri_advisory_v1.0.0")
            ↓
STRUCTURED ACTION MODEL (Water Management, Field Ops, Crop Protection, Disease Monitoring)
            ↓
PRIORITY & RANKING (Critical > High > Medium > Low > Informational)
            ↓
CONFLICT RESOLUTION (Opposing Operations -> EXPERT_REVIEW_REQUIRED)
            ↓
EVIDENCE & PROVENANCE TRACEABILITY
            ↓
AGRO-ADVISORY PERSISTENCE (AgroAdvisory Table & Idempotency)
            ↓
REST API + CLI + DASHBOARD-READY JSON
```

### 🔬 Agronomic Guardrails & Safety Policy:
1. **Advisory $\neq$ Risk**: Phase 10 identifies hazards (e.g. `HEAT_STRESS`, `HIGH`); Phase 11 generates actionable, prioritized, crop-stage-specific advisories with structured timing and operational urgency.
2. **Phase 10 is Source of Truth**: The advisory engine **NEVER** creates or invents a risk. Only `DETECTED` risks generate action advisories. `NOT_DETECTED` produces no hazard advisories; `INSUFFICIENT_DATA` or unconfigured rules produce explicit informational uncertainty without fake prescriptions.
3. **No Disease Diagnosis & No Chemical Prescriptions**: Disease-related advisories strictly state: *"Environmental conditions are favorable for increased disease risk. Inspect the crop and follow locally approved crop-protection guidance."* Never diagnoses disease presence or prescribes chemical pesticides or dosages.
4. **Action vs Informational**: Distinguishes `ACTION_ADVISORY` (validated management actions configured) from `INFORMATIONAL` (guidance explaining situation when no action rule is configured).
5. **Multi-Risk Prioritization**: Ranks multiple risks for the same crop (`priority_rank` 1, 2, 3...) based on hazard severity and stage sensitivity.
6. **Operational Conflict Detection**: Conflicting agronomic recommendations (e.g. irrigate for heat vs withhold irrigation for wind lodging) automatically set `is_expert_review_required = True` and status `EXPERT_REVIEW_REQUIRED`.
7. **Complete Provenance**: Every advisory records `panchayat_weather_id`, `risk_log_id`, `crop_context_id`, `rule_version`, `advisory_rule_version` (`agri_advisory_v1.0.0`), and forecast validity window.

### 💻 Advisory Generation via CLI:
```bash
# Generate advisories for all Panchayats in a Block (Dry-Run)
python scripts/generate_agro_advisories.py --block-id 1 --date 2026-07-15 --dry-run

# Generate advisories for a single Panchayat with database persistence
python scripts/generate_agro_advisories.py --panchayat-id 1 --date 2026-07-15
```

### 📡 Phase 11 Advisory Endpoints:
* `POST /api/v1/advisory/generate` — Generate and persist advisories for Block or individual Panchayat
* `GET /api/v1/advisory` — Query logged advisories with spatial, crop, type, priority, and validity filters
* `GET /api/v1/advisory/panchayat/{panchayat_id}` — Retrieve active advisories grouped by crop for a specific Panchayat
* `GET /api/v1/advisory/{advisory_id}` — Inspect detailed advisory with structured action, rationale, evidence, and provenance
* `GET /api/v1/advisory/status` — Subsystem analytics (counts by status, priority, type, crop, and active rule version)

---

## 🗺️ Incremental Implementation Roadmap

* **Phase 1 (Completed)**: Foundational project structure, configuration, centralized exceptions, unified schemas, and health checks.
* **Phase 2 (Completed)**: PostGIS spatial database schema (Panchayats, Blocks, Land-Use masks, Weather grids, Crops, Soils, Advisories) and Alembic migrations.
* **Phase 3 (Completed)**: Provider-independent weather data ingestion, validation, normalization, and quality control pipeline.
* **Phase 4 (Completed)**: Preprocessing, temporal/spatial alignment, leakage prevention, residual target formulation, cyclical feature engineering, and Parquet dataset generation.
* **Phase 5 (Completed)**: GIS, DEM & Environmental feature engineering (Topographic slope, aspect, TRI, lapse rate, and LULC fractions).
* **Phase 6 (Completed)**: Machine Learning Temperature Downscaling: XGBoost training, early stopping, baseline evaluation (MAE, RMSE, MBE, R²), local model registry, and real-time point/batch inference engine.
* **Phase 7 (Completed)**: 1-km Spatial Weather Downscaling & Inference Engine: Projected metric UTM grid generation, DEM/LULC environmental sampling, batch XGBoost residual downscaling, spatial diagnostics, PostGIS persistence, and GeoParquet export.
* **Phase 8 (Completed)**: Panchayat-Level Weather Aggregation from 1-km Downscaled Grid: Area-weighted spatial intersection, temperature statistics (mean, min, max, std dev), coverage classification, and idempotent persistence.
* **Phase 9 (Completed)**: Panchayat Agricultural Context Engine: Crop Mapping, Crop Phenology Stage Resolution, Soil Hydrological Profiles, Cropland Eligibility Masking, Multi-Crop Context Snapshots, REST APIs, and CLI tools.
* **Phase 10 (Completed)**: Agricultural Risk Engine: Crop-aware and stage-aware threshold rules (`agri_risk_v1.0.0`), modular evaluators (thermal, cold, hydrological, wind, disease-favorable environment), explainable evidence, confidence scoring, REST APIs, and CLI tools.
* **Phase 11 (Completed)**: Agro-Meteorological Advisory Generation Engine: Versioned advisory rules (`agri_advisory_v1.0.0`), structured actions, transparent priority & ranking, conflict detection, safety guardrails (no disease diagnosis, no chemical doses), REST APIs, CLI, and dashboard-ready JSON.
* **Phase 12 (Completed)**: Panchayat Agro-Meteorological Dashboard & Delivery Layer: Production-oriented React 18 + TypeScript + Vite web dashboard with glassmorphism UI, interactive 1-km spatial GIS map, 1-km grid cell inspector, resolution comparison analytics, role-tailored views (Farmer, Extension Officer, Admin), and unified backend delivery endpoints.
* **Phase 13 (Completed)**: SIH Demonstration, Evaluation & Presentation Readiness: Deterministic canonical demonstration seeder (`seed_demo_scenario.py`), 10-link pipeline validator (`validate_demo_scenario.py`), safe demo resetter (`reset_demo_scenario.py`), interactive SIH Judge Mode (`/judge`), 5-minute presentation script (`docs/SIH_DEMO_SCRIPT.md`), and comprehensive technical documentation (`docs/SIH_TECHNICAL_OVERVIEW.md`).

---

## 🏆 SIH Demonstration & Evaluation Package (Phase 13)

Phase 13 packages the end-to-end platform into an interactive, reproducible, judge-ready demonstration workflow:

```bash
# 1. Seed the canonical demonstration scenario
python scripts/seed_demo_scenario.py --date 2026-07-15

# 2. Validate all 10 links in the demonstration pipeline
python scripts/validate_demo_scenario.py --date 2026-07-15

# 3. Safely wipe only synthetic demo records when finished
python scripts/reset_demo_scenario.py --force
```

### 🌟 Key SIH Demonstration Assets:
- **⭐ SIH Judge Walkthrough Mode (`/judge`)**: A guided 60-second interactive pipeline walkthrough showcasing block vs 1-km downscaling, multi-crop separation (Rice at Flowering vs Maize at Tasseling), direction-aware risk detection, and explainable farming actions.
- **📄 [5-Minute Presentation Script](file:///c:/Users/Priyanshi/OneDrive/Pictures/Desktop/SIH%20pt%202/docs/SIH_DEMO_SCRIPT.md)**: Timed presentation sequence covering problem definition, ML physics residual downscaling, GIS aggregation, phenology sensitivity, risk scoring, advisory guardrails, and pilot roadmap.
- **📑 [Comprehensive Technical Overview](file:///c:/Users/Priyanshi/OneDrive/Pictures/Desktop/SIH%20pt%202/docs/SIH_TECHNICAL_OVERVIEW.md)**: Complete engineering architecture, mathematical formulas, calibration benchmarks, API specifications, and limitations.

---

## 🖥️ Panchayat Agro-Meteorological Dashboard & Delivery Layer (Phase 12)


Phase 12 delivers the unified interactive frontend and delivery API layer connecting the complete 12-phase pipeline for all agricultural stakeholders:

```
BLOCK FORECAST (Phase 3)
      ↓
PHASE 6 XGBoost Residual Model
      ↓
PHASE 7 1-km Spatial Weather Grid
      ↓
PHASE 8 Panchayat Weather Aggregation
      ↓
PHASE 9 Agricultural Context (Crop + Stage + Soil + Eligibility)
      ↓
PHASE 10 Agricultural Risk Engine (Detected Risks)
      ↓
PHASE 11 Agro-Meteorological Advisory Engine (Explainable Guidance)
      ↓
PHASE 12 Panchayat / Farmer / Extension Officer / Admin Web Dashboard & GIS Delivery Layer
```

### 🌟 Dashboard Features & Capabilities:
1. **Multi-Role Experience**:
   - **Farmer View**: Plain-language localized weather, crop-specific hazards, high-priority actions, optimal operational windows, and clear dosage/chemical safety guardrails.
   - **Agricultural Extension Officer View**: Panchayat directory, multi-crop situations, risk rankings, operational conflict warnings (`EXPERT_REVIEW_REQUIRED`), and full evidence traceability.
   - **Administrator / Scientist View**: ML Model Registry status (`v1.0.0`), benchmark accuracy metrics (MAE $0.38^\circ$C, $R^2 = 0.94$), Gini feature importances, and active rule versions (`agri_risk_v1.0.0`, `agri_advisory_v1.0.0`).
2. **Interactive 1-km GIS Map Explorer**:
   - Leaflet/Vector canvas hybrid with 1-km thermal grid cell overlay, risk heatmaps, administrative boundary markers, and zoom/pan controls.
   - **1-km Grid Cell Inspector**: Click any cell to view predicted ML residual delta ($\Delta T$), downscaled temperature, SRTM elevation, slope, aspect, and Sentinel-2 cropland fraction.
3. **Downscaling & Weather Analytics**:
   - Diurnal temperature profile comparing coarse block forecast against 1-km downscaled temperatures.
   - Clear scientific transparency: *Temperature is 1-km XGBoost downscaled; Rainfall is coarse Block NWP forecast*.
   - Interactive What-If Residual Simulator.
4. **Agro-Advisory Hub**:
   - Centralized, searchable, and filterable catalog with category, priority, and crop filters.
   - Deep scientific rationale, specific operational steps, and model provenance.
5. **Offline-Resilient API Client**:
   - Seamlessly queries FastAPI backend endpoints with transparent offline mock data fallbacks for standalone demonstration.

### 📡 Phase 12 Delivery Endpoints:
* `GET /api/v1/panchayat/blocks` — List blocks with child panchayat counts and district metadata
* `GET /api/v1/panchayat/geojson` — Return GeoJSON FeatureCollection with downscaled weather and risk properties
* `GET /api/v1/panchayat/{id}/detail` — Unified 1-call payload (metadata, land-use, latest weather, crop contexts, detected risks, active advisories)
* `GET /api/v1/ml/grid/cells` — Return 1-km spatial grid cells with residual predictions, temperatures, and DEM terrain parameters

### 🚀 Running the Dashboard:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev

# Build production bundle
npm run build
```




