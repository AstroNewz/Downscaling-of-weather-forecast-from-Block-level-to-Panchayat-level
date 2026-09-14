from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models.spatial import LandUseMask, Panchayat
from app.gis.schemas import LandUseFeatures
from app.core.logging import logger


class LandUseExtractor:
    """
    Extracts land-use and land-cover (LULC) composition fractions and cropland eligibility flags.
    """

    @staticmethod
    def extract_from_mask_record(mask: LandUseMask) -> LandUseFeatures:
        """Computes normalized land-use fractions from a LandUseMask database model instance."""
        total = mask.total_area_ha
        if total <= 0.0:
            return LandUseFeatures(
                total_area_ha=0.0,
                cropland_area_ha=0.0,
                cropland_fraction=0.0,
                forest_fraction=0.0,
                urban_fraction=0.0,
                water_fraction=0.0,
                barren_fraction=0.0,
                is_agricultural_cropland=mask.is_agricultural_eligible,
            )

        return LandUseFeatures(
            total_area_ha=round(total, 2),
            cropland_area_ha=round(mask.cropland_area_ha, 2),
            cropland_fraction=round(min(1.0, max(0.0, mask.cropland_area_ha / total)), 4),
            forest_fraction=round(min(1.0, max(0.0, mask.forest_area_ha / total)), 4),
            urban_fraction=round(min(1.0, max(0.0, mask.urban_area_ha / total)), 4),
            water_fraction=round(min(1.0, max(0.0, mask.water_area_ha / total)), 4),
            barren_fraction=round(min(1.0, max(0.0, mask.barren_area_ha / total)), 4),
            is_agricultural_cropland=mask.is_agricultural_eligible,
        )

    @classmethod
    def get_land_use_by_panchayat_id(cls, db: Session, panchayat_id: int) -> Optional[LandUseFeatures]:
        """Queries LandUseMask for a given Panchayat ID and returns LandUseFeatures."""
        mask = db.scalar(select(LandUseMask).where(LandUseMask.panchayat_id == panchayat_id))
        if mask:
            return cls.extract_from_mask_record(mask)
        return None
