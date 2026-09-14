# SIH-26074-AgroWeather-Downscaling

[![SIH Problem Statement](https://img.shields.io/badge/SIH%202024-Problem%2026074-blue.svg)](https://www.sih.gov.in/)
[![Repository Status](https://img.shields.io/badge/Status-SIH%20Evaluation%20Ready-success.svg)](#18-repository-status)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-87%20Passed-brightgreen.svg)](#15-testing)
[![Frontend Build](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-blue.svg)](#13-frontend-run)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Smart India Hackathon Problem Statement 26074

> **Problem Statement**:  
> *“Downscaling of weather forecast from Block level to Panchayat level for agro-meteorological advisory services.”*

---

## 1. Problem

Current operational Numerical Weather Prediction (NWP) models provided by national meteorological agencies (such as IMD and NCMRWF) issue forecast data at the **Block level** (~15 km to 25 km spatial resolution). 

However, critical agricultural vulnerabilities and daily farming interventions happen at the **Gram Panchayat field scale** (~1 km). A coarse block-level forecast averages out micro-topographic variations, valley cold air drainage, slope solar radiation differentials, and vegetation heat sink buffers. 

For example, when a coarse forecast predicts 36.0°C across an entire 20-km block, an exposed upland or dry cropland cell within that block might experience 37.8°C—crossing the critical 35.0°C physiological threshold that causes irreversible spikelet sterility during paddy flowering. Conversely, coarse forecasts fail to alert farmers to localized frost pooling or high convective wind gusts.

---

## 2. Solution

> **“We take Block-level weather forecasts, spatially downscale temperature to a 1-km grid, aggregate it at Panchayat level, combine it with crop/stage/soil context, detect agricultural risks, and deliver explainable localized agro-meteorological advisories.”**

Our system provides an end-to-end agro-meteorological intelligence pipeline that turns coarse numerical weather guidance into hyper-local, crop-stage-aware, and actionable farming decisions.

---

## 3. AI / ML Approach

The system **does not generate weather forecasts from scratch**. Instead, it uses a physics-informed statistical downscaling framework:

1. **Coarse NWP Forecast Baseline**: Ingests operational Block-level forecast inputs ($T_{\text{coarse}}$).
2. **Residual Anomaly Learning ($\hat{R}$)**: An **XGBoost Regressor** is trained to predict the high-resolution temperature residual:
   $$\hat{R}(x, y) = T_{\text{downscaled}}(x, y) - T_{\text{coarse}}$$
3. **High-Resolution Surface Predictors**: The model learns fine-scale thermal deviations using 35 engineered spatial, temporal, and biophysical features:
   - **Topography (SRTM 30m DEM)**: Elevation ($z$), slope ($\theta$), aspect ($\phi$), Terrain Ruggedness Index (TRI), and environmental lapse-rate adiabatic cooling.
   - **Land Use & Land Cover (Sentinel-2 LULC)**: Cropland fraction, vegetation canopy cover, urban heat island fraction, and water body latent heat buffers.
   - **Temporal & Solar Dynamics**: Day-of-year cyclical harmonics ($\sin / \cos$) and solar zenith angles.
4. **1-km High-Resolution Weather Field**: The reconstructed temperature field is generated across a continuous 1-km metric grid:
   $$T_{\text{downscaled}}(x, y) = T_{\text{coarse}} + \hat{R}(x, y)$$
5. **Panchayat Aggregation & Agronomic Integration**: The 1-km spatial grid is intersected with administrative Gram Panchayat boundaries using area-weighted aggregation, enriched with crop growth stages and soil hydrological context, evaluated against direction-aware hazard rules, and compiled into explainable advisory outputs.

```
+-----------------------------------------------------------------------------------+
| FORECAST INPUT (Block NWP)                                                        |
|   ├── Coarse Max / Min / Mean Temp, RH, Wind Speed, Rainfall                      |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 1-km DOWNSCALED TEMPERATURE FIELD                                                 |
|   ├── Topography (DEM elevation, slope, aspect) + Sentinel-2 LULC fractions       |
|   └── Physics-informed XGBoost Residual Model: T_downscaled = T_coarse + R(x,y)   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| PANCHAYAT SPATIAL AGGREGATION                                                     |
|   └── Area-weighted geometric intersection in projected metric CRS                |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| CROP / STAGE / SOIL CONTEXT                                                        |
|   ├── Sentinel-2 Cropland Eligibility Mask (excludes water/urban/forest)          |
|   ├── Multi-Crop Separation (Rice, Maize, Wheat evaluated independently)          |
|   ├── Phenology: Days After Sowing (DAS) & Growing Degree Days (GDD)              |
|   └── Soil Hydrology: Available Water Capacity (AWC mm/m), texture, pH            |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| AGRICULTURAL RISK ENGINE (Rule Registry: agri_risk_v1.0.0)                        |
|   ├── Direction-Aware Hazard Detection (Heat Stress, Chilling, Wind, Pathogen)    |
|   └── Uncertainty Safety: Missing inputs produce INSUFFICIENT_DATA                |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| EXPLAINABLE ADVISORY ENGINE (Rule Registry: agri_advisory_v1.0.0)                 |
|   ├── Structured operational action, timing window, and priority ranking          |
|   ├── Operational conflict resolution (EXPERT_REVIEW_REQUIRED)                    |
|   └── Guardrails: No disease diagnosis, no chemical pesticide prescriptions       |
+-----------------------------------------------------------------------------------+
```

---

## 4. End-to-End Pipeline

The operational flow strictly follows this conceptual chain:

```
BLOCK WEATHER FORECAST
        ↓
DOWNSCALED 1-km TEMPERATURE
(Physics-informed XGBoost residual correction using Block NWP + terrain + land-use + spatial/temporal features)
        ↓
PANCHAYAT WEATHER
(Area-weighted aggregation in projected metric CRS)
        ↓
CROP + STAGE + SOIL
(Sentinel-2 cropland mask + DAS/GDD phenology + soil AWC)
        ↓
AGRICULTURAL RISK
(Direction-aware crop-stage hazard evaluation)
        ↓
EXPLAINABLE ADVISORY
(Actionable guidance, operational timing windows, conflict checks)
        ↓
FARMER / EXTENSION OFFICER DASHBOARD
(Interactive GIS maps, resolution comparison, role-based views)
        ↓
SIH DEMO & EVALUATION
(Deterministic scenario, 10-step validator, Judge Mode)
```

---

## 5. Architecture & Technology Stack

| Layer | Technologies Used | Description |
| :--- | :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings | Asynchronous REST APIs, validation, dependency injection |
| **Spatial Database** | PostgreSQL 16 + PostGIS 3.4, SQLAlchemy 2.x, GeoAlchemy2, Alembic | Spatial geometries, land-use masks, weather rasters, migrations |
| **GIS & Geodata** | GeoPandas, Shapely 2.0+, Rasterio, PyProj | Dynamic metric UTM projection, grid generation, spatial intersection |
| **ML & Analytics** | XGBoost 2.0+, Scikit-learn 1.5+, NumPy, Pandas, PyArrow | Gradient-boosted residual regression, cross-validation, Parquet |
| **Frontend Web** | React 18, TypeScript, Vite, TailwindCSS / Glassmorphism | Responsive web dashboard, role views, state management |
| **Mapping & Viz** | Leaflet, Vector Canvas Layer, Lucide React Icons | Interactive 1-km thermal grid overlay, cell inspector, diurnal charts |
| **Infrastructure** | Docker, Docker Compose | Containerized local execution for PostGIS and FastAPI backend |

---

## 6. Major Components

1. **Weather Ingestion & Quality Control (Phase 3)**:
   - Ingests Block NWP forecasts with provider abstraction (IMD, NCMRWF, Open-Meteo, CSV).
   - Validates ranges, physical consistency, and spatial coordinates.
2. **ML Dataset Builder & Feature Engineering (Phases 4 & 5)**:
   - Constructs leakage-free spatial/temporal datasets in Apache Parquet.
   - Extracts 30m SRTM DEM elevation, slope, aspect, TRI, adiabatic lapse rates, and Sentinel-2 LULC fractions.
3. **XGBoost Residual Downscaling Engine (Phases 6 & 7)**:
   - Trained XGBoost model (`temperature_residual_v1.0.0`) predicting temperature residuals ($\Delta T$).
   - Generates 1-km spatial grid cells (1000m $\times$ 1000m) in projected metric UTM CRS.
4. **Panchayat Area-Weighted Aggregation (Phase 8)**:
   - Geometric intersection of 1-km cells with Panchayat administrative polygons.
   - Calculates area-weighted $T_{\text{mean}}, T_{\text{min}}, T_{\text{max}}, \sigma_T$, percentiles, and coverage diagnostics.
5. **Agricultural Context & Phenology Engine (Phase 9)**:
   - Enforces Sentinel-2 Cropland Mask (urban, forest, water bodies excluded).
   - Multi-crop separation (Rice, Maize, Wheat).
   - Resolves crop growth stages via Days After Sowing (DAS) and Growing Degree Days (GDD).
   - Integrates soil hydrological profiles (texture, pH, Available Water Capacity).
6. **Agricultural Risk Engine (Phase 10)**:
   - Versioned rule registry (`agri_risk_v1.0.0`) evaluating thermal, chilling, wind lodging, hydrological, and pathogen-favorable windows.
   - Direction-aware scoring with explicit uncertainty handling (`INSUFFICIENT_DATA`).
7. **Explainable Agro-Advisory Engine (Phase 11)**:
   - Versioned advisory rules (`agri_advisory_v1.0.0`) generating structured farming actions and optimal timing windows.
   - Automated operational conflict detection (`EXPERT_REVIEW_REQUIRED`).
   - Agronomic guardrails: No disease diagnosis, no chemical brand/dosage prescriptions.
8. **Interactive Dashboard & GIS Explorer (Phase 12)**:
   - Role-tailored views: Farmer, Extension Officer, Administrator/Scientist.
   - 1-km Grid Cell Inspector, resolution comparison, and diurnal temperature profiling.
9. **Deterministic SIH Demo & Evaluation Suite (Phase 13)**:
   - Canonical demo scenario for date `2026-07-15` (Ayodhya District).
   - Automated 10-link pipeline validation CLI.
   - Interactive SIH Judge Mode (`/judge`).

---

## 7. Scientific Transparency & Disclaimers

> [!IMPORTANT]
> ### Rigorous Scientific Standards & Boundaries:
> 1. **Calibration vs. Operational Ground-Truth**:
>    - Current benchmark metrics are based on synthetic/test calibration datasets for pipeline verification:
>      - **MAE $\approx$ 0.380 °C** (vs Baseline Coarse MAE: 2.34 °C; **72.6% error reduction**)
>      - **RMSE $\approx$ 0.520 °C**
>      - **R² $\approx$ 0.942**
>    - *“Operational validation against independent AWS/ground-station observations is still required.”*
> 2. **Rainfall Modeling**:
>    - **Rainfall is NOT downscaled.**
>    - Rainfall is preserved directly from the coarse Block NWP input because convective precipitation downscaling requires dense radar/satellite assimilation.
> 3. **Disease & Protection Scope**:
>    - **Disease-favorable conditions indicate environmental risk windows only, not biological disease diagnosis.**
>    - The system **does not provide pesticide dosage recommendations** or commercial chemical prescriptions.

---

## 8. CRS & GIS Methodology

- **Geographic Output Coordinate System**: WGS84 (`EPSG:4326`) for map rendering, GeoJSON APIs, and interoperability.
- **Metric Processing & Grid Projection**: Grid generation and spatial distance/area calculations dynamically select a locally appropriate projected UTM CRS (e.g., `EPSG:32643` / `EPSG:32644` for Northern India).
- **Grid Cell Geometry**: Cells are generated at approximately 1-km resolution using exact **1000 m $\times$ 1000 m** metric spacing in the local projected CRS.
- **Polygon Intersection**: Panchayat boundary intersection and area-weighted aggregation are executed in a **projected metric CRS suitable for local distance/area calculations** before re-projecting to WGS84. (Note: UTM is a conformal projected metric system, not an equal-area projection; area distortion is minimal across localized block bounds).

---

## 9. Deterministic SIH Demonstration

The platform includes a canonical, reproducible demonstration scenario:

- **Target Area**: Ayodhya District, Uttar Pradesh (Maya Bazar & Sohawal Blocks)
- **Canonical Demonstration Date**: `2026-07-15`
- **Agronomic Scenario**:
  - **Coarse Block Forecast**: 36.0°C maximum temperature, 28 km/h wind speed.
  - **1-km Downscaled Temperature**: Predicts a +1.8°C thermal anomaly ($\hat{R}$), reaching **37.8°C** in high-elevation/low-canopy cells.
  - **Crop 1 (Rice - Flowering Stage)**: 37.8°C exceeds the critical 35.0°C threshold $\rightarrow$ **HIGH Heat Stress Risk (Score 0.82)** $\rightarrow$ Action: Maintain 2–3 cm standing water during morning hours to buffer canopy microclimate.
  - **Crop 2 (Maize - Tasseling Stage)**: 28.0 km/h wind exceeds the 25.0 km/h root lodging threshold $\rightarrow$ **MODERATE Wind Risk (Score 0.55)** $\rightarrow$ Action: Withhold deep irrigation prior to wind event.

### Demonstration CLI Scripts:
- `backend/scripts/seed_demo_scenario.py` — Seeds blocks, panchayats, cropland masks, forecasts, grids, crops, risks, and advisories.
- `backend/scripts/validate_demo_scenario.py` — Programmatically validates all 10 pipeline links.
- `backend/scripts/reset_demo_scenario.py` — Safely cleans up demo records without dropping schemas.

---

## 10. System Prerequisites & Setup

### Prerequisites:
- **Python**: 3.11+ (tested on Python 3.11.x and 3.12.x)
- **Node.js**: 18.x+ or 20.x LTS
- **npm**: 9.x+ or 10.x+
- **PostgreSQL**: 15+ with **PostGIS 3.3+** extension (or Docker)
- **Docker & Docker Compose** (optional, for containerized database/backend)

---

## 11. Backend Setup & Run

### Step 1: Create & Activate Virtual Environment
```bash
cd backend

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

### Step 4: Start Database & Apply Migrations
```bash
# Option A: Start PostGIS with Docker (from repository root)
docker compose up -d postgis

# Option B: Using local PostgreSQL/PostGIS, ensure database 'agri_weather_db' exists

# Apply database migrations
cd backend
alembic upgrade head
```

### Step 5: Start FastAPI Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 12. Demonstration Commands

From the `backend/` directory:

```bash
# 1. Seed the canonical SIH demonstration scenario (2026-07-15)
python scripts/seed_demo_scenario.py --date 2026-07-15

# 2. Validate all 10 links in the demonstration pipeline
python scripts/validate_demo_scenario.py --date 2026-07-15

# 3. Safely reset demo records (when finished)
python scripts/reset_demo_scenario.py --force
```

---

## 13. Frontend Setup & Run

Open a separate terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

- **Main Dashboard**: [http://localhost:5173](http://localhost:5173)
- **SIH Judge Mode**: [http://localhost:5173/judge](http://localhost:5173/judge)

*(Note: Port 5173 is Vite's standard default development port configured in `vite.config.ts`.)*

---

## 14. Project Structure

```
SIH-26074-AgroWeather-Downscaling/
│
├── backend/
│   ├── alembic/                 # Database schema migrations (7 migration revisions)
│   ├── app/
│   │   ├── api/v1/              # REST endpoints (health, weather, panchayat, agriculture, advisory, ml)
│   │   ├── core/                # Application config, logging, centralized exceptions
│   │   ├── db/                  # SQLAlchemy sessions and PostGIS ORM models
│   │   ├── gis/                 # 1-km UTM grid generator, DEM sampling, LULC extraction
│   │   ├── ml/                  # XGBoost residual model, feature manifest, trainer, predictor, registry
│   │   ├── repositories/        # Data access layer
│   │   ├── schemas/             # Pydantic v2 validation schemas
│   │   ├── services/            # Spatial inference, Panchayat aggregation, risk engine, advisory engine
│   │   ├── utils/               # DateTime and validation helpers
│   │   ├── weather/             # Ingestion providers (IMD, NCMRWF, Open-Meteo, CSV) & QC validation
│   │   └── main.py              # FastAPI application factory, middleware, CORS
│   │
│   ├── data/
│   │   ├── raw/                 # Raw geodata storage (.gitkeep)
│   │   ├── processed/           # 1-km processed grids & GeoParquet (.gitkeep)
│   │   └── sample/              # Sample weather forecast datasets (*.csv)
│   │
│   ├── models/                  # Trained ML residual model registry (.gitkeep)
│   ├── scripts/                 # CLI pipelines (seed, validate, reset, train, evaluate, ingest)
│   ├── tests/                   # Automated unit & integration tests (19 test files, 87 tests)
│   ├── Dockerfile               # Production Docker container with GDAL/GEOS/PROJ
│   ├── requirements.txt         # Pinned Python dependencies
│   ├── alembic.ini              # Alembic migration configuration
│   └── .env.example             # Backend environment template
│
├── frontend/
│   ├── public/                  # Public static assets
│   ├── src/
│   │   ├── components/          # Common, layout, map, weather, advisory components
│   │   ├── context/             # React application context
│   │   ├── pages/               # Overview, GisMapPage, PanchayatExplorer, PanchayatDetail,
│   │   │                        # WeatherAnalysis, AdvisoryHub, SystemGovernance, JudgeMode
│   │   ├── services/            # API client with offline fallback mock data
│   │   ├── types/               # TypeScript data models
│   │   ├── App.tsx              # Router & layout
│   │   ├── index.css            # Glassmorphism styling tokens
│   │   └── main.tsx             # Entry point
│   ├── package.json             # Frontend dependencies & build scripts
│   ├── tsconfig.json            # TypeScript compiler configuration
│   └── vite.config.ts           # Vite dev server & proxy settings
│
├── docs/
│   ├── SIH_DEMO_SCRIPT.md       # 5-minute timed judge presentation sequence
│   ├── SIH_TECHNICAL_OVERVIEW.md# In-depth architectural & mathematical reference
│   ├── TEAM_SETUP.md            # Comprehensive developer onboarding guide
│   ├── GITHUB_SETUP.md          # GitHub repository initialization & push guide
│   └── RELEASE_NOTES_v1.0.0-sih-evaluation.md # Full evaluation release notes
│
├── .gitignore                   # Root gitignore (Python, Node, PostGIS, Secrets, OS)
├── .env.example                 # Root environment template
├── docker-compose.yml           # Multi-container orchestration (PostGIS + FastAPI backend)
├── CHANGELOG.md                 # Project version history
├── CONTRIBUTING.md              # Team contribution & branch guidelines
├── LICENSE                      # Open-source MIT License
└── README.md                    # Root project documentation
```

---

## 15. Testing & Verification

### Automated Test Suite
The backend is covered by 19 test suites containing **87 comprehensive unit and integration tests**:

```bash
cd backend
pytest -v
```

**Test Coverage Summary**:
- `test_health.py`: Liveness and readiness health probe endpoints.
- `test_config.py`: Pydantic settings loading and validation.
- `test_weather_ingestion.py` & `test_weather_api.py`: Data ingestion, normalization, sanity bounds.
- `test_ml_dataset.py`, `test_ml_training.py`, `test_ml_inference.py`, `test_ml_api.py`: Feature engineering, XGBoost training, residual prediction.
- `test_spatial_downscaling.py`: 1-km UTM grid generation, DEM sampling, GeoParquet export.
- `test_panchayat_weather.py`: Area-weighted spatial aggregation and coverage diagnostics.
- `test_agricultural_context.py`: Crop mapping, DAS/GDD phenology stage, soil profiles.
- `test_agricultural_risk.py`: Direction-aware thermal, chilling, wind, and disease window rules.
- `test_advisory_engine.py`: Structured actions, timing windows, conflict detection, safety guardrails.
- `test_dashboard_api.py`: Frontend delivery endpoints.
- `test_demo_scenario.py`: End-to-end 10-link demonstration pipeline validation.

### Frontend Build Verification
```bash
cd frontend
npm run build
```
Build output compiles cleanly with zero TypeScript errors.

---

## 16. SIH Evaluation Highlights

1. **Deterministic Demonstration**: The canonical scenario (`2026-07-15`) allows judges to reproduce the entire 13-phase workflow in seconds.
2. **Interactive Judge Mode (`/judge`)**: A 10-step guided evaluation interface with real-time visual progress checkmarks.
3. **True ML Downscaling**: Physical residual anomaly learning ($\Delta T$) on a 1-km grid, rather than simple spatial interpolation.
4. **Crop-Stage Specificity**: Weather linked to crop phenology (Rice flowering vs Maize tasseling) and soil available water capacity.
5. **Multi-Crop Separation**: Multi-crop Panchayats maintain distinct, unblended advisories.
6. **Actionable Advisories**: Farmers receive concrete actions and operational windows (e.g. *Early Morning 06:00–09:00 AM*), not raw numbers.
7. **Scientific Transparency**: Explicitly discloses rainfall preservation from Block NWP and requirement of AWS operational validation.

---

## 17. Team Collaboration Workflow

1. Clone repository and set up local environment following [docs/TEAM_SETUP.md](docs/TEAM_SETUP.md).
2. Create a feature branch: `git checkout -b feature/short-description`.
3. Verify changes locally with tests (`pytest -v`) and build (`npm run build`).
4. Commit following conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`).
5. Push to GitHub and open a Pull Request targeting `main`.

---

## 18. Repository Status

> **Status: SIH Evaluation Ready**  
> *(This repository is frozen for Smart India Hackathon evaluation. It is an evaluated hackathon milestone and is not designated as "Production Ready".)*
