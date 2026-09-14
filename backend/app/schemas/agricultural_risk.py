"""
Agricultural Risk Engine Schemas
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Defines data contracts and validation schemas for:
- Individual agricultural risk evaluations and explainable evidence
- Batch risk assessment requests and responses
- Multi-crop Panchayat risk profiles
- Risk subsystem analytics and diagnostic status
"""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RiskStatus(str, Enum):
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID = "INVALID"


class RiskSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class RiskType(str, Enum):
    HEAT_STRESS = "HEAT_STRESS"
    COLD_STRESS = "COLD_STRESS"
    WATER_STRESS = "WATER_STRESS"
    EXCESS_RAIN = "EXCESS_RAIN"
    DISEASE_FAVORABLE_CONDITIONS = "DISEASE_FAVORABLE_CONDITIONS"
    WIND_STRESS = "WIND_STRESS"


class RiskCategory(str, Enum):
    THERMAL = "THERMAL"
    HYDROLOGICAL = "HYDROLOGICAL"
    PATHOLOGICAL_ENVIRONMENT = "PATHOLOGICAL_ENVIRONMENT"
    WIND = "WIND"


class RiskEvidence(BaseModel):
    """Transparent scientific evidence and triggers explaining a risk evaluation result."""
    observed_value: Optional[float] = Field(None, description="Actual observed or downscaled meteorological value")
    threshold_value: Optional[float] = Field(None, description="Crop/stage threshold value triggering severity level")
    unit: Optional[str] = Field(None, description="Measurement unit (e.g. °C, mm, km/h)")
    crop_name: str = Field(..., description="Target crop evaluated")
    stage_name: Optional[str] = Field(None, description="Phenological stage of the crop")
    condition_description: str = Field(..., description="Explainable description of triggering meteorological condition")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Supporting diagnostic variables")

    model_config = ConfigDict(from_attributes=True)


class RiskResult(BaseModel):
    """Detailed risk assessment for a specific crop and risk type in a Panchayat."""
    id: Optional[int] = Field(None, description="Database record ID")
    panchayat_id: int = Field(..., description="Gram Panchayat ID")
    panchayat_name: str = Field(..., description="Gram Panchayat Name")
    block_id: int = Field(..., description="Parent Block ID")
    block_name: Optional[str] = Field(None, description="Parent Block Name")
    
    crop_id: int = Field(..., description="Crop ID")
    crop_name: str = Field(..., description="Crop Name (e.g. Rice, Wheat, Maize)")
    stage_name: Optional[str] = Field(None, description="Active phenological stage")
    
    risk_type: str = Field(..., description="HEAT_STRESS, COLD_STRESS, WATER_STRESS, EXCESS_RAIN, DISEASE_FAVORABLE_CONDITIONS, WIND_STRESS")
    risk_category: str = Field(..., description="THERMAL, HYDROLOGICAL, PATHOLOGICAL_ENVIRONMENT, WIND")
    severity: str = Field(..., description="NONE, LOW, MODERATE, HIGH, EXTREME")
    status: str = Field(..., description="DETECTED, NOT_DETECTED, INSUFFICIENT_DATA, INVALID")
    
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized risk score (0.0 to 1.0)")
    observed_value: Optional[float] = Field(None, description="Triggering metric value")
    threshold_value: Optional[float] = Field(None, description="Applied threshold value")
    unit: Optional[str] = Field(None, description="Metric unit")
    duration_hours: Optional[float] = Field(None, description="Estimated duration in hours")
    
    confidence: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW, INSUFFICIENT")
    rule_version: str = Field(default="agri_risk_v1.0.0", description="Active threshold rule version")
    rule_source: str = Field(default="ICAR_IMD_AGROMET_CRITERIA", description="Authoritative agronomic criteria reference")
    
    evidence: RiskEvidence = Field(..., description="Diagnostic evidence explaining the evaluation")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Traceable input sources and timestamps")
    evaluation_date: str = Field(..., description="Evaluation target forecast date (ISO UTC)")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(from_attributes=True)


class RiskEvaluationRequest(BaseModel):
    """Request payload for triggering agricultural risk evaluation."""
    block_id: int = Field(..., description="Parent Block ID")
    panchayat_id: Optional[int] = Field(None, description="Optional single Panchayat ID filter")
    crop_id: Optional[int] = Field(None, description="Optional single Crop ID filter")
    risk_type: Optional[str] = Field(None, description="Optional single Risk Type filter")
    evaluation_date: datetime = Field(..., description="Target forecast date for evaluation (UTC)")
    persist_to_db: bool = Field(default=True, description="Whether to persist results to agricultural_risk_logs")


class RiskEvaluationResponse(BaseModel):
    """Response returned upon completion of agricultural risk evaluation."""
    evaluation_run_id: str
    block_id: int
    block_name: str
    evaluation_date: str
    total_panchayats: int
    total_crops_evaluated: int
    total_risk_evaluations: int
    detected_risks_count: int
    not_detected_count: int
    insufficient_data_count: int
    results: List[RiskResult]
    execution_timestamp: str
    limitations_note: str = (
        "Phase 10 Agricultural Risk Engine: Identifies crop stress and environmental risk conditions. "
        "Disease-favorable evaluations indicate environmental suitability, NOT a disease diagnosis. "
        "Farmer advisories and management prescriptions are strictly deferred to Phase 11."
    )


class PanchayatRiskProfile(BaseModel):
    """Consolidated agricultural risk profile for a single Gram Panchayat."""
    panchayat_id: int
    panchayat_name: str
    lgd_code: str
    block_id: int
    block_name: Optional[str] = None
    evaluation_date: str
    crop_risks: Dict[str, List[RiskResult]]  # Crop name -> List of risk results
    detected_risks_count: int
    highest_severity: str


class RiskSubsystemStatus(BaseModel):
    """Subsystem-wide risk evaluation inventory and status."""
    total_risk_records: int
    detected_risks: int
    not_detected_evaluations: int
    insufficient_data_evaluations: int
    risk_counts_by_type: Dict[str, int]
    risk_counts_by_severity: Dict[str, int]
    panchayats_evaluated: int
    crops_evaluated: int
    active_rule_version: str = "agri_risk_v1.0.0"
