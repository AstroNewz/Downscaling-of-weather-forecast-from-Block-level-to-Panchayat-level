from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.weather.schemas import IngestionSummary


class WeatherBase(BaseModel):
    """Base meteorological parameters schema."""
    temp_min: Optional[float] = Field(None, description="Minimum temperature in Celsius")
    temp_max: Optional[float] = Field(None, description="Maximum temperature in Celsius")
    rainfall_mm: Optional[float] = Field(None, ge=0.0, description="Total precipitation in millimeters")
    relative_humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Relative humidity percentage")
    wind_speed_kmh: Optional[float] = Field(None, ge=0.0, description="Wind speed in km/h")
    wind_speed_mps: Optional[float] = Field(None, ge=0.0, description="Wind speed in m/s")
    wind_direction_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Wind direction in degrees")
    cloud_cover_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Cloud cover percentage")


class BlockWeatherForecastResponse(WeatherBase):
    """Low-resolution Block-level NWP forecast record."""
    id: int
    block_id: int
    block_name: Optional[str] = None
    forecast_date: datetime = Field(..., description="Target forecast valid datetime (UTC)")
    issue_time: datetime = Field(..., description="Forecast run / generation time (UTC)")
    source_model: str = Field(default="IMD-GFS")
    raw_resolution_km: float = Field(default=12.0)
    quality_flag: str = Field(default="VALID", description="VALID, SUSPICIOUS, or INVALID")
    quality_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherObservationResponse(WeatherBase):
    """Station / AWS Ground-Truth Weather Observation record."""
    id: int
    station_id: str
    station_name: Optional[str] = None
    block_id: Optional[int] = None
    latitude: float
    longitude: float
    observation_time: datetime
    quality_flag: str = "VALID"
    quality_notes: Optional[str] = None
    source: str = "AWS"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownscaledPanchayatWeather(WeatherBase):
    """High-resolution downscaled weather output for a specific Panchayat."""
    panchayat_id: str = Field(..., description="Unique Panchayat identifier or LGD code")
    panchayat_name: str = Field(..., description="Name of the Gram Panchayat")
    block_id: str = Field(..., description="Parent block identifier")
    forecast_date: datetime = Field(..., description="Date of forecast")
    downscaling_algorithm: str = Field(..., description="ML algorithm used for downscaling")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model inference confidence score")
    terrain_corrected: bool = Field(default=True, description="Indicates if elevation/DEM adjustment was applied")

    model_config = ConfigDict(from_attributes=True)


class WeatherIngestionRequest(BaseModel):
    """Request payload for triggering weather data ingestion."""
    file_path: Optional[str] = Field(None, description="Local server file path to CSV/data file")
    raw_csv_content: Optional[str] = Field(None, description="Direct in-memory raw CSV text string")
    source_label: str = Field(default="CSV_MANUAL_INGEST", description="Label for data source")
    model_name: str = Field(default="IMD-GFS", description="Source NWP model name")
    dry_run: bool = Field(default=False, description="If true, validates data without committing to database")


class WeatherStatsResponse(BaseModel):
    """Weather database statistics response."""
    total_block_forecasts: int
    valid_forecasts: int
    suspicious_forecasts: int
    total_observations: int
    raw_ingestion_batches: int
