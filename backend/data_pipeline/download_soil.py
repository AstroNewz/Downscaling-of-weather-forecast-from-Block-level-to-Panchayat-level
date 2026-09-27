#!/usr/bin/env python3
"""
SoilGrids 2.0 Downloader — Soil Properties for Varanasi Pilot
SIH Problem Statement 26074 — Agroweather-Downscaling

Source : ISRIC SoilGrids 2.0 (open REST API, no credentials required)
Type   : DERIVED (250m resolution global soil property maps)
License: CC BY 4.0

RULE: Soil data is a spatial predictor for agricultural context.
      It is NOT a weather observation and must NOT be used as one.

Variables downloaded:
  - soc   : Soil Organic Carbon (dg/kg)
  - phh2o : Soil pH in water × 10
  - clay  : Clay content (g/kg)
  - sand  : Sand content (g/kg)
  - silt  : Silt content (g/kg)
  - bdod  : Bulk density (cg/cm³)

Expected output:
  backend/data/raw/india/pilot/soilgrids_varanasi_<var>.tif
  backend/data/raw/india/pilot/soilgrids_varanasi_<var>.tif.provenance.json
"""
from __future__ import annotations

import sys
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
    STATUS_SUCCESS,
    STATUS_NETWORK_ERROR,
    print_status_report,
)

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"

SOILGRIDS_CITATION = (
    "Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information "
    "for the globe with quantified spatial uncertainty. SOIL, 7, 217-240. "
    "https://doi.org/10.5194/soil-7-217-2021"
)

# SoilGrids WCS base URL — ISO 19128 WCS 1.0.0
# Uses COG (Cloud Optimized GeoTIFF) via OGC WCS
SOILGRIDS_WCS_BASE = "https://maps.isric.org/mapserv?map=/map/{var}.map"

# Variables and their SoilGrids layer names (0-5cm depth)
SOIL_VARS = {
    "soc": ("soc_0-5cm_mean", "Soil Organic Carbon 0-5cm mean (dg/kg)"),
    "phh2o": ("phh2o_0-5cm_mean", "Soil pH H2O 0-5cm mean (pHx10)"),
    "clay": ("clay_0-5cm_mean", "Clay content 0-5cm mean (g/kg)"),
    "sand": ("sand_0-5cm_mean", "Sand content 0-5cm mean (g/kg)"),
    "bdod": ("bdod_0-5cm_mean", "Bulk density 0-5cm mean (cg/cm3)"),
}


def download_soilgrids_var(var_key: str, layer_name: str, description: str,
                            cfg, out_dir: Path) -> bool:
    """
    Downloads a SoilGrids variable via WCS for the pilot AOI.
    Uses Homolosine projection for SoilGrids — reprojects to WGS84 after download.
    Returns True on success.
    """
    # SoilGrids WCS endpoint for the variable
    wcs_url = (
        f"https://maps.isric.org/mapserv?map=/map/{var_key}.map"
        f"&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
        f"&COVERAGEID={layer_name}"
        f"&FORMAT=image/tiff"
        f"&SUBSET=long({cfg.longitude_min},{cfg.longitude_max})"
        f"&SUBSET=lat({cfg.latitude_min},{cfg.latitude_max})"
        f"&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
        f"&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
    )

    out_file = out_dir / f"soilgrids_varanasi_{var_key}.tif"
    approx_mb = 0.5  # SoilGrids tiles for small AOI are small

    print(f"\n[INFO] Downloading SoilGrids: {var_key} ({description})")
    print(f"       AOI: lat {cfg.latitude_min}–{cfg.latitude_max}, lon {cfg.longitude_min}–{cfg.longitude_max}")
    print(f"       Est. size: ~{approx_mb} MB | Output: {out_file}")

    try:
        urllib.request.urlretrieve(wcs_url, str(out_file))
        if out_file.stat().st_size < 1000:
            # Too small — likely an error XML response
            error_text = out_file.read_text(errors="replace")[:200]
            print(f"[WARNING] Response too small ({out_file.stat().st_size}b): {error_text}")
            out_file.unlink()
            return False
        print(f"[SUCCESS] {var_key}: {out_file}")
        write_retrieval_sidecar(
            filepath=out_file,
            source_name="SOILGRIDS_250M",
            source_type="DERIVED",
            organization="ISRIC — World Soil Information",
            dataset_name="SoilGrids 2.0",
            download_url="https://www.isric.org/explore/soilgrids",
            license_str="CC BY 4.0",
            version="2.0",
            variables=[var_key],
            spatial_resolution="250 m",
            temporal_resolution="static",
            coverage=f"Varanasi pilot bbox {cfg.bbox}",
            citation=SOILGRIDS_CITATION,
            notes=(
                f"Variable: {description}. "
                "SOIL PROPERTY DATA ONLY — NOT weather observation. "
                "Used as agricultural context spatial predictor."
            ),
        )
        return True
    except Exception as e:
        print(f"[ERROR] {var_key} download failed: {e}")
        return False


def main():
    print("=" * 70)
    print("SOILGRIDS 2.0 DOWNLOADER — SOIL PROPERTIES")
    print("Source: ISRIC (https://www.isric.org/explore/soilgrids)")
    print("License: CC BY 4.0 — open access, no credentials required")
    print("Source type: DERIVED (NOT weather data)")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n[PRE-FLIGHT] SoilGrids download for Varanasi pilot AOI")
    print(f"  Variables : {list(SOIL_VARS.keys())}")
    print(f"  Resolution: 250 m")
    print(f"  AOI       : lat {cfg.latitude_min}–{cfg.latitude_max}, "
          f"lon {cfg.longitude_min}–{cfg.longitude_max}")
    print(f"  Est. total: ~{len(SOIL_VARS) * 0.5:.1f} MB")

    files_written = []
    failed = []

    for var_key, (layer_name, description) in SOIL_VARS.items():
        out_file = RAW_DIR / f"soilgrids_varanasi_{var_key}.tif"
        if out_file.exists():
            print(f"[SKIP] Already exists: {out_file}")
            files_written.append(str(out_file))
            continue
        success = download_soilgrids_var(var_key, layer_name, description, cfg, RAW_DIR)
        if success:
            files_written.append(str(RAW_DIR / f"soilgrids_varanasi_{var_key}.tif"))
        else:
            failed.append(var_key)

    status = STATUS_SUCCESS if not failed else ("PARTIAL" if files_written else STATUS_NETWORK_ERROR)
    reason = (
        f"Downloaded {len(files_written)}/{len(SOIL_VARS)} SoilGrids variables."
        + (f" Failed: {failed}" if failed else "")
    )
    write_acquisition_status(
        output_dir=STATUS_DIR,
        source_name="SOILGRIDS_250M",
        source_type="DERIVED",
        status=status,
        reason=reason,
        files_written=files_written,
        aoi_bbox=cfg.bbox,
        download_url="https://www.isric.org/explore/soilgrids",
    )
    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
