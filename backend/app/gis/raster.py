import os
from typing import Optional, Tuple, List
import numpy as np
import rasterio
from rasterio.transform import rowcol
from pyproj import Transformer
from app.core.logging import logger


class RasterSampler:
    """
    Safely reads, reprojects, and samples raster pixel values (GeoTIFF) at arbitrary geographic coordinates.
    """

    @staticmethod
    def sample_point_and_window(
        raster_path: str,
        latitude: float,
        longitude: float,
        window_size: int = 3
    ) -> Tuple[Optional[float], Optional[np.ndarray], Optional[Tuple[float, float]]]:
        """
        Samples the center pixel value and local square neighborhood window from a GeoTIFF raster.

        Args:
            raster_path: Path to the GeoTIFF file.
            latitude: Geographic latitude in WGS84 (EPSG:4326).
            longitude: Geographic longitude in WGS84 (EPSG:4326).
            window_size: Odd integer neighborhood dimension (e.g. 3 for 3x3 grid).

        Returns:
            Tuple of:
            - center_value (Optional[float]): Value at coordinate, or None if out of bounds/missing.
            - window_array (Optional[np.ndarray]): 2D array of surrounding neighborhood, or None.
            - pixel_resolution (Optional[Tuple[float, float]]): (res_x, res_y) in projected meters.
        """
        if not os.path.exists(raster_path):
            return None, None, None

        try:
            with rasterio.open(raster_path) as src:
                raster_crs = src.crs
                # Reproject WGS84 (EPSG:4326) coordinate to raster CRS if necessary
                if raster_crs and raster_crs.to_epsg() != 4326:
                    transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
                    proj_x, proj_y = transformer.transform(longitude, latitude)
                else:
                    proj_x, proj_y = longitude, latitude

                # Check bounding box
                bounds = src.bounds
                if not (bounds.left <= proj_x <= bounds.right and bounds.bottom <= proj_y <= bounds.top):
                    return None, None, None

                # Convert projected coordinates to raster row, col
                r, c = rowcol(src.transform, proj_x, proj_y)

                if not (0 <= r < src.height and 0 <= c < src.width):
                    return None, None, None

                # Extract center pixel value
                center_val = float(src.read(1, window=((r, r + 1), (c, c + 1)))[0, 0])
                if src.nodata is not None and center_val == src.nodata:
                    return None, None, None

                # Extract local window
                half_w = window_size // 2
                r_start, r_end = max(0, r - half_w), min(src.height, r + half_w + 1)
                c_start, c_end = max(0, c - half_w), min(src.width, c + half_w + 1)

                window_data = src.read(1, window=((r_start, r_end), (c_start, c_end))).astype(np.float64)

                if src.nodata is not None:
                    window_data[window_data == src.nodata] = np.nan

                res_x, res_y = abs(src.transform.a), abs(src.transform.e)
                return center_val, window_data, (res_x, res_y)

        except Exception as exc:
            logger.warning(f"Error sampling raster '{raster_path}' at ({latitude}, {longitude}): {exc}")
            return None, None, None
