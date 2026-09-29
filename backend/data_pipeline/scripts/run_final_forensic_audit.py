"""
Runner Script: Final Forensic Audit
SIH Problem Statement 26074 (Weather Downscaling - Task 9)

Executes forensic_audit_service.py to perform an exhaustive, independent,
and objective scientific audit across Tasks 1 through 8.
Generates:
- reports/FINAL_FORENSIC_AUDIT.json
- reports/FINAL_FORENSIC_AUDIT.md
"""
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.forensic_audit_service import forensic_audit_service


def main():
    print("=" * 70)
    print("STARTING TASK 9 FINAL FORENSIC AUDIT")
    print("SIH Problem Statement 26074: Downscaling, Satellite & Nowcast Pipeline")
    print("=" * 70)

    # 1. Execute full forensic audit
    audit_data = forensic_audit_service.run_forensic_audit()

    # 2. Output file paths
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "FINAL_FORENSIC_AUDIT.json"
    md_path = reports_dir / "FINAL_FORENSIC_AUDIT.md"

    # 3. Save JSON artifact
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print(f"\n[+] Saved JSON Forensic Report: {json_path}")

    # 4. Save Markdown artifact
    md_report = forensic_audit_service.render_markdown_audit_report(audit_data)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"[+] Saved Markdown Forensic Report: {md_path}")

    # 5. Print high-level executive summary
    print("\n" + "=" * 70)
    print("FORENSIC AUDIT EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"Overall Audit Status:             {audit_data['audit_status']}")
    print(f"Scientific Readiness:             {audit_data['final_scientific_readiness']}")
    print(f"Model Immutability Status:        {audit_data['model_immutability_audit']['status']}")
    print(f"Panchayat Geometry Routing:       {audit_data['panchayat_geometry_audit']['status']}")
    print(f"Admitted Independent Stations:    {audit_data['dataset_provenance_audit']['admitted_stations_count']}")
    print(f"Rejected / Quarantined Stations:  {audit_data['dataset_provenance_audit']['rejected_stations_count']}")
    print(f"Curated Meteorological Events:    {audit_data['sample_count_reconciliation']['curated_multi_regime_events_count']}")
    print(f"Seasonal Monitoring Hours:        {audit_data['sample_count_reconciliation']['operational_monitoring_hours_in_season']}")
    print(f"Stage 1 CSI (Overall / 30m):      {audit_data['metric_reproduction_audit']['stage1_metrics']['overall_csi']:.4f}")
    print(f"Stage 2 MAE (Overall):            {audit_data['metric_reproduction_audit']['stage2_metrics']['overall_mae_mm']:.2f} mm")
    print(f"A/B Spatial Differentiation:      {audit_data['ab_spatial_differentiation_audit']['directional_agreement_pct']:.1f}% Agreement")
    print(f"Live / Demo Isolation:            {audit_data['live_demo_isolation_audit']['status']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
