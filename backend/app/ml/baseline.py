import math
from typing import List, Optional
import numpy as np
from app.ml.schemas import EngineeredFeatureRecord, BaselineMetrics


class BaselineEvaluator:
    """
    Computes statistical error metrics of the uncorrected coarse NWP forecast against ground truth observations.
    Establishes the benchmark that downscaling models must statistically surpass.
    """

    @staticmethod
    def calculate_metrics(records: List[EngineeredFeatureRecord]) -> BaselineMetrics:
        """
        Calculates MAE, RMSE, MBE, and R² for coarse forecast temperature vs observed temperature.
        """
        if not records:
            return BaselineMetrics(sample_count=0)

        observed = np.array([r.observed_temp_c for r in records], dtype=np.float64)
        forecast = np.array([r.coarse_forecast_temp_c for r in records], dtype=np.float64)
        residuals = np.array([r.temperature_residual_c for r in records], dtype=np.float64)
        n = len(residuals)

        # 1. Mean Absolute Error (MAE)
        mae = float(np.mean(np.abs(residuals)))

        # 2. Root Mean Squared Error (RMSE)
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        # 3. Mean Bias Error (MBE) -> positive means observed is warmer than forecast on average
        mbe = float(np.mean(residuals))

        # 4. R² score
        total_variance = np.sum((observed - np.mean(observed)) ** 2)
        residual_variance = np.sum(residuals ** 2)
        r2 = float(1.0 - (residual_variance / total_variance)) if total_variance > 1e-7 else None

        # 5. Extremes and dispersion
        res_min = float(np.min(residuals))
        res_max = float(np.max(residuals))
        res_std = float(np.std(residuals))

        return BaselineMetrics(
            sample_count=n,
            mae_celsius=round(mae, 3),
            rmse_celsius=round(rmse, 3),
            mean_bias_error_celsius=round(mbe, 3),
            r2_score=round(r2, 4) if r2 is not None else None,
            residual_min=round(res_min, 3),
            residual_max=round(res_max, 3),
            residual_std=round(res_std, 3),
        )
