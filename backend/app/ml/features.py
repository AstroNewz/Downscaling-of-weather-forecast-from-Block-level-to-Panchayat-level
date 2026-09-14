import math
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from app.db.models.weather import BlockWeatherForecast, WeatherObservation
from app.ml.schemas import EngineeredFeatureRecord, FEATURE_SCHEMA_VERSION
from app.gis.schemas import EnvironmentalFeatureSet


class FeatureEngineer:
    """
    Constructs deterministic, standardized feature rows for weather downscaling ML models.
    Enriched with Phase 5 GIS, Topographic, and Land-Cover Predictors.
    """

    @staticmethod
    def compute_cyclical_features(dt: datetime) -> Dict[str, float]:
        """Calculates sine and cosine transformations for periodic temporal cycles."""
        hour = dt.hour + dt.minute / 60.0
        day_of_year = dt.timetuple().tm_yday
        month = dt.month

        return {
            "hour_of_day": int(dt.hour),
            "sin_hour": round(math.sin(2.0 * math.pi * hour / 24.0), 6),
            "cos_hour": round(math.cos(2.0 * math.pi * hour / 24.0), 6),
            "day_of_year": int(day_of_year),
            "sin_day_of_year": round(math.sin(2.0 * math.pi * day_of_year / 365.25), 6),
            "cos_day_of_year": round(math.cos(2.0 * math.pi * day_of_year / 365.25), 6),
            "month": int(month),
            "sin_month": round(math.sin(2.0 * math.pi * month / 12.0), 6),
            "cos_month": round(math.cos(2.0 * math.pi * month / 12.0), 6),
        }

    @classmethod
    def extract_temperatures_and_residual(
        cls,
        obs: WeatherObservation,
        forecast: BlockWeatherForecast
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Extracts observed temperature, coarse forecast temperature, and calculates the residual target.

        Returns:
            Tuple of (observed_temp_c, coarse_forecast_temp_c, temperature_residual_c)
        """
        observed_t: Optional[float] = None
        if obs.temp_celsius is not None:
            observed_t = obs.temp_celsius
        elif obs.temp_max is not None and obs.temp_min is not None:
            observed_t = round((obs.temp_max + obs.temp_min) / 2.0, 2)
        elif obs.temp_max is not None:
            observed_t = obs.temp_max
        elif obs.temp_min is not None:
            observed_t = obs.temp_min

        coarse_t: Optional[float] = None
        if forecast.temp_min is not None and forecast.temp_max is not None:
            coarse_t = round((forecast.temp_max + forecast.temp_min) / 2.0, 2)
        elif forecast.temp_max is not None:
            coarse_t = forecast.temp_max
        elif forecast.temp_min is not None:
            coarse_t = forecast.temp_min

        if observed_t is None or coarse_t is None:
            return None, None, None

        # Residual target formulation: y = observed - coarse_forecast
        residual = round(observed_t - coarse_t, 3)
        return observed_t, coarse_t, residual

    @classmethod
    def build_feature_record(
        cls,
        obs: WeatherObservation,
        forecast: BlockWeatherForecast,
        lead_hours: float,
        time_diff_min: float,
        spatial_data: Dict[str, Any],
        environmental_features: Optional[EnvironmentalFeatureSet] = None,
        dataset_version: str = FEATURE_SCHEMA_VERSION,
        split: str = "train"
    ) -> Optional[EngineeredFeatureRecord]:
        """
        Constructs a complete EngineeredFeatureRecord including GIS and environmental predictors.
        """
        obs_temp, coarse_temp, residual = cls.extract_temperatures_and_residual(obs, forecast)
        if residual is None or obs_temp is None or coarse_temp is None:
            return None

        cyclical = cls.compute_cyclical_features(obs.observation_time)

        # Derive forecast mean temp if both min and max are available
        fc_mean = None
        if forecast.temp_min is not None and forecast.temp_max is not None:
            fc_mean = round((forecast.temp_max + forecast.temp_min) / 2.0, 2)

        sample_id = f"SMP_{obs.station_id}_{forecast.block_id}_{int(obs.observation_time.timestamp())}"

        # Extract Terrain Features (Phase 5)
        elevation_m = spatial_data.get("obs_elevation_m")
        block_elevation_m = spatial_data.get("block_elevation_m")
        elevation_diff_m = spatial_data.get("elevation_diff_m")
        slope_deg = None
        aspect_deg = None
        sin_asp = None
        cos_asp = None
        roughness = None
        lapse_adj = None

        if environmental_features and environmental_features.terrain:
            t = environmental_features.terrain
            if t.elevation_m is not None:
                elevation_m = t.elevation_m
            slope_deg = t.slope_deg
            aspect_deg = t.aspect_deg
            sin_asp = t.sin_aspect
            cos_asp = t.cos_aspect
            roughness = t.terrain_roughness
            elevation_diff_m = t.elevation_diff_to_block_m or elevation_diff_m
            lapse_adj = t.lapse_rate_temp_adjustment_c

        # Extract Land-Use Features (Phase 5)
        crop_frac = None
        forest_frac = None
        urban_frac = None
        water_frac = None
        barren_frac = None
        is_agri = None

        if environmental_features and environmental_features.land_use:
            lu = environmental_features.land_use
            crop_frac = lu.cropland_fraction
            forest_frac = lu.forest_fraction
            urban_frac = lu.urban_fraction
            water_frac = lu.water_fraction
            barren_frac = lu.barren_fraction
            is_agri = lu.is_agricultural_cropland

        return EngineeredFeatureRecord(
            sample_id=sample_id,
            station_id=obs.station_id,
            block_id=forecast.block_id,
            block_name=forecast.block.name if forecast.block else None,
            observation_time=obs.observation_time,
            forecast_valid_time=forecast.forecast_date,
            forecast_issue_time=forecast.issue_time,
            source_model=forecast.source_model,
            dataset_version=dataset_version,
            split=split,
            # Coarse NWP Predictors
            forecast_temp_min=forecast.temp_min,
            forecast_temp_max=forecast.temp_max,
            forecast_temp_mean=fc_mean,
            forecast_rainfall_mm=forecast.rainfall_mm,
            forecast_humidity_pct=forecast.relative_humidity_pct,
            forecast_wind_speed_mps=forecast.wind_speed_mps,
            forecast_wind_direction_deg=forecast.wind_direction_deg,
            forecast_cloud_cover_pct=forecast.cloud_cover_pct,
            # Temporal & Lead Time Features
            forecast_lead_hours=lead_hours,
            time_diff_minutes=time_diff_min,
            hour_of_day=cyclical["hour_of_day"],
            sin_hour=cyclical["sin_hour"],
            cos_hour=cyclical["cos_hour"],
            day_of_year=cyclical["day_of_year"],
            sin_day_of_year=cyclical["sin_day_of_year"],
            cos_day_of_year=cyclical["cos_day_of_year"],
            month=cyclical["month"],
            sin_month=cyclical["sin_month"],
            cos_month=cyclical["cos_month"],
            # Spatial & Topographic Features (Phase 5 Enriched)
            obs_latitude=spatial_data["obs_latitude"],
            obs_longitude=spatial_data["obs_longitude"],
            block_centroid_lat=spatial_data.get("block_centroid_lat"),
            block_centroid_lon=spatial_data.get("block_centroid_lon"),
            distance_to_centroid_km=spatial_data.get("distance_to_centroid_km"),
            obs_elevation_m=elevation_m,
            block_elevation_m=block_elevation_m,
            elevation_diff_m=elevation_diff_m,
            slope_deg=slope_deg,
            aspect_deg=aspect_deg,
            sin_aspect=sin_asp,
            cos_aspect=cos_asp,
            terrain_roughness=roughness,
            lapse_rate_temp_adjustment_c=lapse_adj,
            # Land-Use & Land-Cover Composition (Phase 5 Enriched)
            cropland_fraction=crop_frac,
            forest_fraction=forest_frac,
            urban_fraction=urban_frac,
            water_fraction=water_frac,
            barren_fraction=barren_frac,
            is_agricultural_cropland=is_agri,
            # Ground Truth & Targets
            observed_temp_c=obs_temp,
            coarse_forecast_temp_c=coarse_temp,
            temperature_residual_c=residual,
        )
