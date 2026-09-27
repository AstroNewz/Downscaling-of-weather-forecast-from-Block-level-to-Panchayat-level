"""
Agro-Meteorological Advisory Generation Pydantic Schemas
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Defines structured, versioned, explainable, and dashboard-ready advisory schemas.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agricultural_risk import (
    RiskStatus,
    RiskSeverity,
    RiskType,
    RiskCategory,
    RiskEvidence,
    RiskResult,
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    PanchayatRiskProfile,
    RiskSubsystemStatus,
)


class AdvisoryType(str, Enum):
    """Supported agrometeorological advisory types."""
    HEAT_STRESS_ADVISORY = "HEAT_STRESS_ADVISORY"
    COLD_STRESS_ADVISORY = "COLD_STRESS_ADVISORY"
    WATER_STRESS_ADVISORY = "WATER_STRESS_ADVISORY"
    EXCESS_RAIN_ADVISORY = "EXCESS_RAIN_ADVISORY"
    WIND_STRESS_ADVISORY = "WIND_STRESS_ADVISORY"
    DISEASE_FAVORABLE_CONDITIONS_ADVISORY = "DISEASE_FAVORABLE_CONDITIONS_ADVISORY"
    PRECIPITATION_NOWCAST_ADVISORY = "PRECIPITATION_NOWCAST_ADVISORY"
    SHORT_HORIZON_OPERATIONS_ADVISORY = "SHORT_HORIZON_OPERATIONS_ADVISORY"
    INFORMATIONAL = "INFORMATIONAL"


class AdvisoryCategory(str, Enum):
    """Categorization of advisory intent."""
    ACTION_ADVISORY = "ACTION_ADVISORY"
    INFORMATIONAL = "INFORMATIONAL"


class AdvisoryPriority(str, Enum):
    """Advisory priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class AdvisoryStatus(str, Enum):
    """Lifecycle states of an advisory."""
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    EXPIRED = "EXPIRED"
    SUPPRESSED = "SUPPRESSED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EXPERT_REVIEW_REQUIRED = "EXPERT_REVIEW_REQUIRED"


class AdvisoryActionCategory(str, Enum):
    """Categories of structured management actions."""
    MONITOR = "MONITOR"
    WATER_MANAGEMENT = "WATER_MANAGEMENT"
    CROP_PROTECTION = "CROP_PROTECTION"
    FIELD_OPERATIONS = "FIELD_OPERATIONS"
    WEATHER_PREPAREDNESS = "WEATHER_PREPAREDNESS"
    DISEASE_MONITORING = "DISEASE_MONITORING"


class AdvisoryUrgency(str, Enum):
    """Operational urgency of recommended actions."""
    IMMEDIATE = "IMMEDIATE"
    UPCOMING = "UPCOMING"
    ROUTINE = "ROUTINE"


class NowcastAdvisoryState(str, Enum):
    """Explicit operational state of localized precipitation nowcast evidence in advisory decisions."""
    NOWCAST_NOT_AVAILABLE = "NOWCAST_NOT_AVAILABLE"         # No nowcast was executed or provided
    NOWCAST_INSUFFICIENT_DATA = "NOWCAST_INSUFFICIENT_DATA" # Evidence is stale, missing, or coverage < 20%
    NOWCAST_LOW_CONFIDENCE = "NOWCAST_LOW_CONFIDENCE"       # Single source, high latency, or source disagreement
    NOWCAST_MEDIUM_CONFIDENCE = "NOWCAST_MEDIUM_CONFIDENCE" # Moderate evidence; cautious operational use
    NOWCAST_HIGH_CONFIDENCE = "NOWCAST_HIGH_CONFIDENCE"     # Consistent multi-stream evidence; actionable


# ============================================================================
# ADVISORY STRUCTURED ENTITIES
# ============================================================================

class LocalizedPrecipitationAdvisoryEvidence(BaseModel):
    """Structured localized precipitation nowcast evidence attached to an advisory."""
    panchayat_id: str = Field(..., description="Target Gram Panchayat identifier")
    valid_time: str = Field(..., description="Target validity ISO timestamp")
    horizon_minutes: int = Field(..., description="Forecast horizon in minutes (30, 60, or 120)")
    rain_probability: float = Field(..., ge=0.0, le=1.0, description="Stage 1: P(rain >= threshold)")
    expected_amount_mm: Optional[float] = Field(None, description="Stage 2: E[rain | rain >= threshold] in mm")
    confidence: str = Field(..., description="Confidence tier: HIGH, MEDIUM, LOW, INSUFFICIENT_DATA")
    source_state: str = Field(..., description="Contributing sources e.g. NWP_SATELLITE, NWP_ONLY")
    evidence_sources: List[str] = Field(default_factory=list, description="List of active evidence sources")
    evidence_disagreement: bool = Field(default=False, description="True if NWP and observations contradict")
    disagreement_reason: Optional[str] = Field(None, description="Explanation when evidence streams disagree")
    spatial_coverage: float = Field(default=1.0, description="Spatial coverage fraction over Panchayat")
    observation_age_minutes: float = Field(default=0.0, description="Age of newest contributing observation in minutes")
    method_version: str = Field(default="DETERMINISTIC_RESEARCH_HEURISTIC_V1", description="Fusion algorithm version")
    provenance: Optional[Dict[str, Any]] = Field(None, description="Full audit trail of observation sources")

    model_config = ConfigDict(extra="ignore")


class NowcastAdvisoryExplanation(BaseModel):
    """Explainability object detailing how localized nowcast influenced the agricultural advisory."""
    primary_reason: str = Field(..., description="Primary reason for the advisory action")
    localized_precipitation_signal: str = Field(..., description="Summary of localized observation signal")
    baseline_signal: str = Field(..., description="Summary of macroscale NWP baseline signal")
    evidence_agreement: bool = Field(..., description="True if baseline and localized signals agree")
    confidence: str = Field(..., description="Confidence tier assigned to the nowcast evidence")
    action_strength: str = Field(..., description="STRONG, CAUTIOUS, CONTEXT_ONLY, or NO_ACTION")
    recommended_horizon_minutes: int = Field(default=60, description="Horizon most relevant to the action (30, 60, 120)")
    short_horizon_recommendation: Optional[str] = Field(None, description="Specific short-horizon guidance")

    model_config = ConfigDict(extra="ignore")


class AdvisoryAction(BaseModel):
    """Structured action and management guidance."""
    action_category: Optional[str] = Field(None, description="e.g. WATER_MANAGEMENT, FIELD_OPERATIONS")
    action_text: Optional[str] = Field(None, description="Detailed agronomic management guidance")
    timing: Optional[str] = Field(None, description="Recommended operational window")
    urgency: Optional[str] = Field(None, description="IMMEDIATE, UPCOMING, ROUTINE")
    conditions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Preconditions or caveats")


class AdvisoryResult(BaseModel):
    """Complete explainable and dashboard-ready advisory response."""
    id: Optional[int] = Field(None, description="Database record ID if persisted")
    panchayat_id: int
    panchayat_name: str
    block_id: int
    block_name: Optional[str] = None
    crop_id: int
    crop_name: str
    stage_name: Optional[str] = None
    
    # Associated Risk & Weather References
    risk_log_id: Optional[int] = None
    crop_context_id: Optional[int] = None
    panchayat_weather_id: Optional[int] = None
    
    advisory_type: str = Field(..., description="HEAT_STRESS_ADVISORY, COLD_STRESS_ADVISORY, etc.")
    advisory_category: str = Field(default="ACTION_ADVISORY", description="ACTION_ADVISORY or INFORMATIONAL")
    priority: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL")
    priority_rank: int = Field(default=1, description="Rank among active risks for this crop (1 = highest)")
    priority_reason: Optional[str] = None

    title: str = Field(..., description="Short advisory title")
    message: str = Field(..., description="Executive advisory summary message")
    action: Optional[AdvisoryAction] = Field(None, description="Structured management action")
    rationale: Optional[str] = Field(None, description="Agronomic scientific rationale")
    
    severity: str = Field(default="NONE", description="Phase 10 hazard severity")
    confidence: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW, INSUFFICIENT")
    confidence_reason: Optional[str] = None
    
    # Validity & Dates
    valid_from: str = Field(..., description="ISO datetime for validity start")
    valid_until: str = Field(..., description="ISO datetime for validity expiry")
    forecast_date: str = Field(..., description="ISO datetime for forecast date")
    issue_time: str = Field(..., description="ISO datetime for generation time")
    
    # Provenance & Versioning
    source_model: str = Field(default="IMD-GFS")
    weather_model_version: Optional[str] = None
    rule_version: str = Field(default="agri_risk_v1.0.0", description="Phase 10 Risk Rule Version")
    advisory_rule_version: str = Field(default="agri_advisory_v1.0.0", description="Phase 11 Advisory Rule Version")
    rule_source: str = Field(default="ICAR_IMD_AGROMET_GUIDELINES")
    language: str = Field(default="en")
    
    status: str = Field(default="ACTIVE", description="ACTIVE, DRAFT, EXPIRED, SUPPRESSED, INSUFFICIENT_DATA, EXPERT_REVIEW_REQUIRED")
    is_expert_review_required: bool = False
    is_cropland_eligible: bool = True
    
    evidence: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    # Localized Precipitation Nowcast Context (Phase 5 / Task 5 Extension)
    localized_nowcast_context: Optional[LocalizedPrecipitationAdvisoryEvidence] = Field(
        default=None, description="Localized short-horizon precipitation evidence if available"
    )
    baseline_precipitation_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Baseline macroscale precipitation forecast context for comparison"
    )
    nowcast_advisory_state: Optional[NowcastAdvisoryState] = Field(
        default=None, description="State of the localized nowcast integration (AVAILABLE, LOW_CONFIDENCE, etc.)"
    )
    nowcast_explanation: Optional[NowcastAdvisoryExplanation] = Field(
        default=None, description="Explainable rationale on how localized nowcast influenced the advisory"
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# REQUEST & RESPONSE ENVELOPES
# ============================================================================

class AdvisoryGenerationRequest(BaseModel):
    """Payload to trigger agro-meteorological advisory generation."""
    panchayat_id: Optional[int] = Field(None, description="Gram Panchayat ID (optional if block_id provided)")
    block_id: Optional[int] = Field(None, description="Block ID for batch generation")
    date: datetime = Field(default_factory=datetime.utcnow, description="Forecast evaluation date")
    crop_id: Optional[int] = Field(None, description="Filter for specific crop")
    risk_type: Optional[str] = Field(None, description="Filter for specific risk type")
    language: str = Field(default="en", description="Advisory language code (default 'en')")
    persist_to_db: bool = Field(default=True, description="Whether to persist generated advisories")


class AdvisoryGenerationResponse(BaseModel):
    """Response payload summarizing advisory generation execution."""
    generation_run_id: str
    block_id: Optional[int] = None
    block_name: Optional[str] = None
    forecast_date: str
    total_panchayats: int
    total_crops_evaluated: int
    total_advisories_generated: int
    critical_advisories_count: int
    high_advisories_count: int
    medium_advisories_count: int
    low_advisories_count: int
    informational_count: int
    advisories: List[AdvisoryResult] = Field(default_factory=list)
    execution_timestamp: str


class PanchayatAdvisoryProfile(BaseModel):
    """Consolidated agro-meteorological advisory profile for a single Gram Panchayat."""
    panchayat_id: int
    panchayat_name: str
    lgd_code: str
    block_id: int
    block_name: Optional[str] = None
    forecast_date: str
    crop_advisories: Dict[str, List[AdvisoryResult]] = Field(
        default_factory=dict,
        description="Active advisories grouped by crop name"
    )
    total_active_advisories: int = 0
    highest_priority: str = "INFORMATIONAL"
    expert_review_required: bool = False


class AdvisorySubsystemStatus(BaseModel):
    """Subsystem analytics and counts for agro-meteorological advisories."""
    total_advisories: int
    active_advisories: int
    draft_advisories: int
    expired_advisories: int
    suppressed_advisories: int
    insufficient_data_advisories: int
    expert_review_required_advisories: int
    advisories_by_priority: Dict[str, int] = Field(default_factory=dict)
    advisories_by_type: Dict[str, int] = Field(default_factory=dict)
    advisories_by_crop: Dict[str, int] = Field(default_factory=dict)
    advisories_by_panchayat: int = 0
    active_rule_version: str


# ============================================================================
# LEGACY SCHEMAS (BACKWARD COMPATIBILITY)
# ============================================================================

class AgriculturalRisk(BaseModel):
    """Specific agricultural risk identified from downscaled weather + crop stage."""
    risk_id: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    description: str
    triggering_weather_factor: str


class AgroAdvisoryAction(BaseModel):
    """Specific actionable guidance for farmers/officers."""
    action_type: str = Field(..., description="e.g., Irrigation, Pest Spraying, Drainage, Harvesting")
    recommendation: str = Field(..., description="Specific recommended measure")
    timing: str = Field(..., description="Recommended window of execution")
    priority: str = Field(default="Normal", description="Immediate, Urgent, Normal")


class AgroAdvisoryReport(BaseModel):
    """Complete tailored agro-meteorological advisory response."""
    advisory_id: str
    panchayat_id: str
    panchayat_name: str
    crop_name: str
    crop_stage: str
    issue_date: datetime
    valid_until: datetime
    is_cropland_eligible: bool = True
    summary_advisory: str
    risks: List[AgriculturalRisk] = Field(default_factory=list)
    recommended_actions: List[AgroAdvisoryAction] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "RiskStatus",
    "RiskSeverity",
    "RiskType",
    "RiskCategory",
    "RiskEvidence",
    "RiskResult",
    "RiskEvaluationRequest",
    "RiskEvaluationResponse",
    "PanchayatRiskProfile",
    "RiskSubsystemStatus",
    "AdvisoryType",
    "AdvisoryCategory",
    "AdvisoryPriority",
    "AdvisoryStatus",
    "AdvisoryActionCategory",
    "AdvisoryUrgency",
    "AdvisoryAction",
    "AdvisoryResult",
    "AdvisoryGenerationRequest",
    "AdvisoryGenerationResponse",
    "PanchayatAdvisoryProfile",
    "AdvisorySubsystemStatus",
    "AgriculturalRisk",
    "AgroAdvisoryAction",
    "AgroAdvisoryReport",
]
