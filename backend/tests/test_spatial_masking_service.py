"""
Tests for Panchayat Spatial Masking Service
SIH Problem Statement 26074 (Weather Downscaling - Task 2)

Verifies:
1. Panchayat A-only and B-only independent spatial masking
2. Adjacent Panchayat separation on the SAME source weather field
3. Shared-boundary cell straddling (one cell contributes to both A and B with respective weights)
4. Partial-cell fractional overlap weighting (80% vs 20% vs simple mean)
5. Missing-value (NaN) exclusion from weights
6. Zero precipitation (0.0 mm) vs missing precipitation (NaN) semantic distinction
7. Coverage quality tier evaluation
8. Empty grid fail-closed safety
9. Invalid CRS fail-closed safety
10. Invalid / degenerate geometry fail-closed safety
11. No intersecting cells fail-closed safety
12. Unverified geometry fail-closed policy
13. Deterministic repeated execution (100 runs)
14. Provenance preservation: native vs processing vs visualization resolution
"""
import math
import pytest
from shapely.geometry import Polygon, LineString, mapping

from app.gis.boundary_registry import PanchayatBoundaryRegistry
from app.gis.spatial_masking import (
    SpatialMaskingService,
    extract_panchayat_spatial_features,
)
from app.schemas.spatial_masking import (
    CoverageQuality,
    SourceGridCell,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)
from tests.fixtures.imaginary_panchayats_fixture import (
    get_imaginary_panchayat_records,
    SHAPELY_POLY_A,
    SHAPELY_POLY_B,
)
from tests.fixtures.synthetic_weather_fields import (
    build_bimodal_temperature_field,
    build_shared_boundary_straddling_field,
    build_partial_cell_asymmetric_field,
    build_precipitation_field_with_zeros_and_nans,
    create_cell,
)


@pytest.fixture
def masking_service_with_imaginary_panchayats():
    """Provides a SpatialMaskingService preloaded with imaginary Panchayats A and B."""
    reg = PanchayatBoundaryRegistry()
    records = get_imaginary_panchayat_records()
    reg.register_all(records)
    svc = SpatialMaskingService(registry=reg)
    return svc, reg


# =========================================================================
# 1. Adjacent Panchayat Separation on the SAME Source Field
# =========================================================================

def test_adjacent_panchayat_independent_separation(masking_service_with_imaginary_panchayats):
    """
    CRITICAL SUCCESS CRITERION:
    Given the identical bimodal temperature grid:
    - Panchayat A receives statistics derived ONLY from cells intersecting A (~10-12°C).
    - Panchayat B receives statistics derived ONLY from cells intersecting B (~25-28°C).
    - Proves that administrative masking isolates adjacent Panchayats with zero crosstalk.
    """
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field(native_res_km=1.0)

    # 1. Extract for Panchayat A
    res_a = svc.extract_panchayat_spatial_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        source_grid=grid,
    )
    assert res_a.status == "SUCCESS"
    assert res_a.success is True
    assert res_a.panchayat_id == "IMAGINARY_PANCHAYAT_A"
    assert res_a.cells_intersecting > 0
    # Values in A must strictly be within [10.0, 12.0]
    assert 10.0 <= res_a.features["weighted_mean"] <= 12.0
    assert 10.0 <= res_a.features["min"] <= 12.0
    assert 10.0 <= res_a.features["max"] <= 12.0

    # 2. Extract for Panchayat B
    res_b = svc.extract_panchayat_spatial_features(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        source_grid=grid,
    )
    assert res_b.status == "SUCCESS"
    assert res_b.success is True
    assert res_b.panchayat_id == "IMAGINARY_PANCHAYAT_B"
    assert res_b.cells_intersecting > 0
    # Values in B must strictly be within [25.0, 29.0]
    assert 25.0 <= res_b.features["weighted_mean"] <= 29.0
    assert 25.0 <= res_b.features["min"] <= 29.0
    assert 25.0 <= res_b.features["max"] <= 29.0


    # 3. Independent separation verification
    assert res_b.features["weighted_mean"] - res_a.features["weighted_mean"] > 14.0, (
        "FAIL: Panchayat A and B did not separate into distinct temperature domains!"
    )


# =========================================================================
# 2. Shared-Boundary Straddling Grid Cell Handling
# =========================================================================

def test_shared_boundary_cell_straddling(masking_service_with_imaginary_panchayats):
    """
    A single source cell can intersect both A and B across their shared boundary.
    - The cell must be counted in both A and B extractions.
    - The overlap weights must match the respective geometric intersection fractions.
    """
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_shared_boundary_straddling_field()

    res_a = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    res_b = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_B", source_grid=grid)

    assert res_a.status == "SUCCESS"
    assert res_b.status == "SUCCESS"

    # Find the straddling cell in both
    cell_a = next((c for c in res_a.cell_intersections if c.cell_id == "cell_straddles_a_b"), None)
    cell_b = next((c for c in res_b.cell_intersections if c.cell_id == "cell_straddles_a_b"), None)

    assert cell_a is not None, "Straddling cell was not captured in Panchayat A intersection!"
    assert cell_b is not None, "Straddling cell was not captured in Panchayat B intersection!"

    # Cell 3 width = 0.05. Lon [82.43, 82.48]. Boundary is at lon=82.45.
    # In A: [82.43, 82.45] width 0.02 (40%)
    # In B: [82.45, 82.48] width 0.03 (60%)
    assert cell_a.overlap_fraction_of_cell == pytest.approx(0.40, abs=0.02)
    assert cell_b.overlap_fraction_of_cell == pytest.approx(0.60, abs=0.02)
    # Combined coverage of that cell is 100%
    assert (cell_a.overlap_fraction_of_cell + cell_b.overlap_fraction_of_cell) == pytest.approx(1.0, abs=0.01)


# =========================================================================
# 3. Partial-Cell Fractional Overlap Weighting
# =========================================================================

def test_partial_cell_fractional_overlap_weighting(masking_service_with_imaginary_panchayats):
    """
    Verifies that area-weighted aggregation strictly accounts for fractional cell overlap.
    - Cell 1 (value 10.0°C) is 80% inside A.
    - Cell 2 (value 20.0°C) is 20% inside A.
    - True area-weighted mean = (0.80*10 + 0.20*20) / (0.80 + 0.20) = 12.0°C.
    - Unweighted simple mean = (10 + 20) / 2 = 15.0°C.
    - Masking service MUST return 12.0°C for weighted_mean and 15.0°C for unweighted mean.
    """
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_partial_cell_asymmetric_field()

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    assert res.status == "SUCCESS"

    weighted_mean = res.features["weighted_mean"]
    simple_mean = res.features["mean"]

    assert weighted_mean == pytest.approx(12.0, abs=0.15)
    assert simple_mean == pytest.approx(15.0, abs=0.01)
    assert weighted_mean < simple_mean, "Weighted mean must reflect the 80% weight of cell 1!"


# =========================================================================
# 4. Precipitation Semantics & Zero vs NaN Distinction
# =========================================================================

def test_precipitation_zero_vs_missing_nan_distinction(masking_service_with_imaginary_panchayats):
    """
    CRITICAL METEOROLOGICAL SEMANTIC TEST:
    - 0.0 mm rainfall represents verified absence of rain (NOT missing data).
    - NaN/None represents missing data (must be excluded from weights, NOT treated as 0.0 mm).
    - Tests Panchayat A (all 0.0 mm) -> is_rain_detected = False, rain_area_fraction = 0.0.
    - Tests Panchayat B (15.5 mm + NaN) -> is_rain_detected = True, weighted_mean = 15.5 mm (NaN excluded).
    """
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_precipitation_field_with_zeros_and_nans()

    # Panchayat A: 0.0 mm verified no rain
    res_a = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    assert res_a.status == "SUCCESS"
    assert res_a.features["weighted_mean_amount_mm"] == 0.0
    assert res_a.features["is_rain_detected"] is False
    assert res_a.features["rain_area_fraction"] == 0.0

    # Panchayat B: 15.5 mm rain + NaN missing cell
    res_b = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_B", source_grid=grid)
    assert res_b.status == "SUCCESS"
    assert res_b.features["is_rain_detected"] is True
    assert res_b.features["rain_area_fraction"] == pytest.approx(1.0, abs=0.01)
    # NaN cell must be excluded: weighted mean must remain 15.5 mm, NOT diluted to 7.75 mm!
    assert res_b.features["weighted_mean_amount_mm"] == pytest.approx(15.5, abs=0.01)
    assert res_b.valid_cells_intersecting == 1
    assert res_b.cells_intersecting == 2


# =========================================================================
# 5. Coverage Quality Tier Assessment
# =========================================================================

def test_coverage_quality_tiers(masking_service_with_imaginary_panchayats):
    """Verifies coverage quality classification based on spatial fraction."""
    svc, _ = masking_service_with_imaginary_panchayats
    full_grid = build_bimodal_temperature_field()

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_B", source_grid=full_grid)
    assert res.coverage_fraction >= 0.95
    assert res.coverage_quality == CoverageQuality.COMPLETE


# =========================================================================
# 6. Fail-Closed Safety Behaviors
# =========================================================================

def test_empty_grid_fails_closed(masking_service_with_imaginary_panchayats):
    """An empty source grid fails closed with status EMPTY_SOURCE_GRID."""
    svc, _ = masking_service_with_imaginary_panchayats
    empty_prov = SourceResolutionProvenance(
        source_name="EMPTY_SOURCE", native_resolution_km=1.0, processing_resolution_km=1.0,
        crs="EPSG:4326", valid_time="2026-09-27T00:00:00Z", processing_timestamp="2026-09-27T00:00:00Z"
    )
    empty_grid = SourceWeatherGrid(
        variable_name="temperature_2m", variable_unit="°C", provenance=empty_prov, cells=[]
    )
    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=empty_grid)
    assert res.status == "EMPTY_SOURCE_GRID"
    assert res.success is False


def test_invalid_crs_fails_closed(masking_service_with_imaginary_panchayats):
    """Non-EPSG:4326 CRS fails closed."""
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field()
    grid.provenance.crs = "EPSG:3857"  # Web Mercator prohibited for spatial extraction

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    assert res.status == "INVALID_CRS"
    assert res.success is False


def test_invalid_geometry_fails_closed(masking_service_with_imaginary_panchayats):
    """Non-areal geometry fails closed."""
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field()

    line_geom = LineString([(82.4, 25.0), (82.5, 25.1)])
    res = svc.extract_panchayat_spatial_features(
        panchayat_geometry=mapping(line_geom),
        source_grid=grid,
    )
    assert res.status == "INVALID_GEOMETRY"
    assert res.success is False


def test_no_intersecting_cells_fails_closed(masking_service_with_imaginary_panchayats):
    """Grid located completely outside the Panchayat returns NO_INTERSECTING_CELLS."""
    svc, _ = masking_service_with_imaginary_panchayats
    # Cell far to the north [82.4, 27.0]
    cell_far = create_cell("cell_far", 82.4, 27.0, 82.5, 27.1, value=15.0)
    prov = SourceResolutionProvenance(
        source_name="FAR_GRID", native_resolution_km=1.0, processing_resolution_km=1.0,
        crs="EPSG:4326", valid_time="2026-09-27T00:00:00Z", processing_timestamp="2026-09-27T00:00:00Z"
    )
    far_grid = SourceWeatherGrid(
        variable_name="temperature_2m", variable_unit="°C", provenance=prov, cells=[cell_far]
    )

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=far_grid)
    assert res.status == "NO_INTERSECTING_CELLS"
    assert res.coverage_quality == CoverageQuality.ZERO_COVERAGE
    assert res.success is False


def test_all_values_missing_fails_closed(masking_service_with_imaginary_panchayats):
    """When all intersecting cells contain NaN, service fails closed with ALL_VALUES_MISSING."""
    svc, _ = masking_service_with_imaginary_panchayats
    cell_nan = create_cell("cell_nan", 82.41, 25.10, 82.44, 25.15, value=None)
    prov = SourceResolutionProvenance(
        source_name="NAN_GRID", native_resolution_km=1.0, processing_resolution_km=1.0,
        crs="EPSG:4326", valid_time="2026-09-27T00:00:00Z", processing_timestamp="2026-09-27T00:00:00Z"
    )
    nan_grid = SourceWeatherGrid(
        variable_name="temperature_2m", variable_unit="°C", provenance=prov, cells=[cell_nan]
    )

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=nan_grid)
    assert res.status == "ALL_VALUES_MISSING"
    assert res.valid_cells_intersecting == 0
    assert res.success is False


def test_unverified_geometry_policy_enforcement(masking_service_with_imaginary_panchayats):
    """When require_verified=True, unverified boundary fails closed."""
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field()

    # Imaginary Panchayats are is_verified=False
    res = svc.extract_panchayat_spatial_features(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        source_grid=grid,
        require_verified=True,
    )
    assert res.status == "UNVERIFIED_GEOMETRY"
    assert res.success is False


# =========================================================================
# 7. Determinism and Repeatability
# =========================================================================

def test_spatial_masking_repeatability_100_runs(masking_service_with_imaginary_panchayats):
    """Running 100 spatial extractions on the identical grid returns identical statistics."""
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field()

    first = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    for _ in range(100):
        current = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
        assert current.features == first.features
        assert current.coverage_fraction == first.coverage_fraction


# =========================================================================
# 8. Resolution Provenance Preservation
# =========================================================================

def test_provenance_and_resolution_preservation(masking_service_with_imaginary_panchayats):
    """
    Verifies that native resolution (e.g. 1.0 km) is preserved in provenance,
    distinguishing native vs processing vs visualization resolutions.
    """
    svc, _ = masking_service_with_imaginary_panchayats
    grid = build_bimodal_temperature_field(native_res_km=1.0)

    res = svc.extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_A", source_grid=grid)
    assert res.provenance.native_resolution_km == 1.0
    assert res.provenance.processing_resolution_km == 1.0
    assert res.provenance.visualization_resolution_km == 0.25
    assert "does NOT synthesize higher meteorological resolution" in res.provenance.resolution_disclaimer


# =========================================================================
# 9. Top-Level Programmatic Helper Function
# =========================================================================

def test_programmatic_helper_function(masking_service_with_imaginary_panchayats):
    """Tests the convenience export extract_panchayat_spatial_features()."""
    svc, reg = masking_service_with_imaginary_panchayats
    from app.gis.spatial_masking import spatial_masking_service

    orig_reg = spatial_masking_service.registry
    try:
        spatial_masking_service.registry = reg
        grid = build_bimodal_temperature_field()
        res = extract_panchayat_spatial_features(panchayat_id="IMAGINARY_PANCHAYAT_B", source_grid=grid)
        assert res.status == "SUCCESS"
        assert res.panchayat_id == "IMAGINARY_PANCHAYAT_B"
    finally:
        spatial_masking_service.registry = orig_reg
