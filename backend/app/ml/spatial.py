import math
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.db.models.weather import WeatherObservation
from app.db.models.spatial import Block
from app.utils.validators import validate_lat_lon


class SpatialAligner:
    """
    Handles spatial relationship resolution between observation coordinates and administrative Blocks.
    """

    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two points in kilometers using Haversine formula."""
        r = 6371.0  # Earth's radius in kilometers
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 3)

    @classmethod
    def evaluate_spatial_match(
        cls,
        obs: WeatherObservation,
        block: Optional[Block]
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validates spatial relationship and extracts spatial features.

        Returns:
            Tuple of:
            - is_match (bool)
            - spatial_features (Dict[str, Any])
            - rejection_reason (Optional[str])
        """
        # Validate observation coordinates
        valid_coords, coord_msg = validate_lat_lon(obs.latitude, obs.longitude)
        if not valid_coords:
            return False, {}, f"INVALID_COORDINATES: Observation station coordinates invalid: {coord_msg}"

        if block is None:
            return False, {}, "SPATIAL_MISMATCH: No corresponding administrative Block found."

        # Check block association
        if obs.block_id is not None and obs.block_id != block.id:
            return False, {}, f"SPATIAL_MISMATCH: Observation block_id ({obs.block_id}) does not match forecast block_id ({block.id})."

        spatial_data: Dict[str, Any] = {
            "obs_latitude": round(obs.latitude, 6),
            "obs_longitude": round(obs.longitude, 6),
            "block_centroid_lat": None,
            "block_centroid_lon": None,
            "distance_to_centroid_km": None,
            "obs_elevation_m": None,  # Not fabricated
            "block_elevation_m": None,
            "elevation_diff_m": None,
        }

        # If block has coordinates/centroid, compute distance
        # Placeholder or future GIS extension will read block.centroid
        return True, spatial_data, None
