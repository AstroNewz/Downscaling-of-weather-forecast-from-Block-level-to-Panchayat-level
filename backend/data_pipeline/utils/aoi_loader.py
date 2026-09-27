"""
AOI Loader — reads india_pilot.yaml and exposes typed AOI configuration.

All acquisition scripts must call load_pilot_config() to obtain the AOI
rather than hard-coding bbox or station lists.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required: pip install pyyaml")


# Default config path relative to backend root
_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "data_pipeline" / "config" / "india_pilot.yaml"


@dataclass
class AwsStation:
    station_id: str
    name: str
    organization: str
    latitude: float
    longitude: float
    elevation_m: Optional[float]
    data_status: str


@dataclass
class AOISplit:
    start: str  # ISO date string YYYY-MM-DD
    end: str


@dataclass
class PilotConfig:
    country: str
    state: str
    district: str
    block: str
    pilot_blocks: List[str]
    known_aws_stations: List[AwsStation]
    panchayats: List[str]

    # AOI
    aoi_source: str
    latitude_min: float
    latitude_max: float
    longitude_min: float
    longitude_max: float

    # CRS
    timezone: str
    crs_geographic: str
    metric_crs_epsg: int        # expected EPSG for dynamic UTM
    grid_resolution_km: float
    grid_resolution_m: float

    # Time
    weather_start_date: str
    weather_end_date: str
    splits: Dict[str, AOISplit]

    # Raw source config
    data_sources: Dict[str, Any] = field(default_factory=dict)

    @property
    def bbox(self):
        """Returns (lat_min, lat_max, lon_min, lon_max)."""
        return (self.latitude_min, self.latitude_max,
                self.longitude_min, self.longitude_max)

    @property
    def bbox_wsen(self):
        """Returns (west, south, east, north) — CDS API / OGC convention."""
        return (self.longitude_min, self.latitude_min,
                self.longitude_max, self.latitude_max)

    @property
    def bbox_snwe(self):
        """Returns (south, north, west, east) — some NASA APIs."""
        return (self.latitude_min, self.latitude_max,
                self.longitude_min, self.longitude_max)

    def describe(self) -> str:
        return (
            f"Pilot AOI: {self.district} district, {self.state}, {self.country}\n"
            f"  Blocks  : {', '.join(self.pilot_blocks)}\n"
            f"  Bbox    : lat {self.latitude_min}–{self.latitude_max}, "
            f"lon {self.longitude_min}–{self.longitude_max}\n"
            f"  Period  : {self.weather_start_date} to {self.weather_end_date}\n"
            f"  UTM     : EPSG:{self.metric_crs_epsg}\n"
            f"  AWS     : {len(self.known_aws_stations)} stations"
        )


def load_pilot_config(config_path: Optional[str] = None) -> PilotConfig:
    """
    Loads and validates the india_pilot.yaml configuration.

    Args:
        config_path: Explicit path to india_pilot.yaml.
                     Defaults to the canonical location.

    Returns:
        PilotConfig — strongly typed AOI configuration object.

    Raises:
        FileNotFoundError: If config file does not exist.
        KeyError: If required fields are missing from config.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG

    if not path.exists():
        raise FileNotFoundError(
            f"Pilot config not found at: {path}\n"
            f"Expected: backend/data_pipeline/config/india_pilot.yaml"
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    stations = []
    for s in raw.get("known_aws_stations", []):
        stations.append(AwsStation(
            station_id=s["station_id"],
            name=s["name"],
            organization=s["organization"],
            latitude=float(s["latitude"]),
            longitude=float(s["longitude"]),
            elevation_m=s.get("elevation_m"),
            data_status=s.get("data_status", "UNKNOWN"),
        ))

    splits_raw = raw.get("splits", {})
    splits = {
        k: AOISplit(start=v["start"], end=v["end"])
        for k, v in splits_raw.items()
    }

    metric_crs = raw.get("metric_crs", {})
    return PilotConfig(
        country=raw["country"],
        state=raw["state"],
        district=raw["district"],
        block=raw["block"],
        pilot_blocks=raw.get("pilot_blocks", [raw["block"]]),
        known_aws_stations=stations,
        panchayats=raw.get("panchayats", []),
        aoi_source=raw["aoi_source"],
        latitude_min=float(raw["latitude_min"]),
        latitude_max=float(raw["latitude_max"]),
        longitude_min=float(raw["longitude_min"]),
        longitude_max=float(raw["longitude_max"]),
        timezone=raw["timezone"],
        crs_geographic=raw["crs_geographic"],
        metric_crs_epsg=int(metric_crs.get("expected_epsg", 32644)),
        grid_resolution_km=float(raw.get("grid_resolution_km", 1.0)),
        grid_resolution_m=float(raw.get("grid_resolution_m", 1000.0)),
        weather_start_date=raw["weather_start_date"],
        weather_end_date=raw["weather_end_date"],
        splits=splits,
        data_sources=raw.get("data_sources", {}),
    )
