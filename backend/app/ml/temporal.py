from datetime import datetime
from typing import Optional, Tuple
from app.db.models.weather import BlockWeatherForecast, WeatherObservation


class TemporalAligner:
    """
    Handles time-window matching between ground-truth observations and candidate NWP forecasts,
    with strict future-to-past data leakage prevention.
    """

    @staticmethod
    def evaluate_temporal_match(
        obs: WeatherObservation,
        forecast: BlockWeatherForecast,
        tolerance_minutes: int = 180
    ) -> Tuple[bool, float, float, Optional[str]]:
        """
        Evaluates whether a candidate forecast matches an observation in time.

        Returns:
            Tuple of:
            - is_match (bool)
            - time_difference_minutes (float)
            - forecast_lead_hours (float)
            - rejection_reason (Optional[str])
        """
        # 1. Data Leakage Check:
        # A forecast issued AFTER the observation occurred cannot be used as an input feature
        if forecast.issue_time > obs.observation_time:
            return False, 0.0, 0.0, "LEAKAGE_DETECTED: Forecast issue time is after observation timestamp."

        # 2. Time Difference between Observation and Target Forecast Valid Time
        time_diff_sec = abs((obs.observation_time - forecast.forecast_date).total_seconds())
        time_diff_min = round(time_diff_sec / 60.0, 2)

        # 3. Forecast Lead Time (Time from model run to target forecast validity)
        lead_time_sec = (forecast.forecast_date - forecast.issue_time).total_seconds()
        lead_hours = round(max(0.0, lead_time_sec / 3600.0), 2)

        # 4. Tolerance Threshold Check
        if time_diff_min > tolerance_minutes:
            return False, time_diff_min, lead_hours, f"TIME_MISMATCH: Time difference {time_diff_min} min exceeds tolerance {tolerance_minutes} min."

        return True, time_diff_min, lead_hours, None
