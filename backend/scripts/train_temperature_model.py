"""
CLI Tool: Train and Evaluate Temperature Downscaling Model
SIH Problem Statement 26074 (Weather Downscaling)

Usage:
  python scripts/train_temperature_model.py --dataset-path data/processed/weather_downscale_train_v1.0.0.parquet
  python scripts/train_temperature_model.py --version v1.0.0 --allow-synthetic
"""
import os
import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings
from app.core.logging import logger
from app.ml.metadata import HyperparameterConfig
from app.ml.trainer import DownscalingModelTrainer
from app.ml.registry import LocalModelRegistry

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None


def main():
    parser = argparse.ArgumentParser(
        description="Train XGBoost Temperature Residual Downscaling Model (SIH 26074)"
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default=None,
        help="Path to Parquet or CSV training dataset"
    )
    parser.add_argument(
        "--version",
        type=str,
        default=settings.TEMPERATURE_MODEL_VERSION,
        help=f"Target model version string (default: {settings.TEMPERATURE_MODEL_VERSION})"
    )
    parser.add_argument(
        "--dataset-version",
        type=str,
        default="v1.0.0",
        help="Dataset version identifier (default: v1.0.0)"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.05,
        help="XGBoost learning rate (default: 0.05)"
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=200,
        help="Maximum boosting trees (default: 200)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum tree depth (default: 5)"
    )
    parser.add_argument(
        "--early-stopping",
        type=int,
        default=15,
        help="Validation early stopping rounds (default: 15)"
    )
    parser.add_argument(
        "--min-train-rows",
        type=int,
        default=settings.ML_MIN_TRAIN_ROWS,
        help=f"Minimum training samples required (default: {settings.ML_MIN_TRAIN_ROWS})"
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Permit training on synthetic fixtures for development/testing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run training and evaluation without persisting model artifact to registry"
    )

    args = parser.parse_args()

    dataset_path = args.dataset_path
    if not dataset_path:
        default_path = os.path.join(
            settings.DATASET_OUTPUT_DIR,
            f"weather_downscale_train_{args.dataset_version}.parquet"
        )
        if os.path.exists(default_path):
            dataset_path = default_path
        else:
            print(f"[ERROR] No dataset provided and default dataset '{default_path}' not found.")
            print("Please build a dataset first using 'python scripts/build_weather_dataset.py' or provide --dataset-path.")
            sys.exit(1)

    hyperparams = HyperparameterConfig(
        algorithm="xgboost",
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        max_depth=args.max_depth,
        early_stopping_rounds=args.early_stopping,
    )

    trainer = DownscalingModelTrainer()

    if console:
        console.print(
            Panel(
                f"[bold green]SIH 26074 ML Downscaling Training Engine[/bold green]\n"
                f"Model Version: [cyan]{args.version}[/cyan] | Dataset: [yellow]{dataset_path}[/yellow]\n"
                f"Algorithm: [bold]XGBoost Regressor[/bold] | Target: [magenta]temperature_residual_c[/magenta]",
                title="ML Temperature Downscaling",
                expand=False
            )
        )
    else:
        print(f"Starting training for {args.version} on {dataset_path}...")

    try:
        model, metadata, metrics, importances = trainer.train_from_file(
            dataset_filepath=dataset_path,
            model_version=args.version,
            dataset_version=args.dataset_version,
            hyperparameters=hyperparams,
            dry_run=args.dry_run,
            is_synthetic=args.allow_synthetic
        )
    except Exception as e:
        if console:
            console.print(f"[bold red]Training Failed:[/bold red] {e}")
        else:
            print(f"Training Failed: {e}")
        sys.exit(1)

    # Display Metrics Table
    if console:
        table = Table(title=f"Baseline vs Downscaled Performance (Model {args.version})")
        table.add_column("Split", style="cyan")
        table.add_column("Samples", style="dim")
        table.add_column("Baseline MAE", style="red")
        table.add_column("Model MAE", style="green")
        table.add_column("MAE Imp %", style="bold green")
        table.add_column("Baseline RMSE", style="red")
        table.add_column("Model RMSE", style="green")
        table.add_column("RMSE Imp %", style="bold green")

        for eval_item in [metrics.train_evaluation, metrics.validation_evaluation, metrics.test_evaluation]:
            table.add_row(
                eval_item.split_name.capitalize(),
                str(eval_item.baseline_metrics.sample_count),
                f"{eval_item.baseline_metrics.mae:.3f}°C",
                f"{eval_item.model_metrics.mae:.3f}°C",
                f"{eval_item.mae_improvement_pct:+.2f}%",
                f"{eval_item.baseline_metrics.rmse:.3f}°C",
                f"{eval_item.model_metrics.rmse:.3f}°C",
                f"{eval_item.rmse_improvement_pct:+.2f}%",
            )
        console.print(table)

        # Display Top 10 Feature Importances
        imp_table = Table(title="Top 10 Feature Importances (Gain)")
        imp_table.add_column("Rank", style="dim")
        imp_table.add_column("Feature Name", style="cyan")
        imp_table.add_column("Gain", style="bold yellow")
        imp_table.add_column("Frequency (Weight)", style="dim")
        imp_table.add_column("Cover", style="dim")

        for feat in importances[:10]:
            imp_table.add_row(
                str(feat.rank),
                feat.feature_name,
                f"{feat.gain:.4f}",
                str(feat.weight),
                f"{feat.cover:.4f}"
            )
        console.print(imp_table)
        console.print(f"[bold green]✓[/bold green] Model successfully registered to {settings.ML_MODEL_DIR}{args.version}/")
    else:
        print("\n--- Model Evaluation Summary ---")
        for eval_item in [metrics.train_evaluation, metrics.validation_evaluation, metrics.test_evaluation]:
            print(
                f"{eval_item.split_name}: Baseline MAE={eval_item.baseline_metrics.mae:.3f}°C, "
                f"Model MAE={eval_item.model_metrics.mae:.3f}°C ({eval_item.mae_improvement_pct:+.2f}% imp)"
            )
        print(f"\nModel registered to {settings.ML_MODEL_DIR}{args.version}/")


if __name__ == "__main__":
    main()
