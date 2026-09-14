from typing import List, Tuple, Optional
from app.weather.schemas import ParsedWeatherRecord, ValidationErrorDetail


class WeatherValidator:
    """
    Validation engine verifying physical limits, coordinates, and chronological consistency.
    """

    # Physical limits for Earth atmospheric conditions
    LAT_RANGE = (-90.0, 90.0)
    LON_RANGE = (-180.0, 180.0)
    TEMP_ABSOLUTE_RANGE = (-60.0, 65.0)  # Extreme thermodynamic physical limits (°C)
    HUMIDITY_RANGE = (0.0, 100.0)
    WIND_SPEED_MAX_MPS = 100.0  # Category 5 hurricane gust limit (~360 km/h)
    WIND_DIR_RANGE = (0.0, 360.0)
    CLOUD_COVER_RANGE = (0.0, 100.0)
    RAINFALL_DAILY_MAX_MM = 1500.0  # Extreme world record 24h precipitation threshold

    @classmethod
    def validate_coordinates(
        cls,
        lat: Optional[float],
        lon: Optional[float],
        row_num: Optional[int] = None
    ) -> List[ValidationErrorDetail]:
        errors: List[ValidationErrorDetail] = []
        if lat is not None:
            if not (cls.LAT_RANGE[0] <= lat <= cls.LAT_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="latitude",
                        rejected_value=lat,
                        reason=f"Latitude {lat} is outside valid bounds [-90, +90]."
                    )
                )
        if lon is not None:
            if not (cls.LON_RANGE[0] <= lon <= cls.LON_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="longitude",
                        rejected_value=lon,
                        reason=f"Longitude {lon} is outside valid bounds [-180, +180]."
                    )
                )
        return errors

    @classmethod
    def validate_values(
        cls,
        temp_min: Optional[float],
        temp_max: Optional[float],
        rainfall: Optional[float],
        humidity: Optional[float],
        wind_speed_mps: Optional[float],
        wind_direction: Optional[float],
        cloud_cover: Optional[float],
        row_num: Optional[int] = None
    ) -> List[ValidationErrorDetail]:
        errors: List[ValidationErrorDetail] = []

        # Temperature checks
        if temp_min is not None:
            if not (cls.TEMP_ABSOLUTE_RANGE[0] <= temp_min <= cls.TEMP_ABSOLUTE_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="temp_min",
                        rejected_value=temp_min,
                        reason=f"Minimum temperature {temp_min}°C is outside plausible bounds [-60, 65]°C."
                    )
                )
        if temp_max is not None:
            if not (cls.TEMP_ABSOLUTE_RANGE[0] <= temp_max <= cls.TEMP_ABSOLUTE_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="temp_max",
                        rejected_value=temp_max,
                        reason=f"Maximum temperature {temp_max}°C is outside plausible bounds [-60, 65]°C."
                    )
                )
        if temp_min is not None and temp_max is not None:
            if temp_min > temp_max:
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="temperature_consistency",
                        rejected_value={"temp_min": temp_min, "temp_max": temp_max},
                        reason=f"Minimum temperature ({temp_min}°C) cannot exceed maximum temperature ({temp_max}°C)."
                    )
                )

        # Rainfall checks
        if rainfall is not None:
            if rainfall < 0.0:
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="rainfall",
                        rejected_value=rainfall,
                        reason=f"Rainfall cannot be negative: {rainfall} mm."
                    )
                )
            elif rainfall > cls.RAINFALL_DAILY_MAX_MM:
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="rainfall",
                        rejected_value=rainfall,
                        reason=f"Rainfall exceeds theoretical physical threshold: {rainfall} mm."
                    )
                )

        # Humidity checks
        if humidity is not None:
            if not (cls.HUMIDITY_RANGE[0] <= humidity <= cls.HUMIDITY_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="relative_humidity",
                        rejected_value=humidity,
                        reason=f"Relative humidity must be within [0, 100]%, got {humidity}%."
                    )
                )

        # Wind checks
        if wind_speed_mps is not None:
            if wind_speed_mps < 0.0:
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="wind_speed",
                        rejected_value=wind_speed_mps,
                        reason=f"Wind speed cannot be negative: {wind_speed_mps} m/s."
                    )
                )
            elif wind_speed_mps > cls.WIND_SPEED_MAX_MPS:
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="wind_speed",
                        rejected_value=wind_speed_mps,
                        reason=f"Wind speed {wind_speed_mps} m/s exceeds physical maximum."
                    )
                )

        if wind_direction is not None:
            if not (cls.WIND_DIR_RANGE[0] <= wind_direction <= cls.WIND_DIR_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="wind_direction",
                        rejected_value=wind_direction,
                        reason=f"Wind direction must be within [0, 360] degrees, got {wind_direction}."
                    )
                )

        # Cloud cover checks
        if cloud_cover is not None:
            if not (cls.CLOUD_COVER_RANGE[0] <= cloud_cover <= cls.CLOUD_COVER_RANGE[1]):
                errors.append(
                    ValidationErrorDetail(
                        row_number=row_num,
                        field="cloud_cover",
                        rejected_value=cloud_cover,
                        reason=f"Cloud cover percentage must be within [0, 100]%, got {cloud_cover}%."
                    )
                )

        return errors
