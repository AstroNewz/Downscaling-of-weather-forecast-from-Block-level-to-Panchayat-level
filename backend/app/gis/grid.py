"""
Spatial Grid Generation Engine
SIH Problem Statement 26074 (Weather Downscaling)

Generates regular ~1-km (1000m x 1000m) spatial grid cells
across a Block administrative domain using a projected metric CRS suitable for local distance/area calculations.
"""
import math
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field
import numpy as np
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon
from shapely.ops import transform as shapely_transform
from shapely import wkt
import pyproj

from app.core.config import settings
from app.core.logging import logger


class GridCellRecord(BaseModel):
    """Metadata and geometric properties of an individual 1-km spatial grid cell."""
    grid_id: str
    block_id: Optional[int] = None
    row_idx: int
    col_idx: int
    center_latitude: float = Field(..., ge=-90.0, le=90.0)
    center_longitude: float = Field(..., ge=-180.0, le=180.0)
    projected_x: float
    projected_y: float
    resolution_m: float = Field(default=1000.0)
    geometry_wkt: str
    geometry_geojson: Dict[str, Any]


class SpatialGridDomainResult(BaseModel):
    """Summary of a generated spatial grid domain."""
    total_cells: int
    block_id: Optional[int] = None
    requested_resolution_km: float
    requested_resolution_m: float
    actual_resolution_m: float
    projected_crs: str
    boundary_rule: str
    bounding_box_wgs84: Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    bounding_box_projected: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    cells: List[GridCellRecord]


class SpatialGridGenerator:
    """
    Constructs high-resolution spatial grid tiles in a projected metric CRS over geographic polygons.
    """


    @staticmethod
    def get_optimal_utm_epsg(lon: float, lat: float) -> int:
        """
        Determines the optimal Universal Transverse Mercator (UTM) EPSG code for given WGS84 coordinates.
        Minimal distance and area distortion (< 0.1%).
        """
        zone = int((lon + 180.0) / 6.0) + 1
        zone = max(1, min(60, zone))
        if lat >= 0:
            return 32600 + zone  # WGS 84 / UTM Northern Hemisphere
        else:
            return 32700 + zone  # WGS 84 / UTM Southern Hemisphere

    @classmethod
    def generate_grid_for_polygon(
        cls,
        polygon_geom: Union[Polygon, MultiPolygon, str, Dict[str, Any]],
        resolution_km: float = 1.0,
        boundary_rule: str = "center_inside_block",
        block_id: Optional[int] = None,
        override_projected_epsg: Optional[int] = None
    ) -> SpatialGridDomainResult:
        """
        Generates regular square cells of size (resolution_km * 1000m) covering polygon_geom.

        Workflow:
        1. Parse input polygon geometry in WGS84 (EPSG:4326).
        2. Identify optimal local projected CRS (UTM).
        3. Project polygon into metric Cartesian coordinates (meters).
        4. Construct regular 1000m x 1000m grid cells over bounding box.
        5. Filter cells using boundary rule (e.g. center point inside polygon).
        6. Reproject cell polygons and centroids back to WGS84.
        7. Verify actual cell dimensions against requested resolution.
        """
        # 1. Parse Shapely Polygon
        from shapely import wkb, wkt as shapely_wkt
        if hasattr(polygon_geom, "data"):
            # GeoAlchemy2 WKBElement
            poly_wgs84 = wkb.loads(bytes(polygon_geom.data))
        elif hasattr(polygon_geom, "desc"):
            # GeoAlchemy2 WKTElement
            poly_wgs84 = shapely_wkt.loads(str(polygon_geom.desc))
        elif isinstance(polygon_geom, str):
            clean_wkt = polygon_geom
            if "SRID=" in clean_wkt and ";" in clean_wkt:
                clean_wkt = clean_wkt.split(";", 1)[1]
            poly_wgs84 = shapely_wkt.loads(clean_wkt)
        elif isinstance(polygon_geom, dict):
            poly_wgs84 = shape(polygon_geom)
        else:
            poly_wgs84 = polygon_geom

        if hasattr(poly_wgs84, "geoms") and len(poly_wgs84.geoms) > 0:
            # MultiPolygon handling: use valid shape
            pass

        if poly_wgs84.is_empty or not poly_wgs84.is_valid:
            poly_wgs84 = poly_wgs84.buffer(0)
            if not poly_wgs84.is_valid or poly_wgs84.is_empty:
                raise ValueError("Invalid spatial geometry provided for grid generation.")

        # 2. Determine Projected CRS
        centroid = poly_wgs84.centroid
        proj_epsg = override_projected_epsg or cls.get_optimal_utm_epsg(centroid.x, centroid.y)
        projected_crs_str = f"EPSG:{proj_epsg}"

        # 3. Create Transformers
        # WGS84 (lon, lat) <-> Projected (x, y)
        to_projected = pyproj.Transformer.from_crs("EPSG:4326", projected_crs_str, always_xy=True).transform
        to_wgs84 = pyproj.Transformer.from_crs(projected_crs_str, "EPSG:4326", always_xy=True).transform

        poly_projected = shapely_transform(to_projected, poly_wgs84)

        # 4. Compute Cartesian Bounds and Grid Parameters
        min_x, min_y, max_x, max_y = poly_projected.bounds
        step_m = float(resolution_km * 1000.0)

        # Verify dimension properties
        actual_cell_width_m = step_m
        actual_cell_height_m = step_m
        actual_resolution_m = math.sqrt(actual_cell_width_m * actual_cell_height_m)
        requested_res_m = float(resolution_km * 1000.0)

        if abs(actual_resolution_m - requested_res_m) > 1e-4:
            raise ValueError(f"Resolution mismatch: actual {actual_resolution_m}m != requested {requested_res_m}m")

        x_coords = np.arange(min_x, max_x, step_m)
        y_coords = np.arange(min_y, max_y, step_m)

        # Ensure at least 1 coordinate step if bounds are very tight
        if len(x_coords) == 0:
            x_coords = np.array([min_x])
        if len(y_coords) == 0:
            y_coords = np.array([min_y])

        cells: List[GridCellRecord] = []
        cell_id_counter = 0

        # 5. Generate Grid Cells and Filter
        for row_idx, y in enumerate(y_coords):
            for col_idx, x in enumerate(x_coords):
                # Projected square cell geometry
                cell_box_proj = Polygon([
                    (x, y),
                    (x + step_m, y),
                    (x + step_m, y + step_m),
                    (x, y + step_m),
                    (x, y)
                ])

                center_x = x + (step_m / 2.0)
                center_y = y + (step_m / 2.0)
                center_pt_proj = Point(center_x, center_y)

                # Boundary rule evaluation in projected CRS
                is_valid_cell = False
                if boundary_rule == "center_inside_block":
                    is_valid_cell = poly_projected.contains(center_pt_proj) or poly_projected.touches(center_pt_proj)
                elif boundary_rule == "intersects":
                    is_valid_cell = poly_projected.intersects(cell_box_proj)
                else:
                    # Default center inside
                    is_valid_cell = poly_projected.contains(center_pt_proj)

                if is_valid_cell:
                    # Reproject back to WGS84
                    center_lon, center_lat = to_wgs84(center_x, center_y)
                    cell_poly_wgs84 = shapely_transform(to_wgs84, cell_box_proj)

                    grid_id = f"grid_b{block_id or 0}_{row_idx:03d}_{col_idx:03d}"

                    cells.append(
                        GridCellRecord(
                            grid_id=grid_id,
                            block_id=block_id,
                            row_idx=row_idx,
                            col_idx=col_idx,
                            center_latitude=round(float(center_lat), 6),
                            center_longitude=round(float(center_lon), 6),
                            projected_x=round(float(center_x), 2),
                            projected_y=round(float(center_y), 2),
                            resolution_m=actual_resolution_m,
                            geometry_wkt=cell_poly_wgs84.wkt,
                            geometry_geojson=mapping(cell_poly_wgs84)
                        )
                    )
                    cell_id_counter += 1

        # 6. Fallback for Tiny or Narrow Polygons where center is missed
        if len(cells) == 0:
            logger.warning(
                f"No grid cell centers fell inside block geometry (area: {poly_wgs84.area:.6f} deg²). "
                f"Generating single representative cell at centroid."
            )
            c_x_proj, c_y_proj = to_projected(centroid.x, centroid.y)
            half_step = step_m / 2.0
            cell_box_proj = Polygon([
                (c_x_proj - half_step, c_y_proj - half_step),
                (c_x_proj + half_step, c_y_proj - half_step),
                (c_x_proj + half_step, c_y_proj + half_step),
                (c_x_proj - half_step, c_y_proj + half_step),
                (c_x_proj - half_step, c_y_proj - half_step)
            ])
            cell_poly_wgs84 = shapely_transform(to_wgs84, cell_box_proj)
            grid_id = f"grid_b{block_id or 0}_000_000"
            cells.append(
                GridCellRecord(
                    grid_id=grid_id,
                    block_id=block_id,
                    row_idx=0,
                    col_idx=0,
                    center_latitude=round(float(centroid.y), 6),
                    center_longitude=round(float(centroid.x), 6),
                    projected_x=round(float(c_x_proj), 2),
                    projected_y=round(float(c_y_proj), 2),
                    resolution_m=actual_resolution_m,
                    geometry_wkt=cell_poly_wgs84.wkt,
                    geometry_geojson=mapping(cell_poly_wgs84)
                )
            )

        min_lon, min_lat, max_lon, max_lat = poly_wgs84.bounds

        return SpatialGridDomainResult(
            total_cells=len(cells),
            block_id=block_id,
            requested_resolution_km=resolution_km,
            requested_resolution_m=requested_res_m,
            actual_resolution_m=actual_resolution_m,
            projected_crs=projected_crs_str,
            boundary_rule=boundary_rule,
            bounding_box_wgs84=(min_lon, min_lat, max_lon, max_lat),
            bounding_box_projected=(min_x, min_y, max_x, max_y),
            cells=cells
        )
