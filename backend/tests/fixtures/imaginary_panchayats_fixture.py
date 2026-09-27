"""
Deterministic Neighbouring-Panchayat Imaginary Test Fixture
SIH Problem Statement 26074 (Panchayat Boundary Service - Task 1)

Defines two adjacent imaginary Panchayats (A and B) inside an imaginary Block.
PURPOSE:
- Prove exact Point-in-Polygon containment:
    * coordinate inside A -> resolves to Panchayat A
    * coordinate inside B -> resolves to Panchayat B
- Prove nearest-centroid assignment is NEVER used:
    * A point inside an asymmetric arm of A is closer to Centroid B than Centroid A,
      yet correctly resolves to Panchayat A.
- Prove deterministic shared-boundary edge handling:
    * Coordinates on the shared boundary segment or within numerical tolerance
      return ON_BOUNDARY with candidate IDs [A, B].
- Coordinate outside both returns OUTSIDE_REGISTERED_PANCHAYATS.

NOTE: These synthetic geometries are strictly for backend verification testing
and MUST NEVER be used as operational weather or administrative data.
"""
from typing import Any, Dict, List
from shapely.geometry import Polygon, mapping

from app.schemas.panchayat_boundary import PanchayatBoundaryRecord

# =========================================================================
# Geometry Specifications — Imaginary Panchayats (lat 25.00–25.20)
# =========================================================================
# Panchayat A is an L-shaped polygon:
# - Bottom bar: lon [82.40, 82.60], lat [25.00, 25.05]
# - Vertical bar: lon [82.40, 82.45], lat [25.05, 25.20]
COORDS_PANCHAYAT_A = [
    (82.40, 25.00),
    (82.60, 25.00),
    (82.60, 25.05),
    (82.45, 25.05),
    (82.45, 25.20),
    (82.40, 25.20),
    (82.40, 25.00),
]

# Panchayat B is a rectangular polygon adjacent to A:
# - B sits directly above the bottom bar and to the right of the vertical bar:
#   lon [82.45, 82.60], lat [25.05, 25.20]
COORDS_PANCHAYAT_B = [
    (82.45, 25.05),
    (82.60, 25.05),
    (82.60, 25.20),
    (82.45, 25.20),
    (82.45, 25.05),
]

# Shared boundary segments:
# 1. Horizontal segment: (82.45, 25.05) to (82.60, 25.05)
# 2. Vertical segment: (82.45, 25.05) to (82.45, 25.20)

SHAPELY_POLY_A = Polygon(COORDS_PANCHAYAT_A)
SHAPELY_POLY_B = Polygon(COORDS_PANCHAYAT_B)

CENTROID_A = (round(SHAPELY_POLY_A.centroid.y, 6), round(SHAPELY_POLY_A.centroid.x, 6))
CENTROID_B = (round(SHAPELY_POLY_B.centroid.y, 6), round(SHAPELY_POLY_B.centroid.x, 6))


# =========================================================================
# Geometry Specifications — Dholakpur Panchayats (lat 25.50–25.70)
# =========================================================================
# IMPORTANT: Dholakpur geometries are deliberately shifted +0.50 degrees
# north relative to the IMAGINARY set so they occupy a completely
# non-overlapping region of the coordinate plane.  Without this separation,
# loading both sets into the same boundary_registry would produce
# OVERLAPPING_POLYGONS for any point that falls inside shared geometry.
#
# Dholakpur A: L-shaped polygon
# - Bottom bar: lon [82.40, 82.60], lat [25.50, 25.55]
# - Vertical bar: lon [82.40, 82.45], lat [25.55, 25.70]
COORDS_DHOLAKPUR_A = [
    (82.40, 25.50),
    (82.60, 25.50),
    (82.60, 25.55),
    (82.45, 25.55),
    (82.45, 25.70),
    (82.40, 25.70),
    (82.40, 25.50),
]

# Dholakpur B: rectangular polygon adjacent to Dholakpur A.
# lon [82.45, 82.60], lat [25.55, 25.70]
COORDS_DHOLAKPUR_B = [
    (82.45, 25.55),
    (82.60, 25.55),
    (82.60, 25.70),
    (82.45, 25.70),
    (82.45, 25.55),
]

SHAPELY_DHOLAKPUR_A = Polygon(COORDS_DHOLAKPUR_A)
SHAPELY_DHOLAKPUR_B = Polygon(COORDS_DHOLAKPUR_B)

CENTROID_DHOLAKPUR_A = (round(SHAPELY_DHOLAKPUR_A.centroid.y, 6), round(SHAPELY_DHOLAKPUR_A.centroid.x, 6))
CENTROID_DHOLAKPUR_B = (round(SHAPELY_DHOLAKPUR_B.centroid.y, 6), round(SHAPELY_DHOLAKPUR_B.centroid.x, 6))

# Prescribed test points for Dholakpur polygons
# 1. Strictly inside Dholakpur A vertical bar: lon 82.42 in [82.40,82.45], lat 25.60 in [25.55,25.70]
DHOLAKPUR_POINT_INSIDE_A = {"lat": 25.60, "lon": 82.42}
# 2. Strictly inside Dholakpur B: lon 82.52 in [82.45,82.60], lat 25.62 in [25.55,25.70]
DHOLAKPUR_POINT_INSIDE_B = {"lat": 25.62, "lon": 82.52}
# 3. Inside A bottom bar, closer to Centroid B than Centroid A (anti-centroid proof)
DHOLAKPUR_POINT_INSIDE_A_CLOSER_TO_B = {"lat": 25.54, "lon": 82.58}
# 4. Strictly outside both Dholakpur polygons
DHOLAKPUR_POINT_OUTSIDE = {"lat": 25.80, "lon": 82.70}


def get_imaginary_panchayat_records() -> List[PanchayatBoundaryRecord]:
    """Returns canonical records for imaginary Panchayats A and B."""
    import pyproj

    geod = pyproj.Geod(ellps="WGS84")
    area_a = round(abs(float(geod.geometry_area_perimeter(SHAPELY_POLY_A)[0])) / 1e6, 4)
    area_b = round(abs(float(geod.geometry_area_perimeter(SHAPELY_POLY_B)[0])) / 1e6, 4)

    rec_a = PanchayatBoundaryRecord(
        panchayat_id="IMAGINARY_PANCHAYAT_A",
        lgd_code="LGD_IMAGINARY_A_99901",
        panchayat_name="Imaginary Gram Panchayat A",
        block="Imaginary Demonstration Block",
        district="Imaginary District",
        state="Uttar Pradesh",
        geometry=mapping(SHAPELY_POLY_A),
        centroid_lat=CENTROID_A[0],
        centroid_lon=CENTROID_A[1],
        area_sq_km=area_a,
        geometry_source="SYNTHETIC_TEST_FIXTURE_SIH26074",
        geometry_version="1.0.0-test",
        geometry_status="TEST_FIXTURE_ONLY",
        is_verified=False,
        ingestion_timestamp="2026-09-27T00:00:00Z",
        properties={"test_case": "neighbouring_polygons_l_shape"},
    )

    rec_b = PanchayatBoundaryRecord(
        panchayat_id="IMAGINARY_PANCHAYAT_B",
        lgd_code="LGD_IMAGINARY_B_99902",
        panchayat_name="Imaginary Gram Panchayat B",
        block="Imaginary Demonstration Block",
        district="Imaginary District",
        state="Uttar Pradesh",
        geometry=mapping(SHAPELY_POLY_B),
        centroid_lat=CENTROID_B[0],
        centroid_lon=CENTROID_B[1],
        area_sq_km=area_b,
        geometry_source="SYNTHETIC_TEST_FIXTURE_SIH26074",
        geometry_version="1.0.0-test",
        geometry_status="TEST_FIXTURE_ONLY",
        is_verified=False,
        ingestion_timestamp="2026-09-27T00:00:00Z",
        properties={"test_case": "neighbouring_polygons_adjacent_rect"},
    )

    return [rec_a, rec_b] + get_dholakpur_panchayat_records()


def get_dholakpur_panchayat_records() -> List[PanchayatBoundaryRecord]:
    """Returns canonical records for Dholakpur Block Panchayats A and B (SIH PS 26074 - Task 4).

    Dholakpur polygons are at lat [25.50–25.70] — DISTINCT from the IMAGINARY
    set at lat [25.00–25.20] — so no polygon overlap occurs when both sets are
    loaded into the same boundary_registry.
    """
    import pyproj

    geod = pyproj.Geod(ellps="WGS84")
    area_a = round(abs(float(geod.geometry_area_perimeter(SHAPELY_DHOLAKPUR_A)[0])) / 1e6, 4)
    area_b = round(abs(float(geod.geometry_area_perimeter(SHAPELY_DHOLAKPUR_B)[0])) / 1e6, 4)

    rec_a = PanchayatBoundaryRecord(
        panchayat_id="DHOLAKPUR_PANCHAYAT_A",
        lgd_code="LGD_DHOLAKPUR_A_99901",
        panchayat_name="Dholakpur Panchayat A",
        block="Dholakpur Block",
        district="Dholakpur",
        state="Uttar Pradesh",
        geometry=mapping(SHAPELY_DHOLAKPUR_A),
        centroid_lat=CENTROID_DHOLAKPUR_A[0],
        centroid_lon=CENTROID_DHOLAKPUR_A[1],
        area_sq_km=area_a,
        geometry_source="SYNTHETIC_TEST_FIXTURE_SIH26074",
        geometry_version="1.0.0-test",
        geometry_status="TEST_FIXTURE_ONLY",
        is_verified=True,
        ingestion_timestamp="2026-09-27T00:00:00Z",
        properties={"block_name": "Dholakpur Block", "test_case": "dholakpur_adjacent_a"},
    )

    rec_b = PanchayatBoundaryRecord(
        panchayat_id="DHOLAKPUR_PANCHAYAT_B",
        lgd_code="LGD_DHOLAKPUR_B_99902",
        panchayat_name="Dholakpur Panchayat B",
        block="Dholakpur Block",
        district="Dholakpur",
        state="Uttar Pradesh",
        geometry=mapping(SHAPELY_DHOLAKPUR_B),
        centroid_lat=CENTROID_DHOLAKPUR_B[0],
        centroid_lon=CENTROID_DHOLAKPUR_B[1],
        area_sq_km=area_b,
        geometry_source="SYNTHETIC_TEST_FIXTURE_SIH26074",
        geometry_version="1.0.0-test",
        geometry_status="TEST_FIXTURE_ONLY",
        is_verified=True,
        ingestion_timestamp="2026-09-27T00:00:00Z",
        properties={"block_name": "Dholakpur Block", "test_case": "dholakpur_adjacent_b"},
    )

    return [rec_a, rec_b]


def get_imaginary_panchayat_geojson() -> Dict[str, Any]:
    """Returns standard GeoJSON FeatureCollection of the imaginary test Panchayats."""
    records = get_imaginary_panchayat_records()
    features = []
    for r in records:
        features.append({
            "type": "Feature",
            "geometry": r.geometry,
            "properties": {
                "panchayat_id": r.panchayat_id,
                "lgd_code": r.lgd_code,
                "panchayat_name": r.panchayat_name,
                "block": r.block,
                "district": r.district,
                "state": r.state,
                "centroid_lat": r.centroid_lat,
                "centroid_lon": r.centroid_lon,
                "area_sq_km": r.area_sq_km,
                "geometry_source": r.geometry_source,
                "geometry_version": r.geometry_version,
                "geometry_status": r.geometry_status,
                "is_verified": r.is_verified,
                "ingestion_timestamp": r.ingestion_timestamp,
            }
        })
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }


# =========================================================================
# Prescribed Deterministic Test Points — Imaginary Panchayats
# =========================================================================
# 1. Point strictly inside A (vertical bar):
POINT_STRICTLY_INSIDE_A = {"lat": 25.10, "lon": 82.42}

# 2. Point strictly inside B:
POINT_STRICTLY_INSIDE_B = {"lat": 25.12, "lon": 82.52}

# 3. Point inside A that is CLOSER to Centroid B than to Centroid A:
#    (Located at lon=82.58, lat=25.04 in the eastern tip of bottom bar of A)
POINT_INSIDE_A_CLOSER_TO_CENTROID_B = {"lat": 25.04, "lon": 82.58}

# 4. Point exactly on the shared horizontal boundary:
POINT_EXACTLY_ON_SHARED_BOUNDARY = {"lat": 25.05, "lon": 82.50}

# 5. Point within 1e-5 degrees of shared horizontal boundary:
POINT_NEAR_SHARED_BOUNDARY = {"lat": 25.050003, "lon": 82.50}

# 6. Point strictly outside both Panchayats:
POINT_OUTSIDE_BOTH = {"lat": 25.30, "lon": 82.70}
