#!/usr/bin/env python3
"""
LULC Downloader — Land Use / Land Cover for Varanasi Pilot
SIH Problem Statement 26074 — Agroweather-Downscaling

Priority 1: Bhuvan LULC 50K (NRSC/ISRO — Indian authoritative)
Priority 2: ESA WorldCover 10m (open access fallback)

RULE: LULC data is used ONLY for spatial feature extraction:
  - cropland_fraction, forest_fraction, urban_fraction, water_fraction, barren_fraction
  - is_agricultural_cropland

LULC data MUST NOT be used to manufacture weather observations.
"""
from __future__ import annotations

import sys
import os
import urllib.request
from pathlib import Path

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
    STATUS_SKIPPED,
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"

ESA_WC_CITATION = (
    "Zanaga, D. et al. (2022). ESA WorldCover 10m 2021 v200. "
    "Zenodo. https://doi.org/10.5281/zenodo.7254221"
)


def try_bhuvan_lulc(cfg) -> bool:
    """
    Attempts Bhuvan LULC WFS download. Requires Bhuvan account credentials.
    Returns True if successful.
    """
    bhuvan_user = os.environ.get("BHUVAN_USER", "").strip()
    bhuvan_pass = os.environ.get("BHUVAN_PASS", "").strip()
    if not bhuvan_user or not bhuvan_pass:
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="BHUVAN_LULC_50K",
            source_type="REMOTE_SENSING",
            status=STATUS_ACCESS_REQUIRED,
            reason="Bhuvan credentials not configured (BHUVAN_USER, BHUVAN_PASS)",
            required_credentials="Free Bhuvan account: https://bhuvan-app1.nrsc.gov.in/bhuvan2d/",
            required_manual_action=(
                "1. Register at https://bhuvan.nrsc.gov.in/\n"
                "2. Set environment variables: BHUVAN_USER=<user> BHUVAN_PASS=<pass>\n"
                "3. Re-run: python data_pipeline/download_lulc.py"
            ),
            download_url="https://bhuvan.nrsc.gov.in/bhuvan_links.php",
            aoi_bbox=cfg.bbox,
        )
        return False
    print("[INFO] Bhuvan credentials found. WFS download not yet implemented — "
          "please download LULC manually from Bhuvan portal.")
    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="BHUVAN_LULC_50K",
        source_type="REMOTE_SENSING",
        status=STATUS_ACCESS_REQUIRED,
        reason="Bhuvan LULC WFS download requires institutional implementation.",
        download_url="https://bhuvan.nrsc.gov.in/bhuvan_links.php",
        aoi_bbox=cfg.bbox,
    )
    return False


def try_esa_worldcover(cfg, out_file: Path) -> bool:
    """
    Attempts ESA WorldCover 10m download for Varanasi region.
    ESA WorldCover is open access (CC BY 4.0).
    Tile for Varanasi region: N24E081 or N24E082 (check exact tile names).
    Returns True if successful.
    """
    lat_min, lat_max, lon_min, lon_max = cfg.bbox

    # ESA WorldCover tile naming: 3-degree tiles, e.g., N24E081
    # Varanasi is around lat 25.3, lon 82.9 → tile N24E081 (covers N24-N27, E81-E84)
    # Using S3 bucket URL from ESA
    tiles_to_try = [
        ("N24E081", "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N24E081_Map.tif"),
    ]

    approx_mb = 50  # WorldCover tiles are ~50MB compressed

    print(f"\n{'='*60}")
    print(f"ESA WORLDCOVER LULC DOWNLOAD — PRE-FLIGHT CHECK (Requirement 17)")
    print(f"{'='*60}")
    print(f"  Dataset    : ESA WorldCover 10m v200 (2021)")
    print(f"  Source type: REMOTE_SENSING")
    print(f"  Role       : LULC fallback (Bhuvan primary unavailable)")
    print(f"  AOI bbox   : lat {lat_min}–{lat_max}, lon {lon_min}–{lon_max}")
    print(f"  Resolution : 10 m")
    print(f"  License    : CC BY 4.0 (open access)")
    print(f"  Est. volume: ~{approx_mb} MB per tile")
    print(f"  Output     : {out_file}")
    print(f"{'='*60}")

    for tile_name, url in tiles_to_try:
        tile_out = out_file.parent / f"esa_worldcover_{tile_name}.tif"
        try:
            print(f"[INFO] Downloading tile {tile_name}...")
            urllib.request.urlretrieve(url, tile_out)
            print(f"[SUCCESS] ESA WorldCover tile downloaded: {tile_out}")
            write_retrieval_sidecar(
                filepath=tile_out,
                source_name="ESA_WORLDCOVER_10M",
                source_type="REMOTE_SENSING",
                organization="ESA / VITO",
                dataset_name="ESA WorldCover 10m v200 (2021)",
                download_url="https://esa-worldcover.org/en",
                license_str="CC BY 4.0",
                version="v200 (2021)",
                variables=["lulc_class"],
                spatial_resolution="10 m",
                temporal_resolution="annual",
                coverage=f"Tile {tile_name} — Varanasi pilot region",
                citation=ESA_WC_CITATION,
                notes=(
                    "LULC SPATIAL DATA ONLY. Fallback for Bhuvan LULC 50K. "
                    "Used for cropland_fraction, forest_fraction, urban_fraction, "
                    "water_fraction, barren_fraction features. "
                    "Must NOT be used to manufacture weather observations."
                ),
            )
            return True
        except Exception as e:
            print(f"[WARNING] ESA WorldCover download failed for {tile_name}: {e}")

    return False


def main():
    print("=" * 70)
    print("LULC DOWNLOADER — Land Use / Land Cover")
    print("Priority 1: Bhuvan LULC 50K (NRSC/ISRO — India authoritative)")
    print("Priority 2: ESA WorldCover 10m (open access fallback)")
    print("Source type: REMOTE_SENSING (NOT weather data)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    out_file = RAW_DIR / "lulc_varanasi.tif"
    if out_file.exists():
        print(f"[INFO] LULC file already exists: {out_file}")
        sys.exit(0)

    # Priority 1: Bhuvan
    bhuvan_success = try_bhuvan_lulc(cfg)

    if not bhuvan_success:
        print("\n[INFO] Bhuvan LULC unavailable. Attempting ESA WorldCover fallback...")
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="BHUVAN_LULC_50K",
            source_type="REMOTE_SENSING",
            status=STATUS_SKIPPED,
            reason="Bhuvan unavailable — using ESA WorldCover fallback.",
        )
        # Priority 2: ESA WorldCover
        esa_out = RAW_DIR / "esa_worldcover_varanasi.tif"
        esa_success = try_esa_worldcover(cfg, esa_out)
        if esa_success:
            write_acquisition_status(
                output_dir=STATUS_DIR,
                source_name="ESA_WORLDCOVER_10M",
                source_type="REMOTE_SENSING",
                status=STATUS_SUCCESS,
                reason="ESA WorldCover 10m downloaded successfully (Bhuvan fallback).",
                files_written=[str(f) for f in RAW_DIR.glob("esa_worldcover_*.tif")],
                aoi_bbox=cfg.bbox,
            )
        else:
            write_acquisition_status(
                output_dir=STATUS_DIR,
                source_name="ESA_WORLDCOVER_10M",
                source_type="REMOTE_SENSING",
                status=STATUS_NETWORK_ERROR,
                reason="ESA WorldCover download failed. Check network connectivity.",
                required_manual_action=(
                    "Download ESA WorldCover tiles for Varanasi region from:\n"
                    "https://esa-worldcover.org/en\n"
                    f"Save to: {RAW_DIR}/"
                ),
                download_url="https://esa-worldcover.org/en",
                aoi_bbox=cfg.bbox,
            )

    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
