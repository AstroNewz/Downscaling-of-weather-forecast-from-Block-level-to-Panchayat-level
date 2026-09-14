"""
Panchayat Weather Aggregation Schemas
SIH Problem Statement 26074 (Weather Downscaling)

Defines data models for area-weighted Panchayat weather statistics, aggregation requests,
coverage diagnostics, and batch summary responses.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class PanchayatWeatherSummary(BaseModel):
    """Area-weighted weather statistics and quality diagnostics for an individual Gram Panchayat."""
    panchayat_id: int = Field(..., description="Database ID of the Panchayat")
    panchayat_name: str = Field(..., description="Name of the Gram Panchayat")
    lgd_code: str = Field(..., description="Local Government Directory (LGD) code")
    block_id: int = Field(..., description="Parent Block ID")
    block_name: Optional[str] = Field(None, description="Parent Block name")
    
    forecast_valid_time: str = Field(..., description="Target forecast valid time (ISO UTC)")
    forecast_issue_time: str = Field(..., description="Forecast model issue/run time (ISO UTC)")
    source_model: str = Field(default="IMD-GFS", description="Source NWP model")
    model_version: str = Field(default="v1.0.0", description="Phase 6 ML downscaling model version")
    grid_resolution_km: float = Field(default=1.0, description="Spatial resolution of contributing grid (km)")

    # Temperature Statistics (Area-Weighted from 1-km grid)
    mean_temperature_c: float = Field(..., description="Area-weighted mean temperature in °C")
    min_temperature_c: float = Field(..., description="Minimum temperature across valid grid cells in °C")
    max_temperature_c: float = Field(..., description="Maximum temperature across valid grid cells in °C")
    median_temperature_c: Optional[float] = Field(None, description="Median temperature across valid grid cells in °C")
    temperature_stddev_c: Optional[float] = Field(None, description="Spatial standard deviation of temperature in °C")
    temperature_p10_c: Optional[float] = Field(None, description="10th percentile temperature in °C")
    temperature_p90_c: Optional[float] = Field(None, description="90th percentile temperature in °C")
    mean_residual_c: Optional[float] = Field(None, description="Area-weighted mean temperature residual (ΔT in °C)")

    # Spatial Coverage & Diagnostics
    total_panchayat_area_sqkm: float = Field(..., description="Total geometric area of Panchayat in km²")
    covered_area_sqkm: float = Field(..., description="Area covered by valid grid predictions in km²")
    coverage_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of Panchayat area covered by valid grid cells")
    contributing_grid_cells: int = Field(..., ge=0, description="Total intersecting 1-km grid cells")
    valid_grid_cells: int = Field(..., ge=0, description="Number of intersecting grid cells with valid predictions")
    quality_status: str = Field(..., description="COMPLETE (>=95%), PARTIAL (<95%), UNAVAILABLE (0%), SUSPICIOUS")
    quality_flags: List[str] = Field(default_factory=list, description="Quality alert flags e.g. PARTIAL_COVERAGE, RESIDUAL_CLAMPED")

    # Aggregation Provenance
    aggregation_method: str = Field(default="AREA_WEIGHTED", description="Spatial aggregation algorithm")
    aggregation_crs: str = Field(default="EPSG:32643", description="Metric projected CRS used for area calculations")
    cropland_weighted_mean_temp_c: Optional[float] = Field(None, description="Cropland-specific mean temperature if spatial cropland mask available")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(from_attributes=True)


class PanchayatWeatherAggregateRequest(BaseModel):
    """Request payload for triggering Panchayat-level spatial weather aggregation from Phase 7 1-km grid."""
    block_id: int = Field(..., description="Target parent administrative Block identifier")
    forecast_valid_time: datetime = Field(..., description="Target forecast valid timestamp (UTC)")
    forecast_issue_time: Optional[datetime] = Field(None, description="Optional forecast issue timestamp")
    source_model: Optional[str] = Field("IMD-GFS", description="Source NWP forecast model identifier")
    model_version: Optional[str] = Field(None, description="Phase 6 model version (defaults to active)")
    grid_resolution_km: float = Field(default=1.0, gt=0.1, le=10.0, description="Spatial grid resolution in km")
    panchayat_id: Optional[int] = Field(None, description="Optional single Panchayat ID filter (aggregates all in Block if omitted)")
    persist_to_db: bool = Field(default=True, description="Persist aggregated records to panchayat_weather_records table")


class PanchayatWeatherAggregateResponse(BaseModel):
    """Response returned upon completion of Panchayat spatial aggregation."""
    aggregation_id: str
    block_id: int
    block_name: str
    district_name: Optional[str] = None
    state_name: Optional[str] = None
    forecast_valid_time: str
    forecast_issue_time: str
    source_model: str
    model_version: str
    grid_resolution_km: float
    total_panchayats_in_block: int
    aggregated_panchayats_count: int
    complete_coverage_count: int
    partial_coverage_count: int
    unavailable_count: int
    overall_block_coverage_pct: float
    panchayat_weather: List[PanchayatWeatherSummary]
    aggregation_timestamp: str
    limitations_note: str = (
        "Phase 8 Panchayat Weather Aggregation: Downscaled weather statistics aggregated from 1-km grid. "
        "Crop phenology, soil water context, and advisory rules are strictly deferred to Phase 9."
    )
