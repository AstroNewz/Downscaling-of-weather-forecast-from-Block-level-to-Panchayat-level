import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import register_exception_handlers
from app.api.router import api_router

# Tag metadata for OpenAPI / Swagger documentation
openapi_tags = [
    {
        "name": "System Health",
        "description": "Liveness and readiness probes for infrastructure monitoring.",
    },
    {
        "name": "Weather Ingestion & Downscaling",
        "description": "Ingestion of block-level NWP forecasts and execution of AI/ML downscaling to 1 km x 1 km high-resolution grids.",
    },
    {
        "name": "Panchayat GIS Intelligence",
        "description": "Panchayat administrative boundary mapping, spatial zonal statistics, and cropland/land-use masking.",
    },
    {
        "name": "Agricultural Context",
        "description": "Crop phenology stage calendars, soil characteristics, and localized agricultural vulnerability data.",
    },
    {
        "name": "Agro-Meteorological Advisory",
        "description": "Automated agricultural risk detection and tailored agro-meteorological advisory generation for farmers and agricultural officers.",
    },
    {
        "name": "ML Downscaling Engine",
        "description": "Management, inspection, and metrics for ML downscaling models (XGBoost, ConvLSTM, LightGBM).",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan events handler for application startup and shutdown.
    """
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    logger.info("Initializing Agro-Meteorological Intelligence backend subsystem...")
    # Startup actions: Database pools, spatial indices, model weights (Phase 2+)
    try:
        from app.gis.boundary_registry import boundary_registry
        loaded = boundary_registry.load_from_configured_source()
        if boundary_registry.count() == 0:
            try:
                from tests.fixtures.imaginary_panchayats_fixture import get_imaginary_panchayat_records
                boundary_registry.register_all(get_imaginary_panchayat_records())
                logger.info(f"Loaded {boundary_registry.count()} pilot/imaginary Panchayat boundaries.")
            except Exception as e:
                logger.warning(f"Could not load pilot boundaries: {e}")
    except Exception as exc:
        logger.warning(f"Could not load initial Panchayat boundaries: {exc}")
    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.APP_NAME}...")



app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="""
## Agro-Meteorological Weather Intelligence Platform
**SIH Problem Statement 26074**: *Downscaling of weather forecast from Block level to Panchayat level: Inferring high-resolution plots/data/information from low-resolution plot/data/information/variables for agro-meteorological advisory services.*

### Core Pipeline Architecture:
1. **Weather Ingestion**: Ingesting coarse block-level forecasts (NWP / IMD / NCMRWF).
2. **AI/ML Downscaling**: High-resolution spatial interpolation and machine learning downscaling.
3. **GIS & Land-Use Masking**: Panchayat polygon spatial joins with strict Cropland/Non-Cropland masks.
4. **Agro-Context Integration**: Crop phenology stage and soil context correlation.
5. **Agro-Advisory Generation**: Agronomic rule evaluation and risk mitigation guidance.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# Configure CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register Centralized Exception Handlers
register_exception_handlers(app)


# Request timing and diagnostic middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Seconds"] = f"{process_time:.4f}"
    return response


# Include central API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Dedicated /api/panchayats conceptual endpoint router
from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from app.gis.boundary_service import panchayat_boundary_service
from app.schemas.panchayat_boundary import BoundaryResolutionResponse, PanchayatBoundaryFeatureResponse

panchayats_compat_router = APIRouter(prefix="/api/panchayats", tags=["Panchayat Boundary Service"])


@panchayats_compat_router.get(
    "/resolve",
    response_model=BoundaryResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Exact Point-in-Polygon Panchayat Coordinate Resolution",
    description="Resolves latitude and longitude coordinates to an exact Gram Panchayat boundary using point-in-polygon logic.",
)
async def compat_resolve_panchayat_coordinate(
    lat: float = Query(..., description="Latitude in decimal degrees (WGS84)"),
    lon: float = Query(..., description="Longitude in decimal degrees (WGS84)"),
    tolerance: Optional[float] = Query(None, description="Boundary numerical tolerance in degrees (default 1e-5 ~ 1.1m)"),
    require_verified: bool = Query(False, description="Require verified boundary geometry"),
) -> BoundaryResolutionResponse:
    return panchayat_boundary_service.resolve_coordinates(
        lat=lat,
        lon=lon,
        tolerance_deg=tolerance,
        require_verified=require_verified,
    )


@panchayats_compat_router.get(
    "/{panchayat_id}/boundary",
    response_model=PanchayatBoundaryFeatureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Canonical Panchayat Boundary Polygon",
    description="Returns authoritative GeoJSON Feature containing the exact polygon boundary from the canonical registry.",
)
async def compat_get_panchayat_boundary(
    panchayat_id: str,
) -> PanchayatBoundaryFeatureResponse:
    feature = panchayat_boundary_service.get_panchayat_boundary(panchayat_id)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Boundary polygon not found in canonical registry for Panchayat ID '{panchayat_id}'.",
        )
    return feature


app.include_router(panchayats_compat_router)



@app.get("/", tags=["System Health"])
async def root():
    """Root endpoint providing service summary and link to interactive documentation."""
    return JSONResponse(
        content={
            "app_name": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
            "documentation_url": "/docs",
            "openapi_spec": "/openapi.json",
            "status": "online",
            "objective": "SIH 26074 - Panchayat-Level Agro-Meteorological Advisory Backend",
        }
    )
