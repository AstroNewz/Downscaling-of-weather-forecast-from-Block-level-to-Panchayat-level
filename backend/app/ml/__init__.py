"""
Machine Learning Downscaling Subsystem.
SIH Problem Statement 26074 (Weather Downscaling)

Modular ML components for:
- Preprocessing & Alignment (Temporal, Spatial, Topographic, Land-Use)
- Dataset Construction (Feature matrix X, Residual target y, Chronological splitting)
- Feature Manifest & Leakage Quarantine
- Model Architectures (XGBoost Regressor)
- Model Training & Cross-Validation with Early Stopping
- Model Evaluation & Baseline Benchmarking (MAE, RMSE, MBE, R²)
- Filesystem Model Registry
- Real-time Temperature Downscaling Predictor
"""
from app.ml.schemas import (
    DatasetBuildConfig,
    DatasetQualityReport,
    EngineeredFeatureRecord,
    BaselineMetrics,
    FEATURE_SCHEMA_VERSION,
)
from app.ml.temporal import TemporalAligner
from app.ml.spatial import SpatialAligner
from app.ml.features import FeatureEngineer
from app.ml.splitting import TimeSeriesSplitter
from app.ml.baseline import BaselineEvaluator
from app.ml.builder import WeatherTrainingDatasetBuilder
from app.ml.feature_manifest import (
    ALL_PREDICTOR_FEATURES,
    QUARANTINED_LEAKAGE_COLUMNS,
    FORECAST_PREDICTORS,
    TEMPORAL_PREDICTORS,
    SPATIAL_TOPOGRAPHIC_PREDICTORS,
    LANDUSE_PREDICTORS,
    validate_no_leakage,
    extract_features_and_target,
)
from app.ml.metadata import (
    ModelProvenance,
    HyperparameterConfig,
    MetricScore,
    SplitEvaluation,
    ModelMetricsSummary,
    FeatureImportanceItem,
    ModelMetadata,
)
from app.ml.models.base import BaseDownscalingModel
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel
from app.ml.evaluator import DownscalingModelEvaluator
from app.ml.registry import LocalModelRegistry
from app.ml.trainer import DownscalingModelTrainer
from app.ml.predictor import TemperatureDownscalingPredictor

__all__ = [
    "DatasetBuildConfig",
    "DatasetQualityReport",
    "EngineeredFeatureRecord",
    "BaselineMetrics",
    "FEATURE_SCHEMA_VERSION",
    "TemporalAligner",
    "SpatialAligner",
    "FeatureEngineer",
    "TimeSeriesSplitter",
    "BaselineEvaluator",
    "WeatherTrainingDatasetBuilder",
    "ALL_PREDICTOR_FEATURES",
    "QUARANTINED_LEAKAGE_COLUMNS",
    "FORECAST_PREDICTORS",
    "TEMPORAL_PREDICTORS",
    "SPATIAL_TOPOGRAPHIC_PREDICTORS",
    "LANDUSE_PREDICTORS",
    "validate_no_leakage",
    "extract_features_and_target",
    "ModelProvenance",
    "HyperparameterConfig",
    "MetricScore",
    "SplitEvaluation",
    "ModelMetricsSummary",
    "FeatureImportanceItem",
    "ModelMetadata",
    "BaseDownscalingModel",
    "XGBoostTemperatureResidualModel",
    "DownscalingModelEvaluator",
    "LocalModelRegistry",
    "DownscalingModelTrainer",
    "TemperatureDownscalingPredictor",
]
