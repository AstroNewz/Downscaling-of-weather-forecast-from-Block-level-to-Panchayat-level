"""
Research API Router — Dynamic Residual Downscaling Model v2
SIH Problem Statement 26074 — Agro-Meteorological Advisory Services

Exposes candidate research model endpoints with explicit governance markers:
- Status: strictly RESEARCH_ONLY
- Baseline: T_calibrated = T_coarse + 0.7351°C remains certified production standard
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.dynamic_downscaling_service import dynamic_downscaling_service

router = APIRouter(prefix="/research", tags=["Research Candidates"])


class DynamicDownscalingRequest(BaseModel):
    coarse_temperature_c: float = Field(..., description="Coarse NWP or ERA5 forecast temperature in °C")
    relative_humidity_pct: float = Field(65.0, description="Coarse relative humidity (0-100%)")
    wind_speed_mps: float = Field(2.5, description="Coarse wind speed at 10m in m/s")
    wind_direction_deg: float = Field(180.0, description="Wind direction in degrees (0-360)")
    precipitation_mm: float = Field(0.0, description="Precipitation accumulation in mm")
    hour_of_day: int = Field(12, description="Hour of day (0-23)", ge=0, le=23)
    day_of_year: int = Field(200, description="Day of year (1-366)", ge=1, le=366)
    elevation_m: float = Field(100.0, description="Local surface elevation in meters ASL")
    coarse_elevation_m: Optional[float] = Field(None, description="Coarse model elevation in meters ASL")
    slope_deg: float = Field(1.0, description="Local terrain slope in degrees")
    aspect_deg: float = Field(180.0, description="Local terrain aspect in degrees (0-360)")
    land_cover_code: int = Field(40, description="ESA WorldCover LULC code (e.g., 40=cropland, 50=urban)")
    latitude: float = Field(25.32, description="Latitude in decimal degrees")
    longitude: float = Field(82.98, description="Longitude in decimal degrees")


@router.get("/dynamic-downscaling")
def get_dynamic_downscaling(
    coarse_temperature_c: float = Query(28.0, description="Coarse NWP forecast temperature in °C"),
    relative_humidity_pct: float = Query(65.0, description="Coarse relative humidity (0-100%)"),
    wind_speed_mps: float = Query(2.5, description="Coarse wind speed at 10m in m/s"),
    wind_direction_deg: float = Query(180.0, description="Wind direction in degrees (0-360)"),
    precipitation_mm: float = Query(0.0, description="Precipitation accumulation in mm"),
    hour_of_day: int = Query(12, description="Hour of day (0-23)", ge=0, le=23),
    day_of_year: int = Query(200, description="Day of year (1-366)", ge=1, le=366),
    elevation_m: float = Query(100.0, description="Local surface elevation in meters ASL"),
    slope_deg: float = Query(1.0, description="Local terrain slope in degrees"),
    aspect_deg: float = Query(180.0, description="Local terrain aspect in degrees (0-360)"),
    land_cover_code: int = Query(40, description="ESA WorldCover LULC code"),
    latitude: float = Query(25.32, description="Latitude in decimal degrees"),
    longitude: float = Query(82.98, description="Longitude in decimal degrees"),
) -> Dict[str, Any]:
    """
    GET version of dynamic downscaling inference for browser address-bar and judge testing.
    """
    return dynamic_downscaling_service.predict_residual(
        coarse_temp=coarse_temperature_c,
        coarse_rh=relative_humidity_pct,
        coarse_wspd=wind_speed_mps,
        wind_direction_deg=wind_direction_deg,
        precipitation_mm=precipitation_mm,
        hour_of_day=hour_of_day,
        day_of_year=day_of_year,
        elevation_m=elevation_m,
        slope_deg=slope_deg,
        aspect_deg=aspect_deg,
        land_cover_code=land_cover_code,
        latitude=latitude,
        longitude=longitude,
    )


@router.post("/dynamic-downscaling")
def run_dynamic_downscaling(payload: DynamicDownscalingRequest) -> Dict[str, Any]:
    """
    Executes live inference on Dynamic Residual Downscaling Model v2.
    Returns dynamic residual correction, physical guardrail status, and side-by-side comparison
    with the certified scalar production baseline (+0.7351°C).
    """
    return dynamic_downscaling_service.predict_residual(
        coarse_temp=payload.coarse_temperature_c,
        coarse_rh=payload.relative_humidity_pct,
        coarse_wspd=payload.wind_speed_mps,
        wind_direction_deg=payload.wind_direction_deg,
        precipitation_mm=payload.precipitation_mm,
        hour_of_day=payload.hour_of_day,
        day_of_year=payload.day_of_year,
        elevation_m=payload.elevation_m,
        coarse_elevation_m=payload.coarse_elevation_m,
        slope_deg=payload.slope_deg,
        aspect_deg=payload.aspect_deg,
        land_cover_code=payload.land_cover_code,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )


@router.get("/diagnostic")
def get_research_diagnostic() -> Dict[str, Any]:
    """
    Returns full scientific governance metadata, performance metrics on the frozen test partition,
    feature importance, and the production promotion gate audit decision.
    """
    return dynamic_downscaling_service.get_diagnostic()


@router.post("/compare")
def compare_models(payload: DynamicDownscalingRequest) -> Dict[str, Any]:
    """
    Direct comparison between Certified Production Baseline (+0.7351°C) and Dynamic Model v2.
    """
    result = dynamic_downscaling_service.predict_residual(
        coarse_temp=payload.coarse_temperature_c,
        coarse_rh=payload.relative_humidity_pct,
        coarse_wspd=payload.wind_speed_mps,
        wind_direction_deg=payload.wind_direction_deg,
        precipitation_mm=payload.precipitation_mm,
        hour_of_day=payload.hour_of_day,
        day_of_year=payload.day_of_year,
        elevation_m=payload.elevation_m,
        coarse_elevation_m=payload.coarse_elevation_m,
        slope_deg=payload.slope_deg,
        aspect_deg=payload.aspect_deg,
        land_cover_code=payload.land_cover_code,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    baseline_offset = 0.7351
    coarse = payload.coarse_temperature_c
    baseline_temp = round(coarse + baseline_offset, 2)
    dynamic_temp = result["downscaled_temperature_c"]

    return {
        "coarse_input_temperature_c": round(coarse, 2),
        "production_baseline": {
            "model_type": "CERTIFIED_SCALAR_CALIBRATION",
            "status": "ACTIVE_PRODUCTION",
            "formula": "T_coarse + 0.7351°C",
            "correction_offset_c": baseline_offset,
            "downscaled_temperature_c": baseline_temp,
        },
        "research_candidate": {
            "model_type": "DYNAMIC_RESIDUAL_V2_XGBOOST",
            "status": "RESEARCH_ONLY",
            "decision": result.get("guardrail_status"),
            "dynamic_residual_c": result["final_residual_c"],
            "raw_residual_c": result["raw_model_residual_c"],
            "downscaled_temperature_c": dynamic_temp,
            "guardrail_status": result["guardrail_status"],
        },
        "divergence": {
            "temperature_diff_c": round(dynamic_temp - baseline_temp, 4),
            "residual_diff_c": round(result["final_residual_c"] - baseline_offset, 4),
            "significant_divergence": abs(dynamic_temp - baseline_temp) > 0.5,
        },
    }


@router.get("/national-validation")
def get_national_validation_summary() -> Dict[str, Any]:
    """
    Returns nationwide validation framework summary across 7 regions,
    17 WMO synoptic stations, holdout evaluations, elevation bands,
    and automated claim language.
    """
    from app.services.national_validation_service import national_validation_service
    return national_validation_service.get_validation_summary()


@router.get("/promotion-evaluation")
def get_dynamic_v2_promotion_evaluation() -> Dict[str, Any]:
    """
    Executes and returns the authoritative 8-gate scientific promotion evaluation
    of Dynamic Residual Model v2 against the certified +0.7351°C baseline.
    """
    from app.services.dynamic_v2_promotion_service import dynamic_v2_promotion_service
    return dynamic_v2_promotion_service.evaluate_promotion()
