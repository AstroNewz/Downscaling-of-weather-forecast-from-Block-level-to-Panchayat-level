from typing import List, Union
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
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
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
    DEFAULT_SRID: int = 4326  # WGS 84 (lat/lon)
    PROJECTED_SRID: int = 3857  # Web Mercator for planar distance computations
    TARGET_GRID_RESOLUTION_KM: float = 1.0  # High-resolution downscaled grid target (1 km x 1 km)

    # Weather Data Ingestion (IMD / NCMRWF / Open APIs)
    IMD_API_BASE_URL: str = "https://placeholder-imd-api.gov.in/v1"
    IMD_API_KEY: str = ""
    WEATHER_INGESTION_INTERVAL_MINUTES: int = 180

    # Machine Learning Downscaling & Dataset Engineering
    MODEL_ARTIFACTS_DIR: str = "models/"
    ML_MODEL_DIR: str = "models/temperature_residual/"
    DEFAULT_DOWNSCALING_ALGORITHM: str = "xgboost"
    USE_TERRAIN_CORRECTION: bool = True
    DATASET_VERSION: str = "v1.1.0"
    DATASET_OUTPUT_DIR: str = "data/processed/"
    TEMPORAL_MATCH_TOLERANCE_MINUTES: int = 180  # Max tolerance for observation to forecast valid_time match
    TRAIN_RATIO: float = 0.70
    VALIDATION_RATIO: float = 0.15
    TEST_RATIO: float = 0.15
    EXCLUDE_SUSPICIOUS_BY_DEFAULT: bool = True

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
