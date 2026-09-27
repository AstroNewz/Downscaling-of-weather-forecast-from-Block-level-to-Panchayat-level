"""
Tests for Unified Forecast API & Contract (SIH PS 26074)
Verifies:
1. Different locations produce geographically differentiated results
2. Different dates produce distinct forecast timestamps & horizons
3. Diurnal curve has hourly variation (not static)
4. Advisory and risk dates match forecast date (Advisory Consistency Engine)
5. Zero inappropriate July 2026 hardcoding
6. Strict anti-stale caching headers (no-store, no-cache)
"""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.forecast_service import forecast_service

client = TestClient(app)


def test_forecast_api_basic():
    """Verify GET /api/v1/forecast returns valid structure and anti-cache headers."""
    resp = client.get("/api/v1/forecast?location_id=1")
    assert resp.status_code == 200
    assert "no-store" in resp.headers.get("cache-control", "").lower()
    
    data = resp.json()
    assert "location" in data
    assert "current" in data
    assert "daily_forecast" in data
    assert "today_hourly_chart" in data
    assert "agricultural_risks" in data
    assert "farmer_actions" in data
    assert "provenance" in data
    assert len(data["daily_forecast"]) == 7
    assert len(data["today_hourly_chart"]) == 8


def test_forecast_locations_api():
    """Verify GET /api/v1/forecast/locations returns searchable presets."""
    resp = client.get("/api/v1/forecast/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert "locations" in data
    assert data["total"] >= 6
    names = [loc["name"] for loc in data["locations"]]
    assert any("Maya Bazar" in n for n in names)
    assert any("Cholapur" in n for n in names)
    assert any("Varanasi" in n for n in names)
    assert any("Delhi" in n for n in names)


def test_different_locations_different_results():
    """Verify different locations produce different geographic coordinates and temperatures."""
    loc1 = forecast_service.get_forecast(location_id="1", requested_mode="DEMO")
    loc2 = forecast_service.get_forecast(location_id="2", requested_mode="DEMO")
    delhi = forecast_service.get_forecast(location_id="delhi", requested_mode="DEMO")

    assert loc1["location"]["name"] != loc2["location"]["name"]
    assert loc1["location"]["latitude"] != loc2["location"]["latitude"]
    assert loc1["location"]["longitude"] != loc2["location"]["longitude"]
    assert delhi["location"]["name"] == "New Delhi"
    assert delhi["location"]["latitude"] == 28.6139


def test_different_dates_different_timestamps():
    """Verify date changes produce different forecast valid dates without stale leakage."""
    today_dt = datetime.now(timezone.utc) + timedelta(hours=5.5)
    today_str = today_dt.strftime("%Y-%m-%d")
    tomorrow_str = (today_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    day3_str = (today_dt + timedelta(days=3)).strftime("%Y-%m-%d")

    res_today = forecast_service.get_forecast(location_id="1", target_date=today_str, requested_mode="DEMO")
    res_tomorrow = forecast_service.get_forecast(location_id="1", target_date=tomorrow_str, requested_mode="DEMO")
    res_day3 = forecast_service.get_forecast(location_id="1", target_date=day3_str, requested_mode="DEMO")

    assert res_today["selected_date"] == today_str
    assert res_today["is_today"] is True
    assert res_tomorrow["selected_date"] == tomorrow_str
    assert res_tomorrow["is_today"] is False
    assert res_day3["selected_date"] == day3_str
    assert res_day3["is_today"] is False


def test_hourly_forecast_diurnal_curve():
    """Verify hourly forecast contains varying diurnal temperatures, not a static copy."""
    res = forecast_service.get_forecast(location_id="1", requested_mode="DEMO")
    hourly = res["full_hourly"]
    assert len(hourly) == 24
    
    temps = [h["downscaled_temperature_c"] for h in hourly]
    assert len(set(temps)) > 5, "Diurnal curve must not reuse a single static temperature across all hours"
    
    # Peak afternoon temperature should exceed minimum night temperature
    assert max(temps) > min(temps) + 1.0


def test_advisory_consistency_date_and_location():
    """Verify advisories and farmer actions correspond to the selected location and date."""
    target_date = "2026-09-28"
    res = forecast_service.get_forecast(location_id="2", target_date=target_date, requested_mode="DEMO")
    
    assert res["location"]["id"] == "2"
    assert res["selected_date"] == target_date
    assert res["selected_date_label"] == "Monday, 28 September"
    
    # Ensure risks and actions are generated
    assert len(res["agricultural_risks"]) >= 1
    assert len(res["farmer_actions"]) >= 1
    for act in res["farmer_actions"]:
        assert len(act["action"]) > 10
        assert len(act["why"]) > 5


def test_no_hardcoded_july_2026_default():
    """Verify that when no date is requested, the service defaults to today, never July 2026."""
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5.5)
    expected_today = now_ist.strftime("%Y-%m-%d")
    
    res = forecast_service.get_forecast(location_id="1", target_date=None, requested_mode="DEMO")
    assert res["selected_date"] == expected_today
    assert res["selected_date"] != "2026-07-15"
    assert res["is_today"] is True


def test_forecast_api_contract_parameters_and_fields():
    """Verify GET /api/v1/forecast supports start_date, end_date, timezone and returns all top-level keys."""
    resp = client.get("/api/v1/forecast?latitude=25.35&longitude=82.95&start_date=2026-09-25&end_date=2026-10-01&timezone=Asia/Kolkata&mode=DEMO")
    assert resp.status_code == 200
    data = resp.json()

    # Top-level required fields per section 4 & 6
    assert "location_id" in data
    assert "location_name" in data
    assert "latitude" in data
    assert "longitude" in data
    assert "forecast_date" in data
    assert "forecast_hour" in data
    assert "request_id" in data
    assert "generated_at" in data
    assert "source_timestamp" in data
    assert "forecast_valid_time" in data
    assert data["forecast_date"] == "2026-09-25"
    assert data["latitude"] == 25.35
    assert data["longitude"] == 82.95

    # Verify hourly items have full contract fields
    assert len(data["full_hourly"]) == 24
    first_hour = data["full_hourly"][0]
    required_hourly_keys = [
        "timestamp", "local_time", "hour", "coarse_temperature", "dynamic_residual",
        "downscaled_temperature", "humidity", "wind_speed", "wind_direction",
        "precipitation", "weather_code", "rain_probability", "model_used",
        "fallback_active", "risk", "advisory"
    ]
    for key in required_hourly_keys:
        assert key in first_hour, f"Missing required hourly field: {key}"

    # Verify 7-day cards
    assert len(data["daily_forecast"]) == 7
    first_day = data["daily_forecast"][0]
    assert "date" in first_day
    assert "day_label" in first_day
    assert "t_max_c" in first_day
    assert "t_min_c" in first_day
    assert "rainfall_mm" in first_day
    assert "rain_probability_pct" in first_day
    assert "primary_risk" in first_day


def test_advisories_and_risks_strict_consistency():
    """Verify all risks and advisories strictly match the target date and location."""
    res = forecast_service.get_forecast(location_id="2", target_date="2026-09-27", requested_mode="DEMO")
    
    assert res["location_id"] == "2"
    assert res["forecast_date"] == "2026-09-27"
    assert "Cholapur" in res["location_name"]

    # Check risks
    for r in res["agricultural_risks"]:
        assert r["date"] == "2026-09-27"
        assert "Cholapur" in r["location"]
        assert r["severity"] in ("LOW", "MODERATE", "HIGH", "SEVERE")

    # Check farmer actions
    for a in res["farmer_actions"]:
        assert a["date"] == "2026-09-27"
        assert "Cholapur" in a["location"]
        assert a["priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(a["action"]) > 10
        assert len(a["why"]) > 5

