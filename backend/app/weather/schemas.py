from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class QualityFlag(str, Enum):
    VALID = "VALID"
    SUSPICIOUS = "SUSPICIOUS"
    INVALID = "INVALID"


class ValidationErrorDetail(BaseModel):
    """Detailed validation failure item."""
    row_number: Optional[int] = None
    field: str
    rejected_value: Any
    reason: str


class ParsedWeatherRecord(BaseModel):
    """
    Standardized parsed record emitted by any WeatherProvider before normalization.
    Preserves original unit strings and source identifiers.
    """
    row_number: Optional[int] = None
    block_identifier: Optional[str] = Field(None, description="Block LGD code or name")
    station_identifier: Optional[str] = Field(None, description="Station ID for AWS observations")
    latitude: Optional[Union[float, str]] = None
    longitude: Optional[Union[float, str]] = None

    forecast_generated_at_raw: Optional[Union[datetime, str]] = None
    valid_time_raw: Union[datetime, str] = Field(..., description="Target forecast date/time string or object")

    # Meteorological Variables (raw values)
    temp_min_raw: Optional[Union[float, str]] = None
    temp_max_raw: Optional[Union[float, str]] = None
    rainfall_raw: Optional[Union[float, str]] = None
    humidity_raw: Optional[Union[float, str]] = None
    wind_speed_raw: Optional[Union[float, str]] = None
    wind_direction_raw: Optional[Union[float, str]] = None
    cloud_cover_raw: Optional[Union[float, str]] = None

    # Unit tags (if specified by provider, e.g., 'F', 'C', 'mph', 'm/s', 'mm', 'in')
    temp_unit: Optional[str] = "C"
    rain_unit: Optional[str] = "mm"
    wind_speed_unit: Optional[str] = "km/h"

    # Metadata
    source: str = "CSV_PROVIDER"
    model_name: str = "IMD-GFS"
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class NormalizedWeatherRecord(BaseModel):
    """
    Normalized internal weather record with standardized SI/meteorological units
    and UTC timezone-aware timestamps.
    """
    row_number: Optional[int] = None
    block_identifier: Optional[str] = None
    station_identifier: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    forecast_generated_at: datetime = Field(..., description="Run/Issue time in UTC")
    valid_time: datetime = Field(..., description="Forecast valid time in UTC")

    # Normalized Meteorological Values
    temp_min_celsius: Optional[float] = None
    temp_max_celsius: Optional[float] = None
    rainfall_mm: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    cloud_cover_pct: Optional[float] = None

    # Quality control
    quality_flag: QualityFlag = QualityFlag.VALID
    quality_notes: Optional[str] = None
    validation_errors: List[ValidationErrorDetail] = Field(default_factory=list)

    # Provenance
    source: str = "CSV_PROVIDER"
    model_name: str = "IMD-GFS"
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class IngestionSummary(BaseModel):
    """
    Comprehensive structured report produced after every weather ingestion run.
    """
    ingestion_id: Optional[int] = None
    source: str
    source_file: Optional[str] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    
    records_read: int = 0
    records_valid: int = 0
    records_suspicious: int = 0
    records_invalid: int = 0
    records_inserted: int = 0
    records_skipped: int = 0
    duplicate_records: int = 0

    missing_value_counts: Dict[str, int] = Field(default_factory=dict)
    unit_conversions: Dict[str, int] = Field(default_factory=dict)
    validation_errors: List[ValidationErrorDetail] = Field(default_factory=list)

    status: str = "SUCCESS"
    details: Optional[str] = None
