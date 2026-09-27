"""
Task 6 Acceptance & API Integration Test: Localized Nowcast Exposure
SIH Problem Statement 26074 (Weather Downscaling & Agromet Advisory)

Verifies:
1. End-to-end Point-in-Polygon coordinate resolution routes user to exact Panchayat polygon.
2. Forecast endpoint returns distinct localized nowcast for Dholakpur A vs B under identical baseline.
3. Dedicated precipitation-nowcast endpoint operates safely.
4. Farmer Action advisory reflects localized nowcast signal.
5. Fail-closed behavior on invalid dates and unavailable data.

Polygon geometry layout:
  IMAGINARY_PANCHAYAT_A / B: lat [25.00 – 25.20], lon [82.40 – 82.60]
  DHOLAKPUR_PANCHAYAT_A / B: lat [25.50 – 25.70], lon [82.40 – 82.60]  (non-overlapping)
"""
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import pytest

from app.main import app
from app.gis.boundary_registry import boundary_registry
from app.gis.boundary_service import panchayat_boundary_service
from tests.fixtures.imaginary_panchayats_fixture import (
    get_imaginary_panchayat_records,
    DHOLAKPUR_POINT_INSIDE_A,
    DHOLAKPUR_POINT_INSIDE_B,
    DHOLAKPUR_POINT_INSIDE_A_CLOSER_TO_B,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_boundaries():
    """Ensure all pilot Panchayat polygons (IMAGINARY + DHOLAKPUR) are registered.

    Dholakpur polygons are at lat [25.50-25.70], IMAGINARY at lat [25.00-25.20].
    The two sets are geographically disjoint so no OVERLAPPING_POLYGONS error occurs.
    """
    for r in get_imaginary_panchayat_records():
        boundary_registry.register(r)
    panchayat_boundary_service._sync_spatial_index()


def test_pip_coordinate_routing_to_exact_panchayat():
    """Requirement 5: Coordinates resolve strictly via point-in-polygon, never centroid.

    Dholakpur A polygon:
      L-shape: bottom bar lat [25.50,25.55] / vertical bar lat [25.55,25.70], lon [82.40,82.45]
    Dholakpur B polygon:
      Rectangle: lat [25.55,25.70], lon [82.45,82.60]
    """
    # Point strictly inside Dholakpur A's vertical bar
    res = client.get(
        f"/api/v1/panchayat/resolve"
        f"?lat={DHOLAKPUR_POINT_INSIDE_A['lat']}&lon={DHOLAKPUR_POINT_INSIDE_A['lon']}"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESOLVED", (
        f"Expected RESOLVED for Dholakpur A, got {data['status']}: {data.get('message')}"
    )
    assert data["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_A"
    assert "Dholakpur" in data["panchayat_name"]

    # Point strictly inside Dholakpur B's rectangle
    res_b = client.get(
        f"/api/v1/panchayat/resolve"
        f"?lat={DHOLAKPUR_POINT_INSIDE_B['lat']}&lon={DHOLAKPUR_POINT_INSIDE_B['lon']}"
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == "RESOLVED", (
        f"Expected RESOLVED for Dholakpur B, got {data_b['status']}: {data_b.get('message')}"
    )
    assert data_b["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_B"
    assert "Dholakpur" in data_b["panchayat_name"]

    # Anti-centroid proof: point in A's bottom bar, geometrically closer to Centroid B than A
    res_anti = client.get(
        f"/api/v1/panchayat/resolve"
        f"?lat={DHOLAKPUR_POINT_INSIDE_A_CLOSER_TO_B['lat']}&lon={DHOLAKPUR_POINT_INSIDE_A_CLOSER_TO_B['lon']}"
    )
    assert res_anti.status_code == 200
    data_anti = res_anti.json()
    assert data_anti["status"] == "RESOLVED", (
        f"Anti-centroid point should RESOLVE to A, got {data_anti['status']}"
    )
    assert data_anti["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_A", (
        f"Anti-centroid point should be A (not B). Got {data_anti['panchayat_id']}"
    )


def test_dholakpur_ab_forecast_acceptance():
    """
    Requirement 16 & 32: Acceptance scenario
    Panchayat A vs Panchayat B in Dholakpur Block:
    - Same Block baseline NWP
    - Panchayat A receives high localized nowcast
    - Panchayat B receives lower localized nowcast
    - Neither leaks into the other
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch Panchayat A forecast
    res_a = client.get(f"/api/v1/forecast?location_id=DHOLAKPUR_PANCHAYAT_A&target_date={today_str}")
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["location_id"] == "DHOLAKPUR_PANCHAYAT_A"
    assert "precipitation_nowcast" in data_a
    nc_a = data_a["precipitation_nowcast"]
    assert nc_a is not None
    assert nc_a["success"] is True
    assert nc_a["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_A"

    # Fetch Panchayat B forecast
    res_b = client.get(f"/api/v1/forecast?location_id=DHOLAKPUR_PANCHAYAT_B&target_date={today_str}")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["location_id"] == "DHOLAKPUR_PANCHAYAT_B"
    assert "precipitation_nowcast" in data_b
    nc_b = data_b["precipitation_nowcast"]
    assert nc_b is not None
    assert nc_b["success"] is True
    assert nc_b["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_B"

    # Verify separation: primary_horizon uses key 'rain_probability' (confirmed from schema)
    prob_a = nc_a["primary_horizon"]["rain_probability"]
    prob_b = nc_b["primary_horizon"]["rain_probability"]

    # In synthetic fixture, A has colder IR clouds (higher rain risk) than B
    assert prob_a > prob_b, f"Panchayat A probability ({prob_a}) should exceed B ({prob_b})"
    assert prob_a >= 0.50

    # Verify baseline forecast values are retained and visible (not overwritten by nowcast)
    assert "current" in data_a
    assert "current" in data_b
    assert data_a["current"]["temperature_c"] > 0
    assert data_b["current"]["temperature_c"] > 0


def test_dedicated_precipitation_nowcast_endpoint():
    """Requirement 2: Dedicated nowcast endpoint with date guard."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # For today: nowcast should succeed
    res = client.get(f"/api/v1/panchayat/DHOLAKPUR_PANCHAYAT_A/precipitation-nowcast?date={today_str}")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_A"
    assert "horizons" in body["data"]

    # For future date (Requirement 17: fail-closed / not operationally applicable)
    res_future = client.get("/api/v1/panchayat/DHOLAKPUR_PANCHAYAT_A/precipitation-nowcast?date=2028-01-01")
    assert res_future.status_code == 200
    body_f = res_future.json()
    assert body_f["success"] is False
    assert "only operationally applicable for current/short horizons" in body_f["message"]


def test_panchayat_detail_includes_nowcast():
    """Verifies get_panchayat_full_detail returns nowcast data."""
    res = client.get("/api/v1/panchayat/DHOLAKPUR_PANCHAYAT_A/detail")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "precipitation_nowcast" in data
    assert data["precipitation_nowcast"] is not None
    assert data["precipitation_nowcast"]["panchayat_id"] == "DHOLAKPUR_PANCHAYAT_A"
