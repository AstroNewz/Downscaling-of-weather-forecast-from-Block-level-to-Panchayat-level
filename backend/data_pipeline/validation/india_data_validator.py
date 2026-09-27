"""
India-Specific Data Validator
SIH Problem Statement 26074 — Agroweather-Downscaling

Extends the project's existing WeatherValidator with:
  - India geographic bounds check
  - Pilot AOI (Varanasi) bbox membership
  - UTC/IST timestamp consistency
  - Source type integrity (REANALYSIS != OBSERVATION)
  - Quality flag assignment: VALID / SUSPECT / MISSING / INVALID
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any

# India geographic bounds (approximate continental extent)
INDIA_LAT_MIN = 6.0
INDIA_LAT_MAX = 38.0
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 98.0

# Varanasi pilot AOI
PILOT_LAT_MIN = 25.10
PILOT_LAT_MAX = 25.60
PILOT_LON_MIN = 82.70
PILOT_LON_MAX = 83.20

IST_OFFSET = timedelta(hours=5, minutes=30)

# Physical limits (India-context; tighter than global extremes for QC flagging)
INDIA_TEMP_PLAUSIBLE_MIN = -10.0   # Coldest recorded in India: ~-45°C Dras but typical -10°C for plains
INDIA_TEMP_PLAUSIBLE_MAX = 52.0    # Indian record high ~51°C (Phalodi 2016)
INDIA_TEMP_SUSPECT_HIGH = 48.0     # Unusual for Varanasi but possible; flag SUSPECT
INDIA_PRECIP_DAILY_MAX = 1000.0    # Extreme event threshold (Cherrapunji style)
INDIA_WIND_MAX_MPS = 80.0          # Cyclone upper limit for inland
INDIA_HUMIDITY_MAX = 100.0

VALID_SOURCE_TYPES = {"OBSERVATION", "REANALYSIS", "NWP_FORECAST", "REMOTE_SENSING", "DERIVED"}
OBSERVATION_TYPES = {"OBSERVATION"}
REANALYSIS_TYPES = {"REANALYSIS"}


class ValidationResult:
    """Result of validating a single record."""
    def __init__(self):
        self.quality_flag: str = "VALID"
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.quality_flag = "INVALID"

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        if self.quality_flag == "VALID":
            self.quality_flag = "SUSPECT"

    def add_missing(self, field: str):
        self.warnings.append(f"Missing: {field}")
        if self.quality_flag == "VALID":
            self.quality_flag = "MISSING"

    @property
    def is_valid(self) -> bool:
        return self.quality_flag in ("VALID", "SUSPECT")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_flag": self.quality_flag,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class IndiaDataValidator:
    """
    Validates weather records for the India pilot pipeline.

    Design principles:
    - Raw data is NEVER modified
    - INVALID records are flagged but preserved
    - SUSPECT records are flagged but may be used with explicit configuration
    - NULL is always preferred over fabricated values for MISSING fields
    """

    @staticmethod
    def validate_india_bounds(lat: Optional[float], lon: Optional[float]) -> ValidationResult:
        """Checks that coordinates fall within India's geographic extent."""
        result = ValidationResult()
        if lat is None:
            result.add_missing("latitude")
            return result
        if lon is None:
            result.add_missing("longitude")
            return result

        if not (INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX):
            result.add_error(
                f"Latitude {lat}° is outside India bounds [{INDIA_LAT_MIN}, {INDIA_LAT_MAX}]"
            )
        if not (INDIA_LON_MIN <= lon <= INDIA_LON_MAX):
            result.add_error(
                f"Longitude {lon}° is outside India bounds [{INDIA_LON_MIN}, {INDIA_LON_MAX}]"
            )
        return result

    @staticmethod
    def validate_pilot_aoi(lat: Optional[float], lon: Optional[float]) -> bool:
        """Returns True if coordinates are within the Varanasi pilot bbox."""
        if lat is None or lon is None:
            return False
        return (
            PILOT_LAT_MIN <= lat <= PILOT_LAT_MAX
            and PILOT_LON_MIN <= lon <= PILOT_LON_MAX
        )

    @staticmethod
    def validate_temperature(temp_c: Optional[float], field_name: str = "temperature_2m_c") -> ValidationResult:
        result = ValidationResult()
        if temp_c is None:
            result.add_missing(field_name)
            return result
        if temp_c < -60.0 or temp_c > 65.0:
            result.add_error(f"{field_name}={temp_c}°C is outside physical limits [-60, 65]°C")
        elif temp_c < INDIA_TEMP_PLAUSIBLE_MIN or temp_c > INDIA_TEMP_PLAUSIBLE_MAX:
            result.add_warning(f"{field_name}={temp_c}°C is unusual for India — flagging SUSPECT")
        elif temp_c > INDIA_TEMP_SUSPECT_HIGH:
            result.add_warning(f"{field_name}={temp_c}°C is extreme for Varanasi — flagging SUSPECT")
        return result

    @staticmethod
    def validate_precipitation(precip_mm: Optional[float]) -> ValidationResult:
        result = ValidationResult()
        if precip_mm is None:
            result.add_missing("precipitation_mm")
            return result
        if precip_mm < 0.0:
            result.add_error(f"Precipitation cannot be negative: {precip_mm} mm")
        elif precip_mm > INDIA_PRECIP_DAILY_MAX:
            result.add_warning(f"Precipitation {precip_mm} mm/day is extreme — flagging SUSPECT")
        return result

    @staticmethod
    def validate_humidity(humidity_pct: Optional[float]) -> ValidationResult:
        result = ValidationResult()
        if humidity_pct is None:
            result.add_missing("relative_humidity_pct")
            return result
        if not (0.0 <= humidity_pct <= INDIA_HUMIDITY_MAX):
            result.add_error(f"Humidity {humidity_pct}% is outside [0, 100]%")
        return result

    @staticmethod
    def validate_wind(
        wind_speed_mps: Optional[float],
        wind_dir_deg: Optional[float] = None,
    ) -> ValidationResult:
        result = ValidationResult()
        if wind_speed_mps is None:
            result.add_missing("wind_speed")
            return result
        if wind_speed_mps < 0.0:
            result.add_error(f"Wind speed cannot be negative: {wind_speed_mps} m/s")
        elif wind_speed_mps > INDIA_WIND_MAX_MPS:
            result.add_error(f"Wind speed {wind_speed_mps} m/s exceeds physical maximum for India")
        if wind_dir_deg is not None and not (0.0 <= wind_dir_deg <= 360.0):
            result.add_error(f"Wind direction {wind_dir_deg}° is outside [0, 360]°")
        return result

    @staticmethod
    def validate_timestamp(
        timestamp_utc: Optional[datetime],
        timestamp_ist: Optional[datetime] = None,
    ) -> ValidationResult:
        """Validates timestamp validity and UTC/IST consistency."""
        result = ValidationResult()
        if timestamp_utc is None:
            result.add_error("timestamp_utc is required")
            return result

        # Ensure UTC awareness
        if timestamp_utc.tzinfo is None:
            result.add_warning("timestamp_utc has no timezone — assuming UTC")

        # Future timestamp check
        now_utc = datetime.now(timezone.utc)
        ts_utc = timestamp_utc.replace(tzinfo=timezone.utc) if timestamp_utc.tzinfo is None else timestamp_utc
        if ts_utc > now_utc:
            result.add_warning(f"Timestamp {timestamp_utc} is in the future — flagging SUSPECT")

        # IST consistency check
        if timestamp_ist is not None:
            expected_ist = ts_utc + IST_OFFSET
            # Normalise comparison: if timestamp_ist is naive, strip expected_ist tzinfo
            # so arithmetic does not raise TypeError; if aware, compare in UTC.
            if timestamp_ist.tzinfo is None:
                _expected = expected_ist.replace(tzinfo=None)
                diff = abs((timestamp_ist - _expected).total_seconds())
            else:
                diff = abs((timestamp_ist - expected_ist).total_seconds())
            if diff > 60:  # More than 1 minute offset
                result.add_error(
                    f"IST/UTC inconsistency: expected IST={expected_ist.isoformat()}, "
                    f"got IST={timestamp_ist.isoformat()} (diff={diff:.0f}s)"
                )
        return result

    @staticmethod
    def validate_source_type_integrity(
        source_type_coarse: str,
        source_name_coarse: str,
        source_type_reference: str,
        source_name_reference: str,
    ) -> ValidationResult:
        """
        Checks that the same source dataset is NOT used as both the coarse
        input and the independent reference (leakage prevention).

        CRITICAL RULE (Requirement 6):
          target = reference_temp - coarse_temp
          source_name_coarse MUST NOT == source_name_reference
        """
        result = ValidationResult()
        if source_name_coarse == source_name_reference:
            result.add_error(
                f"TARGET LEAKAGE DETECTED: The same source '{source_name_coarse}' "
                f"is used as both the coarse input and the reference temperature. "
                f"This would make target = 0 and constitutes data leakage. "
                f"Use different datasets for X (coarse) and Y (reference)."
            )
        # Warn if reference is REANALYSIS (it can be used but must be labelled)
        if source_type_reference in REANALYSIS_TYPES and source_type_coarse in REANALYSIS_TYPES:
            result.add_warning(
                f"Both coarse ({source_name_coarse}) and reference ({source_name_reference}) "
                f"are REANALYSIS. This is valid only if they are DIFFERENT datasets "
                f"(e.g., ERA5 coarse vs ERA5-Land reference). "
                f"Label all reports as 'REANALYSIS-to-REANALYSIS' — not 'station validation'."
            )
        return result

    @classmethod
    def validate_record(cls, record: Dict[str, Any]) -> ValidationResult:
        """
        Full validation of a single weather record dictionary.
        Returns a merged ValidationResult.
        """
        merged = ValidationResult()

        def merge(r: ValidationResult):
            merged.errors.extend(r.errors)
            merged.warnings.extend(r.warnings)
            if r.quality_flag == "INVALID":
                merged.quality_flag = "INVALID"
            elif r.quality_flag == "SUSPECT" and merged.quality_flag == "VALID":
                merged.quality_flag = "SUSPECT"
            elif r.quality_flag == "MISSING" and merged.quality_flag == "VALID":
                merged.quality_flag = "MISSING"

        merge(cls.validate_india_bounds(record.get("latitude"), record.get("longitude")))
        merge(cls.validate_temperature(record.get("temperature_2m_c")))
        merge(cls.validate_precipitation(record.get("precipitation_mm")))
        merge(cls.validate_humidity(record.get("relative_humidity_pct")))
        merge(cls.validate_wind(
            record.get("wind_speed_mps"),
            record.get("wind_direction_deg"),
        ))
        merge(cls.validate_timestamp(
            record.get("timestamp_utc"),
            record.get("timestamp_ist"),
        ))

        # Source type required
        if not record.get("source_type"):
            merged.add_error("source_type is required and must be one of: " + str(VALID_SOURCE_TYPES))
        elif record["source_type"] not in VALID_SOURCE_TYPES:
            merged.add_error(f"Invalid source_type: {record['source_type']}")

        if not record.get("source_id"):
            merged.add_error("source_id is required for provenance tracking")

        # Check: is this record in the pilot AOI?
        in_aoi = cls.validate_pilot_aoi(record.get("latitude"), record.get("longitude"))
        if not in_aoi and record.get("latitude") and record.get("longitude"):
            merged.add_warning(
                f"Record at ({record.get('latitude')}, {record.get('longitude')}) "
                f"is outside the Varanasi pilot AOI bbox. Not rejected, but verify scope."
            )

        return merged
