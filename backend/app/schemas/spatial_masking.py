"""
Panchayat Spatial Masking Schemas & Provenance Models
SIH Problem Statement 26074 (Weather Downscaling - Task 2)

Defines data models for source weather grids, polygon-cell intersections,
area-weighted extraction results, and meteorological resolution provenance.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field


class VariableType(str, Enum):
    """Meteorological classification of gridded variables determining valid aggregation math."""
    CONTINUOUS = "CONTINUOUS"                             # e.g., temperature (°C), humidity (%)
    PRECIPITATION_ACCUMULATION = "PRECIPITATION_ACCUMULATION"  # e.g., rainfall depth (mm)
    PRECIPITATION_INTENSITY = "PRECIPITATION_INTENSITY"        # e.g., rain rate (mm/h)
    WIND_VECTOR = "WIND_VECTOR"                           # e.g., wind speed/direction
    CATEGORICAL = "CATEGORICAL"                           # e.g., weather codes, cloud masks


class CoverageQuality(str, Enum):
    """Categorical assessment of how strongly source grid cells cover the target Panchayat."""
    COMPLETE = "COMPLETE"           # >= 95% spatial coverage
    HIGH = "HIGH"                   # >= 80% spatial coverage
    MODERATE = "MODERATE"           # >= 50% spatial coverage
    PARTIAL = "PARTIAL"             # > 0% but < 50% spatial coverage
    INSUFFICIENT = "INSUFFICIENT"   # Valid data covers < 20% of polygon or heavy NaN gaps
    ZERO_COVERAGE = "ZERO_COVERAGE" # 0% intersection


class SourceResolutionProvenance(BaseModel):
    """
    Immutable provenance and scientific resolution contract.
    Strictly documents the distinction between native, processing, and visualization resolutions.
    """
    source_name: str = Field(..., description="Name of source product/model (e.g. 'NCMRWF-IMDAA', 'ERA5-LAND', 'DOWNSCALED_1KM')")
    source_product: Optional[str] = Field(None, description="Detailed product identifier or forecast run")
    native_resolution_km: float = Field(..., gt=0.0, description="True physical resolution of the source grid in kilometers")
    processing_resolution_km: float = Field(..., gt=0.0, description="Grid resolution used during spatial intersection")
    visualization_resolution_km: Optional[float] = Field(None, description="Nominal resolution of front-end display layers")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System of the input field")
    spatial_extent: Optional[Tuple[float, float, float, float]] = Field(
        None, description="Bounding box extent: (min_lon, min_lat, max_lon, max_lat) in WGS84"
    )
    valid_time: str = Field(..., description="ISO 8601 UTC timestamp for which weather data is valid")
    processing_timestamp: str = Field(..., description="ISO 8601 UTC timestamp when spatial masking was executed")
    source_version: Optional[str] = Field(default="1.0", description="Version or release tag of the source dataset")
    resolution_disclaimer: str = Field(
        default="Spatial masking intersects native grid cells with administrative boundaries; it does NOT synthesize higher meteorological resolution than the underlying source field.",
        description="Scientific policy guardrail preventing false claims of hyper-resolution"
    )

    model_config = ConfigDict(extra="ignore")


class SourceGridCell(BaseModel):
    """Individual georeferenced grid cell / pixel of a source weather field."""
    cell_id: str = Field(..., description="Unique cell identifier (e.g. 'c_row_col')")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Polygon geometry in EPSG:4326")
    value: Optional[float] = Field(None, description="Scalar observation/forecast value (None/NaN for missing)")
    row_idx: Optional[int] = Field(None, description="Grid row index")
    col_idx: Optional[int] = Field(None, description="Grid column index")
    area_sq_km: Optional[float] = Field(None, description="Precomputed geodetic cell area in sq km")

    model_config = ConfigDict(extra="ignore")


class SourceWeatherGrid(BaseModel):
    """
    Standardized container for a georeferenced weather or observation field.
    Can be composed of explicit polygonal cells or regular raster arrays.
    """
    variable_name: str = Field(..., description="Meteorological variable (e.g. 'temperature_2m', 'precipitation')")
    variable_type: VariableType = Field(default=VariableType.CONTINUOUS, description="Variable physical semantics")
    variable_unit: str = Field(..., description="Unit of measurement (e.g. '°C', 'mm', 'mm/h')")
    provenance: SourceResolutionProvenance = Field(..., description="Native resolution and source metadata")
    cells: List[SourceGridCell] = Field(..., description="Collection of georeferenced grid cells")

    model_config = ConfigDict(extra="ignore")


class CellIntersectionResult(BaseModel):
    """Audit detail of an individual source cell's intersection with the Panchayat polygon."""
    cell_id: str = Field(..., description="Source cell identifier")
    source_value: Optional[float] = Field(None, description="Raw value from source grid cell")
    cell_area_sq_km: float = Field(..., description="Total geodetic area of the source cell")
    intersection_area_sq_km: float = Field(..., description="Area of geometric intersection with Panchayat polygon")
    overlap_fraction_of_cell: float = Field(..., description="Intersection area divided by source cell area (0.0 to 1.0)")
    overlap_fraction_of_panchayat: float = Field(..., description="Intersection area divided by Panchayat polygon area (0.0 to 1.0)")
    is_valid_value: bool = Field(..., description="True if value is not None and finite (not NaN/inf)")

    model_config = ConfigDict(extra="ignore")


class ContinuousVariableFeatures(BaseModel):
    """Spatial statistics tailored for continuous meteorological fields (temperature, humidity)."""
    weighted_mean: Optional[float] = Field(None, description="Area-weighted mean taking exact cell overlap area into account")
    mean: Optional[float] = Field(None, description="Unweighted arithmetic mean of intersecting valid cells")
    min: Optional[float] = Field(None, description="Minimum value among intersecting cells")
    max: Optional[float] = Field(None, description="Maximum value among intersecting cells")
    std: Optional[float] = Field(None, description="Sample standard deviation across intersecting cells")
    median: Optional[float] = Field(None, description="Median value among intersecting cells")
    p10: Optional[float] = Field(None, description="10th percentile value")
    p90: Optional[float] = Field(None, description="90th percentile value")

    model_config = ConfigDict(extra="ignore")


class PrecipitationVariableFeatures(BaseModel):
    """
    Spatial statistics tailored for precipitation fields.
    Preserves critical distinctions between amount, intensity, rain fraction, and detection.
    """
    weighted_mean_amount_mm: Optional[float] = Field(None, description="Area-weighted mean precipitation amount in mm")
    max_amount_mm: Optional[float] = Field(None, description="Maximum precipitation amount observed across cells in mm")
    min_amount_mm: Optional[float] = Field(None, description="Minimum precipitation amount observed across cells in mm")
    intensity_mm_per_hr: Optional[float] = Field(None, description="Estimated/reported precipitation rate in mm/h")
    accumulated_precipitation_mm: Optional[float] = Field(None, description="Temporal accumulation sum over interval in mm")
    rain_area_fraction: Optional[float] = Field(None, description="Fraction of covered Panchayat area with rain >= detection_threshold (0.0 to 1.0)")
    is_rain_detected: Optional[bool] = Field(None, description="Boolean flag: True if any intersecting cell exceeds detection threshold")
    detection_threshold_mm: float = Field(default=0.1, description="Threshold above which precipitation is considered detected (default 0.1 mm)")
    unweighted_mean_amount_mm: Optional[float] = Field(None, description="Unweighted arithmetic mean of valid rain cells")

    model_config = ConfigDict(extra="ignore")


class PanchayatSpatialExtractionResult(BaseModel):
    """
    Canonical output structure for Panchayat-level spatial masking.
    Delivers A-specific or B-specific spatial features with deterministic provenance.
    """
    panchayat_id: str = Field(..., description="Target Panchayat identifier")
    panchayat_name: Optional[str] = Field(None, description="Target Gram Panchayat name")
    variable_name: str = Field(..., description="Meteorological variable extracted")
    variable_unit: str = Field(..., description="Variable measurement unit")
    variable_type: VariableType = Field(..., description="Variable physical semantics")
    source_name: str = Field(..., description="Input source dataset name")
    valid_time: str = Field(..., description="Forecast / observation validity timestamp")
    native_resolution_km: float = Field(..., description="True native resolution of the underlying weather field in km")
    
    # Coverage Diagnostics
    cells_considered: int = Field(..., description="Total candidate cells in spatial extent evaluated")
    cells_intersecting: int = Field(..., description="Number of source cells that geometrically intersect the polygon")
    valid_cells_intersecting: int = Field(..., description="Number of intersecting cells having valid (non-NaN) values")
    panchayat_area_sq_km: float = Field(..., description="Total geodetic surface area of Panchayat polygon in sq km")
    intersecting_area_sq_km: float = Field(..., description="Summed intersection area between polygon and grid cells in sq km")
    coverage_fraction: float = Field(..., description="Fraction of Panchayat polygon area covered by intersecting grid cells (0.0 to 1.0)")
    valid_coverage_fraction: float = Field(..., description="Fraction of Panchayat polygon area covered by valid non-NaN cells (0.0 to 1.0)")
    coverage_quality: CoverageQuality = Field(..., description="Quality tier of spatial coverage")

    # Spatial Features
    features: Dict[str, Any] = Field(..., description="Variable-specific spatial statistics (ContinuousVariableFeatures or PrecipitationVariableFeatures)")
    
    # Audit & Provenance
    cell_intersections: Optional[List[CellIntersectionResult]] = Field(None, description="Optional per-cell intersection breakdown for auditing")
    provenance: SourceResolutionProvenance = Field(..., description="Complete resolution provenance record")
    status: str = Field(default="SUCCESS", description="Operational status: SUCCESS, NO_INTERSECTING_CELLS, ALL_VALUES_MISSING, etc.")
    message: Optional[str] = Field(None, description="Diagnostic commentary or explanation")
    success: bool = Field(default=True, description="API success indicator")

    model_config = ConfigDict(extra="ignore")
