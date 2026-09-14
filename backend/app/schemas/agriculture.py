from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agricultural_context import (
    CropStageContext,
    SoilContextSummary,
    WeatherContextSummary,
    PanchayatCropContextSummary,
    AgriculturalContextRequest,
    AgriculturalContextResponse,
    PanchayatAgriculturalProfile,
    AgricultureSubsystemStatus,
)


class CropStageInfo(BaseModel):
    """Crop phenology stage details."""
    stage_name: str = Field(..., description="Stage name: Sowing, Vegetative, Flowering, Grain Filling, Harvesting")
    stage_order: int = Field(..., description="Chronological stage sequence number")
    water_sensitivity: str = Field(..., description="Sensitivity to water stress: Low, Moderate, High, Critical")
    temperature_sensitivity: str = Field(..., description="Sensitivity to heat/frost stress")


class CropContext(BaseModel):
    """Crop profile and agricultural context."""
    crop_id: str = Field(..., description="Crop identifier")
    crop_name: str = Field(..., description="Common crop name (e.g. Paddy, Wheat, Mustard, Cotton)")
    scientific_name: Optional[str] = Field(None)
    season: str = Field(..., description="Kharif, Rabi, Zaid")
    current_stage: Optional[str] = Field(None, description="Active phenological stage")
    soil_types_preferred: List[str] = Field(default_factory=list, description="Suitable soil types")

    model_config = ConfigDict(from_attributes=True)


class SoilProfile(BaseModel):
    """Soil physical and chemical characteristics."""
    soil_type: str = Field(..., description="e.g. Alluvial, Black, Red, Sandy Loam")
    texture: Optional[str] = None
    drainage_class: str = Field(default="Moderate", description="Well-drained, Poorly-drained, Excessive")
    water_holding_capacity_pct: float = Field(..., ge=0.0, le=100.0)

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "CropStageInfo",
    "CropContext",
    "SoilProfile",
    "CropStageContext",
    "SoilContextSummary",
    "WeatherContextSummary",
    "PanchayatCropContextSummary",
    "AgriculturalContextRequest",
    "AgriculturalContextResponse",
    "PanchayatAgriculturalProfile",
    "AgricultureSubsystemStatus",
]

