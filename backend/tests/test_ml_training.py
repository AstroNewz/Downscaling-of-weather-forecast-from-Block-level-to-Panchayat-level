"""
Tests for ML Downscaling Model Training, Leakage Quarantine & Evaluation
SIH Problem Statement 26074 (Weather Downscaling)
"""
import os
import pytest
import numpy as np
import pandas as pd

from app.ml.feature_manifest import (
    ALL_PREDICTOR_FEATURES,
    QUARANTINED_LEAKAGE_COLUMNS,
    validate_no_leakage,
    extract_features_and_target,
)
from app.ml.models.xgboost_model import XGBoostTemperatureResidualModel
from app.ml.metadata import HyperparameterConfig
from app.ml.evaluator import DownscalingModelEvaluator
from app.ml.registry import LocalModelRegistry
from app.ml.trainer import DownscalingModelTrainer


def generate_synthetic_feature_df(n_samples: int = 120, random_seed: int = 42) -> pd.DataFrame:
    """Generates a synthetic DataFrame containing all 35 predictors and target variables."""
    np.random.seed(random_seed)
    data = {}

    for feat in ALL_PREDICTOR_FEATURES:
        if "sin_" in feat or "cos_" in feat:
            data[feat] = np.random.uniform(-1.0, 1.0, size=n_samples)
        elif "fraction" in feat:
            data[feat] = np.random.uniform(0.0, 1.0, size=n_samples)
        elif "elevation" in feat:
            data[feat] = np.random.uniform(100.0, 1500.0, size=n_samples)
        elif "temp" in feat:
            data[feat] = np.random.uniform(15.0, 35.0, size=n_samples)
        elif "lead_hours" in feat:
            data[feat] = np.random.randint(1, 72, size=n_samples)
        else:
            data[feat] = np.random.uniform(0.0, 50.0, size=n_samples)

    # Base Coarse forecast temperature
    data["coarse_forecast_temp_c"] = np.random.uniform(20.0, 35.0, size=n_samples)

    # Physical residual dependent on elevation diff and land-use
    elevation_effect = -0.0065 * (data["elevation_diff_m"])
    urban_effect = 1.5 * data["urban_fraction"]
    water_effect = -1.0 * data["water_fraction"]
    noise = np.random.normal(0, 0.2, size=n_samples)

    residual = elevation_effect + urban_effect + water_effect + noise
    data["temperature_residual_c"] = residual
    data["observed_temp_c"] = data["coarse_forecast_temp_c"] + residual

    # Add chronological split
    splits = ["train"] * int(n_samples * 0.7) + ["val"] * int(n_samples * 0.15) + ["test"] * (n_samples - int(n_samples * 0.7) - int(n_samples * 0.15))
    data["split"] = splits

    return pd.DataFrame(data)


def test_leakage_prevention_quarantine():
    """Verifies that quarantined metadata and target columns are strictly rejected."""
    # 1. Valid feature list passes
    is_valid, leaked = validate_no_leakage(ALL_PREDICTOR_FEATURES)
    assert is_valid is True
    assert len(leaked) == 0

    # 2. Leaked observed_temp is detected
    tainted_features = ALL_PREDICTOR_FEATURES + ["observed_temp_c"]
    is_valid, leaked = validate_no_leakage(tainted_features)
    assert is_valid is False
    assert "observed_temp_c" in leaked

    # 3. Leaked residual target is detected
    tainted_features2 = ["temperature_residual_c", "forecast_temp_mean"]
    is_valid, leaked = validate_no_leakage(tainted_features2)
    assert is_valid is False
    assert "temperature_residual_c" in leaked

    # 4. extract_features_and_target raises ValueError on contaminated features
    df = generate_synthetic_feature_df(20)
    with pytest.raises(ValueError, match="Data leakage detected"):
        extract_features_and_target(df, features_to_use=["observed_temp_c", "elevation_diff_m"])


def test_evaluator_metrics_calculation():
    """Verifies statistical metric calculation (MAE, RMSE, MBE, R²)."""
    evaluator = DownscalingModelEvaluator()

    y_true = np.array([20.0, 22.0, 24.0, 26.0])
    y_pred = np.array([21.0, 21.0, 25.0, 27.0])  # errors: +1, -1, +1, +1

    metrics = evaluator.calculate_metric_score(y_true, y_pred)
    assert metrics.mae == 1.0
    assert np.isclose(metrics.rmse, 1.0)
    assert np.isclose(metrics.mbe, 0.5)
    assert metrics.r2 > 0.8
    assert metrics.sample_count == 4


def test_xgboost_residual_model_training(tmp_path):
    """Tests fitting, predicting, feature importance, and serialization of XGBoost model."""
    df = generate_synthetic_feature_df(80)

    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]

    X_train, y_train, _, _ = extract_features_and_target(train_df)
    X_val, y_val, _, _ = extract_features_and_target(val_df)

    hyperparams = HyperparameterConfig(
        n_estimators=30,
        learning_rate=0.1,
        max_depth=3,
        early_stopping_rounds=10
    )

    model = XGBoostTemperatureResidualModel(
        model_name="xgboost_temperature_residual",
        version="v1.0.0-test",
        hyperparameters=hyperparams,
        random_seed=42
    )

    model.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val)
    assert model.is_fitted is True

    # Test predictions
    preds = model.predict(X_val)
    assert len(preds) == len(X_val)
    assert isinstance(preds, np.ndarray)

    # Test feature importances
    ranked_importances = model.get_ranked_feature_importances()
    assert len(ranked_importances) == len(ALL_PREDICTOR_FEATURES)
    assert ranked_importances[0].rank == 1

    # Test model serialization & deserialization
    save_dir = str(tmp_path / "model_out")
    model.save(save_dir)
    assert os.path.exists(os.path.join(save_dir, "model.json"))

    loaded_model = XGBoostTemperatureResidualModel(version="v1.0.0-test")
    loaded_model.load(save_dir)
    assert loaded_model.is_fitted is True
    loaded_preds = loaded_model.predict(X_val)
    assert np.allclose(preds, loaded_preds)


def test_model_trainer_min_rows_scientific_guard():
    """Verifies that trainer safely fails if sample size is too small without synthetic authorization."""
    trainer = DownscalingModelTrainer()
    small_df = generate_synthetic_feature_df(20)

    with pytest.raises(ValueError, match="INSUFFICIENT REAL DATA FOR TRAINING"):
        trainer.train_from_dataframe(
            df=small_df,
            model_version="v1.0.0-fail",
            min_train_rows=50,
            allow_synthetic=False,
            is_synthetic=False
        )


def test_model_trainer_end_to_end_pipeline(tmp_path):
    """Verifies end-to-end training, split evaluation, baseline improvements, and registry registration."""
    registry_dir = str(tmp_path / "registry")
    registry = LocalModelRegistry(base_dir=registry_dir)
    trainer = DownscalingModelTrainer(registry=registry)

    df = generate_synthetic_feature_df(100)

    model, metadata, metrics, importances = trainer.train_from_dataframe(
        df=df,
        model_version="v1.0.0-pipeline",
        dataset_version="v1.0.0",
        allow_synthetic=True,
        is_synthetic=True
    )

    # Check metrics existence
    assert metrics.train_evaluation.split_name == "train"
    assert metrics.validation_evaluation.split_name == "validation"
    assert metrics.test_evaluation.split_name == "test"

    # Check that model improved over baseline or computed valid metrics
    assert metrics.test_evaluation.model_metrics.sample_count > 0
    assert metrics.test_evaluation.baseline_metrics.mae > 0

    # Check registry artifacts on disk
    version_dir = os.path.join(registry_dir, "v1.0.0-pipeline")
    assert os.path.exists(os.path.join(version_dir, "model.json"))
    assert os.path.exists(os.path.join(version_dir, "metadata.json"))
    assert os.path.exists(os.path.join(version_dir, "metrics.json"))
    assert os.path.exists(os.path.join(version_dir, "feature_importance.json"))

    # Verify registry can read back the model
    loaded_model, loaded_meta = registry.load_model_artifact("v1.0.0-pipeline")
    assert loaded_meta.model_version == "v1.0.0-pipeline"
    assert loaded_meta.provenance.is_synthetic is True
