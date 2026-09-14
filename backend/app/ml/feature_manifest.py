"""
Feature Manifest & Leakage Quarantine Engine
SIH Problem Statement 26074 (Weather Downscaling)

Defines the authoritative, ordered list of predictors for Schema v1.1.0 and
quarantines target variables and post-forecast metadata to prevent ML data leakage.
"""
from typing import List, Tuple, Dict, Any, Set
import pandas as pd
from app.ml.schemas import FEATURE_SCHEMA_VERSION


# 1. Coarse NWP Weather Predictors (Available at operational forecast run time)
FORECAST_PREDICTORS: List[str] = [
    "forecast_temp_min",
    "forecast_temp_max",
    "forecast_temp_mean",
    "forecast_rainfall_mm",
    "forecast_humidity_pct",
    "forecast_wind_speed_mps",
    "forecast_wind_direction_deg",
    "forecast_cloud_cover_pct",
    "forecast_lead_hours",
    "time_diff_minutes",
]

# 2. Temporal & Astronomical Cyclical Predictors
TEMPORAL_PREDICTORS: List[str] = [
    "hour_of_day",
    "sin_hour",
    "cos_hour",
    "day_of_year",
    "sin_day_of_year",
    "cos_day_of_year",
    "month",
    "sin_month",
    "cos_month",
]

# 3. Spatial & Topographic Environmental Predictors
SPATIAL_TOPOGRAPHIC_PREDICTORS: List[str] = [
    "obs_latitude",
    "obs_longitude",
    "distance_to_centroid_km",
    "obs_elevation_m",
    "block_elevation_m",
    "elevation_diff_m",
    "slope_deg",
    "aspect_deg",
    "sin_aspect",
    "cos_aspect",
    "terrain_roughness",
    "lapse_rate_temp_adjustment_c",
]

# 4. Land-Use / Land-Cover (LULC) Composition Fractions
LANDUSE_PREDICTORS: List[str] = [
    "cropland_fraction",
    "forest_fraction",
    "urban_fraction",
    "water_fraction",
    "barren_fraction",
]

# Complete authoritative ordered list of predictor features fed to ML models (X)
ALL_PREDICTOR_FEATURES: List[str] = (
    FORECAST_PREDICTORS +
    TEMPORAL_PREDICTORS +
    SPATIAL_TOPOGRAPHIC_PREDICTORS +
    LANDUSE_PREDICTORS
)

# Quarantined columns (Metadata & Targets) that must NEVER enter feature matrix X
QUARANTINED_LEAKAGE_COLUMNS: Set[str] = {
    "sample_id",
    "station_id",
    "block_id",
    "block_name",
    "observation_time",
    "forecast_valid_time",
    "forecast_issue_time",
    "source_model",
    "dataset_version",
    "split",
    "observed_temp_c",
    "coarse_forecast_temp_c",
    "temperature_residual_c",
    "is_agricultural_cropland",  # Boolean flag used in advisory mask, not ML regression feature
}

PRIMARY_TARGET_COLUMN: str = "temperature_residual_c"
OBSERVED_TEMP_COLUMN: str = "observed_temp_c"
COARSE_TEMP_COLUMN: str = "coarse_forecast_temp_c"


def validate_no_leakage(columns_to_use: List[str]) -> Tuple[bool, List[str]]:
    """
    Verifies that no quarantined metadata or target columns have leaked into the predictor list.
    """
    leaked = [col for col in columns_to_use if col in QUARANTINED_LEAKAGE_COLUMNS]
    if leaked:
        return False, leaked
    return True, []


def extract_features_and_target(
    df: pd.DataFrame,
    features_to_use: List[str] = ALL_PREDICTOR_FEATURES,
    target_col: str = PRIMARY_TARGET_COLUMN
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Safely extracts feature matrix X, target y, observed_temp, and coarse_forecast_temp from dataset DataFrame.
    """
    is_valid, leaked_cols = validate_no_leakage(features_to_use)
    if not is_valid:
        raise ValueError(f"Data leakage detected! Quarantined columns present in feature list: {leaked_cols}")

    # Ensure all required feature columns exist in DataFrame (fill missing with None/NaN)
    for col in features_to_use:
        if col not in df.columns:
            df[col] = float("nan")

    X = df[features_to_use].copy()
    y = df[target_col].copy() if target_col in df.columns else pd.Series(dtype="float64")
    obs_t = df[OBSERVED_TEMP_COLUMN].copy() if OBSERVED_TEMP_COLUMN in df.columns else pd.Series(dtype="float64")
    coarse_t = df[COARSE_TEMP_COLUMN].copy() if COARSE_TEMP_COLUMN in df.columns else pd.Series(dtype="float64")

    return X, y, obs_t, coarse_t
