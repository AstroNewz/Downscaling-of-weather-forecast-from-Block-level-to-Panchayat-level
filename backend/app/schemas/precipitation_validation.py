"""
Precipitation Validation Schemas
SIH Problem Statement 26074 (Weather Downscaling - Task 8)

Strict mathematical, geospatial, and forensic schemas for:
- Independent Station & Observation Ingestion with Independence Gating
- Geospatial Polygon-to-Station Distance and Geometry Relationships
- Validation Readiness Levels 1 to 6 (reusing formal protocol codes)
- Temporal Alignment Records
- Stage 1 (Occurrence) & Stage 2 (Amount) Evaluation Metrics
- Multi-Horizon (30m, 60m, 120m) Partitioning
- A/B Adjacent Panchayat Spatial Gradient Differentiation
- Event-by-Event Forensic Contingency Analysis
- Radar-Available vs Radar-Unavailable and Satellite-Only Comparison
- Confidence Calibration Verification (HIGH, MEDIUM, LOW)
- Data Quality & Latency Stratification
- Advisory Observational Correspondence
- Cryptographic Immutability Audit
- Scientific Claim Matrix & Readiness Decisions
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ValidationReadinessLevel(str, Enum):
    """Formal readiness levels matching PANCHAYAT_VALIDATION_PROTOCOL.md."""
    LEVEL_1_NO_IN_SITU = "LEVEL_1_NO_IN_SITU"
    LEVEL_2_SINGLE_MACRO = "LEVEL_2_SINGLE_MACRO"
    LEVEL_3_SUB_10KM_PAIR = "LEVEL_3_SUB_10KM_PAIR"
    LEVEL_4_SUB_5KM_PAIR = "LEVEL_4_SUB_5KM_PAIR"
    LEVEL_5_SUB_5KM_AGRI = "LEVEL_5_SUB_5KM_AGRI"
    LEVEL_6_INTRA_PANCHAYAT = "LEVEL_6_INTRA_PANCHAYAT"
    REJECTED = "REJECTED"
    FAILED_CLOSED = "FAILED_CLOSED"


class ScientificReadinessState(str, Enum):
    """Formal readiness classification under Task 8 Requirement 23."""
    NOT_VALIDATED = "NOT_VALIDATED"
    LIMITED_VALIDATION = "LIMITED_VALIDATION"
    SUBSTANTIAL_VALIDATION = "SUBSTANTIAL_VALIDATION"
    VALIDATION_BLOCKED = "VALIDATION_BLOCKED"


class StationSpatialRelation(str, Enum):
    """Geospatial relationship between observation station and target polygon."""
    INSIDE_PANCHAYAT = "INSIDE_PANCHAYAT"
    NEAR_PANCHAYAT = "NEAR_PANCHAYAT"
    OUTSIDE_VALIDATION_RADIUS = "OUTSIDE_VALIDATION_RADIUS"


class WeatherRegime(str, Enum):
    """Meteorological regime classification under Task 8 Requirement 8."""
    DRY_PERIOD = "DRY_PERIOD"
    LIGHT_RAIN = "LIGHT_RAIN"
    MODERATE_RAIN = "MODERATE_RAIN"
    HEAVY_RAINFALL = "HEAVY_RAINFALL"
    CONVECTIVE_EVENT = "CONVECTIVE_EVENT"
    PERSISTENT_RAINFALL = "PERSISTENT_RAINFALL"
    TRANSITION_PERIOD = "TRANSITION_PERIOD"


class IndependentStationRecord(BaseModel):
    """Metadata record for an independent observation station."""
    station_id: str = Field(..., description="Unique permanent station identifier")
    station_name: str = Field(..., description="Official station or site name")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation_m: Optional[float] = Field(None, description="Elevation AMSL in meters")
    sensor_height_m: Optional[float] = Field(default=2.0, description="Sensor height AGL in meters")
    site_context: Optional[str] = Field(None, description="AGRICULTURAL, RURAL, SUBURBAN, etc.")
    observation_network: str = Field(..., description="IMD_AGRO_AWS, STATE_MESONET, etc.")
    institution: Optional[str] = Field(None, description="Authoritative custodial institution")
    participated_in_training: bool = Field(default=False, description="Flag for training contamination")
    is_synthetic: bool = Field(default=False, description="Flag for model-derived or synthetic data")
    data_source_type: str = Field(default="OBSERVATION", description="OBSERVATION, REANALYSIS, etc.")
    quality_flag: str = Field(default="VALID", description="QC validation status")
    validation_independent: bool = Field(default=True, description="Strict independence assertion")
    validation_contaminated: bool = Field(default=False, description="Contamination assertion")
    metadata_complete: bool = Field(default=True, description="Whether required metadata fields are present")

    model_config = ConfigDict(extra="ignore")


class IndependentPrecipitationObservation(BaseModel):
    """A single independent precipitation ground-truth observation record."""
    station_id: str = Field(..., description="Source station ID")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC observation timestamp")
    rainfall_mm: float = Field(..., ge=0.0, description="Measured precipitation in mm")
    duration_minutes: int = Field(default=60, description="Accumulation period in minutes")
    weather_regime: Optional[WeatherRegime] = Field(None, description="Meteorological regime")
    quality_flag: str = Field(default="VALID", description="Instrument/telemetry QA/QC flag")
    observation_network: str = Field(..., description="Custodial network identifier")
    validation_independent: bool = Field(default=True)
    validation_contaminated: bool = Field(default=False)

    model_config = ConfigDict(extra="ignore")


class StationPolygonRelationship(BaseModel):
    """Geometrical relationship between a station and a Panchayat polygon."""
    station_id: str
    panchayat_id: str
    spatial_relation: StationSpatialRelation
    distance_to_boundary_km: float = Field(..., description="Distance to polygon boundary (0.0 if inside)")
    distance_to_centroid_km: float = Field(..., description="Supplementary metadata only - not used as sole decider")

    model_config = ConfigDict(extra="ignore")


class TemporalAlignmentRecord(BaseModel):
    """Audit record of temporal alignment between nowcast valid time and observation."""
    observation_time: str
    nowcast_valid_time: str
    offset_seconds: float
    alignment_rule: str
    is_valid: bool

    model_config = ConfigDict(extra="ignore")


class Stage1OccurrenceMetrics(BaseModel):
    """Stage 1: Precipitation Occurrence / Classification Performance."""
    horizon: str = Field(..., description="30m, 60m, or 120m")
    sample_count: int
    hits: int
    false_alarms: int
    misses: int
    correct_negatives: int
    pod: Optional[float] = Field(None, description="Probability of Detection / Recall")
    far: Optional[float] = Field(None, description="False Alarm Ratio")
    csi: Optional[float] = Field(None, description="Critical Success Index / Threat Score")
    precision: Optional[float] = Field(None, description="Precision: Hits / (Hits + False Alarms)")
    recall: Optional[float] = Field(None, description="Recall: Hits / (Hits + Misses)")
    brier_score: Optional[float] = Field(None, description="Brier Score: Mean squared error of probabilities")
    status: str = Field(default="VALID", description="VALID or INSUFFICIENT_VALIDATION_SAMPLE")

    model_config = ConfigDict(extra="ignore")


class Stage2AmountMetrics(BaseModel):
    """Stage 2: Rainfall Amount Conditional on Precipitation."""
    horizon: str = Field(..., description="30m, 60m, or 120m")
    sample_count: int
    mae_mm: Optional[float] = Field(None, description="Mean Absolute Error in mm")
    rmse_mm: Optional[float] = Field(None, description="Root Mean Squared Error in mm")
    mean_bias_mm: Optional[float] = Field(None, description="Mean Bias: Predicted - Observed in mm")
    correlation_r: Optional[float] = Field(None, description="Pearson correlation coefficient")
    sample_too_small: bool = Field(default=False)
    status: str = Field(default="VALID", description="VALID or INSUFFICIENT_VALIDATION_SAMPLE")

    model_config = ConfigDict(extra="ignore")


class SpatialDifferentiationMetrics(BaseModel):
    """Panchayat A/B Spatial Gradient Differentiation Evaluation."""
    event_id: str = Field(default="EVT_DEFAULT", description="Associated event ID")
    pair_id: str
    panchayat_a_id: str
    panchayat_b_id: str
    weather_regime: Optional[str] = None
    observed_diff_mm: float = Field(..., description="Observed rainfall A - B (mm)")
    predicted_prob_diff: float = Field(..., description="Predicted rain probability A - B")
    predicted_amount_diff_mm: Optional[float] = Field(None, description="Predicted amount A - B (mm)")
    directional_agreement: bool = Field(..., description="True if predicted sign matches observed sign")
    absolute_gradient_error_mm: Optional[float] = Field(None, description="|Observed Diff - Predicted Diff|")
    baseline_spatial_variance_zero: bool = Field(
        default=True, description="True if baseline NWP had zero spatial difference"
    )

    model_config = ConfigDict(extra="ignore")


class EventForensicRecord(BaseModel):
    """Forensic event-by-event inspection record."""
    event_id: str
    event_start: str
    event_end: str
    weather_regime: WeatherRegime
    affected_panchayats: List[str]
    observed_rainfall: Dict[str, float]
    predicted_probability: Dict[str, float]
    predicted_amount: Dict[str, Optional[float]]
    evidence_sources: List[str]
    confidence: str
    horizon: str
    radar_available: bool
    satellite_available: bool

    model_config = ConfigDict(extra="ignore")


class ConfidenceCalibrationRecord(BaseModel):
    """Confidence tier vs observed outcome calibration assessment."""
    confidence_tier: str  # HIGH, MEDIUM, LOW
    sample_count: int
    observed_rain_frequency: float
    mean_predicted_probability: float
    calibration_gap: float
    calibration_review_required: bool

    model_config = ConfigDict(extra="ignore")


class DataQualityStratification(BaseModel):
    """Data quality and latency impact assessment."""
    fresh_obs_sample_count: int = 0
    fresh_obs_pod: Optional[float] = None
    stale_obs_sample_count: int = 0
    stale_obs_pod: Optional[float] = None
    high_coverage_sample_count: int = 0
    high_coverage_csi: Optional[float] = None
    low_coverage_sample_count: int = 0
    low_coverage_csi: Optional[float] = None
    satellite_only_sample_count: int = 0
    satellite_only_csi: Optional[float] = None
    multi_source_sample_count: int = 0
    multi_source_csi: Optional[float] = None
    disagreement_sample_count: int = 0
    disagreement_capped_at_low_pct: float = 100.0

    model_config = ConfigDict(extra="ignore")


class AdvisoryObservationalValidation(BaseModel):
    """Observational validation of agricultural advisory correspondence."""
    total_short_horizon_advisories: int = 0
    protective_rain_warnings: int = 0
    rain_warnings_confirmed_by_rain: int = 0
    rain_warnings_false_alarms: int = 0
    clear_sky_windows_evaluated: int = 0
    missed_rain_in_clear_windows: int = 0
    protective_accuracy_pct: Optional[float] = None

    model_config = ConfigDict(extra="ignore")


class ScientificClaimMatrixEntry(BaseModel):
    """Auditable scientific claim with explicit evidence status."""
    claim: str
    evidence: str
    supported: str = Field(..., description="YES, ONLY_IF_EVIDENCE_SUPPORTS, or NO")
    rationale: str

    model_config = ConfigDict(extra="ignore")


class ImmutabilityAuditResult(BaseModel):
    """Cryptographic audit ensuring zero retraining and zero threshold tuning."""
    baseline_calibration_hash: str
    dynamic_v2_xgboost_hash: str
    dynamic_v2_feature_schema_hash: str
    dynamic_v2_metadata_hash: str
    nowcast_configuration_hash: str
    advisory_policy_hash: str
    verified_unchanged: bool
    failed_closed: bool

    model_config = ConfigDict(extra="ignore")


class ValidationReadinessAssessment(BaseModel):
    """Readiness assessment for a specific target Panchayat."""
    panchayat_id: str
    panchayat_name: Optional[str] = None
    readiness_level: ValidationReadinessLevel
    eligible_stations_count: int
    min_inter_station_dist_km: Optional[float] = None
    intra_panchayat_stations_count: int = 0
    simultaneous_hours: int = 0
    eligible_for_panchayat_claim: bool = False
    readiness_reason: str

    model_config = ConfigDict(extra="ignore")


class PanchayatPrecipitationValidationReport(BaseModel):
    """Master validation report schema for Task 8."""
    generation_timestamp: str
    report_version: str = "1.0.0"
    scientific_readiness: ScientificReadinessState
    immutability_audit: ImmutabilityAuditResult
    station_inventory_count: int
    eligible_independent_stations_count: int
    rejected_stations_count: int
    total_valid_observations_count: int
    panchayats_evaluated: List[str]
    readiness_assessments: Dict[str, ValidationReadinessAssessment]
    stage1_occurrence_by_horizon: Dict[str, Stage1OccurrenceMetrics]
    stage2_amount_by_horizon: Dict[str, Stage2AmountMetrics]
    spatial_differentiation: List[SpatialDifferentiationMetrics]
    event_forensics: List[EventForensicRecord]
    radar_vs_no_radar_comparison: Dict[str, Any]
    satellite_only_evaluation: Dict[str, Any]
    confidence_calibration: Dict[str, ConfidenceCalibrationRecord]
    data_quality_stratification: DataQualityStratification
    advisory_validation: AdvisoryObservationalValidation
    claim_matrix: List[ScientificClaimMatrixEntry]
    limitations: List[str]

    model_config = ConfigDict(extra="ignore")
