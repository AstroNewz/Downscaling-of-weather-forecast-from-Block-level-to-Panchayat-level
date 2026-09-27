"""
Data Acquisition Status Reporter

When a source cannot be accessed, the pipeline must NOT fabricate data.
Instead it produces a data_acquisition_status.json record for that source.

This module provides the canonical status types and the writer function.

Status types:
  SUCCESS              - Data downloaded and verified
  SOURCE_ACCESS_REQUIRED - Requires credentials or manual registration
  NETWORK_ERROR        - Transient connectivity failure
  PARTIAL              - Some temporal/spatial coverage downloaded
  SKIPPED              - Deliberately skipped (lower priority fallback used)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

STATUS_SUCCESS = "SUCCESS"
STATUS_ACCESS_REQUIRED = "SOURCE_ACCESS_REQUIRED"
STATUS_NETWORK_ERROR = "NETWORK_ERROR"
STATUS_PARTIAL = "PARTIAL"
STATUS_SKIPPED = "SKIPPED"

# Permitted source types — must match india_pilot.yaml
VALID_SOURCE_TYPES = {
    "OBSERVATION",
    "REANALYSIS",
    "NWP_FORECAST",
    "REMOTE_SENSING",
    "DERIVED",
}


def write_acquisition_status(
    output_dir: str | Path,
    source_name: str,
    source_type: str,
    status: str,
    reason: str,
    required_credentials: Optional[str] = None,
    required_manual_action: Optional[str] = None,
    download_instructions: Optional[str] = None,
    expected_file_format: Optional[str] = None,
    download_url: Optional[str] = None,
    files_written: Optional[List[str]] = None,
    aoi_bbox: Optional[tuple] = None,
    temporal_range: Optional[tuple] = None,
    expected_volume_mb: Optional[float] = None,
) -> Path:
    """
    Writes or updates data_acquisition_status.json in the output directory.

    One record per source is written. If the file already exists, the
    source entry is added/updated (existing entries are preserved).

    Args:
        output_dir: Directory where data_acquisition_status.json will be written.
        source_name: Identifier matching india_pilot.yaml source names.
        source_type: One of VALID_SOURCE_TYPES.
        status: One of the STATUS_* constants.
        reason: Human-readable reason for this status.
        required_credentials: What credentials/access are needed.
        required_manual_action: Step-by-step manual action required.
        download_instructions: How to manually obtain the data.
        expected_file_format: Format of expected downloaded files.
        download_url: Official source URL.
        files_written: List of files successfully written (for SUCCESS).
        aoi_bbox: (lat_min, lat_max, lon_min, lon_max) tuple.
        temporal_range: (start_date, end_date) tuple as ISO strings.
        expected_volume_mb: Approximate download size.

    Returns:
        Path to the written status file.
    """
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type '{source_type}'. Must be one of {VALID_SOURCE_TYPES}"
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status_file = out_dir / "data_acquisition_status.json"

    # Load existing entries if file exists
    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"generated_at": datetime.now(timezone.utc).isoformat(), "sources": {}}

    record = {
        "source_name": source_name,
        "source_type": source_type,
        "status": status,
        "reason": reason,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if required_credentials:
        record["required_credentials"] = required_credentials
    if required_manual_action:
        record["required_manual_action"] = required_manual_action
    if download_instructions:
        record["download_instructions"] = download_instructions
    if expected_file_format:
        record["expected_file_format"] = expected_file_format
    if download_url:
        record["download_url"] = download_url
    if files_written:
        record["files_written"] = files_written
    if aoi_bbox:
        record["aoi_bbox"] = {
            "lat_min": aoi_bbox[0], "lat_max": aoi_bbox[1],
            "lon_min": aoi_bbox[2], "lon_max": aoi_bbox[3],
        }
    if temporal_range:
        record["temporal_range"] = {
            "start": temporal_range[0], "end": temporal_range[1]
        }
    if expected_volume_mb is not None:
        record["expected_volume_mb"] = expected_volume_mb

    existing["sources"][source_name] = record
    existing["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return status_file


def print_status_report(output_dir: str | Path) -> None:
    """Pretty-prints the acquisition status report to stdout."""
    status_file = Path(output_dir) / "data_acquisition_status.json"
    if not status_file.exists():
        print("[acquisition_status] No status file found.")
        return

    with open(status_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + "=" * 70)
    print("DATA ACQUISITION STATUS REPORT")
    print("=" * 70)
    for src, rec in data.get("sources", {}).items():
        status = rec.get("status", "UNKNOWN")
        icon = {"SUCCESS": "✓", "SOURCE_ACCESS_REQUIRED": "⚠", "NETWORK_ERROR": "✗",
                "PARTIAL": "~", "SKIPPED": "○"}.get(status, "?")
        print(f"  {icon} [{status}] {src} ({rec.get('source_type', '?')})")
        print(f"      {rec.get('reason', '')}")
        if rec.get("required_manual_action"):
            print(f"      ACTION REQUIRED: {rec['required_manual_action']}")
    print("=" * 70)
