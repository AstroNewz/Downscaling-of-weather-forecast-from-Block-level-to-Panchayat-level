"""
System Data-Source & Governance API Router
SIH Problem Statement 26074 (Weather Downscaling)

Exposes data-source mode configuration, live provider status, and freshness probes.
Crucially distinguishes API server connectivity from actual meteorological data availability.
"""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, status, HTTPException

from app.core.config import settings
from app.core.logging import logger
from app.schemas.common import APIResponse
from app.weather.schemas import DataStatusResponse, ProviderInfo, ProviderHealthResponse
from app.weather.providers.live_provider import (
    get_current_data_mode,
    set_runtime_data_mode,
    resolve_weather_data,
    LiveWeatherUnavailableError,
    get_registered_providers,
    check_provider_health,
)

router = APIRouter(prefix="/system", tags=["System Data-Source & Governance"])


class ModeSwitchRequest(BaseModel):
    mode: str = Field(..., description="Target data-source mode: DEMO, LIVE, or AUTO")


@router.get(
    "/data-status",
    response_model=APIResponse[DataStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="System Weather Data Source & Freshness Status",
    description="Inspects active data mode (DEMO/LIVE/AUTO), external provider availability, freshness age, and fallback status.",
)
async def get_data_source_status() -> APIResponse[DataStatusResponse]:
    current_mode = get_current_data_mode()
    now_utc = datetime.now(timezone.utc)

    # Resolve coarse sample for status inspection
    fallback_active = False
    fallback_reason = None
    effective_mode = current_mode
    provider_name = "CANONICAL_PILOT_FIXTURE"
    source_type = "PILOT_FIXTURE"
    source_ts = now_utc.isoformat()
    age_min = 0.0
    quality_status = "PASSED"
    freshness_status = "FRESH"

    try:
        sample_rec = resolve_weather_data(latitude=25.35, longitude=82.95, requested_mode=current_mode)
        effective_mode = sample_rec.effective_mode
        provider_name = sample_rec.source
        source_type = sample_rec.source_type
        source_ts = sample_rec.valid_time
        quality_status = sample_rec.quality_status
        fallback_active = sample_rec.fallback_active
        fallback_reason = sample_rec.fallback_reason

        raw_meta = sample_rec.raw_payload or {}
        age_min = raw_meta.get("age_minutes", 0.0)
        if age_min is not None and age_min > settings.WEATHER_STALE_AFTER_MINUTES:
            freshness_status = "STALE"

    except LiveWeatherUnavailableError as e:
        logger.warning(f"Data status inspection: Live provider unavailable: {e}")
        effective_mode = "LIVE"
        provider_name = "OPEN_METEO_OPERATIONAL_NWP"
        source_type = "FORECAST"
        quality_status = "INSUFFICIENT_DATA"
        freshness_status = "UNKNOWN"
        fallback_active = False
        fallback_reason = f"LIVE_PROVIDER_UNAVAILABLE: {str(e)}"
    except Exception as e:
        logger.error(f"Data status probe error: {e}")
        quality_status = "DEGRADED"

    msg = f"Data mode active: [{current_mode}] (Effective: [{effective_mode}])."
    if fallback_active:
        msg = f"AUTO Fallback active: Serving canonical demo data due to {fallback_reason}."
    elif effective_mode == "LIVE":
        msg = f"Genuine external live forecast feed active via {provider_name}."

    resp = DataStatusResponse(
        mode=current_mode,
        effective_mode=effective_mode,
        live_enabled=(current_mode in ("LIVE", "AUTO")),
        provider=provider_name,
        source_type=source_type,
        latest_source_timestamp=source_ts,
        retrieved_at=now_utc.isoformat(),
        age_minutes=age_min,
        freshness_status=freshness_status,
        quality_status=quality_status,
        fallback_active=fallback_active,
        fallback_reason=fallback_reason,
        calibrated_baseline=f"T_calibrated = T_coarse + {settings.CALIBRATION_OFFSET_C:.4f}°C",
        model_status="XGBoost: RESEARCH_ONLY",
        message=msg,
    )

    return APIResponse(
        success=True,
        message="System data source status retrieved.",
        data=resp,
    )


@router.get(
    "/mode",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get Active Data Source Mode",
    description="Returns active backend data source mode (DEMO, LIVE, or AUTO).",
)
async def get_data_source_mode() -> APIResponse[dict]:
    mode = get_current_data_mode()
    return APIResponse(
        success=True,
        message=f"Current weather data mode is [{mode}].",
        data={"mode": mode},
    )


@router.post(
    "/mode",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Switch Active Data Source Mode",
    description="Dynamically sets backend data source mode to DEMO, LIVE, or AUTO for SIH demonstrations.",
)
async def set_data_source_mode(payload: ModeSwitchRequest) -> APIResponse[dict]:
    try:
        new_mode = set_runtime_data_mode(payload.mode)
        return APIResponse(
            success=True,
            message=f"Weather data mode successfully set to [{new_mode}].",
            data={"mode": new_mode},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


class RolloutModeRequest(BaseModel):
    mode: str = Field(..., description="Target rollout mode: DYNAMIC_PRIMARY or BASELINE_PRIMARY")


@router.post(
    "/rollout-mode",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Set Controlled Production Rollout Mode",
    description="Switches operational primary path between DYNAMIC_PRIMARY and BASELINE_PRIMARY for instantaneous rollback.",
)
async def set_rollout_mode(payload: RolloutModeRequest) -> APIResponse[dict]:
    target = payload.mode.upper().strip()
    if target not in ("DYNAMIC_PRIMARY", "BASELINE_PRIMARY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid rollout mode. Must be 'DYNAMIC_PRIMARY' or 'BASELINE_PRIMARY'."
        )
    settings.ROLLOUT_MODE = target
    logger.info("Rollout mode changed by operator to: %s", target)
    return APIResponse(
        success=True,
        message=f"Controlled production rollout mode successfully set to [{target}].",
        data={
            "rollout_mode": target,
            "model_operational_status": getattr(settings, "MODEL_OPERATIONAL_STATUS", "CONTROLLED_PRODUCTION"),
            "active_model": "DYNAMIC_V2" if target == "DYNAMIC_PRIMARY" else "CERTIFIED_BASELINE_V1",
        },
    )


@router.get(
    "/telemetry",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get Controlled Production Telemetry Snapshot",
    description="Returns atomic counts for dynamic inferences, fallbacks, OOD detections, and safety violations.",
)
async def get_telemetry_snapshot() -> APIResponse[dict]:
    from app.services.operational_safeguards import runtime_telemetry
    return APIResponse(
        success=True,
        message="Operational telemetry retrieved.",
        data={
            "rollout_mode": getattr(settings, "ROLLOUT_MODE", "DYNAMIC_PRIMARY"),
            "model_operational_status": getattr(settings, "MODEL_OPERATIONAL_STATUS", "CONTROLLED_PRODUCTION"),
            "active_model": getattr(settings, "ACTIVE_OPERATIONAL_MODEL", "DYNAMIC_V2"),
            "fallback_model": getattr(settings, "FALLBACK_OPERATIONAL_MODEL", "CERTIFIED_BASELINE_V1"),
            "safety_bounds": [settings.DYNAMIC_RESIDUAL_SAFETY_MIN, settings.DYNAMIC_RESIDUAL_SAFETY_MAX],
            "counters": runtime_telemetry.get_snapshot(),
        },
    )


@router.get(
    "/providers",
    response_model=APIResponse[List[ProviderInfo]],
    status_code=status.HTTP_200_OK,
    summary="List Registered Weather Data Providers",
    description="Returns metadata catalog of all registered weather providers (Open-Meteo, IMD, Demo).",
)
async def list_weather_providers() -> APIResponse[List[ProviderInfo]]:
    providers = get_registered_providers()
    return APIResponse(
        success=True,
        message=f"Retrieved {len(providers)} registered weather data providers.",
        data=providers,
    )


@router.get(
    "/providers/{provider}/health",
    response_model=APIResponse[ProviderHealthResponse],
    status_code=status.HTTP_200_OK,
    summary="Check Specific Weather Provider Health",
    description="Executes a live health and freshness check on the specified provider (e.g. imd, open_meteo, demo).",
)
async def get_provider_health(provider: str) -> APIResponse[ProviderHealthResponse]:
    health = check_provider_health(provider)
    return APIResponse(
        success=True,
        message=f"Health check completed for provider [{provider}].",
        data=health,
    )
