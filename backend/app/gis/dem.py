import math
from typing import Optional, Tuple
import numpy as np
from app.gis.schemas import TerrainFeatures
from app.gis.raster import RasterSampler
from app.core.logging import logger


class DEMTopographicEngine:
    """
    Computes topographic derivatives (slope, aspect, TRI, lapse rate) from Digital Elevation Models.
    """

    # Standard environmental temperature lapse rate in °C per meter
    # -6.5°C per 1,000 meters = -0.0065 °C / m
    STANDARD_LAPSE_RATE_C_PER_M = -0.0065

    @classmethod
    def compute_slope_and_aspect(
        cls,
        window_3x3: np.ndarray,
        res_x: float = 30.0,
        res_y: float = 30.0
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        Computes slope (deg), aspect (deg), sin(aspect), and cos(aspect) using the standard Horn algorithm.

        Args:
            window_3x3: 3x3 2D array of elevation values.
            res_x: Spatial cell resolution in x direction (meters).
            res_y: Spatial cell resolution in y direction (meters).

        Returns:
            Tuple of (slope_deg, aspect_deg, sin_aspect, cos_aspect)
        """
        if window_3x3 is None or window_3x3.shape != (3, 3) or np.isnan(window_3x3).any():
            return None, None, None, None

        # Pixel indices:
        # [0,0] [0,1] [0,2]
        # [1,0] [1,1] [1,2]
        # [2,0] [2,1] [2,2]
        dz_dx = ((window_3x3[0, 2] + 2.0 * window_3x3[1, 2] + window_3x3[2, 2]) -
                 (window_3x3[0, 0] + 2.0 * window_3x3[1, 0] + window_3x3[2, 0])) / (8.0 * res_x)

        dz_dy = ((window_3x3[2, 0] + 2.0 * window_3x3[2, 1] + window_3x3[2, 2]) -
                 (window_3x3[0, 0] + 2.0 * window_3x3[0, 1] + window_3x3[0, 2])) / (8.0 * res_y)

        # Slope in degrees: arctan(hypot(dz_dx, dz_dy))
        slope_rad = math.atan(math.hypot(dz_dx, dz_dy))
        slope_deg = round(math.degrees(slope_rad), 2)

        # Flat terrain aspect handling
        if abs(dz_dx) < 1e-7 and abs(dz_dy) < 1e-7:
            return slope_deg, 0.0, 0.0, 1.0

        # Aspect in degrees: compass direction of steepest slope (0° = North, 90° = East, etc.)
        aspect_rad = math.atan2(-dz_dy, dz_dx)
        aspect_deg = (math.degrees(aspect_rad) + 360.0) % 360.0
        aspect_deg = round(aspect_deg, 2)

        # Cyclical components
        sin_asp = round(math.sin(math.radians(aspect_deg)), 4)
        cos_asp = round(math.cos(math.radians(aspect_deg)), 4)

        return slope_deg, aspect_deg, sin_asp, cos_asp

    @classmethod
    def compute_terrain_roughness(cls, window_3x3: np.ndarray) -> Optional[float]:
        """Calculates the Terrain Roughness Index (TRI) as the standard deviation of the 3x3 elevation window."""
        if window_3x3 is None or window_3x3.size < 4 or np.isnan(window_3x3).all():
            return None
        valid_vals = window_3x3[~np.isnan(window_3x3)]
        if len(valid_vals) < 4:
            return None
        return round(float(np.std(valid_vals)), 2)

    @classmethod
    def calculate_lapse_rate_adjustment(
        cls,
        obs_elevation_m: Optional[float],
        block_elevation_m: Optional[float]
    ) -> Optional[float]:
        """
        Calculates theoretical physical temperature change due to elevation difference.
        Delta_T = -0.0065 °C/m * (z_obs - z_block)
        """
        if obs_elevation_m is None or block_elevation_m is None:
            return None
        delta_z = obs_elevation_m - block_elevation_m
        adj = cls.STANDARD_LAPSE_RATE_C_PER_M * delta_z
        return round(adj, 3)

    @classmethod
    def extract_terrain_features(
        cls,
        latitude: float,
        longitude: float,
        dem_raster_path: Optional[str] = None,
        db_elevation_m: Optional[float] = None,
        block_elevation_m: Optional[float] = None
    ) -> TerrainFeatures:
        """
        Extracts all terrain features for a given geographic point from raster or database metadata.
        """
        elevation_val = db_elevation_m
        slope_deg, aspect_deg, sin_asp, cos_asp = None, None, None, None
        roughness = None

        if dem_raster_path and dem_raster_path != "":
            sampled_elev, window_3x3, pixel_res = RasterSampler.sample_point_and_window(
                raster_path=dem_raster_path,
                latitude=latitude,
                longitude=longitude,
                window_size=3
            )
            if sampled_elev is not None:
                elevation_val = round(sampled_elev, 2)
            if window_3x3 is not None and pixel_res is not None:
                slope_deg, aspect_deg, sin_asp, cos_asp = cls.compute_slope_and_aspect(
                    window_3x3=window_3x3,
                    res_x=pixel_res[0],
                    res_y=pixel_res[1]
                )
                roughness = cls.compute_terrain_roughness(window_3x3)

        elevation_diff = None
        lapse_adj = None
        if elevation_val is not None and block_elevation_m is not None:
            elevation_diff = round(elevation_val - block_elevation_m, 2)
            lapse_adj = cls.calculate_lapse_rate_adjustment(elevation_val, block_elevation_m)

        return TerrainFeatures(
            elevation_m=elevation_val,
            slope_deg=slope_deg,
            aspect_deg=aspect_deg,
            sin_aspect=sin_asp,
            cos_aspect=cos_asp,
            terrain_roughness=roughness,
            elevation_diff_to_block_m=elevation_diff,
            lapse_rate_temp_adjustment_c=lapse_adj,
        )
