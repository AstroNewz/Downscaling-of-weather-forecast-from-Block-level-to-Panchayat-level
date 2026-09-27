#!/usr/bin/env python3
"""
India Weather Data Orchestrator
SIH Problem Statement 26074 — Agroweather-Downscaling

Runs all weather acquisition scripts in source-priority order:
  1. IMD AWS/station observations (OBSERVATION — requires IMD access)
  2. ERA5 reanalysis (REANALYSIS — requires CDS API)
  3. ERA5-Land reanalysis (REANALYSIS — requires CDS API)

Then runs geospatial acquisition:
  4. Administrative boundaries (LGD/Bhuvan)
  5. DEM (SRTM 30m)
  6. LULC (Bhuvan → ESA WorldCover fallback)
  7. Soil (SoilGrids)
  8. Crop calendar metadata

After all scripts run, prints a consolidated acquisition status report.

RULE: This orchestrator NEVER fabricates data. If a source fails,
      its SOURCE_ACCESS_REQUIRED entry is recorded and the next
      source is attempted independently.
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent

STATUS_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"

SCRIPTS = [
    # (script_name, description, source_type)
    ("download_imd.py",              "IMD AWS Station Observations",     "OBSERVATION"),
    ("download_era5.py",             "ERA5 Reanalysis (coarse input)",   "REANALYSIS"),
    ("download_era5_land.py",        "ERA5-Land Reanalysis (reference)", "REANALYSIS"),
    ("download_india_boundaries.py", "Administrative Boundaries (LGD)",  "DERIVED"),
    ("download_dem.py",              "SRTM 30m DEM",                     "REMOTE_SENSING"),
    ("download_lulc.py",             "LULC (Bhuvan/ESA WorldCover)",     "REMOTE_SENSING"),
    ("download_soil.py",             "SoilGrids 2.0",                    "DERIVED"),
    ("download_crop_data.py",        "Crop Calendar Metadata",           "DERIVED"),
]


def main():
    print("=" * 70)
    print("INDIA WEATHER DATA ORCHESTRATOR")
    print("Pilot: Varanasi district, Uttar Pradesh, India")
    print("=" * 70)
    print(f"\nRunning {len(SCRIPTS)} acquisition scripts in source-priority order...\n")

    results = {}
    for script_name, description, source_type in SCRIPTS:
        script_path = SCRIPT_DIR / script_name
        print(f"\n{'─'*60}")
        print(f"[{source_type}] {description}")
        print(f"Script: {script_path.name}")
        print(f"{'─'*60}")

        if not script_path.exists():
            print(f"[ERROR] Script not found: {script_path}")
            results[script_name] = "SCRIPT_MISSING"
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,
                timeout=600,  # 10 min timeout per script
            )
            results[script_name] = "OK" if result.returncode == 0 else f"EXIT_{result.returncode}"
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {script_name} exceeded 10 minute limit.")
            results[script_name] = "TIMEOUT"
        except Exception as e:
            print(f"[ERROR] {script_name} failed: {e}")
            results[script_name] = f"ERROR: {e}"

    # Consolidated status
    print(f"\n{'='*70}")
    print("ORCHESTRATION COMPLETE — SCRIPT RESULTS")
    print(f"{'='*70}")
    for script, status in results.items():
        icon = "✓" if status == "OK" else "✗"
        print(f"  {icon} {script:<45} {status}")

    print(f"\n[INFO] Full acquisition status: {STATUS_DIR}/data_acquisition_status.json")
    print("[INFO] No data has been fabricated. SOURCE_ACCESS_REQUIRED entries")
    print("       indicate sources that require manual access setup.")


if __name__ == "__main__":
    main()
