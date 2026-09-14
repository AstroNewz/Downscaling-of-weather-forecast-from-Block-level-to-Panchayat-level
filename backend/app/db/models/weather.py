from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geometry
from app.db.base import Base


class RawWeatherRecord(Base):
    """
    Raw Ingested Weather Data Payload.
    Preserves untouched raw input from providers (CSV rows, API responses, GRIB metadata)
    for data provenance, auditability, and re-processing.
    """
    __tablename__ = "raw_weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True, doc="e.g., CSV_UPLOAD, IMD_FTP, NCMRWF_API")
    source_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True, doc="SHA256 checksum of payload/file")
    
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, doc="Untransformed raw JSON/dictionary records")
    records_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), default="PROCESSED", nullable=False, index=True, doc="PENDING, PROCESSED, FAILED")

    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BlockWeatherForecast(Base):
    """
    Coarse Numerical Weather Prediction (NWP) Forecast at Block Level (~12-25 km resolution).
    Primary raw input for the AI/ML downscaling pipeline.
    """
    __tablename__ = "block_weather_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)

    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="Target forecast valid date/time (UTC)")
    issue_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, doc="Forecast generation / model run time (UTC)")

    # Meteorological Variables (Normalized)
    temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Minimum Temperature in Celsius")
    temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Maximum Temperature in Celsius")
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Precipitation in mm")
    relative_humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Relative humidity percentage (0-100)")
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Wind speed in km/h")
    wind_speed_mps: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Wind speed in m/s")
    wind_direction_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Wind direction (0-360 degrees)")
    cloud_cover_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Total cloud cover percentage (0-100)")

    # Quality Control & Data Provenance
    quality_flag: Mapped[str] = mapped_column(String(32), default="VALID", nullable=False, index=True, doc="VALID, SUSPICIOUS, INVALID")
    quality_notes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Source NWP Model Metadata
    source_model: Mapped[str] = mapped_column(String(64), default="IMD-GFS", nullable=False, doc="e.g., IMD-GFS, NCUM, ECMWF")
    raw_resolution_km: Mapped[float] = mapped_column(Float, default=12.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    block: Mapped["Block"] = relationship("Block", back_populates="weather_forecasts")

    __table_args__ = (
        Index("idx_block_forecast_date", "block_id", "forecast_date"),
        Index("idx_block_run_date", "block_id", "forecast_date", "issue_time", "source_model"),
        UniqueConstraint("block_id", "forecast_date", "issue_time", "source_model", name="uq_block_forecast_run"),
    )


class WeatherObservation(Base):
    """
    Station-level / Automatic Weather Station (AWS) Ground-Truth Observation.
    Used for validating NWP forecasts and training/evaluating downscaling models.
    """
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, doc="Unique AWS/Station Identifier")
    station_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    block_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="SET NULL"), nullable=True, index=True)

    # Spatial coordinates of weather station
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    observation_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="Observation timestamp (UTC)")

    # Observed Variables
    temp_celsius: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_mps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Quality Control
    quality_flag: Mapped[str] = mapped_column(String(32), default="VALID", nullable=False, index=True)
    quality_notes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="AWS", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_station_time", "station_id", "observation_time"),
        UniqueConstraint("station_id", "observation_time", "source", name="uq_station_observation_time"),
    )


class DownscaledWeatherGrid(Base):
    """
    High-Resolution (1 km x 1 km) Downscaled Weather Grid / Block Spatial Field & Panchayat Prediction.
    Inferred via AI/ML downscaling (XGBoost) with DEM topographic corrections.
    """
    __tablename__ = "downscaled_weather_grids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=True, index=True)
    block_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=True, index=True)

    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="Target forecast valid date/time (UTC)")
    issue_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Forecast generation / model run time (UTC)")
    source_model: Mapped[str] = mapped_column(String(64), default="IMD-GFS", nullable=False)
    grid_cell_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True, doc="Unique 1km grid tile ID")

    # Spatial Point and Coordinates of 1km Grid Cell
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    # Downscaled Temperature Components
    coarse_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Input coarse forecast temperature in °C")
    predicted_residual_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="ML predicted temperature residual (delta T in °C)")
    downscaled_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Final downscaled fine temperature in °C")

    # Additional Meteorological Parameters (for multi-variable or future expansion)
    temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ML Inference Metadata & Quality Control
    downscaling_algorithm: Mapped[str] = mapped_column(String(64), default="xgboost", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="v1.0.0", nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(32), default="v1.1.0", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False, doc="Statistical confidence score (0-1)")
    terrain_corrected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="DEM elevation lapse rate adjusted")
    quality_flag: Mapped[str] = mapped_column(String(32), default="VALID", nullable=False, index=True, doc="VALID, SUSPICIOUS, CLAMPED, UNAVAILABLE")
    prediction_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped[Optional["Panchayat"]] = relationship("Panchayat", back_populates="downscaled_weather_records")
    block: Mapped[Optional["Block"]] = relationship("Block")

    __table_args__ = (
        Index("idx_panchayat_forecast_date", "panchayat_id", "forecast_date"),
        Index("idx_block_grid_forecast_date", "block_id", "forecast_date"),
    )


class PanchayatWeather(Base):
    """
    Gram Panchayat-Level Downscaled Weather Record.
    Derived via area-weighted spatial aggregation of Phase 7 1-km downscaled grid cells.
    Serves as the primary weather input for Phase 9 agro-meteorological advisory context.
    """
    __tablename__ = "panchayat_weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panchayat_id: Mapped[int] = mapped_column(Integer, ForeignKey("panchayats.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False, index=True)

    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="Target forecast valid date/time (UTC)")
    issue_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, doc="Forecast generation / run time (UTC)")
    source_model: Mapped[str] = mapped_column(String(64), default="IMD-GFS", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="v1.0.0", nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(32), default="v1.1.0", nullable=False)
    grid_resolution_km: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Temperature Statistics (Area-Weighted)
    mean_temp_c: Mapped[float] = mapped_column(Float, nullable=False, doc="Area-weighted mean temperature in °C")
    min_temp_c: Mapped[float] = mapped_column(Float, nullable=False, doc="Minimum temperature across valid grid cells in °C")
    max_temp_c: Mapped[float] = mapped_column(Float, nullable=False, doc="Maximum temperature across valid grid cells in °C")
    median_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Median temperature in °C")
    temp_stddev_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Standard deviation of temperature in °C")
    temp_p10_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="10th percentile temperature in °C")
    temp_p90_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="90th percentile temperature in °C")
    mean_residual_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True, doc="Area-weighted mean residual in °C")

    # Spatial Coverage & Diagnostics
    total_panchayat_area_sqkm: Mapped[float] = mapped_column(Float, nullable=False, doc="Total Panchayat area in km²")
    covered_area_sqkm: Mapped[float] = mapped_column(Float, nullable=False, doc="Valid weather covered area in km²")
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False, doc="Coverage percentage (0-100%)")
    contributing_grid_cells: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Total intersecting 1-km grid cells")
    valid_grid_cells: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Grid cells with valid predictions")
    quality_status: Mapped[str] = mapped_column(String(32), default="COMPLETE", nullable=False, index=True, doc="COMPLETE, PARTIAL, UNAVAILABLE, SUSPICIOUS")
    quality_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Aggregation Metadata
    aggregation_method: Mapped[str] = mapped_column(String(64), default="AREA_WEIGHTED", nullable=False)
    aggregation_crs: Mapped[str] = mapped_column(String(32), default="EPSG:32643", nullable=False)
    cropland_weighted_mean_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aggregation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    panchayat: Mapped["Panchayat"] = relationship("Panchayat", back_populates="weather_records")
    block: Mapped["Block"] = relationship("Block")

    __table_args__ = (
        Index("idx_panchayat_weather_date", "panchayat_id", "forecast_date"),
        Index("idx_block_panchayat_weather_date", "block_id", "forecast_date"),
        UniqueConstraint(
            "panchayat_id",
            "forecast_date",
            "issue_time",
            "source_model",
            "model_version",
            name="uq_panchayat_weather_run"
        ),
    )
