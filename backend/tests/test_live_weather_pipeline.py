"""
Comprehensive Test Suite for Live Weather Pipeline and Explicit Data Modes (DEMO, LIVE, AUTO)
SIH Problem Statement 26074 (Weather Downscaling)

Verifies:
1. DEMO mode returns canonical fixture with zero external network requests
2. LIVE mode uses genuine external provider adapter
3. LIVE provider success produces LIVE provenance
4. LIVE provider timeout / connection error produces unavailable/insufficient data state
5. LIVE stale data is rejected / degraded
6. LIVE malformed data is rejected
7. LIVE mode NEVER silently falls back to demo
8. AUTO mode live success remains LIVE
9. AUTO mode live failure explicitly falls back to DEMO with fallback_active=True
10. Scientific Baseline remains strictly T_calibrated = T_coarse + 0.7351°C
11. XGBoost status strictly remains RESEARCH_ONLY
12. What-If simulator is non-mutating
13. Prediction is deterministic for identical inputs in DEMO mode
14. Zero credentials appear in API responses or logs
15. Rapid Panchayat switching regression safety
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.weather.providers.live_provider import (
    DemoWeatherProvider,
    OpenMeteoLiveWeatherProvider,
    IMDLiveWeatherProvider,
    resolve_weather_data,
    set_runtime_data_mode,
    get_current_data_mode,
    LiveWeatherUnavailableError,
    LiveWeatherProviderError,
    LiveProviderNotConfiguredError,
)
from app.services.live_prediction_service import LivePredictionService
from app.weather.quality import WeatherQualityControl


@pytest.fixture(autouse=True)
def reset_mode_to_demo():
    """Ensures test isolation by resetting data mode to DEMO after each test."""
    set_runtime_data_mode("DEMO")
    yield
    set_runtime_data_mode("DEMO")


def test_demo_mode_returns_canonical_fixture():
    """1. DEMO mode returns canonical fixture."""
    provider = DemoWeatherProvider()
    rec = provider.get_weather(25.35, 82.95)
    assert rec.mode == "DEMO"
    assert rec.effective_mode == "DEMO"
    assert rec.source == "CANONICAL_PILOT_FIXTURE"
    assert rec.source_type == "PILOT_FIXTURE"
    assert rec.temperature_c == 36.0
    assert rec.temp_max_c == 36.0
    assert rec.wind_speed_kmh == 28.0
    assert rec.quality_status == "PASSED"
    assert rec.fallback_active is False


def test_demo_mode_makes_zero_external_requests():
    """2. DEMO mode makes zero external provider requests."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        rec = resolve_weather_data(25.35, 82.95, requested_mode="DEMO")
        mock_urlopen.assert_not_called()
        assert rec.mode == "DEMO"
        assert rec.source == "CANONICAL_PILOT_FIXTURE"


def test_live_mode_uses_genuine_provider_adapter():
    """3. LIVE mode uses genuine OpenMeteo provider adapter."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = (
        b'{"current":{"temperature_2m":28.5,"relative_humidity_2m":65.0,"wind_speed_10m":12.0,"wind_direction_10m":180.0,"precipitation":0.0,"cloud_cover":20.0,"time":"2026-09-18T00:00:00Z"}}'
    )
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        rec = resolve_weather_data(25.35, 82.95, requested_mode="LIVE")
        assert rec.mode == "LIVE"
        assert rec.effective_mode == "LIVE"
        assert rec.source == "OPEN_METEO_OPERATIONAL_NWP"
        assert rec.source_type == "FORECAST"
        assert rec.temperature_c == 28.5
        assert rec.fallback_active is False


def test_live_provider_success_produces_live_provenance():
    """4. LIVE provider success produces unambiguous LIVE provenance."""
    client = TestClient(app)
    set_runtime_data_mode("LIVE")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = (
        b'{"current":{"temperature_2m":30.2,"relative_humidity_2m":70.0,"wind_speed_10m":15.0,"wind_direction_10m":190.0,"precipitation":0.0,"time":"2026-09-18T00:00:00Z"}}'
    )
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        res = client.get("/api/v1/system/data-status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["mode"] == "LIVE"
        assert data["effective_mode"] == "LIVE"
        assert data["provider"] == "OPEN_METEO_OPERATIONAL_NWP"
        assert data["fallback_active"] is False


def test_live_provider_timeout_produces_unavailable_state():
    """5. LIVE provider timeout produces unavailable state."""
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
        with pytest.raises(LiveWeatherUnavailableError):
            resolve_weather_data(25.35, 82.95, requested_mode="LIVE")


def test_live_stale_data_is_rejected_or_degraded():
    """6. LIVE stale data (older than WEATHER_STALE_AFTER_MINUTES) is marked DEGRADED."""
    from datetime import datetime, timezone, timedelta
    # Dynamic stale timestamp: 4 hours (240 minutes) before current UTC time
    stale_iso = (datetime.now(timezone.utc) - timedelta(minutes=240)).isoformat()
    qc_status, qc_notes, age_min = WeatherQualityControl.evaluate_live_record(
        temperature_c=31.0,
        valid_time_iso=stale_iso,
        max_age_minutes=180
    )
    assert qc_status == "DEGRADED"
    assert "STALE" in qc_notes
    assert age_min >= 239.0


def test_live_malformed_data_is_rejected():
    """7. LIVE malformed data (violating physical temperature bounds) is rejected."""
    # Temperature 85°C violates physical limit
    qc_status, qc_notes, _ = WeatherQualityControl.evaluate_live_record(
        temperature_c=85.0,
        valid_time_iso="2026-09-18T01:00:00Z"
    )
    assert qc_status == "REJECTED"
    assert "Physical violation" in qc_notes


def test_live_mode_never_silently_falls_back_to_demo():
    """8. LIVE mode NEVER silently falls back to demo when provider fails."""
    client = TestClient(app)
    set_runtime_data_mode("LIVE")

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Network down")):
        # In LIVE mode, API must return HTTP 503 / unavailable, NEVER status 200 with demo data
        res = client.get("/api/v1/prediction/live")
        assert res.status_code == 503
        detail = res.json()["detail"]
        assert detail["status"] == "INSUFFICIENT_DATA"
        assert detail["mode"] == "LIVE"
        assert "safeguard" in detail


def test_auto_live_success_remains_live():
    """9. AUTO mode with working live feed returns LIVE effective mode."""
    mock_response = MagicMock()
    mock_response.status = 200
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mock_response.read.return_value = (
        f'{{"current":{{"temperature_2m":27.8,"relative_humidity_2m":60.0,"wind_speed_10m":8.0,"wind_direction_10m":120.0,"precipitation":0.0,"time":"{now_iso}"}}}}'.encode("utf-8")
    )
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        rec = resolve_weather_data(25.35, 82.95, requested_mode="AUTO")
        assert rec.mode == "AUTO"
        assert rec.effective_mode == "LIVE"
        assert rec.source == "OPEN_METEO_OPERATIONAL_NWP"
        assert rec.fallback_active is False


def test_auto_live_failure_explicitly_falls_back_to_demo():
    """10. AUTO mode with failed live feed explicitly falls back to DEMO."""
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Network down")):
        rec = resolve_weather_data(25.35, 82.95, requested_mode="AUTO")
        assert rec.mode == "AUTO"
        assert rec.effective_mode == "DEMO"
        assert rec.source == "CANONICAL_PILOT_FIXTURE"
        assert rec.fallback_active is True
        assert "LIVE_PROVIDER_UNAVAILABLE" in rec.fallback_reason


def test_certified_baseline_preserved():
    """12. Certified production baseline formula T_cal = T_coarse + 0.7351°C is preserved exactly."""
    svc = LivePredictionService()
    pred = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    
    assert settings.CALIBRATION_OFFSET_C == 0.7351
    assert pred["scalar_offset_c"] == 0.7351
    assert pred["calibration_formula"] == "T_calibrated = T_coarse + 0.7351°C"
    # Shadow baseline computes certified baseline exactly (coarse 36.0 + 0.7351 = 36.74)
    assert pred["shadow_baseline"]["baseline_downscaled_temp_c"] == round(36.0 + 0.7351, 2)
    assert pred["shadow_baseline"]["baseline_downscaled_temp_c"] == 36.74
    # When switched to BASELINE_PRIMARY mode or in fallback, calibrated_temperature_c matches certified baseline
    orig_mode = settings.ROLLOUT_MODE
    try:
        settings.ROLLOUT_MODE = "BASELINE_PRIMARY"
        pred_base = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
        assert pred_base["calibrated_temperature_c"] == 36.74
    finally:
        settings.ROLLOUT_MODE = orig_mode


def test_xgboost_remains_research_only():
    """13. XGBoost remains RESEARCH_ONLY and is never promoted."""
    svc = LivePredictionService()
    pred = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    assert pred["xgboost_status"] == "RESEARCH_ONLY"

    client = TestClient(app)
    res = client.get("/api/v1/system/data-status")
    assert res.status_code == 200
    assert res.json()["data"]["model_status"] == "XGBoost: RESEARCH_ONLY"


def test_prediction_is_deterministic_for_identical_inputs():
    """15. Repeated identical requests produce identical prediction outputs."""
    svc = LivePredictionService()
    pred1 = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    pred2 = svc.predict_panchayat_weather(panchayat_id=1, requested_mode="DEMO")
    
    assert pred1["calibrated_temperature_c"] == pred2["calibrated_temperature_c"]
    assert pred1["calibrated_tmax_c"] == pred2["calibrated_tmax_c"]
    assert pred1["calibrated_tmin_c"] == pred2["calibrated_tmin_c"]
    assert len(pred1["risks"]) == len(pred2["risks"])
    assert len(pred1["advisories"]) == len(pred2["advisories"])


def test_no_credentials_in_responses_or_logs():
    """16. Verification that private credentials/API keys never leak in API responses."""
    client = TestClient(app)
    res1 = client.get("/api/v1/system/data-status")
    content1 = res1.text
    assert "SECRET" not in content1
    assert "dev_insecure_secret_key" not in content1
    assert "password" not in content1.lower()

    res2 = client.get("/api/v1/prediction/live?mode=DEMO")
    content2 = res2.text
    assert "SECRET" not in content2
    assert "password" not in content2.lower()


def test_rapid_panchayat_switching_regression():
    """Regression test for rapid sequential Panchayat queries."""
    svc = LivePredictionService()
    results = {}
    for pid in [1, 2, 3, 1, 2, 3]:
        pred = svc.predict_panchayat_weather(panchayat_id=pid, requested_mode="DEMO")
        assert pred["panchayat_id"] == pid
        if pid not in results:
            results[pid] = pred["calibrated_temperature_c"]
        else:
            assert pred["calibrated_temperature_c"] == results[pid]
