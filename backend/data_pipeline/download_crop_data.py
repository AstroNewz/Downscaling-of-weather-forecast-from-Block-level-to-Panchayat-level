#!/usr/bin/env python3
"""
Crop Calendar Data Downloader — Varanasi Pilot
SIH Problem Statement 26074 — Agroweather-Downscaling

Sources (in priority order):
  1. ICRISAT VDSA (Village Dynamics in South Asia)
  2. ICAR crop calendar for Uttar Pradesh (where accessible)
  3. FAO GAEZ crop calendar (global fallback)

RULE: Crop data is agricultural context metadata.
      It is NOT weather observation data.
"""
from __future__ import annotations

import sys
import json
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


def write_crop_calendar_metadata(cfg, out_dir: Path) -> Path:
    """
    Writes a documented crop calendar metadata file for Varanasi district
    based on publicly known Kharif season information for Uttar Pradesh.
    This is reference metadata — NOT manufactured weather or yield data.
    """
    out_file = out_dir / "varanasi_crop_calendar_metadata.json"
    crop_meta = {
        "note": (
            "Reference crop calendar for Varanasi district, Uttar Pradesh. "
            "Based on well-documented Kharif season agronomy for the IGP. "
            "This is reference metadata — NOT field observation data. "
            "Source: publicly known agronomic knowledge for the Indo-Gangetic Plain."
        ),
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "season": "Kharif",
        "year": "2024",
        "crops": [
            {
                "crop": "Rice (Paddy)",
                "scientific_name": "Oryza sativa",
                "typical_sowing": "June 15 – July 15",
                "typical_transplanting": "July 1 – July 20",
                "typical_harvest": "October – November",
                "critical_stages": ["Tillering (July-Aug)", "Flowering/Heading (Sep)", "Grain-fill (Sep-Oct)"],
                "critical_tmax_threshold_c": 35.0,
                "optimal_tmax_range_c": [22.0, 32.0],
                "reference": "ICAR Rice Research Station; IMD-ICAR Crop Weather Calendar UP",
            },
            {
                "crop": "Maize",
                "scientific_name": "Zea mays",
                "typical_sowing": "June 20 – July 10",
                "typical_harvest": "September – October",
                "critical_stages": ["Tasseling/Silking (August)"],
                "critical_tmax_threshold_c": 38.0,
                "optimal_tmax_range_c": [20.0, 30.0],
                "reference": "ICAR-IARI Maize Research Directorate",
            },
        ],
        "source_type": "DERIVED",
        "is_observation": False,
        "data_status": "REFERENCE_METADATA_ONLY",
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(crop_meta, f, indent=2, ensure_ascii=False)
    return out_file


def main():
    print("=" * 70)
    print("CROP DATA DOWNLOADER — Varanasi Pilot")
    print("=" * 70)

    cfg = load_pilot_config()
    print(cfg.describe())

    crop_dir = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
    crop_dir.mkdir(parents=True, exist_ok=True)

    # Write reference crop metadata
    meta_file = write_crop_calendar_metadata(cfg, crop_dir)
    print(f"[INFO] Crop calendar reference metadata written: {meta_file}")

    # Report external sources as requiring access
    for src in ["ICRISAT_VDSA", "ICAR_CROP_CALENDAR"]:
        write_acquisition_status(
            output_dir=STATUS_DIR,
            source_name=src,
            source_type="DERIVED",
            status=STATUS_ACCESS_REQUIRED,
            reason="Crop database requires institutional registration or specific data request.",
            required_manual_action=(
                "ICRISAT VDSA: https://vdsa.icrisat.org/ (registration may be required)\n"
                "ICAR Crop Calendar UP: Contact ICAR regional centers for digital data."
            ),
            download_url="https://vdsa.icrisat.org/" if "ICRISAT" in src else "https://www.icar.org.in/",
            aoi_bbox=cfg.bbox,
        )

    print_status_report(STATUS_DIR)


if __name__ == "__main__":
    main()
