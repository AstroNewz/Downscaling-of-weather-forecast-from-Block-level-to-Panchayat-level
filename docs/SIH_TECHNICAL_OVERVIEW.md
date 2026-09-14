# SIH Problem Statement 26074: Technical Architecture & System Overview

> **Project Title**: *Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services*  
> **Platform Version**: 1.0.0  
> **Target Geographic Demo**: Ayodhya District (Maya Bazar & Sohawal Blocks), Uttar Pradesh  

---

## 1. Executive Summary & Scientific Pipeline

The platform bridges the spatial resolution gap between coarse Numerical Weather Predictions (NWP at ~12–25 km block level) and actionable agricultural management at the **Gram Panchayat level** (~1 km scale).

```
BLOCK FORECAST (Phase 3: NWP Ingestion, QC & Normalization)
        ↓
PHASE 6: XGBoost ML Residual Downscaling Model
        ↓
PHASE 7: 1-km Metric Projected Spatial Weather Grid (SRTM DEM + LULC Features)
        ↓
PHASE 8: Panchayat Area-Weighted Spatial Aggregation
        ↓
PHASE 9: Panchayat Agricultural Context (Crop Phenology + Soil + Land-Use Mask)
        ↓
PHASE 10: Agricultural Risk Engine (Crop/Stage Direction-Aware Hazard Detection)
        ↓
PHASE 11: Agro-Meteorological Advisory Engine (Structured Action, Timing, Conflict Flags)
        ↓
PHASE 12: Panchayat Web Dashboard & Leaflet GIS Delivery Layer
        ↓
PHASE 13: Deterministic SIH Demonstration, Validation & Evaluation Suite
```

---

## 2. Mathematical Formulation & Machine Learning (Phases 6 & 7)

### A. Residual / Bias Formulation
Direct absolute temperature prediction causes spatial drift and unanchored anomalies. Our architecture formulates the task as **residual anomaly learning ($\Delta T$)**:

$$T_{\text{downscaled}}(x, y) = T_{\text{coarse}} + \hat{R}(x, y)$$

Where the ML model predicts $\hat{R}(x, y) = f_{\text{XGBoost}}(\mathbf{X})$ based on high-resolution surface biophysical features $\mathbf{X}$:
1. **SRTM 30m DEM Elevation ($z$)**: Environmental lapse rate cooling / valley warming.
2. **Topographic Slope ($\theta$) & Aspect ($\phi$)**: Solar irradiance and micro-topographic heating.
3. **Sentinel-2 LULC Fractions**: Cropland, urban heat island, forest canopy, and water body latent heat buffers.
4. **Cyclical Temporal Features**: Day-of-year sine/cosine components.

### B. Calibration Model Benchmarks (v1.0.0)
- **Algorithm**: XGBoost Regressor (`n_estimators=300`, `max_depth=6`, `learning_rate=0.05`, `subsample=0.8`).
- **Pipeline Calibration Metrics**:
  - Test MAE: **0.380 °C** (vs Baseline Coarse MAE: 2.34 °C; **72.6% error reduction**)
  - Test RMSE: **0.520 °C**
  - Test $R^2$: **0.942**
- *Transparency Note*: Evaluated on synthetic/calibration test datasets for algorithm and pipeline verification; operational validation against dense live AWS networks is subject to field pilot deployment.

---

## 3. Spatial GIS & Panchayat Aggregation (Phases 7 & 8)

1. **Projected Metric Grid (Phase 7)**:
   - 1000 m $\times$ 1000 m grid generated in a locally appropriate projected metric CRS (dynamic UTM), with WGS84 used for geographic output.
   - Point/Polygon intersections preserve geometric bounds and output WGS84 (EPSG:4326) coordinates.
2. **Area-Weighted Panchayat Aggregation (Phase 8)**:
   - Intersects 1-km grid cell polygons with official Gram Panchayat administrative boundaries:

   $$w_i = \frac{\text{Area}(\text{Cell}_i \cap \text{Panchayat})}{\text{Area}(\text{Panchayat})}, \quad \bar{T}_{\text{panchayat}} = \frac{\sum w_i \cdot T_i}{\sum w_i}$$

   - Preserves explicit data quality classifications: `COMPLETE` ($\ge 90\%$ coverage), `PARTIAL` ($50\text{--}90\%$), or `UNAVAILABLE` ($<50\%$).
   - **Rainfall Policy**: Rainfall is aggregated from the coarse block forecast without artificial spatial downscaling.

---

## 4. Agricultural Context & Phenology (Phase 9)

- **Cropland Eligibility Mask**: Sentinel-2 10m LULC masks out urban settlements, water bodies, and reserve forests so non-cropland areas never receive agricultural advisories.
- **Multi-Crop Separation**: Multi-crop Panchayats (e.g. Rice + Maize) are maintained as independent context entities without cross-crop data contamination.
- **Crop Phenology Resolution**:
  - Growth stage resolved via **Days After Sowing (DAS)** and **Growing Degree Days (GDD)**:

  $$\text{GDD} = \sum \max\left(0, \frac{T_{\text{max}} + T_{\text{min}}}{2} - T_{\text{base}}\right)$$

- **Soil Profile**: Hydrological capacity characterized by soil texture (Alluvial Silt Loam), pH, and **Available Water Capacity (AWC in mm/m)**.

---

## 5. Agricultural Risk Engine (Phase 10)

- **Versioned Rule Registry**: `agri_risk_v1.0.0`
- **Direction-Aware Threshold Evaluation**:
  - *Thermal Heat Stress ($T_{\text{max}} \ge \text{Threshold}$)*: Risk score scales positively as temperature rises above critical stage limits.
  - *Cold / Chilling Stress ($T_{\text{min}} \le \text{Threshold}$)*: Risk score scales inversely as temperature drops below chilling limits.
  - *High Wind Conditions ($V_{\text{wind}} \ge \text{Threshold}$)*: Evaluates mechanical bending stress on tall standing canopies.
  - *Pathogen Environmental Suitability*: Evaluates micro-climatic windows ($22\text{--}32^\circ\text{C}$, high RH) favorable for foliar pathogens without diagnosing biological disease presence.
- **Uncertainty Safety**: Missing weather or soil parameters result in explicit `INSUFFICIENT_DATA` rather than a false safe signal.

---

## 6. Agro-Meteorological Advisory Generation (Phase 11)

- **Versioned Rule Registry**: `agri_advisory_v1.0.0`
- **Structured Action Output**:
  - Action summary & granular operational steps.
  - Optimal operational timing window (e.g., *Early Morning 06:00 - 09:00 AM*).
  - Urgency level (`IMMEDIATE`, `NEXT_24H`, `NEXT_48H`, `ROUTINE`).
- **Operational Conflict Detection**:
  - Conflicting recommendations (e.g., irrigate for heat stress vs withhold irrigation for wind lodging) automatically set `status = EXPERT_REVIEW_REQUIRED` and flag `conflict_flag = True`.
- **Agronomic Safety Policy**:
  - **No Chemical Prescriptions**: Never prescribes chemical pesticide brands or chemical dosages.
  - **No Disease Diagnosis**: Reports environmental favorability only.
  - **100% Provenance**: Records `block_forecast_id`, `panchayat_weather_id`, `risk_log_id`, and rule versions.

---

## 7. Delivery Dashboard & Judge Mode (Phases 12 & 13)

- **Frontend Tech Stack**: React 18, TypeScript, Vite, Vanilla CSS Glassmorphism Design System.
- **Multi-Role Viewports**:
  - *Farmer View*: Plain language, high-urgency action steps, timing windows.
  - *Extension Officer View*: Multi-crop triage, risk ranking, advisory conflict escalation.
  - *Administrator / Scientist View*: Model registry, calibration metrics, rule version provenance.
- **Interactive Leaflet/Vector GIS Map**: 1-km thermal grid cell inspector displaying elevation, slope, aspect, cropland fraction, coarse temp, and predicted residual $\Delta T$.
- **SIH Judge Walkthrough Mode (`/judge`)**: Guided 10-step interactive visual workflow showing the complete pipeline with live progress checkmarks.
- **Connection Indicator**: Persistent pill showing `🟢 LIVE FASTAPI BACKEND` or `🟡 DEMO / SYNTHETIC DATA MODE`.

---

## 8. CLI & Reproducibility Tooling (Phase 13)

```bash
# Seed the canonical demonstration scenario
python backend/scripts/seed_demo_scenario.py --date 2026-07-15

# Validate all 10 links in the demonstration pipeline
python backend/scripts/validate_demo_scenario.py --date 2026-07-15

# Safely wipe only synthetic demo records
python backend/scripts/reset_demo_scenario.py --force
```

---

## 9. Limitations & Pilot-to-Production Roadmap

| Component | Current Implementation (Phase 1–13) | Pilot-to-Production Roadmap |
| :--- | :--- | :--- |
| **Temperature Downscaling** | 1-km XGBoost Residual Model ($T_{\text{coarse}} + \Delta T$) | Dense Automatic Weather Station (AWS) field validation |
| **Rainfall Modeling** | Coarse Block NWP forecast preserved | Doppler radar & satellite precipitation assimilation |
| **Crop Calibrations** | Rice, Maize, and Wheat | Mustard, Pulses, Sugarcane, and Horticulture crops |
| **Advisory Delivery** | Web Dashboard & REST APIs | Direct SMS / IVR / WhatsApp farmer messaging gateway |
| **Disease Monitoring** | Environmental favorability window | In-situ smart camera trap & spore trap integration |
