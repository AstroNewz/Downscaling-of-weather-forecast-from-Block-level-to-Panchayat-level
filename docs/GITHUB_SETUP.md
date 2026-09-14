# GitHub Repository Setup & Push Guide

**Smart India Hackathon Problem Statement 26074**  
*“Downscaling of weather forecast from Block level to Panchayat level for agro-meteorological advisory services.”*

---

## 🎯 Repository Overview

- **Target Repository Name**: `SIH-26074-AgroWeather-Downscaling`
- **Default Branch**: `main`
- **Evaluation Release Tag**: `v1.0.0-sih-evaluation`
- **Evaluation Status**: `SIH Evaluation Ready`

---

## 🚀 Connecting Local Repository to GitHub

Follow these steps on your workstation to initialize and push this repository to your team's GitHub organization or personal account.

### 1. Create a New GitHub Repository
1. Go to [https://github.com/new](https://github.com/new).
2. Repository name: `SIH-26074-AgroWeather-Downscaling`
3. Description:
   > *AI-based spatial downscaling of Block-level weather forecasts to approximately 1-km Panchayat-level agro-meteorological information with crop, soil, risk, and explainable advisory intelligence — SIH Problem Statement 26074.*
4. Visibility: **Public** (or **Private** per SIH submission instructions).
5. **Do NOT** initialize with a README, .gitignore, or license (these already exist locally).

---

### 2. Initialize Git Locally (If Not Already Initialized)

Open a terminal at the root directory of this project:

```bash
# Verify you are in the project root
# (SIH pt 2 or SIH-26074-AgroWeather-Downscaling)

# Initialize git repository
git init

# Set default branch to main
git branch -M main
```

---

### 3. Verify .gitignore & Staging Safety

Ensure local environment files and dependencies are ignored:

```bash
# Check git status
git status
```

Confirm that the following are NOT staged:
- `backend/.env`
- `frontend/.env`
- `backend/.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`

---

### 4. Stage & Commit Project Files

```bash
# Stage all verified project files
git add .

# Create the initial SIH evaluation release commit
git commit -m "chore: prepare SIH evaluation release"
```

---

### 5. Tag the Release

Create the annotated release tag:

```bash
git tag -a v1.0.0-sih-evaluation -m "SIH Evaluation Ready release"
```

---

### 6. Link Remote & Push to GitHub

Replace `<GITHUB_USERNAME>` with your GitHub username or team organization:

```bash
# Add GitHub remote origin
git remote add origin https://github.com/<GITHUB_USERNAME>/SIH-26074-AgroWeather-Downscaling.git

# Push main branch
git push -u origin main

# Push release tag
git push origin v1.0.0-sih-evaluation
```

---

## 🏷️ Recommended GitHub Topics

Add the following topics in the GitHub repository settings (*About* section):

- `smart-india-hackathon`
- `sih-2024`
- `weather-downscaling`
- `agriculture`
- `agrometeorology`
- `machine-learning`
- `xgboost`
- `gis`
- `postgis`
- `fastapi`
- `react`
- `panchayat`

---

## 🛡️ Pre-Push Verification Checklist

- [x] Root `.gitignore` is present and active.
- [x] Root `.env.example` is present with placeholder credentials.
- [x] No sensitive API keys or database passwords committed.
- [x] Root `docker-compose.yml` orchestrates PostGIS and backend.
- [x] `docs/SIH_DEMO_SCRIPT.md` and `docs/SIH_TECHNICAL_OVERVIEW.md` are present.
- [x] Canonical demo scripts (`seed_demo_scenario.py`, `validate_demo_scenario.py`, `reset_demo_scenario.py`) are present.
- [x] SIH Judge Mode (`JudgeMode.tsx`) is present at route `/judge`.
- [x] Scientific limitations (Rainfall block-preserved, AWS operational validation required, No disease diagnosis) are clearly documented.
