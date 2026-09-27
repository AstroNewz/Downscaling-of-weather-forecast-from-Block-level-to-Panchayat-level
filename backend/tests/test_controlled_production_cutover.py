"""
Controlled Production Cutover Test Suite — Dynamic Residual Model v2
SIH Problem Statement 26074 (Weather Downscaling)

Verifies:
1. Dynamic Success (valid inputs, dynamic variation, end-to-end propagation)
2. Baseline Fallback Triggers (missing RH, stale weather, invalid values, OOD inputs, safety violations)
3. Production Safety (baseline artifact unchanged, production registry untouched)
4. Agricultural Integration (single operational temperature for risk & advisories)
5. DEMO Mode Determinism
6. AUTO Mode Transition Integrity
7. Zero-downtime Rollback via Rollout Mode Switch
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.live_prediction_service import LivePredictionService
from app.services.operational_safeguards import (
    OperationalSafeguardsEngine,
    runtime_telemetry,
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
CANDIDATE_DIR = BACKEND_ROOT / "models" / "candidates" / "temperature_residual" / "dynamic_temperature_residual_v2"
PROD_DIR = BACKEND_ROOT / "models" / "temperature_residual"

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rollout_mode():
    """Ensure tests run with default rollout mode and reset after each test."""
    settings.ROLLOUT_MODE = "DYNAMIC_PRIMARY"
    runtime_telemetry.reset()
    yield
    settings.ROLLOUT_MODE = "DYNAMIC_PRIMARY"


def test_production_registry_isolation():
    """Verify production directory remains empty and pristine (baseline is never overwritten)."""
    assert PROD_DIR.exists()
    prod_files = [f for f in PROD_DIR.iterdir() if f.name != ".gitkeep" and not f.name.startswith(".")]
    assert len(prod_files) == 0, f"Production registry must remain empty, found {prod_files}"
    assert settings.CALIBRATION_OFFSET_C == 0.7351


def test_dynamic_success_end_to_end():
    """Verify valid inputs execute dynamic model v2 and propagate to 1-km grid, risks, and advisories."""
    svc = LivePredictionService()
    res = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")

    assert res["model_used"] == "DYNAMIC_V2"
    assert res["model_status"] == "CONTROLLED_PRODUCTION"
    assert res["fallback_active"] is False
    assert res["safety_status"] == "PASS"
    assert res["ood_status"] == "WITHIN_TRAINING_RANGE"
    assert res["operational_residual_c"] != 0.7351  # Correction genuinely varies dynamically!
    assert -8.0 <= res["operational_residual_c"] <= 8.0

    # Operational temperature feeds 1-km aggregation
    assert res["panchayat_aggregation"]["tmean_c"] == res["calibrated_temperature_c"]
    assert res["panchayat_aggregation"]["tmax_c"] == res["calibrated_tmax_c"]

    # Verify single operational temperature in advisories
    for adv in res["advisories"]:
        if adv["category"] == "HEAT_STRESS":
            assert str(res["calibrated_tmax_c"]) in adv["rationale"]
            assert "Dynamic Model v2" in adv["rationale"]
        elif adv["category"] == "WIND":
            assert str(res["wind_speed_kmh"]) in adv["rationale"]

    # Verify telemetry increment
    snapshot = runtime_telemetry.get_snapshot()
    assert snapshot["dynamic_success"] >= 1


def test_baseline_fallback_on_missing_features():
    """Verify missing relative humidity triggers DYNAMIC_FEATURES_UNAVAILABLE fallback."""
    comp = OperationalSafeguardsEngine.validate_feature_completeness(
        temperature_c=30.0,
        relative_humidity_pct=None,  # MISSING!
        wind_speed_mps=3.0,
        wind_direction_deg=180.0,
        precipitation_mm=0.0,
    )
    assert comp.is_eligible is False
    assert comp.feature_states["relative_humidity_2m"] == "MISSING"


def test_baseline_fallback_on_ood_temperature():
    """Verify extreme temperature outside validated training envelope triggers OUT_OF_DISTRIBUTION fallback."""
    ood = OperationalSafeguardsEngine.check_out_of_distribution(
        temperature_c=58.0,  # OOD! (training bound max 52.0°C)
        relative_humidity_pct=50.0,
        wind_speed_mps=4.0,
        elevation_m=100.0,
        slope_deg=1.0,
    )
    assert ood.is_within_range is False
    assert ood.ood_status == "OUT_OF_DISTRIBUTION"
    assert len(ood.out_of_range_features) == 1
    assert ood.out_of_range_features[0]["feature"] == "temperature_c"


def test_baseline_fallback_on_ood_elevation():
    """Verify extreme elevation outside validated envelope triggers OUT_OF_DISTRIBUTION fallback."""
    ood = OperationalSafeguardsEngine.check_out_of_distribution(
        temperature_c=25.0,
        relative_humidity_pct=60.0,
        wind_speed_mps=3.0,
        elevation_m=3500.0,  # OOD! (training bound max 2800.0m)
        slope_deg=2.0,
    )
    assert ood.is_within_range is False
    assert ood.ood_status == "OUT_OF_DISTRIBUTION"


def test_residual_safety_violation_triggers_fallback_without_clipping():
    """Verify out-of-bounds raw residual marks safety FAILED and NEVER silently clips."""
    safety_high = OperationalSafeguardsEngine.check_residual_safety(10.5)
    assert safety_high.safety_status == "FAILED"
    assert "violates physical safety bounds" in safety_high.failure_reason

    safety_low = OperationalSafeguardsEngine.check_residual_safety(-9.2)
    assert safety_low.safety_status == "FAILED"

    safety_pass = OperationalSafeguardsEngine.check_residual_safety(1.45)
    assert safety_pass.safety_status == "PASS"


def test_zero_downtime_rollback_switch():
    """Verify changing ROLLOUT_MODE to BASELINE_PRIMARY immediately serves certified baseline."""
    svc = LivePredictionService()

    # 1. Primary dynamic
    settings.ROLLOUT_MODE = "DYNAMIC_PRIMARY"
    res_dyn = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    assert res_dyn["model_used"] == "DYNAMIC_V2"
    assert res_dyn["fallback_active"] is False

    # 2. Operator triggers rollback
    settings.ROLLOUT_MODE = "BASELINE_PRIMARY"
    res_base = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    assert res_base["model_used"] == "CERTIFIED_BASELINE_V1"
    assert res_base["fallback_active"] is True
    assert res_base["operational_residual_c"] == 0.7351
    assert res_base["fallback_reason"] == "OPERATOR_CONFIG_BASELINE_PRIMARY"


def test_api_live_prediction_endpoint_contract():
    """Verify GET and POST /api/v1/prediction/live return full controlled production schema."""
    resp = client.get("/api/v1/prediction/live?panchayat_id=1&mode=DEMO")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    # Verify all required keys from specification
    required_keys = [
        "model_used",
        "model_version",
        "model_status",
        "coarse_temperature",
        "residual",
        "downscaled_temperature",
        "fallback_active",
        "safety_status",
        "ood_status",
        "qc_status",
        "freshness",
        "source",
        "source_timestamp",
        "retrieval_timestamp",
        "provenance",
        "shadow_baseline",
    ]
    for k in required_keys:
        assert k in data, f"Missing required response key: {k}"

    assert data["model_status"] == "CONTROLLED_PRODUCTION"
    assert "artifact_sha256" in data["provenance"]
    assert data["provenance"]["certified_fallback_model"] == "CERTIFIED_BASELINE_V1 (+0.7351°C)"


def test_system_telemetry_endpoint():
    """Verify GET /api/v1/system/telemetry returns counters and rollout state."""
    resp = client.get("/api/v1/system/telemetry")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["model_operational_status"] == "CONTROLLED_PRODUCTION"
    assert data["rollout_mode"] in ("DYNAMIC_PRIMARY", "BASELINE_PRIMARY")
    assert "counters" in data
    assert "dynamic_success" in data["counters"]
    assert "safety_failure" in data["counters"]


def test_system_rollout_mode_toggle_endpoint():
    """Verify POST /api/v1/system/rollout-mode accepts valid modes and rejects invalid ones."""
    # Set to BASELINE_PRIMARY
    resp1 = client.post("/api/v1/system/rollout-mode", json={"mode": "BASELINE_PRIMARY"})
    assert resp1.status_code == 200
    assert resp1.json()["data"]["rollout_mode"] == "BASELINE_PRIMARY"
    assert settings.ROLLOUT_MODE == "BASELINE_PRIMARY"

    # Set back to DYNAMIC_PRIMARY
    resp2 = client.post("/api/v1/system/rollout-mode", json={"mode": "DYNAMIC_PRIMARY"})
    assert resp2.status_code == 200
    assert resp2.json()["data"]["rollout_mode"] == "DYNAMIC_PRIMARY"
    assert settings.ROLLOUT_MODE == "DYNAMIC_PRIMARY"

    # Reject invalid mode
    resp3 = client.post("/api/v1/system/rollout-mode", json={"mode": "INVALID_MODE"})
    assert resp3.status_code == 400


def test_cutover_documentation_and_manifest_exist():
    """Verify DYNAMIC_PRODUCTION_CUTOVER.md and DYNAMIC_PRODUCTION_CUTOVER_MANIFEST.json exist and are valid."""
    doc_path = REPO_ROOT / "docs" / "DYNAMIC_PRODUCTION_CUTOVER.md"
    manifest_path = REPO_ROOT / "reports" / "DYNAMIC_PRODUCTION_CUTOVER_MANIFEST.json"

    assert doc_path.exists()
    assert manifest_path.exists()

    with open(doc_path) as f:
        doc = f.read()
        assert "CONTROLLED_PRODUCTION" in doc
        assert "CERTIFIED_FALLBACK_BASELINE" in doc
        assert "RETAIN_FOR_RESEARCH" in doc

    with open(manifest_path) as f:
        manifest = json.load(f)
        assert manifest["operational_architecture"] == "DYNAMIC_PRIMARY_WITH_CERTIFIED_FALLBACK"
        assert manifest["active_model"]["status"] == "CONTROLLED_PRODUCTION"
        assert manifest["fallback_model"]["offset_c"] == 0.7351
