import pytest
from fastapi.testclient import TestClient


def test_get_blocks_endpoint(client: TestClient):
    """
    Verifies that 'GET /api/v1/panchayat/blocks' returns block summaries
    with child panchayat counts and district metadata.
    """
    response = client.get("/api/v1/panchayat/blocks")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    blocks = json_resp["data"]
    assert isinstance(blocks, list)
    if len(blocks) > 0:
        b = blocks[0]
        assert "id" in b
        assert "name" in b
        assert "district" in b
        assert "panchayat_count" in b


def test_get_panchayats_geojson_endpoint(client: TestClient):
    """
    Verifies that 'GET /api/v1/panchayat/geojson' returns a valid GeoJSON
    FeatureCollection with downscaled weather and risk properties.
    """
    response = client.get("/api/v1/panchayat/geojson")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    fc = json_resp["data"]
    assert fc["type"] == "FeatureCollection"
    assert "features" in fc
    assert isinstance(fc["features"], list)
    if len(fc["features"]) > 0:
        f = fc["features"][0]
        assert f["type"] == "Feature"
        assert "geometry" in f
        assert "properties" in f
        assert "name" in f["properties"]
        assert "is_cropland_eligible" in f["properties"]


def test_get_panchayat_detail_endpoint(client: TestClient):
    """
    Verifies unified 1-call detail endpoint 'GET /api/v1/panchayat/{id}/detail'.
    """
    # 1. Fetch available panchayats to get a valid ID or test 404
    p_response = client.get("/api/v1/panchayat/list")
    assert p_response.status_code == 200
    data_field = p_response.json()["data"]
    panchayats = data_field["items"] if isinstance(data_field, dict) and "items" in data_field else data_field

    if isinstance(panchayats, list) and len(panchayats) > 0:
        pid = panchayats[0]["panchayat_id"] if "panchayat_id" in panchayats[0] else panchayats[0].get("id", 1)
        response = client.get(f"/api/v1/panchayat/{pid}/detail")
        assert response.status_code == 200
        payload = response.json()["data"]
        assert "panchayat" in payload
        assert "latest_weather" in payload
        assert "agricultural_contexts" in payload
        assert "detected_risks" in payload
        assert "active_advisories" in payload
        assert payload["panchayat"]["id"] == pid
    else:
        # Non-existent ID returns 404
        response = client.get("/api/v1/panchayat/999999/detail")
        assert response.status_code == 404


def test_get_ml_grid_cells_endpoint(client: TestClient):
    """
    Verifies that 'GET /api/v1/ml/grid/cells' returns 1-km spatial grid cells
    with residual predictions, temperatures, and DEM terrain parameters.
    """
    response = client.get("/api/v1/ml/grid/cells")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    cells = json_resp["data"]
    assert isinstance(cells, list)
    if len(cells) > 0:
        c = cells[0]
        assert "cell_id" in c
        assert "latitude" in c
        assert "longitude" in c
        assert "tmean_c" in c
        assert "predicted_residual" in c
        assert "elevation_m" in c
        assert "slope_deg" in c
