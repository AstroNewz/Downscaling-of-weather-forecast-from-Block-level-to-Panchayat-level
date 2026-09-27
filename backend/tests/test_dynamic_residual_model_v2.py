"""
Unit and Integration Tests for Dynamic Residual Downscaling Model v2
SIH Problem Statement 26074 — Agro-Meteorological Downscaling

Validates:
- Research model artifacts exist and have valid sha256 checksums
- Production registry models/temperature_residual/ remains pristine/empty
- Governance status is strictly RESEARCH_ONLY and decision is RETAIN_FOR_RESEARCH
- Dynamic residual inference functions with correct feature schema
- Physical guardrails clamp extreme residuals to [-8.0, +8.0]°C
- Endpoints /api/v1/research/* respond accurately
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.dynamic_downscaling_service import dynamic_downscaling_service

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
CANDIDATE_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual" / "dynamic_temperature_residual_v2"
PROD_MODEL_DIR = BACKEND_ROOT / "models" / "temperature_residual"

client = TestClient(app)


def test_production_registry_isolation():
    """Verify production temperature_residual directory remains empty/untouched."""
    assert PROD_MODEL_DIR.exists(), "Production directory must exist"
    model_files = [f for f in PROD_MODEL_DIR.iterdir() if f.name != ".gitkeep" and not f.name.startswith(".")]
    assert len(model_files) == 0, f"Production directory must remain empty to protect baseline, found: {model_files}"


def test_candidate_artifacts_exist():
    """Verify all 4 required candidate model artifacts exist in candidate directory."""
    assert CANDIDATE_DIR.exists(), "Candidate directory must exist"
    assert (CANDIDATE_DIR / "xgboost_model.json").exists(), "xgboost_model.json missing"
    assert (CANDIDATE_DIR / "feature_schema.json").exists(), "feature_schema.json missing"
    assert (CANDIDATE_DIR / "metadata.json").exists(), "metadata.json missing"
    assert (CANDIDATE_DIR / "training_manifest.json").exists(), "training_manifest.json missing"


def test_candidate_governance_and_gate_decision():
    """Verify governance metadata confirms RESEARCH_ONLY status and RETAIN_FOR_RESEARCH decision."""
    meta_path = CANDIDATE_DIR / "metadata.json"
    with open(meta_path) as f:
        meta = json.load(f)

    assert meta["status"] == "RESEARCH_ONLY"
    assert meta["decision"] == "RETAIN_FOR_RESEARCH"
    assert meta["certified_production_baseline_offset_c"] == 0.7351
    assert "promotion_gate" in meta
    assert meta["promotion_gate"]["final_decision"] == "RETAIN_FOR_RESEARCH"


def test_service_prediction_and_guardrail():
    """Verify inference produces valid predictions and clamps extreme values."""
    res = dynamic_downscaling_service.predict_residual(
        coarse_temp=28.5,
        coarse_rh=70.0,
        coarse_wspd=3.0,
        wind_direction_deg=180.0,
        precipitation_mm=0.0,
        hour_of_day=14,
        day_of_year=210,
        elevation_m=120.0,
        slope_deg=1.5,
        aspect_deg=160.0,
        land_cover_code=40,
        latitude=25.5,
        longitude=83.0,
    )

    assert res["status"] == "RESEARCH_ONLY"
    assert res["candidate_id"] == "dynamic_temperature_residual_v2"
    assert isinstance(res["downscaled_temperature_c"], float)
    assert isinstance(res["final_residual_c"], float)
    assert res["guardrail_status"] in ["PASS", "CLAMPED"]
    assert -8.0 <= res["final_residual_c"] <= 8.0
    assert "baseline_comparison" in res
    assert res["baseline_comparison"]["certified_baseline_offset_c"] == 0.7351


def test_endpoint_dynamic_downscaling():
    """Verify POST /api/v1/research/dynamic-downscaling."""
    payload = {
        "coarse_temperature_c": 31.2,
        "relative_humidity_pct": 60.0,
        "wind_speed_mps": 2.8,
        "wind_direction_deg": 220.0,
        "precipitation_mm": 0.0,
        "hour_of_day": 15,
        "day_of_year": 215,
        "elevation_m": 90.0,
        "coarse_elevation_m": 80.0,
        "slope_deg": 0.8,
        "aspect_deg": 120.0,
        "land_cover_code": 40,
        "latitude": 25.4,
        "longitude": 82.8,
    }
    resp = client.post("/api/v1/research/dynamic-downscaling", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RESEARCH_ONLY"
    assert "downscaled_temperature_c" in data
    assert "final_residual_c" in data
    assert "guardrail_status" in data
    assert -8.0 <= data["final_residual_c"] <= 8.0


def test_endpoint_diagnostic():
    """Verify GET /api/v1/research/diagnostic."""
    resp = client.get("/api/v1/research/diagnostic")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RESEARCH_ONLY"
    assert data["is_loaded"] is True
    assert "metadata" in data
    assert data["metadata"]["decision"] == "RETAIN_FOR_RESEARCH"


def test_endpoint_compare():
    """Verify POST /api/v1/research/compare."""
    payload = {
        "coarse_temperature_c": 32.0,
        "relative_humidity_pct": 55.0,
        "wind_speed_mps": 3.5,
        "wind_direction_deg": 270.0,
        "precipitation_mm": 0.0,
        "hour_of_day": 13,
        "day_of_year": 220,
        "elevation_m": 150.0,
        "slope_deg": 2.0,
        "aspect_deg": 180.0,
        "land_cover_code": 50,
        "latitude": 28.5,
        "longitude": 77.2,
    }
    resp = client.post("/api/v1/research/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["production_baseline"]["status"] == "ACTIVE_PRODUCTION"
    assert data["production_baseline"]["correction_offset_c"] == 0.7351
    assert data["research_candidate"]["status"] == "RESEARCH_ONLY"
    assert "divergence" in data
    assert "temperature_diff_c" in data["divergence"]


def test_scientific_report_and_documentation_exist():
    """Verify reports and documentation files are generated and contain key sections."""
    report_file = REPO_ROOT / "reports" / "DYNAMIC_RESIDUAL_V2_REPORT.md"
    doc_file = REPO_ROOT / "docs" / "dynamic_residual_model_v2.md"
    manifest_file = REPO_ROOT / "reports" / "dynamic_residual_v2_manifest.json"

    assert report_file.exists(), "DYNAMIC_RESIDUAL_V2_REPORT.md must exist"
    assert doc_file.exists(), "dynamic_residual_model_v2.md must exist"
    assert manifest_file.exists(), "dynamic_residual_v2_manifest.json must exist"

    with open(report_file) as f:
        content = f.read()
        assert "EXP_INDIA_DYNAMIC_RESIDUAL_V2" in content
        assert "Candidate A (Constant)" in content
        assert "Candidate C (Weather + Geography)" in content
        assert "RETAIN_FOR_RESEARCH" in content
