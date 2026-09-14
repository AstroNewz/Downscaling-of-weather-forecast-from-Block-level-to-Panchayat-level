from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional
from app.weather.schemas import ParsedWeatherRecord


class WeatherProvider(ABC):
    """
    Abstract Base Interface for Weather Data Providers.
    Decouples raw external feeds (CSV, IMD GRIB2, NCMRWF NetCDF, API endpoints)
    from downstream validation, normalization, and database ingestion.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'CSV_PROVIDER', 'IMD_NWP_PROVIDER')."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported input formats or protocols (e.g. ['csv', 'tsv'])."""
        pass

    @abstractmethod
    def parse(
        self,
        source_data: Any,
        options: Optional[Dict[str, Any]] = None
    ) -> List[ParsedWeatherRecord]:
        """
        Parses source data into standardized ParsedWeatherRecord instances.

        Args:
            source_data: File path, file-like stream, raw string, or dictionary payload.
            options: Optional configuration dictionary (delimiter, default units, column mapping).

        Returns:
            List of ParsedWeatherRecord objects.
        """
        pass
