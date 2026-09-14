"""
Base Downscaling Model Interface
SIH Problem Statement 26074 (Weather Downscaling)

Defines the abstract base contract for all statistical/ML downscaling regression models.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd


class BaseDownscalingModel(ABC):
    """
    Abstract interface for downscaling models.
    All models must implement fitting, residual prediction, explainability extraction,
    and serialization/deserialization.
    """

    def __init__(self, model_name: str, version: str = "v1.0.0"):
        self.model_name = model_name
        self.version = version
        self.features_used: List[str] = []
        self.is_fitted: bool = False

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        **kwargs
    ) -> "BaseDownscalingModel":
        """
        Fits the model to predict the residual target y.
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generates predicted temperature residuals (delta T in deg C).
        """
        pass

    @abstractmethod
    def get_feature_importances(self) -> Dict[str, Dict[str, float]]:
        """
        Extracts feature importances (e.g. gain, weight, cover).
        """
        pass

    @abstractmethod
    def save(self, directory_path: str) -> str:
        """
        Serializes model artifact to disk. Returns path to saved file.
        """
        pass

    @abstractmethod
    def load(self, directory_path: str) -> "BaseDownscalingModel":
        """
        Deserializes model artifact from disk.
        """
        pass
