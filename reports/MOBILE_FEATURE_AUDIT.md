# Mobile Feature Audit & Dependency Trace
**Project:** AgroWeather — SIH PS 26074 (Mobile ↔ Backend Integration)  
**Reference Product:** `mobile/` (Flutter Client)  
**Date:** September 26, 2026  
**Status:** AUDITED

---

## 1. Executive Summary

The existing Flutter application in `mobile/` serves as the **authoritative reference UX** for user-facing agricultural weather and advisory presentation. It supports two primary user personas:
1. **Farmer Persona (`FarmerShell`):** Action-first, jargon-free agricultural weather, diurnal forecasts, crop-specific advisory guidance, and role toggle.
2. **Government Official Persona (`OfficialShell`):** Multi-Panchayat operational surveillance, 1-km GIS microclimate grid, advisory conflicts, administrative explorer, and scientific governance/audit tracking.

This audit maps every screen, user journey, control, data dependency, and source transition from `MockRepository` to the FastAPI backend.

---

## 2. Screen Inventory & Journey Mapping

### User Journey 1: Role Selection & Onboarding
- **Screen:** `RoleSelectionScreen` (`lib/screens/role_selection_screen.dart`)
- **Flow:** User arrives from `SplashScreen`. Chooses between **Farmer / Citizen** (`AppUserRole.farmer`) and **Government Official** (`AppUserRole.official`). Persisted in `SharedPreferences`.

### User Journey 2: Farmer Experience (`FarmerShell`)
1. **Home (`FarmerHomeScreen`):**
   - **Data Needed:** Downscaled temperature, condition emoji, humidity, wind, rainfall, 1-km downscale badge, 3 prioritized today's advisories, Panchayat selector.
   - **Controls:** Panchayat picker dropdown, advisory card expansion, language toggle.
   - **Dependencies:** Location, Date, Weather, Advisory.
2. **Weather & Hourly (`FarmerWeatherScreen`):**
   - **Data Needed:** 24-hour diurnal downscaled hourly curve, temperature min/max range, humidity, wind, solar radiation, downscaling explanation.
   - **Controls:** Hourly scroll row, day horizon selection.
   - **Dependencies:** Location, Date, Diurnal Forecast.
3. **Advisories (`FarmerAdvisoryScreen`):**
   - **Data Needed:** Crop-specific advisories (Action, Best Time to Act, Agronomic Reason / Why, Priority), filter chips.
   - **Controls:** Crop Filter Chips (All, Rice, Maize, etc.).
   - **Dependencies:** Location, Date, Crop, Crop Stage, Risk, Advisory.
4. **Profile (`FarmerProfileScreen`):**
   - **Data Needed:** Panchayat name, block, district, seasonal holdings, active crops, soil type, language selection, backend data mode.
   - **Controls:** Language toggle (EN/HI), backend data mode toggle (Live/Demo), switch role to Official.
   - **Dependencies:** Location, Data Mode.

### User Journey 3: Government Official Experience (`OfficialShell`)
1. **Officer Dashboard (`OfficerScreen`):**
   - **Data Needed:** Jurisdiction summary, monitored Panchayats count, high-risk count, action conflict banner, critical intervention cards.
   - **Controls:** Tap Panchayat to open `PanchayatDetailScreen`.
   - **Dependencies:** District/Block jurisdiction, Multi-Panchayat Risks, Action Conflicts.
2. **1-km GIS Microclimate (`GisMapScreen`):**
   - **Data Needed:** 1-km metric grid cells (temperature, residual, cropland fraction, elevation, risk zones).
   - **Controls:** Layer Mode toggle (Temperature, Residual, Cropland, Risk Zones), cell tap inspector modal.
   - **Dependencies:** Spatial 1-km Grid, Elevation, Residual Downscaling.
3. **Advisory Hub (`AdvisoryHubScreen`):**
   - **Data Needed:** Full sorted advisory inventory (Critical first), priority labels, crop tags, timing windows.
   - **Controls:** Priority filter pill, crop filter pill.
   - **Dependencies:** Multi-Crop Advisories, Risk Priority.
4. **Panchayat Explorer (`ExplorerScreen`):**
   - **Data Needed:** Searchable, filterable directory of all Panchayats with dominant crop, weather, risk severity, contributing cells.
   - **Controls:** View mode toggle (Cards / Table), Search text query, Crop filter, Risk filter.
   - **Dependencies:** Panchayat Directory, Aggregate Weather, Risk Severity.
5. **Governance & Audit (`AdminScreen`):**
   - **Data Needed:** API latency, database status, last ingestion, certified baseline invariant ($T_{\text{coarse}} + 0.7351^\circ\text{C}$), ML model status (Dynamic V2 controlled production / research), audit log stream.
   - **Controls:** Run pipeline visualizer (`PipelineVisualizerScreen`), test fallback trigger.
   - **Dependencies:** System Telemetry, Model Metadata, Audit Logs.
6. **Official Profile (`OfficialProfileScreen`):**
   - **Data Needed:** Official credentials, designation, assigned block jurisdiction, settings, language.
   - **Controls:** Switch role to Farmer, toggle language, toggle live/demo mode.
   - **Dependencies:** User Role, Data Mode.
7. **Panchayat Detail (`PanchayatDetailScreen`):**
   - **Data Needed:** 6-tab deep dive for a single Panchayat: Weather, Crops & Soil, Risks, Advisories, Map, Provenance.
   - **Controls:** TabController (6 tabs), date picker.
   - **Dependencies:** Panchayat ID, Date, Full Agro-Met Bundle.

---

## 3. Comprehensive Feature & Integration Matrix

| Screen | Feature | Current Source (`MockRepository`) | Backend Source (`FastAPI`) | Integration Status |
| :--- | :--- | :--- | :--- | :--- |
| `FarmerHomeScreen` | Current Weather Hero | `MockRepository.weatherForPanchayat` | `GET /api/v1/forecast` (`current`) | Connected via Central API |
| `FarmerHomeScreen` | Actionable Farmer Cards | `MockRepository.advisoriesForPanchayat` | `GET /api/v1/forecast` (`farmer_actions`) | Connected via Central API |
| `FarmerHomeScreen` | Location Dropdown | `MockRepository.allPanchayats` | `GET /api/v1/forecast/locations` | Connected via Central API |
| `FarmerWeatherScreen` | 24-Hour Diurnal Schedule | Hardcoded static `_hours` list | `GET /api/v1/forecast` (`hourly_forecast`) | Connected via Central API |
| `FarmerWeatherScreen` | Today Range & Weather Metrics | `MockRepository.weatherForPanchayat` | `GET /api/v1/forecast` (`current` + `daily_forecast[0]`) | Connected via Central API |
| `FarmerWeatherScreen` | Downscaling Info Badge | Static formula text | `GET /api/v1/forecast` (`provenance` + model info) | Connected via Central API |
| `FarmerAdvisoryScreen` | Crop Advisory Cards | `MockRepository.advisories` | `GET /api/v1/forecast` (`farmer_actions` / `advisories`) | Connected via Central API |
| `FarmerAdvisoryScreen` | Crop Filter Chips | Static list `['All', 'Rice', 'Maize']` | `GET /api/v1/forecast` (`primary_crops`) | Connected via Central API |
| `FarmerProfileScreen` | Farm & Crop Holdings | Hardcoded Kharif profile | `GET /api/v1/panchayat/{id}/detail` | Connected via Central API |
| `FarmerProfileScreen` | Data Mode & Language | Local state in `AppState` | `GET /api/v1/system/mode` + `AppState` | Connected via Central API |
| `OfficerScreen` | Monitored Panchayats KPI | `MockRepository.allPanchayats.length` | `GET /api/v1/forecast/locations` | Connected via Central API |
| `OfficerScreen` | High-Risk Alert & Conflict | Hardcoded conflict banner | `GET /api/v1/panchayat/{id}/detail` (`detected_risks`) | Connected via Central API |
| `OfficerScreen` | Critical Intervention Cards | Filtered `allPanchayats` | `GET /api/v1/forecast/locations` + `/detail` | Connected via Central API |
| `GisMapScreen` | 1-km Grid Layer & Cells | `MockRepository.generateGridCells()` | `GET /api/v1/ml/grid/cells` | Connected via Central API |
| `GisMapScreen` | Cell Inspector Modal | Local cell properties | `GET /api/v1/ml/grid/cells` item | Connected via Central API |
| `AdvisoryHubScreen` | Multi-Crop Priority Advisories | `MockRepository.advisories` | `GET /api/v1/advisory/list` or `/panchayat/{id}/detail` | Connected via Central API |
| `ExplorerScreen` | Searchable Panchayat Directory | `MockRepository.allPanchayats` | `GET /api/v1/forecast/locations` + `/panchayat/list` | Connected via Central API |
| `AdminScreen` | System Health & Governance | `MockRepository.governanceMetrics` | `GET /api/v1/system/telemetry` & `/system/data-status` | Connected via Central API |
| `PanchayatDetailScreen` | 6-Tab Holistic Profile | Static maps in `MockRepository` | `GET /api/v1/panchayat/{id}/detail` + `/forecast` | Connected via Central API |

---

## 4. State Management & Synchronization Rules

1. **Location Synchronization:** Changing `_selectedPanchayatId` must clear current forecast/advisories to prevent stale data display and trigger an asynchronous reload with request ID tracking.
2. **Date Synchronization:** Changing `_forecastDate` must immediately re-fetch the forecast and calculate advisories aligned to that exact target date.
3. **Crop & Stage Synchronization:** When the user filters or selects a crop (e.g., Rice vs Maize), advisories and risk indicators must isolate that crop's specific phenology and thresholds without cross-contamination.
4. **Data Mode Authority:** Data mode is dictated by the backend (`GET /api/v1/system/mode` and `provenance.data_mode`), never assumed by the mobile app.
