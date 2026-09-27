# Phase 23: Operational Pipeline Architecture & Graceful Degradation Design

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE23`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Document**: Operational Pipeline Specification & Fault-Tolerant Hierarchy  

---

## 1. End-to-End Operational Pipeline Architecture

The certified operational production baseline adheres to a deterministic, zero-unobserved-feature architecture:

```
[1. Coarse Reanalysis / NWP Feed]
     ERA5 / IMD GFS Coarse Forecast (~25 km resolution)
                    │
                    ▼
[2. Rigorous Ingestion Quality Control]
     - Timestamp validity & ISO-8601 parsing
     - Physical boundary check (-40°C to +60°C)
     - Temporal freshness check (<= 180 min staleness)
                    │
                    ▼
[3. Certified Deterministic Calibration]
     T_calibrated = T_coarse + 0.7351°C
     (Attached uncertainty: MAE ±1.27°C, P80 ±1.96°C)
                    │
                    ▼
[4. 1-km Spatial Metric Grid Generation]
     - Metric CRS: Dynamic local UTM (e.g., EPSG:32644)
     - Geographic Output: WGS84 (EPSG:4326)
     - Display Only: Web Mercator (EPSG:3857)
                    │
                    ▼
[5. Panchayat Area-Weighted Spatial Aggregation]
     Polygon intersection between 1-km grid cells & Gram Panchayat boundary
     T_panchayat = SUM(T_cell * Area_weight) / SUM(Area_weight)
                    │
                    ▼
[6. Agricultural Crop & Stage Context Integration]
     Crop mapping, sowing dates, GDD phenology, soil texture
                    │
                    ▼
[7. Agronomic Risk Engine]
     Crop-specific heat stress, frost stress, disease favorable windows
                    │
                    ▼
[8. Farmer-Facing Explainable Agro-Advisory]
     Actionable, timing-constrained, bilingual advisory with uncertainty bounds
```

---

## 2. Graceful Degradation Hierarchy (Zero-Fabrication Policy)

The production pipeline enforces a strict, explicit degradation hierarchy. Under **no circumstances** does the system fabricate weather values or synthesize artificial temperatures.

```
Level 1: [VALIDATED CALIBRATED ERA5] (Full Operational Mode)
  ├── Coarse forecast passes QC AND calibration parameter applied
  └── Confidence: HIGH | Uncertainty: ±1.27°C MAE | Flag: CALIBRATED_OPERATIONAL

Level 2: [VALIDATED RAW ERA5] (Calibration Fallback Mode)
  ├── Calibration lookup fails OR regional station data unavailable
  └── System outputs raw coarse forecast with raw uncertainty
  └── Confidence: MODERATE | Uncertainty: ±1.59°C MAE | Flag: RAW_BASELINE_FALLBACK

Level 3: [INSUFFICIENT_DATA] (Safety Interruption Mode)
  ├── Missing coarse weather, stale data (>180 min), corrupt payload, or boundary failure
  └── Downstream advisory generation is SUSPENDED
  └── Status: INSUFFICIENT_DATA | Farmer Advisory: "Weather telemetry temporarily unavailable"
  └── NO RISK SCORE COMPUTED | ZERO OVERCONFIDENT ADVISORIES ISSUED
```

---

## 3. Operational Feature Minimization

To eliminate runtime fragility, the production baseline utilizes only variables that are reliably available in real time:

| Variable Name | Role in Production | Source | Temporal Cadence | Availability Status | Fallback Behavior |
|---|---|---|---|---|---|
| `temperature_2m` | Primary predictor | ECMWF / IMD GFS | Hourly / 3-hourly | **100% Operational** | Raw ERA5 -> INSUFFICIENT_DATA |
| `latitude` / `longitude` | Grid geolocation | Boundary Shapefiles | Static | **100% Operational** | Rejection if out of bounds |
| `elevation_m` | Topographic context | NASA SRTM 30m DEM | Static | **100% Operational** | Standard lapse rate fallback |
| `calibration_offset` | Scalar adjustment | Frozen Phase 23 Baseline | Static parameter | **100% Operational** | Raw ERA5 (Level 2) |

### Features Intentionally Excluded from Production
- ❌ Sub-hourly real-time relative humidity (high latency and telemetry dropouts in rural Panchayats).
- ❌ In-situ surface barometric pressure (sparse rural telemetry).
- ❌ Dynamic real-time lapse-rate adjustments (unstable under regional boundary extrapolation).
- ❌ Real-time cloud fraction (high satellite latency).

---

## 4. Coordinate Reference System (CRS) Protocol

1. **Metric Scientific Calculation**:
   - All distance, buffer, grid construction, and area calculations strictly utilize a dynamic local UTM projection (e.g., EPSG:32644 for Varanasi/Ayodhya pilot).
2. **Geographic Storage & GeoJSON API**:
   - All spatial outputs, GeoJSON geometries, and coordinates are encoded in WGS84 (EPSG:4326).
3. **Display-Only Rendering**:
   - EPSG:3857 (Web Mercator) is restricted strictly to frontend Leaflet tile display.
   - **Critical Rule**: EPSG:3857 is NEVER used for distance, area, cell size, or downscaling calculations.
