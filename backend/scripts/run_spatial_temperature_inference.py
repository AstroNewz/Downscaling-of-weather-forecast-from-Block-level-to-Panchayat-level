"""
CLI Tool: Run 1-km Spatial Weather Temperature Downscaling Inference
SIH Problem Statement 26074 (Weather Downscaling)

Usage:
  python scripts/run_spatial_temperature_inference.py --block-id 1 --valid-time 2026-01-15T12:00:00 --dry-run
  python scripts/run_spatial_temperature_inference.py --block-id 1 --valid-time 2026-01-15T12:00:00 --model-version v1.0.0
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
from app.services.spatial_inference import SpatialTemperatureInferenceService

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def main():
    parser = argparse.ArgumentParser(
        description="Execute 1-km Spatial Temperature Downscaling Inference across a Block (SIH 26074)"
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
        help=f"Target ML model version (default: {settings.TEMPERATURE_MODEL_VERSION})"
    )
    parser.add_argument(
        "--resolution-km",
        type=float,
        default=1.0,
        help="Spatial grid resolution in kilometers (default: 1.0)"
    )
    parser.add_argument(
        "--dem-raster",
        type=str,
        default=None,
        help="Optional file path to DEM GeoTIFF raster"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run spatial grid downscaling without writing records to database"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Disable GeoParquet and GeoJSON disk export"
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
                f"[bold green]SIH 26074 - 1-km Spatial Weather Downscaling Engine[/bold green]\n"
                f"Target Block ID: [cyan]{args.block_id}[/cyan] | Valid Time: [yellow]{args.valid_time}[/yellow]\n"
                f"Model Version: [magenta]{args.model_version}[/magenta] | Target Resolution: [bold]{args.resolution_km} km (1000m x 1000m)[/bold]",
                title="Phase 7 Spatial Inference",
                expand=False
            )
        )
    else:
        print(f"Starting 1-km spatial downscaling for Block ID {args.block_id} at {args.valid_time}...")

    db = SessionLocal()
    try:
        service = SpatialTemperatureInferenceService(
            db=db,
            dem_raster_path=args.dem_raster
        )
        response = service.run_spatial_downscaling(
            block_id=args.block_id,
            forecast_valid_time=valid_dt,
            forecast_issue_time=issue_dt,
            source_model=args.source_model,
            model_version=args.model_version,
            grid_resolution_km=args.resolution_km,
            persist_to_db=not args.dry_run,
            export_geoparquet=not args.no_export,
            include_cell_payload=False
        )
    except Exception as e:
        if console:
            console.print(f"[bold red]Spatial Downscaling Failed:[/bold red] {e}")
        else:
            print(f"Spatial Downscaling Failed: {e}")
        sys.exit(1)
    finally:
        db.close()

    summary = response.quality_summary

    if console:
        # Spatial Grid Dimension Table
        grid_table = Table(title="1-km Spatial Grid & Coordinate Reference System (CRS)")
        grid_table.add_column("Property", style="cyan")
        grid_table.add_column("Value", style="bold yellow")
        grid_table.add_row("Total Generated Cells", str(summary.total_grid_cells))
        grid_table.add_row("Projected Metric CRS", response.projected_crs)
        grid_table.add_row("Requested Resolution", f"{response.grid_resolution_km:.2f} km ({response.grid_resolution_km * 1000:.1f} m)")
        grid_table.add_row("Actual Measured Resolution", f"{response.actual_resolution_m:.2f} m (width) x {response.actual_resolution_m:.2f} m (height)")
        grid_table.add_row("Boundary Inclusion Rule", response.boundary_rule)
        grid_table.add_row("Spatial Coverage %", f"{summary.spatial_coverage_pct:.2f}%")
        console.print(grid_table)

        # Temperature Field Diagnostics Table
        stats_table = Table(title="Downscaled Temperature Field Diagnostics")
        stats_table.add_column("Diagnostic Metric", style="cyan")
        stats_table.add_column("Downscaled Temperature (°C)", style="green")
        stats_table.add_column("Predicted Residual (ΔT °C)", style="magenta")

        stats_table.add_row(
            "Minimum",
            f"{summary.min_temperature_c:.2f}°C" if summary.min_temperature_c is not None else "N/A",
            f"{summary.min_residual_c:+.3f}°C" if summary.min_residual_c is not None else "N/A"
        )
        stats_table.add_row(
            "Maximum",
            f"{summary.max_temperature_c:.2f}°C" if summary.max_temperature_c is not None else "N/A",
            f"{summary.max_residual_c:+.3f}°C" if summary.max_residual_c is not None else "N/A"
        )
        stats_table.add_row(
            "Mean",
            f"{summary.mean_temperature_c:.2f}°C" if summary.mean_temperature_c is not None else "N/A",
            f"{summary.mean_residual_c:+.3f}°C" if summary.mean_residual_c is not None else "N/A"
        )
        stats_table.add_row(
            "Standard Deviation",
            f"{summary.std_temperature_c:.2f}°C" if summary.std_temperature_c is not None else "N/A",
            "N/A"
        )
        console.print(stats_table)

        # Export Files Panel
        if response.geoparquet_path:
            console.print(f"[bold green]✓ GeoParquet Export:[/bold green] {response.geoparquet_path}")
        if response.geojson_path:
            console.print(f"[bold green]✓ GeoJSON Export:[/bold green] {response.geojson_path}")

        console.print(
            Panel(
                "[dim]✓ Panchayat aggregation NOT implemented in Phase 7 (deferred to Phase 8).\n"
                "✓ Rainfall downscaling NOT implemented in Phase 7.\n"
                "✓ No new ML training performed in Phase 7.[/dim]",
                title="Scope Verification",
                expand=False
            )
        )
    else:
        print(f"\n--- 1-km Spatial Downscaling Results ---")
        print(f"Total Cells: {summary.total_grid_cells}, Valid: {summary.successful_predictions} ({summary.spatial_coverage_pct:.1f}%)")
        print(f"Downscaled Temp: Min={summary.min_temperature_c}°C, Max={summary.max_temperature_c}°C, Mean={summary.mean_temperature_c}°C")
        print(f"GeoParquet Export: {response.geoparquet_path}")


if __name__ == "__main__":
    main()
