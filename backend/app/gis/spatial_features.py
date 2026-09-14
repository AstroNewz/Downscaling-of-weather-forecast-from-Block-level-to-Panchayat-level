import math
from typing import Optional, Tuple, Dict, Any
from shapely.geometry import shape, Point
from app.utils.validators import validate_lat_lon


class SpatialFeatureExtractor:
    """
    Computes spatial distances and resolves vector relationships between coordinates and administrative polygons.
    """

    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes great-circle distance between two coordinates in kilometers."""
        r = 6371.0  # Earth radius (km)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 3)

    @classmethod
    def extract_centroid_coordinates(cls, geometry_obj: Any) -> Tuple[Optional[float], Optional[float]]:
        """Extracts (centroid_lat, centroid_lon) from a GeoAlchemy2 geometry or GeoJSON dictionary."""
        if geometry_obj is None:
            return None, None
        try:
            if hasattr(geometry_obj, "data"):  # GeoAlchemy2 WKBElement
                from geoalchemy2.shape import to_shape
                geom = to_shape(geometry_obj)
                cent = geom.centroid
                return round(cent.y, 6), round(cent.x, 6)
            elif isinstance(geometry_obj, dict):
                geom = shape(geometry_obj)
                cent = geom.centroid
                return round(cent.y, 6), round(cent.x, 6)
        except Exception:
            return None, None
        return None, None
