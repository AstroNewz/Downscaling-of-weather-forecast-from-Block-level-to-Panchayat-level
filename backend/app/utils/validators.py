from typing import Tuple


def validate_lat_lon(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Validates that latitude and longitude fall within standard geographical limits.
    """
    if not (-90.0 <= latitude <= 90.0):
        return False, f"Invalid latitude {latitude}. Must be between -90.0 and 90.0 degrees."
    if not (-180.0 <= longitude <= 180.0):
        return False, f"Invalid longitude {longitude}. Must be between -180.0 and 180.0 degrees."
    return True, "Valid coordinates"


def validate_srid(srid: int) -> bool:
    """
    Validates that the SRID is a supported EPSG code.
    """
    supported_srids = {4326, 3857, 32643, 32644}  # Common Indian UTM zones included
    return srid in supported_srids
