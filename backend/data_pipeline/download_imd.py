#!/usr/bin/env python3
"""
IMD AWS / Station Data Downloader
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : India Meteorological Department (IMD)
Type   : OBSERVATION  (real station measurements — NOT reanalysis)
Access : Restricted — requires IMD data sharing agreement

RULE: If IMD access is not configured, this script emits
      SOURCE_ACCESS_REQUIRED and exits cleanly.
      It NEVER fabricates station observations.

Manual Access Steps:
  1. Visit https://www.imd.gov.in/pages/services_data.php
  2. Register for IMD data services (institutional login required)
  3. Request access to AWS historical data for Varanasi district
  4. Configure IMD_FTP_HOST, IMD_FTP_USER, IMD_FTP_PASS in .env
  5. Re-run this script after credentials are configured

Expected output files (when access is available):
  backend/data/raw/india/pilot/imd_aws_varanasi_YYYYMM.csv
  backend/data/raw/india/pilot/imd_aws_varanasi_YYYYMM.csv.provenance.json
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Resolve backend root
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from data_pipeline.utils.aoi_loader import load_pilot_config
from data_pipeline.utils.acquisition_status import (
    write_acquisition_status,
    STATUS_ACCESS_REQUIRED,
    STATUS_SUCCESS,
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"


def check_imd_credentials() -> tuple[bool, str]:
    """
    Checks whether IMD FTP/API credentials are configured.
    Returns (credentials_present: bool, reason: str).
    """
    imd_host = os.environ.get("IMD_FTP_HOST", "").strip()
    imd_user = os.environ.get("IMD_FTP_USER", "").strip()
    imd_pass = os.environ.get("IMD_FTP_PASS", "").strip()
    imd_api_key = os.environ.get("IMD_API_KEY", "").strip()

    if imd_api_key and imd_api_key != "":
        return True, f"IMD_API_KEY configured"
    if imd_host and imd_user and imd_pass:
        return True, f"IMD FTP credentials configured for {imd_host}"
    return False, "No IMD credentials found in environment (IMD_FTP_HOST/USER/PASS or IMD_API_KEY)"


def main():
    print("=" * 70)
    print("IMD AWS STATION DATA DOWNLOADER")
    print("Source type: OBSERVATION")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    has_creds, reason = check_imd_credentials()

    if not has_creds:
        print(f"\n[SOURCE_ACCESS_REQUIRED] {reason}")
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="IMD_AWS_STATION",
            source_type="OBSERVATION",
            status=STATUS_ACCESS_REQUIRED,
            reason=reason,
            required_credentials=(
                "IMD data sharing agreement required. "
                "Environment variables: IMD_FTP_HOST, IMD_FTP_USER, IMD_FTP_PASS "
                "or IMD_API_KEY"
            ),
            required_manual_action=(
                "1. Visit https://www.imd.gov.in/pages/services_data.php\n"
                "2. Register for IMD data services (institutional email required)\n"
                "3. Request access to Automatic Weather Station (AWS) historical data\n"
                "   for Varanasi district, Uttar Pradesh\n"
                "4. Configure credentials in backend/.env:\n"
                "   IMD_FTP_HOST=<host>  IMD_FTP_USER=<user>  IMD_FTP_PASS=<pass>\n"
                "5. Re-run: python data_pipeline/download_imd.py"
            ),
            download_instructions=(
                "IMD AWS data for Varanasi district.\n"
                "Stations: AWS_BHU_001 (25.2677N, 82.9913E), "
                "AWS_BABATPUR_002 (25.4520N, 82.8590E)\n"
                f"Period: {cfg.weather_start_date} to {cfg.weather_end_date}\n"
                "Variables: temperature, humidity, precipitation, wind speed/direction"
            ),
            expected_file_format="CSV with columns: station_id, datetime, temp_c, humidity_pct, "
                                 "rainfall_mm, wind_speed_kmh, wind_direction_deg",
            download_url="https://www.imd.gov.in/pages/services_data.php",
            aoi_bbox=cfg.bbox,
            temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
        )
        print("\n[INFO] data_acquisition_status.json updated.")
        print("[INFO] No data has been fabricated or substituted.")
        print_status_report(STATUS_DIR)
        sys.exit(0)   # Clean exit — not an error

    # --- Credentials present: attempt download ---
    print(f"[INFO] {reason}")
    print("[INFO] IMD download not yet implemented in open-source build.")
    print("[INFO] Please implement FTP/API logic using your institutional credentials.")
    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="IMD_AWS_STATION",
        source_type="OBSERVATION",
        status=STATUS_ACCESS_REQUIRED,
        reason="Credentials configured but IMD download implementation pending institutional build.",
        download_url="https://www.imd.gov.in/pages/services_data.php",
        aoi_bbox=cfg.bbox,
        temporal_range=(cfg.weather_start_date, cfg.weather_end_date),
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
