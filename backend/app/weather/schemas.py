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


class LiveWeatherRecord(BaseModel):
    """
    Standardized live or canonical demo coarse weather retrieval record.
    Preserves exact provenance, physical metrics, timestamps, and quality flags.
    """
    latitude: float
    longitude: float
    temperature_c: float
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    valid_time: str
    retrieved_at: str
    source: str
    source_type: str = "FORECAST"  # FORECAST, OBSERVATION, REANALYSIS, PILOT_FIXTURE
    mode: str = "LIVE"  # DEMO, LIVE, AUTO
    effective_mode: str = "LIVE"
    quality_status: str = "PASSED"  # PASSED, DEGRADED, REJECTED, INSUFFICIENT_DATA, NOT_CONFIGURED
    quality_notes: Optional[str] = None
    fallback_active: bool = False
    fallback_reason: Optional[str] = None
    live_request_id: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class DataStatusResponse(BaseModel):
    """
    System data-source status report.
    Distinguishes API server health from real weather data availability.
    """
    mode: str = "DEMO"  # DEMO, LIVE, AUTO
    effective_mode: str = "DEMO"
    live_enabled: bool = False
    provider: str = "CANONICAL_PILOT_FIXTURE"
    source_type: str = "PILOT_FIXTURE"
    latest_source_timestamp: Optional[str] = None
    retrieved_at: str
    age_minutes: Optional[float] = None
    freshness_status: str = "FRESH"  # FRESH, STALE, UNKNOWN
    quality_status: str = "PASSED"  # PASSED, DEGRADED, REJECTED, INSUFFICIENT_DATA, NOT_CONFIGURED
    fallback_active: bool = False
    fallback_reason: Optional[str] = None
    calibrated_baseline: str = "T_calibrated = T_coarse + 0.7351°C"
    model_status: str = "XGBoost: RESEARCH_ONLY"
    message: str = "Deterministic canonical demo fixtures active."


class ProviderStatus(str, Enum):
    LIVE = "LIVE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    QC_FAILED = "QC_FAILED"
    AUTH_FAILED = "AUTH_FAILED"


class ProviderInfo(BaseModel):
    name: str
    code: str
    status: ProviderStatus
    source_type: str
    configured: bool
    requires_auth: bool
    auth_configured: bool
    endpoint: str
    supported_products: List[str] = Field(default_factory=list)
    description: str
    coverage: str
    geographic_coverage: str = "India"
    licensing: str = "Open Access / Government Restricted"
    configuration_instructions: Optional[str] = None


class ProviderHealthResponse(BaseModel):
    provider: str
    status: ProviderStatus
    source_type: str
    configured: bool
    latency_ms: Optional[float] = None
    source_timestamp: Optional[str] = None
    retrieved_at: str
    data_age_minutes: Optional[float] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    variables: List[str] = Field(default_factory=list)
    qc_status: str = "PASSED"
    freshness_status: str = "FRESH"
    fallback_active: bool = False
    fallback_reason: Optional[str] = None
    request_id: Optional[str] = None
    error_message: Optional[str] = None
    required_configuration: Optional[Dict[str, str]] = None

