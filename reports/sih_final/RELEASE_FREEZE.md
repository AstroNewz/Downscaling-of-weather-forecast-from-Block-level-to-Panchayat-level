# SIH Release Freeze Declaration

**SIH Problem Statement 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level**  
**Freeze Version**: `SIH-2024-FINAL-FREEZE`  
**Classification**: `LIMITED_VALIDATION` (Task 9 Certified)  
**Freeze Timestamp**: 2026-09-27T17:00:00Z  

---

## 1. Executive Summary & Freeze Scope

As of 2026-09-27, the **Agroweather-Downscaling** codebase is under formal **Release Freeze** for the Smart India Hackathon grand finale evaluation. 

Zero modifications to scientific weights, thresholds, model architectures, or validation datasets are permitted without an approved change-control entry.

```
       ┌────────────────────────────────────────────────────────┐
       │             RELEASE FREEZE STATUS: ACTIVE              │
       │                                                        │
       │  • Scientific Core: FROZEN (SHA-256 Verified)          │
       │  • Validation Results: FROZEN (N=24 Pilot Events)      │
       │  • API Contracts: FROZEN (FastAPI v1 Schemas)          │
       │  • UI Design & Presentation: FROZEN                    │
       │  • Readiness Tier: LIMITED_VALIDATION                  │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Frozen Scientific Artifacts & Cryptographic Signatures

All core scientific models and reference datasets are cryptographically pinned in [`RELEASE_FREEZE_MANIFEST.json`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/reports/sih_final/RELEASE_FREEZE_MANIFEST.json):

| Component | File Path | SHA-256 Signature | Status |
|---|---|---|---|
| **Certified Baseline Parameter** | `backend/models/production_baseline/baseline_calibration.json` | `dad1b693277a3be95aa283eeae5f1181adbe42cf6f76a5c1fe52f36d396ec2b9` | **FROZEN** |
| **Dynamic Residual V2 Weights** | `backend/models/candidates/.../xgboost_model.json` | `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294` | **FROZEN** |
| **Dynamic Residual V2 Schema** | `backend/models/candidates/.../metadata.json` | `193212a33f44fa205342a7810332822a912bb33f76fcbe9a531e0f0687e83616` | **FROZEN** |
| **Pilot Panchayat Boundaries** | `backend/data/raw/india/pilot/boundaries/authorized_panchayats.geojson` | `2711d412cc80e3089d846b074a3f36a4aa3fcce1aa013d332d7f87ea9ee2c2a0` | **FROZEN** |
| **Real Captured Satellite Raster** | `backend/data/raw/satellite/REAL_CAPTURED_INSAT3D_TIR_VARANASI.tif` | `a81ca52e2f07edd074092b7405e3f43b6794ce8b9aeeec01c73c52a0a2df31d3` | **FROZEN** |
| **Independent Validation Dataset**| `backend/data/raw/panchayat_mesonet/independent_validation_observations.json` | `31f437cd5f438104cb4eda83b0cde328df28d4943fd0cf69204403aa05781668` | **FROZEN** |
| **Forensic Audit Machine Registry**| `reports/FINAL_FORENSIC_AUDIT.json` | `72a01a726f8f68f070cb70e28f3ea73ca7b966bfb1b702111d45127ee6db15ec` | **FROZEN** |
| **Precipitation Validation Report**| `reports/PANCHAYAT_PRECIPITATION_VALIDATION_REPORT.json` | `5e617ed8371e0f1ef7806509935ee57a7fa311cf5da97db5fb2912534ce65876` | **FROZEN** |

---

## 3. Regression Test Status

| Test Suite | File | Count | Outcome | Notes |
|---|---|---|---|---|
| **SIH Demo Acceptance** | [`test_sih_demo_acceptance.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_sih_demo_acceptance.py) | **12 / 12** | **PASS** ✅ | Full 12 judge workflow criteria verified |
| **Final Forensic Audit** | [`test_final_forensic_audit.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_final_forensic_audit.py) | **12 / 12** | **PASS** ✅ | Immutability, reality, claim matrix |
| **Precipitation Validation**| [`test_panchayat_precipitation_validation.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_panchayat_precipitation_validation.py) | **18 / 18** | **PASS** ✅ | Metric calculation, station independence |
| **Real Data Activation** | [`test_real_data_activation.py`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/tests/test_real_data_activation.py) | **7 / 7** | **PASS** ✅ | Quality gates, PIP routing, A/B differentiation |
| **Frontend Contract** | [`localized_nowcast_contract.test.mjs`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/frontend/src/__tests__/localized_nowcast_contract.test.mjs) | **9 / 9** | **PASS** ✅ | Presentation contract & fail-closed states |
| **Frontend Build** | `npm run build` (Vite + TypeScript) | — | **PASS** ✅ | Production build compiles in ~929ms, 0 errors |
| **Flutter Mobile Tests** | `flutter test` | **22 / 22** | **PASS** ✅ | Role selection, navigation, cards |
| **Flutter Static Analysis** | `flutter analyze` | — | **PASS** ✅ | 0 issues found |

---

## 4. Operational Modes: DEMO vs. LIVE

### 4.1 Controlled DEMO Mode (Offline Resilient)
- Designed for hackathon judging environments with unstable or restricted internet connectivity.
- Deterministic, zero-network-dependent playback using canonical verified fixtures.
- Clearly displays `DEMO` badge in header and cards.
- Demonstrates exact A/B Panchayat spatial differentiation (Rameshwar vs. Jansa) using the real captured INSAT-3DR satellite field.

### 4.2 LIVE Operational Mode
- Connects to external upstream services:
  - IMD GFS / Open-Meteo operational numerical models for coarse baseline forecasts.
  - ISRO MOSDAC / IMD satellite observation adapter for 15-minute INSAT-3DR imagery feeds.
- If upstream telemetry is unavailable, stale (>60 min), or missing required credentials, the system **fails closed**:
  - Displays `LIVE • DATA UNAVAILABLE` with clear diagnostic reason.
  - Never silently substitutes mock data under a live label.

---

## 5. Known Scientific Limitations & Disclosures

1. **Geographic Validation Boundary**: Physical ground truth validation is established exclusively within the **Varanasi pilot district** (Rameshwar and Jansa Gram Panchayats, Arajiline Block). The system must be introduced to judges under the **`LIMITED_VALIDATION`** framework.
2. **Native Sensor Resolution**: INSAT-3DR TIR-1 pixel spacing is nominal **~3.8 km**. Displaying values within a Panchayat polygon does not imply finer meteorological observations than the underlying sensor resolution.
3. **Absence of Local Doppler Radar**: Eastern Uttar Pradesh lacks active Doppler weather radar coverage; precipitation nowcasting is driven by geostationary satellite infrared brightness temperature gradients.
4. **Agronomic Yield Claims**: Advisory logic follows IMD-GKMS rules; farmer income and yield enhancement percentages require multi-season randomized controlled trials (RCTs).
