"""
ML Models Package for Downscaling Subsystem.
SIH Problem Statement 26074
"""
from app.ml.models.base import BaseDownscalingModel
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel

__all__ = [
    "BaseDownscalingModel",
    "XGBoostTemperatureResidualModel",
]
