# Runbook 02: Input Data Quality Degradation & Missing Feature Handling
**System**: SIH 26074 Panchayat Agro-Meteorological Advisory Platform  
**Target SLA**: Immediate automated mitigation upon ingestion validation failure  
**Severity**: P2 - Moderate to High (Degrades precision of 1-km downscaled temperatures)

---

## 1. Trigger Conditions
- Missing or corrupted Sentinel-2 Cropland NDVI rasters due to excessive cloud cover or cloud-masking errors.
- Automatic Weather Station (AWS) telemetric sensor drift (> 3.5°C anomaly compared to spatial nearest neighbors).
- Digital Elevation Model (DEM) nodata voids or projection CRS mismatch (EPSG:4326 vs UTM 44N).
- Extreme temperature anomalies outside meteorological physical bounds (< -5°C or > 52°C for Indo-Gangetic Plains).

---

## 2. Automated Quality Gates (Data Ingestion Sanity Engine)

```text
Incoming Data Stream
       │
       ├──> [Check 1: Physical Bounds (-5°C <= T <= 52°C)] ──── Fail ──> Quarantine & Flag
       │
       ├──> [Check 2: Spatial Neighbor Consistency (Z-score < 3.0)] ── Fail ──> AWS Sensor Anomaly
       │
       └──> [Check 3: Static Raster Integrity (0% NoData in Panchayat Mask)] ── Fail ──> Spatial Imputation
```

---

## 3. Mitigation Procedures

### Procedure A: Cloud-Covered Sentinel-2 Cropland Mask
When high-resolution optical imagery is obscured during the monsoon/Kharif season:
1. Fallback to seasonal baseline **10-day synthetic composite** or Copernicus Global Land Cover (100m resampled to 1km).
2. The pipeline flags the cell feature:
   `cropland_source = "seasonal_climatology_fallback"`.
3. In the mobile app, the cell inspector displays:
   `Cropland Data: Estimated from 10-day composite (Confidence: 88%)`.

### Procedure B: AWS Ground Truth Sensor Failure / Drift
When a ground AWS (e.g. AWS-MayaBazar-01) reports erroneous readings:
1. Isolate the faulty station from the Kalman filter / spatial residual correction loop:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/sensors/quarantine \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"station_id": "AWS-MB-01", "reason": "3.8C drift vs neighbor stations"}'
   ```
2. Re-compute spatial downscaled residuals using inverse distance weighting (IDW) from adjacent operational stations (e.g. AWS-Sohawal, AWS-Bikapur).
3. The system records an entry in the Governance Audit Trail:
   `"Sensor AWS-MB-01 quarantined; fallback interpolation applied"`.

### Procedure C: Digital Elevation Model (DEM) Reprojection Error
1. Verify coordinate reference system alignment:
   ```bash
   gdalinfo /data/static/rasters/dem_ayodhya_1km.tif | grep "Coordinate System"
   ```
2. If CRS misaligned, execute automated reprojection:
   ```bash
   gdalwarp -t_srs EPSG:4326 -r bilinear /data/static/dem_raw.tif /data/static/rasters/dem_ayodhya_1km.tif
   ```

---

## 4. Verification & Recovery
- Run validation test suite:
  ```bash
  python -m pytest tests/test_data_sanity.py
  ```
- Confirm in Mobile App:
  Navigate to **Governance > Model Provenance**; ensure "Input Data Quality" reports `PASSED` and "Ground Sensor Health" displays operational telemetry.
