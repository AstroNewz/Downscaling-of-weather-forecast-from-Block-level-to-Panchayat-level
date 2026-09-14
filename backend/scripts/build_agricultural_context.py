"""
CLI Tool: Build Panchayat Agricultural Context (Crop + Stage + Soil + Weather)
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Usage:
  python scripts/build_agricultural_context.py --block-id 1 --date 2026-01-15 --dry-run
  python scripts/build_agricultural_context.py --panchayat-id 1 --date 2026-01-15
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
from app.services.agricultural_context import AgriculturalContextService

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def main():
    parser = argparse.ArgumentParser(
        description="Build Panchayat Agricultural Context: Crop + Stage + Soil + Weather (SIH 26074)"
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
        "--date",
        type=str,
        default=None,
        help="Target context date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, defaults to now)"
    )
    parser.add_argument(
        "--source-model",
        type=str,
        default="IMD-GFS",
        help="Source NWP forecast model identifier (default: IMD-GFS)"
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default=None,
        help="Phase 6 model version (defaults to active configuration)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute context construction without persisting records to database"
    )

    args = parser.parse_args()

    if args.block_id is None and args.panchayat_id is None:
        parser.error("Either --block-id or --panchayat-id must be provided.")

    if args.date:
        try:
            if "T" in args.date:
                context_dt = datetime.fromisoformat(args.date)
            else:
                context_dt = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"[ERROR] Invalid date format: '{args.date}'. Expected YYYY-MM-DD or ISO 8601.")
            sys.exit(1)
    else:
        context_dt = datetime.utcnow()

    db = SessionLocal()
    try:
        service = AgriculturalContextService(db=db)

        if args.panchayat_id is not None:
            # Single Panchayat processing
            contexts = service.build_panchayat_crop_context(
                panchayat_id=args.panchayat_id,
                context_date=context_dt,
                source_model=args.source_model,
                model_version=args.model_version,
                persist_to_db=not args.dry_run,
            )
            total_contexts = len(contexts)
            complete_c = sum(1 for c in contexts if c.status == "COMPLETE")
            partial_c = sum(1 for c in contexts if c.status == "PARTIAL")
            unavail_c = sum(1 for c in contexts if c.status == "UNAVAILABLE")

            print_report(
                title=f"Phase 9 Agricultural Context: Panchayat #{args.panchayat_id}",
                contexts=contexts,
                total_panchayats=1,
                total_contexts=total_contexts,
                complete_count=complete_c,
                partial_count=partial_c,
                unavail_count=unavail_c,
                dry_run=args.dry_run,
                context_date=context_dt.isoformat(),
            )
        else:
            # Block-level batch processing
            response = service.build_block_agricultural_context(
                block_id=args.block_id,
                context_date=context_dt,
                source_model=args.source_model,
                model_version=args.model_version,
                persist_to_db=not args.dry_run,
            )

            print_report(
                title=f"Phase 9 Agricultural Context: Block '{response.block_name}' (ID: {args.block_id})",
                contexts=response.contexts,
                total_panchayats=response.total_panchayats,
                total_contexts=response.total_crop_contexts,
                complete_count=response.complete_contexts_count,
                partial_count=response.partial_contexts_count,
                unavail_count=response.unavailable_contexts_count,
                dry_run=args.dry_run,
                context_date=context_dt.isoformat(),
            )

    except Exception as exc:
        logger.error(f"Execution failed: {str(exc)}", exc_info=True)
        print(f"\n[ERROR] Agricultural context construction failed: {str(exc)}")
        sys.exit(1)
    finally:
        db.close()


def print_report(
    title: str,
    contexts: list,
    total_panchayats: int,
    total_contexts: int,
    complete_count: int,
    partial_count: int,
    unavail_count: int,
    dry_run: bool,
    context_date: str,
):
    if console:
        table = Table(title=title, show_header=True, header_style="bold green")
        table.add_column("Panchayat", style="bold")
        table.add_column("Crop")
        table.add_column("Area (ha)", justify="right")
        table.add_column("Stage")
        table.add_column("Days Post-Plant", justify="right")
        table.add_column("Soil Status")
        table.add_column("Weather Status")
        table.add_column("Overall Status", style="bold")

        for ctx in contexts:
            stage_str = ctx.crop_stage.stage_name or "Unknown"
            if ctx.crop_stage.stage_derivation_method != "UNKNOWN":
                stage_str += f" ({ctx.crop_stage.stage_derivation_method})"

            dsp_str = str(ctx.crop_stage.days_since_planting) if ctx.crop_stage.days_since_planting is not None else "-"
            area_str = f"{ctx.crop_area_ha:.1f}" if ctx.crop_area_ha is not None else "-"

            status_style = "green" if ctx.status == "COMPLETE" else ("yellow" if ctx.status == "PARTIAL" else "red")

            table.add_row(
                f"{ctx.panchayat_name} (#{ctx.panchayat_id})",
                ctx.crop_name,
                area_str,
                stage_str,
                dsp_str,
                ctx.soil.soil_status,
                ctx.weather.weather_status,
                f"[{status_style}]{ctx.status}[/{status_style}]",
            )

        console.print(table)
        console.print(
            Panel.fit(
                f"[bold cyan]Date:[/bold cyan] {context_date} | "
                f"[bold cyan]Total Panchayats:[/bold cyan] {total_panchayats} | "
                f"[bold cyan]Contexts:[/bold cyan] {total_contexts} | "
                f"[green]Complete:[/green] {complete_count} | "
                f"[yellow]Partial:[/yellow] {partial_count} | "
                f"[red]Unavailable:[/red] {unavail_count} | "
                f"[bold magenta]Dry Run:[/bold magenta] {dry_run}\n"
                f"[italic white]Phase 9: Crop + Stage + Soil context. Risk detection & advisories strictly deferred to Phase 10.[/italic white]",
                title="Execution Summary"
            )
        )
    else:
        print(f"\n=== {title} ===")
        print(f"Date: {context_date} | Dry Run: {dry_run}")
        print(f"{'Panchayat':<20} {'Crop':<12} {'Area(ha)':<10} {'Stage':<20} {'DSP':<6} {'Soil':<12} {'Weather':<12} {'Status':<10}")
        print("-" * 100)
        for ctx in contexts:
            stage_str = ctx.crop_stage.stage_name or "Unknown"
            dsp_str = str(ctx.crop_stage.days_since_planting) if ctx.crop_stage.days_since_planting is not None else "-"
            area_str = f"{ctx.crop_area_ha:.1f}" if ctx.crop_area_ha is not None else "-"
            print(f"{ctx.panchayat_name[:18]:<20} {ctx.crop_name[:10]:<12} {area_str:<10} {stage_str[:18]:<20} {dsp_str:<6} {ctx.soil.soil_status:<12} {ctx.weather.weather_status:<12} {ctx.status:<10}")
        print("-" * 100)
        print(f"Summary: Total Panchayats: {total_panchayats} | Contexts: {total_contexts} | Complete: {complete_count} | Partial: {partial_count} | Unavailable: {unavail_count}\n")


if __name__ == "__main__":
    main()
