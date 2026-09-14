# Changelog

All notable changes to the **SIH-26074-AgroWeather-Downscaling** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0-sih-evaluation] - 2026-09-14

### 🌟 Release Summary: SIH Evaluation Ready Snapshot
This milestone represents the frozen, fully verified evaluation release for **Smart India Hackathon Problem Statement 26074**: *“Downscaling of weather forecast from Block level to Panchayat level for agro-meteorological advisory services.”*

The system delivers an end-to-end operational pipeline from Numerical Weather Prediction (NWP) ingestion to 1-km spatial machine learning downscaling, Panchayat area-weighted aggregation, multi-crop phenology and soil context resolution, direction-aware risk assessment, explainable farmer advisories, interactive GIS dashboards, and a deterministic judge evaluation suite.

---

### 🚀 Key Features & Capabilities

#### 1. Weather Ingestion & Quality Control (Phase 3)
- Provider-independent weather ingestion engine supporting IMD, NCMRWF, Open-Meteo, and local CSV providers.
- Automated range validation, sanity bounds, physical consistency checks, and outlier flagging.
- Temporal alignment with diurnal profile interpolation and standardized schema normalization.

#### 2. Machine Learning Residual Downscaling (Phases 4, 5, 6, 7)
- **Physics-Informed Formulation**: Predicts fine-scale temperature residual anomaly $\hat{R}(x,y) = T_{\text{downscaled}} - T_{\text{coarse}}$ rather than direct black-box temperatures.
- **Topographic & Biophysical Features**: Incorporates 30m SRTM DEM elevation, slope, aspect, Terrain Ruggedness Index (TRI), environmental lapse rate, and Sentinel-2 Land-Use/Land-Cover (LULC) vegetation fractions.
- **XGBoost Regressor Engine**: Trained with early stopping, spatial/temporal cross-validation, and local model registry versioning (`temperature_residual_v1.0.0`).
- **1-km Spatial Inference Grid**: Dynamic metric UTM projected grid generation (1000 m $\times$ 1000 m cells) with batch spatial inference and GeoParquet export.
- **Calibration Benchmark Metrics**: Test MAE $\approx 0.380^\circ\text{C}$, Test RMSE $\approx 0.520^\circ\text{C}$, Test $R^2 \approx 0.942$ (72.6% error reduction over coarse baseline).

#### 3. Area-Weighted Panchayat Aggregation (Phase 8)
- Exact spatial geometric polygon intersection in projected metric CRS.
- Area-weighted temperature statistics ($T_{\text{mean}}, T_{\text{min}}, T_{\text{max}}$, standard deviation $\sigma_T$, percentiles $T_{p10}, T_{p90}$).
- Data coverage quality classification (`COMPLETE` $\ge 95\%$, `PARTIAL` $50\text{--}95\%$, `UNAVAILABLE` $<50\%$).
- Transparent policy: Rainfall is preserved from coarse Block NWP without artificial spatial downscaling.

#### 4. Agricultural Context & Phenology Engine (Phase 9)
- Sentinel-2 cropland eligibility masking excluding urban, water bodies, and reserve forests.
- Strict multi-crop separation for mixed-cropping Panchayats (e.g. Rice + Maize).
- Deterministic crop phenological stage resolution using Days After Sowing (DAS), Growing Degree Days (GDD), and crop calendar defaults.
- Soil hydrological profiling with Available Water Capacity (AWC in mm/m), texture, drainage, and pH.

#### 5. Agricultural Risk Engine (Phase 10)
- Modular versioned rule registry (`agri_risk_v1.0.0`) based on ICAR/IMD agrometeorological standards.
- Crop/stage direction-aware hazard evaluators:
  - Thermal / Heat Stress (e.g. Rice flowering sterility $\ge 35^\circ\text{C}$, Maize tasseling $\ge 35^\circ\text{C}$, Wheat heading $\ge 28^\circ\text{C}$)
  - Cold / Chilling / Frost Stress (e.g. Wheat heading frost injury $\le 2^\circ\text{C}$)
  - Pathogen Environmental Suitability (micro-climatic windows $22\text{--}32^\circ\text{C}$, high RH)
  - Convective Wind Lodging Stress ($>25\text{--}35\text{ km/h}$)
  - Soil Water & Hydrological Stress
- Uncertainty safety: Missing weather/soil attributes produce explicit `INSUFFICIENT_DATA` rather than false safe signals.

#### 6. Explainable Agro-Advisory Engine (Phase 11)
- Rule-based advisory generator (`agri_advisory_v1.0.0`) driven strictly by detected risks.
- Actionable farmer guidance with optimal operational timing windows (e.g. *Early Morning 06:00–09:00 AM*).
- Operational conflict detection (e.g. irrigate for heat vs withhold for wind lodging) automatically flagging `EXPERT_REVIEW_REQUIRED`.
- **Safety Policy & Guardrails**: No disease diagnosis, no chemical pesticide prescriptions or dosages, 100% provenance traceability.

#### 7. Modern GIS Dashboard & Judge Evaluation Mode (Phases 12, 13)
- React 18 + TypeScript + Vite responsive web application with glassmorphism design.
- Leaflet interactive map with 1-km spatial thermal grid overlay, boundary markers, and grid cell inspector.
- Multi-role dashboards: Farmer View, Extension Officer View, Administrator / Scientist View.
- **Interactive SIH Judge Walkthrough (`/judge`)**: 10-step guided evaluation sequence with real-time verification status.
- Deterministic demo suite for canonical date `2026-07-15`:
  - `seed_demo_scenario.py`
  - `validate_demo_scenario.py`
  - `reset_demo_scenario.py`

---

### 🔬 Scientific Transparency & Disclaimers
1. **Calibration vs Operational Validation**: Model performance metrics (MAE $0.380^\circ\text{C}$, RMSE $0.520^\circ\text{C}$, $R^2 = 0.942$) reflect calibration test datasets. Operational validation against independent Automatic Weather Station (AWS) ground networks is subject to field pilot deployment.
2. **Rainfall Modeling**: Rainfall is **not** downscaled; it is transparently preserved from coarse Block NWP forecast inputs.
3. **Pathogen Scope**: Disease-favorable conditions indicate environmental risk windows only, not biological disease diagnosis. The system does not prescribe pesticide brand names or chemical dosages.

---

### 🔮 Future Roadmap (Post-SIH Pilot Phase)
- Dense Automatic Weather Station (AWS) real-time telemetric validation.
- Doppler weather radar and satellite precipitation assimilation for convective rainfall downscaling.
- Expanded crop calibration for mustard, pulses, sugarcane, and horticultural crops.
- Multi-channel farmer advisory dissemination via SMS, WhatsApp API, and Interactive Voice Response (IVR).
- In-situ camera and IoT soil moisture probe integration.
