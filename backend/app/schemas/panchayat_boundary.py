"""
Panchayat Boundary Data Models & API Schemas
SIH Problem Statement 26074 (Panchayat Boundary Service)

Defines canonical Pydantic representations for authoritative Panchayat
polygons, point-in-polygon resolution requests, and boundary audit metadata.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundaryResolutionStatus(str, Enum):
    """Overall status of the coordinate-to-Panchayat resolution query."""
    RESOLVED = "RESOLVED"
    ON_BOUNDARY = "ON_BOUNDARY"
    OUTSIDE_REGISTERED_PANCHAYATS = "OUTSIDE_REGISTERED_PANCHAYATS"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    OVERLAPPING_POLYGONS = "OVERLAPPING_POLYGONS"
    UNVERIFIED_GEOMETRY = "UNVERIFIED_GEOMETRY"


class PointLocationStatus(str, Enum):
    """Topological relationship between query point and polygon boundary."""
    INSIDE_POLYGON = "INSIDE_POLYGON"
    ON_BOUNDARY = "ON_BOUNDARY"
    OUTSIDE_POLYGON = "OUTSIDE_POLYGON"
    AMBIGUOUS_OVERLAP = "AMBIGUOUS_OVERLAP"
    INVALID = "INVALID"


class PanchayatBoundaryRecord(BaseModel):
    """
    Canonical backend representation of an administrative Panchayat polygon.
    All geometries MUST be in WGS84 (EPSG:4326).
    """
    panchayat_id: str = Field(..., description="Unique canonical Panchayat identifier (e.g. LGD or designated code)")
    lgd_code: Optional[str] = Field(None, description="Local Government Directory (LGD) code, when available from GoI")
    panchayat_name: str = Field(..., description="Official name of the Gram Panchayat")
    state: str = Field(..., description="State name (e.g. Uttar Pradesh)")
    district: str = Field(..., description="District name (e.g. Varanasi)")
    block: str = Field(..., description="Parent administrative Block/Tehsil name")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry object (Polygon or MultiPolygon in EPSG:4326)")
    centroid_lat: float = Field(..., ge=-90.0, le=90.0, description="Polygon centroid latitude (EPSG:4326)")
    centroid_lon: float = Field(..., ge=-180.0, le=180.0, description="Polygon centroid longitude (EPSG:4326)")
    area_sq_km: float = Field(..., ge=0.0, description="Geodesic surface area in square kilometers")
    geometry_source: str = Field(..., description="Data provenance source (e.g. 'LGD', 'BHUVAN_NRSC', 'AUTHORIZED_SURVEY')")
    geometry_version: str = Field(default="1.0", description="Version or release tag of the boundary geometry")
    geometry_status: str = Field(default="UNVERIFIED", description="Verification classification (e.g. 'VERIFIED', 'UNVERIFIED', 'AUDITED')")
    is_verified: bool = Field(default=False, description="True only if official source metadata confirms authoritative status")
    ingestion_timestamp: str = Field(..., description="ISO 8601 UTC timestamp when geometry was ingested into registry")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Auxiliary source attributes preserved from raw file")

    model_config = ConfigDict(extra="ignore")


class BoundaryResolutionResponse(BaseModel):
    """Response payload for coordinate point-in-polygon resolution."""
    status: BoundaryResolutionStatus = Field(..., description="High-level resolution outcome")
    boundary_status: PointLocationStatus = Field(..., description="Topological relationship to polygon boundary")
    panchayat_id: Optional[str] = Field(None, description="Matched Panchayat ID when RESOLVED")
    lgd_code: Optional[str] = Field(None, description="Matched LGD code when available")
    panchayat_name: Optional[str] = Field(None, description="Matched Gram Panchayat name")
    block: Optional[str] = Field(None, description="Parent administrative block name")
    district: Optional[str] = Field(None, description="District name")
    state: Optional[str] = Field(None, description="State name")
    centroid_lat: Optional[float] = Field(None, description="Matched Panchayat centroid latitude")
    centroid_lon: Optional[float] = Field(None, description="Matched Panchayat centroid longitude")
    area_sq_km: Optional[float] = Field(None, description="Matched Panchayat area in sq km")
    matched_geometry_version: Optional[str] = Field(None, description="Geometry version used for resolution")
    source: Optional[str] = Field(None, description="Authoritative source of the matched geometry")
    is_verified: Optional[bool] = Field(None, description="Verification status of the matched boundary")
    candidate_panchayat_ids: Optional[List[str]] = Field(None, description="Candidate Panchayat IDs when ON_BOUNDARY or OVERLAPPING")
    distance_to_boundary_m: Optional[float] = Field(None, description="Approximate distance to boundary in meters")
    message: Optional[str] = Field(None, description="Diagnostic or explanatory message")
    success: bool = Field(default=True, description="API success indicator")

    model_config = ConfigDict(extra="ignore")


class PanchayatBoundaryFeatureResponse(BaseModel):
    """GeoJSON Feature representation of a Panchayat boundary."""
    type: str = Field(default="Feature")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Polygon/MultiPolygon geometry")
    properties: Dict[str, Any] = Field(..., description="Panchayat attributes and boundary provenance")

    model_config = ConfigDict(extra="ignore")
