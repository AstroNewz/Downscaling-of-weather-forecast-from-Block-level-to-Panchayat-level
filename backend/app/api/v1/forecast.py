"""
Unified Forecast API Router
SIH Problem Statement 26074 (AgroWeather Downscaling & Agromet Advisory)

GET /api/v1/forecast - Full multi-day & hourly downscaled forecast + agro-risk engine
GET /api/v1/forecast/locations - Searchable preset panchayats, blocks, and reference cities
"""
from typing import Optional
from fastapi import APIRouter, Query, Response
from app.services.forecast_service import forecast_service, PRESET_LOCATIONS

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("", summary="Get unified 7-day downscaled weather and agro-advisories")
def get_forecast_endpoint(
    response: Response,
    location_id: Optional[str] = Query(None, description="Preset ID or Location name (e.g. Maya Bazar Panchayat, 1, Varanasi)"),
    location_type: Optional[str] = Query(None, description="Location type: PANCHAYAT, BLOCK, CITY, or CUSTOM_COORDINATE"),
    latitude: Optional[float] = Query(None, description="Optional latitude coordinate"),
    longitude: Optional[float] = Query(None, description="Optional longitude coordinate"),
    target_date: Optional[str] = Query(None, description="Target forecast date in YYYY-MM-DD format (defaults to today)"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    timezone: Optional[str] = Query("Asia/Kolkata", description="IANA timezone identifier"),
    mode: Optional[str] = Query(None, description="Requested mode: 'AUTO', 'LIVE', or 'DEMO'"),
):
    # Set strict anti-stale caching headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    result = forecast_service.get_forecast(
        location_id=location_id,
        location_type=location_type,
        latitude=latitude,
        longitude=longitude,
        target_date=target_date,
        start_date=start_date,
        end_date=end_date,
        timezone_str=timezone,
        requested_mode=mode,
    )
    return result


@router.get("/locations", summary="List searchable preset Panchayats, Blocks, and Cities")
def get_preset_locations(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    locations_list = list(PRESET_LOCATIONS.values())
    return {"locations": locations_list, "total": len(locations_list)}
