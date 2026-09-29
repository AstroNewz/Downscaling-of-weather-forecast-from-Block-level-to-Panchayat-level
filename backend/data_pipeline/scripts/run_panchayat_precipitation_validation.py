#!/usr/bin/env python3
"""
Runner Script: Run Panchayat Precipitation Validation (Task 8)
SIH Problem Statement 26074 (Weather Downscaling - Task 8)

Executes independent validation against physical ground truth observations,
verifies cryptographic immutability, and writes both JSON and Markdown reports.
"""
import json
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
REPO_ROOT = BACKEND_ROOT.parent

sys.path.insert(0, str(BACKEND_ROOT))

from app.gis.boundary_registry import boundary_registry
from app.gis.boundary_service import panchayat_boundary_service
from app.services.precipitation_validation_service import precipitation_validation_service

REAL_BOUNDARIES_PATH = BACKEND_ROOT / "data" / "raw" / "india" / "pilot" / "boundaries" / "authorized_panchayats.geojson"
GROUND_TRUTH_PATH = BACKEND_ROOT / "data" / "raw" / "panchayat_mesonet" / "independent_validation_observations.json"
REPORTS_DIR = REPO_ROOT / "reports"

REPORT_JSON_PATH = REPORTS_DIR / "PANCHAYAT_PRECIPITATION_VALIDATION_REPORT.json"
REPORT_MD_PATH = REPORTS_DIR / "PANCHAYAT_PRECIPITATION_VALIDATION_REPORT.md"


def main():
    print("=" * 80)
    print("TASK 8: Independent Panchayat-Scale Precipitation Validation Pipeline")
    print("SIH Problem Statement 26074")
    print("=" * 80)

    # 1. Load official pilot boundaries
    print("\n[Step 1] Loading official verified pilot boundaries...")
    boundary_registry.clear()
    count = boundary_registry.load_from_file(
        file_path=REAL_BOUNDARIES_PATH,
        source_name="GOI_LGD_AUTHORIZED_PILOT",
        is_verified=True,
        geometry_status="AUTHORIZED_OFFICIAL",
    )
    print(f"Loaded {count} pilot Panchayats from {REAL_BOUNDARIES_PATH.name}")
    panchayat_boundary_service._sync_spatial_index()

    # 2. Execute validation engine
    print("\n[Step 2] Executing independent validation protocol & immutability audit...")
    report = precipitation_validation_service.run_full_validation(ground_truth_path=GROUND_TRUTH_PATH)
    print(f"Scientific Readiness Classification: {report.scientific_readiness.value}")
    print(f"Immutability Verified: {report.immutability_audit.verified_unchanged}")

    # 3. Serialize outputs
    print(f"\n[Step 3] Writing reports to {REPORTS_DIR}...")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON report
    report_dict = report.model_dump()
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    print(f"Wrote JSON report to: {REPORT_JSON_PATH}")

    # Markdown report
    md_content = precipitation_validation_service.render_markdown_report(report)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Wrote Markdown report to: {REPORT_MD_PATH}")

    print("\n" + "=" * 80)
    print("TASK 8 VALIDATION SUMMARY:")
    print(f"- Stations admitted: {report.eligible_independent_stations_count} (Independent)")
    print(f"- Stations rejected: {report.rejected_stations_count} (Contaminated / Synthetic / Incomplete)")
    print(f"- Multi-regime events evaluated: {len(report.event_forensics)}")
    print(f"- 30m Occurrence CSI: {report.stage1_occurrence_by_horizon['30m'].csi:.3f} | Brier: {report.stage1_occurrence_by_horizon['30m'].brier_score:.4f}")
    print(f"- 30m Amount MAE: {report.stage2_amount_by_horizon['30m'].mae_mm:.2f} mm | RMSE: {report.stage2_amount_by_horizon['30m'].rmse_mm:.2f} mm")
    print(f"- Spatial A/B Directional Agreement: {sum(1 for s in report.spatial_differentiation if s.directional_agreement)} / {len(report.spatial_differentiation)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
