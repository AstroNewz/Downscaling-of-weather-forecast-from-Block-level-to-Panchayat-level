import hashlib
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from app.weather.providers.base import WeatherProvider
from app.weather.providers.csv_provider import CSVWeatherProvider
from app.weather.normalization import WeatherNormalizer
from app.weather.quality import WeatherQualityControl
from app.weather.schemas import (
    ParsedWeatherRecord,
    NormalizedWeatherRecord,
    QualityFlag,
    IngestionSummary,
    ValidationErrorDetail,
)
from app.repositories.weather_repository import WeatherRepository
from app.db.models.weather import BlockWeatherForecast, WeatherObservation
from app.core.logging import logger


class WeatherIngestionService:
    """
    Central orchestration service for weather data ingestion.
    Executes: Provider -> Raw Archive -> Normalization -> Quality Control -> Deduplication -> Persistence -> Report.
    """

    def __init__(self, db: Session, default_provider: Optional[WeatherProvider] = None):
        self.db = db
        self.repository = WeatherRepository(db)
        self.default_provider = default_provider or CSVWeatherProvider()

    @staticmethod
    def compute_payload_checksum(data: Any) -> str:
        """Calculates a SHA256 hash of raw input data."""
        if isinstance(data, (bytes, bytearray)):
            return hashlib.sha256(data).hexdigest()
        elif isinstance(data, str):
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        else:
            return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    def ingest(
        self,
        source_data: Any,
        provider: Optional[WeatherProvider] = None,
        source_file_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> IngestionSummary:
        """
        Executes end-to-end ingestion pipeline.
        """
        active_provider = provider or self.default_provider
        options = options or {}
        source_label = options.get("source", active_provider.name)
        checksum = self.compute_payload_checksum(source_data)

        logger.info(f"Initiating weather ingestion via [{active_provider.name}], source: '{source_label}', dry_run: {dry_run}")

        summary = IngestionSummary(
            source=source_label,
            source_file=source_file_name,
            ingested_at=datetime.utcnow(),
        )

        unit_conversions: Dict[str, int] = {}
        missing_values: Dict[str, int] = {
            "temp_min": 0,
            "temp_max": 0,
            "rainfall": 0,
            "humidity": 0,
            "wind_speed": 0,
            "wind_direction": 0,
            "cloud_cover": 0,
        }

        # 1. Parse raw data with provider
        try:
            parsed_records: List[ParsedWeatherRecord] = active_provider.parse(source_data, options)
        except Exception as exc:
            logger.error(f"Weather parsing error with provider [{active_provider.name}]: {exc}", exc_info=True)
            summary.status = "FAILED"
            summary.details = f"Parsing failed: {str(exc)}"
            return summary

        summary.records_read = len(parsed_records)
        if summary.records_read == 0:
            summary.status = "EMPTY"
            summary.details = "No data records found in input source."
            return summary

        # 2. Store raw payload in raw_weather_records for audit provenance (if not dry-run)
        if not dry_run:
            raw_payload_sample = [r.raw_payload for r in parsed_records[:100]]  # sample top 100 in payload
            raw_record = self.repository.insert_raw_record(
                source=source_label,
                source_file=source_file_name,
                checksum=checksum,
                raw_payload={"sample_records": raw_payload_sample, "total_count": len(parsed_records)},
                records_count=len(parsed_records),
                processing_status="PROCESSING"
            )
            summary.ingestion_id = raw_record.id

        forecasts_to_insert: List[BlockWeatherForecast] = []
        observations_to_insert: List[WeatherObservation] = []

        # 3. Normalize & Quality-Check each record
        for parsed in parsed_records:
            # Track missing value counts
            if parsed.temp_min_raw is None:
                missing_values["temp_min"] += 1
            if parsed.temp_max_raw is None:
                missing_values["temp_max"] += 1
            if parsed.rainfall_raw is None:
                missing_values["rainfall"] += 1
            if parsed.humidity_raw is None:
                missing_values["humidity"] += 1
            if parsed.wind_speed_raw is None:
                missing_values["wind_speed"] += 1
            if parsed.wind_direction_raw is None:
                missing_values["wind_direction"] += 1
            if parsed.cloud_cover_raw is None:
                missing_values["cloud_cover"] += 1

            # Normalization
            normalized = WeatherNormalizer.normalize_record(parsed, unit_conversions)

            # Quality classification
            evaluated = WeatherQualityControl.evaluate(normalized)

            if evaluated.quality_flag == QualityFlag.INVALID:
                summary.records_invalid += 1
                summary.records_skipped += 1
                summary.validation_errors.extend(evaluated.validation_errors)
                continue
            elif evaluated.quality_flag == QualityFlag.SUSPICIOUS:
                summary.records_suspicious += 1
                summary.records_valid += 1
            else:
                summary.records_valid += 1

            # 4. Resolve entity and deduplicate
            if evaluated.station_identifier and (evaluated.latitude is not None and evaluated.longitude is not None):
                # AWS Ground Observation routing
                existing_obs = self.repository.find_existing_observation(
                    station_id=evaluated.station_identifier,
                    observation_time=evaluated.valid_time,
                    source=evaluated.source
                )
                if existing_obs:
                    summary.duplicate_records += 1
                    summary.records_skipped += 1
                    continue

                # Prepare WeatherObservation entity
                obs = WeatherObservation(
                    station_id=evaluated.station_identifier,
                    station_name=evaluated.station_identifier,
                    latitude=evaluated.latitude,
                    longitude=evaluated.longitude,
                    observation_time=evaluated.valid_time,
                    temp_min=evaluated.temp_min_celsius,
                    temp_max=evaluated.temp_max_celsius,
                    rainfall_mm=evaluated.rainfall_mm,
                    relative_humidity_pct=evaluated.relative_humidity_pct,
                    wind_speed_mps=evaluated.wind_speed_mps,
                    wind_direction_deg=evaluated.wind_direction_deg,
                    cloud_cover_pct=evaluated.cloud_cover_pct,
                    quality_flag=evaluated.quality_flag.value,
                    quality_notes=evaluated.quality_notes,
                    source=evaluated.source,
                )
                observations_to_insert.append(obs)

            else:
                # Block NWP Forecast routing
                block_id_val = evaluated.block_identifier or "DEFAULT_BLOCK"
                block = self.repository.get_or_create_block_placeholder(block_id_val)

                # Deduplication check: (block_id, forecast_date, issue_time, source_model)
                existing_forecast = self.repository.find_existing_forecast(
                    block_id=block.id,
                    forecast_date=evaluated.valid_time,
                    issue_time=evaluated.forecast_generated_at,
                    source_model=evaluated.model_name
                )
                if existing_forecast:
                    summary.duplicate_records += 1
                    summary.records_skipped += 1
                    continue

                forecast = BlockWeatherForecast(
                    block_id=block.id,
                    forecast_date=evaluated.valid_time,
                    issue_time=evaluated.forecast_generated_at,
                    temp_min=evaluated.temp_min_celsius,
                    temp_max=evaluated.temp_max_celsius,
                    rainfall_mm=evaluated.rainfall_mm,
                    relative_humidity_pct=evaluated.relative_humidity_pct,
                    wind_speed_kmh=evaluated.wind_speed_kmh,
                    wind_speed_mps=evaluated.wind_speed_mps,
                    wind_direction_deg=evaluated.wind_direction_deg,
                    cloud_cover_pct=evaluated.cloud_cover_pct,
                    quality_flag=evaluated.quality_flag.value,
                    quality_notes=evaluated.quality_notes,
                    source_model=evaluated.model_name,
                    raw_resolution_km=12.0,
                )
                forecasts_to_insert.append(forecast)

        # 5. Persist to PostgreSQL (if not dry-run)
        if not dry_run:
            inserted_fc_count = self.repository.bulk_insert_forecasts(forecasts_to_insert)
            inserted_obs_count = self.repository.bulk_insert_observations(observations_to_insert)
            summary.records_inserted = inserted_fc_count + inserted_obs_count
        else:
            summary.records_inserted = len(forecasts_to_insert) + len(observations_to_insert)

        summary.missing_value_counts = missing_values
        summary.unit_conversions = unit_conversions
        summary.status = "SUCCESS"
        summary.details = (
            f"Successfully processed {summary.records_read} records: "
            f"{summary.records_inserted} inserted, {summary.duplicate_records} duplicates skipped, "
            f"{summary.records_invalid} invalid."
        )

        logger.info(
            f"Weather ingestion complete: Read={summary.records_read}, Inserted={summary.records_inserted}, "
            f"Suspicious={summary.records_suspicious}, Invalid={summary.records_invalid}, Duplicates={summary.duplicate_records}"
        )
        return summary
