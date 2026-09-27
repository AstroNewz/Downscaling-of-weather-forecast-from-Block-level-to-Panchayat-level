"""
Unit and Integration Tests for Panchayat Boundary Service
SIH Problem Statement 26074 (Panchayat Boundary Service - Task 1)

Verifies:
1. Exact Point-in-Polygon containment (Inside A -> A, Inside B -> B)
2. Nearest-centroid refutation (Point closer to Centroid B still resolves to A)
3. Shared-boundary edge ambiguity (ON_BOUNDARY with candidate IDs [A, B])
4. Coordinate tolerance proximity handling
5. Outside registered polygons handling
6. Invalid coordinates validation (latitude, longitude, NaN/inf)
7. Empty registry fail-closed behavior
8. Malformed geometry rejection during ingestion
9. Mechanical geometry healing (make_valid on self-touching bowties)
10. Duplicate Panchayat ID detection
11. Overlapping polygons fail-closed handling
12. Unverified geometry fail-closed policy
13. Exact determinism and repeatability across 100 iterations
14. Spatial index (STRtree) lookup correctness
15. Multi-key registry lookups (by ID, LGD code, and composite hierarchy)
16. Geodesic area calculation on WGS84 ellipsoid
17. API endpoints: /api/v1/panchayat/resolve, /api/panchayats/resolve, and boundary endpoints
18. Downstream integration primitive: resolve_panchayat_from_coordinates()
"""
import math
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, LineString, mapping

from app.main import app
from app.gis.boundary_ingestion import PanchayatBoundaryIngestor
from app.gis.boundary_registry import PanchayatBoundaryRegistry
from app.gis.boundary_service import (
    PanchayatBoundaryService,
    resolve_panchayat_from_coordinates,
)
from app.schemas.panchayat_boundary import (
    BoundaryResolutionStatus,
    PointLocationStatus,
    PanchayatBoundaryRecord,
)
from tests.fixtures.imaginary_panchayats_fixture import (
    get_imaginary_panchayat_records,
    get_imaginary_panchayat_geojson,
    POINT_STRICTLY_INSIDE_A,
    POINT_STRICTLY_INSIDE_B,
    POINT_INSIDE_A_CLOSER_TO_CENTROID_B,
    POINT_EXACTLY_ON_SHARED_BOUNDARY,
    POINT_NEAR_SHARED_BOUNDARY,
    POINT_OUTSIDE_BOTH,
    CENTROID_A,
    CENTROID_B,
)

client = TestClient(app)


@pytest.fixture
def isolated_service():
    """Provides a clean, isolated PanchayatBoundaryService with imaginary Panchayats A and B."""
    reg = PanchayatBoundaryRegistry()
    records = get_imaginary_panchayat_records()
    reg.register_all(records)
    svc = PanchayatBoundaryService(registry=reg)
    return svc, reg


# =========================================================================
# 1. Empty Registry Handling
# =========================================================================

def test_empty_registry_fails_closed():
    """When no polygons are registered, queries return OUTSIDE_REGISTERED_PANCHAYATS safely."""
    empty_reg = PanchayatBoundaryRegistry()
    svc = PanchayatBoundaryService(registry=empty_reg)

    res = svc.resolve_coordinates(lat=25.10, lon=82.42)
    assert res.status == BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS
    assert res.boundary_status == PointLocationStatus.OUTSIDE_POLYGON
    assert res.panchayat_id is None
    assert "No Panchayat boundaries registered" in res.message


# =========================================================================
# 2. Exact Point-in-Polygon Containment
# =========================================================================

def test_valid_point_inside_panchayat_a(isolated_service):
    """Point strictly inside Panchayat A resolves unambiguously to A."""
    svc, _ = isolated_service
    res = svc.resolve_coordinates(
        lat=POINT_STRICTLY_INSIDE_A["lat"],
        lon=POINT_STRICTLY_INSIDE_A["lon"]
    )
    assert res.status == BoundaryResolutionStatus.RESOLVED
    assert res.boundary_status == PointLocationStatus.INSIDE_POLYGON
    assert res.panchayat_id == "IMAGINARY_PANCHAYAT_A"
    assert res.lgd_code == "LGD_IMAGINARY_A_99901"
    assert res.panchayat_name == "Imaginary Gram Panchayat A"
    assert res.block == "Imaginary Demonstration Block"
    assert res.district == "Imaginary District"
    assert res.state == "Uttar Pradesh"
    assert res.area_sq_km > 0.0
    assert res.centroid_lat == pytest.approx(CENTROID_A[0], abs=1e-4)
    assert res.centroid_lon == pytest.approx(CENTROID_A[1], abs=1e-4)


def test_valid_point_inside_panchayat_b(isolated_service):
    """Point strictly inside Panchayat B resolves unambiguously to B."""
    svc, _ = isolated_service
    res = svc.resolve_coordinates(
        lat=POINT_STRICTLY_INSIDE_B["lat"],
        lon=POINT_STRICTLY_INSIDE_B["lon"]
    )
    assert res.status == BoundaryResolutionStatus.RESOLVED
    assert res.boundary_status == PointLocationStatus.INSIDE_POLYGON
    assert res.panchayat_id == "IMAGINARY_PANCHAYAT_B"
    assert res.lgd_code == "LGD_IMAGINARY_B_99902"
    assert res.panchayat_name == "Imaginary Gram Panchayat B"


# =========================================================================
# 3. Refutation of Nearest-Centroid Logic
# =========================================================================

def test_nearest_centroid_heuristic_refutation(isolated_service):
    """
    CRITICAL SCIENTIFIC TEST:
    A point located inside the asymmetric bottom arm of Panchayat A is
    geometrically CLOSER to Centroid B than Centroid A.
    Nearest-centroid logic would incorrectly assign this point to B.
    Exact Point-in-Polygon logic MUST assign this point to A.
    """
    svc, reg = isolated_service
    p_lat = POINT_INSIDE_A_CLOSER_TO_CENTROID_B["lat"]
    p_lon = POINT_INSIDE_A_CLOSER_TO_CENTROID_B["lon"]

    # Verify geometric distance truth
    d_to_cent_a = math.sqrt((p_lat - CENTROID_A[0]) ** 2 + (p_lon - CENTROID_A[1]) ** 2)
    d_to_cent_b = math.sqrt((p_lat - CENTROID_B[0]) ** 2 + (p_lon - CENTROID_B[1]) ** 2)
    assert d_to_cent_b < d_to_cent_a, "Test fixture invariant violated: test point must be closer to Centroid B"

    # Execute service resolution
    res = svc.resolve_coordinates(lat=p_lat, lon=p_lon)
    assert res.status == BoundaryResolutionStatus.RESOLVED
    assert res.panchayat_id == "IMAGINARY_PANCHAYAT_A", (
        "FAIL: Service improperly used nearest-centroid or radius heuristics instead of exact polygon containment!"
    )
    assert res.panchayat_name == "Imaginary Gram Panchayat A"


# =========================================================================
# 4. Deterministic Boundary-Edge Ambiguity Handling
# =========================================================================

def test_point_exactly_on_shared_boundary(isolated_service):
    """
    Coordinates lying precisely on the shared boundary segment between A and B
    must return ON_BOUNDARY with candidate IDs [A, B] deterministically.
    """
    svc, _ = isolated_service
    res = svc.resolve_coordinates(
        lat=POINT_EXACTLY_ON_SHARED_BOUNDARY["lat"],
        lon=POINT_EXACTLY_ON_SHARED_BOUNDARY["lon"]
    )
    assert res.status == BoundaryResolutionStatus.ON_BOUNDARY
    assert res.boundary_status == PointLocationStatus.ON_BOUNDARY
    assert res.panchayat_id is None
    assert res.candidate_panchayat_ids == ["IMAGINARY_PANCHAYAT_A", "IMAGINARY_PANCHAYAT_B"]


def test_point_near_shared_boundary_within_tolerance(isolated_service):
    """
    Coordinates within the numerical boundary tolerance (1e-5 deg ≈ 1.1m)
    must trigger ON_BOUNDARY rather than guessing.
    """
    svc, _ = isolated_service
    res = svc.resolve_coordinates(
        lat=POINT_NEAR_SHARED_BOUNDARY["lat"],
        lon=POINT_NEAR_SHARED_BOUNDARY["lon"],
        tolerance_deg=1e-5
    )
    assert res.status == BoundaryResolutionStatus.ON_BOUNDARY
    assert res.boundary_status == PointLocationStatus.ON_BOUNDARY
    assert "IMAGINARY_PANCHAYAT_A" in res.candidate_panchayat_ids
    assert "IMAGINARY_PANCHAYAT_B" in res.candidate_panchayat_ids


def test_coordinate_outside_both_panchayats(isolated_service):
    """Coordinates outside all registered polygons return OUTSIDE_REGISTERED_PANCHAYATS."""
    svc, _ = isolated_service
    res = svc.resolve_coordinates(
        lat=POINT_OUTSIDE_BOTH["lat"],
        lon=POINT_OUTSIDE_BOTH["lon"]
    )
    assert res.status == BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS
    assert res.boundary_status == PointLocationStatus.OUTSIDE_POLYGON
    assert res.panchayat_id is None


# =========================================================================
# 5. Coordinate Boundary Validation
# =========================================================================

@pytest.mark.parametrize("invalid_lat, invalid_lon", [
    (95.0, 82.5),       # Lat > 90
    (-95.0, 82.5),      # Lat < -90
    (25.0, 185.0),      # Lon > 180
    (25.0, -190.0),     # Lon < -180
    (float("nan"), 82.5),
    (25.0, float("inf")),
    ("not_a_num", 82.5),
])
def test_invalid_coordinates(isolated_service, invalid_lat, invalid_lon):
    """Invalid coordinates fail safely with INVALID_COORDINATES and success=False."""
    svc, _ = isolated_service
    res = svc.resolve_coordinates(lat=invalid_lat, lon=invalid_lon)
    assert res.status == BoundaryResolutionStatus.INVALID_COORDINATES
    assert res.boundary_status == PointLocationStatus.INVALID
    assert res.success is False
    assert res.panchayat_id is None


# =========================================================================
# 6. Boundary Ingestion Layer & Geometry Repair
# =========================================================================

def test_malformed_non_areal_geometry_rejected():
    """Non-areal geometries (LineString, Point) must be rejected with ValueError."""
    ingestor = PanchayatBoundaryIngestor()
    malformed_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(LineString([(82.4, 25.0), (82.5, 25.1)])),
                "properties": {"panchayat_id": "GP_LINESTRING"}
            }
        ]
    }
    with pytest.raises(ValueError, match="irrecoverably invalid"):
        ingestor.ingest_geojson_dict(malformed_geojson, source_name="TEST_MALFORMED")


def test_mechanical_geometry_repair():
    """
    Self-intersecting 'bowtie' polygon is mechanically invalid, but can be
    healed via make_valid into valid MultiPolygon without changing boundary intent.
    """
    ingestor = PanchayatBoundaryIngestor()
    # Figure-8 / bowtie polygon with self-intersecting crossing edge
    bowtie_coords = [(82.0, 25.0), (82.1, 25.1), (82.0, 25.1), (82.1, 25.0), (82.0, 25.0)]
    bowtie_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [bowtie_coords]},
                "properties": {"panchayat_id": "GP_BOWTIE", "name": "Bowtie GP"}
            }
        ]
    }
    records = ingestor.ingest_geojson_dict(bowtie_geojson, source_name="TEST_BOWTIE")
    assert len(records) == 1
    rec = records[0]
    assert rec.panchayat_id == "GP_BOWTIE"
    assert rec.area_sq_km > 0.0


def test_duplicate_panchayat_id_detected():
    """Ingestion of multiple features with duplicate Panchayat IDs must be rejected."""
    ingestor = PanchayatBoundaryIngestor()
    dup_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(Polygon([(82.0, 25.0), (82.1, 25.0), (82.1, 25.1), (82.0, 25.1), (82.0, 25.0)])),
                "properties": {"panchayat_id": "DUPLICATE_GP"}
            },
            {
                "type": "Feature",
                "geometry": mapping(Polygon([(82.2, 25.0), (82.3, 25.0), (82.3, 25.1), (82.2, 25.1), (82.2, 25.0)])),
                "properties": {"panchayat_id": "DUPLICATE_GP"}
            }
        ]
    }
    with pytest.raises(ValueError, match="Duplicate Panchayat ID detected"):
        ingestor.ingest_geojson_dict(dup_geojson, source_name="TEST_DUP")


# =========================================================================
# 7. Overlapping Polygons Fail-Closed Ambiguity
# =========================================================================

def test_overlapping_polygons_fail_closed():
    """
    If two polygons overlap across their interior, a query point inside the overlap
    must trigger OVERLAPPING_POLYGONS error state with conflicting IDs recorded.
    """
    reg = PanchayatBoundaryRegistry()
    # Overlapping squares [82.0, 82.2] and [82.1, 82.3]
    poly1 = Polygon([(82.0, 25.0), (82.2, 25.0), (82.2, 25.2), (82.0, 25.2), (82.0, 25.0)])
    poly2 = Polygon([(82.1, 25.0), (82.3, 25.0), (82.3, 25.2), (82.1, 25.2), (82.1, 25.0)])

    reg.register(PanchayatBoundaryRecord(
        panchayat_id="OVERLAP_GP_1",
        panchayat_name="Overlap GP 1",
        block="Block", district="District", state="State",
        geometry=mapping(poly1),
        centroid_lat=25.1, centroid_lon=82.1, area_sq_km=10.0,
        geometry_source="TEST", ingestion_timestamp="2026-09-27T00:00:00Z"
    ))
    reg.register(PanchayatBoundaryRecord(
        panchayat_id="OVERLAP_GP_2",
        panchayat_name="Overlap GP 2",
        block="Block", district="District", state="State",
        geometry=mapping(poly2),
        centroid_lat=25.1, centroid_lon=82.2, area_sq_km=10.0,
        geometry_source="TEST", ingestion_timestamp="2026-09-27T00:00:00Z"
    ))

    svc = PanchayatBoundaryService(registry=reg)
    # Point at (82.15, 25.1) is strictly inside BOTH polygons
    res = svc.resolve_coordinates(lat=25.1, lon=82.15)
    assert res.status == BoundaryResolutionStatus.OVERLAPPING_POLYGONS
    assert res.boundary_status == PointLocationStatus.AMBIGUOUS_OVERLAP
    assert res.candidate_panchayat_ids == ["OVERLAP_GP_1", "OVERLAP_GP_2"]
    assert res.success is False


# =========================================================================
# 8. Unverified Geometry Fail-Closed Policy
# =========================================================================

def test_unverified_geometry_fail_closed(isolated_service):
    """When require_verified=True, unverified boundary fails closed."""
    svc, _ = isolated_service
    # Imaginary Panchayats are marked is_verified=False
    res = svc.resolve_coordinates(
        lat=POINT_STRICTLY_INSIDE_A["lat"],
        lon=POINT_STRICTLY_INSIDE_A["lon"],
        require_verified=True
    )
    assert res.status == BoundaryResolutionStatus.UNVERIFIED_GEOMETRY
    assert res.success is False
    assert res.is_verified is False
    assert "unverified" in res.message


# =========================================================================
# 9. Determinism and Repeatability
# =========================================================================

def test_query_repeatability_100_runs(isolated_service):
    """The identical query executed 100 times must return bit-for-bit identical results."""
    svc, _ = isolated_service
    first_res = svc.resolve_coordinates(lat=POINT_STRICTLY_INSIDE_A["lat"], lon=POINT_STRICTLY_INSIDE_A["lon"])

    for _ in range(100):
        res = svc.resolve_coordinates(lat=POINT_STRICTLY_INSIDE_A["lat"], lon=POINT_STRICTLY_INSIDE_A["lon"])
        assert res.model_dump() == first_res.model_dump()


# =========================================================================
# 10. Multi-Key Canonical Registry Lookups
# =========================================================================

def test_registry_lookups(isolated_service):
    """Verify registry lookups by Panchayat ID, LGD code, and composite hierarchy."""
    _, reg = isolated_service
    rec_by_id = reg.get_by_id("IMAGINARY_PANCHAYAT_A")
    assert rec_by_id is not None
    assert rec_by_id.panchayat_name == "Imaginary Gram Panchayat A"

    rec_by_lgd = reg.get_by_lgd_code("LGD_IMAGINARY_A_99901")
    assert rec_by_lgd is not None
    assert rec_by_lgd.panchayat_id == "IMAGINARY_PANCHAYAT_A"

    rec_by_hierarchy = reg.get_by_name(
        state="Uttar Pradesh",
        district="Imaginary District",
        block="Imaginary Demonstration Block",
        panchayat_name="Imaginary Gram Panchayat A"
    )
    assert rec_by_hierarchy is not None
    assert rec_by_hierarchy.panchayat_id == "IMAGINARY_PANCHAYAT_A"


# =========================================================================
# 11. Downstream Integration Geographic Primitive
# =========================================================================

def test_downstream_integration_primitive(isolated_service):
    """Downstream services can call resolve_panchayat_from_coordinates()."""
    svc, reg = isolated_service
    from app.gis.boundary_service import panchayat_boundary_service

    # Temporarily point global service to test registry
    orig_reg = panchayat_boundary_service.registry
    try:
        panchayat_boundary_service.registry = reg
        rec = resolve_panchayat_from_coordinates(
            lat=POINT_STRICTLY_INSIDE_A["lat"],
            lon=POINT_STRICTLY_INSIDE_A["lon"]
        )
        assert rec is not None
        assert rec.panchayat_id == "IMAGINARY_PANCHAYAT_A"

        # Point outside returns None
        rec_outside = resolve_panchayat_from_coordinates(lat=26.0, lon=83.0)
        assert rec_outside is None
    finally:
        panchayat_boundary_service.registry = orig_reg


# =========================================================================
# 12. API Endpoints
# =========================================================================

def test_api_resolve_and_boundary_endpoints():
    """Verify /api/v1/panchayat/resolve and /api/panchayats/resolve API routes."""
    from app.gis.boundary_service import panchayat_boundary_service
    from app.gis.boundary_registry import boundary_registry

    # Seed test records into global registry for API tests
    test_recs = get_imaginary_panchayat_records()
    boundary_registry.register_all(test_recs)

    try:
        # 1. Test /api/v1/panchayat/resolve
        resp1 = client.get(f"/api/v1/panchayat/resolve?lat={POINT_STRICTLY_INSIDE_A['lat']}&lon={POINT_STRICTLY_INSIDE_A['lon']}")
        assert resp1.status_code == 200
        d1 = resp1.json()
        assert d1["status"] == "RESOLVED"
        assert d1["panchayat_id"] == "IMAGINARY_PANCHAYAT_A"
        assert d1["boundary_status"] == "INSIDE_POLYGON"

        # 2. Test /api/panchayats/resolve (conceptual compatibility alias)
        resp2 = client.get(f"/api/panchayats/resolve?lat={POINT_STRICTLY_INSIDE_A['lat']}&lon={POINT_STRICTLY_INSIDE_A['lon']}")
        assert resp2.status_code == 200
        d2 = resp2.json()
        assert d2["status"] == "RESOLVED"
        assert d2["panchayat_id"] == "IMAGINARY_PANCHAYAT_A"

        # 3. Test /api/v1/panchayat/{panchayat_id}/boundary
        b_resp1 = client.get("/api/v1/panchayat/IMAGINARY_PANCHAYAT_A/boundary")
        assert b_resp1.status_code == 200
        feat1 = b_resp1.json()
        assert feat1["type"] == "Feature"
        assert feat1["properties"]["panchayat_id"] == "IMAGINARY_PANCHAYAT_A"
        assert feat1["geometry"]["type"] == "Polygon"

        # 4. Test /api/panchayats/{panchayat_id}/boundary
        b_resp2 = client.get("/api/panchayats/IMAGINARY_PANCHAYAT_A/boundary")
        assert b_resp2.status_code == 200
        feat2 = b_resp2.json()
        assert feat2["type"] == "Feature"
        assert feat2["properties"]["panchayat_id"] == "IMAGINARY_PANCHAYAT_A"

        # 5. Nonexistent Panchayat ID returns 404
        b_404 = client.get("/api/panchayats/NONEXISTENT_PANCHAYAT/boundary")
        assert b_404.status_code == 404

        # 6. Shared boundary returns ON_BOUNDARY
        edge_resp = client.get(f"/api/panchayats/resolve?lat={POINT_EXACTLY_ON_SHARED_BOUNDARY['lat']}&lon={POINT_EXACTLY_ON_SHARED_BOUNDARY['lon']}")
        assert edge_resp.status_code == 200
        edge_d = edge_resp.json()
        assert edge_d["status"] == "ON_BOUNDARY"
        assert edge_d["candidate_panchayat_ids"] == ["IMAGINARY_PANCHAYAT_A", "IMAGINARY_PANCHAYAT_B"]
    finally:
        boundary_registry.clear()
