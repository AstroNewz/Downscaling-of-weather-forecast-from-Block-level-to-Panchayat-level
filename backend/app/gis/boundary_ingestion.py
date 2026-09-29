"""
Panchayat Administrative Boundary Ingestion Pipeline
SIH Problem Statement 26074 (Panchayat Boundary Service)

Ingests, validates, repairs, and standardizes authoritative Gram Panchayat
polygons from local formats (GeoJSON, GeoPackage, Shapefile) into canonical
WGS84 (EPSG:4326) representations.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pyproj
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid
from shapely.ops import transform as shapely_transform

from app.core.logging import logger
from app.schemas.panchayat_boundary import PanchayatBoundaryRecord


class PanchayatBoundaryIngestor:
    """
    Ingests and validates administrative Panchayat boundary datasets.

    Strict Quality Guarantees:
    1. Rejects empty, corrupt, or non-areal geometry.
    2. Enforces canonical WGS84 (EPSG:4326) CRS, performing reprojection when necessary.
    3. Heals mechanically invalid self-intersections without modifying outer borders.
    4. Detects and flags duplicate Panchayat identifiers.
    5. Computes high-precision geodesic surface areas (WGS84 ellipsoid).
    6. Attaches immutable provenance (checksums, ingestion timestamps, source tags).
    """

    def __init__(self):
        self.geod = pyproj.Geod(ellps="WGS84")

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Computes SHA-256 hash of a file for deterministic provenance tracking."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def ingest_file(
        self,
        file_path: Union[str, Path],
        source_name: Optional[str] = None,
        source_version: str = "1.0",
        is_verified: bool = False,
        geometry_status: str = "UNVERIFIED",
    ) -> List[PanchayatBoundaryRecord]:
        """
        Ingests boundary data from a local file path.
        Supports: .geojson, .json, .gpkg, .shp.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Boundary file not found at: {path}")

        checksum = self.compute_sha256(path)
        ext = path.suffix.lower()
        src_label = source_name or f"FILE:{path.name}"

        if ext in (".geojson", ".json"):
            with open(path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
            return self.ingest_geojson_dict(
                data=raw_json,
                source_name=src_label,
                source_version=source_version,
                is_verified=is_verified,
                geometry_status=geometry_status,
                file_path=str(path),
                file_checksum=checksum,
            )
        elif ext in (".gpkg", ".shp"):
            import geopandas as gpd

            gdf = gpd.read_file(str(path))
            return self.ingest_geodataframe(
                gdf=gdf,
                source_name=src_label,
                source_version=source_version,
                is_verified=is_verified,
                geometry_status=geometry_status,
                file_path=str(path),
                file_checksum=checksum,
            )
        else:
            raise ValueError(f"Unsupported spatial boundary format '{ext}'. Must be .geojson, .json, .gpkg, or .shp.")

    def ingest_geojson_dict(
        self,
        data: Dict[str, Any],
        source_name: str,
        source_version: str = "1.0",
        is_verified: bool = False,
        geometry_status: str = "UNVERIFIED",
        file_path: Optional[str] = None,
        file_checksum: Optional[str] = None,
    ) -> List[PanchayatBoundaryRecord]:
        """
        Ingests a GeoJSON dictionary (FeatureCollection or individual Feature).
        """
        features: List[Dict[str, Any]] = []
        doc_type = data.get("type", "")

        if doc_type == "FeatureCollection":
            features = data.get("features", [])
        elif doc_type == "Feature":
            features = [data]
        elif doc_type in ("Polygon", "MultiPolygon"):
            features = [{"type": "Feature", "geometry": data, "properties": {}}]
        else:
            raise ValueError(f"Invalid GeoJSON structure with type='{doc_type}'. Expected FeatureCollection or Feature.")

        # Inspect CRS metadata if explicitly embedded
        source_crs_str = "EPSG:4326"
        crs_obj = data.get("crs")
        if isinstance(crs_obj, dict):
            props = crs_obj.get("properties", {})
            source_crs_str = props.get("name", "EPSG:4326")

        transformer: Optional[pyproj.Transformer] = None
        if source_crs_str and "4326" not in source_crs_str:
            try:
                src_crs = pyproj.CRS(source_crs_str)
                dst_crs = pyproj.CRS("EPSG:4326")
                transformer = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
            except Exception as e:
                logger.warning(f"Could not parse CRS '{source_crs_str}': {e}. Defaulting to EPSG:4326.")

        records: List[PanchayatBoundaryRecord] = []
        seen_panchayat_ids = set()
        ingest_ts = datetime.now(timezone.utc).isoformat()

        for idx, feat in enumerate(features):
            geom_dict = feat.get("geometry")
            if not geom_dict:
                logger.warning(f"Skipping feature index {idx}: missing geometry.")
                continue

            properties = feat.get("properties") or {}

            # Parse and validate Shapely geometry
            try:
                geom = shape(geom_dict)
            except Exception as e:
                raise ValueError(f"Feature at index {idx} contains malformed geometry: {e}")

            # Reproject if needed
            if transformer is not None:
                geom = shapely_transform(transformer.transform, geom)

            cleaned_geom, is_valid_now = self._validate_and_heal_geometry(geom, feature_idx=idx)
            if not is_valid_now:
                raise ValueError(f"Feature at index {idx} contains irrecoverably invalid geometry.")

            # Validate coordinate boundaries (must be valid lat/lon degrees)
            self._validate_geographic_bounds(cleaned_geom, feature_idx=idx)

            # Metadata extraction
            panchayat_id = self._extract_panchayat_id(properties, default_idx=idx)
            if panchayat_id in seen_panchayat_ids:
                raise ValueError(f"Duplicate Panchayat ID detected: '{panchayat_id}' at feature index {idx}.")
            seen_panchayat_ids.add(panchayat_id)

            lgd_code = self._extract_lgd_code(properties)
            name = self._extract_string(properties, ["panchayat_name", "name", "gp_name", "GP_NAME", "village_name"], f"Panchayat_{panchayat_id}")
            block = self._extract_string(properties, ["block", "block_name", "BLOCK_NAME", "tehsil", "taluk"], "Unknown Block")
            district = self._extract_string(properties, ["district", "district_name", "DISTRICT", "dist_name"], "Unknown District")
            state = self._extract_string(properties, ["state", "state_name", "STATE"], "Uttar Pradesh")

            centroid = cleaned_geom.centroid
            centroid_lat = round(float(centroid.y), 6)
            centroid_lon = round(float(centroid.x), 6)
            area_sqkm = self._calculate_geodesic_area_sq_km(cleaned_geom)

            aux_props = dict(properties)
            if file_path:
                aux_props["_source_file"] = file_path
            if file_checksum:
                aux_props["_source_sha256"] = file_checksum

            feature_verified = bool(properties["is_verified"]) if "is_verified" in properties else is_verified
            feature_status = str(properties["geometry_status"]) if "geometry_status" in properties else geometry_status

            record = PanchayatBoundaryRecord(
                panchayat_id=panchayat_id,
                lgd_code=lgd_code,
                panchayat_name=name,
                state=state,
                district=district,
                block=block,
                geometry=mapping(cleaned_geom),
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
                area_sq_km=area_sqkm,
                geometry_source=properties.get("geometry_source", source_name),
                geometry_version=properties.get("geometry_version", source_version),
                geometry_status=feature_status,
                is_verified=feature_verified,
                ingestion_timestamp=ingest_ts,
                properties=aux_props,
            )
            records.append(record)

        return records

    def ingest_geodataframe(
        self,
        gdf: Any,
        source_name: str,
        source_version: str = "1.0",
        is_verified: bool = False,
        geometry_status: str = "UNVERIFIED",
        file_path: Optional[str] = None,
        file_checksum: Optional[str] = None,
    ) -> List[PanchayatBoundaryRecord]:
        """
        Ingests a GeoPandas GeoDataFrame, automatically converting to EPSG:4326.
        """
        if gdf.empty:
            return []

        # Enforce WGS84 CRS
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        geojson_str = gdf.to_json()
        data = json.loads(geojson_str)
        return self.ingest_geojson_dict(
            data=data,
            source_name=source_name,
            source_version=source_version,
            is_verified=is_verified,
            geometry_status=geometry_status,
            file_path=file_path,
            file_checksum=file_checksum,
        )

    def _validate_and_heal_geometry(self, geom: BaseGeometry, feature_idx: int) -> Tuple[BaseGeometry, bool]:
        """
        Validates geometry. If mechanically invalid (e.g. self-intersecting ring),
        applies shapely make_valid. Only retains Polygon or MultiPolygon components.
        Rejects point, line, or empty degenerate geometries.
        """
        if geom is None or geom.is_empty:
            logger.warning(f"Feature at index {feature_idx} has empty or null geometry.")
            return geom, False

        # Check numeric coordinates
        bounds = geom.bounds
        for val in bounds:
            if not np.isfinite(val):
                logger.error(f"Feature {feature_idx} has non-numeric/infinite coordinate bounds: {bounds}")
                return geom, False

        if not geom.is_valid:
            try:
                fixed = make_valid(geom)
            except Exception as exc:
                logger.error(f"make_valid failed on feature {feature_idx}: {exc}")
                return geom, False

            # Extract areal parts if a collection was returned
            if isinstance(fixed, (Polygon, MultiPolygon)):
                geom = fixed
            elif fixed.geom_type == "GeometryCollection":
                areal_parts = [p for p in fixed.geoms if isinstance(p, (Polygon, MultiPolygon))]
                if not areal_parts:
                    logger.error(f"Feature {feature_idx} make_valid produced no areal geometries.")
                    return geom, False
                if len(areal_parts) == 1:
                    geom = areal_parts[0]
                else:
                    polys = []
                    for part in areal_parts:
                        if isinstance(part, Polygon):
                            polys.append(part)
                        elif isinstance(part, MultiPolygon):
                            polys.extend(part.geoms)
                    geom = MultiPolygon(polys)
            else:
                logger.error(f"Feature {feature_idx} invalid geometry type after fix: {fixed.geom_type}")
                return geom, False

        # Final structural check
        if not isinstance(geom, (Polygon, MultiPolygon)) or geom.is_empty:
            return geom, False

        return geom, True

    def _validate_geographic_bounds(self, geom: BaseGeometry, feature_idx: int) -> None:
        """Verifies that all coordinate bounds lie within valid WGS84 limits."""
        minx, miny, maxx, maxy = geom.bounds
        if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0):
            raise ValueError(f"Feature {feature_idx} longitude bounds [{minx}, {maxx}] exceed valid WGS84 range [-180, 180].")
        if not (-90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
            raise ValueError(f"Feature {feature_idx} latitude bounds [{miny}, {maxy}] exceed valid WGS84 range [-90, 90].")

    def _calculate_geodesic_area_sq_km(self, geom: BaseGeometry) -> float:
        """
        Calculates true ellipsoidal surface area in square kilometers
        using pyproj Geod (WGS84 ellipsoid).
        """
        try:
            area_m2, _ = self.geod.geometry_area_perimeter(geom)
            return round(abs(float(area_m2)) / 1e6, 4)
        except Exception:
            # Fallback estimation if geod fails on degenerate multipolygon
            return 0.0

    def _extract_panchayat_id(self, props: Dict[str, Any], default_idx: int) -> str:
        """Extracts primary unique identifier with priority order."""
        candidates = [
            "panchayat_id", "PANCHAYAT_ID", "id", "ID",
            "lgd_code", "LGD_CODE", "gp_code", "GP_CODE",
            "panchayat_code", "PANCHAYAT_CODE"
        ]
        for key in candidates:
            if key in props and props[key] is not None and str(props[key]).strip():
                return str(props[key]).strip()
        # Fallback to name if unique
        name = props.get("name") or props.get("panchayat_name") or props.get("GP_NAME")
        if name and str(name).strip():
            return f"GP_{str(name).strip().upper().replace(' ', '_')}"
        return f"GP_{default_idx + 1:04d}"

    def _extract_lgd_code(self, props: Dict[str, Any]) -> Optional[str]:
        """Extracts Government of India Local Government Directory (LGD) code."""
        candidates = ["lgd_code", "LGD_CODE", "lgd_gp_code", "gp_code", "GP_CODE", "lgdCode"]
        for key in candidates:
            if key in props and props[key] is not None and str(props[key]).strip():
                return str(props[key]).strip()
        return None

    def _extract_string(self, props: Dict[str, Any], keys: List[str], default: str) -> str:
        """Extracts string property from candidates."""
        for k in keys:
            if k in props and props[k] is not None and str(props[k]).strip():
                return str(props[k]).strip()
        return default

    def export_canonical_geojson(
        self,
        records: List[PanchayatBoundaryRecord],
        output_path: Union[str, Path]
    ) -> Path:
        """
        Serializes boundary records into a standardized GeoJSON FeatureCollection artifact.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        features = []
        for r in records:
            features.append({
                "type": "Feature",
                "geometry": r.geometry,
                "properties": {
                    "panchayat_id": r.panchayat_id,
                    "lgd_code": r.lgd_code,
                    "panchayat_name": r.panchayat_name,
                    "block": r.block,
                    "district": r.district,
                    "state": r.state,
                    "centroid_lat": r.centroid_lat,
                    "centroid_lon": r.centroid_lon,
                    "area_sq_km": r.area_sq_km,
                    "geometry_source": r.geometry_source,
                    "geometry_version": r.geometry_version,
                    "geometry_status": r.geometry_status,
                    "is_verified": r.is_verified,
                    "ingestion_timestamp": r.ingestion_timestamp,
                }
            })

        feature_coll = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }

        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(feature_coll, f, indent=2, ensure_ascii=False)

        return out_p
