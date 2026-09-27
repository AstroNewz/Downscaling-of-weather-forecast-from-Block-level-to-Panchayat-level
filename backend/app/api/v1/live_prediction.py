"""
Authoritative Live Weather Prediction API Router
SIH Problem Statement 26074 (Weather Downscaling)

Exposes GET and POST /api/v1/prediction/live endpoints for genuine live
or deterministic canonical demo inference with certified scientific safeguards.
"""
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, status, HTTPException, Query, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import APIResponse
from app.services.live_prediction_service import LivePredictionService
from app.weather.providers.live_provider import LiveWeatherUnavailableError

router = APIRouter(prefix="/prediction", tags=["Live Weather Downscaling Prediction"])


class LivePredictionRequest(BaseModel):
    panchayat_id: Optional[int] = Field(1, description="Gram Panchayat database ID or identifier")
    latitude: Optional[float] = Field(25.3500, description="Latitude in decimal degrees (WGS84)")
    longitude: Optional[float] = Field(82.9500, description="Longitude in decimal degrees (WGS84)")
    target_date: Optional[str] = Field(None, description="Forecast target date (YYYY-MM-DD)")
    mode: Optional[str] = Field(None, description="Optional override: DEMO, LIVE, or AUTO")


@router.get(
    "/live",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Execute Downscaled Weather Prediction",
    description="Runs certified spatial calibration and agronomic advisory pipeline using active data mode (DEMO/LIVE/AUTO).",
)
async def get_live_prediction(
    response: Response,
    panchayat_id: Optional[int] = Query(1, description="Gram Panchayat database ID"),
    latitude: Optional[float] = Query(None, description="Latitude (WGS84)"),
    longitude: Optional[float] = Query(None, description="Longitude (WGS84)"),
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    mode: Optional[str] = Query(None, description="Data mode override: DEMO, LIVE, or AUTO"),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    service = LivePredictionService(db=db)
    try:
        prediction_result = service.predict_panchayat_weather(
            panchayat_id=panchayat_id,
            latitude=latitude,
            longitude=longitude,
            target_date=target_date,
            requested_mode=mode,
        )
        return APIResponse(
            success=True,
            message="Downscaled prediction generated successfully.",
            data=prediction_result,
        )
    except LiveWeatherUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "INSUFFICIENT_DATA",
                "error": "Live external weather data is currently unavailable.",
                "reason": str(e),
                "mode": "LIVE",
                "safeguard": "Scientific policy prohibits silent synthetic substitution in LIVE mode.",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Downscaled prediction pipeline execution failed: {e}",
        )


@router.post(
    "/live",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Execute Downscaled Weather Prediction (POST)",
    description="Runs certified spatial calibration and agronomic advisory pipeline from structured request body.",
)
async def post_live_prediction(
    payload: LivePredictionRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    service = LivePredictionService(db=db)
    try:
        prediction_result = service.predict_panchayat_weather(
            panchayat_id=payload.panchayat_id,
            latitude=payload.latitude or 25.3500,
            longitude=payload.longitude or 82.9500,
            target_date=payload.target_date,
            requested_mode=payload.mode,
        )
        return APIResponse(
            success=True,
            message="Downscaled prediction generated successfully.",
            data=prediction_result,
        )
    except LiveWeatherUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "INSUFFICIENT_DATA",
                "error": "Live external weather data is currently unavailable.",
                "reason": str(e),
                "mode": "LIVE",
                "safeguard": "Scientific policy prohibits silent synthetic substitution in LIVE mode.",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Downscaled prediction pipeline execution failed: {e}",
        )
