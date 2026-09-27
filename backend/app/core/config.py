from typing import List, Union, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings for Agro-Meteorological Weather Intelligence Platform.
    Adheres to 12-factor configuration via environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Core Application
    APP_NAME: str = "GraminKrishi-Mausam-Intelligence"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev_insecure_secret_key_change_in_production_min_32_bytes_long"

    # Server Binding
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8085",
        "http://localhost:8086",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8085",
        "http://127.0.0.1:8086",
        "http://127.0.0.1:8080",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database & PostGIS
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "agri_weather_db"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/agri_weather_db"

    # GIS / Spatial Intelligence Settings
    DEFAULT_SRID: int = 4326  # WGS 84 (lat/lon) — all stored coordinates use this CRS

    # SCIENTIFIC NOTE: EPSG:3857 (Web Mercator) MUST NOT be used for distance, area,
    # or grid calculations. It is provided here only for reference/display contexts
    # (e.g. map tile servers). ALL metric calculations use a dynamically selected
    # local UTM CRS computed by SpatialGridGenerator.get_optimal_utm_epsg(lon, lat).
    # For Varanasi pilot AOI this resolves to EPSG:32644 (WGS 84 / UTM zone 44N).
    PROJECTED_SRID: int = 3857  # DISPLAY/TILE CRS ONLY — see note above

    TARGET_GRID_RESOLUTION_KM: float = 1.0  # High-resolution downscaled grid target (1 km x 1 km)

    # Panchayat Boundary Service Settings (SIH PS 26074)
    PANCHAYAT_BOUNDARY_SOURCE_PATH: Optional[str] = "backend/data/raw/india/pilot/boundaries/authorized_panchayats.geojson"
    PANCHAYAT_BOUNDARY_TOLERANCE_DEG: float = 1e-5  # Boundary buffer zone: 1e-5 deg ≈ 1.1m at equator
    PANCHAYAT_BOUNDARY_FAIL_CLOSED_ON_UNVERIFIED: bool = False

    # Weather Data Ingestion Modes (DEMO, LIVE, AUTO)
    WEATHER_DATA_MODE: str = "DEMO"  # DEMO, LIVE, AUTO
    LIVE_WEATHER_ENABLED: bool = False
    WEATHER_STALE_AFTER_MINUTES: int = 180  # Stale threshold: 3 hours
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    LIVE_PROVIDER_TIMEOUT_SECONDS: float = 6.0
    IMD_API_BASE_URL: str = "https://placeholder-imd-api.gov.in/v1"
    IMD_API_KEY: str = ""
    WEATHER_INGESTION_INTERVAL_MINUTES: int = 180

    # Satellite Observation Adapter Settings (SIH PS 26074 - Task 3)
    SATELLITE_PROVIDER_ENABLED: bool = True
    SATELLITE_DATA_DIR: str = "backend/data/raw/satellite/"
    SATELLITE_FRESHNESS_THRESHOLD_MINUTES: float = 60.0
    SATELLITE_CONVECTIVE_TEMP_THRESHOLD_K: float = 235.0  # Heuristic convective cloud-top threshold (Kelvin)
    SATELLITE_FAIL_CLOSED_ON_GEOREFERENCE: bool = True

    # Localized Precipitation Observation-Fusion & Nowcasting (SIH PS 26074 - Task 4)
    NOWCAST_ENABLED: bool = True
    NOWCAST_MEASURABLE_RAIN_THRESHOLD_MM: float = 0.1
    NOWCAST_FRESHNESS_THRESHOLD_MINUTES: float = 60.0
    NOWCAST_STALE_PENALTY_FACTOR: float = 0.50
    NOWCAST_MIN_SPATIAL_COVERAGE: float = 0.20
    NOWCAST_DISAGREEMENT_PROB_DELTA: float = 0.35
    NOWCAST_METHOD_VERSION: str = "DETERMINISTIC_RESEARCH_HEURISTIC_V1"


    # Certified Scientific Baseline Constants (NON-NEGOTIABLE)
    CALIBRATION_OFFSET_C: float = 0.7351  # Certified scalar baseline offset (Phase 23/24)

    # Controlled Production Rollout Settings (Dynamic Residual Model v2)
    ROLLOUT_MODE: str = "DYNAMIC_PRIMARY"  # DYNAMIC_PRIMARY, BASELINE_PRIMARY (immediate rollback switch)
    MODEL_OPERATIONAL_STATUS: str = "CONTROLLED_PRODUCTION"  # RESEARCH_ONLY, PRODUCTION_CANDIDATE, CONTROLLED_PRODUCTION, PRODUCTION
    ACTIVE_OPERATIONAL_MODEL: str = "DYNAMIC_V2"
    FALLBACK_OPERATIONAL_MODEL: str = "CERTIFIED_BASELINE_V1"

    # Dynamic Residual Safety Guardrail Bounds (Strict: failure triggers baseline fallback)
    DYNAMIC_RESIDUAL_SAFETY_MIN: float = -8.0
    DYNAMIC_RESIDUAL_SAFETY_MAX: float = 8.0

    # Operational Applicability / OOD Training Domain Bounds (from 17 WMO Kharif 2024 dataset)
    TRAINING_TEMP_MIN_C: float = 5.0
    TRAINING_TEMP_MAX_C: float = 52.0
    TRAINING_RH_MIN_PCT: float = 10.0
    TRAINING_RH_MAX_PCT: float = 100.0
    TRAINING_WIND_MAX_MPS: float = 28.0
    TRAINING_ELEV_MAX_M: float = 2800.0
    TRAINING_SLOPE_MAX_DEG: float = 35.0

    # Machine Learning Downscaling & Dataset Engineering
    MODEL_ARTIFACTS_DIR: str = "models/"
    ML_MODEL_DIR: str = "models/temperature_residual/"  # Production model registry — DO NOT overwrite
    CANDIDATES_MODEL_DIR: str = "models/candidates/"    # Real-data candidate models (never overwrite production)
    DEFAULT_DOWNSCALING_ALGORITHM: str = "xgboost"
    USE_TERRAIN_CORRECTION: bool = True
    DATASET_VERSION: str = "v1.1.0"
    DATASET_OUTPUT_DIR: str = "data/processed/"
    TEMPORAL_MATCH_TOLERANCE_MINUTES: int = 180  # Max tolerance for observation to forecast valid_time match
    TRAIN_RATIO: float = 0.70
    VALIDATION_RATIO: float = 0.15
    TEST_RATIO: float = 0.15
    EXCLUDE_SUSPICIOUS_BY_DEFAULT: bool = True

    # India Pilot Pipeline Paths
    PILOT_CONFIG_PATH: str = "backend/data_pipeline/config/india_pilot.yaml"
    INDIA_DATA_ROOT: str = "backend/data"

    # Phase 6 ML Training & Inference Engine Settings
    TEMPERATURE_MODEL_VERSION: str = "v1.0.0"
    ML_RANDOM_SEED: int = 42
    ML_MIN_TRAIN_ROWS: int = 50
    ML_EARLY_STOPPING_ROUNDS: int = 15
    ML_ALLOW_SYNTHETIC_TRAINING: bool = False  # Strict scientific policy: Never train production models on synthetic fixtures

    # Agro-Meteorological Advisory Engine
    ADVISORY_MIN_CONFIDENCE_THRESHOLD: float = 0.75
    CROPMASK_VALIDATION_ENABLED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
