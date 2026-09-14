from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PanchayatBase(BaseModel):
    """Base schema for Gram Panchayat administrative unit."""
    panchayat_id: str = Field(..., description="Unique Panchayat code (e.g. LGD Code)")
    name: str = Field(..., description="Name of the Gram Panchayat")
    block_id: str = Field(..., description="Identifier of parent block")
    district_name: str = Field(..., description="District name")
    state_name: str = Field(..., description="State name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Centroid latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Centroid longitude")
    elevation_meters: Optional[float] = Field(None, description="Average elevation in meters")


class LandUseComposition(BaseModel):
    """Land use and land cover distribution for a Panchayat."""
    total_area_hectares: float = Field(..., ge=0.0, description="Total geographical area")
    cropland_area_hectares: float = Field(..., ge=0.0, description="Net agricultural / cropped area")
    forest_area_hectares: float = Field(default=0.0, ge=0.0)
    urban_area_hectares: float = Field(default=0.0, ge=0.0)
    water_bodies_hectares: float = Field(default=0.0, ge=0.0)
    barren_area_hectares: float = Field(default=0.0, ge=0.0)
    is_agricultural_eligible: bool = Field(
        default=True,
        description="True if cropland exceeds minimum threshold to warrant crop-specific advisories"
    )


class PanchayatResponse(PanchayatBase):
    """Detailed Panchayat response including land-use classification."""
    land_use: Optional[LandUseComposition] = None
    geojson_geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon or multipolygon")

    model_config = ConfigDict(from_attributes=True)
