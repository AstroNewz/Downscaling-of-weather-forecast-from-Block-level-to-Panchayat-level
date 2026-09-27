# Mobile Backend API Inventory & Mapping
**Project:** AgroWeather — SIH Problem Statement 26074  
**Date:** September 26, 2026  
**Status:** COMPLETED & VERIFIED

---

## 1. Unified Forecast & Downscaling API

### `GET /api/v1/forecast`
- **Method:** `GET`
- **Path:** `/api/v1/forecast`
- **Purpose:** Primary high-resolution downscaled weather, diurnal hourly schedule, multi-day synoptic outlook, agricultural risks, and actionable farmer guidance.
- **Request Parameters:**
  - `location_type`: (Optional) `"panchayat" | "station" | "coordinates"` (default: `"panchayat"`)
  - `location_id`: (Optional) `"1" | "2" | "maya_bazar" | "delhi"` (default: `"1"`)
  - `latitude`, `longitude`: (Optional) Floating point coordinates
  - `target_date`: (Optional) ISO Date string (`YYYY-MM-DD`, default: current date)
  - `start_date`, `end_date`: (Optional) Horizon bounds
  - `timezone`: (Optional) Timezone string (default: `"Asia/Kolkata"`)
  - `mode`: (Optional) `"auto" | "dynamic_v2" | "baseline" | "mock"` (default: `"auto"`)
- **Request Body:** None
- **Response Structure:**
  ```json
  {
    "location_id": "1",
    "location_name": "Maya Bazar Gram Panchayat",
    "latitude": 25.35,
    "longitude": 82.95,
    "elevation_m": 112.0,
    "forecast_date": "2026-09-26",
    "forecast_hour": 14,
    "request_id": "req_fc_e464e04feb63",
    "generated_at": "2026-09-26T05:20:22.993306Z",
    "source_timestamp": "2026-09-26T12:00",
    "forecast_valid_time": "2026-09-26T14:00:00+05:30",
    "current": {
      "temperature_c": 32.9,
      "downscaled_temperature_c": 32.9,
      "coarse_temperature_c": 32.8,
      "dynamic_residual_c": 0.1,
      "humidity_pct": 68,
      "wind_speed_kmh": 20.0,
      "rainfall_mm": 0.0,
      "rain_probability_pct": 10,
      "weather_code": 1,
      "condition_text": "Sunny / Favorable",
      "icon_name": "sun"
    },
    "hourly_forecast": [
      {
        "local_time": "2026-09-26T00:00:00+05:30",
        "hour": 0,
        "downscaled_temperature_c": 26.5,
        "coarse_temperature_c": 26.4,
        "dynamic_residual_c": 0.1,
        "humidity_pct": 82,
        "wind_speed_kmh": 12.0,
        "precipitation_mm": 0.0,
        "rain_probability_pct": 5,
        "risk": "NONE",
        "advisory": "Stable night microclimate."
      }
    ],
    "daily_forecast": [
      {
        "date": "2026-09-26",
        "display_label": "Today",
        "day_label": "Today",
        "is_today": true,
        "t_max_c": 33.6,
        "t_min_c": 25.4,
        "rainfall_mm": 0.0,
        "rain_probability_pct": 10,
        "condition_text": "Partly Cloudy",
        "icon_name": "cloud-sun",
        "primary_risk": "MODERATE"
      }
    ],
    "agricultural_risks": [
      {
        "id": "risk_heat_stress",
        "category": "HEAT",
        "risk_type": "HEAT_STRESS",
        "title": "Heat Stress Risk",
        "severity": "LOW",
        "status": "NOT_DETECTED",
        "observed_value": 33.6,
        "threshold_value": 35.0,
        "unit": "°C",
        "crop": "Rice (Paddy)",
        "crop_stage": "Flowering / Anthesis",
        "why": "High ambient temperatures during morning anthesis desiccate pollen grains.",
        "trigger": "Downscaled temperature 33.6°C"
      }
    ],
    "farmer_actions": [
      {
        "id": "act_routine_weeding",
        "priority": "LOW",
        "category": "FIELD_MANAGEMENT",
        "title": "Proceed with Routine Field Operations",
        "timing": "Daytime",
        "action": "Weather conditions are favorable for manual weeding and routine field scouting.",
        "why": "Absence of thermal extremes or high precipitation permits normal field access.",
        "crop": "Rice (Paddy)",
        "crop_stage": "Flowering / Anthesis",
        "risk": "LOW"
      }
    ],
    "provenance": {
      "source_provider": "CANONICAL_PILOT_FIXTURE",
      "model_used": "DYNAMIC_V2",
      "certified_baseline_invariant": "T_calibrated = T_coarse + 0.7351°C",
      "fallback_active": false,
      "data_mode": "DEMO",
      "quality_status": "PASSED",
      "data_age_minutes": 0.0
    }
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Invalid dates or coordinates
  - `404 Not Found`: Location ID not recognized
  - `503 Service Unavailable`: Backend downscaling pipeline failure
- **Freshness & Provenance:** Handled in top-level `provenance` block.
- **Data Mode:** Explicitly reported (`"DEMO" | "LIVE" | "FALLBACK"`).
- **Usable by Mobile:** **YES — Primary client endpoint for Farmer and Official dashboards.**

---

### `GET /api/v1/forecast/locations`
- **Method:** `GET`
- **Path:** `/api/v1/forecast/locations`
- **Purpose:** Enumerates all monitored Panchayats and locations with geographic coordinates, LGD codes, administrative block, and primary crop profiles.
- **Request Parameters:** None
- **Response Structure:**
  ```json
  {
    "locations": [
      {
        "id": "1",
        "name": "Maya Bazar Gram Panchayat",
        "type": "PANCHAYAT",
        "block_name": "Maya Bazar Demonstration Block",
        "district_name": "Varanasi",
        "state_name": "Uttar Pradesh",
        "latitude": 25.35,
        "longitude": 82.95,
        "elevation_m": 112.0,
        "primary_crops": ["Rice (Paddy)", "Maize (Kharif)"]
      }
    ],
    "total": 8
  }
  ```
- **Usable by Mobile:** **YES — Used for global location pickers and Explorer.**

---

## 2. Panchayat Spatial & Detail APIs

### `GET /api/v1/panchayat/{panchayat_id}/detail`
- **Method:** `GET`
- **Path:** `/api/v1/panchayat/{panchayat_id}/detail`
- **Purpose:** Full agronomic profile including land use, soil available water capacity (AWC), crop stage phenology, active advisories, and detected risks.
- **Request Parameters:** `panchayat_id` (path)
- **Response Structure:** Contains `panchayat`, `agricultural_contexts`, `detected_risks`, `active_advisories`.
- **Usable by Mobile:** **YES — Powers `PanchayatDetailScreen` (6 tabs).**

### `GET /api/v1/panchayat/list`
- **Method:** `GET`
- **Path:** `/api/v1/panchayat/list`
- **Purpose:** Administrative directory of monitored Panchayats.
- **Usable by Mobile:** **YES — Powers `ExplorerScreen`.**

---

## 3. High-Resolution GIS Grid API

### `GET /api/v1/ml/grid/cells`
- **Method:** `GET`
- **Path:** `/api/v1/ml/grid/cells`
- **Purpose:** 1-km spatial metric downscaled grid cells across pilot region with elevation, slope, aspect, cropland fraction, coarse temperature, residual, and downscaled temperature.
- **Request Parameters:** None
- **Response Structure:** Array of 81 cells inside `data`.
- **Usable by Mobile:** **YES — Powers `GisMapScreen` (1-km GIS layer and cell inspector).**

---

## 4. System Status, Mode & Governance APIs

### `GET /api/v1/system/mode`
- **Method:** `GET`
- **Path:** `/api/v1/system/mode`
- **Purpose:** Authority for system data mode (`"DEMO" | "LIVE"`).
- **Usable by Mobile:** **YES — Powers disclosure banners and profile mode displays.**

### `GET /api/v1/system/data-status`
- **Method:** `GET`
- **Path:** `/api/v1/system/data-status`
- **Purpose:** Reports upstream data provider health, age in minutes, freshness status, and quality flags.
- **Usable by Mobile:** **YES — Powers data freshness labels and connectivity indicators.**

### `GET /api/v1/system/telemetry`
- **Method:** `GET`
- **Path:** `/api/v1/system/telemetry`
- **Purpose:** Operational metrics including model status, active model, fallback status, and execution counters.
- **Usable by Mobile:** **YES — Powers `AdminScreen` governance KPIs.**

---

## 5. Summary of Usable Endpoints for Mobile

| Mobile Component | Primary API Endpoint | Secondary Fallback |
| :--- | :--- | :--- |
| Current Weather & Hero | `GET /api/v1/forecast?location_id={id}` | In-memory cache / Last fresh |
| Hourly 24-hr Forecast | `GET /api/v1/forecast?location_id={id}` | Diurnal synthesis |
| 7-Day Daily Forecast | `GET /api/v1/forecast?location_id={id}` | Multi-day horizon |
| Farmer Advisories & Actions | `GET /api/v1/forecast?location_id={id}` | `GET /api/v1/advisory/list` |
| Location Selection | `GET /api/v1/forecast/locations` | Static list |
| 1-km GIS Grid View | `GET /api/v1/ml/grid/cells` | `MockRepository.generateGridCells()` |
| Panchayat Detail (6 Tabs) | `GET /api/v1/panchayat/{id}/detail` | Local composite |
| System Governance & Audit | `GET /api/v1/system/telemetry` | Baseline status |
| Data Mode & Freshness | `GET /api/v1/system/data-status` | Offline fallback |
