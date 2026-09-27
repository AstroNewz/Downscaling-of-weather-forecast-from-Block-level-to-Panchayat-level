"""
Panchayat Boundary Point-in-Polygon Resolution Service
SIH Problem Statement 26074 (Panchayat Boundary Service)

Implements exact topological Point-in-Polygon (PIP) coordinate resolution,
R-tree spatial indexing, deterministic shared-boundary edge handling,
and fail-closed ambiguity safety.
"""
from __future__ import annotations

import math
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from app.core.config import settings
from app.core.logging import logger
from app.gis.boundary_registry import PanchayatBoundaryRegistry, boundary_registry
from app.schemas.panchayat_boundary import (
    BoundaryResolutionResponse,
    BoundaryResolutionStatus,
    PanchayatBoundaryFeatureResponse,
    PanchayatBoundaryRecord,
    PointLocationStatus,
)


class PanchayatBoundaryService:
    """
    Authoritative service resolving user GPS coordinates to exact Gram Panchayat boundaries.

    Scientific Principles:
    1. Exact Point-in-Polygon: Administrative assignment is based strictly on polygon
       containment, NEVER centroid proximity or nearest-forecast-point heuristics.
    2. Explicit Boundary Edge Ambiguity: Points lying within numerical tolerance of a shared
       boundary return ON_BOUNDARY with deterministic candidate IDs, never a random choice.
    3. Spatial Index Acceleration: Uses STRtree (2D R-Tree) for O(log N) lookup scalability.
    4. Fail-Closed Governance: Missing data, invalid coordinates, or overlapping polygons
       fail safely into explicit error states.
    """

    # Default boundary tolerance: 1e-5 degrees ≈ 1.11 meters at the equator
    DEFAULT_BOUNDARY_TOLERANCE_DEG: float = 1e-5

    def __init__(self, registry: Optional[PanchayatBoundaryRegistry] = None):
        self.registry = registry or boundary_registry
        self._lock = threading.RLock()
        self._strtree: Optional[STRtree] = None
        self._tree_panchayat_ids: List[str] = []
        self._tree_version: int = 0
        self._last_registry_count: int = -1

    def _sync_spatial_index(self) -> None:
        """Reconstructs the STRtree spatial index if registry contents changed."""
        with self._lock:
            current_count = self.registry.count()
            if self._strtree is not None and current_count == self._last_registry_count:
                return

            geom_map = self.registry.get_all_geometries()
            if not geom_map:
                self._strtree = None
                self._tree_panchayat_ids = []
                self._last_registry_count = 0
                return

            self._tree_panchayat_ids = list(geom_map.keys())
            geometries = [geom_map[pid] for pid in self._tree_panchayat_ids]
            self._strtree = STRtree(geometries)
            self._last_registry_count = len(geometries)
            self._tree_version += 1
            logger.debug(f"PanchayatBoundaryService STRtree indexed with {len(geometries)} geometries.")

    @classmethod
    def validate_coordinates(cls, lat: Any, lon: Any) -> Tuple[bool, Optional[float], Optional[float], str]:
        """
        Validates that latitude and longitude are valid numeric floats within WGS84 bounds.
        Returns: (is_valid, float_lat, float_lon, error_message)
        """
        if lat is None or lon is None:
            return False, None, None, "Latitude and longitude query parameters are required."

        try:
            f_lat = float(lat)
            f_lon = float(lon)
        except (ValueError, TypeError):
            return False, None, None, f"Coordinates must be numeric. Received lat={lat}, lon={lon}."

        if not (math.isfinite(f_lat) and math.isfinite(f_lon)):
            return False, None, None, f"Coordinates must be finite numbers. Received lat={f_lat}, lon={f_lon}."

        if not (-90.0 <= f_lat <= 90.0):
            return False, None, None, f"Latitude {f_lat} out of range [-90.0, +90.0]."

        if not (-180.0 <= f_lon <= 180.0):
            return False, None, None, f"Longitude {f_lon} out of range [-180.0, +180.0]."

        return True, f_lat, f_lon, ""

    def resolve_coordinates(
        self,
        lat: float,
        lon: float,
        tolerance_deg: Optional[float] = None,
        require_verified: bool = False,
    ) -> BoundaryResolutionResponse:
        """
        Resolves (lat, lon) coordinates to an exact Gram Panchayat polygon.

        Parameters:
            lat: Latitude in decimal degrees (EPSG:4326)
            lon: Longitude in decimal degrees (EPSG:4326)
            tolerance_deg: Numerical boundary ambiguity tolerance in degrees (default 1e-5 ~ 1.1m)
            require_verified: If True, fails closed if the matched polygon is unverified
        """
        # 1. Coordinate Validation
        is_valid, f_lat, f_lon, err_msg = self.validate_coordinates(lat, lon)
        if not is_valid:
            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.INVALID_COORDINATES,
                boundary_status=PointLocationStatus.INVALID,
                message=err_msg,
                success=False,
            )

        eff_tolerance = (
            tolerance_deg
            if tolerance_deg is not None
            else getattr(settings, "PANCHAYAT_BOUNDARY_TOLERANCE_DEG", self.DEFAULT_BOUNDARY_TOLERANCE_DEG)
        )
        if eff_tolerance < 0:
            eff_tolerance = self.DEFAULT_BOUNDARY_TOLERANCE_DEG

        # 2. Check Registry Population
        self._sync_spatial_index()
        if self._strtree is None or not self._tree_panchayat_ids:
            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS,
                boundary_status=PointLocationStatus.OUTSIDE_POLYGON,
                message="No Panchayat boundaries registered in service. Ingestion required.",
                success=True,
            )

        # 3. Spatial Index Bounding-Box Filtering (O(log N))
        pt = Point(f_lon, f_lat)
        # Query STRtree with buffered point to capture boundary proximity
        search_geom = pt.buffer(eff_tolerance) if eff_tolerance > 0 else pt
        candidate_indices = self._strtree.query(search_geom)

        if len(candidate_indices) == 0:
            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS,
                boundary_status=PointLocationStatus.OUTSIDE_POLYGON,
                message="Coordinates fall outside all registered Panchayat polygons.",
                success=True,
            )

        # 4. Exact Geometric Evaluation
        boundary_candidates: List[Tuple[str, float]] = []  # (panchayat_id, distance_to_boundary_deg)
        interior_candidates: List[str] = []

        for idx in candidate_indices:
            pid = self._tree_panchayat_ids[idx]
            poly = self.registry.get_shapely_geometry(pid)
            if poly is None:
                continue

            dist_to_boundary_deg = float(poly.boundary.distance(pt))
            is_inside = bool(poly.contains(pt))
            is_covered = bool(poly.covers(pt))

            # Proximity to polygon perimeter within tolerance
            if dist_to_boundary_deg <= eff_tolerance:
                boundary_candidates.append((pid, dist_to_boundary_deg))
            elif is_inside and dist_to_boundary_deg > eff_tolerance:
                interior_candidates.append(pid)

        # 5. Boundary Ambiguity Evaluation (Deterministic Edge Handling)
        if boundary_candidates:
            # Deterministic sorted order of candidate IDs
            sorted_candidates = sorted(list({c[0] for c in boundary_candidates}))
            min_dist_deg = min(c[1] for c in boundary_candidates)
            min_dist_m = round(min_dist_deg * 111320.0, 3)

            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.ON_BOUNDARY,
                boundary_status=PointLocationStatus.ON_BOUNDARY,
                candidate_panchayat_ids=sorted_candidates,
                distance_to_boundary_m=min_dist_m,
                message=(
                    f"Coordinate lies within {min_dist_m}m of the boundary for "
                    f"Panchayat(s): {', '.join(sorted_candidates)}. Cannot assign single Panchayat."
                ),
                success=True,
            )

        # 6. Overlapping Polygons Handling (Fail-Closed Safety)
        if len(interior_candidates) > 1:
            sorted_overlap = sorted(interior_candidates)
            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.OVERLAPPING_POLYGONS,
                boundary_status=PointLocationStatus.AMBIGUOUS_OVERLAP,
                candidate_panchayat_ids=sorted_overlap,
                message=f"Ambiguity detected: coordinate falls strictly inside multiple overlapping polygons ({sorted_overlap}).",
                success=False,
            )

        # 7. Unambiguous Resolution (Single Polygon Interior)
        if len(interior_candidates) == 1:
            matched_id = interior_candidates[0]
            record = self.registry.get_by_id(matched_id)
            if not record:
                return BoundaryResolutionResponse(
                    status=BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS,
                    boundary_status=PointLocationStatus.OUTSIDE_POLYGON,
                    message="Matched Panchayat metadata record missing from registry.",
                    success=False,
                )

            # Verification enforcement policy
            if require_verified and not record.is_verified:
                return BoundaryResolutionResponse(
                    status=BoundaryResolutionStatus.UNVERIFIED_GEOMETRY,
                    boundary_status=PointLocationStatus.OUTSIDE_POLYGON,
                    panchayat_id=record.panchayat_id,
                    lgd_code=record.lgd_code,
                    panchayat_name=record.panchayat_name,
                    block=record.block,
                    district=record.district,
                    state=record.state,
                    matched_geometry_version=record.geometry_version,
                    source=record.geometry_source,
                    is_verified=record.is_verified,
                    message="Matched boundary geometry is unverified; fail-closed policy rejected assignment.",
                    success=False,
                )

            return BoundaryResolutionResponse(
                status=BoundaryResolutionStatus.RESOLVED,
                boundary_status=PointLocationStatus.INSIDE_POLYGON,
                panchayat_id=record.panchayat_id,
                lgd_code=record.lgd_code,
                panchayat_name=record.panchayat_name,
                block=record.block,
                district=record.district,
                state=record.state,
                centroid_lat=record.centroid_lat,
                centroid_lon=record.centroid_lon,
                area_sq_km=record.area_sq_km,
                matched_geometry_version=record.geometry_version,
                source=record.geometry_source,
                is_verified=record.is_verified,
                message=f"Unambiguously resolved to Panchayat '{record.panchayat_name}'.",
                success=True,
            )

        # 8. Outside all polygons
        return BoundaryResolutionResponse(
            status=BoundaryResolutionStatus.OUTSIDE_REGISTERED_PANCHAYATS,
            boundary_status=PointLocationStatus.OUTSIDE_POLYGON,
            message="Coordinates fall outside all registered Panchayat polygons.",
            success=True,
        )

    def get_panchayat_boundary(self, panchayat_id: Union[str, int]) -> Optional[PanchayatBoundaryFeatureResponse]:
        """
        Retrieves the canonical GeoJSON Feature for a Panchayat boundary.
        Directly backed by the canonical registry.
        """
        record = self.registry.get_by_id(panchayat_id)
        if not record:
            # Try LGD code
            record = self.registry.get_by_lgd_code(panchayat_id)

        if not record:
            return None

        props = {
            "panchayat_id": record.panchayat_id,
            "lgd_code": record.lgd_code,
            "panchayat_name": record.panchayat_name,
            "block": record.block,
            "district": record.district,
            "state": record.state,
            "centroid_lat": record.centroid_lat,
            "centroid_lon": record.centroid_lon,
            "area_sq_km": record.area_sq_km,
            "geometry_source": record.geometry_source,
            "geometry_version": record.geometry_version,
            "geometry_status": record.geometry_status,
            "is_verified": record.is_verified,
            "ingestion_timestamp": record.ingestion_timestamp,
        }
        if record.properties:
            props["auxiliary"] = {k: v for k, v in record.properties.items() if not k.startswith("_")}

        return PanchayatBoundaryFeatureResponse(
            type="Feature",
            geometry=record.geometry,
            properties=props,
        )

    def resolve_panchayat_id(self, lat: float, lon: float) -> Optional[str]:
        """
        Lightweight convenience primitive for downstream forecast/weather services.
        Returns the resolved panchayat_id string if cleanly RESOLVED, otherwise None.
        """
        res = self.resolve_coordinates(lat=lat, lon=lon)
        if res.status == BoundaryResolutionStatus.RESOLVED:
            return res.panchayat_id
        return None


# Global singleton service instance
panchayat_boundary_service = PanchayatBoundaryService()


def resolve_panchayat_from_coordinates(
    lat: float,
    lon: float,
    tolerance_deg: Optional[float] = None,
    require_verified: bool = False,
) -> Optional[PanchayatBoundaryRecord]:
    """
    Downstream Geographic Primitive:
    Resolves GPS coordinates to an exact authoritative PanchayatBoundaryRecord.
    If coordinates fall on boundary, outside, or in an overlapping region, returns None
    (failing closed so downstream services can handle ambiguity explicitly).
    """
    res = panchayat_boundary_service.resolve_coordinates(
        lat=lat,
        lon=lon,
        tolerance_deg=tolerance_deg,
        require_verified=require_verified,
    )
    if res.status == BoundaryResolutionStatus.RESOLVED and res.panchayat_id:
        return panchayat_boundary_service.registry.get_by_id(res.panchayat_id)
    return None

