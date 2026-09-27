"""
Panchayat Localized Precipitation Observation-Fusion & Nowcasting Schemas
SIH Problem Statement 26074 (Weather Downscaling - Task 4)

Defines data models for short-horizon (30, 60, 120 min) Panchayat precipitation
nowcasting combining NWP forecasts, satellite evidence, optional radar telemetry,
and recent surface observations.

Adheres strictly to the two-stage precipitation paradigm:
  Stage 1: P(rain > threshold) - Probability of measurable precipitation
  Stage 2: E[rain | rain > threshold] - Expected rainfall conditional on rain occurring
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.spatial_masking import CoverageQuality


class PrecipitationSourceState(str, Enum):
    """Categorical representation of available independent meteorological evidence streams."""
    NWP_ONLY = "NWP_ONLY"                                       # Baseline NWP forecast only (no fresh observations)
    NWP_SATELLITE = "NWP_SATELLITE"                             # NWP + Fresh geostationary satellite evidence
    NWP_SATELLITE_RADAR = "NWP_SATELLITE_RADAR"                 # NWP + Satellite + Ground Doppler weather radar
    NWP_SATELLITE_SURFACE_OBS = "NWP_SATELLITE_SURFACE_OBS"     # NWP + Satellite + Surface AWS/gauge confirmation
    NWP_SATELLITE_RADAR_SURFACE_OBS = "NWP_SATELLITE_RADAR_SURFACE_OBS" # Complete multi-tier observation fusion
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"                     # All sources stale, missing, or unverified


class NowcastConfidence(str, Enum):
    """Conservative data-quality and evidence confidence tiers."""
    HIGH = "HIGH"                       # Multiple independent agreeing streams, fresh data, complete coverage
    MEDIUM = "MEDIUM"                   # NWP + Satellite agreeing, or partial observation streams with good coverage
    LOW = "LOW"                         # Single source, high latency, source disagreement, or marginal coverage
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA" # Cannot formulate a scientifically defensible localized nowcast


class EvidenceSignalType(str, Enum):
    """Classification of evidence signals contributing to the two-stage precipitation estimation."""
    NWP_FORECAST = "NWP_FORECAST"
    SATELLITE_CLOUD_INFRARED = "SATELLITE_CLOUD_INFRARED"
    SATELLITE_PRECIPITATION_ESTIMATE = "SATELLITE_PRECIPITATION_ESTIMATE"
    RADAR_REFLECTIVITY = "RADAR_REFLECTIVITY"
    SURFACE_OBSERVATION = "SURFACE_OBSERVATION"


class PrecipitationEvidenceComponent(BaseModel):
    """Standardized representation of an individual contributing evidence stream."""
    source_type: EvidenceSignalType = Field(..., description="Evidence category")
    source_name: str = Field(..., description="Provider or instrument name (e.g. 'IMD-GFS', 'INSAT-3DR-TIR', 'DWR-VARANASI')")
    available: bool = Field(..., description="True if data was successfully retrieved and parsed")
    fresh: bool = Field(default=True, description="True if observation latency is within configured freshness threshold")
    age_minutes: float = Field(default=0.0, ge=0.0, description="Age of observation relative to execution time")
    spatial_coverage_fraction: float = Field(default=1.0, ge=0.0, le=1.0, description="Spatial overlap with Panchayat")
    signal_strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized precipitation indicator [0.0, 1.0]")
    raw_metric_name: str = Field(..., description="Physical variable name (e.g. 'rain_mm', 'tb_min_k', 'reflectivity_dbz')")
    raw_metric_value: Optional[float] = Field(None, description="Physical measured/retrieved value")
    weight_used: float = Field(default=0.0, ge=0.0, description="Weight assigned in deterministic fusion heuristic")
    disclaimer: Optional[str] = Field(None, description="Scientific context or limitation notes")

    model_config = ConfigDict(extra="ignore")


class RadarObservationFeatures(BaseModel):
    """
    Standardized container for optional Doppler Weather Radar (DWR) observation features.
    Designed so future RadarObservationProvider can plug in seamlessly.
    """
    provider_name: str = Field(default="DWR_RADAR_PROVIDER", description="Radar station or network name")
    observation_time: str = Field(..., description="UTC timestamp of radar volume scan")
    age_minutes: float = Field(..., ge=0.0, description="Observation age in minutes")
    mean_reflectivity_dbz: Optional[float] = Field(None, description="Area-weighted mean reflectivity in dBZ")
    max_reflectivity_dbz: Optional[float] = Field(None, description="Peak core reflectivity in dBZ")
    radar_estimated_rain_rate_mm_h: Optional[float] = Field(None, ge=0.0, description="Z-R derived rain rate in mm/h")
    echo_area_fraction: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of Panchayat covered by echoes >= 15 dBZ")
    convective_echo_fraction: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of Panchayat covered by echoes >= 35 dBZ")
    is_available: bool = Field(default=True, description="True if radar coverage exists and data was ingested")
    quality_flag: str = Field(default="VALID", description="VALID, BEAM_BLOCKAGE, GROUND_CLUTTER, ATTENUATED")

    model_config = ConfigDict(extra="ignore")


class SurfaceObservationFeatures(BaseModel):
    """Standardized container for optional ground-truth AWS/gauge telemetry."""
    station_id: str = Field(..., description="WMO or IMD AWS station identifier")
    station_name: Optional[str] = Field(None, description="Station name")
    observation_time: str = Field(..., description="UTC timestamp of surface observation")
    age_minutes: float = Field(..., ge=0.0, description="Observation age in minutes")
    distance_to_centroid_km: float = Field(..., ge=0.0, description="Distance from station to Panchayat centroid in km")
    precipitation_last_1h_mm: Optional[float] = Field(None, ge=0.0, description="Precipitation accumulated in last hour (mm)")
    current_rain_rate_mm_h: Optional[float] = Field(None, ge=0.0, description="Instantaneous rain rate in mm/h")
    is_raining: bool = Field(default=False, description="True if gauge detects active measurable rain >= 0.1 mm")
    is_available: bool = Field(default=True, description="True if nearby station exists within valid radius")

    model_config = ConfigDict(extra="ignore")


class BaselinePrecipitationExpectation(BaseModel):
    """NWP / Block-level baseline precipitation forecast prior to localized observation fusion."""
    source_model: str = Field(default="IMD-GFS", description="Source NWP forecast model")
    forecast_valid_time: str = Field(..., description="Target forecast valid time (ISO UTC)")
    forecast_issue_time: Optional[str] = Field(None, description="Model generation time (ISO UTC)")
    baseline_precipitation_mm: float = Field(..., ge=0.0, description="Expected precipitation accumulation from NWP (mm)")
    baseline_probability: float = Field(..., ge=0.0, le=1.0, description="Baseline probability of precipitation from NWP")
    block_id: Optional[Union[str, int]] = Field(None, description="Parent Block identifier")
    block_name: Optional[str] = Field(None, description="Parent Block name")

    model_config = ConfigDict(extra="ignore")


class PrecipitationNowcastHorizonResult(BaseModel):
    """
    Localized observation-fused precipitation outlook for a specific forecast horizon.
    Adheres strictly to the two-stage representation.
    """
    horizon_minutes: int = Field(..., description="Forecast horizon in minutes (30, 60, or 120)")
    valid_time: str = Field(..., description="Target validity timestamp (UTC ISO)")
    
    # Stage 1: Probability of Measurable Precipitation
    rain_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Stage 1: P(rain >= threshold) - Probability of measurable precipitation"
    )
    measurable_rain_threshold_mm: float = Field(
        default=0.1, description="Threshold defining measurable rain in mm (typically 0.1 mm)"
    )
    is_rain_likely: bool = Field(
        ..., description="True if rain_probability >= 0.50"
    )

    # Stage 2: Expected Precipitation Amount (Conditional on rain occurring)
    expected_amount_mm: Optional[float] = Field(
        None, ge=0.0, description="Stage 2: E[rainfall | rain >= threshold] in mm. null if evidence is insufficient to estimate amount reliably."
    )
    expected_intensity_mm_h: Optional[float] = Field(
        None, ge=0.0, description="Conditional rain rate in mm/h"
    )
    amount_uncertainty_range_mm: Optional[Tuple[float, float]] = Field(
        None, description="Estimated lower and upper plausible bounds for precipitation amount [p25, p75]"
    )

    # Quality, Confidence & Agreement Diagnostics
    confidence: NowcastConfidence = Field(..., description="Overall confidence tier based on measurable evidence factors")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Numeric composite confidence metric [0.0, 1.0]")
    evidence_sources: List[str] = Field(..., description="Names of active evidence streams (e.g. ['NWP', 'SATELLITE'])")
    source_state: PrecipitationSourceState = Field(..., description="Categorical state of contributing evidence sources")
    evidence_disagreement: bool = Field(..., description="True if independent evidence streams point in contradictory directions")
    disagreement_reason: Optional[str] = Field(None, description="Explanation when evidence streams disagree")
    
    # Metadata & Provenance
    observation_age_minutes: float = Field(..., ge=0.0, description="Age of most recent observation input in minutes")
    spatial_coverage: float = Field(..., ge=0.0, le=1.0, description="Effective spatial coverage fraction across Panchayat")
    fusion_method: str = Field(default="DETERMINISTIC_RESEARCH_HEURISTIC_V1", description="Algorithm version identifier")

    model_config = ConfigDict(extra="ignore")


class PrecipitationNowcastProvenance(BaseModel):
    """Audit and scientific provenance trail for a localized precipitation nowcast."""
    nwp_source: str = Field(..., description="NWP baseline provider and model run")
    satellite_source: Optional[str] = Field(None, description="Satellite provider, product, and scan time")
    radar_source: Optional[str] = Field(None, description="Radar station, scan time, and status")
    surface_obs_source: Optional[str] = Field(None, description="Surface observation station and timestamp")
    evidence_weight_version: str = Field(default="RESEARCH_HEURISTIC_V1", description="Evidence weighting rule version")
    config_version: str = Field(default="1.0.0", description="Configuration schema version")
    generated_at: str = Field(..., description="UTC ISO execution timestamp")
    scientific_disclaimer: str = Field(
        default=(
            "Localized precipitation nowcasting combines NWP baseline expectations with georeferenced satellite "
            "and radar evidence. It provides conservative risk estimates; it does NOT constitute certified ground-truth "
            "rainfall observations or verified empirical nowcasting accuracy."
        ),
        description="Non-negotiable scientific governance guardrail"
    )

    model_config = ConfigDict(extra="ignore")


class PanchayatPrecipitationNowcastResult(BaseModel):
    """
    Canonical output structure for a Panchayat-level observation-fused precipitation nowcast.
    Provides multi-horizon outlooks alongside the original baseline forecast for direct comparison.
    """
    panchayat_id: str = Field(..., description="Target Gram Panchayat identifier")
    panchayat_name: Optional[str] = Field(None, description="Target Gram Panchayat name")
    block_id: Optional[Union[str, int]] = Field(None, description="Parent Block identifier")
    block_name: Optional[str] = Field(None, description="Parent Block name")
    issue_time: str = Field(..., description="Nowcast issue time (UTC ISO)")
    
    # Baseline vs Observation-Fused Comparison (Requirement 3)
    baseline_forecast: BaselinePrecipitationExpectation = Field(
        ..., description="Original Block/NWP forecast baseline before localized observation fusion"
    )
    
    # Multi-Horizon Outlooks (30m, 60m, 120m)
    horizons: Dict[str, PrecipitationNowcastHorizonResult] = Field(
        ..., description="Map of horizon key ('30m', '60m', '120m') to localized nowcast results"
    )
    
    # Primary / Headline Horizon (defaults to 60-minute outlook)
    primary_horizon: PrecipitationNowcastHorizonResult = Field(
        ..., description="Headline 60-minute nowcast outlook"
    )
    
    # Evidence Breakdown
    evidence_components: List[PrecipitationEvidenceComponent] = Field(
        default_factory=list, description="Audit of all individual evidence components considered"
    )
    
    # Overall Quality & Governance
    source_state: PrecipitationSourceState = Field(..., description="Active multi-source fusion configuration")
    overall_confidence: NowcastConfidence = Field(..., description="Aggregated confidence across all active horizons")
    evidence_disagreement: bool = Field(default=False, description="Flag indicating contradictory evidence signals")
    disagreement_details: Optional[str] = Field(None, description="Detailed analysis of signal disagreement")
    
    # Provenance
    provenance: PrecipitationNowcastProvenance = Field(..., description="Immutable audit and provenance record")
    status: str = Field(default="SUCCESS", description="Execution status ('SUCCESS', 'INSUFFICIENT_DATA', etc.)")
    message: Optional[str] = Field(None, description="Diagnostic commentary or fail-closed explanation")
    success: bool = Field(default=True, description="API success flag")

    model_config = ConfigDict(extra="ignore")
