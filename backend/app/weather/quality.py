from typing import List, Tuple
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
