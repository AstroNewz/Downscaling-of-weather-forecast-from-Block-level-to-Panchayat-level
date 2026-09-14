import csv
import io
import os
from typing import List, Any, Dict, Optional, Union
from app.weather.providers.base import WeatherProvider
from app.weather.schemas import ParsedWeatherRecord
from app.core.logging import logger


class CSVWeatherProvider(WeatherProvider):
    """
    CSV / TSV Weather Provider for tabular forecast and observation files.
    Extracts structured meteorological records from local files or in-memory text streams.
    """

    # Flexible column mapping aliases
    COLUMN_ALIASES = {
        "block": ["block", "block_id", "block_name", "block_code", "lgd_code"],
        "station": ["station", "station_id", "station_name", "aws_id"],
        "latitude": ["latitude", "lat", "lat_deg"],
        "longitude": ["longitude", "lon", "long", "lon_deg"],
        "forecast_generated_at": ["forecast_generated_at", "issue_time", "run_time", "init_time", "generated_at"],
        "valid_time": ["valid_time", "forecast_date", "valid_date", "target_date", "datetime", "date"],
        "temp_min": ["temp_min", "temperature_min", "tmin", "min_temp", "minimum_temperature"],
        "temp_max": ["temp_max", "temperature_max", "tmax", "max_temp", "maximum_temperature"],
        "rainfall": ["rainfall", "rainfall_mm", "precipitation", "precip", "rain", "rain_mm", "prcp"],
        "humidity": ["humidity", "relative_humidity", "rh", "relative_humidity_pct", "rh_pct"],
        "wind_speed": ["wind_speed", "wind_speed_kmh", "wind_speed_mps", "wspd", "wind_spd", "wind"],
        "wind_direction": ["wind_direction", "wind_direction_deg", "wdir", "wind_dir", "dir"],
        "cloud_cover": ["cloud_cover", "cloud_cover_pct", "cloud", "tcdc", "total_cloud_cover"],
        "temp_unit": ["temp_unit", "temperature_unit", "unit_temp"],
        "rain_unit": ["rain_unit", "rainfall_unit", "unit_rain", "precip_unit"],
        "wind_speed_unit": ["wind_speed_unit", "unit_wind", "wind_unit"],
        "source": ["source", "source_name", "data_source"],
        "model_name": ["model_name", "model", "nwp_model", "source_model"],
    }

    @property
    def name(self) -> str:
        return "CSV_PROVIDER"

    @property
    def supported_formats(self) -> List[str]:
        return ["csv", "tsv", "txt"]

    def _resolve_column(self, header: List[str], field_key: str) -> Optional[str]:
        """Finds matching column name from aliases in a case-insensitive manner."""
        aliases = self.COLUMN_ALIASES.get(field_key, [field_key])
        header_lower_map = {col.strip().lower(): col for col in header}
        for alias in aliases:
            if alias.lower() in header_lower_map:
                return header_lower_map[alias.lower()]
        return None

    def parse(
        self,
        source_data: Union[str, bytes, io.IOBase],
        options: Optional[Dict[str, Any]] = None
    ) -> List[ParsedWeatherRecord]:
        options = options or {}
        default_source = options.get("source", "CSV_UPLOAD")
        default_model = options.get("model_name", "IMD-GFS")
        default_temp_unit = options.get("temp_unit", "C")
        default_rain_unit = options.get("rain_unit", "mm")
        default_wind_unit = options.get("wind_speed_unit", "km/h")

        # Prepare text stream
        if isinstance(source_data, str) and os.path.exists(source_data):
            with open(source_data, mode="r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        elif isinstance(source_data, str):
            content = source_data
        elif isinstance(source_data, bytes):
            content = source_data.decode("utf-8-sig", errors="replace")
        elif hasattr(source_data, "read"):
            raw_content = source_data.read()
            content = raw_content.decode("utf-8-sig", errors="replace") if isinstance(raw_content, bytes) else raw_content
        else:
            raise ValueError(f"Unsupported source data type for CSVWeatherProvider: {type(source_data)}")

        # Filter out full comment lines starting with '#'
        lines = [line for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        if not lines:
            logger.warning("CSV data contains no valid data lines.")
            return []

        # Detect delimiter (comma or tab or semicolon)
        sample = lines[0]
        delimiter = "\t" if "\t" in sample and "," not in sample else (";" if ";" in sample and "," not in sample else ",")
        if "delimiter" in options:
            delimiter = options["delimiter"]

        reader = csv.DictReader(lines, delimiter=delimiter)
        if not reader.fieldnames:
            logger.warning("CSV headers could not be determined.")
            return []

        fieldnames = [f.strip() for f in reader.fieldnames if f]
        col_map = {key: self._resolve_column(fieldnames, key) for key in self.COLUMN_ALIASES.keys()}

        valid_time_col = col_map["valid_time"]
        if not valid_time_col:
            raise ValueError("CSV is missing mandatory forecast date/valid_time column.")

        parsed_records: List[ParsedWeatherRecord] = []

        for row_idx, row in enumerate(reader, start=1):
            raw_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items() if k}

            valid_time_val = raw_row.get(valid_time_col)
            if not valid_time_val:
                # Skip empty lines
                continue

            def get_val(key: str) -> Optional[Any]:
                col_name = col_map.get(key)
                if col_name and col_name in raw_row:
                    val = raw_row[col_name]
                    if val is None or val == "" or str(val).strip().lower() in ["nan", "null", "none", "na", "-999", "-999.0"]:
                        return None
                    return val
                return None

            record = ParsedWeatherRecord(
                row_number=row_idx,
                block_identifier=get_val("block"),
                station_identifier=get_val("station"),
                latitude=get_val("latitude"),
                longitude=get_val("longitude"),
                forecast_generated_at_raw=get_val("forecast_generated_at"),
                valid_time_raw=valid_time_val,
                temp_min_raw=get_val("temp_min"),
                temp_max_raw=get_val("temp_max"),
                rainfall_raw=get_val("rainfall"),
                humidity_raw=get_val("humidity"),
                wind_speed_raw=get_val("wind_speed"),
                wind_direction_raw=get_val("wind_direction"),
                cloud_cover_raw=get_val("cloud_cover"),
                temp_unit=str(get_val("temp_unit") or default_temp_unit).upper(),
                rain_unit=str(get_val("rain_unit") or default_rain_unit).lower(),
                wind_speed_unit=str(get_val("wind_speed_unit") or default_wind_unit).lower(),
                source=str(get_val("source") or default_source),
                model_name=str(get_val("model_name") or default_model),
                raw_payload=raw_row,
            )
            parsed_records.append(record)

        logger.info(f"CSVWeatherProvider successfully parsed {len(parsed_records)} rows.")
        return parsed_records
