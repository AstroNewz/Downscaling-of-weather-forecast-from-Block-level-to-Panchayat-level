"""
Canonical Panchayat Boundary Registry
SIH Problem Statement 26074 (Panchayat Boundary Service)

Maintains an in-memory, thread-safe, authoritative registry of Gram Panchayat
boundary polygons and associated administrative metadata. Supports multi-key
indexing (by Panchayat ID, LGD code, and composite hierarchical name).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.core.config import settings
from app.core.logging import logger
from app.schemas.panchayat_boundary import PanchayatBoundaryRecord


class PanchayatBoundaryRegistry:
    """
    In-memory canonical registry for administrative Panchayat boundary polygons.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._records_by_id: Dict[str, PanchayatBoundaryRecord] = {}
        self._records_by_lgd: Dict[str, PanchayatBoundaryRecord] = {}
        self._records_by_composite_name: Dict[Tuple[str, str, str, str], PanchayatBoundaryRecord] = {}
        self._shapely_geometries: Dict[str, BaseGeometry] = {}
        self._source_manifests: List[Dict[str, Any]] = []

    def _make_composite_key(self, state: str, district: str, block: str, panchayat_name: str) -> Tuple[str, str, str, str]:
        """Normalizes administrative hierarchy components into canonical lookup key."""
        return (
            state.strip().lower(),
            district.strip().lower(),
            block.strip().lower(),
            panchayat_name.strip().lower(),
        )

    def register(self, record: PanchayatBoundaryRecord) -> None:
        """
        Registers a validated PanchayatBoundaryRecord into the canonical index.
        """
        with self._lock:
            # Parse Shapely geometry
            geom = shape(record.geometry)
            self._records_by_id[str(record.panchayat_id)] = record
            self._shapely_geometries[str(record.panchayat_id)] = geom

            if record.lgd_code:
                self._records_by_lgd[str(record.lgd_code).strip()] = record

            composite_key = self._make_composite_key(
                state=record.state,
                district=record.district,
                block=record.block,
                panchayat_name=record.panchayat_name
            )
            self._records_by_composite_name[composite_key] = record

    def register_all(self, records: List[PanchayatBoundaryRecord]) -> int:
        """Registers a batch of records. Returns count of registered records."""
        with self._lock:
            for r in records:
                self.register(r)
            return len(records)

    def get_by_id(self, panchayat_id: Union[str, int]) -> Optional[PanchayatBoundaryRecord]:
        """Looks up a Panchayat boundary record by unique Panchayat ID."""
        with self._lock:
            return self._records_by_id.get(str(panchayat_id).strip())

    def get(self, panchayat_id: Union[str, int]) -> Optional[PanchayatBoundaryRecord]:
        """Convenience alias for get_by_id."""
        return self.get_by_id(panchayat_id)


    def get_by_lgd_code(self, lgd_code: Union[str, int]) -> Optional[PanchayatBoundaryRecord]:
        """Looks up a Panchayat boundary record by Government of India LGD code."""
        with self._lock:
            return self._records_by_lgd.get(str(lgd_code).strip())

    def get_by_name(
        self,
        state: str,
        district: str,
        block: str,
        panchayat_name: str
    ) -> Optional[PanchayatBoundaryRecord]:
        """
        Looks up a Panchayat boundary record by administrative hierarchy:
        (state + district + block + panchayat_name).
        """
        key = self._make_composite_key(state, district, block, panchayat_name)
        with self._lock:
            return self._records_by_composite_name.get(key)

    def get_shapely_geometry(self, panchayat_id: Union[str, int]) -> Optional[BaseGeometry]:
        """Retrieves cached Shapely geometry for spatial queries."""
        with self._lock:
            return self._shapely_geometries.get(str(panchayat_id).strip())

    def list_all(self) -> List[PanchayatBoundaryRecord]:
        """Returns all registered Panchayat records."""
        with self._lock:
            return list(self._records_by_id.values())

    def list_ids(self) -> List[str]:
        """Returns list of registered Panchayat IDs."""
        with self._lock:
            return list(self._records_by_id.keys())

    def get_all_geometries(self) -> Dict[str, BaseGeometry]:
        """Returns map of panchayat_id -> BaseGeometry for spatial indexing."""
        with self._lock:
            return dict(self._shapely_geometries)

    def count(self) -> int:
        """Returns number of registered Panchayats."""
        with self._lock:
            return len(self._records_by_id)

    def clear(self) -> None:
        """Clears all registered records from memory."""
        with self._lock:
            self._records_by_id.clear()
            self._records_by_lgd.clear()
            self._records_by_composite_name.clear()
            self._shapely_geometries.clear()
            self._source_manifests.clear()

    def load_from_file(
        self,
        file_path: Union[str, Path],
        source_name: Optional[str] = None,
        source_version: str = "1.0",
        is_verified: bool = False,
        geometry_status: str = "UNVERIFIED",
    ) -> int:
        """
        Loads and registers boundaries from an authorized local file.
        """
        from app.gis.boundary_ingestion import PanchayatBoundaryIngestor

        ingestor = PanchayatBoundaryIngestor()
        records = ingestor.ingest_file(
            file_path=file_path,
            source_name=source_name,
            source_version=source_version,
            is_verified=is_verified,
            geometry_status=geometry_status,
        )
        return self.register_all(records)

    def load_from_configured_source(self) -> int:
        """
        Attempts to load boundaries from configured source path if one exists.
        Fails closed gracefully (returns 0) if no official source file is configured.
        """
        source_path = getattr(settings, "PANCHAYAT_BOUNDARY_SOURCE_PATH", None)
        if not source_path:
            logger.info("No PANCHAYAT_BOUNDARY_SOURCE_PATH configured; registry remains empty.")
            return 0

        p = Path(source_path)
        if not p.is_absolute():
            # Resolve relative to repo root
            backend_root = Path(__file__).resolve().parent.parent.parent
            p = (backend_root / source_path).resolve()

        if not p.exists():
            logger.info(f"Configured boundary file '{p}' does not exist on disk; registry initialized empty.")
            return 0

        try:
            count = self.load_from_file(
                file_path=p,
                source_name="CONFIGURED_LOCAL_SOURCE",
                source_version="1.0",
                is_verified=False,
                geometry_status="UNVERIFIED",
            )
            logger.info(f"Loaded {count} authoritative Panchayat boundaries from {p}.")
            return count
        except Exception as e:
            logger.error(f"Failed to load boundaries from {p}: {e}")
            return 0


# Global singleton registry instance
boundary_registry = PanchayatBoundaryRegistry()
