import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configures centralized structured logging for the FastAPI application.
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("rasterio").setLevel(logging.WARNING)
    logging.getLogger("shapely").setLevel(logging.WARNING)

    logger = logging.getLogger("agri_weather_backend")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
