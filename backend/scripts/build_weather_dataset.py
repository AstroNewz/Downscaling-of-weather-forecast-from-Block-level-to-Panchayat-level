"""
Weather Downscaling Dataset Construction CLI
SIH Problem Statement 26074

Usage:
    python scripts/build_weather_dataset.py --dataset-version v1.0.0
    python scripts/build_weather_dataset.py --dataset-version v1.0.0 --dry-run
"""
import sys
import os
import argparse
from datetime import datetime
from dateutil import parser as date_parser

# Ensure project root is on sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.core.config import settings
from app.ml.schemas import DatasetBuildConfig
from app.ml.builder import WeatherTrainingDatasetBuilder
from app.core.logging import logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build Coarse-to-Fine Weather Downscaling Dataset (SIH 26074)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset-version",
        "-v",
        type=str,
        default=settings.DATASET_VERSION,
        help="Semantic version identifier for the dataset artifact",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=settings.DATASET_OUTPUT_DIR,
        help="Directory where Parquet and JSON report will be saved",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start datetime for observations filter (ISO format)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End datetime for observations filter (ISO format)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Filter by source NWP model (e.g. IMD-GFS, NCUM)",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=settings.TEMPORAL_MATCH_TOLERANCE_MINUTES,
        help="Max time tolerance in minutes between observation and forecast valid time",
    )
    parser.add_argument(
        "--include-suspicious",
        action="store_true",
        help="Include records flagged as SUSPICIOUS in the dataset",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute alignment and baseline calculations without writing Parquet artifact",
    )
    return parser.parse_args()


def print_dataset_report(report):
    sep = "=" * 75
    sub_sep = "-" * 75
    print("\n" + sep)
    print("🌾 WEATHER DOWNSCALING DATASET BUILD REPORT (SIH 26074)")
    print(sep)
    print(f"Dataset Version         : {report.dataset_version}")
    print(f"Feature Schema Version  : {report.feature_schema_version}")
    print(f"Created At (UTC)        : {report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Status                  : {report.status}")
    print(f"Details                 : {report.details}")

    print("\n" + sub_sep)
    print("📊 ALIGNMENT & FILTERING METRICS")
    print(sub_sep)
    print(f"Observations Considered : {report.observation_records_considered}")
    print(f"Forecasts Considered    : {report.forecast_records_considered}")
    print(f"Spatially Matched       : {report.spatially_matched}")
    print(f"Temporally Matched      : {report.temporally_matched}")
    print(f"Valid Samples           : {report.valid_samples}")
    print(f"Suspicious Samples      : {report.suspicious_samples}")
    print(f"Duplicate Samples       : {report.duplicate_samples}")
    print(f"Excluded Samples        : {report.excluded_samples}")

    if report.exclusion_reasons:
        print("\n" + sub_sep)
        print("🚫 EXCLUSION REASONS BREAKDOWN")
        print(sub_sep)
        for reason, count in report.exclusion_reasons.items():
            print(f"  • {reason:<30} : {count} sample(s)")

    print("\n" + sub_sep)
    print("✂️ CHRONOLOGICAL SPLIT DISTRIBUTION")
    print(sub_sep)
    total_samples = report.train_samples + report.validation_samples + report.test_samples
    print(f"Training Set (Train)    : {report.train_samples:<6} ({report.train_samples/total_samples*100:.1f}%)" if total_samples else "Training Set: 0")
    print(f"Validation Set (Val)    : {report.validation_samples:<6} ({report.validation_samples/total_samples*100:.1f}%)" if total_samples else "Validation Set: 0")
    print(f"Testing Set (Test)      : {report.test_samples:<6} ({report.test_samples/total_samples*100:.1f}%)" if total_samples else "Testing Set: 0")

    if report.overall_baseline.sample_count > 0:
        print("\n" + sub_sep)
        print("🎯 COARSE FORECAST BASELINE ERROR METRICS (Benchmark for future ML)")
        print(sub_sep)
        b = report.overall_baseline
        print(f"  • Mean Absolute Error (MAE)  : {b.mae_celsius}°C")
        print(f"  • Root Mean Squared Error    : {b.rmse_celsius}°C")
        print(f"  • Mean Bias Error (MBE)      : {b.mean_bias_error_celsius}°C")
        print(f"  • Coefficient of Det. (R²)   : {b.r2_score if b.r2_score is not None else 'N/A'}")
        print(f"  • Residual Spread (Min/Max)  : [{b.residual_min}°C, {b.residual_max}°C] (Std: {b.residual_std}°C)")

    if report.parquet_path:
        print("\n" + sub_sep)
        print("💾 EXPORTED ARTIFACTS")
        print(sub_sep)
        print(f"Parquet Dataset Path    : {report.parquet_path}")
        print(f"JSON Quality Report     : {report.report_path}")

    print(sep + "\n")


def main():
    args = parse_args()

    start_dt = date_parser.parse(args.start) if args.start else None
    end_dt = date_parser.parse(args.end) if args.end else None

    config = DatasetBuildConfig(
        dataset_version=args.dataset_version,
        start_time=start_dt,
        end_time=end_dt,
        source_model=args.model,
        temporal_tolerance_minutes=args.tolerance,
        exclude_suspicious=not args.include_suspicious,
        output_dir=args.output,
        dry_run=args.dry_run,
    )

    db = SessionLocal()
    try:
        builder = WeatherTrainingDatasetBuilder(db)
        report = builder.build_dataset(config)
        print_dataset_report(report)

        if report.status not in ["SUCCESS", "EMPTY", "NO_MATCHES"]:
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error during dataset construction: {exc}", exc_info=True)
        print(f"❌ Dataset construction failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
