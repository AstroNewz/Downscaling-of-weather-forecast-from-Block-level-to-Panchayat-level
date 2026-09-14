from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TerrainFeatures(BaseModel):
    """Topographic and relief variables derived from DEM / elevation data."""
    elevation_m: Optional[float] = Field(None, description="Surface elevation in meters above sea level")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Terrain slope inclination in degrees")
    aspect_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Terrain aspect/orientation in degrees (0-360°)")
    sin_aspect: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Sine of terrain aspect (North-South orientation)")
    cos_aspect: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Cosine of terrain aspect (East-West orientation)")
    terrain_roughness: Optional[float] = Field(None, ge=0.0, description="Terrain Roughness Index (TRI)")
    elevation_diff_to_block_m: Optional[float] = Field(None, description="Elevation relative to mean Block elevation (m)")
    lapse_rate_temp_adjustment_c: Optional[float] = Field(
        None,
        description="Standard atmospheric lapse-rate temperature adjustment: -6.5°C/1000m * Delta_z"
    )

    model_config = ConfigDict(from_attributes=True)


class LandUseFeatures(BaseModel):
    """Land-Use / Land-Cover (LULC) composition fractions for an area."""
    total_area_ha: Optional[float] = Field(None, ge=0.0)
    cropland_area_ha: Optional[float] = Field(None, ge=0.0)
    cropland_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of land in agricultural cultivation")
    forest_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of forest/canopy cover")
    urban_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of urban/built-up cover")
    water_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of open water bodies")
    barren_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of barren/fallow land")
    is_agricultural_cropland: bool = Field(default=True, description="True if area meets cropland advisory eligibility")

    model_config = ConfigDict(from_attributes=True)


class EnvironmentalFeatureSet(BaseModel):
    """
    Unified environmental predictor set combining terrain, spatial distance, and LULC context.
    """
    latitude: float
    longitude: float
    block_id: Optional[int] = None
    panchayat_id: Optional[int] = None

    # Terrain / Topography
    terrain: Optional[TerrainFeatures] = None

    # Land-Use & Land-Cover
    land_use: Optional[LandUseFeatures] = None

    # Spatial Distances
    distance_to_block_centroid_km: Optional[float] = None
    distance_to_panchayat_centroid_km: Optional[float] = None

    # Data provenance and layer availability tracking
    feature_provenance: Dict[str, str] = Field(
        default_factory=dict,
        description="Tracks which spatial layers provided values vs defaulted to None"
    )

    model_config = ConfigDict(from_attributes=True)
