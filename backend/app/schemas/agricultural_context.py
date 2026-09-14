"""
Agricultural Context Schemas
SIH Problem Statement 26074 (Agro-Meteorological Advisory Services)

Defines data models and validation contracts for:
- Panchayat Weather + Crop + Crop Stage + Soil Context snapshot
- Multi-crop agricultural profiles per Panchayat
- Phenological stage resolution and soil profile diagnostics
- Batch and single Panchayat context requests and responses
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class CropStageContext(BaseModel):
    """Resolved phenological growth stage context for a crop."""
    phenology_stage_id: Optional[int] = Field(None, description="Database ID of resolved phenology stage")
    stage_name: Optional[str] = Field(None, description="Name of phenological stage (e.g. Vegetative, Flowering)")
    stage_order: Optional[int] = Field(None, description="Sequential stage order (1, 2, 3...)")
    gdd_required: Optional[float] = Field(None, description="Growing Degree Days needed for stage")
    water_sensitivity: Optional[str] = Field(None, description="Sensitivity to water stress: LOW, MODERATE, HIGH, CRITICAL")
    temp_sensitivity: Optional[str] = Field(None, description="Sensitivity to thermal stress: LOW, MODERATE, HIGH, CRITICAL")
    
    stage_derivation_method: str = Field(
        default="UNKNOWN",
        description="Method used: OBSERVED, PLANTING_DATE, CROP_CALENDAR, UNKNOWN"
    )
    planting_date: Optional[str] = Field(None, description="Sowing/Planting date (ISO format YYYY-MM-DD)")
    days_since_planting: Optional[int] = Field(None, description="Days elapsed since planting date")
    expected_harvest_date: Optional[str] = Field(None, description="Estimated harvest date (ISO format YYYY-MM-DD)")
    is_stage_resolved: bool = Field(default=False, description="True if a valid stage was explicitly resolved")

    model_config = ConfigDict(from_attributes=True)


class SoilContextSummary(BaseModel):
    """Soil physical, chemical, and hydrological properties for agricultural context."""
    soil_profile_id: Optional[int] = Field(None, description="Database ID of soil profile")
    soil_type: Optional[str] = Field(None, description="Soil classification: Alluvial, Black, Red, Sandy Loam, Clay")
    texture: Optional[str] = Field(None, description="Soil texture description")
    drainage_class: Optional[str] = Field(None, description="Drainage class: Excessive, Well, Moderate, Poor")
    water_holding_capacity_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Available water capacity %")
    ph_level: Optional[float] = Field(None, ge=0.0, le=14.0, description="Soil pH level")
    organic_carbon_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Soil organic carbon %")
    available_nitrogen_kg_ha: Optional[float] = Field(None, ge=0.0, description="Available nitrogen in kg/ha")
    available_phosphorus_kg_ha: Optional[float] = Field(None, ge=0.0, description="Available phosphorus in kg/ha")
    available_potassium_kg_ha: Optional[float] = Field(None, ge=0.0, description="Available potassium in kg/ha")
    
    soil_available: bool = Field(default=False, description="True if soil profile is mapped")
    soil_status: str = Field(default="UNAVAILABLE", description="COMPLETE, PARTIAL, UNAVAILABLE")

    model_config = ConfigDict(from_attributes=True)


class WeatherContextSummary(BaseModel):
    """Associated Panchayat-level downscaled weather snapshot."""
    panchayat_weather_id: Optional[int] = Field(None, description="Database ID of PanchayatWeather record")
    forecast_valid_time: Optional[str] = Field(None, description="Valid forecast datetime (ISO UTC)")
    mean_temp_c: Optional[float] = Field(None, description="Area-weighted mean temperature in °C")
    min_temp_c: Optional[float] = Field(None, description="Minimum temperature in °C")
    max_temp_c: Optional[float] = Field(None, description="Maximum temperature in °C")
    temp_stddev_c: Optional[float] = Field(None, description="Spatial temperature standard deviation in °C")
    weather_status: str = Field(default="UNAVAILABLE", description="COMPLETE, PARTIAL, UNAVAILABLE")

    model_config = ConfigDict(from_attributes=True)


class PanchayatCropContextSummary(BaseModel):
    """Normalized Agricultural Context snapshot for a specific Crop in a Panchayat."""
    id: Optional[int] = Field(None, description="Database record ID")
    panchayat_id: int = Field(..., description="Gram Panchayat ID")
    panchayat_name: str = Field(..., description="Gram Panchayat Name")
    block_id: int = Field(..., description="Parent Block ID")
    block_name: Optional[str] = Field(None, description="Parent Block Name")
    
    crop_id: int = Field(..., description="Crop ID")
    crop_name: str = Field(..., description="Common crop name (e.g. Rice, Wheat, Maize)")
    scientific_name: Optional[str] = Field(None, description="Botanical name")
    season: Optional[str] = Field(None, description="Cropping season (Kharif, Rabi, Zaid)")

    # Context components
    crop_stage: CropStageContext
    soil: SoilContextSummary
    weather: WeatherContextSummary

    # Cropland area
    crop_area_ha: Optional[float] = Field(None, ge=0.0, description="Cultivated crop area in hectares")
    agricultural_area_ha: Optional[float] = Field(None, ge=0.0, description="Total agricultural cropland in hectares")
    crop_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Crop area fraction of total cropland")
    is_agricultural_eligible: bool = Field(default=True, description="Whether Panchayat has verified cropland")

    # Metadata & Quality
    context_date: str = Field(..., description="Target forecast / evaluation date (ISO UTC)")
    source: str = Field(default="AGRI_CONTEXT_ENGINE", description="Context generation engine")
    source_version: Optional[str] = Field(default="v1.0.0", description="Service engine version")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Context integrity confidence score")
    status: str = Field(..., description="COMPLETE, PARTIAL, UNAVAILABLE")
    quality_flags: List[str] = Field(default_factory=list, description="Diagnostic quality alerts")
    provenance: Optional[Dict[str, Any]] = Field(None, description="Traceable data sources and timestamps")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(from_attributes=True)


class AgriculturalContextRequest(BaseModel):
    """Request payload for constructing Panchayat Agricultural Context."""
    block_id: int = Field(..., description="Parent Block ID to process")
    panchayat_id: Optional[int] = Field(None, description="Optional single Panchayat ID filter")
    context_date: datetime = Field(..., description="Target forecast valid timestamp (UTC)")
    source_model: Optional[str] = Field("IMD-GFS", description="Source NWP forecast model identifier")
    model_version: Optional[str] = Field(None, description="Phase 6 model version")
    persist_to_db: bool = Field(default=True, description="Whether to persist context records to database")


class AgriculturalContextResponse(BaseModel):
    """Response returned upon completion of Agricultural Context generation."""
    context_run_id: str
    block_id: int
    block_name: str
    context_date: str
    total_panchayats: int
    total_crop_contexts: int
    complete_contexts_count: int
    partial_contexts_count: int
    unavailable_contexts_count: int
    contexts: List[PanchayatCropContextSummary]
    execution_timestamp: str
    limitations_note: str = (
        "Phase 9 Panchayat Agricultural Context: Combines downscaled weather, crop stage, and soil characteristics. "
        "Agricultural risk detection, pest/disease prediction, and farmer advisories are strictly deferred to Phase 10."
    )


class PanchayatAgriculturalProfile(BaseModel):
    """Multi-crop agricultural profile for a single Gram Panchayat."""
    panchayat_id: int
    panchayat_name: str
    lgd_code: str
    block_id: int
    block_name: Optional[str] = None
    context_date: str
    is_agricultural_eligible: bool
    agricultural_area_ha: Optional[float] = None
    total_active_crops: int
    crop_contexts: List[PanchayatCropContextSummary]
    overall_status: str


class AgricultureSubsystemStatus(BaseModel):
    """Subsystem-wide agricultural inventory and coverage status."""
    total_context_records: int
    panchayats_with_crop_mappings: int
    panchayats_with_soil_profiles: int
    panchayats_with_resolved_stages: int
    complete_status_count: int
    partial_status_count: int
    unavailable_status_count: int
    last_context_date: Optional[str] = None
