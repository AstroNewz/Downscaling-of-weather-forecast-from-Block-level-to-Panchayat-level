"""
Weather Ingestion CLI Tool
SIH Problem Statement 26074

Usage:
    python scripts/ingest_weather.py --file data/sample/weather_forecast_sample.csv
    python scripts/ingest_weather.py --file data/sample/weather_forecast_sample.csv --dry-run
"""
import sys
import os
import argparse
from typing import Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.weather.ingestion import WeatherIngestionService
from app.weather.providers.csv_provider import CSVWeatherProvider
from app.core.logging import logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agro-Meteorological Weather Ingestion CLI (SIH 26074)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Path to the weather CSV/data file to ingest",
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default="CSV_CLI_INGEST",
        help="Data source label for provenance tracking",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="IMD-GFS",
        help="Source NWP model identifier (e.g. IMD-GFS, NCUM, ECMWF)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation, normalization, and quality checks without saving to the database",
    )
    return parser.parse_args()


def print_summary_report(summary, dry_run: bool):
    separator = "=" * 70
    sub_sep = "-" * 70
    print("\n" + separator)
    print("🌾 AGRO-METEOROLOGICAL WEATHER INGESTION REPORT (SIH 26074)")
    print(separator)
    print(f"Status              : {summary.status}")
    print(f"Execution Mode      : {'DRY RUN (No Database Changes)' if dry_run else 'LIVE PERSISTENCE'}")
    print(f"Source File         : {summary.source_file or 'In-Memory/Stream'}")
    print(f"Source Label        : {summary.source}")
    print(f"Timestamp (UTC)     : {summary.ingested_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if summary.ingestion_id:
        print(f"Raw Audit Record ID : #{summary.ingestion_id}")

    print("\n" + sub_sep)
    print("📊 RECORD PROCESSING METRICS")
    print(sub_sep)
    print(f"Total Rows Read     : {summary.records_read}")
    print(f"Valid Records       : {summary.records_valid}")
    print(f"Suspicious Records  : {summary.records_suspicious} (Flagged with warning notes)")
    print(f"Invalid Records     : {summary.records_invalid} (Rejected due to physical/format limits)")
    print(f"Duplicates Skipped  : {summary.duplicate_records}")
    print(f"Records Inserted    : {summary.records_inserted}")
    print(f"Total Skipped       : {summary.records_skipped}")

    if summary.unit_conversions:
        print("\n" + sub_sep)
        print("🔄 UNIT CONVERSIONS PERFORMED")
        print(sub_sep)
        for conv_type, count in summary.unit_conversions.items():
            print(f"  • {conv_type:<25} : {count} occurrences")

    if summary.missing_value_counts:
        print("\n" + sub_sep)
        print("❓ MISSING VALUES PRESERVED (NULL / NONE)")
        print(sub_sep)
        for field, count in summary.missing_value_counts.items():
            if count > 0:
                print(f"  • {field:<25} : {count} missing")

    if summary.validation_errors:
        print("\n" + sub_sep)
        print("⚠️ VALIDATION ERRORS DETAIL (Top 5)")
        print(sub_sep)
        for err in summary.validation_errors[:5]:
            row_str = f"Row {err.row_number}: " if err.row_number else ""
            print(f"  • {row_str}[{err.field}] Rejected '{err.rejected_value}' -> {err.reason}")
        if len(summary.validation_errors) > 5:
            print(f"  ... and {len(summary.validation_errors) - 5} more error(s).")

    print(separator + "\n")


def main():
    args = parse_args()

    if not os.path.exists(args.file):
        print(f"❌ Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        service = WeatherIngestionService(db=db, default_provider=CSVWeatherProvider())
        options = {
            "source": args.source,
            "model_name": args.model,
        }

        summary = service.ingest(
            source_data=args.file,
            source_file_name=args.file,
            options=options,
            dry_run=args.dry_run
        )

        print_summary_report(summary, args.dry_run)

        if summary.status == "FAILED":
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error during CLI ingestion: {exc}", exc_info=True)
        print(f"❌ Ingestion pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
