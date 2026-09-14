"""
SQLAlchemy ORM Models Registry
Exports all entity models for Alembic metadata tracking and application queries.
"""
from app.db.base import Base
from app.db.models.spatial import Block, Panchayat, LandUseMask
from app.db.models.weather import (
    RawWeatherRecord,
    BlockWeatherForecast,
    WeatherObservation,
    DownscaledWeatherGrid,
    PanchayatWeather,
)
from app.db.models.agriculture import (
    Crop,
    CropPhenologyStage,
    SoilProfile,
    PanchayatCropMapping,
    PanchayatCropContext,
)
from app.db.models.advisory import AgroAdvisory, AgriculturalRiskLog

__all__ = [
    "Base",
    "Block",
    "Panchayat",
    "LandUseMask",
    "RawWeatherRecord",
    "BlockWeatherForecast",
    "WeatherObservation",
    "DownscaledWeatherGrid",
    "PanchayatWeather",
    "Crop",
    "CropPhenologyStage",
    "SoilProfile",
    "PanchayatCropMapping",
    "PanchayatCropContext",
    "AgroAdvisory",
    "AgriculturalRiskLog",
]

