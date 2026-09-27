# Satellite Observation Adapter & Spatial Fusion Layer
**SIH Problem Statement 26074 (Weather Downscaling - Task 3)**
*Authoritative Architecture & Scientific Governance Document*

---

## 1. Executive Summary & Architectural Scope

Task 3 establishes the backend **Satellite Observation Adapter** for the Agro-Meteorological Weather Downscaling Platform. This layer ingests authorized, georeferenced satellite-derived meteorological imagery and gridded products, converting them into the canonical `SourceWeatherGrid` abstraction introduced in Task 2.

Through this abstraction, the existing Task 2 `SpatialMaskingService` performs exact polygon-cell intersections against authoritative Gram Panchayat boundaries, deriving independent, Panchayat-specific spatial features (e.g. separating Panchayat A from adjacent Panchayat B) while strictly preserving native sensor resolution and data provenance.

```
Authorized Satellite Feed (GeoTIFF / HDF / In-Memory Grid)
                         │
                         ▼
        ┌───────────────────────────────────┐
        │   SatelliteObservationProvider    │
        │ - CRS & Geotransform Validation   │
        │ - Fail-Closed Guardrails          │
        │ - Freshness Classification        │
        └─────────────────┬─────────────────┘
                         │
                         ▼
                 SourceWeatherGrid
                         │
                         ▼
        ┌───────────────────────────────────┐
        │   Task 2 SpatialMaskingService    │
        │ - Exact Polygon/Grid Intersection │
        │ - Geodesic Fractional Weighting   │
        └───────┬───────────────────┬───────┘
                │                   │
                ▼                   ▼
    ┌───────────────────────┐   ┌───────────────────────┐
    │  Panchayat A Polygon  │   │  Panchayat B Polygon  │
    │  - Cold Convective IR │   │  - Warm Clear Skies   │
    │  - Isolated Features  │   │  - Isolated Features  │
    └───────────────────────┘   └───────────────────────┘
```

---

## 2. Core Scientific Principles & Mandates

### A. Satellite Data is an Observation & Evidence Layer
Satellite products represent top-of-atmosphere radiances, derived brightness temperatures, and retrieval model outputs. They provide empirical spatial evidence of cloud cover, convective development, and moisture fields. They are an **evidence stream**, not an automatic replacement for ground truth or numerical weather predictions (NWP).

### B. Satellite Cloud Information is NOT Automatically Rainfall
Cloud cover or high infrared brightness temperature depressions (cold cloud tops) signify vertical cloud development, but they do **NOT** establish ground-level rainfall. Cloud droplets may be non-precipitating, sub-cloud virga may evaporate precipitation before reaching the surface, or convective cores may be in early pre-rain stages.
- The adapter strictly separates `SATELLITE_CLOUD_MASK` and `SATELLITE_IR_BRIGHTNESS_TEMPERATURE` from precipitation.
- No cloud metric is ever converted or renamed to rainfall.

### C. Satellite Precipitation Estimates are Estimates and Must Retain That Label
Where authorized satellite precipitation products (e.g., INSAT-3D/3DR Hydro-Estimator / HEGG, IMERG) are ingested:
- The variable name in all backend models and schemas is strictly:
  $$\mathbf{satellite\_precipitation\_estimate}$$
- Under no circumstances is this field renamed or surfaced as `observed_rainfall`.
- Ground truth rainfall remains reserved for calibrated automatic weather stations (AWS), rain gauges, and verified surface observations.
- Missing values (`NaN` or `None`) are strictly distinguished from zero rainfall (`0.0 mm`). Missing data is never coerced to zero.

### D. Polygon Masking Preserves Native Resolution Without False Synthesis
Spatial masking computes the exact geometric intersection between administrative polygon boundaries and native sensor pixels.
- If an INSAT-3DR thermal infrared pixel has a native resolution of $4.0\text{ km} \times 4.0\text{ km}$, polygon masking intersects those $16\text{ km}^2$ cells with the Panchayat boundary.
- **Provenance Guardrail**: Spatial masking calculates area-weighted averages across intersecting pixels; it **does NOT synthesize microclimate meteorological resolution finer than the sensor footprint**.
- All payloads retain `native_resolution_km`, `processing_resolution_km`, and the immutable disclaimer:
  > *"Spatial masking intersects native grid cells with administrative boundaries; it does NOT synthesize higher meteorological resolution than the underlying source field."*

### E. Radar Compatibility & Multi-Sensor Fusion Roadmap
Task 3 establishes the base `GriddedObservationProvider` interface. The future architecture supports:
$$\text{Satellite Provider} \longrightarrow \text{SourceWeatherGrid} \longrightarrow \text{Spatial Mask}$$
$$\text{Radar Provider} \longrightarrow \text{SourceWeatherGrid} \longrightarrow \text{Spatial Mask}$$
$$\text{Ground Mesonet} \longrightarrow \text{Point Calibration} \longrightarrow \text{Spatial Fusion}$$
This modular design ensures Doppler Weather Radar (DWR) products can be integrated without modifying the downstream spatial-masking service or advisory engine.

### F. Satellite Observation Freshness Matters
Geostationary and low-Earth-orbit satellite products are time-critical:
- The adapter enforces separate tracking of:
  1. `observation_time`: UTC timestamp of sensor scan acquisition.
  2. `product_valid_time`: UTC timestamp for which retrieval algorithm is valid.
  3. `ingestion_time`: UTC timestamp when local system processed the data.
- Operational latency is categorized against a configurable freshness threshold ($\tau_{\text{freshness}} = 60.0\text{ minutes}$ by default):
  - `LIVE_DATA_AVAILABLE`: $t_{\text{now}} - t_{\text{obs}} \le \tau$
  - `LIVE_DATA_STALE`: $t_{\text{now}} - t_{\text{obs}} > \tau$
  - `LIVE_DATA_UNAVAILABLE`: feed offline, file missing, or network failure.

### G. Missing, Corrupt, and Stale Data Fails Closed
The adapter implements strict fail-closed safety:
- **Missing CRS**: Rejects file immediately; never assumes an arbitrary coordinate reference system.
- **Degenerate Geotransform**: Identity or zero-determinant transforms fail closed.
- **Unverified Geometry**: If boundary policy requires verification (`require_verified=True`), unverified polygons fail closed with `UNVERIFIED_GEOMETRY`.
- **Never Fabricate Data**: Missing satellite fields never trigger silent substitution of Open-Meteo or synthetic fixtures.

### H. No Scientific Accuracy Claim Prior to Independent Validation
No claim of localized Panchayat-level precipitation accuracy is made. All heuristics (e.g. convective cloud-top threshold at $235\text{ K}$) are explicitly documented as configurable exploratory parameters pending multi-season empirical validation against ground networks.

---

## 3. Product Taxonomy

| Taxonomic Key | Physical Variable | Units | Semantics | Estimation Flag |
| :--- | :--- | :--- | :--- | :--- |
| `SATELLITE_CLOUD_MASK` | `cloud_mask` | fraction | Categorical cloud cover ($0=\text{clear}, 1=\text{cloud}$) | Observed/Retrieved |
| `SATELLITE_IR_BRIGHTNESS_TEMPERATURE` | `brightness_temperature_ir` | $\text{K}$ | $10.8\,\mu\text{m} / 12\,\mu\text{m}$ Thermal infrared brightness temp | Radiometric Observation |
| `SATELLITE_PRECIPITATION_ESTIMATE` | `satellite_precipitation_estimate` | $\text{mm}$ or $\text{mm/h}$ | Algorithmic precipitation retrieval (HEGG/IMERG) | **Estimated** |
| `SATELLITE_WATER_VAPOUR` | `water_vapour` | $\text{K}$ or $\%$ | Tropospheric moisture channel ($6.7\,\mu\text{m}$) | Radiometric Observation |
| `SATELLITE_VISIBLE_REFLECTANCE` | `visible_reflectance` | fraction ($0-1$) | Top-of-atmosphere visible channel albedo | Radiometric Observation |

---

## 4. Programmatic API

```python
from app.services.satellite_service import (
    fetch_satellite_observation,
    extract_panchayat_satellite_features,
)
from app.schemas.satellite import SatelliteProductType

# 1. Ingest an authorized GeoTIFF or array
satellite_grid = fetch_satellite_observation(
    product=SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE,
    options={"file_path": "/path/to/insat3dr_tir1.tif"}
)

# 2. Extract Panchayat-specific features (reusing Task 2 SpatialMaskingService)
panchayat_a_features = extract_panchayat_satellite_features(
    panchayat_id="UP_VAR_001_P01",
    satellite_grid=satellite_grid,
    convective_threshold_k=235.0,
)

# 3. Independent extraction for neighboring Panchayat B
panchayat_b_features = extract_panchayat_satellite_features(
    panchayat_id="UP_VAR_001_P02",
    satellite_grid=satellite_grid,
    convective_threshold_k=235.0,
)
```

---

## 5. Verification & Test Summary
The adapter is verified by `tests/test_satellite_observation_adapter.py` across 17 deterministic scenarios:
- GeoTIFF rasterio ingestion and SHA-256 cryptographic provenance tracking.
- Fail-closed rejection of missing CRS and identity/degenerate geotransforms.
- Native resolution preservation ($1.0\text{ km}$ and $4.0\text{ km}$).
- Distinct observation, valid, and ingestion timestamps.
- Operational freshness classification (`LIVE_DATA_AVAILABLE` vs `LIVE_DATA_STALE`).
- Strict satellite precipitation semantics (`satellite_precipitation_estimate`, zero dry preservation, NaN gap retention).
- Neighboring Panchayat A/B independent separation on the same satellite field.
- Boundary-straddling fractional cell overlap.
- Multi-temporal change tracking and trend classification (`COOLING_CONVECTIVE`).
- Complete isolation of test fixtures (`SATELLITE_SYNTHETIC_TEST_FIXTURE`).
