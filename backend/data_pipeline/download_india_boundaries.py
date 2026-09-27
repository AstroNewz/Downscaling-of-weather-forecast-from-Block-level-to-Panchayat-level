#!/usr/bin/env python3
"""
India Administrative Boundaries Downloader
SIH Problem Statement 26074 — Agroweather-Downscaling

Downloads: State → District → Block → Gram Panchayat boundaries
for Varanasi district, Uttar Pradesh.

Priority 1: LGD (Local Government Directory) — Government of India
Priority 2: Bhuvan administrative layers (NRSC/ISRO)

Expected output:
  backend/data/raw/india/pilot/boundaries/
    varanasi_district.geojson
    varanasi_blocks.geojson
    varanasi_panchayats.geojson
"""
from __future__ import annotations

import sys
import json
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
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
BOUNDARY_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot" / "boundaries"


def try_lgd_api(cfg, out_dir: Path) -> bool:
    """
    Attempts to download LGD boundaries via Geospatial portal.
    LGD codes for Varanasi: State code 09, District code 0720.
    Returns True if any data obtained.
    """
    # LGD open data — public boundary shapefiles
    # The AGIS portal provides open block/panchayat boundaries
    lgd_urls = {
        "varanasi_district": (
            "https://lgdirectory.gov.in/generateGeojson.do"
            "?level=3&stateCode=09&districtCode=0720"
        ),
    }

    success = False
    for name, url in lgd_urls.items():
        out_file = out_dir / f"{name}.geojson"
        try:
            urllib.request.urlretrieve(url, str(out_file))
            if out_file.exists() and out_file.stat().st_size > 100:
                print(f"[SUCCESS] Downloaded LGD boundary: {out_file}")
                write_retrieval_sidecar(
                    filepath=out_file,
                    source_name="LGD_BOUNDARIES",
                    source_type="DERIVED",
                    organization="Ministry of Panchayati Raj / MoRD, GoI",
                    dataset_name="Local Government Directory (LGD) Administrative Boundaries",
                    download_url="https://lgdirectory.gov.in/",
                    license_str="Government of India Open Data License (GODL)",
                    version="current",
                    variables=["boundary_geometry", "lgd_code", "name"],
                    spatial_resolution="cadastral",
                    temporal_resolution="static",
                    coverage="Varanasi district, Uttar Pradesh",
                    citation="Local Government Directory, Ministry of Panchayati Raj, GoI",
                )
                success = True
            else:
                if out_file.exists():
                    out_file.unlink()
        except Exception as e:
            print(f"[WARNING] LGD API failed for {name}: {e}")

    return success


def create_pilot_bbox_geojson(cfg, out_dir: Path) -> Path:
    """
    Creates a minimal AOI GeoJSON for the Varanasi pilot bbox.
    This is a placeholder geometry until real administrative boundaries
    can be obtained from LGD/Bhuvan.
    """
    out_file = out_dir / "varanasi_pilot_aoi_bbox.geojson"
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Varanasi Pilot AOI Bounding Box",
                    "state": cfg.state,
                    "district": cfg.district,
                    "note": (
                        "PLACEHOLDER bounding box — NOT actual administrative boundary. "
                        "Replace with real LGD/Bhuvan boundary data when available. "
                        "Source: india_pilot.yaml AOI configuration."
                    ),
                    "source": "india_pilot.yaml",
                    "is_placeholder": True,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [cfg.longitude_min, cfg.latitude_min],
                        [cfg.longitude_max, cfg.latitude_min],
                        [cfg.longitude_max, cfg.latitude_max],
                        [cfg.longitude_min, cfg.latitude_max],
                        [cfg.longitude_min, cfg.latitude_min],
                    ]],
                },
            }
        ],
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"[INFO] Created placeholder AOI GeoJSON: {out_file}")
    return out_file


def main():
    print("=" * 70)
    print("INDIA ADMINISTRATIVE BOUNDARIES DOWNLOADER")
    print("Sources: LGD (GoI) → Bhuvan (NRSC/ISRO)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())
    BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)

    # Try LGD
    lgd_success = try_lgd_api(cfg, BOUNDARY_DIR)

    if lgd_success:
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="LGD_BOUNDARIES",
            source_type="DERIVED",
            status=STATUS_SUCCESS,
            reason="LGD administrative boundaries downloaded.",
            aoi_bbox=cfg.bbox,
        )
    else:
        print("[INFO] LGD API not accessible. Creating placeholder AOI bbox GeoJSON.")
        bbox_file = create_pilot_bbox_geojson(cfg, BOUNDARY_DIR)
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name="LGD_BOUNDARIES",
            source_type="DERIVED",
            status=STATUS_ACCESS_REQUIRED,
            reason="LGD API not accessible. Placeholder bbox GeoJSON created.",
            required_manual_action=(
                "Download Varanasi district boundaries manually:\n"
                "Option 1: https://lgdirectory.gov.in/ (state: UP, district: Varanasi)\n"
                "Option 2: https://bhuvan.nrsc.gov.in/ → District/Block/Panchayat layers\n"
                "Option 3: Survey of India / NLSMA open data\n"
                f"Save GeoJSON files to: {BOUNDARY_DIR}/"
            ),
            download_url="https://lgdirectory.gov.in/",
            files_written=[str(bbox_file)],
            aoi_bbox=cfg.bbox,
        )

    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="BHUVAN_ADMIN",
        source_type="DERIVED",
        status=STATUS_ACCESS_REQUIRED,
        reason="Bhuvan WFS administrative boundary download requires Bhuvan account.",
        required_credentials="Bhuvan account: https://bhuvan.nrsc.gov.in/",
        download_url="https://bhuvan.nrsc.gov.in/bhuvan_links.php",
        aoi_bbox=cfg.bbox,
    )

    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
