"""
Dataset Manifest Writer — India Pilot Real-Data Pipeline
SIH Problem Statement 26074 — Agroweather-Downscaling

Produces a complete, auditable dataset_manifest.json capturing:
  - geographic identity (country → state → district → block → panchayats)
  - all data sources with type, access status, license, version
  - temporal and spatial extents
  - row counts per split
  - QC summary (missing %, invalid count, suspect count)
  - file checksums
  - processing and schema version

RULES
-----
- data_classification must be one of: REAL_DATA | DEMO_DATA | SYNTHETIC_DATA
- DEMO_DATA and SYNTHETIC_DATA are NEVER labelled REAL_DATA.
- ERA5 and ERA5-Land are classified REANALYSIS (never OBSERVATION).
- If acquisition status is SOURCE_ACCESS_REQUIRED the record is included
  in the manifest with status SOURCE_ACCESS_REQUIRED — not fabricated.
- Only data files that actually exist on disk are checksummed.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MANIFEST_SCHEMA_VERSION = "v1.0.0"
PROCESSING_VERSION = "v1.1.0"  # matches FEATURE_SCHEMA_VERSION

VALID_DATA_CLASSIFICATIONS = {"REAL_DATA", "DEMO_DATA", "SYNTHETIC_DATA"}
VALID_SOURCE_TYPES = {
    "OBSERVATION",
    "REANALYSIS",
    "NWP_FORECAST",
    "REMOTE_SENSING",
    "DERIVED",
    "ADMINISTRATIVE",
}
VALID_ACQUISITION_STATUSES = {
    "DOWNLOADED",
    "VALIDATED",
    "SOURCE_ACCESS_REQUIRED",
    "UNAVAILABLE",
    "PARTIAL",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    """SHA-256 checksum of a file. Returns 'FILE_NOT_FOUND' if absent."""
    if not path.exists():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_files(directory: Path, glob: str = "*") -> int:
    """Counts files matching a glob pattern in a directory (non-recursive)."""
    if not directory.exists():
        return 0
    return sum(1 for p in directory.glob(glob) if p.is_file())


def _count_files_recursive(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob("*") if p.is_file())


def _validate_source_type(source_type: str, source_name: str) -> None:
    """Raises ValueError if source_type is invalid or misclassified."""
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type '{source_type}' for source '{source_name}'. "
            f"Must be one of {VALID_SOURCE_TYPES}."
        )
    # Explicit misclassification guard
    reanalysis_keywords = {"era5", "era5_land", "era5land", "merra", "cfsr"}
    if source_type == "OBSERVATION" and any(
        kw in source_name.lower() for kw in reanalysis_keywords
    ):
        raise ValueError(
            f"MISCLASSIFICATION DETECTED: '{source_name}' is a reanalysis product "
            "but has been classified as OBSERVATION. "
            "Use source_type='REANALYSIS' for ERA5/ERA5-Land."
        )


def _validate_classification(data_classification: str) -> None:
    if data_classification not in VALID_DATA_CLASSIFICATIONS:
        raise ValueError(
            f"Invalid data_classification '{data_classification}'. "
            f"Must be one of {VALID_DATA_CLASSIFICATIONS}."
        )
    if data_classification != "REAL_DATA":
        raise ValueError(
            f"data_classification='{data_classification}': Non-real-data manifests "
            "must not be written by this pipeline writer. "
            "Synthetic/demo data must remain isolated from the real-data pipeline."
        )


# ---------------------------------------------------------------------------
# Source record dataclass-like dict builder
# ---------------------------------------------------------------------------

def build_source_record(
    *,
    source_name: str,
    provider: str,
    source_type: str,
    dataset_url: str,
    official_documentation_url: str,
    license_str: str,
    access_method: str,
    dataset_version: str,
    retrieval_date: Optional[str],
    temporal_resolution: str,
    spatial_resolution: str,
    variables: List[str],
    variable_units: Dict[str, str],
    time_start: Optional[str],
    time_end: Optional[str],
    acquisition_status: str,
    role_in_model: str,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Builds a standardised source sub-record for dataset_manifest.json.

    Args:
        source_name         : Unique identifier matching india_pilot.yaml key.
        provider            : Organisation providing the data.
        source_type         : One of VALID_SOURCE_TYPES.
        dataset_url         : Direct dataset download/API URL.
        official_documentation_url: Official documentation URL.
        license_str         : License / terms of use.
        access_method       : How to access (API, FTP, open download, etc.).
        dataset_version     : Dataset version string.
        retrieval_date      : ISO date of last retrieval attempt. None if not attempted.
        temporal_resolution : Human-readable e.g. "hourly", "static".
        spatial_resolution  : Human-readable e.g. "31 km (0.25°)".
        variables           : List of variable names.
        variable_units      : Dict mapping variable name → unit string.
        time_start          : ISO date start of acquired period (None if not downloaded).
        time_end            : ISO date end of acquired period (None if not downloaded).
        acquisition_status  : One of VALID_ACQUISITION_STATUSES.
        role_in_model       : How the dataset is used (e.g. "COARSE_INPUT", "REFERENCE").
        notes               : Optional additional notes.

    Returns:
        Dict suitable for inclusion in manifest["sources"].

    Raises:
        ValueError on invalid source_type or acquisition_status.
    """
    _validate_source_type(source_type, source_name)
    if acquisition_status not in VALID_ACQUISITION_STATUSES:
        raise ValueError(
            f"Invalid acquisition_status '{acquisition_status}' for '{source_name}'. "
            f"Must be one of {VALID_ACQUISITION_STATUSES}."
        )

    return {
        "source_name": source_name,
        "provider": provider,
        "source_type": source_type,
        "dataset_url": dataset_url,
        "official_documentation_url": official_documentation_url,
        "license": license_str,
        "access_method": access_method,
        "dataset_version": dataset_version,
        "retrieval_date": retrieval_date,
        "temporal_resolution": temporal_resolution,
        "spatial_resolution": spatial_resolution,
        "variables": variables,
        "variable_units": variable_units,
        "time_start": time_start,
        "time_end": time_end,
        "acquisition_status": acquisition_status,
        "role_in_model": role_in_model,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Main manifest writer
# ---------------------------------------------------------------------------

class DatasetManifestWriter:
    """
    Generates dataset_manifest.json for the India pilot real-data pipeline.

    Usage::

        writer = DatasetManifestWriter(pilot_config=cfg)
        writer.set_split_counts(train=1200, validation=300, test=200)
        writer.set_quality_summary(missing_pct=12.4, invalid_count=5, suspect_count=23)
        writer.add_source(build_source_record(...))
        writer.add_processed_file(Path("data/processed/india/pilot/training.parquet"))
        manifest = writer.build()
        writer.write(Path("data/manifests/india/pilot/dataset_manifest.json"))
    """

    def __init__(
        self,
        *,
        dataset_id: str,
        dataset_name: str,
        data_classification: str = "REAL_DATA",
        country: str = "India",
        state: str,
        district: str,
        block: str,
        panchayats: Optional[List[str]] = None,
        latitude_min: float,
        latitude_max: float,
        longitude_min: float,
        longitude_max: float,
        crs: str = "EPSG:4326",
        metric_crs: str = "EPSG:32644 (dynamic local UTM — Varanasi pilot)",
        time_start: str,
        time_end: str,
    ) -> None:
        _validate_classification(data_classification)

        self._meta: Dict[str, Any] = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "data_classification": data_classification,
            "country": country,
            "state": state,
            "district": district,
            "block": block,
            "panchayats": panchayats or [],
            "aoi": f"{district} district, {state}, {country}",
            "latitude_bounds": {"min": latitude_min, "max": latitude_max},
            "longitude_bounds": {"min": longitude_min, "max": longitude_max},
            "crs": crs,
            "metric_crs": metric_crs,
            "time_start": time_start,
            "time_end": time_end,
        }

        self._sources: List[Dict[str, Any]] = []
        self._raw_files: List[Path] = []
        self._processed_files: List[Path] = []

        self._train_rows: Optional[int] = None
        self._val_rows: Optional[int] = None
        self._test_rows: Optional[int] = None
        self._total_rows: Optional[int] = None

        self._quality: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Builder methods
    # ------------------------------------------------------------------

    def add_source(self, source_record: Dict[str, Any]) -> "DatasetManifestWriter":
        """Adds a source record (built via build_source_record()) to the manifest."""
        self._sources.append(source_record)
        return self

    def add_raw_file(self, path: Path) -> "DatasetManifestWriter":
        """Registers a raw downloaded file for checksumming."""
        self._raw_files.append(path)
        return self

    def add_processed_file(self, path: Path) -> "DatasetManifestWriter":
        """Registers a processed output file for checksumming."""
        self._processed_files.append(path)
        return self

    def set_split_counts(
        self,
        train: int,
        validation: int,
        test: int,
    ) -> "DatasetManifestWriter":
        """Sets the record counts per chronological split."""
        self._train_rows = train
        self._val_rows = validation
        self._test_rows = test
        self._total_rows = train + validation + test
        return self

    def set_total_rows(self, total: int) -> "DatasetManifestWriter":
        """Overrides the total row count (useful when splits not yet computed)."""
        self._total_rows = total
        return self

    def set_quality_summary(
        self,
        missing_percentage: float,
        invalid_count: int,
        suspect_count: int,
        valid_count: Optional[int] = None,
        notes: str = "",
    ) -> "DatasetManifestWriter":
        """Attaches data quality summary statistics to the manifest."""
        self._quality = {
            "missing_percentage": round(missing_percentage, 2),
            "invalid_count": invalid_count,
            "suspect_count": suspect_count,
            "valid_count": valid_count,
            "notes": notes,
        }
        return self

    def build(self) -> Dict[str, Any]:
        """
        Constructs the complete manifest dictionary.

        Returns:
            Dict ready for JSON serialisation.
        """
        # File checksums
        raw_checksums: Dict[str, str] = {}
        for p in self._raw_files:
            raw_checksums[str(p)] = _sha256(p)

        processed_checksums: Dict[str, str] = {}
        for p in self._processed_files:
            processed_checksums[str(p)] = _sha256(p)

        # Combined checksum (hash of all processed file hashes)
        combined_input = "".join(sorted(processed_checksums.values())).encode()
        combined_checksum = hashlib.sha256(combined_input).hexdigest() if processed_checksums else "NO_FILES"

        manifest: Dict[str, Any] = {
            # Identity
            **self._meta,
            # Sources
            "sources": self._sources,
            # File counts
            "raw_file_count": len(self._raw_files),
            "processed_file_count": len(self._processed_files),
            # Row counts
            "row_count": self._total_rows,
            "training_row_count": self._train_rows,
            "validation_row_count": self._val_rows,
            "testing_row_count": self._test_rows,
            # Checksums
            "raw_file_checksums": raw_checksums,
            "processed_file_checksums": processed_checksums,
            "checksum": combined_checksum,
            # Quality
            "quality_summary": self._quality,
            # Versioning
            "processing_version": PROCESSING_VERSION,
            "schema_version": MANIFEST_SCHEMA_VERSION,
            # Timestamp
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return manifest

    def write(self, output_path: Path) -> Path:
        """
        Builds and writes dataset_manifest.json to output_path.

        Args:
            output_path: Destination path (parent directories created if needed).

        Returns:
            Path to the written manifest file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.build()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return output_path


# ---------------------------------------------------------------------------
# Pilot-specific pre-built sources
# ---------------------------------------------------------------------------

def build_pilot_sources() -> List[Dict[str, Any]]:
    """
    Returns the canonical list of source records for the Varanasi pilot.

    Acquisition statuses reflect what the download scripts actually report —
    no source is claimed as DOWNLOADED unless data files exist on disk.
    This function defines SOURCE_ACCESS_REQUIRED for restricted sources and
    DOWNLOADED status only for sources with open programmatic access.

    Callers (train_real_model.py, pipeline orchestrator) should verify actual
    file existence before changing any status to DOWNLOADED.
    """
    return [
        build_source_record(
            source_name="IMD_AWS_STATION",
            provider="India Meteorological Department (IMD)",
            source_type="OBSERVATION",
            dataset_url="https://www.imd.gov.in/pages/services_data.php",
            official_documentation_url="https://mausam.imd.gov.in/",
            license_str="Government of India Open Data License (GODL) — data sharing agreement required",
            access_method="FTP/API — requires IMD institutional data sharing agreement",
            dataset_version="Real-time / historical archive",
            retrieval_date=None,
            temporal_resolution="sub-hourly to hourly",
            spatial_resolution="point station",
            variables=["temperature_2m_c", "relative_humidity_pct", "precipitation_mm",
                       "wind_speed_kmh", "wind_direction_deg"],
            variable_units={
                "temperature_2m_c": "°C",
                "relative_humidity_pct": "%",
                "precipitation_mm": "mm",
                "wind_speed_kmh": "km/h",
                "wind_direction_deg": "degrees",
            },
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="INDEPENDENT_REFERENCE_TEMPERATURE (preferred ground truth for target construction)",
            notes=(
                "Stations: AWS_BHU_001 (25.2677N, 82.9913E), "
                "AWS_BABATPUR_002 (25.452N, 82.859E). "
                "Requires formal IMD data sharing agreement. "
                "Contact: https://www.imd.gov.in/pages/services_data.php"
            ),
        ),
        build_source_record(
            source_name="ERA5",
            provider="ECMWF / Copernicus Climate Change Service (C3S)",
            source_type="REANALYSIS",
            dataset_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels",
            official_documentation_url="https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5",
            license_str="Copernicus Climate Change Service (C3S) License — free for research",
            access_method="CDS API — requires free CDS account and ~/.cdsapirc",
            dataset_version="5th generation ERA5",
            retrieval_date=None,
            temporal_resolution="hourly",
            spatial_resolution="~31 km (0.25°)",
            variables=["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
                       "10m_v_component_of_wind", "total_precipitation", "surface_pressure",
                       "total_cloud_cover"],
            variable_units={
                "2m_temperature": "K (convert to °C: -273.15)",
                "2m_dewpoint_temperature": "K",
                "10m_u_component_of_wind": "m/s",
                "10m_v_component_of_wind": "m/s",
                "total_precipitation": "m (convert to mm: ×1000)",
                "surface_pressure": "Pa (convert to hPa: ÷100)",
                "total_cloud_cover": "fraction [0,1] (convert to %: ×100)",
            },
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="COARSE_INPUT (X — coarse weather predictor)",
            notes=(
                "REANALYSIS — NOT a station observation. "
                "Must NOT be used simultaneously as coarse input and reference temperature "
                "(would cause target leakage). "
                "Citation: Hersbach et al. (2020), Q.J.R. Meteorol. Soc., 146, 1999-2049."
            ),
        ),
        build_source_record(
            source_name="ERA5_LAND",
            provider="ECMWF / Copernicus Climate Change Service (C3S)",
            source_type="REANALYSIS",
            dataset_url="https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-land",
            official_documentation_url="https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5-land",
            license_str="Copernicus Climate Change Service (C3S) License — free for research",
            access_method="CDS API — same credentials as ERA5",
            dataset_version="ERA5-Land v5",
            retrieval_date=None,
            temporal_resolution="hourly",
            spatial_resolution="~9 km (0.1°)",
            variables=["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
                       "10m_v_component_of_wind", "total_precipitation", "surface_pressure"],
            variable_units={
                "2m_temperature": "K",
                "2m_dewpoint_temperature": "K",
                "10m_u_component_of_wind": "m/s",
                "10m_v_component_of_wind": "m/s",
                "total_precipitation": "m",
                "surface_pressure": "Pa",
            },
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model=(
                "REFERENCE_TEMPERATURE_FALLBACK — used as independent reference ONLY IF "
                "IMD station data is unavailable. This gives REANALYSIS-to-REANALYSIS "
                "comparison, NOT station-observed validation."
            ),
            notes=(
                "REANALYSIS — NOT a station observation. "
                "Citation: Munoz-Sabater et al. (2021), ESSD, 13, 4349-4383."
            ),
        ),
        build_source_record(
            source_name="SRTM_30M",
            provider="NASA / USGS",
            source_type="REMOTE_SENSING",
            dataset_url="https://lpdaac.usgs.gov/products/srtmgl1v003/",
            official_documentation_url=(
                "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation"
                "-shuttle-radar-topography-mission-srtm"
            ),
            license_str="NASA/USGS — free for scientific use",
            access_method="elevation Python library (auto-download) or NASA Earthdata HTTP",
            dataset_version="SRTMGL1 v003 (February 2000)",
            retrieval_date=None,
            temporal_resolution="static (single acquisition)",
            spatial_resolution="30 m (1 arc-second)",
            variables=["elevation_m"],
            variable_units={"elevation_m": "metres"},
            time_start="2000-02-11",
            time_end="2000-02-22",
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="SPATIAL_PREDICTOR (elevation_m, slope_deg, aspect_deg, terrain_roughness, lapse_rate_temp_adjustment_c)",
            notes="Tiles needed for Varanasi: N25E082, N25E083. Citation: Farr et al. (2007), Rev. Geophys., 45.",
        ),
        build_source_record(
            source_name="BHUVAN_LULC_50K",
            provider="NRSC / ISRO",
            source_type="REMOTE_SENSING",
            dataset_url="https://bhuvan.nrsc.gov.in/bhuvan_links.php",
            official_documentation_url="https://bhuvan.nrsc.gov.in/",
            license_str="NRSC Open Data Archive — non-commercial use permitted",
            access_method="Bhuvan WMS/WFS — requires free Bhuvan account (BHUVAN_USER, BHUVAN_PASS env vars)",
            dataset_version="biennial update",
            retrieval_date=None,
            temporal_resolution="biennial",
            spatial_resolution="~56 m (1:50,000 scale)",
            variables=["lulc_class"],
            variable_units={"lulc_class": "categorical"},
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="SPATIAL_PREDICTOR_PRIMARY (cropland_fraction, forest_fraction, urban_fraction, water_fraction, barren_fraction) — Indian authoritative LULC",
        ),
        build_source_record(
            source_name="ESA_WORLDCOVER_10M",
            provider="ESA / VITO",
            source_type="REMOTE_SENSING",
            dataset_url="https://esa-worldcover.org/en",
            official_documentation_url="https://esa-worldcover.org/en",
            license_str="CC BY 4.0",
            access_method="Open HTTP download — S3 bucket, no credentials required",
            dataset_version="v200 (2021)",
            retrieval_date=None,
            temporal_resolution="annual",
            spatial_resolution="10 m",
            variables=["lulc_class"],
            variable_units={"lulc_class": "categorical"},
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="SPATIAL_PREDICTOR_FALLBACK (used if Bhuvan LULC unavailable)",
            notes="Citation: Zanaga et al. (2022), Zenodo. Tile N24E081 for Varanasi.",
        ),
        build_source_record(
            source_name="SOILGRIDS_250M",
            provider="ISRIC — World Soil Information",
            source_type="DERIVED",
            dataset_url="https://soilgrids.org/",
            official_documentation_url="https://www.isric.org/explore/soilgrids",
            license_str="CC BY 4.0",
            access_method="Open REST API — no credentials required",
            dataset_version="SoilGrids 2.0",
            retrieval_date=None,
            temporal_resolution="static",
            spatial_resolution="250 m",
            variables=["soc", "phh2o", "clay", "sand", "silt", "bdod"],
            variable_units={
                "soc": "dg/kg",
                "phh2o": "pH×10",
                "clay": "g/kg",
                "sand": "g/kg",
                "silt": "g/kg",
                "bdod": "cg/cm³",
            },
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="AGRICULTURAL_CONTEXT (soil properties for advisory, not ML temperature feature)",
            notes="Citation: Poggio et al. (2021), SOIL, 7, 217-240.",
        ),
        build_source_record(
            source_name="LGD_BOUNDARIES",
            provider="Ministry of Panchayati Raj / MoRD, Government of India",
            source_type="ADMINISTRATIVE",
            dataset_url="https://lgdirectory.gov.in/",
            official_documentation_url="https://lgdirectory.gov.in/",
            license_str="Government of India Open Data License (GODL)",
            access_method="LGD open portal / API",
            dataset_version="current",
            retrieval_date=None,
            temporal_resolution="static (administrative)",
            spatial_resolution="cadastral level",
            variables=["district_boundary", "block_boundary", "panchayat_boundary"],
            variable_units={},
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="SPATIAL_AGGREGATION (panchayat → block → district hierarchy for output)",
        ),
    ]
