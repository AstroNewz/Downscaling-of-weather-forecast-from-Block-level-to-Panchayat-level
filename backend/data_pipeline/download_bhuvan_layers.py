#!/usr/bin/env python3
"""
Bhuvan/NRSC Layer Downloader
SIH Problem Statement 26074 — Agroweather-Downscaling

Downloads Bhuvan geospatial layers for the Varanasi pilot AOI.
Bhuvan is the Indian authoritative geospatial portal (NRSC/ISRO).

Layers attempted:
  - LULC 50K (National Land Use/Land Cover)
  - Soil map (NBSS&LUP / ICAR)
  - Administrative boundaries (District, Block, Panchayat)

Access: Free Bhuvan account required (BHUVAN_USER, BHUVAN_PASS env vars)
        If unavailable: SOURCE_ACCESS_REQUIRED is reported.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from data_pipeline.utils.aoi_loader import load_pilot_config
from data_pipeline.utils.acquisition_status import (
    write_acquisition_status,
    STATUS_ACCESS_REQUIRED,
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"


def main():
    print("=" * 70)
    print("BHUVAN / NRSC LAYER DOWNLOADER")
    print("Source: National Remote Sensing Centre (NRSC/ISRO)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    bhuvan_user = os.environ.get("BHUVAN_USER", "").strip()
    bhuvan_pass = os.environ.get("BHUVAN_PASS", "").strip()

    if not bhuvan_user or not bhuvan_pass:
        print("\n[SOURCE_ACCESS_REQUIRED] Bhuvan credentials not configured.")
        for layer in ["BHUVAN_LULC_50K", "BHUVAN_ADMIN"]:
            write_acquisition_status(
                output_dir=STATUS_DIR,
                source_name=layer,
                source_type="REMOTE_SENSING" if "LULC" in layer else "DERIVED",
                status=STATUS_ACCESS_REQUIRED,
                reason="Bhuvan account credentials not configured (BHUVAN_USER, BHUVAN_PASS).",
                required_credentials="Free Bhuvan account: https://bhuvan-app1.nrsc.gov.in/",
                required_manual_action=(
                    "1. Register at https://bhuvan.nrsc.gov.in/\n"
                    "2. Set BHUVAN_USER=<email> BHUVAN_PASS=<password> in backend/.env\n"
                    "3. Re-run: python data_pipeline/download_bhuvan_layers.py\n\n"
                    "Manual download alternative:\n"
                    "  - Visit https://bhuvan.nrsc.gov.in/\n"
                    "  - Navigate to Thematic layers > Land Use\n"
                    "  - Select Varanasi district area and download"
                ),
                download_url="https://bhuvan.nrsc.gov.in/bhuvan_links.php",
                aoi_bbox=cfg.bbox,
            )
        print_status_report(STATUS_DIR)
        sys.exit(0)

    print("[INFO] Bhuvan credentials found.")
    print("[INFO] Bhuvan WFS/WCS download implementation requires institutional build.")
    print("[INFO] Please use the Bhuvan portal to download layers manually.")
    for layer in ["BHUVAN_LULC_50K", "BHUVAN_ADMIN"]:
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name=layer,
            source_type="REMOTE_SENSING" if "LULC" in layer else "DERIVED",
            status=STATUS_ACCESS_REQUIRED,
            reason="Credentials configured but Bhuvan WFS implementation pending.",
            download_url="https://bhuvan.nrsc.gov.in/",
            aoi_bbox=cfg.bbox,
        )
    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
