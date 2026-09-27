#!/usr/bin/env python3
"""
ERA5-Land Reanalysis Downloader — Higher-Resolution Reference
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : ECMWF ERA5-Land via Copernicus CDS
Type   : REANALYSIS (~9km / 0.1°) — NOT a station observation
Access : Same CDS credentials as ERA5 (~/.cdsapirc)

SCIENTIFIC RULE:
  ERA5-Land may be used as the reference temperature ONLY IF:
    1. No IMD station observations are available (SOURCE_ACCESS_REQUIRED)
    2. ERA5 (coarse ~31km) is used as the coarse input
    3. ERA5-Land and ERA5 are clearly labelled as DIFFERENT datasets
    4. The methodology section explicitly states this is REANALYSIS-to-REANALYSIS
       downscaling, NOT observation-validated downscaling.

  If ERA5 is the coarse input and ERA5-Land is the reference:
    target = era5_land_temp - era5_temp
  This is physically valid because ERA5-Land resolves finer terrain features,
  but it does NOT substitute for actual station validation.

Expected output:
  backend/data/raw/india/pilot/era5land_varanasi_YYYY_MM.nc
  backend/data/raw/india/pilot/era5land_varanasi_YYYY_MM.nc.provenance.json
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from data_pipeline.utils.aoi_loader import load_pilot_config
from data_pipeline.utils.checksum import write_retrieval_sidecar
from data_pipeline.utils.acquisition_status import (
    write_acquisition_status,
    STATUS_ACCESS_REQUIRED,
    STATUS_SUCCESS,
    STATUS_NETWORK_ERROR,
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"

ERA5_LAND_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "surface_pressure",
]

ERA5_LAND_CITATION = (
    "Munoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset "
    "for land applications. Earth System Science Data, 13, 4349-4383. "
    "https://doi.org/10.5194/essd-13-4349-2021"
)


def check_cdsapi() -> tuple[bool, str]:
    try:
        import cdsapi  # noqa
    except ImportError:
        return False, "cdsapi package not installed. Run: pip install cdsapi"
    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        return False, "~/.cdsapirc not found. See https://cds.climate.copernicus.eu/api-how-to"
    return True, "cdsapi installed and ~/.cdsapirc found"


def download_era5land_month(cfg, year: int, month: int, out_dir: Path) -> Path | None:
    import cdsapi
    import calendar

    lat_min, lat_max, lon_min, lon_max = cfg.bbox
    area = [lat_max, lon_min, lat_min, lon_max]  # [N, W, S, E]
    days_in_month = calendar.monthrange(year, month)[1]
    hours = [f"{h:02d}:00" for h in range(24)]
    days = [f"{d:02d}" for d in range(1, days_in_month + 1)]

    # ERA5-Land: 0.1° resolution — ~4x more data than ERA5
    lat_cells = max(1, int((lat_max - lat_min) / 0.1) + 1)
    lon_cells = max(1, int((lon_max - lon_min) / 0.1) + 1)
    approx_mb = 6 * 24 * days_in_month * lat_cells * lon_cells * 4 / 1e6

    out_file = out_dir / f"era5land_varanasi_{year}_{month:02d}.nc"

    print(f"\n{'='*60}")
    print(f"ERA5-LAND DOWNLOAD — PRE-FLIGHT CHECK (Requirement 17)")
    print(f"{'='*60}")
    print(f"  Dataset    : ERA5-Land Hourly Reanalysis")
    print(f"  Source type: REANALYSIS (NOT OBSERVATION)")
    print(f"  Role       : Higher-resolution reference (if IMD unavailable)")
    print(f"  AOI bbox   : lat {lat_min}–{lat_max}, lon {lon_min}–{lon_max}")
    print(f"  Period     : {year}-{month:02d}-01 to {year}-{month:02d}-{days_in_month:02d}")
    print(f"  Resolution : 0.1° (~9 km)")
    print(f"  Grid cells : {lat_cells} lat × {lon_cells} lon")
    print(f"  Est. volume: ~{approx_mb:.1f} MB")
    print(f"  Output     : {out_file}")
    print(f"{'='*60}")

    try:
        c = cdsapi.Client(quiet=True)
        c.retrieve(
            "reanalysis-era5-land",
            {
                "variable": ERA5_LAND_VARIABLES,
                "year": str(year),
                "month": f"{month:02d}",
                "day": days,
                "time": hours,
                "area": area,
                "format": "netcdf",
            },
            str(out_file),
        )
        print(f"[SUCCESS] Downloaded: {out_file}")
        return out_file
    except Exception as e:
        print(f"[ERROR] ERA5-Land download failed for {year}-{month:02d}: {e}")
        return None


def main():
    print("=" * 70)
    print("ERA5-LAND REANALYSIS DOWNLOADER — HIGH-RESOLUTION REFERENCE")
    print("Source type: REANALYSIS (NOT a station observation)")
    print("Role: Reference temperature (only if IMD station data unavailable)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    available, reason = check_cdsapi()
    if not available:
        print(f"\n[SOURCE_ACCESS_REQUIRED] {reason}")
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="ERA5_LAND",
            source_type="REANALYSIS",
            status=STATUS_ACCESS_REQUIRED,
            reason=reason,
            required_credentials="Same CDS credentials as ERA5. See download_era5.py for setup.",
            download_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land",
            aoi_bbox=cfg.bbox,
            temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
            expected_volume_mb=200.0,
        )
        print_status_report(STATUS_DIR)
        sys.exit(0)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat(cfg.weather_start_date)
    end = date.fromisoformat(cfg.weather_end_date)

    months = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    files_written = []
    for year, month in months:
        out_file = download_era5land_month(cfg, year, month, RAW_DIR)
        if out_file:
            write_retrieval_sidecar(
                filepath=out_file,
                source_name="ERA5_LAND",
                source_type="REANALYSIS",
                organization="ECMWF / Copernicus",
                dataset_name="ERA5-Land Hourly Reanalysis",
                download_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land",
                license_str="Copernicus Climate Change Service (C3S) License",
                version=f"{year}-{month:02d}",
                variables=ERA5_LAND_VARIABLES,
                spatial_resolution="0.1 degrees (~9 km)",
                temporal_resolution="hourly",
                coverage=f"Varanasi pilot bbox {cfg.bbox}",
                citation=ERA5_LAND_CITATION,
                notes=(
                    "SOURCE TYPE: REANALYSIS. "
                    "Used as higher-resolution reference ONLY when IMD station data is unavailable. "
                    "This is REANALYSIS-to-REANALYSIS comparison — not station validation. "
                    "Must be labelled as such in all reports."
                ),
            )
            files_written.append(str(out_file))

    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="ERA5_LAND",
        source_type="REANALYSIS",
        status=STATUS_SUCCESS if files_written else STATUS_NETWORK_ERROR,
        reason=f"Downloaded {len(files_written)} month(s) successfully.",
        files_written=files_written,
        aoi_bbox=cfg.bbox,
        temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
    )
    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
