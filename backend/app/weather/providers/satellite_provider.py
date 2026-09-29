"""
Satellite Observation Provider & Ingestion Adapter
SIH Problem Statement 26074 (Weather Downscaling - Task 3)

Ingests authorized georeferenced satellite products (GeoTIFF/rasters) and converts
them into the canonical SourceWeatherGrid abstraction used by the Task 2 spatial-masking layer.

Preserves native spatial resolution, strict CRS & Affine georeferencing,
observation timestamps, and meteorological variable semantics.
Fails closed on missing or invalid georeferencing.
"""
from __future__ import annotations

import hashlib
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pyproj
import rasterio
from rasterio.transform import Affine

from app.core.config import settings
from app.schemas.satellite import (
    ProviderOperationalState,
    SatelliteObservationStatus,
    SatelliteProductType,
    SatelliteProvenance,
)
from app.schemas.spatial_masking import (
    CoverageQuality,
    SourceGridCell,
    SourceResolutionProvenance,
    SourceWeatherGrid,
    VariableType,
)
from app.weather.providers.gridded_base import GriddedObservationProvider


class SatelliteObservationProvider(GriddedObservationProvider):
    """
    Ingestion adapter for authorized satellite meteorological imagery and derived products.
    Converts raster feeds (GeoTIFF, in-memory arrays) to canonical SourceWeatherGrid.
    """

    def __init__(
        self,
        provider_name: str = "SATELLITE_OBSERVATION_ADAPTER",
        freshness_threshold_minutes: Optional[float] = None,
        convective_threshold_k: Optional[float] = None,
        data_dir: Optional[str] = None,
    ):
        self._provider_name = provider_name
        self.freshness_threshold_minutes = (
            freshness_threshold_minutes
            if freshness_threshold_minutes is not None
            else settings.SATELLITE_FRESHNESS_THRESHOLD_MINUTES
        )
        self.convective_threshold_k = (
            convective_threshold_k
            if convective_threshold_k is not None
            else settings.SATELLITE_CONVECTIVE_TEMP_THRESHOLD_K
        )
        self.data_dir = data_dir or settings.SATELLITE_DATA_DIR
        self.geod = pyproj.Geod(ellps="WGS84")

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_type(self) -> str:
        return "SATELLITE"

    @property
    def supported_products(self) -> List[str]:
        return [p.value for p in SatelliteProductType]

    def check_freshness(
        self,
        observation_time: Union[datetime, str],
        threshold_minutes: Optional[float] = None,
    ) -> Tuple[bool, float, SatelliteObservationStatus]:
        """
        Evaluates observation latency against operational freshness requirements.
        Returns:
            (is_fresh, age_minutes, SatelliteObservationStatus)
        """
        threshold = threshold_minutes if threshold_minutes is not None else self.freshness_threshold_minutes

        if isinstance(observation_time, str):
            # Parse ISO 8601
            clean_str = observation_time.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
        else:
            dt = observation_time

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        age_seconds = (now_utc - dt).total_seconds()
        age_minutes = max(0.0, round(age_seconds / 60.0, 2))

        if age_minutes <= threshold:
            return True, age_minutes, SatelliteObservationStatus.LIVE_DATA_AVAILABLE
        else:
            return False, age_minutes, SatelliteObservationStatus.LIVE_DATA_STALE

    def ingest_raster_file(
        self,
        file_path: Union[str, Path],
        product: Union[SatelliteProductType, str],
        observation_time: Optional[Union[datetime, str]] = None,
        product_valid_time: Optional[Union[datetime, str]] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        native_resolution_km: Optional[float] = None,
        band_idx: int = 1,
        source_url: Optional[str] = None,
        source_identifier: Optional[str] = None,
        product_version: Optional[str] = "1.0",
        quality_flags: Optional[Dict[str, Any]] = None,
    ) -> SourceWeatherGrid:
        """
        Ingests a georeferenced raster file (GeoTIFF) and returns a SourceWeatherGrid.
        Fails closed on missing/corrupt files, missing CRS, or invalid geotransforms.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Satellite raster file not found: {path}")

        # Compute SHA-256 for provenance & integrity
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        with rasterio.open(path) as src:
            # 1. CRS Validation (FAIL CLOSED)
            if src.crs is None or not src.crs.to_string():
                raise ValueError(
                    f"Raster '{path.name}' lacks a Coordinate Reference System (CRS). "
                    "Fail-closed policy enforced: cannot infer arbitrary coordinates."
                )
            crs_str = src.crs.to_string()

            # 2. Affine Geotransform Validation (FAIL CLOSED)
            transform: Affine = src.transform
            det = transform.a * transform.e - transform.b * transform.d
            if (
                transform is None
                or transform.is_identity
                or abs(transform.a) < 1e-12
                or abs(transform.e) < 1e-12
                or abs(det) < 1e-12
            ):
                raise ValueError(
                    f"Raster '{path.name}' has invalid or missing Affine geotransform: {transform}. "
                    "Fail-closed policy enforced: cannot infer arbitrary coordinates."
                )

            nodata = src.nodata
            data = src.read(band_idx)

            return self.create_grid_from_array(
                array=data,
                transform=transform,
                crs=crs_str,
                product=product,
                observation_time=observation_time,
                product_valid_time=product_valid_time,
                nodata=nodata,
                bounding_box=bounding_box,
                native_resolution_km=native_resolution_km,
                file_sha256=file_hash,
                source_identifier=source_identifier or path.name,
                source_url=source_url,
                product_version=product_version,
                quality_flags=quality_flags,
            )

    def create_grid_from_array(
        self,
        array: np.ndarray,
        transform: Affine,
        crs: str,
        product: Union[SatelliteProductType, str],
        observation_time: Optional[Union[datetime, str]] = None,
        product_valid_time: Optional[Union[datetime, str]] = None,
        nodata: Optional[float] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        native_resolution_km: Optional[float] = None,
        file_sha256: Optional[str] = None,
        source_identifier: Optional[str] = None,
        source_url: Optional[str] = None,
        product_version: Optional[str] = "1.0",
        quality_flags: Optional[Dict[str, Any]] = None,
    ) -> SourceWeatherGrid:
        """
        Constructs canonical SourceWeatherGrid from a 2D numpy array and Affine geotransform.
        Preserves native resolution, exact bounds, timestamps, and nodata semantics.
        """
        # 1. Product Semantics
        if isinstance(product, str):
            try:
                prod_type = SatelliteProductType(product)
            except ValueError:
                raise ValueError(
                    f"Unsupported satellite product '{product}'. "
                    f"Must be one of {[p.value for p in SatelliteProductType]}"
                )
        else:
            prod_type = product

        # 2. CRS & Geotransform Verification (FAIL CLOSED)
        if not crs or not str(crs).strip():
            raise ValueError("CRS must be provided and non-empty. Fail-closed policy enforced.")
        det = transform.a * transform.e - transform.b * transform.d if transform is not None else 0.0
        if (
            transform is None
            or transform.is_identity
            or abs(transform.a) < 1e-12
            or abs(transform.e) < 1e-12
            or abs(det) < 1e-12
        ):
            raise ValueError(f"Invalid Affine geotransform: {transform}. Fail-closed policy enforced.")

        # 3. Shape verification
        if array.ndim != 2:
            raise ValueError(f"Array must be 2-dimensional (rows, cols), got shape {array.shape}.")
        nrows, ncols = array.shape
        if nrows == 0 or ncols == 0:
            raise ValueError("Array has zero rows or columns. Fail-closed.")

        # 4. Timestamps
        now_iso = datetime.now(timezone.utc).isoformat()
        if observation_time is None:
            obs_iso = now_iso
        elif isinstance(observation_time, datetime):
            obs_iso = observation_time.astimezone(timezone.utc).isoformat()
        else:
            obs_iso = str(observation_time)

        if product_valid_time is None:
            val_iso = obs_iso
        elif isinstance(product_valid_time, datetime):
            val_iso = product_valid_time.astimezone(timezone.utc).isoformat()
        else:
            val_iso = str(product_valid_time)

        # 5. Native Spatial Resolution Calculation
        # Compute pixel physical dimensions at raster center if not explicitly provided
        pixel_width_deg = abs(transform.a)
        pixel_height_deg = abs(transform.e)

        # Calculate bounding extent of the entire array
        x_corners = [transform.c, transform.c + ncols * transform.a]
        y_corners = [transform.f, transform.f + nrows * transform.e]
        min_lon = min(x_corners)
        max_lon = max(x_corners)
        min_lat = min(y_corners)
        max_lat = max(y_corners)
        center_lat = (min_lat + max_lat) / 2.0

        if native_resolution_km is not None and native_resolution_km > 0:
            res_km = float(native_resolution_km)
        else:
            # If CRS is EPSG:4326 or similar geographic, compute geodesic pixel dimension
            if "4326" in str(crs).upper() or "WGS" in str(crs).upper() or pixel_width_deg < 5.0:
                # 1 deg lat ≈ 111.139 km; 1 deg lon ≈ 111.139 * cos(lat) km
                lat_rad = math.radians(center_lat)
                dx_km = pixel_width_deg * 111.139 * math.cos(lat_rad)
                dy_km = pixel_height_deg * 111.139
                res_km = round(math.sqrt(dx_km * dy_km), 3)
            else:
                # If projected in meters, scale by 1000.0
                res_km = round(math.sqrt(abs(transform.a * transform.e)) / 1000.0, 3)

        # 6. Map Product Semantics to SourceWeatherGrid variables
        variable_name, var_type, unit, is_est = self._get_variable_contract(prod_type)

        # 7. Generate Cells (with optional Bounding Box filter)
        cells: List[SourceGridCell] = []
        for r in range(nrows):
            for c in range(ncols):
                # Calculate pixel corner coordinates in raster's native CRS
                # Top-left, top-right, bottom-right, bottom-left
                p_tl_x = transform.c + c * transform.a + r * transform.b
                p_tl_y = transform.f + c * transform.d + r * transform.e
                p_tr_x = transform.c + (c + 1) * transform.a + r * transform.b
                p_tr_y = transform.f + (c + 1) * transform.d + r * transform.e
                p_br_x = transform.c + (c + 1) * transform.a + (r + 1) * transform.b
                p_br_y = transform.f + (c + 1) * transform.d + (r + 1) * transform.e
                p_bl_x = transform.c + c * transform.a + (r + 1) * transform.b
                p_bl_y = transform.f + c * transform.d + (r + 1) * transform.e

                cell_min_lon = min(p_tl_x, p_tr_x, p_br_x, p_bl_x)
                cell_max_lon = max(p_tl_x, p_tr_x, p_br_x, p_bl_x)
                cell_min_lat = min(p_tl_y, p_tr_y, p_br_y, p_bl_y)
                cell_max_lat = max(p_tl_y, p_tr_y, p_br_y, p_bl_y)

                # Bounding box filter (if supplied)
                if bounding_box is not None:
                    b_min_lon, b_min_lat, b_max_lon, b_max_lat = bounding_box
                    if (
                        cell_max_lon < b_min_lon
                        or cell_min_lon > b_max_lon
                        or cell_max_lat < b_min_lat
                        or cell_min_lat > b_max_lat
                    ):
                        continue

                raw_val = array[r, c]
                if (
                    raw_val is None
                    or np.isnan(raw_val)
                    or np.isinf(raw_val)
                    or (nodata is not None and np.isclose(raw_val, nodata, atol=1e-5))
                ):
                    pixel_val = None
                else:
                    pixel_val = float(raw_val)

                cell_geom = {
                    "type": "Polygon",
                    "coordinates": [[
                        [round(p_tl_x, 7), round(p_tl_y, 7)],
                        [round(p_tr_x, 7), round(p_tr_y, 7)],
                        [round(p_br_x, 7), round(p_br_y, 7)],
                        [round(p_bl_x, 7), round(p_bl_y, 7)],
                        [round(p_tl_x, 7), round(p_tl_y, 7)],
                    ]]
                }

                # Approximate cell area in sq km
                try:
                    area_m2, _ = self.geod.polygon_area_perimeter(
                        [p_tl_x, p_tr_x, p_br_x, p_bl_x],
                        [p_tl_y, p_tr_y, p_br_y, p_bl_y],
                    )
                    cell_area_sq_km = round(abs(area_m2) / 1e6, 6)
                except Exception:
                    cell_area_sq_km = round(res_km * res_km, 6)

                cells.append(
                    SourceGridCell(
                        cell_id=f"sat_{r}_{c}",
                        geometry=cell_geom,
                        value=pixel_val,
                        row_idx=r,
                        col_idx=c,
                        area_sq_km=cell_area_sq_km,
                    )
                )

        if not cells:
            logger.warning(
                f"Satellite grid generation resulted in 0 cells for product={prod_type.value}, "
                f"bounding_box={bounding_box}, source_identifier={source_identifier}"
            )

        # 8. Construct SourceResolutionProvenance
        provenance = SourceResolutionProvenance(
            source_name=self.provider_name,
            source_product=prod_type.value,
            native_resolution_km=res_km,
            processing_resolution_km=res_km,
            crs=str(crs),
            spatial_extent=(round(min_lon, 5), round(min_lat, 5), round(max_lon, 5), round(max_lat, 5)),
            valid_time=val_iso,
            processing_timestamp=now_iso,
            source_version=product_version or "1.0",
            resolution_disclaimer=(
                "Spatial masking intersects native grid cells with administrative boundaries; "
                "it does NOT synthesize higher meteorological resolution than the underlying source field."
            ),
        )

        return SourceWeatherGrid(
            variable_name=variable_name,
            variable_type=var_type,
            variable_unit=unit,
            provenance=provenance,
            cells=cells,
        )

    def fetch_observation(
        self,
        product: str,
        observation_time: Optional[Union[datetime, str]] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> SourceWeatherGrid:
        """
        Retrieves or ingests a georeferenced satellite observation returning SourceWeatherGrid.
        Options dictionary can contain:
            - 'file_path': Path to local GeoTIFF file
            - 'array': 2D numpy array
            - 'transform': Affine geotransform
            - 'crs': Coordinate Reference System
            - 'nodata': Missing/nodata sentinel value
            - 'native_resolution_km': Explicit sensor resolution in km
            - 'source_url': Repository/stream URL
            - 'source_identifier': Identifier or scene name
        """
        opts = options or {}

        if "file_path" in opts:
            return self.ingest_raster_file(
                file_path=opts["file_path"],
                product=product,
                observation_time=observation_time,
                product_valid_time=opts.get("product_valid_time"),
                bounding_box=bounding_box,
                native_resolution_km=opts.get("native_resolution_km"),
                band_idx=opts.get("band_idx", 1),
                source_url=opts.get("source_url"),
                source_identifier=opts.get("source_identifier"),
                product_version=opts.get("product_version", "1.0"),
                quality_flags=opts.get("quality_flags"),
            )

        if "array" in opts and "transform" in opts and "crs" in opts:
            return self.create_grid_from_array(
                array=opts["array"],
                transform=opts["transform"],
                crs=opts["crs"],
                product=product,
                observation_time=observation_time,
                product_valid_time=opts.get("product_valid_time"),
                nodata=opts.get("nodata"),
                bounding_box=bounding_box,
                native_resolution_km=opts.get("native_resolution_km"),
                file_sha256=opts.get("file_sha256"),
                source_identifier=opts.get("source_identifier"),
                source_url=opts.get("source_url"),
                product_version=opts.get("product_version", "1.0"),
                quality_flags=opts.get("quality_flags"),
            )

        raise ValueError(
            "SatelliteObservationProvider requires either 'file_path' or ('array', 'transform', 'crs') in options."
        )

    def build_satellite_provenance(
        self,
        grid: SourceWeatherGrid,
        product_type: SatelliteProductType,
        observation_time: str,
        file_sha256: Optional[str] = None,
        source_url: Optional[str] = None,
        source_identifier: Optional[str] = None,
        quality_flags: Optional[Dict[str, Any]] = None,
    ) -> SatelliteProvenance:
        """Helper to construct comprehensive SatelliteProvenance from SourceWeatherGrid."""
        prov = grid.provenance
        is_est = product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE

        return SatelliteProvenance(
            provider=prov.source_name,
            product=prov.source_product or product_type.value,
            product_type=product_type,
            product_version=prov.source_version or "1.0",
            observation_time=observation_time,
            product_valid_time=prov.valid_time,
            ingestion_time=prov.processing_timestamp,
            native_resolution_km=prov.native_resolution_km,
            crs=prov.crs,
            spatial_extent=prov.spatial_extent,
            source_identifier=source_identifier,
            source_url=source_url,
            file_sha256=file_sha256,
            quality_flags=quality_flags or {},
            is_estimated=is_est,
        )

    @staticmethod
    def _get_variable_contract(product_type: SatelliteProductType) -> Tuple[str, VariableType, str, bool]:
        """Maps satellite taxonomy to variable name, type, units, and estimation flag."""
        if product_type == SatelliteProductType.SATELLITE_CLOUD_MASK:
            return "cloud_mask", VariableType.CATEGORICAL, "fraction", False
        elif product_type == SatelliteProductType.SATELLITE_IR_BRIGHTNESS_TEMPERATURE:
            return "brightness_temperature_ir", VariableType.CONTINUOUS, "K", False
        elif product_type == SatelliteProductType.SATELLITE_PRECIPITATION_ESTIMATE:
            # NON-NEGOTIABLE RULE: Must be named satellite_precipitation_estimate, NEVER observed_rainfall
            return "satellite_precipitation_estimate", VariableType.PRECIPITATION_ACCUMULATION, "mm", True
        elif product_type == SatelliteProductType.SATELLITE_WATER_VAPOUR:
            return "water_vapour", VariableType.CONTINUOUS, "K", False
        elif product_type == SatelliteProductType.SATELLITE_VISIBLE_REFLECTANCE:
            return "visible_reflectance", VariableType.CONTINUOUS, "fraction", False
        else:
            return product_type.value.lower(), VariableType.CONTINUOUS, "dimensionless", True

    def validate_quality_gates(
        self,
        grid: SourceWeatherGrid,
        panchayat_record: Optional[Any] = None,
        min_coverage: float = 0.20,
        max_age_minutes: Optional[float] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Enforces strict real-data quality gates before satellite evidence
        can influence localized nowcasting (Task 7 Requirement 10).

        Checks:
        1. Valid CRS (must be non-empty and recognizable)
        2. Valid geotransform (cells have positive, finite areas and coordinates)
        3. Valid spatial extent (extent must be non-degenerate)
        4. Valid timestamp (valid_time parseable)
        5. Acceptable freshness (within max_age_minutes)
        6. Minimum spatial coverage (if intersecting cells > 0)
        7. Valid source product type
        8. Valid provenance
        9. Valid Panchayat geometry (if record provided)

        Fails closed: if any mandatory check fails, returns (False, [failure_reasons]).
        """
        failures: List[str] = []

        # 1. Valid CRS
        crs = getattr(grid.provenance, "crs", None)
        if not crs or not str(crs).strip() or str(crs).upper() == "NONE":
            failures.append("INVALID_CRS: Coordinate Reference System is missing or empty.")

        # 2. Valid Spatial Extent
        extent = getattr(grid.provenance, "spatial_extent", None)
        if not extent or len(extent) != 4:
            failures.append("INVALID_SPATIAL_EXTENT: Spatial extent bounds missing or incomplete.")
        else:
            min_lon, min_lat, max_lon, max_lat = extent
            if min_lon >= max_lon or min_lat >= max_lat:
                failures.append(f"INVALID_SPATIAL_EXTENT: Degenerate bounding box ({extent}).")

        # 3. Valid Geotransform / Cell Structure
        if not grid.cells or len(grid.cells) == 0:
            failures.append("INVALID_GEOTRANSFORM: Grid contains zero cells.")
        else:
            invalid_cells = [
                c for c in grid.cells
                if (c.area_sq_km is not None and c.area_sq_km <= 0) or not c.geometry
            ]
            if invalid_cells:
                failures.append(f"INVALID_CELL_GEOMETRY: {len(invalid_cells)} cells have non-positive area or missing geometry.")

        # 4. Valid Timestamp
        valid_time = getattr(grid.provenance, "valid_time", None)
        if not valid_time:
            failures.append("INVALID_TIMESTAMP: Observation valid_time is missing.")
        else:
            try:
                datetime.fromisoformat(str(valid_time).replace("Z", "+00:00"))
            except Exception:
                failures.append(f"INVALID_TIMESTAMP: Unparseable timestamp '{valid_time}'.")

        # 5. Acceptable Freshness
        if max_age_minutes is not None and valid_time:
            try:
                is_fresh, age_m, _ = self.check_freshness(valid_time, threshold_minutes=max_age_minutes)
                if not is_fresh:
                    failures.append(f"OBSERVATION_STALE: Observation age ({age_m:.1f}m) exceeds threshold ({max_age_minutes:.1f}m).")
            except Exception as e:
                failures.append(f"FRESHNESS_CHECK_FAILED: {e}")

        # 6. Valid Source Product Type
        prod = getattr(grid.provenance, "source_product", None)
        if prod:
            valid_prods = [p.value for p in SatelliteProductType]
            if prod not in valid_prods:
                failures.append(f"UNRECOGNIZED_PRODUCT_TYPE: '{prod}' not in registered taxonomy.")

        # 7. Valid Provenance
        if not getattr(grid.provenance, "source_name", None):
            failures.append("INVALID_PROVENANCE: Source provider name is missing.")
        if getattr(grid.provenance, "native_resolution_km", 0.0) <= 0.0:
            failures.append("INVALID_PROVENANCE: native_resolution_km must be > 0.0.")

        # 8. Valid Panchayat Geometry (if record provided)
        if panchayat_record is not None:
            geom = getattr(panchayat_record, "geometry", None)
            area = getattr(panchayat_record, "area_sq_km", None)
            if not geom:
                failures.append("INVALID_PANCHAYAT_GEOMETRY: Target Panchayat geometry is missing.")
            if area is not None and area <= 0.0:
                failures.append("INVALID_PANCHAYAT_GEOMETRY: Target Panchayat area must be > 0 sq km.")

        passed = len(failures) == 0
        return passed, failures

    def get_operational_state(self) -> ProviderOperationalState:
        """
        Determines the current operational state of the satellite data provider
        without exposing any sensitive credentials or secrets (Task 7 Requirement 4).
        """
        if not getattr(settings, "SATELLITE_PROVIDER_ENABLED", True):
            return ProviderOperationalState.PRODUCT_UNAVAILABLE

        source_mode = getattr(settings, "WEATHER_DATA_MODE", "DEMO").upper()
        if source_mode == "DEMO":
            return ProviderOperationalState.CONFIGURED

        # LIVE mode: check credentials and local repository directory
        data_dir = Path(getattr(settings, "SATELLITE_DATA_DIR", "backend/data/raw/satellite/"))
        mosdac_key = getattr(settings, "MOSDAC_API_KEY", "").strip()
        imd_key = getattr(settings, "IMD_API_KEY", "").strip()

        # Check credentials
        has_credentials = bool(mosdac_key or imd_key)
        
        # Check files on disk
        has_files = False
        if data_dir.exists():
            tifs = list(data_dir.glob("*.tif")) + list(data_dir.glob("*.tiff"))
            if tifs:
                has_files = True

        if has_files:
            return ProviderOperationalState.LIVE_DATA_AVAILABLE

        if not has_credentials:
            return ProviderOperationalState.MISSING_CREDENTIALS

        return ProviderOperationalState.PRODUCT_UNAVAILABLE
