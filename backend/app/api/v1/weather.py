from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.weather import (
    WeatherIngestionRequest,
    BlockWeatherForecastResponse,
    WeatherObservationResponse,
    WeatherStatsResponse,
)
from app.weather.schemas import IngestionSummary
from app.weather.ingestion import WeatherIngestionService
from app.repositories.weather_repository import WeatherRepository
from app.core.logging import logger

router = APIRouter(prefix="/weather", tags=["Weather Ingestion & Downscaling"])


@router.get(
    "/status",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Weather Subsystem & Ingestion Status",
    description="Returns current status, active providers, and ingestion statistics for meteorological data."
)
async def get_weather_service_status(db: Session = Depends(get_db)) -> APIResponse[dict]:
    repo = WeatherRepository(db)
    stats = repo.get_stats()

    return APIResponse(
        success=True,
        message="Weather ingestion subsystem operational.",
        data={
            "module": "Weather Ingestion Service",
            "phase": "Phase 3 Ingestion & Validation Active",
            "active_providers": ["CSVWeatherProvider", "Future_IMD_NWP_Provider"],
            "supported_formats": [".csv", ".tsv"],
            "normalization_standards": {
                "temperature": "Degrees Celsius (°C)",
                "precipitation": "Millimeters (mm)",
                "wind_speed": "Meters per second (m/s) and km/h",
                "timestamps": "UTC ISO-8601 (Timezone-Aware)"
            },
            "database_stats": stats,
            "downscaling_status": "Awaiting ML Pipeline (Phase 4+)"
        }
    )


@router.post(
    "/ingest",
    response_model=APIResponse[IngestionSummary],
    status_code=status.HTTP_200_OK,
    summary="Ingest Weather Forecast / Observation Feed",
    description="Ingests, validates, normalizes, quality-checks, and persists weather data from CSV content or server file."
)
async def ingest_weather_data(
    payload: WeatherIngestionRequest,
    db: Session = Depends(get_db)
) -> APIResponse[IngestionSummary]:
    service = WeatherIngestionService(db)

    source_content = payload.raw_csv_content or payload.file_path
    if not source_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'file_path' or 'raw_csv_content' for weather ingestion."
        )

    options = {
        "source": payload.source_label,
        "model_name": payload.model_name,
    }

    summary = service.ingest(
        source_data=source_content,
        source_file_name=payload.file_path,
        options=options,
        dry_run=payload.dry_run
    )

    if summary.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weather ingestion failed: {summary.details}"
        )

    return APIResponse(
        success=True,
        message=f"Weather ingestion completed: {summary.records_inserted} records inserted.",
        data=summary
    )


@router.get(
    "/forecast",
    response_model=APIResponse[PaginatedResponse[BlockWeatherForecastResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query Block-Level Weather Forecasts",
    description="Retrieves paginated, filtered coarse NWP block forecasts stored in PostgreSQL."
)
async def query_forecasts(
    block_id: Optional[int] = Query(None, description="Filter by integer Block ID"),
    block_name: Optional[str] = Query(None, description="Filter by Block name keyword"),
    start_time: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    source_model: Optional[str] = Query(None, description="Filter by NWP model name (e.g., IMD-GFS, NCUM)"),
    quality_flag: Optional[str] = Query(None, description="Filter by quality flag: VALID, SUSPICIOUS, INVALID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> APIResponse[PaginatedResponse[BlockWeatherForecastResponse]]:
    repo = WeatherRepository(db)
    items, total = repo.get_forecasts(
        block_id=block_id,
        block_name=block_name,
        start_time=start_time,
        end_time=end_time,
        source_model=source_model,
        quality_flag=quality_flag,
        page=page,
        page_size=page_size
    )

    response_items = []
    for item in items:
        resp_item = BlockWeatherForecastResponse.model_validate(item)
        if item.block:
            resp_item.block_name = item.block.name
        response_items.append(resp_item)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    paginated = PaginatedResponse[BlockWeatherForecastResponse](
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(response_items)} forecast records.",
        data=paginated
    )


@router.get(
    "/observations",
    response_model=APIResponse[PaginatedResponse[WeatherObservationResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query Weather Station Observations",
    description="Retrieves paginated, filtered ground-truth AWS station observations."
)
async def query_observations(
    station_id: Optional[str] = Query(None, description="Filter by AWS Station ID"),
    block_id: Optional[int] = Query(None, description="Filter by Block ID"),
    start_time: Optional[datetime] = Query(None, description="Start date/time (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End date/time (UTC)"),
    source: Optional[str] = Query(None, description="Filter by data source (e.g. AWS)"),
    quality_flag: Optional[str] = Query(None, description="Filter by quality flag"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> APIResponse[PaginatedResponse[WeatherObservationResponse]]:
    repo = WeatherRepository(db)
    items, total = repo.get_observations(
        station_id=station_id,
        block_id=block_id,
        start_time=start_time,
        end_time=end_time,
        source=source,
        quality_flag=quality_flag,
        page=page,
        page_size=page_size
    )

    response_items = [WeatherObservationResponse.model_validate(item) for item in items]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    paginated = PaginatedResponse[WeatherObservationResponse](
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return APIResponse(
        success=True,
        message=f"Retrieved {len(response_items)} observation records.",
        data=paginated
    )
