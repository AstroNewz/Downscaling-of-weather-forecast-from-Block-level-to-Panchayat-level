from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.gis.schemas import EnvironmentalFeatureSet, TerrainFeatures, LandUseFeatures
from app.gis.dem import DEMTopographicEngine
from app.gis.landuse import LandUseExtractor
from app.gis.spatial_features import SpatialFeatureExtractor
from app.core.config import settings
from app.core.logging import logger


class GISEnvironmentalFeatureService:
    """
    Unified environmental feature orchestrator combining DEM topography,
    spatial geometries, and LULC land-use classifications.
    """

    def __init__(self, db: Session, dem_raster_path: Optional[str] = None):
        self.db = db
        self.dem_raster_path = dem_raster_path

    def get_features_for_location(
        self,
        latitude: float,
        longitude: float,
        block_id: Optional[int] = None,
        panchayat_id: Optional[int] = None
    ) -> EnvironmentalFeatureSet:
        """
        Extracts all terrain, spatial distance, and land-use features for a given coordinate.
        """
        provenance: Dict[str, str] = {}

        # 1. Spatial Entities from Database
        block = self.db.scalar(select(Block).where(Block.id == block_id)) if block_id else None
        panchayat = self.db.scalar(select(Panchayat).where(Panchayat.id == panchayat_id)) if panchayat_id else None

        # 2. Distance Calculations
        dist_block_km = None
        block_elev = None
        if block:
            block_lat, block_lon = SpatialFeatureExtractor.extract_centroid_coordinates(block.centroid or block.geometry)
            if block_lat is not None and block_lon is not None:
                dist_block_km = SpatialFeatureExtractor.haversine_distance_km(latitude, longitude, block_lat, block_lon)
                provenance["distance_to_block"] = "COMPUTED_FROM_BLOCK_CENTROID"

        dist_panchayat_km = None
        if panchayat:
            p_lat, p_lon = SpatialFeatureExtractor.extract_centroid_coordinates(panchayat.centroid or panchayat.geometry)
            if p_lat is not None and p_lon is not None:
                dist_panchayat_km = SpatialFeatureExtractor.haversine_distance_km(latitude, longitude, p_lat, p_lon)
                provenance["distance_to_panchayat"] = "COMPUTED_FROM_PANCHAYAT_CENTROID"

        # 3. Topographic / DEM Features
        db_elevation = panchayat.elevation_meters if (panchayat and panchayat.elevation_meters) else None
        terrain = DEMTopographicEngine.extract_terrain_features(
            latitude=latitude,
            longitude=longitude,
            dem_raster_path=self.dem_raster_path,
            db_elevation_m=db_elevation,
            block_elevation_m=block_elev
        )
        provenance["terrain_source"] = "DEM_RASTER" if (self.dem_raster_path and terrain.slope_deg is not None) else ("DATABASE_PANCHAYAT_ELEVATION" if db_elevation else "UNAVAILABLE")

        # 4. Land-Use / Cropland Features
        land_use = None
        if panchayat_id:
            land_use = LandUseExtractor.get_land_use_by_panchayat_id(self.db, panchayat_id)
            if land_use:
                provenance["land_use_source"] = "DATABASE_LAND_USE_MASK"

        if land_use is None:
            provenance["land_use_source"] = "UNAVAILABLE"

        return EnvironmentalFeatureSet(
            latitude=latitude,
            longitude=longitude,
            block_id=block_id,
            panchayat_id=panchayat_id,
            terrain=terrain,
            land_use=land_use,
            distance_to_block_centroid_km=dist_block_km,
            distance_to_panchayat_centroid_km=dist_panchayat_km,
            feature_provenance=provenance,
        )
