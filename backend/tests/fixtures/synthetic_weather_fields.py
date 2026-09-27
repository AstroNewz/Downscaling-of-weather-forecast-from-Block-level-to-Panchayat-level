"""
Deterministic Synthetic Weather Field Fixtures for Spatial Masking Tests
SIH Problem Statement 26074 (Weather Downscaling - Task 2)

Constructs georeferenced synthetic weather grids intersecting imaginary Panchayats A and B:
1. Bimodal Temperature Field (A has ~10°C to 12°C; B has ~25°C to 28°C)
2. Shared-Boundary Straddling Grid (cells intersecting only A, only B, and both A and B)
3. Partial-Overlap Asymmetric Grid (80% inside vs 20% inside)
4. Precipitation Field (Panchayat A = 0.0 mm NO RAIN; Panchayat B = 15.5 mm RAIN; Cell with NaN MISSING)

NOTE: These fixtures are strictly for backend spatial verification tests.
THEY MUST NEVER BE USED AS REAL METEOROLOGICAL FORECAST DATA.
"""
from typing import Dict, List, Optional, Tuple
from shapely.geometry import box, mapping, Polygon

from app.schemas.spatial_masking import (
    SourceGridCell,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)
from tests.fixtures.imaginary_panchayats_fixture import (
    SHAPELY_POLY_A,
    SHAPELY_POLY_B,
)


def create_cell(
    cell_id: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    value: Optional[float] = None,
    row_idx: int = 0,
    col_idx: int = 0,
) -> SourceGridCell:
    """Helper to create a rectangular SourceGridCell."""
    b = box(min_lon, min_lat, max_lon, max_lat)
    return SourceGridCell(
        cell_id=cell_id,
        geometry=mapping(b),
        value=value,
        row_idx=row_idx,
        col_idx=col_idx,
    )


def build_bimodal_temperature_field(
    native_res_km: float = 1.0,
    valid_time: str = "2026-09-27T12:00:00Z"
) -> SourceWeatherGrid:
    """
    Constructs a regular grid across the domain [82.40, 82.60] x [25.00, 25.20].
    Cells purely in A are assigned ~10-12°C.
    Cells purely in B are assigned ~25-28°C.
    Proves that spatial masking on the SAME field isolates A and B independently.
    """
    cells: List[SourceGridCell] = []
    
    # 4 rows x 4 cols regular grid (each cell is 0.05 deg x 0.05 deg)
    lons = [82.40, 82.45, 82.50, 82.55, 82.60]
    lats = [25.00, 25.05, 25.10, 25.15, 25.20]

    for r in range(4):
        for c in range(4):
            min_lon, max_lon = lons[c], lons[c + 1]
            min_lat, max_lat = lats[r], lats[r + 1]
            cell_box = box(min_lon, min_lat, max_lon, max_lat)
            cell_id = f"temp_cell_{r}_{c}"

            # Intersects A or B?
            inter_a = SHAPELY_POLY_A.intersection(cell_box).area
            inter_b = SHAPELY_POLY_B.intersection(cell_box).area

            # Assign synthetic temperature based on true physical geography:
            # - Bottom row (r=0) is entirely in bottom arm of A: 10.0°C to 11.5°C
            # - Column 0 (c=0, r>=1) is in vertical arm of A: 10.5°C to 12.0°C
            # - Columns 1, 2, 3 (r>=1) are inside B: 25.0°C to 28.0°C
            if r == 0:
                val = 10.0 + c * 0.5  # 10.0, 10.5, 11.0, 11.5
            elif c == 0:
                val = 11.0 + r * 0.3  # 11.3, 11.6, 11.9
            else:
                val = 25.0 + (r * 0.8) + (c * 0.4)  # 25.8 to 28.2°C

            cells.append(create_cell(
                cell_id=cell_id,
                min_lon=min_lon, min_lat=min_lat,
                max_lon=max_lon, max_lat=max_lat,
                value=round(val, 2),
                row_idx=r, col_idx=c,
            ))

    prov = SourceResolutionProvenance(
        source_name="SYNTHETIC_BIMODAL_NWP",
        source_product="SURFACE_TEMP_TEST_1KM",
        native_resolution_km=native_res_km,
        processing_resolution_km=native_res_km,
        visualization_resolution_km=0.25,
        crs="EPSG:4326",
        spatial_extent=(82.40, 25.00, 82.60, 25.20),
        valid_time=valid_time,
        processing_timestamp="2026-09-27T00:00:00Z",
        source_version="v1.0-test",
    )

    return SourceWeatherGrid(
        variable_name="temperature_2m",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="°C",
        provenance=prov,
        cells=cells,
    )


def build_shared_boundary_straddling_field() -> SourceWeatherGrid:
    """
    Constructs explicit cells designed to test:
    - Cell 1: entirely inside A
    - Cell 2: entirely inside B
    - Cell 3: straddles the boundary (partially in A, partially in B)
    """
    cells = [
        # Cell 1: Strictly in vertical bar of A [82.41, 82.44] x [25.10, 25.15]
        create_cell("cell_strictly_a", 82.41, 25.10, 82.44, 25.15, value=12.0),
        # Cell 2: Strictly in B [82.48, 82.55] x [25.10, 25.15]
        create_cell("cell_strictly_b", 82.48, 25.10, 82.55, 25.15, value=26.0),
        # Cell 3: Straddles vertical boundary at lon=82.45 [82.43, 82.48] x [25.10, 25.15]
        # Overlap in A = [82.43, 82.45] width 0.02 (40% of cell)
        # Overlap in B = [82.45, 82.48] width 0.03 (60% of cell)
        create_cell("cell_straddles_a_b", 82.43, 25.10, 82.48, 25.15, value=20.0),
    ]

    prov = SourceResolutionProvenance(
        source_name="SYNTHETIC_STRADDLE_TEST",
        source_product="BOUNDARY_OVERLAP_FIELD",
        native_resolution_km=1.0,
        processing_resolution_km=1.0,
        crs="EPSG:4326",
        spatial_extent=(82.41, 25.10, 82.55, 25.15),
        valid_time="2026-09-27T12:00:00Z",
        processing_timestamp="2026-09-27T00:00:00Z",
    )

    return SourceWeatherGrid(
        variable_name="temperature_2m",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="°C",
        provenance=prov,
        cells=cells,
    )


def build_partial_cell_asymmetric_field() -> SourceWeatherGrid:
    """
    Constructs a field where:
    - Cell 1 has 80% overlap inside Panchayat A (value = 10.0°C)
    - Cell 2 has 20% overlap inside Panchayat A (value = 20.0°C)
    The area-weighted mean must equal: (0.80 * 10 + 0.20 * 20) / (0.80 + 0.20) = 12.0°C.
    An unweighted simple average would incorrectly return (10 + 20) / 2 = 15.0°C.
    """
    # Panchayat A boundary at west edge is lon=82.40.
    # Cell 1: lon [82.38, 82.48] x [25.01, 25.03]. Width = 0.10.
    # Inside A: [82.40, 82.48] (width 0.08 = 80%). Value = 10.0.
    cell1 = create_cell("cell_80pct_in_a", 82.38, 25.01, 82.48, 25.03, value=10.0)

    # Cell 2: lon [82.38, 82.48] x [25.03, 25.05]. But position it:
    # Cell 2: lon [82.38, 82.48]... to get 20%:
    # Inside A: [82.40, 82.42] (width 0.02 = 20%), outside: [82.32, 82.40] (width 0.08).
    cell2 = create_cell("cell_20pct_in_a", 82.32, 25.03, 82.42, 25.05, value=20.0)

    prov = SourceResolutionProvenance(
        source_name="SYNTHETIC_PARTIAL_OVERLAP",
        source_product="PARTIAL_WEIGHTING_VERIFIER",
        native_resolution_km=1.0,
        processing_resolution_km=1.0,
        crs="EPSG:4326",
        spatial_extent=(82.32, 25.01, 82.48, 25.05),
        valid_time="2026-09-27T12:00:00Z",
        processing_timestamp="2026-09-27T00:00:00Z",
    )

    return SourceWeatherGrid(
        variable_name="temperature_2m",
        variable_type=VariableType.CONTINUOUS,
        variable_unit="°C",
        provenance=prov,
        cells=[cell1, cell2],
    )


def build_precipitation_field_with_zeros_and_nans() -> SourceWeatherGrid:
    """
    Constructs a precipitation grid specifically proving:
    - 0.0 mm rainfall in A (explicitly NO RAIN: is_rain_detected=False, rain_area_fraction=0.0)
    - 15.5 mm rainfall in B (RAIN: is_rain_detected=True, rain_area_fraction=1.0)
    - NaN cell in B (MISSING DATA: excluded from weights, does NOT become zero!)
    """
    cells = [
        # Cell in A with 0.0 mm (valid measurement of no precipitation)
        create_cell("precip_a_zero", 82.41, 25.10, 82.44, 25.15, value=0.0),
        # Cell in B with 15.5 mm (valid measurement of rain)
        create_cell("precip_b_rain", 82.48, 25.10, 82.52, 25.15, value=15.5),
        # Cell in B with None/NaN (missing measurement)
        create_cell("precip_b_missing", 82.53, 25.10, 82.57, 25.15, value=None),
    ]

    prov = SourceResolutionProvenance(
        source_name="SYNTHETIC_PRECIPITATION_QC",
        source_product="ACCUMULATED_RAINFALL_24H",
        native_resolution_km=4.0,
        processing_resolution_km=1.0,
        crs="EPSG:4326",
        spatial_extent=(82.41, 25.10, 82.57, 25.15),
        valid_time="2026-09-27T12:00:00Z",
        processing_timestamp="2026-09-27T00:00:00Z",
    )

    return SourceWeatherGrid(
        variable_name="precipitation_24h",
        variable_type=VariableType.PRECIPITATION_ACCUMULATION,
        variable_unit="mm",
        provenance=prov,
        cells=cells,
    )
