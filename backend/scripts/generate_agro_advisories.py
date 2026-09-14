"""
CLI Tool: Generate Agro-Meteorological Advisories
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Translates Phase 10 agricultural risks into explainable, prioritized advisories
for a specific Panchayat or an entire Block.

Usage:
    python scripts/generate_agro_advisories.py --panchayat-id 1 --date 2026-07-15 --dry-run
    python scripts/generate_agro_advisories.py --block-id 1 --date 2026-07-15
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Ensure backend root is on Python path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal
from app.services.advisory_engine import AdvisoryEngine


def main():
    parser = argparse.ArgumentParser(
        description="Phase 11: Generate Agro-Meteorological Advisories for Gram Panchayats and Blocks."
    )
    parser.add_argument("--panchayat-id", type=int, default=None, help="Gram Panchayat ID")
    parser.add_argument("--block-id", type=int, default=None, help="Block ID for batch generation")
    parser.add_argument("--crop-id", type=int, default=None, help="Filter for specific crop ID")
    parser.add_argument("--risk-type", type=str, default=None, help="Filter for specific risk type (e.g. HEAT_STRESS)")
    parser.add_argument("--date", type=str, default=None, help="Forecast date (YYYY-MM-DD, default today)")
    parser.add_argument("--language", type=str, default="en", help="Advisory language code (default 'en')")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate advisories without persisting to database")

    args = parser.parse_args()

    if args.panchayat_id is None and args.block_id is None:
        parser.error("Must provide either --panchayat-id or --block-id.")

    eval_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.utcnow()

    db = SessionLocal()
    try:
        engine = AdvisoryEngine(db=db)

        print("=" * 80)
        print("SIH PS 26074: PHASE 11 AGRO-METEOROLOGICAL ADVISORY ENGINE")
        print(f"Evaluation Date: {eval_date.strftime('%Y-%m-%d')}")
        print(f"Mode: {'DRY RUN (No DB write)' if args.dry_run else 'PERSIST TO DB'}")
        print(f"Language: {args.language}")
        print("=" * 80)

        if args.block_id is not None:
            response = engine.generate_block_advisories(
                block_id=args.block_id,
                forecast_date=eval_date,
                panchayat_id=args.panchayat_id,
                crop_id=args.crop_id,
                risk_type=args.risk_type,
                persist_to_db=not args.dry_run,
                language=args.language,
            )
            advisories = response.advisories
            print(f"\n[SUMMARY] Block: {response.block_name} (ID: {response.block_id})")
            print(f"Total Panchayats: {response.total_panchayats}")
            print(f"Total Crops Evaluated: {response.total_crops_evaluated}")
            print(f"Total Advisories Generated: {response.total_advisories_generated}")
            print(f"Critical: {response.critical_advisories_count} | High: {response.high_advisories_count} | "
                  f"Medium: {response.medium_advisories_count} | Low: {response.low_advisories_count} | Info: {response.informational_count}\n")
        else:
            advisories = engine.generate_panchayat_advisories(
                panchayat_id=args.panchayat_id,
                forecast_date=eval_date,
                crop_id=args.crop_id,
                risk_type_filter=args.risk_type,
                persist_to_db=not args.dry_run,
                language=args.language,
            )
            print(f"\n[SUMMARY] Generated {len(advisories)} advisories for Panchayat ID: {args.panchayat_id}\n")

        if not advisories:
            print("No actionable agricultural risks detected for the selected criteria.")
            return

        table_rows = []
        for a in advisories:
            act_text = a.action.action_text if a.action and a.action.action_text else "None"
            # Truncate action text for clean terminal display
            short_act = (act_text[:45] + "...") if len(act_text) > 48 else act_text

            table_rows.append([
                a.panchayat_name,
                a.crop_name,
                a.stage_name or "N/A",
                a.priority,
                a.severity,
                a.advisory_type.replace("_ADVISORY", ""),
                a.title[:30] + "..." if len(a.title) > 30 else a.title,
                short_act,
                a.confidence,
                f"{a.valid_from[:10]} to {a.valid_until[:10]}",
            ])

        headers = [
            "Panchayat",
            "Crop",
            "Stage",
            "Priority",
            "Severity",
            "Type",
            "Title",
            "Action",
            "Confidence",
            "Validity Window",
        ]

        print(tabulate(table_rows, headers=headers, tablefmt="grid"))
        print("\nAdvisory generation completed successfully.")

    except Exception as e:
        print(f"\n[ERROR] Advisory generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
