# Release Notes: v1.0.0-sih-evaluation

**Smart India Hackathon Problem Statement 26074**  
*“Downscaling of weather forecast from Block level to Panchayat level for agro-meteorological advisory services.”*

---

## 🏷️ Release Metadata

| Attribute | Value |
| :--- | :--- |
| **Release Tag** | `v1.0.0-sih-evaluation` |
| **Release Status** | **SIH Evaluation Ready** (Not Production Ready) |
| **Target Demonstration Area** | Ayodhya District (Maya Bazar & Sohawal Blocks), UP |
| **Canonical Demo Date** | `2026-07-15` |
| **Backend Framework** | FastAPI (Python 3.11+), PostgreSQL 16 + PostGIS 3.4 |
| **Frontend Framework** | React 18, TypeScript, Vite, TailwindCSS / Glassmorphism |
| **ML Engine** | XGBoost Regressor Residual Downscaling (`v1.0.0`) |
| **Test Suite Coverage** | 19 test modules, 87 unit and integration tests |

---

## 🎯 Release Objectives & Accomplishments

This release packages the complete 13-phase engineering pipeline into a reproducible, evaluated, and team-shareable repository:

```
BLOCK WEATHER FORECAST (Phase 3)
         ↓
1-km XGBOOST TEMPERATURE DOWNSCALING (Phases 4-7)
         ↓
PANCHAYAT AREA-WEIGHTED AGGREGATION (Phase 8)
         ↓
AGRICULTURAL CONTEXT & PHENOLOGY (Phase 9)
         ↓
AGRICULTURAL RISK DETECTION ENGINE (Phase 10)
         ↓
EXPLAINABLE AGRO-ADVISORY ENGINE (Phase 11)
         ↓
FARMER & EXTENSION OFFICER GIS DASHBOARD (Phase 12)
         ↓
SIH DEMONSTRATION & EVALUATION SUITE (Phase 13)
```

---

## 📊 Calibration Benchmarks (v1.0.0)

- **Algorithm**: XGBoost Regressor with DEM elevation, slope, aspect, TRI, lapse rate, and Sentinel-2 LULC fractions.
- **Formulation**: $T_{\text{downscaled}}(x,y) = T_{\text{coarse}} + \hat{R}(x,y)$
- **Test Set MAE**: `0.380 °C` (Coarse baseline: `2.34 °C` $\rightarrow$ 72.6% error reduction)
- **Test Set RMSE**: `0.520 °C`
- **Test Set R²**: `0.942`

---

## 🛡️ Scientific Disclaimers & Limitations

1. **Operational Validation**: Benchmark metrics are derived from synthetic/test calibration. Ground truth operational validation against dense in-situ Automatic Weather Stations (AWS) is required for operational deployment.
2. **Rainfall Preservation**: Rainfall is not spatially downscaled; it is aggregated directly from the coarse Block NWP input.
3. **Pathogen Scope**: Disease-favorable conditions represent micro-climatic environmental windows only. The platform does not diagnose biological disease or prescribe pesticide brand names/dosages.

---

## 🧪 Verification & Demonstration Tools

- **Demo Seeder**: `python backend/scripts/seed_demo_scenario.py --date 2026-07-15`
- **Pipeline Validator**: `python backend/scripts/validate_demo_scenario.py --date 2026-07-15`
- **Safe Reset**: `python backend/scripts/reset_demo_scenario.py --force`
- **Judge Walkthrough**: Navigate to `/judge` in the web application.
