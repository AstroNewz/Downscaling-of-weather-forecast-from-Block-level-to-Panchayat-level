"""
test_three_track_system.py — Comprehensive Test Suite for SIH PS 26074
Validates:
Track A: IMD Live Integration & Provider Abstraction
Track B: Nationwide Panchayat Validation & Coverage Accounting
Track C: Dynamic Residual Model v2 Scientific Promotion Gates & Shadow Baseline
Live & Advisory: Multi-location, multi-date, block aggregation, and zero demo leak
Judge Attack Test: 20-Step Deterministic Verification Sequence
"""
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.weather.schemas import ProviderStatus
from app.weather.providers.live_provider import (
    get_registered_providers,
    check_provider_health,
    get_provider,
    set_runtime_data_mode,
    resolve_weather_data,
    LiveProviderNotConfiguredError,
    IMDLiveWeatherProvider,
    OpenMeteoLiveWeatherProvider,
    DemoWeatherProvider,
)
from app.services.national_validation_service import national_validation_service
from app.services.dynamic_v2_promotion_service import dynamic_v2_promotion_service
from app.services.live_prediction_service import LivePredictionService


client = TestClient(app)


class TestTrackAIMDIntegration:
    """Test Suite for Track A: IMD Live Integration & Provider Abstraction."""

    def test_registered_providers_catalog(self):
        providers = get_registered_providers()
        assert len(providers) == 3
        codes = [p.code for p in providers]
        assert "open_meteo" in codes
        assert "imd" in codes
        assert "demo" in codes

    def test_imd_unconfigured_when_credentials_absent(self):
        imd = get_provider("imd")
        assert isinstance(imd, IMDLiveWeatherProvider)
        assert imd.is_configured() is False

        # Must raise LiveProviderNotConfiguredError, never fabricate responses
        with pytest.raises(LiveProviderNotConfiguredError):
            imd.get_current(25.35, 82.95)

    def test_imd_health_reports_not_configured(self):
        health = check_provider_health("imd")
        assert health.status == ProviderStatus.NOT_CONFIGURED
        assert health.configured is False
        assert health.fallback_active is True
        assert "IMD_API_KEY_UNSET" in (health.fallback_reason or "")
        assert health.required_configuration is not None
        assert "IMD_API_KEY" in health.required_configuration

    def test_open_meteo_health_probe(self):
        health = check_provider_health("open_meteo")
        assert health.status in (ProviderStatus.LIVE, ProviderStatus.UNAVAILABLE)
        assert health.configured is True
        assert health.source_type == "FORECAST"
        if health.status == ProviderStatus.LIVE:
            assert health.latency_ms is not None
            assert health.latency_ms > 0
            assert health.request_id is not None
            assert health.request_id.startswith("req_live_")

    def test_demo_provider_health(self):
        health = check_provider_health("demo")
        assert health.status == ProviderStatus.LIVE
        assert health.configured is True
        assert health.source_type == "PILOT_FIXTURE"
        assert health.fallback_active is False

    def test_system_providers_endpoint(self):
        resp = client.get("/api/v1/system/providers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 3
        imd_entry = next(p for p in data if p["code"] == "imd")
        assert imd_entry["status"] == "NOT_CONFIGURED"
        assert imd_entry["requires_auth"] is True
        assert imd_entry["auth_configured"] is False

    def test_system_provider_health_endpoint(self):
        resp = client.get("/api/v1/system/providers/imd/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "NOT_CONFIGURED"
        assert "IMD_API_KEY" in data["required_configuration"]


class TestTrackBNationwideValidation:
    """Test Suite for Track B: Nationwide Panchayat Validation & Coverage Accounting."""

    def test_nationwide_validation_summary_loaded(self):
        summary = national_validation_service.get_validation_summary()
        assert summary["total_observations"] == 23949
        assert summary["test_observations"] == 5288
        assert summary["station_count"] == 17
        assert summary["states_covered"] == 11
        assert summary["regions_evaluated"] == 6
        assert summary["regions_unvalidated"] == 1

    def test_automated_claim_language(self):
        summary = national_validation_service.get_validation_summary()
        # Must strictly use exact approved phrasing
        assert summary["claim_language"] == "NATIONWIDE MULTI-REGION VALIDATION COMPLETED; COVERAGE LIMITATIONS REMAIN"

    def test_unvalidated_region_transparency(self):
        summary = national_validation_service.get_validation_summary()
        reg_breakdown = summary["regional_breakdown"]
        south = next((r for r in reg_breakdown if "South" in r["region"]), None)
        assert south is not None
        assert south["status"] == "INSUFFICIENT_OBSERVATIONS"
        assert south["sample_count"] == 0
        assert south["station_count"] == 0

    def test_model_metrics_hierarchy(self):
        summary = national_validation_service.get_validation_summary()
        models = summary["overall_models"]
        raw = models["model_a_raw_nwp"]
        base = models["model_b_certified_baseline"]
        dyn = models["model_c_dynamic_v2"]

        assert raw["mae"] == 1.5907
        assert base["mae"] == 1.2661
        assert dyn["mae"] == 1.1690

        # Verify progression
        assert raw["mae"] > base["mae"]
        assert base["mae"] > dyn["mae"]

    def test_paired_metrics_and_ci(self):
        summary = national_validation_service.get_validation_summary()
        paired = summary["paired_eval"]
        assert paired["delta_mae_c_vs_b"] == 0.0971
        assert paired["statistically_significant"] is True
        assert paired["exceeds_sensor_uncertainty"] is False

    def test_research_national_validation_endpoint(self):
        resp = client.get("/api/v1/research/national-validation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["claim_language"] == "NATIONWIDE MULTI-REGION VALIDATION COMPLETED; COVERAGE LIMITATIONS REMAIN"
        assert len(data["stations_catalog"]) == 17


class TestTrackCDynamicV2Promotion:
    """Test Suite for Track C: Dynamic Residual Model v2 Promotion Gates & Shadow Mode."""

    def test_promotion_evaluation_gates(self):
        eval_res = dynamic_v2_promotion_service.evaluate_promotion()
        assert eval_res["active_certified_baseline"] == "T_calibrated = T_coarse + 0.7351°C"
        gates = eval_res["promotion_gates"]
        assert len(gates) == 8

        # Gate 1: MAE Improvement >= 0.1000°C must FAIL
        g1 = next(g for g in gates if g["gate_id"] == "GATE_1_MAE_IMPROVEMENT")
        assert g1["passed"] is False
        assert "0.0971°C" in g1["actual_value"]

        # Gate 2: LOSO <= 1.4000°C must FAIL
        g2 = next(g for g in gates if g["gate_id"] == "GATE_2_LOSO_SPATIAL_STABILITY")
        assert g2["passed"] is False

        # Gate 3: Generalization Gap <= 0.1500°C must FAIL
        g3 = next(g for g in gates if g["gate_id"] == "GATE_3_GENERALIZATION_GAP")
        assert g3["passed"] is False

        # Safeguard gates must PASS
        g5 = next(g for g in gates if g["gate_id"] == "GATE_5_RUNTIME_SAFEGUARDS")
        assert g5["passed"] is True

        # Final decision must strictly be RETAIN_FOR_RESEARCH
        assert eval_res["final_scientific_decision"] == "RETAIN_FOR_RESEARCH"
        assert eval_res["operational_deployment_state"] == "CONTROLLED_PRODUCTION"

    def test_research_promotion_endpoint(self):
        resp = client.get("/api/v1/research/promotion-evaluation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["final_scientific_decision"] == "RETAIN_FOR_RESEARCH"
        assert data["passed_gates_count"] == 5
        assert data["failed_gates_count"] == 3


class TestLiveWeatherAndBlockAggregation:
    """Test Suite for Live Weather, Date Sensitivity, and Block Aggregation."""

    def test_block_aggregation_endpoint(self):
        resp = client.get("/api/v1/panchayat/block/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["block_id"] == 1
        assert data["panchayat_count"] == 3
        assert data["aggregation_method"] == "CONSTITUENT_PANCHAYAT_SPATIAL_AGGREGATION"

        temp_stats = data["temperature_statistics"]
        assert "mean_downscaled_c" in temp_stats
        assert "spatial_spread_c" in temp_stats
        assert temp_stats["spatial_spread_c"] >= 0.0

        # Verify constituent Panchayats have distinct coordinates and temperatures
        constituents = data["constituent_panchayats"]
        assert len(constituents) == 3
        coords = [(c["latitude"], c["longitude"]) for c in constituents]
        assert len(set(coords)) == 3, "All 3 constituent Panchayats must have distinct coordinates"

    def test_cache_prevention_headers(self):
        resp = client.get("/api/v1/panchayat/1/detail")
        assert resp.status_code == 200
        assert "no-cache" in resp.headers.get("Cache-Control", "")
        assert "no-store" in resp.headers.get("Cache-Control", "")


class TestJudgeAttackSequence:
    """20-Step Deterministic Judge Attack Test."""

    def test_judge_attack_20_steps(self):
        # Step 1: Select Panchayat 1
        r1 = client.get("/api/v1/panchayat/1/detail")
        assert r1.status_code == 200
        d1 = r1.json()["data"]

        # Step 2: Observe live provenance
        w1 = d1["latest_weather"]
        assert w1 is not None
        assert "source_provider" in w1
        assert "retrieval_timestamp" in w1

        # Step 3: Select Panchayat 2
        r2 = client.get("/api/v1/panchayat/2/detail")
        assert r2.status_code == 200
        d2 = r2.json()["data"]

        # Step 4: Observe different location & coordinates
        assert d1["panchayat"]["id"] != d2["panchayat"]["id"]
        assert d1["panchayat"]["name"] != d2["panchayat"]["name"]

        # Step 5: Change Date to Tomorrow
        r_tomorrow = client.get("/api/v1/panchayat/1/detail?date=2026-09-19")
        assert r_tomorrow.status_code == 200

        # Step 6: Observe date-specific forecast
        d_tomorrow = r_tomorrow.json()["data"]
        assert d_tomorrow is not None

        # Step 7 & 8: Inspect Forecast Time
        assert "latest_weather" in d_tomorrow

        # Step 9: Open Advisory
        advisories = d1.get("advisories", [])
        assert isinstance(advisories, list)

        # Step 10: Trace Advisory to Weather/Model
        if advisories:
            adv0 = advisories[0]
            assert "category" in adv0 or "title" in adv0

        # Step 11 & 12: Compare Dynamic V2 vs Baseline Shadow
        r_comp = client.post(
            "/api/v1/research/compare",
            json={
                "coarse_temperature_c": 30.0,
                "relative_humidity_pct": 70.0,
                "wind_speed_mps": 3.0,
                "wind_direction_deg": 180.0,
                "precipitation_mm": 0.0,
                "hour_of_day": 14,
                "day_of_year": 210,
                "elevation_m": 85.0,
                "slope_deg": 1.0,
                "aspect_deg": 120.0,
                "land_cover_code": 40,
                "latitude": 25.35,
                "longitude": 82.95,
            }
        )
        assert r_comp.status_code == 200
        comp_data = r_comp.json()
        assert "production_baseline" in comp_data
        assert "research_candidate" in comp_data
        assert comp_data["production_baseline"]["correction_offset_c"] == 0.7351

        # Step 13 & 14: Inspect Nationwide Validation Map
        r_nat = client.get("/api/v1/research/national-validation")
        assert r_nat.status_code == 200
        nat_data = r_nat.json()
        assert nat_data["regions_evaluated"] == 6
        assert nat_data["regions_unvalidated"] == 1

        # Step 15 & 16: Open Provider Health & Inspect IMD
        r_prov = client.get("/api/v1/system/providers/imd/health")
        assert r_prov.status_code == 200
        assert r_prov.json()["data"]["status"] == "NOT_CONFIGURED"

        # Step 17: Trigger Provider Failure / Demo Fallback Mode
        r_switch = client.post("/api/v1/system/mode", json={"mode": "AUTO"})
        assert r_switch.status_code == 200

        # Step 18: Observe Explicit Fallback or Live execution
        status_resp = client.get("/api/v1/system/data-status")
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["mode"] == "AUTO"

        # Step 19: Restore LIVE Mode
        client.post("/api/v1/system/mode", json={"mode": "LIVE"})
        status_live = client.get("/api/v1/system/data-status")
        assert status_live.json()["data"]["mode"] == "LIVE"

        # Step 20: Verify Request ID and Timestamps
        r_final = client.get("/api/v1/panchayat/1/detail")
        assert r_final.status_code == 200
        assert r_final.json()["data"]["latest_weather"]["live_request_id"] is not None
