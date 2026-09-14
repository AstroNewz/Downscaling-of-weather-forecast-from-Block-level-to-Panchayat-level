"""
Temperature Downscaling Real-Time Predictor & Inference Service
SIH Problem Statement 26074 (Weather Downscaling)

Provides low-latency point downscaling inference, schema compatibility validation,
and physical bounds verification for operational agro-meteorological forecasting.
"""
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.logging import logger
from app.ml.registry import LocalModelRegistry
from app.ml.models.base import BaseDownscalingModel
from app.ml.metadata import ModelMetadata
from app.ml.schemas import FEATURE_SCHEMA_VERSION


class TemperatureDownscalingPredictor:
    """
    Inference service for computing high-resolution temperature downscaling.
    Formulation:
      T_downscaled = T_coarse + y_residual_pred
    """

    # Physical thermal sanity bounds (in Celsius)
    MIN_PHYSICAL_TEMP_C: float = -30.0
    MAX_PHYSICAL_TEMP_C: float = 60.0
    MAX_RESIDUAL_DELTA_C: float = 15.0  # Maximum plausible residual magnitude

    def __init__(self, registry: Optional[LocalModelRegistry] = None):
        self.registry = registry or LocalModelRegistry()
        self._model_cache: Dict[str, Tuple[BaseDownscalingModel, ModelMetadata]] = {}

    def _get_model(self, version: Optional[str] = None) -> Tuple[BaseDownscalingModel, ModelMetadata]:
        """Loads and caches model instance for the specified version."""
        target_version = version or settings.TEMPERATURE_MODEL_VERSION
        if target_version not in self._model_cache:
            model, metadata = self.registry.load_model_artifact(target_version)
            self._model_cache[target_version] = (model, metadata)
        return self._model_cache[target_version]

    def predict_point(
        self,
        coarse_forecast_temp_c: float,
        features: Dict[str, Any],
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes point temperature downscaling inference.
        """
        # 1. Validate coarse temperature
        if coarse_forecast_temp_c is None or np.isnan(coarse_forecast_temp_c) or np.isinf(coarse_forecast_temp_c):
            raise ValueError(f"Invalid coarse_forecast_temp_c: {coarse_forecast_temp_c}")

        # 2. Retrieve model
        model, metadata = self._get_model(model_version)

        # 3. Align and validate features
        expected_features = metadata.features_used
        row_dict = {}
        for feat in expected_features:
            if feat not in features:
                # If optional or missing, check if it's computable or raise error
                raise ValueError(
                    f"Missing required predictor '{feat}' for model {metadata.model_version}. "
                    f"Model requires: {expected_features}"
                )
            val = features[feat]
            if val is None or (isinstance(val, (int, float)) and (np.isnan(val) or np.isinf(val))):
                raise ValueError(f"Feature '{feat}' contains invalid NaN or Inf value: {val}")
            row_dict[feat] = float(val)

        X_input = pd.DataFrame([row_dict], columns=expected_features)

        # 4. Predict residual
        residual_raw = float(model.predict(X_input)[0])

        # 5. Physical bounds sanity check & clamping
        is_clamped = False
        residual_clamped = residual_raw
        if abs(residual_raw) > self.MAX_RESIDUAL_DELTA_C:
            residual_clamped = np.clip(residual_raw, -self.MAX_RESIDUAL_DELTA_C, self.MAX_RESIDUAL_DELTA_C)
            is_clamped = True
            logger.warning(
                f"Residual {residual_raw:.2f}°C exceeded physical delta bound ±{self.MAX_RESIDUAL_DELTA_C}°C. Clamped to {residual_clamped:.2f}°C."
            )

        downscaled_temp_raw = coarse_forecast_temp_c + residual_clamped
        downscaled_temp_final = np.clip(downscaled_temp_raw, self.MIN_PHYSICAL_TEMP_C, self.MAX_PHYSICAL_TEMP_C)
        if downscaled_temp_final != downscaled_temp_raw:
            is_clamped = True
            logger.warning(
                f"Downscaled temperature {downscaled_temp_raw:.2f}°C exceeded physical limits [{self.MIN_PHYSICAL_TEMP_C}, {self.MAX_PHYSICAL_TEMP_C}]. Clamped to {downscaled_temp_final:.2f}°C."
            )

        lapse_adj = features.get("lapse_rate_temp_adjustment_c")
        slope = features.get("slope_deg")

        return {
            "downscaled_temperature_c": round(float(downscaled_temp_final), 2),
            "coarse_forecast_temp_c": round(float(coarse_forecast_temp_c), 2),
            "predicted_residual_c": round(float(residual_clamped), 3),
            "raw_residual_c": round(float(residual_raw), 3),
            "model_version": metadata.model_version,
            "feature_schema_version": metadata.feature_schema_version,
            "lapse_rate_adjustment_c": round(float(lapse_adj), 3) if lapse_adj is not None else None,
            "topographic_slope_deg": round(float(slope), 2) if slope is not None else None,
            "is_physically_clamped": is_clamped,
            "inference_timestamp": datetime.utcnow().isoformat()
        }

    def predict_batch(
        self,
        df_features: pd.DataFrame,
        coarse_temp_col: str = "coarse_forecast_temp_c",
        model_version: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Executes vectorized batch downscaling for a DataFrame of features.
        """
        model, metadata = self._get_model(model_version)
        expected_features = metadata.features_used

        missing_cols = [c for c in expected_features if c not in df_features.columns]
        if missing_cols:
            raise ValueError(f"Batch DataFrame missing required feature columns: {missing_cols}")

        if coarse_temp_col not in df_features.columns:
            raise ValueError(f"Batch DataFrame missing coarse temperature column '{coarse_temp_col}'")

        X_input = df_features[expected_features].astype(np.float64)
        residuals = model.predict(X_input)

        # Vectorized clamping
        residuals_clamped = np.clip(residuals, -self.MAX_RESIDUAL_DELTA_C, self.MAX_RESIDUAL_DELTA_C)
        coarse_temps = df_features[coarse_temp_col].to_numpy(dtype=np.float64)
        downscaled_temps = np.clip(coarse_temps + residuals_clamped, self.MIN_PHYSICAL_TEMP_C, self.MAX_PHYSICAL_TEMP_C)

        result_df = df_features.copy()
        result_df["predicted_residual_c"] = residuals_clamped
        result_df["downscaled_temperature_c"] = downscaled_temps
        return result_df
