"""
Tests for ML Downscaling Inference Engine, Registry & API Endpoints
SIH Problem Statement 26074 (Weather Downscaling)
"""
import os
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import settings
from app.ml.feature_manifest import ALL_PREDICTOR_FEATURES
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel
from app.ml.metadata import HyperparameterConfig
from app.ml.trainer import DownscalingModelTrainer
from app.ml.registry import LocalModelRegistry
from app.ml.predictor import TemperatureDownscalingPredictor
from tests.test_ml_training import generate_synthetic_feature_df


@pytest.fixture
def test_model_registry(tmp_path, monkeypatch):
    """Fixture that initializes a temporary model registry and trains a test model."""
    registry_dir = str(tmp_path / "models_test")
    monkeypatch.setattr(settings, "ML_MODEL_DIR", registry_dir)
    monkeypatch.setattr(settings, "TEMPERATURE_MODEL_VERSION", "v1.0.0-test")

    registry = LocalModelRegistry(base_dir=registry_dir)
    trainer = DownscalingModelTrainer(registry=registry)

    df = generate_synthetic_feature_df(80)
    trainer.train_from_dataframe(
        df=df,
        model_version="v1.0.0-test",
        allow_synthetic=True,
        is_synthetic=True
    )

    return registry


def test_registry_inspection_and_schema_compatibility(test_model_registry):
    """Verifies registry listing and feature schema checking."""
    registry = test_model_registry

    # List models
    models = registry.list_models()
    assert len(models) == 1
    assert models[0]["version"] == "v1.0.0-test"
    assert models[0]["is_active"] is True

    # Check schema compatibility: complete features list passes
    is_compat, missing = registry.check_schema_compatibility("v1.0.0-test", ALL_PREDICTOR_FEATURES)
    assert is_compat is True
    assert len(missing) == 0

    # Incomplete features list fails
    is_compat, missing = registry.check_schema_compatibility("v1.0.0-test", ["forecast_temp_mean"])
    assert is_compat is False
    assert len(missing) > 0


def test_predictor_point_inference_accuracy(test_model_registry):
    """Verifies single-point inference calculation: T_downscaled = T_coarse + y_pred."""
    predictor = TemperatureDownscalingPredictor(registry=test_model_registry)

    features = {feat: 1.0 for feat in ALL_PREDICTOR_FEATURES}
    features["lapse_rate_temp_adjustment_c"] = -1.25
    features["slope_deg"] = 12.5

    result = predictor.predict_point(
        coarse_forecast_temp_c=28.0,
        features=features,
        model_version="v1.0.0-test"
    )

    assert "downscaled_temperature_c" in result
    assert result["coarse_forecast_temp_c"] == 28.0
    assert result["model_version"] == "v1.0.0-test"
    assert result["lapse_rate_adjustment_c"] == -1.25
    assert result["topographic_slope_deg"] == 12.5
    assert np.isclose(
        result["downscaled_temperature_c"],
        round(28.0 + result["predicted_residual_c"], 2)
    )


def test_predictor_rejection_of_missing_and_invalid_inputs(test_model_registry):
    """Verifies that missing features or NaN/Inf values are rejected with informative errors."""
    predictor = TemperatureDownscalingPredictor(registry=test_model_registry)

    # 1. Missing feature
    incomplete_features = {"forecast_temp_min": 20.0}
    with pytest.raises(ValueError, match="Missing required predictor"):
        predictor.predict_point(coarse_forecast_temp_c=25.0, features=incomplete_features, model_version="v1.0.0-test")

    # 2. NaN in feature
    nan_features = {feat: 1.0 for feat in ALL_PREDICTOR_FEATURES}
    nan_features["slope_deg"] = float("nan")
    with pytest.raises(ValueError, match="invalid NaN or Inf"):
        predictor.predict_point(coarse_forecast_temp_c=25.0, features=nan_features, model_version="v1.0.0-test")

    # 3. Invalid coarse temperature
    valid_features = {feat: 1.0 for feat in ALL_PREDICTOR_FEATURES}
    with pytest.raises(ValueError, match="Invalid coarse_forecast_temp_c"):
        predictor.predict_point(coarse_forecast_temp_c=float("nan"), features=valid_features, model_version="v1.0.0-test")


def test_predictor_batch_inference(test_model_registry):
    """Verifies vectorized batch prediction on a DataFrame."""
    predictor = TemperatureDownscalingPredictor(registry=test_model_registry)

    df = generate_synthetic_feature_df(25)
    result_df = predictor.predict_batch(
        df_features=df,
        coarse_temp_col="coarse_forecast_temp_c",
        model_version="v1.0.0-test"
    )

    assert "predicted_residual_c" in result_df.columns
    assert "downscaled_temperature_c" in result_df.columns
    assert len(result_df) == 25


def test_api_model_management_and_inference(test_model_registry, client: TestClient):
    """Tests the full suite of ML REST API endpoints."""
    # 1. GET /api/v1/ml/models
    resp = client.get("/api/v1/ml/models")
    assert resp.status_code == 200
    json_data = resp.json()["data"]
    assert json_data["total_models"] >= 1

    # 2. GET /api/v1/ml/models/v1.0.0-test
    resp = client.get("/api/v1/ml/models/v1.0.0-test")
    assert resp.status_code == 200
    meta = resp.json()["data"]
    assert meta["model_version"] == "v1.0.0-test"
    assert len(meta["features_used"]) == len(ALL_PREDICTOR_FEATURES)

    # 3. GET /api/v1/ml/models/v1.0.0-test/metrics
    resp = client.get("/api/v1/ml/models/v1.0.0-test/metrics")
    assert resp.status_code == 200
    metrics = resp.json()["data"]
    assert "test_evaluation" in metrics

    # 4. GET /api/v1/ml/models/v1.0.0-test/features
    resp = client.get("/api/v1/ml/models/v1.0.0-test/features")
    assert resp.status_code == 200
    features = resp.json()["data"]
    assert len(features) == len(ALL_PREDICTOR_FEATURES)
    assert features[0]["rank"] == 1

    # 5. POST /api/v1/ml/predict/temperature
    features_dict = {feat: 1.0 for feat in ALL_PREDICTOR_FEATURES}
    payload = {
        "coarse_forecast_temp_c": 31.5,
        "features": features_dict,
        "model_version": "v1.0.0-test"
    }
    resp = client.post("/api/v1/ml/predict/temperature", json=payload)
    assert resp.status_code == 200
    pred = resp.json()["data"]
    assert "downscaled_temperature_c" in pred
    assert pred["coarse_forecast_temp_c"] == 31.5
    assert pred["model_version"] == "v1.0.0-test"
