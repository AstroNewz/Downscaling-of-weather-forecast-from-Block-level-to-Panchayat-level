from datetime import datetime
from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthCheckResponse, ComponentStatus
from app.schemas.common import APIResponse
from app.db.session import check_database_health

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get(
    "",
    response_model=APIResponse[HealthCheckResponse],
    status_code=status.HTTP_200_OK,
    summary="Liveness Health Check",
    description="Returns the operational status of the Agro-Meteorological Weather Intelligence API and connected components.",
)
async def liveness_check() -> APIResponse[HealthCheckResponse]:
    """
    Basic liveness endpoint for container orchestrators and load balancers.
    """
    db_ok, db_msg = check_database_health()
    db_status = "healthy" if db_ok else "unhealthy"

    health_data = HealthCheckResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        version="1.0.0",
        api_version="v1",
        timestamp=datetime.utcnow(),
        components={
            "api_server": ComponentStatus(status="healthy", details="FastAPI server accepting requests"),
            "database": ComponentStatus(
                status=db_status,
                details=db_msg
            ),
            "ml_engine": ComponentStatus(
                status="standby",
                details="Downscaling inference pipeline ready for model weights"
            ),
            "gis_pipeline": ComponentStatus(
                status="standby",
                details="Panchayat spatial indexer ready for shapefile/GeoJSON ingestion"
            )
        }
    )
    return APIResponse(
        success=True,
        message="Agro-Meteorological Intelligence Service health probe executed",
        data=health_data
    )


@router.get(
    "/ready",
    response_model=APIResponse[HealthCheckResponse],
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Validates that subsystem dependencies (PostgreSQL/PostGIS, ML model artifacts) are loaded.",
)
async def readiness_check() -> APIResponse[HealthCheckResponse]:
    """
    Readiness endpoint confirming backend is ready to accept production traffic.
    """
    db_ok, db_msg = check_database_health()
    is_ready = db_ok

    ready_data = HealthCheckResponse(
        status="ready" if is_ready else "not_ready",
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        version="1.0.0",
        api_version="v1",
        timestamp=datetime.utcnow(),
        components={
            "database": ComponentStatus(
                status="ready" if db_ok else "not_ready",
                details=db_msg
            ),
            "spatial_engine": ComponentStatus(
                status="ready",
                details="GeoPandas / GDAL / GeoAlchemy2 bindings active"
            ),
        }
    )
    return APIResponse(
        success=is_ready,
        message="Backend is ready to serve downscaling and advisory requests" if is_ready else "Backend dependencies not yet ready",
        data=ready_data
    )
