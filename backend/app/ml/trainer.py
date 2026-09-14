"""
Downscaling Model Trainer & Orchestrator
SIH Problem Statement 26074 (Weather Downscaling)

Orchestrates dataset ingestion, leakage verification, chronological splitting,
XGBoost training with early stopping, benchmark evaluation, and model registry persistence.
"""
import os
from typing import Optional, Dict, Any, Tuple, List
import pandas as pd
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.ml.feature_manifest import (
    ALL_PREDICTOR_FEATURES,
    PRIMARY_TARGET_COLUMN,
    OBSERVED_TEMP_COLUMN,
    COARSE_TEMP_COLUMN,
    validate_no_leakage,
    extract_features_and_target,
)
from app.ml.schemas import FEATURE_SCHEMA_VERSION
from app.ml.metadata import (
    ModelProvenance,
    HyperparameterConfig,
    ModelMetadata,
    ModelMetricsSummary,
    FeatureImportanceItem,
)
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel
from app.ml.evaluator import DownscalingModelEvaluator
from app.ml.registry import LocalModelRegistry
from app.ml.splitting import TimeSeriesSplitter


class DownscalingModelTrainer:
    """
    End-to-end trainer for temperature downscaling models.
    """

    def __init__(
        self,
        registry: Optional[LocalModelRegistry] = None,
        evaluator: Optional[DownscalingModelEvaluator] = None
    ):
        self.registry = registry or LocalModelRegistry()
        self.evaluator = evaluator or DownscalingModelEvaluator()

    def train_from_dataframe(
        self,
        df: pd.DataFrame,
        model_version: str = "v1.0.0",
        dataset_version: str = "v1.0.0",
        dataset_path: Optional[str] = None,
        hyperparameters: Optional[HyperparameterConfig] = None,
        features_to_use: List[str] = ALL_PREDICTOR_FEATURES,
        min_train_rows: Optional[int] = None,
        allow_synthetic: Optional[bool] = None,
        random_seed: Optional[int] = None,
        dry_run: bool = False,
        is_synthetic: bool = False
    ) -> Tuple[XGBoostTemperatureResidualModel, ModelMetadata, ModelMetricsSummary, List[FeatureImportanceItem]]:
        """
        Executes end-to-end training pipeline on a pandas DataFrame.
        """
        seed = random_seed if random_seed is not None else settings.ML_RANDOM_SEED
        min_rows = min_train_rows if min_train_rows is not None else settings.ML_MIN_TRAIN_ROWS
        permit_synthetic = allow_synthetic if allow_synthetic is not None else settings.ML_ALLOW_SYNTHETIC_TRAINING
        params = hyperparameters or HyperparameterConfig()

        total_rows = len(df)
        logger.info(f"Starting ML downscaling training for version '{model_version}' with {total_rows} total rows...")

        # 1. Scientific Data Policy Guard
        if total_rows < min_rows and not permit_synthetic and not is_synthetic:
            raise ValueError(
                f"INSUFFICIENT REAL DATA FOR TRAINING: Dataset contains {total_rows} rows, "
                f"but minimum required is {min_rows}. Real ground-truth AWS observations must be "
                f"ingested before operational model training."
            )

        # 2. Strict Leakage Verification
        is_valid, leaked = validate_no_leakage(features_to_use)
        if not is_valid:
            raise ValueError(f"CRITICAL: Data leakage detected! Quarantined features present: {leaked}")

        # 3. Ensure Chronological Splits
        if "split" not in df.columns or df["split"].isnull().all():
            splitter = TimeSeriesSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
            df = splitter.split(df, time_col="observation_time" if "observation_time" in df.columns else None)

        train_df = df[df["split"] == "train"].copy()
        val_df = df[df["split"] == "val"].copy()
        test_df = df[df["split"] == "test"].copy()

        if len(train_df) == 0:
            raise ValueError("Training split is empty! Ensure valid chronological partition.")

        logger.info(
            f"Split sizes -> Train: {len(train_df)}, Validation: {len(val_df)}, Test: {len(test_df)}"
        )

        # 4. Extract Predictor Matrix X and Targets
        X_train, y_train, obs_train, coarse_train = extract_features_and_target(train_df, features_to_use)
        X_val, y_val, obs_val, coarse_val = extract_features_and_target(val_df, features_to_use)
        X_test, y_test, obs_test, coarse_test = extract_features_and_target(test_df, features_to_use)

        # 5. Instantiate and Fit XGBoost Model
        model = XGBoostTemperatureResidualModel(
            model_name="xgboost_temperature_residual",
            version=model_version,
            hyperparameters=params,
            random_seed=seed
        )
        model.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val if len(X_val) > 0 else None,
            y_val=y_val if len(y_val) > 0 else None
        )

        # 6. Comprehensive Evaluation against Baseline
        train_data = {"X": X_train, "y": y_train, "obs_temp": obs_train, "coarse_temp": coarse_train}
        val_data = {"X": X_val, "y": y_val, "obs_temp": obs_val, "coarse_temp": coarse_val}
        test_data = {"X": X_test, "y": y_test, "obs_temp": obs_test, "coarse_temp": coarse_test}

        metrics_summary = self.evaluator.evaluate_all_splits(
            model=model,
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            best_iteration=model.best_iteration
        )

        # 7. Extract Feature Importances
        feature_importances = model.get_ranked_feature_importances()

        # 8. Assemble Metadata
        provenance = ModelProvenance(
            dataset_version=dataset_version,
            dataset_path=dataset_path,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            train_row_count=len(train_df),
            validation_row_count=len(val_df),
            test_row_count=len(test_df),
            total_row_count=total_rows,
            random_seed=seed,
            is_synthetic=is_synthetic
        )

        metadata = ModelMetadata(
            model_name="xgboost_temperature_residual",
            model_version=model_version,
            model_type="GradientBoostedDecisionTrees",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            features_used=features_to_use,
            provenance=provenance,
            hyperparameters=params,
            metrics_summary=metrics_summary
        )

        # 9. Register Artifacts to Disk
        if not dry_run:
            self.registry.save_model_artifact(
                model=model,
                metadata=metadata,
                metrics=metrics_summary,
                feature_importances=feature_importances
            )

        return model, metadata, metrics_summary, feature_importances

    def train_from_file(
        self,
        dataset_filepath: str,
        model_version: str = "v1.0.0",
        dataset_version: str = "v1.0.0",
        hyperparameters: Optional[HyperparameterConfig] = None,
        dry_run: bool = False,
        is_synthetic: bool = False
    ) -> Tuple[XGBoostTemperatureResidualModel, ModelMetadata, ModelMetricsSummary, List[FeatureImportanceItem]]:
        """
        Loads dataset from Parquet or CSV and runs training pipeline.
        """
        if not os.path.exists(dataset_filepath):
            raise FileNotFoundError(f"Dataset file not found at {dataset_filepath}")

        if dataset_filepath.endswith(".parquet"):
            df = pd.read_parquet(dataset_filepath)
        elif dataset_filepath.endswith(".csv"):
            df = pd.read_csv(dataset_filepath)
        else:
            raise ValueError("Unsupported dataset format. Must be .parquet or .csv")

        return self.train_from_dataframe(
            df=df,
            model_version=model_version,
            dataset_version=dataset_version,
            dataset_path=dataset_filepath,
            hyperparameters=hyperparameters,
            dry_run=dry_run,
            is_synthetic=is_synthetic
        )
