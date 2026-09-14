"""
ML Schemas for API Requests & Responses
SIH Problem Statement 26074 (Weather Downscaling)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.ml.schemas import BaselineMetrics, DatasetQualityReport, FEATURE_SCHEMA_VERSION
from app.ml.metadata import (
    ModelMetadata,
    ModelMetricsSummary,
    FeatureImportanceItem,
    HyperparameterConfig,
    SplitEvaluation,
)


class DatasetStatusResponse(BaseModel):
    """Metadata and operational status for ML downscaling dataset engineering."""
    module: str = "ML Downscaling Dataset Engine"
    phase: str = "Phase 4 Preprocessing & Dataset Engineering"
    dataset_version: str = "v1.0.0"
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    target_variable: str = "temperature_residual_c = observed_temp - coarse_forecast_temp"
    dataset_output_dir: str = "data/processed/"
    available_datasets: List[str] = Field(default_factory=list)
    latest_report: Optional[DatasetQualityReport] = None


class DatasetBuildRequest(BaseModel):
    """API request schema for triggering dataset construction."""
    dataset_version: str = Field(default="v1.0.0", description="Semantic dataset version string")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    source_model: Optional[str] = None
    temporal_tolerance_minutes: int = Field(default=180, ge=0)
    exclude_suspicious: bool = Field(default=True)
    train_ratio: float = Field(default=0.70, ge=0.0, le=1.0)
    validation_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    dry_run: bool = Field(default=False)


class ModelSummary(BaseModel):
    """Summary record for registered downscaling models."""
    version: str
    model_name: str
    model_type: str
    feature_schema_version: str
    feature_count: int
    created_at: str
    is_active: bool
    is_synthetic: bool
    train_rows: int
    test_mae: Optional[float] = None
    test_mae_improvement_pct: Optional[float] = None


class ModelListResponse(BaseModel):
    """List of all registered models."""
    total_models: int
    active_version: str
    models: List[ModelSummary]


class TemperaturePredictionRequest(BaseModel):
    """Real-time request for point-level temperature downscaling."""
    coarse_forecast_temp_c: float = Field(..., description="Coarse block-level forecast temperature in °C", ge=-30.0, le=60.0)
    features: Dict[str, float] = Field(..., description="Dictionary of operational predictors matching Schema v1.1.0")
    model_version: Optional[str] = Field(None, description="Optional target model version (defaults to active)")


class TemperaturePredictionResponse(BaseModel):
    """Downscaling inference result with diagnostic indicators."""
    downscaled_temperature_c: float = Field(..., description="Predicted high-resolution temperature in °C")
    coarse_forecast_temp_c: float = Field(..., description="Input coarse forecast temperature in °C")
    predicted_residual_c: float = Field(..., description="Learned residual offset added to coarse forecast (y_pred)")
    raw_residual_c: float = Field(..., description="Unclamped model raw residual prediction")
    model_version: str = Field(..., description="Model version used for inference")
    feature_schema_version: str = Field(..., description="Feature schema version (e.g. v1.1.0)")
    lapse_rate_adjustment_c: Optional[float] = Field(None, description="Physical elevation lapse rate component")
    topographic_slope_deg: Optional[float] = Field(None, description="Terrain slope angle")
    is_physically_clamped: bool = Field(..., description="True if prediction exceeded physical limits and was clamped")
    inference_timestamp: str = Field(..., description="ISO UTC timestamp of inference execution")


class ModelTrainRequest(BaseModel):
    """Request schema for triggering downscaling model training."""
    model_version: str = Field(default="v1.0.0", description="Version string for new model artifact")
    dataset_version: str = Field(default="v1.0.0", description="Version of source dataset")
    dataset_path: Optional[str] = Field(None, description="Optional explicit Parquet/CSV file path")
    hyperparameters: Optional[HyperparameterConfig] = None
    allow_synthetic: bool = Field(default=False, description="Explicit flag allowing training on synthetic test fixtures")
    min_train_rows: Optional[int] = Field(default=None, description="Override minimum row constraint")
    dry_run: bool = Field(default=False, description="Run training without persisting model to registry")
