# SIH 2024 Demonstration & Presentation Script

> **Problem Statement 26074**: *Downscaling of weather forecast from Block level to Panchayat level: Inferring high-resolution plots/data/information from low-resolution plot/data/information/variables for agro-meteorological advisory services.*

---

## ⏱️ 5-Minute Master Demonstration Sequence

### 0:00 – 0:30 | The Core Problem (Block vs Field Scale)
- **Screen**: Overview Dashboard / Judge Walkthrough (Stage 1)
- **Presenter**:
  > *"Respected Judges, current numerical weather prediction (NWP) models from IMD or NCMRWF issue forecasts at the **Block level** (~15 to 25 km spatial scale). However, agricultural vulnerability and farming operations are decided at the **Gram Panchayat field level** (~1 km scale).*
  >
  > *A single block-level temperature forecast averages out local valleys, gentle slopes, water bodies, and vegetation heat buffers. If a coarse forecast predicts 36°C across an entire block, high-elevation uplands might actually be 37.8°C—crossing the exact 35°C physiological threshold that causes irreversible spikelet sterility in flowering paddy. Our platform bridges this spatial and agronomic gap."*

---

### 0:30 – 1:15 | 1-km Temperature Downscaling Engine (Physics + ML)
- **Screen**: Weather & 1-km ML Analytics / GIS Spatial Map
- **Presenter**:
  > *"Rather than training a direct black-box model that drifts spatially, our **Phase 6 XGBoost Engine** predicts the **residual temperature anomaly ($\Delta T$)**:*
  >
  > $$\mathbf{T_{\text{downscaled}}(x, y) = T_{\text{coarse}} + \hat{R}(x, y)}$$
  >
  > *Features include 30-meter SRTM DEM elevation, topographic slope, aspect, and Sentinel-2 land-use vegetation fractions.*
  > *In our canonical demo scenario, while the coarse block forecast is 36.0°C, our 1-km spatial grid computes a +1.8°C local thermal residual, accurately predicting a local maximum temperature of 37.8°C.*
  >
  > *Notice our scientific honesty: Temperature is downscaled to 1-km using topography; rainfall is transparently preserved from coarse Block NWP without artificial fabrication."*

---

### 1:15 – 1:45 | Panchayat Area-Weighted Aggregation
- **Screen**: Panchayat Explorer / GIS Spatial Map
- **Presenter**:
  > *"In Phase 8, we intersect the continuous 1-km grid with administrative Gram Panchayat boundary polygons using **projected metric area-weighting**:*
  >
  > $$\mathbf{\bar{T}_{\text{panchayat}} = \frac{\sum w_i \cdot T_i}{\sum w_i}}$$
  >
  > *This yields localized Panchayat statistics ($T_{\text{max}}, T_{\text{min}}, T_{\text{mean}}$, standard deviation, and coverage quality) without boundary distortion."*

---

### 1:45 – 2:30 | Agricultural Context (Crop Stage + Soil Moisture)
- **Screen**: Panchayat Detail -> Agricultural Context Tab / Judge Mode
- **Presenter**:
  > *"Weather alone does not create agricultural risk—the **crop growth stage and soil context** determine vulnerability. In Phase 9, we isolate individual crops:*
  >
  > 1. **Rice (Paddy)**: Currently at *Flowering / Anthesis* (DAS 45, GDD 680)—critically sensitive to daytime heat above 35.0°C.
  > 2. **Maize (Corn)**: Currently at *Tasseling / Silking* (DAS 38, GDD 590)—vulnerable to mechanical root lodging under sustained winds above 25.0 km/h.
  >
  > *Soil hydrology is integrated: Alluvial Silt Loam with an Available Water Capacity (AWC) of 145 mm/m."*

---

### 2:30 – 3:15 | Agricultural Risk Engine (Direction-Aware Thresholds)
- **Screen**: Detected Risks Tab / Risk Monitor
- **Presenter**:
  > *"In Phase 10, our modular risk engine evaluates stage-specific hazard rules (`agri_risk_v1.0.0`):*
  >
  > - **Rice**: 37.8°C downscaled $T_{\text{max}}$ exceeds the 35.0°C flowering threshold $\rightarrow$ **HIGH Heat Stress (Risk Score: 0.82)**.
  > - **Maize**: 28.0 km/h wind exceeds the 25.0 km/h threshold $\rightarrow$ **MODERATE Wind Lodging Risk (Risk Score: 0.55)**.
  >
  > *Scoring is direction-aware: as temperature increases above critical heat thresholds, risk increases; missing data yields explicit `INSUFFICIENT_DATA` rather than a false safe signal."*

---

### 3:15 – 4:00 | Explainable Agro-Advisories & Conflict Resolution
- **Screen**: Advisory Hub / Advisory Card Deep-Dive
- **Presenter**:
  > *"Phase 11 converts detected risks into prioritized, actionable farming guidance:*
  >
  > - **For Rice**: *'Maintain 2–3 cm standing water layer in paddy fields during daytime peak hours to buffer canopy micro-climate temperature by 1.5–2.5°C.'* Optimal window: Early Morning (06:00–09:00 AM).
  > - **For Maize**: *'Withhold deep field irrigation immediately prior to high wind events to preserve soil mechanical anchoring against lodging.'*
  >
  > *Safety Policy & Guardrails:*
  > 1. **No Chemical/Pesticide Prescriptions**: Recommends monitoring and approved extension guidance.
  > 2. **No Disease Diagnosis**: Evaluates environmental favorability only.
  > 3. **Conflict Detection**: If irrigation is recommended for heat but contradicted by wind lodging, the system automatically flags `EXPERT_REVIEW_REQUIRED`."*

---

### 4:00 – 4:30 | Technical Governance & Pilot Readiness
- **Screen**: System Governance
- **Presenter**:
  > *"Under System Governance, judges can inspect:*
  > - Model Registry: XGBoost $v1.0.0$ residual model.
  > - Calibration Test Benchmarks: MAE 0.380°C, RMSE 0.520°C, $R^2 = 0.942$.
  > - Live API / Synthetic Demo toggle indicator.
  > - Complete provenance logs from Block NWP down to advisory issuance.
  >
  > *The system is fully modular, containerized, covered by 80+ automated unit and integration tests, and ready for Automatic Weather Station (AWS) field pilot deployment."*

---

## 🎯 Key Takeaways for Evaluators

1. **True Downscaling**: Physical residual correction ($\Delta T$) on 1-km metric grid, not simple spatial interpolation.
2. **Agriculture-Centric**: Weather connected to GDD, DAS, phenological thresholds, and soil AWC.
3. **Multi-Crop Separation**: Multi-crop Panchayats generate distinct, unblended advisories per crop.
4. **Actionable & Explainable**: Farmers receive specific operational timing windows and reasons, not raw numbers.
5. **Scientific Honesty**: Explicitly discloses that rainfall is block-level and operational ground truth validation is subject to AWS field pilot.
