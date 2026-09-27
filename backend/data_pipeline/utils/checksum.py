"""
File checksum utilities for data provenance tracking.

Every raw file downloaded by the pipeline must be checksummed and
recorded so that any future re-processing can verify data integrity.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def sha256_file(filepath: str | Path) -> str:
    """
    Computes SHA-256 checksum of a file in streaming blocks.

    Args:
        filepath: Absolute or relative path to the file.

    Returns:
        Hex-encoded SHA-256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Cannot checksum missing file: {path}")

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_retrieval_sidecar(
    filepath: str | Path,
    source_name: str,
    source_type: str,            # OBSERVATION / REANALYSIS / REMOTE_SENSING / DERIVED
    organization: str,
    dataset_name: str,
    download_url: str,
    license_str: str,
    version: str,
    variables: list,
    spatial_resolution: str,
    temporal_resolution: str,
    coverage: str,
    citation: str,
    notes: str = "",
    extra: Optional[dict] = None,
) -> Path:
    """
    Writes a JSON sidecar file alongside the downloaded raw file.
    Sidecar name: <original_filename>.provenance.json

    This is the primary provenance record for every raw dataset.
    It answers requirements 10 and 14 from the project specification.

    Returns:
        Path to the written sidecar file.
    """
    path = Path(filepath)
    checksum = sha256_file(path) if path.exists() else "FILE_NOT_FOUND"
    file_size_bytes = path.stat().st_size if path.exists() else 0

    sidecar = {
        "source_name": source_name,
        "source_type": source_type,
        "organization": organization,
        "dataset_name": dataset_name,
        "download_url": download_url,
        "license": license_str,
        "version": version,
        "variables": variables,
        "spatial_resolution": spatial_resolution,
        "temporal_resolution": temporal_resolution,
        "coverage": coverage,
        "citation": citation,
        "notes": notes,
        "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "file_path": str(path.resolve()),
        "file_size_bytes": file_size_bytes,
        "sha256_checksum": checksum,
        **(extra or {}),
    }

    sidecar_path = path.with_suffix(path.suffix + ".provenance.json")
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, ensure_ascii=False)

    return sidecar_path
