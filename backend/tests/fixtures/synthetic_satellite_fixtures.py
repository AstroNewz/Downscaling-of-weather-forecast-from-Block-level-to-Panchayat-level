"""
Deterministic Synthetic Satellite Test Fixtures
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Provides strictly test-isolated synthetic satellite fields for verifying:
1. Native resolution preservation (e.g., 1.0 km, 4.0 km)
2. Spatial cloud features (cloud_fraction, brightness temperature, convective threshold)
3. Satellite precipitation estimate semantics (satellite_precipitation_estimate, NaN vs 0.0 mm)
4. A/B independent spatial separation across common boundary
5. Multi-temporal change tracking (T0 vs T1)
6. Real GeoTIFF file ingestion via rasterio with fail-closed CRS/geotransform validation

CRITICAL SCIENTIFIC SAFETY:
THESE FIXTURES ARE STRICTLY TEST-ONLY AND CLEARLY LABELED AS:
'SATELLITE_SYNTHETIC_TEST_FIXTURE'.
THEY MUST NEVER BE EXPOSED AS GENUINE SATELLITE OBSERVATIONS.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from rasterio.transform import from_origin
import rasterio
from shapely.geometry import box, mapping, Polygon

from app.schemas.satellite import (
    SatelliteProductType,
    SatelliteProvenance,
)
from app.schemas.spatial_masking import (
    SourceGridCell,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)
from tests.fixtures.imaginary_panchayats_fixture import (
    SHAPELY_POLY_A,
    SHAPELY_POLY_B,
    SHAPELY_DHOLAKPUR_A,
    SHAPELY_DHOLAKPUR_B,
)


def create_satellite_cell(
    cell_id: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    value: Optional[float] = None,
    row_idx: int = 0,
    col_idx: int = 0,
    area_sq_km: Optional[float] = None,
) -> SourceGridCell:
    """Helper to create a georeferenced SourceGridCell."""
    b = box(min_lon, min_lat, max_lon, max_lat)
    return SourceGridCell(
        cell_id=cell_id,
        geometry=mapping(b),
        value=value,
        row_idx=row_idx,
        col_idx=col_idx,
        area_sq_km=area_sq_km,
    )


def build_synthetic_satellite_ir_field(
    native_res_km: float = 1.0,
    valid_time: str = "2026-09-27T12:00:00Z",
) -> SourceWeatherGrid:
    """
    Constructs a synthetic infrared brightness temperature field (Kelvin) across
    domain [82.40, 82.60] x [25.00, 25.20].
    
    Structure:
    - Panchayat A contains cold convective cloud tops (210K - 230K, well below 235K).
    - Panchayat B contains warm clear sky radiances (295K - 305K).
    - Cells along the shared boundary straddle both polygons (intermediate temp ~ 240K).
    
    Proves independent A/B extraction on the SAME source grid.
    """
    cells: List[SourceGridCell] = []
    
    # 4 rows x 4 cols (0.05 deg x 0.05 deg resolution)
    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.00, 25.05, 25.10, 25.15, 25.20]

    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            cell_box = box(min_lon, min_lat, max_lon, max_lat)
            cell_id = f"sat_ir_cell_{r}_{c}"

            # Intersects A or B?
            inter_a = SHAPELY_POLY_A.intersection(cell_box).area
            inter_b = SHAPELY_POLY_B.intersection(cell_box).area

            # Assign synthetic brightness temperature:
            # Bottom row (r=0, bottom arm of A): 215K - 225K (deep convective cloud)
            # Col 0 (c=0, r>=1, vertical arm of A): 210K - 220K (deep cloud)
            # Cols 1-3 (r>=1, Panchayat B): 296K - 304K (clear ground)
            if r == 0:
                val = 215.0 + c * 2.5
            elif c == 0:
                val = 210.0 + r * 3.0
            else:
                val = 295.0 + (r * 2.0) + (c * 1.5)

            cells.append(create_satellite_cell(
                cell_id=cell_id,
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
                area_sq_km=30.25,
            ))

    prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.00, 82.60, 25.20),
        valid_time=valid_time,
        processing_timestamp="2026-09-27T12:05:00Z",
        source_version="1.0.0-test",
        resolution_disclaimer=(
            "SATELLITE_SYNTHETIC_TEST_FIXTURE: Spatial masking intersects native grid cells with administrative "
            "boundaries; it does NOT synthesize higher meteorological resolution than the underlying source field."
        ),
    )

    return SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=prov,
        cells=cells,
    )


def build_synthetic_dholakpur_ir_field(
    native_res_km: float = 1.0,
    valid_time: str = "2026-09-27T12:00:00Z",
) -> SourceWeatherGrid:
    """
    Constructs a synthetic infrared brightness temperature field (Kelvin) across
    the Dholakpur polygon domain [82.40, 82.60] x [25.50, 25.70].

    Mirrors the structure of build_synthetic_satellite_ir_field but covers the
    Dholakpur panchayat geometry (lat 25.50–25.70) rather than the IMAGINARY
    panchayat geometry (lat 25.00–25.20).

    Structure:
    - Dholakpur A vertical bar (c=0, r>=1) and bottom row (r=0): cold convective
      cloud tops (210K–225K) → high rain probability for Panchayat A.
    - Dholakpur B area (c>=1, r>=1): warm clear-sky radiance (295K–305K)
      → low rain probability for Panchayat B.

    Proves that A/B extraction is independent and spatially correct even when
    both Dholakpur panchayats are present in the same boundary registry alongside
    the IMAGINARY panchayats.
    """
    cells: List[SourceGridCell] = []

    # 4 rows x 4 cols at 0.05-degree resolution (covering lat 25.50–25.70, lon 82.40–82.60)
    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.50, 25.55, 25.60, 25.65, 25.70]

    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            cell_box = box(min_lon, min_lat, max_lon, max_lat)
            cell_id = f"dholakpur_ir_cell_{r}_{c}"

            # Determine IR temperature:
            # Bottom row (r=0, bottom arm of Dholakpur A): deep convective cloud (215K–225K)
            # Col 0 (c=0, r>=1, vertical bar of Dholakpur A): deep cloud (210K–220K)
            # Cols 1-3 (r>=1, Dholakpur B area): clear sky (295K–305K)
            if r == 0:
                val = 215.0 + c * 2.5   # 215K to 222.5K — cold cloud bottom bar
            elif c == 0:
                val = 210.0 + r * 3.0   # 213K to 219K — cold cloud vertical bar
            else:
                val = 295.0 + (r * 2.0) + (c * 1.5)  # 298.5K to 305K — clear sky

            cells.append(create_satellite_cell(
                cell_id=cell_id,
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
                area_sq_km=30.25,
            ))

    prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.50, 82.60, 25.70),
        valid_time=valid_time,
        processing_timestamp="2026-09-27T12:05:00Z",
        source_version="1.0.0-test",
        resolution_disclaimer=(
            "SATELLITE_SYNTHETIC_TEST_FIXTURE (Dholakpur domain): Spatial masking intersects "
            "native grid cells with administrative boundaries; it does NOT synthesize higher "
            "meteorological resolution than the underlying source field."
        ),
    )

    return SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=prov,
        cells=cells,
    )


def build_synthetic_satellite_temporal_pair(
    native_res_km: float = 1.0,
) -> Tuple[SourceWeatherGrid, SourceWeatherGrid]:
    """
    Constructs a pair of synthetic satellite observations at T0 and T1 (30 minutes apart).
    
    T0 (12:00 UTC): Moderate cloud over Panchayat A (IR ~ 248K, cloud_fraction ~ 0.50).
    T1 (12:30 UTC): Rapid convective cooling and expansion (IR ~ 215K, cloud_fraction ~ 0.95).
    
    Verifies deterministic temporal delta and trend calculation (COOLING_CONVECTIVE).
    """
    # Base T0
    t0_time = "2026-09-27T12:00:00Z"
    t1_time = "2026-09-27T12:30:00Z"
    
    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.00, 25.05, 25.10, 25.15, 25.20]

    # Build T0
    t0_cells = []
    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            if r == 0:
                val = 250.0 + c * 2.0  # Warm cloud / edge
            elif c == 0:
                val = 245.0 + r * 2.0
            else:
                val = 295.0 + (r * 1.5)
            t0_cells.append(create_satellite_cell(
                cell_id=f"t0_cell_{r}_{c}",
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
            ))

    t0_prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.00, 82.60, 25.20),
        valid_time=t0_time,
        processing_timestamp=t0_time,
        source_version="1.0.0-test",
    )
    t0_grid = SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=t0_prov,
        cells=t0_cells,
    )

    # Build T1 (intensified convective storm over A)
    t1_cells = []
    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            if r == 0:
                val = 215.0 + c * 2.0  # Deep convective cooling (-35K)
            elif c == 0:
                val = 212.0 + r * 2.0  # Deep convective cooling (-33K)
            else:
                val = 295.0 + (r * 1.5)  # Steady over B
            t1_cells.append(create_satellite_cell(
                cell_id=f"t1_cell_{r}_{c}",
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
            ))

    t1_prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.00, 82.60, 25.20),
        valid_time=t1_time,
        processing_timestamp=t1_time,
        source_version="1.0.0-test",
    )
    t1_grid = SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=t1_prov,
        cells=t1_cells,
    )

    return t0_grid, t1_grid


def build_synthetic_satellite_precip_field(
    native_res_km: float = 4.0,
    valid_time: str = "2026-09-27T12:00:00Z",
) -> SourceWeatherGrid:
    """
    Constructs a synthetic satellite precipitation estimate field.
    
    Structure:
    - Retains variable_name 'satellite_precipitation_estimate' (NOT 'observed_rainfall').
    - Distinguishes 0.0 mm (dry) from missing/unobserved (None/NaN).
    - Panchayat A contains estimated rain rates (8.5 - 14.0 mm).
    - Panchayat B contains 0.0 mm (verified clear/dry).
    - One cell has None (sensor missing data flag).
    """
    cells: List[SourceGridCell] = []
    
    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.00, 25.05, 25.10, 25.15, 25.20]

    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            cell_id = f"sat_precip_cell_{r}_{c}"

            if r == 0 and c == 3:
                # Cell with missing data (NaN)
                val = None
            elif r == 0 or c == 0:
                # Over Panchayat A: active precipitation
                val = 8.5 + (r + c) * 1.5
            else:
                # Over Panchayat B: zero rain (0.0 mm)
                val = 0.0

            cells.append(create_satellite_cell(
                cell_id=cell_id,
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2) if val is not None else None,
                row_idx=r, col_idx=c,
            ))

    prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_PRECIPITATION_ESTIMATE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.00, 82.60, 25.20),
        valid_time=valid_time,
        processing_timestamp=valid_time,
        source_version="1.0.0-test",
    )

    return SourceWeatherGrid(
        variable_name="satellite_precipitation_estimate",
        variable_type=VariableType.PRECIPITATION_ACCUMULATION,
        variable_unit="mm",
        provenance=prov,
        cells=cells,
    )


def create_test_geotiff_file(
    output_path: Path,
    width: int = 10,
    height: int = 10,
    min_lon: float = 82.40,
    max_lat: float = 25.20,
    pixel_size: float = 0.02,
    crs: Optional[str] = "EPSG:4326",
    nodata: float = -9999.0,
    corrupt_transform: bool = False,
) -> Path:
    """
    Creates a real GeoTIFF file on disk using rasterio to test physical file ingestion.
    Supports testing missing CRS, corrupt geotransforms, and nodata handling.
    """
    if corrupt_transform:
        transform = rasterio.transform.Affine(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    else:
        transform = from_origin(min_lon, max_lat, pixel_size, pixel_size)

    # Synthetic 2D array of brightness temperatures
    data = np.full((height, width), 290.0, dtype=np.float32)
    # Put convective cloud in top-left
    data[:5, :5] = 220.0
    # Put nodata pixel in bottom-right
    data[-1, -1] = nodata

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data, 1)

    return output_path


def build_synthetic_dholakpur_temporal_pair(
    native_res_km: float = 1.0,
) -> Tuple[SourceWeatherGrid, SourceWeatherGrid]:
    """
    Constructs a T0/T1 pair of synthetic satellite IR fields across the
    Dholakpur domain [82.40, 82.60] x [25.50, 25.70].

    T0 (12:00 UTC): Moderate cloud over Dholakpur A (IR ~248K).
    T1 (12:30 UTC): Rapid convective cooling (IR ~213K) — intensified storm.

    Verifies temporal delta and COOLING_CONVECTIVE trend for Dholakpur panchayats.
    """
    t0_time = "2026-09-27T12:00:00Z"
    t1_time = "2026-09-27T12:30:00Z"

    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.50, 25.55, 25.60, 25.65, 25.70]

    # Build T0
    t0_cells = []
    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            if r == 0:
                val = 250.0 + c * 2.0
            elif c == 0:
                val = 245.0 + r * 2.0
            else:
                val = 295.0 + (r * 1.5)
            t0_cells.append(create_satellite_cell(
                cell_id=f"dhol_t0_cell_{r}_{c}",
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
            ))

    t0_prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.50, 82.60, 25.70),
        valid_time=t0_time,
        processing_timestamp=t0_time,
        source_version="1.0.0-test",
    )
    t0_grid = SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=t0_prov,
        cells=t0_cells,
    )

    # Build T1 (intensified convective storm over Dholakpur A)
    t1_cells = []
    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            if r == 0:
                val = 215.0 + c * 2.0
            elif c == 0:
                val = 212.0 + r * 2.0
            else:
                val = 295.0 + (r * 1.5)
            t1_cells.append(create_satellite_cell(
                cell_id=f"dhol_t1_cell_{r}_{c}",
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
            ))

    t1_prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_IR_BRIGHTNESS_TEMPERATURE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.50, 82.60, 25.70),
        valid_time=t1_time,
        processing_timestamp=t1_time,
        source_version="1.0.0-test",
    )
    t1_grid = SourceWeatherGrid(
        variable_name="brightness_temperature_ir",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="K",
        provenance=t1_prov,
        cells=t1_cells,
    )

    return t0_grid, t1_grid


def build_synthetic_dholakpur_precip_field(
    native_res_km: float = 4.0,
    valid_time: str = "2026-09-27T12:00:00Z",
) -> SourceWeatherGrid:
    """
    Synthetic satellite precipitation estimate field over the Dholakpur domain
    [82.40, 82.60] x [25.50, 25.70].

    Dholakpur A cells get active rain rates (8.5–14.0 mm).
    Dholakpur B cells get 0.0 mm (verified clear/dry).
    One cell has None (sensor missing data flag).
    """
    cells: List[SourceGridCell] = []

    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.50, 25.55, 25.60, 25.65, 25.70]

    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            cell_id = f"dhol_precip_cell_{r}_{c}"

            if r == 0 and c == 3:
                val = None  # sensor missing data
            elif r == 0 or c == 0:
                val = 8.5 + (r + c) * 1.5  # over Dholakpur A
            else:
                val = 0.0  # over Dholakpur B

            cells.append(create_satellite_cell(
                cell_id=cell_id,
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2) if val is not None else None,
                row_idx=r, col_idx=c,
            ))

    prov = SourceResolutionProvenance(
        source_name="SATELLITE_SYNTHETIC_TEST_FIXTURE",
        source_product="SATELLITE_PRECIPITATION_ESTIMATE",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.50, 82.60, 25.70),
        valid_time=valid_time,
        processing_timestamp=valid_time,
        source_version="1.0.0-test",
    )

    return SourceWeatherGrid(
        variable_name="satellite_precipitation_estimate",
        variable_type=VariableType.PRECIPITATION_ACCUMULATION,
        variable_unit="mm",
        provenance=prov,
        cells=cells,
    )
