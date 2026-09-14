"""
Downscaling Model Evaluator & Benchmark Engine
SIH Problem Statement 26074 (Weather Downscaling)

Computes statistical error metrics (MAE, RMSE, MBE, R²) and comparative
improvement percentages between Coarse NWP Baselines and ML Downscaled predictions.
"""
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.ml.metadata import MetricScore, SplitEvaluation, ModelMetricsSummary
from app.ml.models.base import BaseDownscalingModel
from app.core.logging import logger


class DownscalingModelEvaluator:
    """
    Evaluates ML Downscaling models against coarse NWP baseline forecasts across dataset splits.
    """

    @staticmethod
    def calculate_metric_score(y_true: np.ndarray, y_pred: np.ndarray) -> MetricScore:
        """
        Computes MAE, RMSE, MBE, and R² for true vs predicted series.
        """
        n_samples = len(y_true)
        if n_samples == 0:
            return MetricScore(mae=0.0, rmse=0.0, mbe=0.0, r2=0.0, sample_count=0)

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        mbe = float(np.mean(y_pred - y_true))

        # R² requires at least 2 samples and non-zero variance
        if n_samples >= 2 and np.var(y_true) > 1e-9:
            r2 = float(r2_score(y_true, y_pred))
        else:
            r2 = 0.0

        return MetricScore(
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            mbe=round(mbe, 4),
            r2=round(r2, 4),
            sample_count=n_samples
        )

    def evaluate_split(
        self,
        split_name: str,
        model: BaseDownscalingModel,
        X: pd.DataFrame,
        y_residual_true: pd.Series,
        obs_temp: pd.Series,
        coarse_temp: pd.Series
    ) -> SplitEvaluation:
        """
        Computes comparative metrics on a single data split.
        """
        n_samples = len(X)
        if n_samples == 0:
            empty_metric = MetricScore(mae=0.0, rmse=0.0, mbe=0.0, r2=0.0, sample_count=0)
            return SplitEvaluation(
                split_name=split_name,
                baseline_metrics=empty_metric,
                model_metrics=empty_metric,
                mae_improvement_c=0.0,
                mae_improvement_pct=0.0,
                rmse_improvement_c=0.0,
                rmse_improvement_pct=0.0,
                mbe_reduction_c=0.0
            )

        y_obs = np.asarray(obs_temp, dtype=np.float64)
        y_coarse = np.asarray(coarse_temp, dtype=np.float64)

        # Baseline: Raw coarse forecast vs observed
        baseline_metrics = self.calculate_metric_score(y_true=y_obs, y_pred=y_coarse)

        # ML Model: Predicted fine temperature = coarse + predicted residual
        predicted_residuals = model.predict(X)
        y_fine_pred = y_coarse + predicted_residuals
        model_metrics = self.calculate_metric_score(y_true=y_obs, y_pred=y_fine_pred)

        # Improvements
        mae_delta = baseline_metrics.mae - model_metrics.mae
        mae_pct = (mae_delta / baseline_metrics.mae * 100.0) if baseline_metrics.mae > 1e-6 else 0.0

        rmse_delta = baseline_metrics.rmse - model_metrics.rmse
        rmse_pct = (rmse_delta / baseline_metrics.rmse * 100.0) if baseline_metrics.rmse > 1e-6 else 0.0

        mbe_reduction = abs(baseline_metrics.mbe) - abs(model_metrics.mbe)

        logger.info(
            f"Split '{split_name}' Evaluation -> Baseline MAE: {baseline_metrics.mae}°C, "
            f"Model MAE: {model_metrics.mae}°C ({mae_pct:+.2f}% imp), "
            f"Baseline RMSE: {baseline_metrics.rmse}°C, Model RMSE: {model_metrics.rmse}°C ({rmse_pct:+.2f}% imp)"
        )

        return SplitEvaluation(
            split_name=split_name,
            baseline_metrics=baseline_metrics,
            model_metrics=model_metrics,
            mae_improvement_c=round(mae_delta, 4),
            mae_improvement_pct=round(mae_pct, 2),
            rmse_improvement_c=round(rmse_delta, 4),
            rmse_improvement_pct=round(rmse_pct, 2),
            mbe_reduction_c=round(mbe_reduction, 4)
        )

    def evaluate_all_splits(
        self,
        model: BaseDownscalingModel,
        train_data: Dict[str, Any],
        val_data: Dict[str, Any],
        test_data: Dict[str, Any],
        best_iteration: Optional[int] = None
    ) -> ModelMetricsSummary:
        """
        Runs comprehensive evaluation over train, validation, and test sets.
        Each data dict should contain: 'X', 'y', 'obs_temp', 'coarse_temp'.
        """
        train_eval = self.evaluate_split(
            split_name="train",
            model=model,
            X=train_data["X"],
            y_residual_true=train_data["y"],
            obs_temp=train_data["obs_temp"],
            coarse_temp=train_data["coarse_temp"]
        )

        val_eval = self.evaluate_split(
            split_name="validation",
            model=model,
            X=val_data["X"],
            y_residual_true=val_data["y"],
            obs_temp=val_data["obs_temp"],
            coarse_temp=val_data["coarse_temp"]
        )

        test_eval = self.evaluate_split(
            split_name="test",
            model=model,
            X=test_data["X"],
            y_residual_true=test_data["y"],
            obs_temp=test_data["obs_temp"],
            coarse_temp=test_data["coarse_temp"]
        )

        return ModelMetricsSummary(
            train_evaluation=train_eval,
            validation_evaluation=val_eval,
            test_evaluation=test_eval,
            best_iteration=best_iteration,
            overall_status="EVALUATED"
        )
