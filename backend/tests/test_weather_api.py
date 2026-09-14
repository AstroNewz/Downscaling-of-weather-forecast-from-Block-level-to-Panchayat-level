import pytest
from fastapi.testclient import TestClient


def test_weather_status_endpoint(client: TestClient):
    """Verifies that '/api/v1/weather/status' returns subsystem status and statistics."""
    response = client.get("/api/v1/weather/status")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    data = json_resp["data"]
    assert "active_providers" in data
    assert "CSVWeatherProvider" in data["active_providers"]
    assert "normalization_standards" in data


def test_weather_ingest_dry_run_endpoint(client: TestClient):
    """Verifies dry-run weather ingestion via POST '/api/v1/weather/ingest'."""
    sample_csv = """block,valid_time,temp_min,temp_max,rainfall,humidity,wind_speed
Varanasi Sadar,2026-09-15 00:00:00,24.5,33.0,12.0,75.0,15.0
Pindra,2026-09-15 00:00:00,23.0,31.5,0.0,65.0,8.0
"""
    payload = {
        "raw_csv_content": sample_csv,
        "source_label": "TEST_CSV_STREAM",
        "model_name": "IMD-GFS",
        "dry_run": True,
    }
    response = client.post("/api/v1/weather/ingest", json=payload)
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    summary = json_resp["data"]
    assert summary["records_read"] == 2
    assert summary["records_valid"] == 2
    assert summary["records_inserted"] == 2
    assert summary["status"] == "SUCCESS"


def test_weather_ingest_validation_failure(client: TestClient):
    """Verifies that totally empty/missing data payloads return appropriate errors."""
    payload = {
        "source_label": "EMPTY_PAYLOAD",
        "dry_run": True,
    }
    response = client.post("/api/v1/weather/ingest", json=payload)
    assert response.status_code == 400


def test_weather_forecast_query_endpoint(client: TestClient):
    """Verifies that GET '/api/v1/weather/forecast' accepts parameters and returns paginated response."""
    response = client.get("/api/v1/weather/forecast?page=1&page_size=10")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert "items" in json_resp["data"]
    assert "total" in json_resp["data"]
    assert json_resp["data"]["page"] == 1
    assert json_resp["data"]["page_size"] == 10


def test_weather_observations_query_endpoint(client: TestClient):
    """Verifies that GET '/api/v1/weather/observations' accepts parameters and returns paginated response."""
    response = client.get("/api/v1/weather/observations?page=1&page_size=10")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert "items" in json_resp["data"]
    assert "total" in json_resp["data"]
