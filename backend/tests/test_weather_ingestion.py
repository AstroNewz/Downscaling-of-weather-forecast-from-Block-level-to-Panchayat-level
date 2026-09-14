import pytest
from datetime import datetime, timezone
from app.weather.providers.csv_provider import CSVWeatherProvider
from app.weather.validation import WeatherValidator
from app.weather.normalization import WeatherNormalizer
from app.weather.quality import WeatherQualityControl
from app.weather.schemas import ParsedWeatherRecord, QualityFlag


def test_csv_provider_parsing_valid():
    """Verifies that CSVWeatherProvider parses CSV strings correctly."""
    csv_data = """block,valid_time,temp_min,temp_max,rainfall,humidity,wind_speed
Varanasi Sadar,2026-09-15 00:00:00,24.5,33.0,12.0,75.0,15.0
Pindra,2026-09-15 00:00:00,23.0,31.5,0.0,65.0,8.0
"""
    provider = CSVWeatherProvider()
    records = provider.parse(csv_data)
    assert len(records) == 2
    assert records[0].block_identifier == "Varanasi Sadar"
    assert records[0].temp_min_raw == "24.5"
    assert records[1].block_identifier == "Pindra"


def test_coordinate_validation():
    """Verifies latitude and longitude bounds checking."""
    # Valid
    assert len(WeatherValidator.validate_coordinates(25.31, 82.97)) == 0
    # Invalid latitude
    errors_lat = WeatherValidator.validate_coordinates(95.0, 82.97)
    assert len(errors_lat) == 1
    assert errors_lat[0].field == "latitude"
    # Invalid longitude
    errors_lon = WeatherValidator.validate_coordinates(25.31, 200.0)
    assert len(errors_lon) == 1
    assert errors_lon[0].field == "longitude"


def test_weather_value_validation():
    """Verifies sanity checks on physical weather variables."""
    # Negative rainfall
    errs = WeatherValidator.validate_values(
        temp_min=20.0, temp_max=30.0, rainfall=-5.0, humidity=50.0,
        wind_speed_mps=5.0, wind_direction=180.0, cloud_cover=50.0
    )
    assert any(e.field == "rainfall" for e in errs)

    # Humidity > 100%
    errs_rh = WeatherValidator.validate_values(
        temp_min=20.0, temp_max=30.0, rainfall=0.0, humidity=120.0,
        wind_speed_mps=5.0, wind_direction=180.0, cloud_cover=50.0
    )
    assert any(e.field == "relative_humidity" for e in errs_rh)

    # Temp min > Temp max
    errs_temp = WeatherValidator.validate_values(
        temp_min=35.0, temp_max=25.0, rainfall=0.0, humidity=50.0,
        wind_speed_mps=5.0, wind_direction=180.0, cloud_cover=50.0
    )
    assert any(e.field == "temperature_consistency" for e in errs_temp)

    # Negative wind speed
    errs_wind = WeatherValidator.validate_values(
        temp_min=20.0, temp_max=30.0, rainfall=0.0, humidity=50.0,
        wind_speed_mps=-2.0, wind_direction=180.0, cloud_cover=50.0
    )
    assert any(e.field == "wind_speed" for e in errs_wind)


def test_unit_normalization():
    """Verifies conversion from imperial and non-standard units to SI/meteorological standard."""
    # Temperature Fahrenheit -> Celsius: 77°F -> 25°C, 32°F -> 0°C
    celsius_77, conv1 = WeatherNormalizer.normalize_temperature(77.0, "F")
    assert celsius_77 == 25.0
    assert conv1 is True

    celsius_32, conv2 = WeatherNormalizer.normalize_temperature(32.0, "F")
    assert celsius_32 == 0.0
    assert conv2 is True

    # Rainfall inches -> mm: 1 in -> 25.4 mm
    rain_mm, r_conv = WeatherNormalizer.normalize_rainfall(1.0, "in")
    assert rain_mm == 25.4
    assert r_conv is True

    # Wind speed mph -> m/s: 10 mph -> 4.47 m/s
    w_mps, w_kmh, w_conv = WeatherNormalizer.normalize_wind_speed(10.0, "mph")
    assert w_mps == 4.47
    assert w_conv is True


def test_timestamp_utc_normalization():
    """Verifies timezone-aware UTC datetime parsing."""
    dt_iso = WeatherNormalizer.parse_datetime_to_utc("2026-09-15T05:30:00+05:30")
    assert dt_iso is not None
    assert dt_iso.tzinfo is not None
    # 05:30 in IST (+05:30) is 00:00 UTC
    assert dt_iso.hour == 0
    assert dt_iso.minute == 0


def test_quality_control_classification():
    """Verifies VALID, SUSPICIOUS, and INVALID quality tagging."""
    tracker = {}

    # 1. Normal valid record
    rec_valid = ParsedWeatherRecord(
        valid_time_raw="2026-09-15 00:00:00",
        temp_min_raw=22.0,
        temp_max_raw=32.0,
        rainfall_raw=10.0,
        humidity_raw=70.0,
        wind_speed_raw=12.0,
    )
    norm_valid = WeatherNormalizer.normalize_record(rec_valid, tracker)
    eval_valid = WeatherQualityControl.evaluate(norm_valid)
    assert eval_valid.quality_flag == QualityFlag.VALID

    # 2. Suspicious heatwave record (Tmax = 50.0°C)
    rec_susp = ParsedWeatherRecord(
        valid_time_raw="2026-09-15 00:00:00",
        temp_min_raw=30.0,
        temp_max_raw=50.0,
        rainfall_raw=0.0,
        humidity_raw=20.0,
        wind_speed_raw=10.0,
    )
    norm_susp = WeatherNormalizer.normalize_record(rec_susp, tracker)
    eval_susp = WeatherQualityControl.evaluate(norm_susp)
    assert eval_susp.quality_flag == QualityFlag.SUSPICIOUS
    assert "Extreme high temperature" in eval_susp.quality_notes

    # 3. Invalid record (Negative rainfall)
    rec_inv = ParsedWeatherRecord(
        valid_time_raw="2026-09-15 00:00:00",
        temp_min_raw=20.0,
        temp_max_raw=30.0,
        rainfall_raw=-10.0,
    )
    norm_inv = WeatherNormalizer.normalize_record(rec_inv, tracker)
    eval_inv = WeatherQualityControl.evaluate(norm_inv)
    assert eval_inv.quality_flag == QualityFlag.INVALID


def test_missing_value_preservation():
    """Verifies that missing variables remain None instead of 0 or -999."""
    rec = ParsedWeatherRecord(
        valid_time_raw="2026-09-15 00:00:00",
        temp_min_raw=None,
        temp_max_raw="30.0",
        rainfall_raw=None,
    )
    norm = WeatherNormalizer.normalize_record(rec)
    assert norm.temp_min_celsius is None
    assert norm.rainfall_mm is None
    assert norm.temp_max_celsius == 30.0
