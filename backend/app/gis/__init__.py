"""
Geospatial Information System (GIS) Engine.
Subsystem for:
- 1-km spatial grid generation in projected UTM coordinate systems
- Topographic / DEM terrain analysis (Elevation, Slope, Aspect, TRI, Lapse Rate)
- Land-Use & Land-Cover (LULC) cropland masking and area fraction calculations
- Spatial vector operations (Centroid distances, Point-in-polygon queries)
- Unified environmental feature extraction service
"""
from app.gis.schemas import TerrainFeatures, LandUseFeatures, EnvironmentalFeatureSet
from app.gis.raster import RasterSampler
from app.gis.dem import DEMTopographicEngine
from app.gis.landuse import LandUseExtractor
from app.gis.spatial_features import SpatialFeatureExtractor
from app.gis.feature_service import GISEnvironmentalFeatureService
from app.gis.grid import SpatialGridGenerator, GridCellRecord, SpatialGridDomainResult
from app.gis.boundary_ingestion import PanchayatBoundaryIngestor
from app.gis.boundary_registry import PanchayatBoundaryRegistry, boundary_registry
from app.gis.boundary_service import PanchayatBoundaryService, panchayat_boundary_service, resolve_panchayat_from_coordinates
from app.gis.spatial_masking import SpatialMaskingService, spatial_masking_service, extract_panchayat_spatial_features

__all__ = [
    "TerrainFeatures",
    "LandUseFeatures",
    "EnvironmentalFeatureSet",
    "RasterSampler",
    "DEMTopographicEngine",
    "LandUseExtractor",
    "SpatialFeatureExtractor",
    "GISEnvironmentalFeatureService",
    "SpatialGridGenerator",
    "GridCellRecord",
    "SpatialGridDomainResult",
    "PanchayatBoundaryIngestor",
    "PanchayatBoundaryRegistry",
    "boundary_registry",
    "PanchayatBoundaryService",
    "panchayat_boundary_service",
    "resolve_panchayat_from_coordinates",
    "SpatialMaskingService",
    "spatial_masking_service",
    "extract_panchayat_spatial_features",
]



