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


# ============================================================================
# ADVISORY STRUCTURED ENTITIES
# ============================================================================

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
