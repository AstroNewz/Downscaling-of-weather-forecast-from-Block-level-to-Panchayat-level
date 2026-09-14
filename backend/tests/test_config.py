from app.core.config import settings
from app.utils.validators import validate_lat_lon, validate_srid


def test_settings_loaded():
    """Verifies that core application settings load properly."""
    assert settings.APP_NAME == "GraminKrishi-Mausam-Intelligence"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DEFAULT_SRID == 4326
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)


def test_spatial_validators():
    """Verifies coordinate and SRID spatial validation helpers."""
    valid_lat, _ = validate_lat_lon(28.6139, 77.2090)  # New Delhi
    assert valid_lat is True

    invalid_lat, msg = validate_lat_lon(95.0, 77.2090)
    assert invalid_lat is False
    assert "Invalid latitude" in msg

    assert validate_srid(4326) is True
    assert validate_srid(3857) is True
    assert validate_srid(999999) is False
