#!/usr/bin/env python3
"""
SRTM 30m DEM Downloader — Terrain Features for Varanasi Pilot
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : NASA / USGS SRTM 1 Arc-Second Global (SRTMGL1 v003)
Type   : REMOTE_SENSING (static terrain data — NOT weather observation)
Access : Open access via NASA Earthdata (free account) or direct download

RULE: DEM data is used ONLY for spatial feature extraction:
  - elevation_m
  - slope_deg
  - aspect_deg
  - terrain_roughness
  - lapse_rate_temp_adjustment_c

DEM data MUST NOT be used to manufacture weather observations.
DEM is a spatial predictor, not a target variable.

Download approach:
  Primary  : elevation Python library (uses SRTM tiles, free)
  Fallback : Direct NASA Earthdata URL download (requires free account)

Expected output:
  backend/data/raw/india/pilot/srtm_varanasi_30m.tif
  backend/data/raw/india/pilot/srtm_varanasi_30m.tif.provenance.json
"""
from __future__ import annotations

import sys
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
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"

SRTM_CITATION = (
    "Farr, T.G. et al. (2007). The Shuttle Radar Topography Mission. "
    "Reviews of Geophysics, 45. https://doi.org/10.1029/2005RG000183"
)


def try_elevation_library(cfg, out_file: Path) -> bool:
    """
    Attempts DEM download via the `elevation` Python library.
    This library automatically fetches SRTM tiles and merges them.
    Returns True on success, False on failure.
    """
    try:
        import elevation
    except ImportError:
        print("[INFO] `elevation` library not installed. Run: pip install elevation")
        return False

    lat_min, lat_max, lon_min, lon_max = cfg.bbox
    bounds = (lon_min, lat_min, lon_max, lat_max)  # (left, bottom, right, top)

    approx_cells = int((lat_max - lat_min) / (1/3600)) * int((lon_max - lon_min) / (1/3600))
    approx_mb = approx_cells * 2 / 1e6  # int16 = 2 bytes

    print(f"\n{'='*60}")
    print(f"SRTM DEM DOWNLOAD — PRE-FLIGHT CHECK (Requirement 17)")
    print(f"{'='*60}")
    print(f"  Dataset    : SRTM 1 Arc-Second Global (SRTMGL1 v003)")
    print(f"  Source type: REMOTE_SENSING (terrain only — NOT weather)")
    print(f"  AOI bbox   : lat {lat_min}–{lat_max}, lon {lon_min}–{lon_max}")
    print(f"  Resolution : 30m (1 arc-second)")
    print(f"  Bounds     : {bounds}")
    print(f"  Est. volume: ~{approx_mb:.1f} MB")
    print(f"  Output     : {out_file}")
    print(f"{'='*60}")

    try:
        elevation.clip(bounds=bounds, output=str(out_file), product="SRTM1")
        elevation.clean()
        print(f"[SUCCESS] SRTM DEM downloaded: {out_file}")
        return True
    except Exception as e:
        print(f"[WARNING] elevation library download failed: {e}")
        return False


def try_direct_download(cfg, out_file: Path) -> bool:
    """
    Attempts direct download of SRTM tile covering Varanasi from NASA Earthdata.
    The Varanasi region is covered by SRTM tile N25E082.
    Requires NASA Earthdata credentials in environment.
    Returns True on success.
    """
    import os
    import urllib.request

    earthdata_user = os.environ.get("EARTHDATA_USER", "").strip()
    earthdata_pass = os.environ.get("EARTHDATA_PASS", "").strip()

    if not earthdata_user or not earthdata_pass:
        print("[INFO] EARTHDATA_USER and EARTHDATA_PASS not set.")
        print("[INFO] Register free at https://urs.earthdata.nasa.gov/")
        return False

    # SRTM tiles for Varanasi region (N25E082, N25E083)
    # Note: multiple tiles may need to be merged for full AOI coverage
    tiles = ["N25E082", "N25E083"]
    tile_urls = [
        f"https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/{t}.SRTMGL1.hgt.zip"
        for t in tiles
    ]

    print("[INFO] Attempting direct NASA Earthdata SRTM tile download...")
    downloaded = []
    for url, tile in zip(tile_urls, tiles):
        tile_file = out_file.parent / f"srtm_{tile}.hgt.zip"
        try:
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, "https://urs.earthdata.nasa.gov", earthdata_user, earthdata_pass)
            auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.request.build_opener(auth_handler)
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, tile_file)
            downloaded.append(tile_file)
            print(f"[SUCCESS] Downloaded SRTM tile: {tile}")
        except Exception as e:
            print(f"[WARNING] Failed to download {tile}: {e}")

    if downloaded:
        print(f"[INFO] {len(downloaded)} SRTM tile(s) downloaded. Merge with GDAL to create mosaic.")
        print(f"[INFO] Command: gdal_merge.py -o {out_file} {' '.join(str(d) for d in downloaded)}")
        return True
    return False


def main():
    print("=" * 70)
    print("SRTM 30M DEM DOWNLOADER — TERRAIN FEATURES")
    print("Source type: REMOTE_SENSING (NOT weather data)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RAW_DIR / "srtm_varanasi_30m.tif"

    if out_file.exists():
        print(f"[INFO] DEM file already exists: {out_file}")
        print("[INFO] Delete to force re-download.")
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="SRTM_30M",
            source_type="REMOTE_SENSING",
            status=STATUS_SUCCESS,
            reason=f"DEM file already present: {out_file}",
            files_written=[str(out_file)],
        )
        sys.exit(0)

    # Try primary: elevation library
    success = try_elevation_library(cfg, out_file)

    # Try fallback: direct NASA Earthdata download
    if not success:
        success = try_direct_download(cfg, out_file)

    if success and out_file.exists():
        write_retrieval_sidecar(
            filepath=out_file,
            source_name="SRTM_30M",
            source_type="REMOTE_SENSING",
            organization="NASA / USGS",
            dataset_name="SRTM 1 Arc-Second Global (SRTMGL1 v003)",
            download_url="https://lpdaac.usgs.gov/products/srtmgl1v003/",
            license_str="NASA/USGS — free for scientific use",
            version="v003 (acquired February 2000)",
            variables=["elevation_m"],
            spatial_resolution="30 m (1 arc-second)",
            temporal_resolution="static",
            coverage=f"Varanasi pilot bbox {cfg.bbox}",
            citation=SRTM_CITATION,
            notes=(
                "TERRAIN DATA ONLY. Used for: elevation_m, slope_deg, aspect_deg, "
                "terrain_roughness, lapse_rate_temp_adjustment_c. "
                "Must NOT be used to manufacture weather observations."
            ),
        )
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="SRTM_30M",
            source_type="REMOTE_SENSING",
            status=STATUS_SUCCESS,
            reason="SRTM DEM downloaded successfully.",
            files_written=[str(out_file)],
            aoi_bbox=cfg.bbox,
        )
        print("[SUCCESS] DEM download complete.")
    else:
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="SRTM_30M",
            source_type="REMOTE_SENSING",
            status=STATUS_ACCESS_REQUIRED,
            reason="Could not download via elevation library or direct NASA Earthdata.",
            required_credentials="NASA Earthdata account: EARTHDATA_USER, EARTHDATA_PASS env vars",
            required_manual_action=(
                "Option 1: pip install elevation && re-run (auto-downloads SRTM tiles)\n"
                "Option 2: Register at https://urs.earthdata.nasa.gov/ then set\n"
                "  EARTHDATA_USER=<user> EARTHDATA_PASS=<pass> and re-run\n"
                "Option 3: Download manually from https://lpdaac.usgs.gov/products/srtmgl1v003/\n"
                "  Tiles needed: N25E082.SRTMGL1.hgt.zip, N25E083.SRTMGL1.hgt.zip\n"
                f"  Save as: {out_file}"
            ),
            download_url="https://lpdaac.usgs.gov/products/srtmgl1v003/",
            aoi_bbox=cfg.bbox,
        )

    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
