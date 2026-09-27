# Runbook 01: Downscaling Pipeline Ingestion & Model Execution Failure
**System**: SIH 26074 Panchayat Agro-Meteorological Advisory Platform  
**Target SLA**: < 15 minutes recovery for morning 06:00 IST advisory run  
**Severity**: P1 - High (Blocks issuance of 1-km downscaled forecasts and advisories)

---

## 1. Trigger Conditions
- IMD Open Data API / GFS numerical weather forecast ingestion returns HTTP 5xx, timeout (>30s), or corrupt NetCDF/GRIB2 payload.
- Python ML downscaling worker (`celery_worker` / `fastapi_pipeline`) fails with exit code 1 or OOM error during raster reprojection.
- Database (`PostGIS`) write fails when storing 1-km grid cell inferencing outputs.

---

## 2. Immediate Triage (< 5 Minutes)

### Step 2.1: Check Service Health
```bash
# Verify backend API container status
docker ps --filter "name=agrometeo-api" --filter "name=celery-worker"

# Inspect latest pipeline execution logs
docker logs --tail 150 -f agrometeo-pipeline
```

### Step 2.2: Identify Failure Stage
1. **Stage 1: IMD Ingestion**: Check if raw block forecast exists in `/data/raw/imd/<YYYY-MM-DD>/block_forecast.json`.
2. **Stage 2: Static Raster Alignment**: Verify DEM (SRTM), Slope, Aspect, and Sentinel-2 Cropland rasters are present in `/data/static/rasters/`.
3. **Stage 3: ML Inference**: Inspect `/logs/downscaling_xgb.log` for CUDA or CPU memory exhaustion.
4. **Stage 4: Advisory Generation**: Verify rule engine inputs in `/data/processed/panchayat_weather.json`.

---

## 3. Mitigation & Fallback Procedures

### Procedure A: Upstream IMD API Unavailable
If IMD/NCMRWF endpoints are unreachable for > 15 minutes:
1. Switch ingestion source to the secondary fallback mirror (ECMWF Open Data 0.1° subset or NCMRWF Unified Model).
   ```bash
   curl -X POST http://localhost:8000/api/v1/pipeline/fallback-source \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"source": "ncmrwf_backup", "force": true}'
   ```
2. If both external sources fail, trigger **Persistence + Climatological Blend Fallback**:
   - Uses previous day's forecast with IMD climatology delta.
   - Automatically sets header badge to `FALLBACK MODE` with transparent disclaimer to extension officers.

### Procedure B: Model Out-of-Memory (OOM)
If 1-km grid inferencing crashes on large state-wide batches:
1. Switch from spatial chunk size `100x100` to `25x25` tiles:
   ```bash
   export DOWNSCALE_CHUNK_SIZE=25
   systemctl restart agrometeo-worker
   ```
2. Run single-panchayat targeted priority queue for high-risk agricultural blocks first.

---

## 4. Verification & Validation
1. Query API health endpoint:
   ```bash
   curl http://localhost:8000/api/v1/health/pipeline
   # Expected response: {"status": "HEALTHY", "active_pipeline": "live", "last_run_timestamp": "..."}
   ```
2. Verify that Maya Bazar Panchayat 1-km cells are populated:
   ```bash
   curl "http://localhost:8000/api/v1/panchayats/p-01/weather"
   ```
3. Check mobile app: Ensure Live badge turns green and advisories render without error.

---

## 5. Post-Incident Review
- Log incident in `/audit/incident_log.json` with Root Cause Analysis (RCA).
- Notify District Agricultural Officer (DAO) if advisories were delayed beyond 07:30 IST.
