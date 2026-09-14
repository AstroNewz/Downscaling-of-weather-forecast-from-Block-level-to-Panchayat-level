from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Health status of an individual system component (PostgreSQL, PostGIS, ML Model, etc.)."""
    status: str = Field(..., description="Operational status: healthy, degraded, or unhealthy")
    details: Optional[str] = Field(default=None, description="Optional diagnostic or connection information")


class HealthCheckResponse(BaseModel):
    """Health check and system status response schema."""
    status: str = Field(default="healthy", description="Overall system health status")
    app_name: str = Field(..., description="Name of the backend service")
    app_env: str = Field(..., description="Current environment (development, staging, production)")
    version: str = Field(default="1.0.0", description="Application semantic version")
    api_version: str = Field(default="v1", description="Active API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current UTC timestamp")
    components: Dict[str, ComponentStatus] = Field(
        default_factory=dict,
        description="Health status of external dependencies and subsystem pipelines"
    )
