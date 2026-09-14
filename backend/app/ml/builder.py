import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from app.db.models.weather import BlockWeatherForecast, WeatherObservation
from app.db.models.spatial import Block
from app.ml.schemas import (
    DatasetBuildConfig,
    DatasetQualityReport,
    EngineeredFeatureRecord,
    BaselineMetrics,
    FEATURE_SCHEMA_VERSION,
)
from app.ml.temporal import TemporalAligner
from app.ml.spatial import SpatialAligner
from app.ml.features import FeatureEngineer
from app.ml.splitting import TimeSeriesSplitter
from app.ml.baseline import BaselineEvaluator
from app.gis.feature_service import GISEnvironmentalFeatureService
from app.core.logging import logger


class WeatherTrainingDatasetBuilder:
    """
    Orchestration service for building reproducible, leakage-free coarse-to-fine downscaling datasets.
    Enriched with Phase 5 GIS, DEM, and Land-Cover environmental predictors.
    """

    def __init__(self, db: Session):
        self.db = db

    def build_dataset(self, config: Optional[DatasetBuildConfig] = None) -> DatasetQualityReport:
        """
        Executes end-to-end dataset construction pipeline.
        """
        config = config or DatasetBuildConfig()
        logger.info(f"Starting weather dataset build for version [{config.dataset_version}] (Schema: {FEATURE_SCHEMA_VERSION})...")

        report = DatasetQualityReport(
            dataset_version=config.dataset_version,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            config=config,
        )

        gis_service = GISEnvironmentalFeatureService(db=self.db, dem_raster_path=config.dem_raster_path)

        # 1. Query candidate observations
        obs_stmt = select(WeatherObservation)
        obs_conds = []
        if config.start_time:
            obs_conds.append(WeatherObservation.observation_time >= config.start_time)
        if config.end_time:
            obs_conds.append(WeatherObservation.observation_time <= config.end_time)
        if config.exclude_suspicious:
            obs_conds.append(WeatherObservation.quality_flag == "VALID")
        else:
            obs_conds.append(WeatherObservation.quality_flag.in_(["VALID", "SUSPICIOUS"]))

        if obs_conds:
            obs_stmt = obs_stmt.where(and_(*obs_conds))

        observations = self.db.scalars(obs_stmt.order_by(WeatherObservation.observation_time)).all()
        report.observation_records_considered = len(observations)

        # 2. Query candidate block forecasts
        fc_stmt = select(BlockWeatherForecast)
        fc_conds = []
        if config.source_model:
            fc_conds.append(BlockWeatherForecast.source_model == config.source_model)
        if config.exclude_suspicious:
            fc_conds.append(BlockWeatherForecast.quality_flag == "VALID")
        else:
            fc_conds.append(BlockWeatherForecast.quality_flag.in_(["VALID", "SUSPICIOUS"]))

        if fc_conds:
            fc_stmt = fc_stmt.where(and_(*fc_conds))

        forecasts = self.db.scalars(fc_stmt).all()
        report.forecast_records_considered = len(forecasts)

        if not observations or not forecasts:
            report.status = "EMPTY"
            report.details = "Insufficient database records to construct training dataset."
            logger.warning(f"Dataset build aborted: Obs={len(observations)}, Forecasts={len(forecasts)}")
            return report

        # Pre-index forecasts by block_id for fast lookup
        forecasts_by_block: Dict[int, List[BlockWeatherForecast]] = {}
        for fc in forecasts:
            forecasts_by_block.setdefault(fc.block_id, []).append(fc)

        # Pre-cache blocks
        all_blocks = {b.id: b for b in self.db.scalars(select(Block)).all()}

        matched_feature_records: List[EngineeredFeatureRecord] = []
        seen_sample_keys = set()
        exclusion_reasons: Dict[str, int] = {}
        missing_features: Dict[str, int] = {}

        # 3. Align observations with forecasts
        for obs in observations:
            # Check target availability
            if obs.temp_celsius is None and obs.temp_max is None and obs.temp_min is None:
                exclusion_reasons["MISSING_TARGET"] = exclusion_reasons.get("MISSING_TARGET", 0) + 1
                report.excluded_samples += 1
                continue

            # Identify candidate block
            candidate_block: Optional[Block] = None
            if obs.block_id and obs.block_id in all_blocks:
                candidate_block = all_blocks[obs.block_id]
            elif all_blocks:
                candidate_block = next(iter(all_blocks.values()), None)

            if not candidate_block:
                exclusion_reasons["SPATIAL_MISMATCH"] = exclusion_reasons.get("SPATIAL_MISMATCH", 0) + 1
                report.excluded_samples += 1
                continue

            # Evaluate spatial match
            sp_valid, spatial_data, sp_reason = SpatialAligner.evaluate_spatial_match(obs, candidate_block)
            if not sp_valid:
                reason_key = sp_reason.split(":")[0] if sp_reason else "SPATIAL_MISMATCH"
                exclusion_reasons[reason_key] = exclusion_reasons.get(reason_key, 0) + 1
                report.excluded_samples += 1
                continue
            report.spatially_matched += 1

            candidate_forecasts = forecasts_by_block.get(candidate_block.id, [])
            best_match: Optional[Tuple[BlockWeatherForecast, float, float]] = None
            min_time_diff = float("inf")

            for fc in candidate_forecasts:
                t_valid, time_diff, lead_hours, t_reason = TemporalAligner.evaluate_temporal_match(
                    obs, fc, config.temporal_tolerance_minutes
                )
                if t_valid and time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_match = (fc, lead_hours, time_diff)

            if not best_match:
                exclusion_reasons["TIME_MISMATCH"] = exclusion_reasons.get("TIME_MISMATCH", 0) + 1
                report.excluded_samples += 1
                continue

            report.temporally_matched += 1
            fc_matched, lead_hrs, t_diff = best_match

            # Deduplication key: (station_id, block_id, observation_time, forecast_issue_time)
            sample_key = (obs.station_id, fc_matched.block_id, obs.observation_time, fc_matched.issue_time)
            if sample_key in seen_sample_keys:
                exclusion_reasons["DUPLICATE_SAMPLE"] = exclusion_reasons.get("DUPLICATE_SAMPLE", 0) + 1
                report.duplicate_samples += 1
                report.excluded_samples += 1
                continue
            seen_sample_keys.add(sample_key)

            # Extract Environmental & GIS Features (Phase 5)
            env_features = gis_service.get_features_for_location(
                latitude=obs.latitude,
                longitude=obs.longitude,
                block_id=fc_matched.block_id
            )

            # Build feature record
            feature_rec = FeatureEngineer.build_feature_record(
                obs=obs,
                forecast=fc_matched,
                lead_hours=lead_hrs,
                time_diff_min=t_diff,
                spatial_data=spatial_data,
                environmental_features=env_features,
                dataset_version=config.dataset_version,
            )

            if not feature_rec:
                exclusion_reasons["TARGET_CALCULATION_FAILED"] = exclusion_reasons.get("TARGET_CALCULATION_FAILED", 0) + 1
                report.excluded_samples += 1
                continue

            if obs.quality_flag == "SUSPICIOUS" or fc_matched.quality_flag == "SUSPICIOUS":
                report.suspicious_samples += 1
            else:
                report.valid_samples += 1

            matched_feature_records.append(feature_rec)

        if not matched_feature_records:
            report.status = "NO_MATCHES"
            report.exclusion_reasons = exclusion_reasons
            report.details = "No observation-forecast pairs met alignment and quality thresholds."
            return report

        # 4. Chronological Train / Val / Test Partitioning
        partitioned_records = TimeSeriesSplitter.split_chronologically(
            records=matched_feature_records,
            train_ratio=config.train_ratio,
            validation_ratio=config.validation_ratio,
            test_ratio=config.test_ratio
        )

        train_set = [r for r in partitioned_records if r.split == "train"]
        val_set = [r for r in partitioned_records if r.split == "val"]
        test_set = [r for r in partitioned_records if r.split == "test"]

        report.train_samples = len(train_set)
        report.validation_samples = len(val_set)
        report.test_samples = len(test_set)

        # 5. Evaluate Coarse Forecast Baselines
        report.overall_baseline = BaselineEvaluator.calculate_metrics(partitioned_records)
        report.train_baseline = BaselineEvaluator.calculate_metrics(train_set)
        report.validation_baseline = BaselineEvaluator.calculate_metrics(val_set)
        report.test_baseline = BaselineEvaluator.calculate_metrics(test_set)

        # 6. Metadata summary
        obs_times = [r.observation_time for r in partitioned_records]
        fc_times = [r.forecast_valid_time for r in partitioned_records]
        report.min_observation_time = min(obs_times)
        report.max_observation_time = max(obs_times)
        report.min_forecast_time = min(fc_times)
        report.max_forecast_time = max(fc_times)
        report.exclusion_reasons = exclusion_reasons

        # 7. Export Parquet & JSON Artifacts (if not dry run)
        if not config.dry_run:
            os.makedirs(config.output_dir, exist_ok=True)
            df = pd.DataFrame([r.model_dump() for r in partitioned_records])

            parquet_filename = f"weather_downscale_{config.dataset_version}.parquet"
            parquet_filepath = os.path.join(config.output_dir, parquet_filename)
            try:
                df.to_parquet(parquet_filepath, index=False)
                report.parquet_path = parquet_filepath
                logger.info(f"Parquet dataset saved: {parquet_filepath}")
            except Exception as e:
                csv_filename = f"weather_downscale_{config.dataset_version}.csv"
                csv_filepath = os.path.join(config.output_dir, csv_filename)
                df.to_csv(csv_filepath, index=False)
                report.parquet_path = csv_filepath
                logger.warning(f"Parquet export failed ({e}); exported CSV fallback to {csv_filepath}")

            report_filename = f"weather_downscale_{config.dataset_version}_report.json"
            report_filepath = os.path.join(config.output_dir, report_filename)
            with open(report_filepath, "w", encoding="utf-8") as rf:
                rf.write(report.model_dump_json(indent=2))
            report.report_path = report_filepath

        report.status = "SUCCESS"
        report.details = (
            f"Successfully built dataset [{config.dataset_version}] (Schema: {FEATURE_SCHEMA_VERSION}) with "
            f"{len(partitioned_records)} aligned samples (Train={report.train_samples}, Val={report.validation_samples}, Test={report.test_samples}). "
            f"Baseline MAE: {report.overall_baseline.mae_celsius}°C, RMSE: {report.overall_baseline.rmse_celsius}°C."
        )

        logger.info(report.details)
        return report
