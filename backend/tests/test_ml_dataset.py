import pytest
from datetime import datetime, timezone, timedelta
from app.db.models.weather import BlockWeatherForecast, WeatherObservation
from app.db.models.spatial import Block
from app.ml.temporal import TemporalAligner
from app.ml.spatial import SpatialAligner
from app.ml.features import FeatureEngineer
from app.ml.splitting import TimeSeriesSplitter
from app.ml.baseline import BaselineEvaluator
from app.ml.schemas import EngineeredFeatureRecord


def test_temporal_alignment_valid():
    """Verifies that observation and forecast within tolerance are successfully matched."""
    obs_time = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)
    fc_valid = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)
    fc_issue = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)

    obs = WeatherObservation(
        station_id="AWS_01",
        latitude=25.3,
        longitude=82.9,
        observation_time=obs_time,
        temp_celsius=28.0
    )
    fc = BlockWeatherForecast(
        block_id=1,
        forecast_date=fc_valid,
        issue_time=fc_issue,
        temp_min=22.0,
        temp_max=32.0,
        source_model="IMD-GFS"
    )

    is_match, time_diff, lead_hours, reason = TemporalAligner.evaluate_temporal_match(
        obs=obs, forecast=fc, tolerance_minutes=180
    )
    assert is_match is True
    assert time_diff == 0.0
    assert lead_hours == 6.0
    assert reason is None


def test_temporal_alignment_leakage_prevention():
    """Verifies that forecasts issued AFTER observation time are strictly rejected to prevent leakage."""
    obs_time = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)
    # Forecast issued at 12:00 UTC (after observation at 06:00 UTC)
    fc_issue_future = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    fc_valid = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)

    obs = WeatherObservation(
        station_id="AWS_01",
        latitude=25.3,
        longitude=82.9,
        observation_time=obs_time,
        temp_celsius=28.0
    )
    fc = BlockWeatherForecast(
        block_id=1,
        forecast_date=fc_valid,
        issue_time=fc_issue_future,
        source_model="IMD-GFS"
    )

    is_match, _, _, reason = TemporalAligner.evaluate_temporal_match(obs=obs, forecast=fc)
    assert is_match is False
    assert "LEAKAGE_DETECTED" in reason


def test_temporal_alignment_exceeds_tolerance():
    """Verifies that excessive time difference between observation and forecast is rejected."""
    obs_time = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    fc_valid = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)  # 12 hours difference (720 min)
    fc_issue = datetime(2026, 9, 14, 18, 0, tzinfo=timezone.utc)

    obs = WeatherObservation(station_id="AWS_01", latitude=25.3, longitude=82.9, observation_time=obs_time)
    fc = BlockWeatherForecast(block_id=1, forecast_date=fc_valid, issue_time=fc_issue)

    is_match, time_diff, _, reason = TemporalAligner.evaluate_temporal_match(
        obs=obs, forecast=fc, tolerance_minutes=180
    )
    assert is_match is False
    assert time_diff == 720.0
    assert "TIME_MISMATCH" in reason


def test_spatial_alignment_and_distance():
    """Verifies coordinate validation and geodesic Haversine distance calculation."""
    # Haversine distance between Varanasi (25.3176, 82.9739) and Babatpur Airport (25.4520, 82.8590) ~ 19.0 km
    dist = SpatialAligner.haversine_distance_km(25.3176, 82.9739, 25.4520, 82.8590)
    assert 17.0 <= dist <= 21.0

    # Invalid coordinates check
    obs_invalid = WeatherObservation(
        station_id="AWS_BAD",
        latitude=120.0,
        longitude=82.9,
        observation_time=datetime.utcnow()
    )
    block = Block(id=1, lgd_code="B1", name="Test Block", district_name="D1", state_name="S1")
    is_sp_match, _, reason = SpatialAligner.evaluate_spatial_match(obs_invalid, block)
    assert is_sp_match is False
    assert "INVALID_COORDINATES" in reason


def test_cyclical_and_residual_features():
    """Verifies cyclical feature generation and residual target calculation."""
    dt = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)
    cyclical = FeatureEngineer.compute_cyclical_features(dt)
    assert -1.0 <= cyclical["sin_hour"] <= 1.0
    assert -1.0 <= cyclical["cos_hour"] <= 1.0
    assert -1.0 <= cyclical["sin_day_of_year"] <= 1.0
    assert -1.0 <= cyclical["cos_day_of_year"] <= 1.0

    # Residual target: observed = 28.5°C, coarse forecast mean = 25.0°C (from 20°C min, 30°C max)
    # residual = 28.5 - 25.0 = 3.5°C
    obs = WeatherObservation(
        station_id="AWS_01",
        latitude=25.3,
        longitude=82.9,
        observation_time=dt,
        temp_celsius=28.5
    )
    fc = BlockWeatherForecast(
        block_id=1,
        forecast_date=dt,
        issue_time=dt - timedelta(hours=6),
        temp_min=20.0,
        temp_max=30.0,
        rainfall_mm=0.0,
        relative_humidity_pct=60.0,
        wind_speed_mps=5.0,
        source_model="IMD-GFS"
    )

    feat_rec = FeatureEngineer.build_feature_record(
        obs=obs,
        forecast=fc,
        lead_hours=6.0,
        time_diff_min=0.0,
        spatial_data={"obs_latitude": 25.3, "obs_longitude": 82.9}
    )

    assert feat_rec is not None
    assert feat_rec.observed_temp_c == 28.5
    assert feat_rec.coarse_forecast_temp_c == 25.0
    assert feat_rec.temperature_residual_c == 3.5


def test_chronological_time_series_splitting():
    """Verifies that time-series records are split strictly chronologically without future leakage."""
    base_time = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(10):
        t = base_time + timedelta(days=i)
        rec = EngineeredFeatureRecord(
            sample_id=f"S_{i}",
            station_id="AWS_01",
            block_id=1,
            observation_time=t,
            forecast_valid_time=t,
            forecast_issue_time=t - timedelta(hours=12),
            source_model="IMD-GFS",
            forecast_lead_hours=12.0,
            time_diff_minutes=0.0,
            hour_of_day=0,
            sin_hour=0.0,
            cos_hour=1.0,
            day_of_year=t.timetuple().tm_yday,
            sin_day_of_year=0.0,
            cos_day_of_year=1.0,
            month=9,
            sin_month=0.0,
            cos_month=1.0,
            obs_latitude=25.3,
            obs_longitude=82.9,
            observed_temp_c=25.0 + i,
            coarse_forecast_temp_c=25.0,
            temperature_residual_c=float(i),
        )
        records.append(rec)

    # 70% Train (7 samples: days 0-6), 15% Val (1 sample: day 7), 15% Test (2 samples: days 8-9)
    split_records = TimeSeriesSplitter.split_chronologically(
        records=records, train_ratio=0.70, validation_ratio=0.15, test_ratio=0.15
    )

    train_recs = [r for r in split_records if r.split == "train"]
    val_recs = [r for r in split_records if r.split == "val"]
    test_recs = [r for r in split_records if r.split == "test"]

    assert len(train_recs) == 7
    assert len(val_recs) == 1
    assert len(test_recs) == 2

    # Verify chronological boundary: max(train) <= min(val) <= min(test)
    assert max(r.observation_time for r in train_recs) <= min(r.observation_time for r in val_recs)
    assert max(r.observation_time for r in val_recs) <= min(r.observation_time for r in test_recs)


def test_baseline_error_evaluation():
    """Verifies baseline MAE, RMSE, MBE, and R² calculations."""
    base_time = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    # True residuals: [2.0, -2.0, 4.0, -4.0]
    # MAE = (|2| + |-2| + |4| + |-4|) / 4 = 3.0
    # RMSE = sqrt((4 + 4 + 16 + 16) / 4) = sqrt(10) ≈ 3.162
    # MBE = (2 - 2 + 4 - 4) / 4 = 0.0
    residuals = [2.0, -2.0, 4.0, -4.0]
    records = []
    for i, res in enumerate(residuals):
        rec = EngineeredFeatureRecord(
            sample_id=f"S_{i}",
            station_id="AWS_01",
            block_id=1,
            observation_time=base_time + timedelta(hours=i),
            forecast_valid_time=base_time + timedelta(hours=i),
            forecast_issue_time=base_time,
            source_model="IMD-GFS",
            forecast_lead_hours=float(i),
            time_diff_minutes=0.0,
            hour_of_day=i,
            sin_hour=0.0,
            cos_hour=1.0,
            day_of_year=244,
            sin_day_of_year=0.0,
            cos_day_of_year=1.0,
            month=9,
            sin_month=0.0,
            cos_month=1.0,
            obs_latitude=25.3,
            obs_longitude=82.9,
            observed_temp_c=25.0 + res,
            coarse_forecast_temp_c=25.0,
            temperature_residual_c=res,
        )
        records.append(rec)

    metrics = BaselineEvaluator.calculate_metrics(records)
    assert metrics.sample_count == 4
    assert metrics.mae_celsius == 3.0
    assert metrics.rmse_celsius == pytest.approx(3.162, 0.01)
    assert metrics.mean_bias_error_celsius == 0.0
