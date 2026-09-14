"""
CLI Tool: Area-Weighted Panchayat Weather Aggregation from 1-km Downscaled Grid
SIH Problem Statement 26074 (Weather Downscaling)

Usage:
  python scripts/aggregate_panchayat_weather.py --block-id 1 --valid-time 2026-01-15T12:00:00 --dry-run
  python scripts/aggregate_panchayat_weather.py --block-id 1 --valid-time 2026-01-15T12:00:00 --model-version v1.0.0
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
from app.services.panchayat_aggregation import PanchayatWeatherAggregationService

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate Phase 7 1-km Downscaled Grid to Gram Panchayat Level (SIH 26074)"
    )
    parser.add_argument(
        "--block-id",
        type=int,
        required=True,
        help="Database ID of the target Block"
    )
    parser.add_argument(
        "--valid-time",
        type=str,
        required=True,
        help="Target forecast valid time in ISO format (e.g., 2026-01-15T12:00:00)"
    )
    parser.add_argument(
        "--issue-time",
        type=str,
        default=None,
        help="Optional forecast issue timestamp in ISO format"
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
        default=settings.TEMPERATURE_MODEL_VERSION,
        help=f"Phase 6 downscaling model version (default: {settings.TEMPERATURE_MODEL_VERSION})"
    )
    parser.add_argument(
        "--resolution-km",
        type=float,
        default=1.0,
        help="1-km grid resolution (default: 1.0)"
    )
    parser.add_argument(
        "--panchayat-id",
        type=int,
        default=None,
        help="Optional single Panchayat ID filter"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform spatial aggregation without writing records to database"
    )

    args = parser.parse_args()

    try:
        valid_dt = datetime.fromisoformat(args.valid_time)
    except ValueError:
        print(f"[ERROR] Invalid ISO timestamp format for --valid-time: '{args.valid_time}'")
        sys.exit(1)

    issue_dt = datetime.fromisoformat(args.issue_time) if args.issue_time else None

    if console:
        console.print(
            Panel(
                f"[bold green]SIH 26074 - Area-Weighted Panchayat Weather Aggregation[/bold green]\n"
                f"Block ID: [cyan]{args.block_id}[/cyan] | Valid Time: [yellow]{args.valid_time}[/yellow]\n"
                f"Model: [magenta]{args.model_version}[/magenta] | Method: [bold]Area-Weighted Polygon Intersection[/bold]",
                title="Phase 8 Panchayat Aggregation",
                expand=False
            )
        )
    else:
        print(f"Starting area-weighted aggregation for Block ID {args.block_id} at {args.valid_time}...")

    db = SessionLocal()
    try:
        service = PanchayatWeatherAggregationService(db=db)
        response = service.aggregate_block_panchayats(
            block_id=args.block_id,
            forecast_valid_time=valid_dt,
            forecast_issue_time=issue_dt,
            source_model=args.source_model,
            model_version=args.model_version,
            grid_resolution_km=args.resolution_km,
            panchayat_id=args.panchayat_id,
            persist_to_db=not args.dry_run
        )
    except Exception as e:
        if console:
            console.print(f"[bold red]Aggregation Failed:[/bold red] {e}")
        else:
            print(f"Aggregation Failed: {e}")
        sys.exit(1)
    finally:
        db.close()

    if console:
        # Table of Panchayat Weather Statistics
        table = Table(title=f"Gram Panchayat Weather Statistics ({response.block_name} Block)")
        table.add_column("Panchayat (LGD)", style="cyan")
        table.add_column("Area (km²)", style="dim")
        table.add_column("Cells (Valid/Tot)", style="dim")
        table.add_column("Coverage %", style="yellow")
        table.add_column("Mean Temp (°C)", style="bold green")
        table.add_column("Min Temp", style="blue")
        table.add_column("Max Temp", style="red")
        table.add_column("Std Dev", style="dim")
        table.add_column("Status", style="bold")

        for pw in response.panchayat_weather:
            status_style = "green" if pw.quality_status == "COMPLETE" else ("yellow" if pw.quality_status == "PARTIAL" else "red")
            table.add_row(
                f"{pw.panchayat_name} ({pw.lgd_code})",
                f"{pw.total_panchayat_area_sqkm:.2f}",
                f"{pw.valid_grid_cells}/{pw.contributing_grid_cells}",
                f"{pw.coverage_percentage:.1f}%",
                f"{pw.mean_temperature_c:.2f}°C",
                f"{pw.min_temperature_c:.2f}°C",
                f"{pw.max_temperature_c:.2f}°C",
                f"{pw.temperature_stddev_c:.2f}°C" if pw.temperature_stddev_c is not None else "N/A",
                f"[{status_style}]{pw.quality_status}[/{status_style}]"
            )

        console.print(table)

        # Summary Metrics Panel
        console.print(
            Panel(
                f"Total Panchayats: [cyan]{response.total_panchayats_in_block}[/cyan] | "
                f"Complete Coverage (≥95%): [green]{response.complete_coverage_count}[/green] | "
                f"Partial Coverage: [yellow]{response.partial_coverage_count}[/yellow] | "
                f"Unavailable: [red]{response.unavailable_count}[/red]\n"
                f"Overall Block Area Coverage: [bold yellow]{response.overall_block_coverage_pct:.2f}%[/bold yellow]",
                title="Aggregation Summary",
                expand=False
            )
        )
    else:
        print("\n--- Panchayat Weather Aggregation Summary ---")
        for pw in response.panchayat_weather:
            print(
                f"Panchayat: {pw.panchayat_name} ({pw.lgd_code}) | "
                f"Coverage: {pw.coverage_percentage:.1f}% | "
                f"Mean Temp: {pw.mean_temperature_c:.2f}°C [{pw.min_temperature_c:.2f}°C - {pw.max_temperature_c:.2f}°C] | "
                f"Status: {pw.quality_status}"
            )


if __name__ == "__main__":
    main()
