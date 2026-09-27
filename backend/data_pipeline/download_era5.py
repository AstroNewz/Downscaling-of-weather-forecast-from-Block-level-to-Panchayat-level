#!/usr/bin/env python3
"""
ERA5 Reanalysis Downloader — Coarse Weather Input
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : ECMWF ERA5 via Copernicus Climate Data Store (CDS)
Type   : REANALYSIS (NOT a station observation — must never be labelled OBSERVATION)
Access : Free CDS account required; ~/.cdsapirc must be configured

SCIENTIFIC RULE: ERA5 is the COARSE INPUT to the downscaling model.
                 It must NOT simultaneously be used as the independent
                 reference/validation temperature. That would cause leakage.

Target variables for Varanasi pilot:
  - 2m temperature (t2m)
  - 2m dewpoint temperature (d2m)
  - 10m u/v wind components (u10, v10)
  - Total precipitation (tp)
  - Surface pressure (sp)
  - Total cloud cover (tcc)

Setup instructions if ~/.cdsapirc is missing:
  1. Register at https://cds.climate.copernicus.eu/
  2. Go to your profile and copy your UID and API key
  3. Create ~/.cdsapirc with:
       url: https://cds.climate.copernicus.eu/api/v2
       key: <UID>:<API_KEY>
       verify: 0
  4. pip install cdsapi
  5. Re-run this script

Expected output:
  backend/data/raw/india/pilot/era5_varanasi_YYYY_MM.nc
  backend/data/raw/india/pilot/era5_varanasi_YYYY_MM.nc.provenance.json
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from datetime import datetime, date

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

ERA5_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "surface_pressure",
    "total_cloud_cover",
]

ERA5_CITATION = (
    "Hersbach, H. et al. (2020). The ERA5 global reanalysis. "
    "Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049. "
    "https://doi.org/10.1002/qj.3803"
)


def check_cdsapi() -> tuple[bool, str]:
    """Returns (available, reason)."""
    try:
        import cdsapi  # noqa: F401
    except ImportError:
        return False, "cdsapi package not installed. Run: pip install cdsapi"

    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        return False, (
            f"~/.cdsapirc not found. Create it with your CDS credentials. "
            f"See: https://cds.climate.copernicus.eu/api-how-to"
        )
    return True, "cdsapi installed and ~/.cdsapirc found"


def download_era5_month(
    cfg,
    year: int,
    month: int,
    out_dir: Path,
) -> Path | None:
    """
    Downloads ERA5 hourly data for one month for the pilot AOI.

    IMPORTANT: Before downloading, prints the exact AOI, period and
    expected approximate volume so the user can verify (requirement 17).

    Returns path to downloaded file, or None on failure.
    """
    import cdsapi

    lat_min, lat_max, lon_min, lon_max = cfg.bbox
    # CDS API expects [north, west, south, east]
    area = [lat_max, lon_min, lat_min, lon_max]

    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    hours = [f"{h:02d}:00" for h in range(24)]
    days = [f"{d:02d}" for d in range(1, days_in_month + 1)]

    # Approximate: 7 variables × 24h × days × ~0.25° grid cells in bbox
    lat_cells = max(1, int((lat_max - lat_min) / 0.25) + 1)
    lon_cells = max(1, int((lon_max - lon_min) / 0.25) + 1)
    approx_records = 7 * 24 * days_in_month * lat_cells * lon_cells
    approx_mb = approx_records * 4 / 1e6  # float32

    out_file = out_dir / f"era5_varanasi_{year}_{month:02d}.nc"

    print(f"\n{'='*60}")
    print(f"ERA5 DOWNLOAD — PRE-FLIGHT CHECK (Requirement 17)")
    print(f"{'='*60}")
    print(f"  Dataset    : ERA5 Hourly on Single Levels")
    print(f"  Source type: REANALYSIS (NOT OBSERVATION)")
    print(f"  AOI bbox   : lat {lat_min}–{lat_max}, lon {lon_min}–{lon_max}")
    print(f"  Period     : {year}-{month:02d}-01 to {year}-{month:02d}-{days_in_month:02d}")
    print(f"  Variables  : {ERA5_VARIABLES}")
    print(f"  Grid cells : {lat_cells} lat × {lon_cells} lon @ 0.25°")
    print(f"  Est. volume: ~{approx_mb:.1f} MB")
    print(f"  Output     : {out_file}")
    print(f"{'='*60}")

    try:
        c = cdsapi.Client(quiet=True)
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "variable": ERA5_VARIABLES,
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
        print(f"[ERROR] ERA5 download failed for {year}-{month:02d}: {e}")
        return None


def main():
    print("=" * 70)
    print("ERA5 REANALYSIS DOWNLOADER — COARSE WEATHER INPUT")
    print("Source type: REANALYSIS (NOT a station observation)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    available, reason = check_cdsapi()
    if not available:
        print(f"\n[SOURCE_ACCESS_REQUIRED] {reason}")
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="ERA5",
            source_type="REANALYSIS",
            status=STATUS_ACCESS_REQUIRED,
            reason=reason,
            required_credentials=(
                "Free CDS account and ~/.cdsapirc required. "
                "Register at https://cds.climate.copernicus.eu/"
            ),
            required_manual_action=(
                "1. Register at https://cds.climate.copernicus.eu/\n"
                "2. Accept the Terms of Use for ERA5 dataset\n"
                "3. Go to Profile > API key and copy UID and key\n"
                "4. Create ~/.cdsapirc:\n"
                "   url: https://cds.climate.copernicus.eu/api/v2\n"
                "   key: <UID>:<API_KEY>\n"
                "   verify: 0\n"
                "5. pip install cdsapi\n"
                "6. Re-run: python data_pipeline/download_era5.py"
            ),
            download_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
            aoi_bbox=cfg.bbox,
            temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
            expected_volume_mb=50.0,
        )
        print_status_report(STATUS_DIR)
        sys.exit(0)

    print(f"[INFO] {reason}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    from datetime import date
    start = date.fromisoformat(cfg.weather_start_date)
    end = date.fromisoformat(cfg.weather_end_date)

    # Enumerate year/month combinations in the pilot period
    months = []
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    files_written = []
    errors = []

    for year, month in months:
        out_file = download_era5_month(cfg, year, month, RAW_DIR)
        if out_file:
            sidecar = write_retrieval_sidecar(
                filepath=out_file,
                source_name="ERA5",
                source_type="REANALYSIS",
                organization="ECMWF / Copernicus",
                dataset_name="ERA5 Hourly Reanalysis on Single Levels",
                download_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
                license_str="Copernicus Climate Change Service (C3S) License",
                version=f"{year}-{month:02d}",
                variables=ERA5_VARIABLES,
                spatial_resolution="0.25 degrees (~31 km)",
                temporal_resolution="hourly",
                coverage=f"Varanasi pilot bbox {cfg.bbox}",
                citation=ERA5_CITATION,
                notes=(
                    "SOURCE TYPE: REANALYSIS. This dataset is the COARSE INPUT "
                    "to the downscaling model. It must NOT be used simultaneously "
                    "as the independent reference/validation temperature (leakage prevention)."
                ),
            )
            files_written.append(str(out_file))
        else:
            errors.append(f"{year}-{month:02d}")

    status = STATUS_SUCCESS if not errors else ("PARTIAL" if files_written else STATUS_NETWORK_ERROR)
    reason = (
        f"Downloaded {len(files_written)} month(s) successfully."
        if not errors
        else f"Downloaded {len(files_written)} month(s); failed: {errors}"
    )

    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="ERA5",
        source_type="REANALYSIS",
        status=status,
        reason=reason,
        files_written=files_written,
        aoi_bbox=cfg.bbox,
        temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
        download_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
    )
    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
