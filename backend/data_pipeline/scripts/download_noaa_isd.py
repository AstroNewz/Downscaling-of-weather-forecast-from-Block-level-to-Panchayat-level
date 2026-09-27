#!/usr/bin/env python3
"""
NOAA ISD Lite Downloader — Station Observation Reference
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : NOAA Integrated Surface Dataset (ISD) Lite
         https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/
Type   : OBSERVATION — real surface weather station measurements
License: NOAA public domain (U.S. Government data)
Access : No credentials required — open HTTP download

STATION:
  Name     : Varanasi (Babatpur) Airport
  ICAO     : VIBN
  WMO ID   : 42360
  USAF/WBAN: 423600-99999
  Latitude : 25.452°N
  Longitude: 82.859°E
  Elevation: 76 m
  Note     : Corresponds to AWS_BABATPUR_002 in india_pilot.yaml

WHY THIS STATION:
  - Located within the Varanasi pilot AOI
  - NOAA ISD provides real hourly observations
  - No credentials required
  - Real OBSERVATION data — not reanalysis, not fabricated
  - Serves as the independent reference for the temperature residual target

ISD LITE FORMAT (fixed-width):
  Col 1: Year (4 chars)
  Col 2: Month (2 chars)
  Col 3: Day (2 chars)
  Col 4: Hour (2 chars) — UTC
  Col 5: Air temperature (tenths °C, -9999 = missing)
  Col 6: Dew point temperature (tenths °C, -9999 = missing)
  Col 7: Sea level pressure (tenths hPa, -9999 = missing)
  Col 8: Wind direction (degrees, -9999 = missing)
  Col 9: Wind speed (tenths m/s, -9999 = missing)
  Col 10: Total sky cover code (0-9, -9999 = missing)
  Col 11: One-hour liquid precipitation (tenths mm, -9999 = missing)
  Col 12: Six-hour liquid precipitation (tenths mm, -9999 = missing)

Expected output:
  data/raw/india/pilot/noaa_isd_babatpur_423600_2024.json
  data/raw/india/pilot/noaa_isd_babatpur_423600_2024.json.provenance.json
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
MANIFEST_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Pilot period
START_DATE = "2024-06-01"
END_DATE   = "2024-08-31"
START_MONTH = 6
END_MONTH   = 8

# Station constants
STATION_ID   = "NOAA_ISD_423600"
STATION_NAME = "Varanasi (Babatpur) Airport"
STATION_ICAO = "VIBN"
STATION_WMO  = "42360"
STATION_LAT  = 25.452
STATION_LON  = 82.859
STATION_ELEV = 76.0  # metres
USAF_WBAN    = "423600-99999"
ISD_YEAR     = 2024

# Cloud cover code → fraction mapping (WMO code table 2700)
SKY_COVER_MAP = {
    0: 0.00,   # Clear
    1: 0.10,   # Few
    2: 0.25,   # Few
    3: 0.40,   # Scattered
    4: 0.50,   # Scattered
    5: 0.62,   # Broken
    6: 0.75,   # Broken
    7: 0.87,   # Broken
    8: 1.00,   # Overcast
    9: None,   # Sky obscured
}

NOAA_CITATION = (
    "Smith, A. et al. (2011). The Integrated Surface Database: Recent Developments "
    "and Partnerships. Bull. Amer. Meteor. Soc., 92, 704-708. "
    "https://doi.org/10.1175/2011BAMS3015.1. "
    "Data: NOAA National Centers for Environmental Information (NCEI)."
)

SSL_CTX = ssl._create_unverified_context()


def download_isd_gz(year: int) -> bytes | None:
    """Downloads ISD Lite gzip file for given station and year."""
    url = (f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/{year}/"
           f"{USAF_WBAN}-{year}.gz")
    print(f"  Downloading: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SIH26074-Pilot/1.0"})
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
            return r.read()
    except urllib.request.HTTPError as e:
        print(f"  HTTP {e.code}: {e.reason}")
        # Try alternate WBAN format
        url2 = (f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/{year}/"
                f"423600-99999-{year}.gz")
        print(f"  Trying alternate URL: {url2}")
        try:
            req2 = urllib.request.Request(url2, headers={"User-Agent": "SIH26074-Pilot/1.0"})
            with urllib.request.urlopen(req2, timeout=60, context=SSL_CTX) as r2:
                return r2.read()
        except Exception as e2:
            print(f"  Alternate URL also failed: {e2}")
            return None
    except Exception as e:
        print(f"  Download failed: {e}")
        return None


def parse_isd_lite(raw_gz: bytes) -> list[dict]:
    """Parses ISD Lite fixed-width format into list of observation records."""
    records = []
    with gzip.open(io.BytesIO(raw_gz), "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 12:
                continue
            try:
                year  = int(parts[0])
                month = int(parts[1])
                day   = int(parts[2])
                hour  = int(parts[3])
            except ValueError:
                continue

            # Filter to pilot period
            if month < START_MONTH or month > END_MONTH:
                continue

            def decode(raw_str: str, scale: float) -> float | None:
                val = int(raw_str)
                if val == -9999:
                    return None
                return round(val * scale, 4)

            temp_c      = decode(parts[4], 0.1)   # tenths°C → °C
            dew_c       = decode(parts[5], 0.1)   # tenths°C → °C
            pressure_hpa = decode(parts[6], 0.1)  # tenths hPa → hPa
            wind_dir    = decode(parts[7], 1.0)   # degrees
            wind_mps    = decode(parts[8], 0.1)   # tenths m/s → m/s
            sky_code_raw = int(parts[9])
            sky_code    = None if sky_code_raw == -9999 else sky_code_raw
            precip_1h   = decode(parts[10], 0.1)  # tenths mm → mm
            precip_6h   = decode(parts[11], 0.1)  # tenths mm → mm

            # Cloud cover from sky code
            cloud_fraction = SKY_COVER_MAP.get(sky_code) if sky_code is not None else None
            cloud_pct = round(cloud_fraction * 100, 1) if cloud_fraction is not None else None

            # Relative humidity from temp + dewpoint (Magnus formula)
            rh_pct = None
            if temp_c is not None and dew_c is not None:
                # Magnus formula approximation
                a, b = 17.625, 243.04
                import math
                gamma_obs = (a * dew_c) / (b + dew_c)
                gamma_sat = (a * temp_c) / (b + temp_c)
                rh_pct = round(100.0 * math.exp(gamma_obs - gamma_sat), 1)
                rh_pct = max(0.0, min(100.0, rh_pct))  # physical clamp

            # UTC timestamp
            ts_utc = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00+00:00"

            records.append({
                "source_id": STATION_ID,
                "source_type": "OBSERVATION",
                "source_dataset": "NOAA ISD Lite",
                "station_name": STATION_NAME,
                "station_icao": STATION_ICAO,
                "station_wmo": STATION_WMO,
                "usaf_wban": USAF_WBAN,
                "timestamp_utc": ts_utc,
                "latitude": STATION_LAT,
                "longitude": STATION_LON,
                "elevation_m": STATION_ELEV,
                # Canonical weather fields
                "temperature_2m_c": temp_c,
                "dewpoint_2m_c": dew_c,
                "relative_humidity_pct": rh_pct,
                "precipitation_mm": precip_1h,     # 1-hour total
                "precipitation_6h_mm": precip_6h,  # 6-hour total
                "wind_speed_mps": wind_mps,
                "wind_direction_deg": wind_dir,
                "cloud_cover_pct": cloud_pct,
                "cloud_cover_code": sky_code,
                "surface_pressure_hpa": pressure_hpa,
                # Quality flag (pre-validation)
                "quality_flag": "PENDING_QC",
            })

    return records


def main():
    print("=" * 70)
    print("NOAA ISD LITE — VARANASI BABATPUR AIRPORT OBSERVATIONS")
    print("Source type: OBSERVATION (real station measurements)")
    print(f"Station    : {STATION_NAME} (WMO {STATION_WMO}, ICAO {STATION_ICAO})")
    print(f"Location   : {STATION_LAT}°N, {STATION_LON}°E, {STATION_ELEV}m")
    print(f"Period     : {START_DATE} to {END_DATE}")
    print("=" * 70)

    print(f"\n[DOWNLOAD] Year {ISD_YEAR}...")
    raw_gz = download_isd_gz(ISD_YEAR)

    if raw_gz is None:
        print("\n[SOURCE_ACCESS_REQUIRED OR NETWORK_ERROR]")
        print("NOAA ISD data for station 423600 could not be downloaded.")
        print("This may mean:")
        print("  1. The station ID is wrong for 2024 data")
        print("  2. Network connectivity issue")
        print("  3. The station file doesn't exist for 2024")

        # Update status
        status_file = MANIFEST_DIR / "data_acquisition_status.json"
        with open(status_file) as f:
            status = json.load(f)
        status["sources"]["NOAA_ISD_BABATPUR"] = {
            "source_type": "OBSERVATION",
            "status": "NETWORK_ERROR",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "reason": "ISD Lite gzip download failed for station 423600-99999 year 2024",
            "files": [],
            "note": "REAL_REFERENCE_DATA_REQUIRED — without observation data, residual target cannot be constructed",
        }
        status["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)
        sys.exit(1)

    print(f"  Downloaded {len(raw_gz):,} bytes (gzip compressed)")

    print("\n[PARSE] Decoding ISD Lite fixed-width format...")
    records = parse_isd_lite(raw_gz)

    if not records:
        print("[WARNING] No records found for pilot period. Check station coverage.")
        sys.exit(1)

    print(f"  Parsed {len(records):,} hourly records for {START_DATE} → {END_DATE}")

    # Count non-null temperatures (key QC metric)
    temps = [r["temperature_2m_c"] for r in records if r["temperature_2m_c"] is not None]
    missing_temp = len(records) - len(temps)
    print(f"  Temperature observations: {len(temps):,}/{len(records):,} "
          f"({100*missing_temp/len(records):.1f}% missing)")

    # Write output
    out_file = RAW_DIR / f"noaa_isd_babatpur_423600_{ISD_YEAR}.json"
    output = {
        "dataset": "NOAA Integrated Surface Dataset (ISD) Lite",
        "source_type": "OBSERVATION",
        "source_id": STATION_ID,
        "source_name": "NOAA_ISD_BABATPUR",
        "provider": "NOAA National Centers for Environmental Information (NCEI)",
        "license": "Public domain (U.S. Government data, no restrictions)",
        "citation": NOAA_CITATION,
        "station": {
            "name": STATION_NAME,
            "icao": STATION_ICAO,
            "wmo_id": STATION_WMO,
            "usaf_wban": USAF_WBAN,
            "latitude": STATION_LAT,
            "longitude": STATION_LON,
            "elevation_m": STATION_ELEV,
        },
        "spatial_resolution": "point station",
        "temporal_resolution": "hourly",
        "time_start": START_DATE,
        "time_end": END_DATE,
        "timezone": "UTC",
        "record_count": len(records),
        "temperature_observations": len(temps),
        "missing_temperature_pct": round(100 * missing_temp / len(records), 2),
        "variable_units": {
            "temperature_2m_c": "degC",
            "dewpoint_2m_c": "degC",
            "relative_humidity_pct": "% (derived via Magnus formula)",
            "precipitation_mm": "mm (1-hour total)",
            "wind_speed_mps": "m/s",
            "wind_direction_deg": "degrees (0=North)",
            "cloud_cover_pct": "% (from WMO sky cover code)",
            "surface_pressure_hpa": "hPa (sea level pressure)",
        },
        "important_note": (
            "CLASSIFICATION: OBSERVATION. "
            "These are real surface weather station measurements from Babatpur Airport. "
            "This station corresponds to AWS_BABATPUR_002 in the project configuration. "
            "This dataset is used as the INDEPENDENT REFERENCE temperature. "
            "It must NOT be the same source as the coarse input (which is ERA5/REANALYSIS)."
        ),
        "records": records,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    # SHA-256
    h = hashlib.sha256()
    with open(out_file, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    sha = h.hexdigest()

    prov = {
        "source_name": "NOAA_ISD_BABATPUR",
        "source_type": "OBSERVATION",
        "organization": "NOAA NCEI",
        "dataset_name": "NOAA Integrated Surface Dataset (ISD) Lite",
        "download_url": (
            f"https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/{ISD_YEAR}/"
            f"{USAF_WBAN}-{ISD_YEAR}.gz"
        ),
        "license": "Public domain (NOAA/U.S. Government)",
        "version": f"ISD Lite {ISD_YEAR}",
        "station_name": STATION_NAME,
        "station_icao": STATION_ICAO,
        "station_wmo": STATION_WMO,
        "station_lat": STATION_LAT,
        "station_lon": STATION_LON,
        "station_elev_m": STATION_ELEV,
        "variables": [
            "temperature_2m_c", "dewpoint_2m_c", "relative_humidity_pct",
            "precipitation_mm", "wind_speed_mps", "wind_direction_deg",
            "cloud_cover_pct", "surface_pressure_hpa",
        ],
        "spatial_resolution": "point station",
        "temporal_resolution": "hourly",
        "coverage": f"{STATION_NAME}: {STATION_LAT}°N, {STATION_LON}°E",
        "time_start": START_DATE,
        "time_end": END_DATE,
        "citation": NOAA_CITATION,
        "sha256_checksum": sha,
        "file_path": str(out_file.resolve()),
        "file_size_bytes": out_file.stat().st_size,
        "record_count": len(records),
        "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Varanasi Babatpur Airport (VIBN). "
            "Corresponds to project AWS_BABATPUR_002. "
            "Real station OBSERVATION data — not reanalysis, not fabricated. "
            "Used as the independent reference for the temperature residual target. "
            "IST = UTC + 05:30."
        ),
    }

    prov_file = Path(str(out_file) + ".provenance.json")
    with open(prov_file, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)

    # Update acquisition status
    status_file = MANIFEST_DIR / "data_acquisition_status.json"
    with open(status_file) as f:
        status = json.load(f)
    status["sources"]["NOAA_ISD_BABATPUR"] = {
        "source_type": "OBSERVATION",
        "status": "DOWNLOADED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "temperature_obs": len(temps),
        "missing_temp_pct": round(100 * missing_temp / len(records), 2),
        "size_bytes": out_file.stat().st_size,
        "sha256": sha,
        "files": [str(out_file.resolve())],
        "note": (
            "Varanasi Babatpur Airport NOAA ISD Lite. OBSERVATION. "
            "Independent reference for temperature residual target."
        ),
    }
    status["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)

    print(f"\n{'='*70}")
    print(f"[SUCCESS] NOAA ISD download complete")
    print(f"  Records   : {len(records):,} hourly observations")
    print(f"  Temp obs  : {len(temps):,} ({100*missing_temp/len(records):.1f}% missing)")
    print(f"  File      : {out_file.name} ({out_file.stat().st_size/1e6:.1f} MB)")
    print(f"  SHA-256   : {sha[:32]}...")
    print(f"  Type      : OBSERVATION (real station measurements)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
