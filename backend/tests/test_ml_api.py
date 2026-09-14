import pytest
from fastapi.testclient import TestClient


def test_ml_registry_status_endpoint(client: TestClient):
    """Verifies that '/api/v1/ml/status' returns ML downscaling subsystem information."""
    response = client.get("/api/v1/ml/status")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    data = json_resp["data"]
    assert "supported_models" in data
    assert "XGBoost Regressor" in data["supported_models"]
    assert data["modeling_strategy"] == "Residual/Bias Correction (y = observed - coarse_forecast)"


def test_ml_dataset_status_endpoint(client: TestClient):
    """Verifies that '/api/v1/ml/dataset/status' reports dataset versions and directories."""
    response = client.get("/api/v1/ml/dataset/status")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    data = json_resp["data"]
    assert data["dataset_version"] == "v1.0.0"
    assert "feature_schema_version" in data
    assert "target_variable" in data


def test_ml_dataset_build_dry_run_endpoint(client: TestClient):
    """Verifies dry run dataset build via POST '/api/v1/ml/dataset/build'."""
    payload = {
        "dataset_version": "test_v1.0",
        "dry_run": True,
        "temporal_tolerance_minutes": 180,
    }
    response = client.post("/api/v1/ml/dataset/build", json=payload)
    assert response.status_code == 200
    json_resp = response.json()
    # If empty database, returns EMPTY status cleanly
    assert json_resp["data"]["dataset_version"] == "test_v1.0"
    assert "overall_baseline" in json_resp["data"]
