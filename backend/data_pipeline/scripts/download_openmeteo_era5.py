#!/usr/bin/env python3
"""
Open-Meteo Historical ERA5 Downloader — Coarse Weather Input
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : Open-Meteo Historical Weather API (https://open-meteo.com/)
         Data model: ERA5 reanalysis from ECMWF via Open-Meteo
Type   : REANALYSIS — NOT a station observation
License: Open-Meteo is free for non-commercial use; data is ERA5 (Copernicus C3S)
Access : No credentials required — open HTTP API

WHY THIS SCRIPT:
  The configured download_era5.py requires ~/.cdsapirc (CDS account).
  That credential is not available in this environment.
  Open-Meteo serves the same ERA5 data via a free, unauthenticated HTTP API.
  This is explicitly documented as a non-silent alternative:
    source_name = OPEN_METEO_ERA5
    source_type = REANALYSIS
    NOT classified as OBSERVATION
    NOT the same as direct CDS ERA5 download

VARIABLES DOWNLOADED (matching feature_schema.json):
  temperature_2m         (°C)   → forecast_temp_min / max / mean
  dewpoint_2m            (°C)   → for humidity derivation
  relative_humidity_2m   (%)    → forecast_humidity_pct
  precipitation          (mm/h) → forecast_rainfall_mm
  wind_speed_10m         (km/h) → convert → forecast_wind_speed_mps
  wind_direction_10m     (°)    → forecast_wind_direction_deg
  cloud_cover            (%)    → forecast_cloud_cover_pct
  surface_pressure       (hPa)  → surface_pressure_hpa

GRID:
  Varanasi pilot AOI: 25.10–25.60°N, 82.70–83.20°E
  Sampling: ~0.25° ERA5 native spacing
  Grid points: 6 (2 lat × 3 lon)

Expected output:
  data/raw/india/pilot/openmeteo_era5_varanasi_2024.json
  data/raw/india/pilot/openmeteo_era5_varanasi_2024.json.provenance.json
"""
from __future__ import annotations

import hashlib
import json
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
MANIFEST_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Pilot config
LAT_MIN, LAT_MAX = 25.10, 25.60
LON_MIN, LON_MAX = 82.70, 83.20
START_DATE = "2024-06-01"
END_DATE = "2024-08-31"

# ERA5 native spacing (~0.25°); sample grid points within pilot AOI
GRID_POINTS = [
    {"id": "era5_25.25_82.75", "lat": 25.25, "lon": 82.75},
    {"id": "era5_25.25_83.00", "lat": 25.25, "lon": 83.00},
    {"id": "era5_25.25_83.25", "lat": 25.25, "lon": 83.25},
    {"id": "era5_25.50_82.75", "lat": 25.50, "lon": 82.75},
    {"id": "era5_25.50_83.00", "lat": 25.50, "lon": 83.00},
    {"id": "era5_25.50_83.25", "lat": 25.50, "lon": 83.25},
]

# Variables to request
HOURLY_VARS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
    "surface_pressure",
]

OPEN_METEO_CITATION = (
    "Open-Meteo contributors (2023). Open-Meteo API. https://open-meteo.com/. "
    "Data source: ERA5 reanalysis by ECMWF / Copernicus Climate Change Service. "
    "Hersbach, H. et al. (2020). ERA5. Q.J.R. Meteorol. Soc. 146, 1999-2049."
)

SSL_CTX = ssl._create_unverified_context()


def fetch_grid_point(lat: float, lon: float, retries: int = 3) -> dict | None:
    """Fetches hourly ERA5 data from Open-Meteo for one grid point."""
    params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
    }
    url = "https://archive.api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SIH26074-Pilot/1.0"})
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"    Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    return None


def records_from_response(point_id: str, lat: float, lon: float, data: dict) -> list[dict]:
    """
    Converts Open-Meteo response to flat list of hourly records.
    Each record is one hour for one grid point.
    Units are converted to canonical project units.
    """
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    records = []

    for i, ts_str in enumerate(times):
        def val(var):
            arr = hourly.get(var, [])
            v = arr[i] if i < len(arr) else None
            return v  # None = missing — never fabricate

        temp_c = val("temperature_2m")           # °C
        dew_c = val("dewpoint_2m")               # °C
        rh_pct = val("relative_humidity_2m")     # %
        precip_mm = val("precipitation")         # mm/h (already mm)
        wind_kmh = val("wind_speed_10m")         # km/h
        wind_dir = val("wind_direction_10m")     # degrees
        cloud_pct = val("cloud_cover")           # %
        pressure_hpa = val("surface_pressure")   # hPa

        # Convert wind km/h → m/s
        wind_mps = round(wind_kmh / 3.6, 3) if wind_kmh is not None else None

        # Convert hPa → Pa for internal storage (consistent with ERA5 CDS native units)
        pressure_pa = round(pressure_hpa * 100, 1) if pressure_hpa is not None else None

        records.append({
            "source_id": "OPEN_METEO_ERA5",
            "source_type": "REANALYSIS",
            "source_dataset": "Open-Meteo Historical (ERA5)",
            "grid_point_id": point_id,
            "timestamp_utc": ts_str + ":00+00:00",  # ISO 8601
            "latitude": lat,
            "longitude": lon,
            # Canonical weather fields
            "temperature_2m_c": temp_c,
            "dewpoint_2m_c": dew_c,
            "relative_humidity_pct": rh_pct,
            "precipitation_mm": precip_mm,
            "wind_speed_mps": wind_mps,
            "wind_speed_kmh_raw": wind_kmh,       # preserve raw
            "wind_direction_deg": wind_dir,
            "cloud_cover_pct": cloud_pct,
            "surface_pressure_hpa": pressure_hpa,
            "surface_pressure_pa": pressure_pa,   # for ERA5 consistency
            # Quality flag (pre-validation placeholder)
            "quality_flag": "PENDING_QC",
        })

    return records


def main():
    print("=" * 70)
    print("OPEN-METEO ERA5 HISTORICAL DOWNLOADER")
    print("Source type: REANALYSIS (Open-Meteo serves ERA5 data)")
    print("NOT OBSERVATION — NOT a station measurement")
    print(f"AOI: {LAT_MIN}–{LAT_MAX}°N, {LON_MIN}–{LON_MAX}°E")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Grid: {len(GRID_POINTS)} points at 0.25° spacing")
    print("=" * 70)

    # Pre-flight check
    print("\n[PRE-FLIGHT CHECK]")
    print(f"  CDS credentials: NOT available → using Open-Meteo alternative")
    print(f"  Source classification: REANALYSIS")
    print(f"  Variables: {HOURLY_VARS}")
    expected_rows = len(GRID_POINTS) * 92 * 24  # 92 days × 24 hours
    expected_mb = expected_rows * 200 / 1e6     # ~200 bytes per JSON record
    print(f"  Expected rows: ~{expected_rows:,}")
    print(f"  Expected size: ~{expected_mb:.0f} MB (JSON)")

    all_records = []
    failed_points = []

    for pt in GRID_POINTS:
        print(f"\n  Fetching {pt['id']} (lat={pt['lat']}, lon={pt['lon']})...")
        data = fetch_grid_point(pt["lat"], pt["lon"])
        if data is None:
            print(f"  [FAIL] {pt['id']} — all retries exhausted")
            failed_points.append(pt["id"])
            continue

        records = records_from_response(pt["id"], pt["lat"], pt["lon"], data)
        all_records.extend(records)
        print(f"  [OK] {len(records):,} hourly records")
        time.sleep(0.5)  # polite rate limiting

    if not all_records:
        print("\n[ERROR] No records acquired. Check network connectivity.")
        sys.exit(1)

    # Write output
    out_file = RAW_DIR / "openmeteo_era5_varanasi_2024.json"
    output = {
        "dataset": "Open-Meteo Historical Weather (ERA5)",
        "source_type": "REANALYSIS",
        "source_name": "OPEN_METEO_ERA5",
        "provider": "Open-Meteo (data: ECMWF ERA5 / Copernicus C3S)",
        "license": (
            "Open-Meteo API: free for non-commercial use "
            "(https://open-meteo.com/en/terms). "
            "ERA5 data: Copernicus Climate Change Service (C3S) License."
        ),
        "citation": OPEN_METEO_CITATION,
        "spatial_resolution": "0.25 degrees (~27 km at this latitude)",
        "temporal_resolution": "hourly",
        "time_start": START_DATE,
        "time_end": END_DATE,
        "timezone": "UTC",
        "aoi": {
            "lat_min": LAT_MIN, "lat_max": LAT_MAX,
            "lon_min": LON_MIN, "lon_max": LON_MAX,
        },
        "grid_points": GRID_POINTS,
        "variables": HOURLY_VARS,
        "variable_units": {
            "temperature_2m_c": "degC",
            "dewpoint_2m_c": "degC",
            "relative_humidity_pct": "%",
            "precipitation_mm": "mm (hourly total)",
            "wind_speed_mps": "m/s (converted from km/h)",
            "wind_direction_deg": "degrees (0=North, 90=East)",
            "cloud_cover_pct": "%",
            "surface_pressure_hpa": "hPa",
            "surface_pressure_pa": "Pa (×100 from hPa)",
        },
        "important_note": (
            "CLASSIFICATION: REANALYSIS. "
            "This dataset is the COARSE INPUT to the downscaling model. "
            "It MUST NOT be used simultaneously as the independent reference "
            "(that would be ERA5-vs-ERA5 leakage). "
            "The independent reference comes from NOAA ISD station observations."
        ),
        "record_count": len(all_records),
        "failed_grid_points": failed_points,
        "records": all_records,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))  # compact JSON

    # SHA-256
    h = hashlib.sha256()
    with open(out_file, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    sha = h.hexdigest()

    prov = {
        "source_name": "OPEN_METEO_ERA5",
        "source_type": "REANALYSIS",
        "organization": "Open-Meteo (ERA5 data: ECMWF / Copernicus C3S)",
        "dataset_name": "Open-Meteo Historical Weather API (ERA5 model)",
        "download_url": "https://archive.api.open-meteo.com/v1/archive",
        "license": "Open-Meteo: free non-commercial; ERA5: Copernicus C3S License",
        "version": f"ERA5 via Open-Meteo API, retrieved {datetime.now(timezone.utc).date()}",
        "variables": HOURLY_VARS,
        "spatial_resolution": "~0.25 degrees (ERA5 native)",
        "temporal_resolution": "hourly",
        "coverage": f"Varanasi pilot AOI {LAT_MIN}–{LAT_MAX}°N, {LON_MIN}–{LON_MAX}°E",
        "time_start": START_DATE,
        "time_end": END_DATE,
        "grid_points": GRID_POINTS,
        "citation": OPEN_METEO_CITATION,
        "sha256_checksum": sha,
        "file_path": str(out_file.resolve()),
        "file_size_bytes": out_file.stat().st_size,
        "record_count": len(all_records),
        "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Alternative to direct CDS ERA5 download (which requires ~/.cdsapirc). "
            "Open-Meteo serves ERA5 data via an open HTTP API. "
            "Classified as REANALYSIS. Used as COARSE INPUT only. "
            "NOAA ISD provides the independent OBSERVATION reference."
        ),
    }

    prov_file = Path(str(out_file) + ".provenance.json")
    with open(prov_file, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)

    # Update acquisition status
    status_file = MANIFEST_DIR / "data_acquisition_status.json"
    with open(status_file) as f:
        status = json.load(f)
    status["sources"]["OPEN_METEO_ERA5"] = {
        "source_type": "REANALYSIS",
        "status": "DOWNLOADED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(all_records),
        "grid_points": len(GRID_POINTS),
        "failed_points": failed_points,
        "size_bytes": out_file.stat().st_size,
        "sha256": sha,
        "files": [str(out_file.resolve())],
        "note": (
            "ERA5 data via Open-Meteo API. Classified as REANALYSIS. "
            "Alternative to CDS ERA5 (SOURCE_ACCESS_REQUIRED for direct CDS). "
            "Coarse input only — not used as reference."
        ),
    }
    status["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)

    print(f"\n{'='*70}")
    print(f"[SUCCESS] Open-Meteo ERA5 download complete")
    print(f"  Records   : {len(all_records):,} hourly observations")
    print(f"  Grid pts  : {len(GRID_POINTS) - len(failed_points)}/{len(GRID_POINTS)} succeeded")
    print(f"  File      : {out_file.name} ({out_file.stat().st_size/1e6:.1f} MB)")
    print(f"  SHA-256   : {sha[:32]}...")
    print(f"  Type      : REANALYSIS")
    print(f"  Period    : {START_DATE} → {END_DATE}")
    if failed_points:
        print(f"  Failed    : {failed_points}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
