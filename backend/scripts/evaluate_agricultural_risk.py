"""
CLI Tool: Evaluate Agricultural Risk & Stress Conditions
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Usage:
  python scripts/evaluate_agricultural_risk.py --block-id 1 --date 2026-07-15 --dry-run
  python scripts/evaluate_agricultural_risk.py --panchayat-id 1 --date 2026-07-15
  python scripts/evaluate_agricultural_risk.py --block-id 1 --risk-type HEAT_STRESS
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal
from app.core.config import settings
from app.core.logging import logger
from app.services.agricultural_risk import AgriculturalRiskEngine

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Agricultural Risk & Stress Conditions (SIH 26074 - Phase 10)"
    )
    parser.add_argument(
        "--block-id",
        type=int,
        default=None,
        help="Database ID of parent Block (required if --panchayat-id not specified)"
    )
    parser.add_argument(
        "--panchayat-id",
        type=int,
        default=None,
        help="Database ID of specific Gram Panchayat"
    )
    parser.add_argument(
        "--crop-id",
        type=int,
        default=None,
        help="Optional Crop ID filter"
    )
    parser.add_argument(
        "--risk-type",
        type=str,
        default=None,
        help="Optional risk type filter (HEAT_STRESS, COLD_STRESS, WATER_STRESS, EXCESS_RAIN, DISEASE_FAVORABLE_CONDITIONS, WIND_STRESS)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target evaluation date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, defaults to today)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute risk evaluation without persisting logs to database"
    )

    args = parser.parse_args()

    if args.block_id is None and args.panchayat_id is None:
        parser.error("Either --block-id or --panchayat-id must be provided.")

    if args.date:
        try:
            if "T" in args.date:
                eval_dt = datetime.fromisoformat(args.date)
            else:
                eval_dt = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"[ERROR] Invalid date format: '{args.date}'. Expected YYYY-MM-DD or ISO 8601.")
            sys.exit(1)
    else:
        eval_dt = datetime.utcnow()

    db = SessionLocal()
    try:
        engine = AgriculturalRiskEngine(db=db)

        if args.panchayat_id is not None:
            results = engine.evaluate_panchayat_crop_risks(
                panchayat_id=args.panchayat_id,
                evaluation_date=eval_dt,
                crop_id=args.crop_id,
                risk_type_filter=args.risk_type,
                persist_to_db=not args.dry_run,
            )
            detected_c = sum(1 for r in results if r.status == "DETECTED")
            not_det_c = sum(1 for r in results if r.status == "NOT_DETECTED")
            insuff_c = sum(1 for r in results if r.status == "INSUFFICIENT_DATA")

            print_risk_report(
                title=f"Phase 10 Agricultural Risk Assessment: Panchayat #{args.panchayat_id}",
                results=results,
                total_panchayats=1,
                total_evaluations=len(results),
                detected_count=detected_c,
                not_detected_count=not_det_c,
                insufficient_count=insuff_c,
                dry_run=args.dry_run,
                evaluation_date=eval_dt.isoformat(),
            )
        else:
            response = engine.evaluate_block_risks(
                block_id=args.block_id,
                evaluation_date=eval_dt,
                panchayat_id=args.panchayat_id,
                crop_id=args.crop_id,
                risk_type=args.risk_type,
                persist_to_db=not args.dry_run,
            )
            print_risk_report(
                title=f"Phase 10 Agricultural Risk Assessment: Block '{response.block_name}' (ID: {args.block_id})",
                results=response.results,
                total_panchayats=response.total_panchayats,
                total_evaluations=response.total_risk_evaluations,
                detected_count=response.detected_risks_count,
                not_detected_count=response.not_detected_count,
                insufficient_count=response.insufficient_data_count,
                dry_run=args.dry_run,
                evaluation_date=eval_dt.isoformat(),
            )

    except Exception as exc:
        logger.error(f"Risk evaluation execution failed: {str(exc)}", exc_info=True)
        print(f"\n[ERROR] Agricultural risk evaluation failed: {str(exc)}")
        sys.exit(1)
    finally:
        db.close()


def print_risk_report(
    title: str,
    results: list,
    total_panchayats: int,
    total_evaluations: int,
    detected_count: int,
    not_detected_count: int,
    insufficient_count: int,
    dry_run: bool,
    evaluation_date: str,
):
    if console:
        table = Table(title=title, show_header=True, header_style="bold green")
        table.add_column("Panchayat", style="bold")
        table.add_column("Crop")
        table.add_column("Stage")
        table.add_column("Risk Type")
        table.add_column("Observed", justify="right")
        table.add_column("Threshold", justify="right")
        table.add_column("Severity", style="bold")
        table.add_column("Status", style="bold")
        table.add_column("Confidence")
        table.add_column("Rule Version")

        sev_colors = {
            "NONE": "dim white",
            "LOW": "blue",
            "MODERATE": "yellow",
            "HIGH": "bold red",
            "EXTREME": "bold magenta",
        }

        status_colors = {
            "DETECTED": "bold red",
            "NOT_DETECTED": "green",
            "INSUFFICIENT_DATA": "yellow",
            "INVALID": "dim red",
        }

        for r in results:
            obs_str = f"{r.observed_value:.1f} {r.unit or ''}" if r.observed_value is not None else "-"
            thresh_str = f"{r.threshold_value:.1f} {r.unit or ''}" if r.threshold_value is not None else "-"
            stage_str = r.stage_name or "-"

            s_color = sev_colors.get(r.severity, "white")
            st_color = status_colors.get(r.status, "white")

            table.add_row(
                f"{r.panchayat_name} (#{r.panchayat_id})",
                r.crop_name,
                stage_str,
                r.risk_type.replace("_", " "),
                obs_str,
                thresh_str,
                f"[{s_color}]{r.severity}[/{s_color}]",
                f"[{st_color}]{r.status}[/{st_color}]",
                r.confidence,
                r.rule_version,
            )

        console.print(table)
        console.print(
            Panel.fit(
                f"[bold cyan]Date:[/bold cyan] {evaluation_date} | "
                f"[bold cyan]Total Panchayats:[/bold cyan] {total_panchayats} | "
                f"[bold cyan]Evaluations:[/bold cyan] {total_evaluations} | "
                f"[red]Detected Risks:[/red] {detected_count} | "
                f"[green]Not Detected:[/green] {not_detected_count} | "
                f"[yellow]Insufficient Data:[/yellow] {insufficient_count} | "
                f"[bold magenta]Dry Run:[/bold magenta] {dry_run}\n"
                f"[italic white]Phase 10: Agricultural Risk Assessment. Prescriptive farmer advisories are strictly deferred to Phase 11.[/italic white]",
                title="Risk Summary"
            )
        )
    else:
        print(f"\n=== {title} ===")
        print(f"Date: {evaluation_date} | Dry Run: {dry_run}")
        print(f"{'Panchayat':<18} {'Crop':<10} {'Stage':<15} {'Risk Type':<18} {'Observed':<10} {'Thresh':<10} {'Severity':<10} {'Status':<12} {'Conf':<8}")
        print("-" * 110)
        for r in results:
            obs_str = f"{r.observed_value:.1f}" if r.observed_value is not None else "-"
            thresh_str = f"{r.threshold_value:.1f}" if r.threshold_value is not None else "-"
            stage_str = (r.stage_name or "-")[:14]
            print(f"{r.panchayat_name[:16]:<18} {r.crop_name[:9]:<10} {stage_str:<15} {r.risk_type[:17]:<18} {obs_str:<10} {thresh_str:<10} {r.severity:<10} {r.status:<12} {r.confidence:<8}")
        print("-" * 110)
        print(f"Summary: Panchayats: {total_panchayats} | Evaluations: {total_evaluations} | Detected: {detected_count} | Not Detected: {not_detected_count} | Insufficient: {insufficient_count}\n")


if __name__ == "__main__":
    main()
