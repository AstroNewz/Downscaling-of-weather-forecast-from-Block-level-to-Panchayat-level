"""
Spatial Grid Inference Schemas
SIH Problem Statement 26074 (Weather Downscaling)

Defines data models for spatial grid inference requests, grid cell predictions,
spatial quality diagnostics, and export summaries.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class GridCellOutputRecord(BaseModel):
    """Full prediction and environmental profile for an individual 1-km grid cell."""
    grid_id: str
    block_id: Optional[int] = None
    latitude: float
    longitude: float
    valid_time: str
    coarse_temperature_c: Optional[float] = Field(None, description="Coarse NWP forecast temperature in °C")
    predicted_residual_c: Optional[float] = Field(None, description="ML predicted residual in °C")
    downscaled_temperature_c: Optional[float] = Field(None, description="Final high-resolution temperature in °C")
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    cropland_fraction: Optional[float] = None
    is_agricultural_cropland: bool = Field(default=True, description="Cropland advisory eligibility flag")
    quality_flag: str = Field(default="VALID", description="VALID, SUSPICIOUS, CLAMPED, UNAVAILABLE")
    quality_warnings: List[str] = Field(default_factory=list)
    geometry_geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SpatialQualitySummary(BaseModel):
    """Aggregate quality, coverage, and statistical continuity metrics for downscaled field."""
    total_grid_cells: int
    successful_predictions: int
    unavailable_predictions: int
    failed_predictions: int
    spatial_coverage_pct: float
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    mean_temperature_c: Optional[float] = None
    std_temperature_c: Optional[float] = None
    min_residual_c: Optional[float] = None
    max_residual_c: Optional[float] = None
    mean_residual_c: Optional[float] = None
    quality_flags_count: Dict[str, int] = Field(default_factory=dict)
    diagnostics_passed: bool = Field(default=True)


class SpatialInferenceRequest(BaseModel):
    """Request payload for executing 1-km spatial temperature downscaling over a Block."""
    block_id: int = Field(..., description="Target administrative Block identifier")
    forecast_valid_time: datetime = Field(..., description="Target forecast valid timestamp (UTC)")
    forecast_issue_time: Optional[datetime] = Field(None, description="Optional forecast issue/run timestamp")
    source_model: Optional[str] = Field("IMD-GFS", description="Source NWP forecast model identifier")
    model_version: Optional[str] = Field(None, description="Trained downscaling model version (defaults to active)")
    grid_resolution_km: float = Field(default=1.0, gt=0.1, le=10.0, description="Spatial grid cell size in kilometers")
    persist_to_db: bool = Field(default=True, description="Persist generated grid to DownscaledWeatherGrid table")
    export_geoparquet: bool = Field(default=True, description="Save spatial layer to GeoParquet file")
    include_cell_payload: bool = Field(default=False, description="Include full array of cells in HTTP response payload")


class SpatialInferenceResponse(BaseModel):
    """Response returned upon completion of 1-km spatial downscaling inference."""
    inference_id: str
    block_id: int
    block_name: Optional[str] = None
    district_name: Optional[str] = None
    state_name: Optional[str] = None
    forecast_valid_time: str
    forecast_issue_time: str
    source_model: str
    model_version: str
    feature_schema_version: str
    grid_resolution_km: float
    actual_resolution_m: float
    projected_crs: str
    boundary_rule: str
    quality_summary: SpatialQualitySummary
    geoparquet_path: Optional[str] = None
    geojson_path: Optional[str] = None
    grid_cells: Optional[List[GridCellOutputRecord]] = None
    inference_timestamp: str
    limitations_note: str = (
        "Phase 7 Spatial Downscaled Field: 1-km block grid generated. "
        "Panchayat spatial aggregation and agricultural risk rules are strictly deferred to Phase 8."
    )
