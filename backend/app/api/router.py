from fastapi import APIRouter
from app.api.v1 import health, weather, panchayat, agriculture, advisory, ml

api_router = APIRouter()

# Include versioned sub-routers
api_router.include_router(health.router)
api_router.include_router(weather.router)
api_router.include_router(panchayat.router)
api_router.include_router(agriculture.router)
api_router.include_router(advisory.router)
api_router.include_router(ml.router)
