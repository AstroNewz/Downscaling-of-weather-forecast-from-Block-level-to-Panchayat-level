# Team Setup & Developer Onboarding Guide

**Smart India Hackathon Problem Statement 26074**  
*“Downscaling of weather forecast from Block level to Panchayat level for agro-meteorological advisory services.”*

---

## 📋 System Prerequisites

Before setting up the project, ensure your workstation meets the following requirements:

| Component | Minimum Version | Recommended | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+ | 3.11.x or 3.12.x | Required for backend & ML downscaling |
| **Node.js** | 18.x+ | 20.x LTS | Required for React frontend & Vite build |
| **npm** | 9.x+ | 10.x+ | Bundled with Node.js |
| **PostgreSQL** | 15+ | 16.x | Required for relational storage |
| **PostGIS** | 3.3+ | 3.4+ | Required for spatial geometry & raster operations |
| **Docker & Compose** | 24.x+ | Latest Desktop | Optional (alternative to local PostGIS install) |
| **Git** | 2.30+ | Latest | Version control |

---

## ⚡ Quick Start: 12-Step Setup Walkthrough

### Step 1: Clone the Repository
```bash
git clone https://github.com/<GITHUB_USERNAME>/SIH-26074-AgroWeather-Downscaling.git
cd SIH-26074-AgroWeather-Downscaling
```

---

### Step 2: Set Up the Backend Virtual Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment (.venv)
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

---

### Step 3: Install Backend Dependencies
```bash
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install Python packages
pip install -r requirements.txt
```

> **Note for Windows / Geospatial Libraries**: `geopandas`, `shapely`, and `rasterio` install binary wheels on Windows automatically. If you encounter GDAL build errors, ensure wheel installations are enabled.

---

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` in both backend and frontend directories:

```bash
# From repository root:

# Backend configuration
copy backend\.env.example backend\.env    # Windows CMD
# or: cp backend/.env.example backend/.env # Linux/Mac/PowerShell

# Frontend configuration
copy frontend\.env.example frontend\.env    # Windows CMD
# or: cp frontend/.env.example frontend/.env # Linux/Mac/PowerShell
```

---

### Step 5: Start PostgreSQL with PostGIS

#### Option A: Using Docker Compose (Recommended)
From the repository root, start the PostGIS container:
```bash
docker compose up -d postgis
```
Verify the container is healthy:
```bash
docker compose ps
```

#### Option B: Using Local PostgreSQL / PostGIS
Ensure PostgreSQL is running locally on port 5432 with PostGIS extension enabled:
```sql
CREATE DATABASE agri_weather_db;
\c agri_weather_db;
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

### Step 6: Apply Database Migrations (Alembic)
```bash
cd backend
alembic upgrade head
```
This sets up all PostGIS tables (`blocks`, `panchayats`, `land_use_masks`, `raw_weather_forecasts`, `weather_grids_1km`, `panchayat_weather_records`, `crop_profiles`, `soil_profiles`, `panchayat_crop_contexts`, `agricultural_risk_logs`, `agro_advisories`).

---

### Step 7: Seed the Canonical SIH Demonstration Scenario
Seed the deterministic dataset for the SIH evaluation scenario (`2026-07-15`, Ayodhya District):
```bash
cd backend
python scripts/seed_demo_scenario.py --date 2026-07-15
```

---

### Step 8: Start the FastAPI Backend Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify backend health:
- Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check Probe: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Step 9: Install & Start Frontend Dashboard
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
The Vite development server will start at [http://localhost:5173](http://localhost:5173).

---

### Step 10: Run End-to-End Pipeline Validation
In a separate terminal (with backend environment activated):
```bash
cd backend
python scripts/validate_demo_scenario.py --date 2026-07-15
```
All 10 pipeline stages should report `PASS`.

---

### Step 11: Open SIH Judge Evaluation Mode
Open your browser and navigate to:
👉 **[http://localhost:5173/judge](http://localhost:5173/judge)**

This runs the guided 10-step evaluator interface with interactive visual checks across all downscaling, agricultural context, and advisory layers.

---

### Step 12: Resetting Demo Data Safely
To wipe only synthetic demonstration records without dropping the database schema:
```bash
cd backend
python scripts/reset_demo_scenario.py --force
```

---

## 🧪 Running Automated Tests

Run the complete backend test suite (19 test files, 87 tests):
```bash
cd backend
pytest -v
```

Run frontend production build verification:
```bash
cd frontend
npm run build
```

---

## 📂 Local-Only vs Tracked Files

To maintain repository hygiene and avoid data leaks, understand which files are local-only:

| File / Folder | Status | Purpose |
| :--- | :--- | :--- |
| `backend/.env` | **LOCAL-ONLY** | Local database credentials & secret keys |
| `frontend/.env` | **LOCAL-ONLY** | Local API URL endpoints |
| `backend/.venv/` | **LOCAL-ONLY** | Python virtual environment |
| `frontend/node_modules/` | **LOCAL-ONLY** | Node dependencies |
| `frontend/dist/` | **LOCAL-ONLY** | Production build outputs |
| `backend/data/raw/*` | **LOCAL-ONLY** | Large GeoTIFF / GRIB2 files (gitignored) |
| `backend/data/processed/*` | **LOCAL-ONLY** | Generated 1-km rasters (gitignored) |
| `backend/data/sample/*.csv` | **TRACKED** | Small sample datasets for demonstration |
| `*.gitkeep` | **TRACKED** | Preserves empty directory layout |
| `.env.example` | **TRACKED** | Configuration template with safe placeholders |

---

## 🔒 Security Policy for Team Members

1. **NEVER commit `.env` or files containing passwords/keys.**
2. If you add a new configuration parameter, add a safe placeholder to `.env.example`.
3. Check `git status` before staging to verify that no secret files or large binaries are included.
