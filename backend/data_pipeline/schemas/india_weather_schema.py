"""
Canonical India Weather Record Schema
SIH Problem Statement 26074 — Agroweather-Downscaling

This schema supports:
  - Pilot AOI (Varanasi, UP)
  - Future India-wide expansion
  - All source types (OBSERVATION, REANALYSIS, NWP_FORECAST, REMOTE_SENSING, DERIVED)

Fields that are genuinely unavailable must be left as None (NULL).
Never populate unavailable fields with invented or interpolated values.

source_type must be one of:
  OBSERVATION    — real station/AWS measurement
  REANALYSIS     — gridded model reanalysis (ERA5, ERA5-Land)
  NWP_FORECAST   — numerical weather prediction output
  REMOTE_SENSING — satellite-derived product
  DERIVED        — computed/processed from above
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


SourceType = Literal[
    "OBSERVATION",
    "REANALYSIS",
    "NWP_FORECAST",
    "REMOTE_SENSING",
    "DERIVED",
]

QualityFlag = Literal["VALID", "SUSPECT", "MISSING", "INVALID"]

INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 38.0
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 98.0

PILOT_LAT_MIN = 25.10
PILOT_LAT_MAX = 25.60
PILOT_LON_MIN = 82.70
PILOT_LON_MAX = 83.20


class IndiaWeatherRecord(BaseModel):
    """
    Canonical weather record for the India pilot pipeline.

    Every record is traceable to its source. NULL is always preferred
    over a fabricated value for unavailable fields.
    """

    # --- Temporal ---
    timestamp_utc: datetime = Field(..., description="Observation/reanalysis timestamp in UTC")
    timestamp_ist: Optional[datetime] = Field(None, description="IST = UTC + 05:30")

    # --- Spatial ---
    latitude: float = Field(..., ge=INDIA_LAT_MIN, le=INDIA_LAT_MAX,
                            description="WGS84 latitude (EPSG:4326)")
    longitude: float = Field(..., ge=INDIA_LON_MIN, le=INDIA_LON_MAX,
                             description="WGS84 longitude (EPSG:4326)")

    # --- Administrative Context ---
    state: Optional[str] = Field(None, description="Indian state name")
    district: Optional[str] = Field(None, description="District name")
    block: Optional[str] = Field(None, description="Block/Tehsil name")
    panchayat: Optional[str] = Field(None, description="Gram Panchayat name")

    # --- Meteorological Variables ---
    temperature_2m_c: Optional[float] = Field(
        None, ge=-60.0, le=65.0,
        description="2-metre air temperature in °C. NULL if unavailable."
    )
    dewpoint_2m_c: Optional[float] = Field(
        None, ge=-60.0, le=65.0,
        description="2-metre dewpoint temperature in °C. NULL if unavailable."
    )
    relative_humidity_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0,
        description="Relative humidity in % (0–100). NULL if unavailable."
    )
    wind_speed_kmh: Optional[float] = Field(
        None, ge=0.0, le=360.0,
        description="10-metre wind speed in km/h. NULL if unavailable."
    )
    wind_direction_deg: Optional[float] = Field(
        None, ge=0.0, le=360.0,
        description="10-metre wind direction in degrees (0–360). NULL if unavailable."
    )
    precipitation_mm: Optional[float] = Field(
        None, ge=0.0,
        description="Precipitation in mm. NULL if unavailable. Never negative."
    )
    surface_pressure_hpa: Optional[float] = Field(
        None, ge=800.0, le=1100.0,
        description="Surface pressure in hPa. NULL if unavailable."
    )

    # --- Source Provenance (required for every record) ---
    source_id: str = Field(..., description="Unique source identifier matching india_pilot.yaml")
    source_type: SourceType = Field(
        ...,
        description=(
            "Source classification: OBSERVATION (station/AWS) | REANALYSIS (ERA5/ERA5-Land) | "
            "NWP_FORECAST | REMOTE_SENSING | DERIVED. "
            "CRITICAL: Never label reanalysis as OBSERVATION."
        )
    )
    source_dataset: str = Field(..., description="Dataset name (e.g. ERA5_LAND, IMD_AWS_STATION)")
    source_version: Optional[str] = Field(None, description="Dataset version or retrieval date")

    # --- Quality Control ---
    quality_flag: QualityFlag = Field(
        default="VALID",
        description="QC flag: VALID | SUSPECT | MISSING | INVALID"
    )
    quality_notes: Optional[str] = Field(None, description="Human-readable QC notes")

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (INDIA_LAT_MIN <= v <= INDIA_LAT_MAX):
            raise ValueError(
                f"Latitude {v} is outside India bounds [{INDIA_LAT_MIN}, {INDIA_LAT_MAX}]"
            )
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not (INDIA_LON_MIN <= v <= INDIA_LON_MAX):
            raise ValueError(
                f"Longitude {v} is outside India bounds [{INDIA_LON_MIN}, {INDIA_LON_MAX}]"
            )
        return v

    @model_validator(mode="after")
    def set_ist_and_validate(self) -> "IndiaWeatherRecord":
        from datetime import timedelta
        # Auto-compute IST if not set
        if self.timestamp_ist is None and self.timestamp_utc is not None:
            self.timestamp_ist = self.timestamp_utc + timedelta(hours=5, minutes=30)
        return self

    def is_in_pilot_aoi(self) -> bool:
        """Returns True if this record falls within the Varanasi pilot bbox."""
        return (
            PILOT_LAT_MIN <= self.latitude <= PILOT_LAT_MAX
            and PILOT_LON_MIN <= self.longitude <= PILOT_LON_MAX
        )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp_utc": "2024-07-01T06:00:00Z",
                "timestamp_ist": "2024-07-01T11:30:00+05:30",
                "latitude": 25.2677,
                "longitude": 82.9913,
                "state": "Uttar Pradesh",
                "district": "Varanasi",
                "block": "Varanasi Sadar",
                "panchayat": None,
                "temperature_2m_c": 32.4,
                "dewpoint_2m_c": 26.1,
                "relative_humidity_pct": 74.0,
                "wind_speed_kmh": 14.4,
                "wind_direction_deg": 200.0,
                "precipitation_mm": 0.0,
                "surface_pressure_hpa": 994.2,
                "source_id": "AWS_BHU_001",
                "source_type": "OBSERVATION",
                "source_dataset": "IMD_AWS_STATION",
                "source_version": "2024",
                "quality_flag": "VALID",
                "quality_notes": None,
            }
        }
