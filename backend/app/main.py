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
