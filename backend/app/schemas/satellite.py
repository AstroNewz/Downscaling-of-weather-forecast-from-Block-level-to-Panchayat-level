"""
Satellite Observation Schemas & Product Taxonomy
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Defines data models for satellite product taxonomy, resolution provenance,
brightness-temperature/cloud features, freshness tracking, and temporal deltas.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.spatial_masking import (
    CoverageQuality,
    SourceResolutionProvenance,
    VariableType,
)


class SatelliteProductType(str, Enum):
    """Explicit taxonomy of satellite-derived meteorological products."""
    SATELLITE_CLOUD_MASK = "SATELLITE_CLOUD_MASK"                         # Binary/fractional cloud mask (0=clear, 1=cloud)
    SATELLITE_IR_BRIGHTNESS_TEMPERATURE = "SATELLITE_IR_BRIGHTNESS_TEMPERATURE" # Infrared 10.8µm/12µm brightness temp (Kelvin)
    SATELLITE_PRECIPITATION_ESTIMATE = "SATELLITE_PRECIPITATION_ESTIMATE" # Satellite precipitation estimate (HEGG, IMERG) in mm or mm/h
    SATELLITE_WATER_VAPOUR = "SATELLITE_WATER_VAPOUR"                     # Upper/mid-tropospheric water vapour (6.7µm, % or TPW mm)
    SATELLITE_VISIBLE_REFLECTANCE = "SATELLITE_VISIBLE_REFLECTANCE"       # Daytime visible channel albedo (0.0 to 1.0)


class SatelliteObservationStatus(str, Enum):
    """Data availability and operational health classification for satellite observations."""
    LIVE_DATA_AVAILABLE = "LIVE_DATA_AVAILABLE"             # Fresh satellite observation retrieved and validated
    LIVE_DATA_STALE = "LIVE_DATA_STALE"                     # Available but exceeds operational freshness threshold
    LIVE_DATA_UNAVAILABLE = "LIVE_DATA_UNAVAILABLE"         # External feed unreachable or missing
    PRODUCT_NOT_CONFIGURED = "PRODUCT_NOT_CONFIGURED"       # Requested satellite product not registered
    INVALID_PRODUCT = "INVALID_PRODUCT"                     # Data corrupted, invalid dimensions, or non-numeric
    INVALID_GEOREFERENCING = "INVALID_GEOREFERENCING"       # Missing CRS or invalid Affine geotransform (FAIL CLOSED)
    INSUFFICIENT_SPATIAL_COVERAGE = "INSUFFICIENT_SPATIAL_COVERAGE" # AOI falls outside satellite scene extent


class SatelliteProvenance(BaseModel):
    """
    Complete audit trail and resolution provenance for a satellite observation.
    Maintains strict separation between observation time, valid time, and ingestion time.
    """
    provider: str = Field(..., description="Provider name (e.g. 'ISRO-MOSDAC', 'EUMETSAT', 'NOAA-NESDIS', 'NASA-GPM')")
    product: str = Field(..., description="Satellite product identifier (e.g. 'INSAT-3D_HEGG', 'INSAT-3DR_TIR1')")
    product_type: SatelliteProductType = Field(..., description="Taxonomic classification of satellite variable")
    product_version: Optional[str] = Field(default="1.0", description="Product release or algorithm version")
    observation_time: str = Field(..., description="ISO 8601 UTC timestamp of raw satellite sensor scan/acquisition")
    product_valid_time: str = Field(..., description="ISO 8601 UTC timestamp for which product is valid")
    ingestion_time: str = Field(..., description="ISO 8601 UTC timestamp when product entered local pipeline")
    native_resolution_km: float = Field(..., gt=0.0, description="Native sub-satellite spatial resolution in kilometers")
    crs: str = Field(default="EPSG:4326", description="Authoritative Coordinate Reference System")
    spatial_extent: Optional[Tuple[float, float, float, float]] = Field(
        None, description="Bounding extent: (min_lon, min_lat, max_lon, max_lat) in WGS84"
    )
    source_identifier: Optional[str] = Field(None, description="Granule or scene file identifier")
    source_url: Optional[str] = Field(None, description="Upstream access URL or repository reference")
    file_sha256: Optional[str] = Field(None, description="Cryptographic SHA-256 checksum of input raster")
    quality_flags: Dict[str, Any] = Field(default_factory=dict, description="Product quality and confidence flags")
    is_estimated: bool = Field(
        default=True,
        description="True for derived meteorological estimates (e.g. precipitation); False for direct radiance measurements"
    )
    resolution_disclaimer: str = Field(
        default="Satellite observations represent pixel-integrated radiances or algorithm estimates; spatial masking does NOT synthesize higher resolution than the native sensor grid.",
        description="Scientific policy guardrail against false microclimate resolution claims"
    )

    model_config = ConfigDict(extra="ignore")


class SatelliteCloudFeatures(BaseModel):
    """
    Mathematically and scientifically defensible cloud features extracted from satellite imagery.
    Thresholds are strictly labeled as configurable research heuristics.
    """
    cloud_fraction: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Fraction of valid Panchayat area covered by clouds (0.0=clear, 1.0=overcast)"
    )
    clear_fraction: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Fraction of valid Panchayat area with clear sky conditions"
    )
    mean_brightness_temperature_k: Optional[float] = Field(
        None, description="Area-weighted mean 10.8µm infrared brightness temperature in Kelvin"
    )
    min_brightness_temperature_k: Optional[float] = Field(
        None, description="Minimum brightness temperature in Kelvin (identifies deepest convective cloud tops)"
    )
    fraction_below_convective_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Fraction of Panchayat area with IR temperature below convective threshold (e.g. 235K)"
    )
    convective_threshold_k: Optional[float] = Field(
        default=235.0, description="Configurable exploratory threshold in Kelvin indicating deep convective cloud tops"
    )
    spatial_std_k: Optional[float] = Field(
        None, ge=0.0, description="Spatial standard deviation across intersecting cells in Kelvin"
    )
    spatial_gradient: Optional[float] = Field(
        None, description="Normalized spatial standard deviation / gradient across cells"
    )
    cloud_cells_intersecting: int = Field(default=0, description="Number of intersecting cells classified as cloudy")
    total_valid_cells: int = Field(default=0, description="Number of intersecting cells with valid sensor values")

    model_config = ConfigDict(extra="ignore")


class SatelliteTemporalDelta(BaseModel):
    """
    Temporal change metrics between two consecutive satellite observations (T0 -> T1).
    Provides empirical change evidence for future localized nowcasting.
    """
    t0_observation_time: str = Field(..., description="Timestamp of baseline/earlier satellite observation")
    t1_observation_time: str = Field(..., description="Timestamp of current/later satellite observation")
    delta_minutes: float = Field(..., ge=0.0, description="Elapsed time between observations in minutes")
    cloud_fraction_delta: Optional[float] = Field(None, description="Change in cloud fraction (t1 - t0)")
    mean_signal_delta: Optional[float] = Field(None, description="Change in mean signal / brightness temp (t1 - t0)")
    min_signal_delta: Optional[float] = Field(None, description="Change in coldest cloud top temp (t1 - t0)")
    cloud_area_change_sq_km: Optional[float] = Field(None, description="Change in cloudy area in sq km")
    trend: str = Field(
        default="STEADY",
        description="Empirical trend indicator: 'EXPANDING', 'DISSIPATING', 'COOLING_CONVECTIVE', 'WARMING', 'STEADY'"
    )

    model_config = ConfigDict(extra="ignore")


class PanchayatSatelliteExtractionResult(BaseModel):
    """
    Canonical output structure for Panchayat-level satellite observation extraction.
    Delivers A-specific or B-specific satellite features with complete provenance.
    """
    panchayat_id: str = Field(..., description="Target Gram Panchayat identifier")
    panchayat_name: Optional[str] = Field(None, description="Target Gram Panchayat name")
    source: str = Field(default="SATELLITE", description="Observation sensor domain")
    product: str = Field(..., description="Specific satellite product name")
    product_type: SatelliteProductType = Field(..., description="Semantic product category")
    observation_time: str = Field(..., description="Raw satellite acquisition timestamp (UTC)")
    product_valid_time: str = Field(..., description="Product validity timestamp (UTC)")
    native_resolution_km: float = Field(..., description="True native sensor resolution in km")
    
    # Extracted Features
    features: Dict[str, Any] = Field(..., description="Variable-specific spatial features (Cloud or Precipitation)")
    temporal_change: Optional[SatelliteTemporalDelta] = Field(
        None, description="Temporal change from previous observation window when available"
    )
    
    # Coverage & Quality Diagnostics
    coverage_quality: CoverageQuality = Field(..., description="Spatial coverage tier from Task 2 masking")
    coverage_fraction: float = Field(..., description="Fraction of Panchayat polygon area covered by satellite grid")
    cells_intersecting: int = Field(..., description="Number of satellite pixels intersecting the Panchayat")
    valid_cells_intersecting: int = Field(..., description="Number of intersecting pixels with valid data")
    
    # Freshness Metadata
    observation_age_minutes: float = Field(..., description="Age of observation relative to current processing time")
    is_fresh: bool = Field(..., description="True if observation_age <= freshness_threshold_minutes")
    freshness_status: SatelliteObservationStatus = Field(..., description="Operational status: LIVE_DATA_AVAILABLE, LIVE_DATA_STALE, etc.")
    
    # Provenance
    provenance: SatelliteProvenance = Field(..., description="Complete source, sensor, and resolution provenance")
    status: str = Field(default="SUCCESS", description="Execution status")
    message: Optional[str] = Field(None, description="Diagnostic commentary or fail-closed explanation")
    success: bool = Field(default=True, description="API success indicator")

    model_config = ConfigDict(extra="ignore")
