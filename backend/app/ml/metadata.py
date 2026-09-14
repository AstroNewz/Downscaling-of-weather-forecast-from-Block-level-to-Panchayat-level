"""
ML Metadata & Evaluation Schemas
SIH Problem Statement 26074 (Weather Downscaling)

Defines structured data models for model provenance, hyperparameters,
cross-validation metrics, baseline comparisons, and feature importance.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ModelProvenance(BaseModel):
    """Provenance and audit trail for a trained downscaling model artifact."""
    dataset_version: str = Field(..., description="Dataset version used for training (e.g. 'v1.0.0')")
    dataset_path: Optional[str] = Field(None, description="Path or URI to source dataset")
    feature_schema_version: str = Field(..., description="Feature schema version (e.g. 'v1.1.0')")
    training_timestamp: datetime = Field(default_factory=datetime.utcnow)
    train_row_count: int = Field(..., ge=0)
    validation_row_count: int = Field(..., ge=0)
    test_row_count: int = Field(..., ge=0)
    total_row_count: int = Field(..., ge=0)
    target_variable: str = Field(default="temperature_residual_c")
    coarse_variable: str = Field(default="coarse_forecast_temp_c")
    observed_variable: str = Field(default="observed_temp_c")
    random_seed: int = Field(default=42)
    is_synthetic: bool = Field(default=False, description="True if trained on synthetic test fixtures")


class HyperparameterConfig(BaseModel):
    """Hyperparameters for the downscaling regression model."""
    algorithm: str = Field(default="xgboost", description="ML Algorithm name")
    n_estimators: int = Field(default=200, ge=10, le=2000)
    learning_rate: float = Field(default=0.05, gt=0.0, le=1.0)
    max_depth: int = Field(default=5, ge=1, le=20)
    subsample: float = Field(default=0.8, gt=0.0, le=1.0)
    colsample_bytree: float = Field(default=0.8, gt=0.0, le=1.0)
    min_child_weight: float = Field(default=3.0, ge=0.0)
    reg_alpha: float = Field(default=0.1, ge=0.0)
    reg_lambda: float = Field(default=1.0, ge=0.0)
    early_stopping_rounds: Optional[int] = Field(default=15)
    objective: str = Field(default="reg:squarederror")


class MetricScore(BaseModel):
    """Statistical error metrics for regression evaluation."""
    mae: float = Field(..., description="Mean Absolute Error in degrees Celsius")
    rmse: float = Field(..., description="Root Mean Squared Error in degrees Celsius")
    mbe: float = Field(..., description="Mean Bias Error in degrees Celsius (positive = overpredicting)")
    r2: float = Field(..., description="Coefficient of determination R-squared")
    sample_count: int = Field(..., ge=0)


class SplitEvaluation(BaseModel):
    """Comparative evaluation between Coarse NWP Baseline and ML Downscaled model."""
    split_name: str = Field(..., description="Name of split: 'train', 'validation', or 'test'")
    baseline_metrics: MetricScore = Field(..., description="Raw coarse NWP forecast vs observation")
    model_metrics: MetricScore = Field(..., description="ML downscaled forecast (T_coarse + y_pred) vs observation")
    mae_improvement_c: float = Field(..., description="Reduction in MAE (baseline_mae - model_mae)")
    mae_improvement_pct: float = Field(..., description="Percentage improvement in MAE relative to baseline")
    rmse_improvement_c: float = Field(..., description="Reduction in RMSE (baseline_rmse - model_rmse)")
    rmse_improvement_pct: float = Field(..., description="Percentage improvement in RMSE relative to baseline")
    mbe_reduction_c: float = Field(..., description="Reduction in absolute bias (|baseline_mbe| - |model_mbe|)")


class ModelMetricsSummary(BaseModel):
    """Full evaluation metrics across train, validation, and test splits."""
    train_evaluation: SplitEvaluation
    validation_evaluation: SplitEvaluation
    test_evaluation: SplitEvaluation
    best_iteration: Optional[int] = None
    overall_status: str = Field(default="EVALUATED")


class FeatureImportanceItem(BaseModel):
    """Feature importance metrics for model explainability."""
    feature_name: str
    gain: float = Field(..., description="Relative contribution of the feature to the model (Gain)")
    weight: int = Field(..., description="Number of times a feature appears in a tree (Frequency/Weight)")
    cover: float = Field(..., description="Relative quantity of observations concerned by a feature (Cover)")
    rank: int = Field(..., ge=1, description="Importance rank (1 = most important)")


class ModelMetadata(BaseModel):
    """Comprehensive metadata bundle stored alongside model binary."""
    model_name: str = Field(default="xgboost_temperature_residual")
    model_version: str = Field(..., description="Semantic version string e.g. 'v1.0.0'")
    model_type: str = Field(default="GradientBoostedDecisionTrees")
    feature_schema_version: str = Field(..., description="Feature schema version (e.g. 'v1.1.0')")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    features_used: List[str] = Field(..., description="Authoritative ordered list of predictor features")
    provenance: ModelProvenance
    hyperparameters: HyperparameterConfig
    metrics_summary: Optional[ModelMetricsSummary] = None
