from typing import List, Tuple, Optional
from app.weather.schemas import NormalizedWeatherRecord, QualityFlag


class WeatherQualityControl:
    """
    Quality control engine classifying normalized records into:
    - VALID: Normal plausible meteorological values
    - SUSPICIOUS: Unusually extreme but non-disqualified anomalies (heatwaves, cyclone winds, cloudbursts)
    - INVALID: Physical violations or unparseable corrupted values
    """

    # Configurable thresholds for SUSPICIOUS classification
    SUSPICIOUS_HIGH_TEMP_C = 48.0        # Extreme heatwave threshold
    SUSPICIOUS_LOW_TEMP_C = -25.0        # Extreme freeze in non-Himalayan Indian plains
    SUSPICIOUS_DIURNAL_RANGE_C = 28.0    # Large daily temperature swing (Tmax - Tmin)
    SUSPICIOUS_HIGH_RAIN_MM = 250.0      # Very heavy rainfall / cloudburst threshold
    SUSPICIOUS_HIGH_WIND_MPS = 30.0      # Gale force / severe cyclone winds (~108 km/h)
    SUSPICIOUS_LOW_HUMIDITY_PCT = 5.0    # Unusually arid condition

    @classmethod
    def evaluate(cls, record: NormalizedWeatherRecord) -> NormalizedWeatherRecord:
        """
        Evaluates normalized record, assigning QualityFlag and diagnostic notes.
        """
        # If validator already flagged errors, classify as INVALID
        if record.validation_errors:
            record.quality_flag = QualityFlag.INVALID
            reasons = "; ".join([e.reason for e in record.validation_errors])
            record.quality_notes = f"Validation Failed: {reasons}"
            return record

        suspicious_reasons: List[str] = []

        # Temperature checks
        if record.temp_max_celsius is not None and record.temp_max_celsius >= cls.SUSPICIOUS_HIGH_TEMP_C:
            suspicious_reasons.append(f"Extreme high temperature: {record.temp_max_celsius}°C (>= {cls.SUSPICIOUS_HIGH_TEMP_C}°C)")

        if record.temp_min_celsius is not None and record.temp_min_celsius <= cls.SUSPICIOUS_LOW_TEMP_C:
            suspicious_reasons.append(f"Extreme low temperature: {record.temp_min_celsius}°C (<= {cls.SUSPICIOUS_LOW_TEMP_C}°C)")

        if record.temp_min_celsius is not None and record.temp_max_celsius is not None:
            diurnal_range = record.temp_max_celsius - record.temp_min_celsius
            if diurnal_range >= cls.SUSPICIOUS_DIURNAL_RANGE_C:
                suspicious_reasons.append(f"Unusually large diurnal range: {diurnal_range:.1f}°C")

        # Rainfall checks
        if record.rainfall_mm is not None and record.rainfall_mm >= cls.SUSPICIOUS_HIGH_RAIN_MM:
            suspicious_reasons.append(f"Very high precipitation: {record.rainfall_mm} mm (>= {cls.SUSPICIOUS_HIGH_RAIN_MM} mm)")

        # Wind checks
        if record.wind_speed_mps is not None and record.wind_speed_mps >= cls.SUSPICIOUS_HIGH_WIND_MPS:
            suspicious_reasons.append(f"High gale/cyclonic wind speed: {record.wind_speed_mps} m/s (>= {cls.SUSPICIOUS_HIGH_WIND_MPS} m/s)")

        # Humidity checks
        if record.relative_humidity_pct is not None and record.relative_humidity_pct <= cls.SUSPICIOUS_LOW_HUMIDITY_PCT:
            suspicious_reasons.append(f"Unusually low relative humidity: {record.relative_humidity_pct}% (<= {cls.SUSPICIOUS_LOW_HUMIDITY_PCT}%)")

        if suspicious_reasons:
            record.quality_flag = QualityFlag.SUSPICIOUS
            record.quality_notes = "; ".join(suspicious_reasons)
        else:
            record.quality_flag = QualityFlag.VALID
            record.quality_notes = "Passed automated meteorological quality control."

        return record

    @classmethod
    def evaluate_live_record(
        cls,
        temperature_c: Optional[float],
        valid_time_iso: str,
        humidity_pct: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        precipitation_mm: Optional[float] = None,
        max_age_minutes: int = 180,
    ) -> Tuple[str, str, Optional[float]]:
        """
        Validates live meteorological observations/forecasts for physical plausibility
        and freshness.
        
        Returns:
            Tuple of (quality_status, notes, age_minutes)
            quality_status in {"PASSED", "DEGRADED", "REJECTED", "INSUFFICIENT_DATA"}
        """
        from datetime import datetime, timezone

        if temperature_c is None:
            return "INSUFFICIENT_DATA", "Missing coarse temperature observation.", None

        # Physical limit bounds check [-60, 65]°C
        if not (-60.0 <= temperature_c <= 65.0):
            return "REJECTED", f"Physical violation: Temperature {temperature_c}°C outside plausible limits [-60, 65]°C.", None

        if humidity_pct is not None and not (0.0 <= humidity_pct <= 100.0):
            return "REJECTED", f"Physical violation: Relative humidity {humidity_pct}% outside [0, 100]%.", None

        if wind_speed_kmh is not None and (wind_speed_kmh < 0.0 or wind_speed_kmh > 360.0):
            return "REJECTED", f"Physical violation: Wind speed {wind_speed_kmh} km/h outside [0, 360] km/h.", None

        if precipitation_mm is not None and precipitation_mm < 0.0:
            return "REJECTED", f"Physical violation: Negative precipitation {precipitation_mm} mm.", None

        # Parse timestamp and evaluate freshness
        age_minutes: Optional[float] = None
        try:
            # Handle ISO timestamps with or without Z/timezone
            clean_ts = valid_time_iso.replace("Z", "+00:00")
            if "+" in clean_ts or "-" in clean_ts[10:]:
                vt = datetime.fromisoformat(clean_ts)
            else:
                vt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            # Compare time difference
            diff_seconds = (now_utc - vt).total_seconds()
            age_minutes = round(max(0.0, diff_seconds / 60.0), 1)

            # Future forecasts are acceptable within operational forecast horizon (+72 hours)
            if diff_seconds < -72 * 3600:
                return "DEGRADED", f"Valid time is too far in future ({age_minutes} mins ahead).", age_minutes

            # Stale check: if historical data is older than threshold
            if diff_seconds > max_age_minutes * 60.0:
                return "DEGRADED", f"Data is STALE: Age {age_minutes} minutes exceeds threshold of {max_age_minutes} minutes.", age_minutes

        except Exception as e:
            return "REJECTED", f"Invalid timestamp format '{valid_time_iso}': {e}", None

        # Check for suspicious meteorological extremes
        notes = "Passed automated meteorological QC and freshness validation."
        if temperature_c >= cls.SUSPICIOUS_HIGH_TEMP_C:
            notes = f"Elevated temperature ({temperature_c}°C >= {cls.SUSPICIOUS_HIGH_TEMP_C}°C); QC passed with heat advisory caution."

        return "PASSED", notes, age_minutes
