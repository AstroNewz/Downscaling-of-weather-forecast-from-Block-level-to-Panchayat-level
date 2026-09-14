"""
Local Model Registry for ML Downscaling
SIH Problem Statement 26074 (Weather Downscaling)

Manages persistence, versioning, metadata tracking, metrics inspection,
and schema compatibility checks for trained downscaling models.
"""
import os
import json
import glob
from typing import List, Dict, Any, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.ml.metadata import ModelMetadata, ModelMetricsSummary, FeatureImportanceItem
from app.ml.models.base import BaseDownscalingModel
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel


class LocalModelRegistry:
    """
    Filesystem-backed model registry for versioned ML artifacts.
    Structure:
    models/temperature_residual/
    └── v1.0.0/
        ├── model.json
        ├── metadata.json
        ├── metrics.json
        └── feature_importance.json
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.ML_MODEL_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_version_dir(self, version: str) -> str:
        return os.path.join(self.base_dir, version)

    def is_model_registered(self, version: str) -> bool:
        """Checks if a model artifact and its metadata exist for the given version."""
        version_dir = self._get_version_dir(version)
        model_file = os.path.join(version_dir, "model.json")
        metadata_file = os.path.join(version_dir, "metadata.json")
        return os.path.exists(model_file) and os.path.exists(metadata_file)

    def save_model_artifact(
        self,
        model: BaseDownscalingModel,
        metadata: ModelMetadata,
        metrics: Optional[ModelMetricsSummary] = None,
        feature_importances: Optional[List[FeatureImportanceItem]] = None
    ) -> str:
        """
        Persists all artifacts for a model version to disk.
        """
        version = metadata.model_version
        version_dir = self._get_version_dir(version)
        os.makedirs(version_dir, exist_ok=True)

        # 1. Save model binary/json
        model.save(version_dir)

        # 2. Attach metrics to metadata if provided
        if metrics is not None:
            metadata.metrics_summary = metrics

        # 3. Save metadata.json
        metadata_path = os.path.join(version_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        # 4. Save metrics.json
        if metrics is not None:
            metrics_path = os.path.join(version_dir, "metrics.json")
            with open(metrics_path, "w", encoding="utf-8") as f:
                f.write(metrics.model_dump_json(indent=2))

        # 5. Save feature_importance.json
        if feature_importances is not None:
            feat_path = os.path.join(version_dir, "feature_importance.json")
            with open(feat_path, "w", encoding="utf-8") as f:
                json_data = [item.model_dump() for item in feature_importances]
                json.dump(json_data, f, indent=2)

        logger.info(f"Model version '{version}' successfully registered in {version_dir}")
        return version_dir

    def load_model_artifact(
        self,
        version: Optional[str] = None
    ) -> Tuple[BaseDownscalingModel, ModelMetadata]:
        """
        Loads a trained model and its metadata for inference.
        If version is None, uses default settings.TEMPERATURE_MODEL_VERSION.
        """
        target_version = version or settings.TEMPERATURE_MODEL_VERSION
        version_dir = self._get_version_dir(target_version)

        if not self.is_model_registered(target_version):
            raise FileNotFoundError(
                f"Model version '{target_version}' not found in registry at {version_dir}"
            )

        # Load metadata
        metadata = self.get_model_metadata(target_version)
        if metadata is None:
            raise ValueError(f"Corrupt registry: metadata.json missing for version '{target_version}'")

        # Instantiate and load model
        if metadata.model_name == "xgboost_temperature_residual":
            model = XGBoostTemperatureResidualModel(
                model_name=metadata.model_name,
                version=metadata.model_version,
                hyperparameters=metadata.hyperparameters,
                random_seed=metadata.provenance.random_seed
            )
            model.load(version_dir, features_used=metadata.features_used)
        else:
            raise NotImplementedError(f"Unsupported model type '{metadata.model_name}'")

        return model, metadata

    def get_model_metadata(self, version: str) -> Optional[ModelMetadata]:
        """Retrieves ModelMetadata for a given version."""
        metadata_path = os.path.join(self._get_version_dir(version), "metadata.json")
        if not os.path.exists(metadata_path):
            return None
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ModelMetadata.model_validate(data)

    def get_model_metrics(self, version: str) -> Optional[ModelMetricsSummary]:
        """Retrieves ModelMetricsSummary for a given version."""
        metrics_path = os.path.join(self._get_version_dir(version), "metrics.json")
        if not os.path.exists(metrics_path):
            # Try to extract from metadata
            meta = self.get_model_metadata(version)
            return meta.metrics_summary if meta else None
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ModelMetricsSummary.model_validate(data)

    def get_feature_importances(self, version: str) -> Optional[List[FeatureImportanceItem]]:
        """Retrieves ranked feature importances for a given version."""
        feat_path = os.path.join(self._get_version_dir(version), "feature_importance.json")
        if not os.path.exists(feat_path):
            return None
        with open(feat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [FeatureImportanceItem.model_validate(item) for item in data]

    def list_models(self) -> List[Dict[str, Any]]:
        """Lists all registered model versions and basic metadata."""
        if not os.path.exists(self.base_dir):
            return []

        model_dirs = [
            d for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
        ]

        results = []
        for version_str in sorted(model_dirs):
            meta = self.get_model_metadata(version_str)
            if meta:
                is_active = (version_str == settings.TEMPERATURE_MODEL_VERSION)
                test_eval = meta.metrics_summary.test_evaluation if meta.metrics_summary else None
                results.append({
                    "version": meta.model_version,
                    "model_name": meta.model_name,
                    "model_type": meta.model_type,
                    "feature_schema_version": meta.feature_schema_version,
                    "feature_count": len(meta.features_used),
                    "created_at": meta.created_at.isoformat(),
                    "is_active": is_active,
                    "is_synthetic": meta.provenance.is_synthetic,
                    "train_rows": meta.provenance.train_row_count,
                    "test_mae": test_eval.model_metrics.mae if test_eval else None,
                    "test_mae_improvement_pct": test_eval.mae_improvement_pct if test_eval else None,
                })
        return results

    def check_schema_compatibility(
        self,
        version: str,
        input_features: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Validates whether input feature set is compatible with the model's required features.
        Returns (is_compatible, list_of_missing_features).
        """
        meta = self.get_model_metadata(version)
        if meta is None:
            return False, ["MODEL_NOT_FOUND"]

        missing = [f for f in meta.features_used if f not in input_features]
        return len(missing) == 0, missing
