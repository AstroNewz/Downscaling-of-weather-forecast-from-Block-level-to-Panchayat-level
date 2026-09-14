from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

FEATURE_SCHEMA_VERSION = "v1.1.0"


class DatasetBuildConfig(BaseModel):
    """Configuration options for building a coarse-to-fine weather downscaling dataset."""
    dataset_version: str = Field(default="v1.1.0", description="Semantic dataset version tag")
    start_time: Optional[datetime] = Field(None, description="Start date/time for observations (UTC)")
    end_time: Optional[datetime] = Field(None, description="End date/time for observations (UTC)")
    source_model: Optional[str] = Field(None, description="Filter by NWP model (e.g., IMD-GFS)")
    temporal_tolerance_minutes: int = Field(default=180, ge=0, description="Max allowed time diff between obs and forecast valid_time")
    exclude_suspicious: bool = Field(default=True, description="If True, excludes records flagged as SUSPICIOUS")
    train_ratio: float = Field(default=0.70, ge=0.0, le=1.0)
    validation_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    dem_raster_path: Optional[str] = Field(None, description="Optional path to DEM GeoTIFF for high-res topographic sampling")
    output_dir: str = Field(default="data/processed/", description="Directory path for exported Parquet artifacts")
    dry_run: bool = Field(default=False, description="If True, builds and returns report without writing Parquet artifact")


class BaselineMetrics(BaseModel):
    """
    Evaluation metrics of the raw coarse NWP forecast against ground truth observations.
    Serves as the benchmark that future ML models must outperform.
    """
    sample_count: int = 0
    mae_celsius: Optional[float] = Field(None, description="Mean Absolute Error (°C)")
    rmse_celsius: Optional[float] = Field(None, description="Root Mean Squared Error (°C)")
    mean_bias_error_celsius: Optional[float] = Field(None, description="Mean Bias Error (°C)")
    r2_score: Optional[float] = Field(None, description="Coefficient of Determination (R²)")
    residual_min: Optional[float] = None
    residual_max: Optional[float] = None
    residual_std: Optional[float] = None


class EngineeredFeatureRecord(BaseModel):
    """
    Standardized, leakage-free feature row for training coarse-to-fine downscaling models.
    Enriched with Phase 5 GIS, Topographic, and Land-Cover Predictors.
    """
    # 1. Traceability Metadata (Excluded from ML training feature vector X)
    sample_id: str
    station_id: str
    block_id: int
    block_name: Optional[str] = None
    observation_time: datetime
    forecast_valid_time: datetime
    forecast_issue_time: datetime
    source_model: str
    dataset_version: str = FEATURE_SCHEMA_VERSION
    split: str = "train"  # 'train', 'val', 'test'

    # 2. Coarse NWP Forecast Predictors (Available at inference time)
    forecast_temp_min: Optional[float] = None
    forecast_temp_max: Optional[float] = None
    forecast_temp_mean: Optional[float] = None
    forecast_rainfall_mm: Optional[float] = None
    forecast_humidity_pct: Optional[float] = None
    forecast_wind_speed_mps: Optional[float] = None
    forecast_wind_direction_deg: Optional[float] = None
    forecast_cloud_cover_pct: Optional[float] = None

    # 3. Temporal & Lead Time Features
    forecast_lead_hours: float
    time_diff_minutes: float
    hour_of_day: int
    sin_hour: float
    cos_hour: float
    day_of_year: int
    sin_day_of_year: float
    cos_day_of_year: float
    month: int
    sin_month: float
    cos_month: float

    # 4. Spatial & Topographic Predictors (Phase 5 Enriched)
    obs_latitude: float
    obs_longitude: float
    block_centroid_lat: Optional[float] = None
    block_centroid_lon: Optional[float] = None
    distance_to_centroid_km: Optional[float] = None
    obs_elevation_m: Optional[float] = None
    block_elevation_m: Optional[float] = None
    elevation_diff_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    sin_aspect: Optional[float] = None
    cos_aspect: Optional[float] = None
    terrain_roughness: Optional[float] = None
    lapse_rate_temp_adjustment_c: Optional[float] = None

    # 5. Land-Use / Land-Cover Composition (Phase 5 Enriched)
    cropland_fraction: Optional[float] = None
    forest_fraction: Optional[float] = None
    urban_fraction: Optional[float] = None
    water_fraction: Optional[float] = None
    barren_fraction: Optional[float] = None
    is_agricultural_cropland: Optional[bool] = None

    # 6. Verified Ground Truth & Targets
    observed_temp_c: float
    coarse_forecast_temp_c: float
    temperature_residual_c: float  # PRIMARY TARGET y = observed - coarse_forecast

    model_config = ConfigDict(from_attributes=True)


class DatasetQualityReport(BaseModel):
    """Comprehensive dataset provenance and quality report."""
    dataset_version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    config: DatasetBuildConfig

    # Record counts
    forecast_records_considered: int = 0
    observation_records_considered: int = 0
    temporally_matched: int = 0
    spatially_matched: int = 0
    valid_samples: int = 0
    suspicious_samples: int = 0
    excluded_samples: int = 0
    duplicate_samples: int = 0

    # Temporal bounds
    min_observation_time: Optional[datetime] = None
    max_observation_time: Optional[datetime] = None
    min_forecast_time: Optional[datetime] = None
    max_forecast_time: Optional[datetime] = None

    # Missing value counts across features
    missing_feature_counts: Dict[str, int] = Field(default_factory=dict)
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)

    # Split distributions
    train_samples: int = 0
    validation_samples: int = 0
    test_samples: int = 0

    # Baseline performance metrics
    overall_baseline: BaselineMetrics = Field(default_factory=BaselineMetrics)
    train_baseline: BaselineMetrics = Field(default_factory=BaselineMetrics)
    validation_baseline: BaselineMetrics = Field(default_factory=BaselineMetrics)
    test_baseline: BaselineMetrics = Field(default_factory=BaselineMetrics)

    # Artifact output paths
    parquet_path: Optional[str] = None
    report_path: Optional[str] = None
    status: str = "SUCCESS"
    details: Optional[str] = None
