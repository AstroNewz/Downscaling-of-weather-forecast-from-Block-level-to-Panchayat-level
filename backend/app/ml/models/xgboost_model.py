"""
XGBoost Temperature Residual Model Implementation
SIH Problem Statement 26074 (Weather Downscaling)

Trains gradient boosted decision trees to predict localized temperature residuals:
y = Observed_Temp - Coarse_Forecast_Temp
"""
import os
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import xgboost as xgb

from app.ml.models.base import BaseDownscalingModel
from app.ml.metadata import HyperparameterConfig, FeatureImportanceItem
from app.core.logging import logger


class XGBoostTemperatureResidualModel(BaseDownscalingModel):
    """
    XGBoost Regressor for learning micro-topographic and land-use temperature residuals.
    """

    def __init__(
        self,
        model_name: str = "xgboost_temperature_residual",
        version: str = "v1.0.0",
        hyperparameters: Optional[HyperparameterConfig] = None,
        random_seed: int = 42
    ):
        super().__init__(model_name=model_name, version=version)
        self.hyperparameters = hyperparameters or HyperparameterConfig()
        self.random_seed = random_seed
        self.model: Optional[xgb.XGBRegressor] = None
        self.best_iteration: Optional[int] = None
        self.best_score: Optional[float] = None

    def _init_regressor(self, use_early_stopping: bool = False) -> xgb.XGBRegressor:
        """Instantiates the underlying XGBRegressor with configured hyperparameters."""
        early_stopping = self.hyperparameters.early_stopping_rounds if use_early_stopping else None
        
        return xgb.XGBRegressor(
            n_estimators=self.hyperparameters.n_estimators,
            learning_rate=self.hyperparameters.learning_rate,
            max_depth=self.hyperparameters.max_depth,
            subsample=self.hyperparameters.subsample,
            colsample_bytree=self.hyperparameters.colsample_bytree,
            min_child_weight=self.hyperparameters.min_child_weight,
            reg_alpha=self.hyperparameters.reg_alpha,
            reg_lambda=self.hyperparameters.reg_lambda,
            objective=self.hyperparameters.objective,
            random_state=self.random_seed,
            early_stopping_rounds=early_stopping,
            n_jobs=-1,
            tree_method="hist",
        )

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        verbose: bool = False
    ) -> "XGBoostTemperatureResidualModel":
        """
        Fits the XGBoost regressor on training features X and residual target y.
        """
        self.features_used = list(X_train.columns)
        has_val = X_val is not None and y_val is not None and len(X_val) > 0

        self.model = self._init_regressor(use_early_stopping=has_val)

        eval_set = [(X_val[self.features_used], y_val)] if has_val else None

        logger.info(
            f"Training {self.model_name} ({self.version}) on {len(X_train)} samples with {len(self.features_used)} features..."
        )

        if eval_set:
            self.model.fit(
                X_train[self.features_used],
                y_train,
                eval_set=eval_set,
                verbose=verbose
            )
            self.best_iteration = getattr(self.model, "best_iteration", None)
            self.best_score = getattr(self.model, "best_score", None)
        else:
            self.model.fit(
                X_train[self.features_used],
                y_train,
                verbose=verbose
            )
            self.best_iteration = self.hyperparameters.n_estimators

        self.is_fitted = True
        logger.info(
            f"Training complete. Best iteration: {self.best_iteration}, Best score: {self.best_score}"
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generates predicted temperature residuals (delta T in deg C) for input feature matrix X.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Cannot predict with unfitted model. Call fit() or load() first.")

        # Ensure feature alignment
        missing_cols = [c for c in self.features_used if c not in X.columns]
        if missing_cols:
            raise ValueError(f"Input feature matrix missing required columns: {missing_cols}")

        X_aligned = X[self.features_used]
        preds = self.model.predict(X_aligned)
        return np.asarray(preds, dtype=np.float64)

    def get_feature_importances(self) -> Dict[str, Dict[str, float]]:
        """
        Returns feature importance metrics (Gain, Weight, Cover) for all features.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Cannot extract feature importance.")

        booster = self.model.get_booster()
        gain_dict = booster.get_score(importance_type="gain")
        weight_dict = booster.get_score(importance_type="weight")
        cover_dict = booster.get_score(importance_type="cover")

        results = {}
        for feature in self.features_used:
            results[feature] = {
                "gain": float(gain_dict.get(feature, 0.0)),
                "weight": float(weight_dict.get(feature, 0.0)),
                "cover": float(cover_dict.get(feature, 0.0)),
            }
        return results

    def get_ranked_feature_importances(self) -> List[FeatureImportanceItem]:
        """
        Returns a sorted list of FeatureImportanceItem ranked by Gain descending.
        """
        raw_importances = self.get_feature_importances()
        
        # Sort by gain descending
        sorted_features = sorted(
            raw_importances.items(),
            key=lambda item: item[1]["gain"],
            reverse=True
        )

        ranked = []
        for rank, (feat_name, metrics) in enumerate(sorted_features, start=1):
            ranked.append(
                FeatureImportanceItem(
                    feature_name=feat_name,
                    gain=round(metrics["gain"], 6),
                    weight=int(metrics["weight"]),
                    cover=round(metrics["cover"], 6),
                    rank=rank
                )
            )
        return ranked

    def save(self, directory_path: str) -> str:
        """
        Saves XGBoost model artifact (model.json) in directory_path.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Cannot save unfitted model.")

        os.makedirs(directory_path, exist_ok=True)
        model_path = os.path.join(directory_path, "model.json")
        self.model.save_model(model_path)
        logger.info(f"Model saved successfully to {model_path}")
        return model_path

    def load(self, directory_path: str, features_used: Optional[List[str]] = None) -> "XGBoostTemperatureResidualModel":
        """
        Loads XGBoost model artifact from model.json in directory_path.
        """
        model_path = os.path.join(directory_path, "model.json")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found at {model_path}")

        self.model = xgb.XGBRegressor()
        self.model.load_model(model_path)
        self.is_fitted = True

        if features_used:
            self.features_used = features_used
        elif hasattr(self.model, "feature_names_in_"):
            self.features_used = list(self.model.feature_names_in_)
        else:
            # Fallback to booster feature names if available
            booster = self.model.get_booster()
            self.features_used = booster.feature_names or []

        logger.info(f"Model loaded successfully from {model_path} with {len(self.features_used)} features.")
        return self
