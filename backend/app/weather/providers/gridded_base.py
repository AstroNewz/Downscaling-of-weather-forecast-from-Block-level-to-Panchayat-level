"""
Abstract Base Interface for Gridded Observation Providers
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Establishes a uniform observation abstraction for satellite, future radar,
and gridded atmospheric observations. All providers output a canonical
SourceWeatherGrid that plugs directly into the Task 2 spatial-masking layer.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from app.schemas.spatial_masking import SourceWeatherGrid


class GriddedObservationProvider(ABC):
    """
    Abstract base provider for spatial gridded observations.
    Decouples raw raster formats (GeoTIFF, NetCDF, GRIB) and telemetry feeds
    from downstream spatial-masking and agro-meteorological modeling.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'ISRO_MOSDAC_PROVIDER', 'FUTURE_RADAR_DWR')."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Physical observation category: 'SATELLITE', 'RADAR', 'MESONET_INTERPOLATED'."""
        pass

    @property
    @abstractmethod
    def supported_products(self) -> List[str]:
        """List of supported product names or variable keys."""
        pass

    @abstractmethod
    def fetch_observation(
        self,
        product: str,
        observation_time: Optional[Union[datetime, str]] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> SourceWeatherGrid:
        """
        Retrieves or ingests a georeferenced raster/grid observation,
        returning the canonical SourceWeatherGrid.

        Args:
            product: Specific product identifier from supported_products
            observation_time: Target acquisition/observation timestamp (UTC)
            bounding_box: Optional crop extent: (min_lon, min_lat, max_lon, max_lat)
            options: Supplementary parameters (file paths, channel selections, thresholds)

        Returns:
            SourceWeatherGrid ready for exact Panchayat polygon masking.
        """
        pass

    @abstractmethod
    def check_freshness(
        self,
        observation_time: Union[datetime, str],
        threshold_minutes: float = 60.0,
    ) -> Tuple[bool, float, str]:
        """
        Evaluates observation latency against operational freshness requirements.

        Returns:
            Tuple of (is_fresh, age_minutes, status_description)
        """
        pass
