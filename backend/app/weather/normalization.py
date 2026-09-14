from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, Union
from dateutil import parser as date_parser
from app.weather.schemas import ParsedWeatherRecord, NormalizedWeatherRecord, ValidationErrorDetail, QualityFlag
from app.weather.validation import WeatherValidator


class WeatherNormalizer:
    """
    Transforms raw units and timestamps into standardized SI/meteorological units
    and UTC timezone-aware datetimes.
    """

    @staticmethod
    def parse_datetime_to_utc(dt_val: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """Converts datetime or string into a timezone-aware UTC datetime object."""
        if dt_val is None:
            return None
        if isinstance(dt_val, datetime):
            if dt_val.tzinfo is None:
                return dt_val.replace(tzinfo=timezone.utc)
            return dt_val.astimezone(timezone.utc)

        val_str = str(dt_val).strip()
        if not val_str or val_str.lower() in ["none", "null", "nan"]:
            return None

        try:
            parsed = date_parser.parse(val_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def normalize_temperature(val: Optional[Union[float, str]], unit: str = "C") -> Tuple[Optional[float], bool]:
        """Normalizes temperature to Celsius. Returns (normalized_celsius, was_converted)."""
        if val is None:
            return None, False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return None, False

        unit = unit.strip().upper() if unit else "C"
        if unit in ["F", "FAHRENHEIT"]:
            return round((fval - 32.0) * (5.0 / 9.0), 2), True
        elif unit in ["K", "KELVIN"]:
            return round(fval - 273.15, 2), True
        return round(fval, 2), False

    @staticmethod
    def normalize_rainfall(val: Optional[Union[float, str]], unit: str = "mm") -> Tuple[Optional[float], bool]:
        """Normalizes rainfall to millimeters (mm). Returns (normalized_mm, was_converted)."""
        if val is None:
            return None, False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return None, False

        unit = unit.strip().lower() if unit else "mm"
        if unit in ["in", "inch", "inches"]:
            return round(fval * 25.4, 2), True
        elif unit in ["cm", "centimeter", "centimeters"]:
            return round(fval * 10.0, 2), True
        return round(fval, 2), False

    @staticmethod
    def normalize_wind_speed(
        val: Optional[Union[float, str]],
        unit: str = "km/h"
    ) -> Tuple[Optional[float], Optional[float], bool]:
        """
        Normalizes wind speed to both m/s and km/h.
        Returns (wind_speed_mps, wind_speed_kmh, was_converted).
        """
        if val is None:
            return None, None, False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return None, None, False

        unit = unit.strip().lower() if unit else "km/h"
        was_converted = False

        if unit in ["m/s", "mps", "meter_per_second"]:
            mps = fval
            kmh = fval * 3.6
        elif unit in ["km/h", "kmh", "kph"]:
            kmh = fval
            mps = fval / 3.6
        elif unit in ["mph", "miles_per_hour"]:
            mps = fval * 0.44704
            kmh = mps * 3.6
            was_converted = True
        elif unit in ["kt", "knot", "knots"]:
            mps = fval * 0.514444
            kmh = mps * 3.6
            was_converted = True
        else:
            # Default fallback assumption is km/h
            kmh = fval
            mps = fval / 3.6

        return round(mps, 2), round(kmh, 2), was_converted

    @classmethod
    def normalize_record(
        cls,
        parsed: ParsedWeatherRecord,
        conversion_tracker: Optional[Dict[str, int]] = None
    ) -> NormalizedWeatherRecord:
        """
        Normalizes a ParsedWeatherRecord into NormalizedWeatherRecord.
        Tracks unit conversions and records validation issues.
        """
        if conversion_tracker is None:
            conversion_tracker = {}

        errors: List[ValidationErrorDetail] = []

        # 1. Timestamps
        valid_time_utc = cls.parse_datetime_to_utc(parsed.valid_time_raw)
        if valid_time_utc is None:
            errors.append(
                ValidationErrorDetail(
                    row_number=parsed.row_number,
                    field="valid_time",
                    rejected_value=parsed.valid_time_raw,
                    reason="Invalid or unparseable target forecast date/valid_time timestamp."
                )
            )
            # Default to now if invalid to allow validation error preservation
            valid_time_utc = datetime.now(timezone.utc)

        forecast_gen_utc = cls.parse_datetime_to_utc(parsed.forecast_generated_at_raw)
        if forecast_gen_utc is None:
            forecast_gen_utc = valid_time_utc  # Fallback to valid_time if run_time omitted

        # 2. Coordinates
        lat_float: Optional[float] = None
        lon_float: Optional[float] = None
        if parsed.latitude is not None:
            try:
                lat_float = float(parsed.latitude)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        row_number=parsed.row_number,
                        field="latitude",
                        rejected_value=parsed.latitude,
                        reason="Latitude could not be parsed to numeric float."
                    )
                )

        if parsed.longitude is not None:
            try:
                lon_float = float(parsed.longitude)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        row_number=parsed.row_number,
                        field="longitude",
                        rejected_value=parsed.longitude,
                        reason="Longitude could not be parsed to numeric float."
                    )
                )

        # 3. Weather variables normalization
        temp_min_c, tmin_conv = cls.normalize_temperature(parsed.temp_min_raw, parsed.temp_unit or "C")
        if tmin_conv:
            conversion_tracker["temperature_f_to_c"] = conversion_tracker.get("temperature_f_to_c", 0) + 1

        temp_max_c, tmax_conv = cls.normalize_temperature(parsed.temp_max_raw, parsed.temp_unit or "C")
        if tmax_conv:
            conversion_tracker["temperature_f_to_c"] = conversion_tracker.get("temperature_f_to_c", 0) + 1

        rain_mm, rain_conv = cls.normalize_rainfall(parsed.rainfall_raw, parsed.rain_unit or "mm")
        if rain_conv:
            conversion_tracker["rainfall_in_to_mm"] = conversion_tracker.get("rainfall_in_to_mm", 0) + 1

        wind_mps, wind_kmh, wind_conv = cls.normalize_wind_speed(parsed.wind_speed_raw, parsed.wind_speed_unit or "km/h")
        if wind_conv:
            conversion_tracker["wind_mph_to_mps"] = conversion_tracker.get("wind_mph_to_mps", 0) + 1

        # Humidity
        humidity_pct: Optional[float] = None
        if parsed.humidity_raw is not None:
            try:
                humidity_pct = round(float(parsed.humidity_raw), 2)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        row_number=parsed.row_number,
                        field="relative_humidity",
                        rejected_value=parsed.humidity_raw,
                        reason="Humidity value is not a valid number."
                    )
                )

        # Wind Direction
        wind_dir_deg: Optional[float] = None
        if parsed.wind_direction_raw is not None:
            try:
                wind_dir_deg = round(float(parsed.wind_direction_raw), 2)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        row_number=parsed.row_number,
                        field="wind_direction",
                        rejected_value=parsed.wind_direction_raw,
                        reason="Wind direction is not a valid number."
                    )
                )

        # Cloud Cover
        cloud_pct: Optional[float] = None
        if parsed.cloud_cover_raw is not None:
            try:
                cloud_pct = round(float(parsed.cloud_cover_raw), 2)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        row_number=parsed.row_number,
                        field="cloud_cover",
                        rejected_value=parsed.cloud_cover_raw,
                        reason="Cloud cover is not a valid number."
                    )
                )

        # 4. Perform Physical Limit Validation Checks
        coord_errors = WeatherValidator.validate_coordinates(lat_float, lon_float, parsed.row_number)
        val_errors = WeatherValidator.validate_values(
            temp_min_c, temp_max_c, rain_mm, humidity_pct, wind_mps, wind_dir_deg, cloud_pct, parsed.row_number
        )
        errors.extend(coord_errors)
        errors.extend(val_errors)

        return NormalizedWeatherRecord(
            row_number=parsed.row_number,
            block_identifier=parsed.block_identifier,
            station_identifier=parsed.station_identifier,
            latitude=lat_float,
            longitude=lon_float,
            forecast_generated_at=forecast_gen_utc,
            valid_time=valid_time_utc,
            temp_min_celsius=temp_min_c,
            temp_max_celsius=temp_max_c,
            rainfall_mm=rain_mm,
            relative_humidity_pct=humidity_pct,
            wind_speed_mps=wind_mps,
            wind_speed_kmh=wind_kmh,
            wind_direction_deg=wind_dir_deg,
            cloud_cover_pct=cloud_pct,
            quality_flag=QualityFlag.INVALID if errors else QualityFlag.VALID,
            validation_errors=errors,
            source=parsed.source,
            model_name=parsed.model_name,
            raw_payload=parsed.raw_payload,
        )
