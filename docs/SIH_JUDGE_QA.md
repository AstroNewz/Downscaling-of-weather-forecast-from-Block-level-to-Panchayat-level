# SIH Evaluation: Technical & Scientific Judge Q&A

**Project**: AgroMet — Downscaling Weather Forecast from Block to Panchayat Level  
**SIH Problem Statement**: 26074  
**Experiment**: `EXP_VARANASI_PILOT_PHASE18_FREEZE`  
**Release ID**: `SIH_PHASE20_FINAL`  

---

### 1. Why Panchayat-level?
Operational Numerical Weather Prediction (NWP) models from IMD and NCMRWF issue guidance at the Block scale (~12 km to 25 km). However, farming decisions (irrigation, spraying, harvesting) and administrative agricultural interventions (Krishi Vigyan Kendras, Gram Sabha advisories) are executed at the Gram Panchayat scale (~1 km to 5 km). Panchayat-level downscaling bridges the gap between macro-scale atmospheric forecasts and local farm field reality.

### 2. Why a 1-km grid?
A 1000m × 1000m metric grid (projected in UTM Zone 44N, `EPSG:32644`) balances computational feasibility with the physical scale of microclimatic drivers. Surface features that govern local temperature anomalies—such as 30m SRTM digital elevation, topographic slope, and 10m Sentinel-derived land cover fractions—aggregate naturally at 1-km resolution without introducing excessive sub-grid noise.

### 3. Why XGBoost?
Statistical residual downscaling involves complex non-linear interactions between continuous topographic features (elevation, aspect, slope) and discrete land-use classes (cropland vs. urban vs. water). Gradient-boosted decision trees (XGBoost) capture non-linear threshold effects, feature interactions, and tabular heterogeneity efficiently with low inference latency and robust handling of collinearity.

### 4. What is the residual target?
The model does not predict raw temperature directly. Instead, it predicts the high-resolution temperature residual:
$$\Delta T = T_{\text{independent\_reference}} - T_{\text{coarse}}$$
Downscaled temperature is reconstructed as:
$$T_{\text{downscaled}}(x, y) = T_{\text{coarse}} + \hat{\Delta T}(x, y)$$
Predicting residuals preserves the large-scale thermodynamic conservation of the coarse NWP forecast while allowing local surface predictors to adjust the microclimatic anomaly.

### 5. What is the independent observation source?
Ground-truth reference observations come from genuine NOAA Integrated Surface Database (ISD) stations. For the Varanasi pilot, 2,635 matched observations across 4 physical stations (Babatpur Airport, Varanasi Synoptic, Ghazipur, and Allahabad Airport) spanning June 1 to August 31, 2024 were ingested.

### 6. Why NOAA ISD?
NOAA ISD provides publicly accessible, quality-controlled, standardized hourly and synoptic surface weather observations from official WMO-indexed weather stations across India. Because real-time IMD high-density AWS feeds require restricted departmental credentials, NOAA ISD offers an auditable, open, and reproducible observation record for scientific validation.

### 7. Why not claim ERA5 as ground truth?
ERA5 is an atmospheric numerical reanalysis model product (~31 km resolution) that assimilates past observations into a global physical model. While it provides a consistent, uncorrupted coarse meteorological baseline, it is a model output, not an in-situ thermometer measurement. Conflating reanalysis with ground truth creates circular validation.

### 8. How was data leakage prevented?
Data leakage was prevented through four strict controls:
1. **Target Quarantine**: $\Delta T$ and ground-truth temperatures are excluded from the ordered feature matrix.
2. **Disjoint Chronological Split**: 70% train (Jun 1 – Jul 25), 15% validation (Jul 26 – Aug 12), 15% test (Aug 13 – Aug 31) with zero temporal overlap.
3. **Spatial Feature Separation**: Spatial coordinates are used only for static surface lookups, preventing memorize-and-lookup spatial leakage.
4. **Automated Audit**: Test suites programmatically verify that no target or proxy column enters the feature pipeline.

### 9. How was spatial generalization tested?
Spatial generalization was evaluated via Leave-One-Station-Out (LOSO) cross-validation across the 4 genuine regional stations:
- Each station was systematically held out while training on the remaining 3 stations.
- For example, on the Ghazipur regional holdout ($n=132$), Candidate V3 achieved a positive $R^2 = +0.137$ compared to the negative baseline $R^2 = -0.015$, confirming that learned terrain and land-use relationships generalize across geographic space.

### 10. Why was Candidate V3 not promoted to production?
Although Candidate V3 showed positive spatial transfer during LOSO validation, on the final frozen chronological holdout test it did not outperform the zero-residual baseline:
- Baseline MAE: 1.016 °C vs. V3 MAE: 1.077 °C.
- Baseline RMSE: 1.353 °C vs. V3 RMSE: 1.404 °C.
Following rigorous scientific integrity standards, a model that does not beat the simple operational baseline on the holdout test is **retained for research** and **rejected for production**.

### 11. Why is raw ERA5 still the operational baseline?
In operational agricultural advisories, safety is paramount. When an ML downscaling candidate fails to demonstrate statistical superiority over coarse NWP, deploying it introduces unpredictable residual errors that could trigger false heat-stress or chilling alerts. Falling back to the raw ERA5 coarse forecast guarantees physical atmospheric consistency.

### 12. Why is the terrain signal weak in this pilot?
The Varanasi pilot study area lies in the flat alluvial Gangetic plain:
- Regional elevations range between 80 m and 98 m MSL across stations (relief $< 18\text{ m}$).
- Slopes are $< 0.5^\circ$ throughout the 3,844 grid cells.
- The theoretical dry adiabatic lapse rate ($-0.0065\text{ }^\circ\text{C/m}$) produces a maximum thermal elevation difference of less than $0.12\text{ }^\circ\text{C}$, which is smaller than thermometer sensor uncertainty ($\pm 0.2\text{ }^\circ\text{C}$). Terrain downscaling requires high-relief topography ($> 500\text{ m}$) to express a dominant physical signal.

### 13. How would nationwide deployment be validated?
Nationwide deployment would require:
1. Division of India into agro-climatic zones (e.g., Western Himalayas, Indo-Gangetic Plains, Deccan Plateau, Coastal).
2. Continuous ingestion from 20+ automated weather stations (AWS) per district.
3. High-relief pilot validation in mountainous terrain (e.g., Himachal Pradesh or Uttarakhand).
4. Assimilation of satellite thermal infrared Land Surface Temperature (INSAT-3D/3DR, MODIS, Landsat).

### 14. How does the system handle missing data?
The system enforces strict uncertainty handling:
- If required weather variables (e.g., maximum temperature or wind speed) are missing or fail physical quality control bounds, the Agricultural Risk Engine outputs `INSUFFICIENT_DATA`.
- It never silently coerces missing values to zero or default constants.
- The Advisory Engine responds with an informational review notice rather than issuing ungrounded farming recommendations.

### 15. Can the What-If simulator alter the trained model?
No. The What-If simulator is strictly isolated. It accepts ephemeral parameter perturbations via API to project hypothetical downscaled temperature fields and evaluate downstream risk changes. It runs in-memory inference without writing to disk, mutating model weights, or altering database records.

### 16. How are demo records separated from real observations?
Demo records are quarantined using database keys and naming prefixes (`DEMO_` and `SYNTHETIC_`). The real data pipeline explicitly audits datasets and rejects records with demo classifications, preventing simulated or mock data from contaminating ML training or validation sets.

### 17. What would be needed for production certification?
Production certification requires:
1. Demonstration of statistically significant MAE and RMSE improvements over raw NWP across multiple consecutive seasons.
2. Dense district-level ground-truth validation using IMD AWS networks.
3. Automated continuous data drift monitoring and model retraining pipelines.
4. Formal review and endorsement by agrometeorological subject-matter experts (ICAR / IMD).

### 18. How does the system support explainability?
Every agro-meteorological advisory includes:
- **Biophysical Evidence**: Exact weather metric observed, physiological threshold exceeded, and crop growth stage.
- **Rule Traceability**: Unique identifier of the versioned risk and advisory rule that generated the alert (e.g., `agri_risk_v1.0.0 / RULE_RICE_HEAT_FLOWERING`).
- **Actionable Guidance**: Concrete cultural practice (e.g., *maintain 2–3 cm standing water*), specific timing window (e.g., *Early Morning 06:00–09:00 AM*), and priority ranking.
- **Conflict Transparency**: Conflicting actions flag `EXPERT_REVIEW_REQUIRED` rather than giving contradictory advice.
