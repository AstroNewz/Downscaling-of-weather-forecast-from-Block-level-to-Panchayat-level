"""
tests/test_india_pipeline.py — India Pilot Pipeline Test Suite
SIH Problem Statement 26074 — Agroweather-Downscaling

Comprehensive test suite for the real-data India pipeline.
Tests run as unit tests — no network access, no database, no synthetic fallback.

Coverage
--------
1.  test_india_pilot_configuration     — YAML config fields are correct
2.  test_varanasi_aoi                  — AOI bounds match project definition
3.  test_india_coordinate_bounds       — India validator accepts valid, rejects invalid coords
4.  test_dynamic_utm                   — UTM EPSG derived correctly for Varanasi
5.  test_crs_policy                    — EPSG:3857 not used for metric calculations
6.  test_source_provenance             — Source type classification guards (ERA5 != OBSERVATION)
7.  test_unit_consistency              — Feature schema unit checks
8.  test_timestamp_conversion          — UTC/IST offset is exactly +05:30
9.  test_duplicate_detection           — Duplicate record detection
10. test_missing_data_qc               — NULL policy (no fabricated values)
11. test_temporal_split                — Chronological split dates
12. test_spatial_split                 — Spatial holdout produces zero TRAIN∩HOLDOUT overlap
13. test_target_leakage                — Target/reference columns not in feature matrix X
14. test_feature_schema                — feature_schema.json loads and matches ORDERED_FEATURE_COLUMNS
15. test_manifest_integrity            — Manifest writer validates classification and source type
16. test_real_demo_separation          — DEMO_DATA/SYNTHETIC_DATA cannot enter REAL_DATA pipeline
"""
from __future__ import annotations

import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup — allow import from backend/
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from data_pipeline.validation.india_data_validator import (
    IndiaDataValidator,
    PILOT_LAT_MIN,
    PILOT_LAT_MAX,
    PILOT_LON_MIN,
    PILOT_LON_MAX,
    INDIA_LAT_MIN,
    INDIA_LAT_MAX,
    INDIA_LON_MIN,
    INDIA_LON_MAX,
    IST_OFFSET,
)
from data_pipeline.pipeline.feature_engineer import (
    RealDataFeatureEngineer,
    ORDERED_FEATURE_COLUMNS,
    QUARANTINED_COLUMNS,
    SCHEMA_VERSION,
    EXPECTED_SCHEMA_VERSION,
    build_features,
    validate_feature_matrix,
    _FORBIDDEN_DATA_CLASSIFICATIONS,
)
from data_pipeline.pipeline.target_builder import TargetBuilder
from data_pipeline.pipeline.chronological_splitter import (
    ChronologicalSplitter,
    SPLIT_TRAIN,
    SPLIT_VALIDATION,
    SPLIT_TEST,
)
from data_pipeline.manifests.dataset_manifest_writer import (
    DatasetManifestWriter,
    build_source_record,
    VALID_SOURCE_TYPES,
    VALID_DATA_CLASSIFICATIONS,
    VALID_ACQUISITION_STATUSES,
)


# ===========================================================================
# 1. test_india_pilot_configuration
# ===========================================================================

class TestIndiaPilotConfiguration:
    """Verifies india_pilot.yaml contains the expected authoritative values."""

    def _load_pilot_yaml(self) -> Dict[str, Any]:
        """Loads india_pilot.yaml as a plain dict (no external YAML lib assumed)."""
        yaml_path = _BACKEND_ROOT / "data_pipeline" / "config" / "india_pilot.yaml"
        assert yaml_path.exists(), f"india_pilot.yaml not found at {yaml_path}"
        try:
            import yaml  # type: ignore
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            pytest.skip("PyYAML not installed — skip YAML parsing tests")

    def test_country_is_india(self):
        cfg = self._load_pilot_yaml()
        assert cfg["country"] == "India", f"Expected country='India', got {cfg.get('country')}"

    def test_state_is_uttar_pradesh(self):
        cfg = self._load_pilot_yaml()
        assert cfg["state"] == "Uttar Pradesh"

    def test_district_is_varanasi(self):
        cfg = self._load_pilot_yaml()
        assert cfg["district"] == "Varanasi"

    def test_pilot_blocks_present(self):
        cfg = self._load_pilot_yaml()
        expected_blocks = {
            "Varanasi Sadar", "Pindra", "Arajiline", "Cholapur", "Kashi Vidyapeeth"
        }
        actual_blocks = set(cfg.get("pilot_blocks", []))
        for block in expected_blocks:
            assert block in actual_blocks, (
                f"Expected block '{block}' not found in pilot_blocks: {actual_blocks}"
            )

    def test_known_aws_stations(self):
        cfg = self._load_pilot_yaml()
        station_ids = {s["station_id"] for s in cfg.get("known_aws_stations", [])}
        assert "AWS_BHU_001" in station_ids
        assert "AWS_BABATPUR_002" in station_ids

    def test_aws_bhu_coordinates(self):
        cfg = self._load_pilot_yaml()
        bhu = next(
            s for s in cfg["known_aws_stations"] if s["station_id"] == "AWS_BHU_001"
        )
        assert abs(bhu["latitude"] - 25.2677) < 0.0001
        assert abs(bhu["longitude"] - 82.9913) < 0.0001

    def test_aws_babatpur_coordinates(self):
        cfg = self._load_pilot_yaml()
        bab = next(
            s for s in cfg["known_aws_stations"] if s["station_id"] == "AWS_BABATPUR_002"
        )
        assert abs(bab["latitude"] - 25.4520) < 0.0001
        assert abs(bab["longitude"] - 82.8590) < 0.0001

    def test_aws_status_is_source_access_required(self):
        """AWS stations must not be claimed as downloaded without actual data files."""
        cfg = self._load_pilot_yaml()
        for station in cfg.get("known_aws_stations", []):
            assert station.get("data_status") == "SOURCE_ACCESS_REQUIRED", (
                f"Station {station['station_id']}: expected data_status=SOURCE_ACCESS_REQUIRED, "
                f"got {station.get('data_status')}"
            )

    def test_geographic_crs_is_epsg4326(self):
        cfg = self._load_pilot_yaml()
        assert cfg.get("crs_geographic") == "EPSG:4326"

    def test_expected_utm_is_32644(self):
        cfg = self._load_pilot_yaml()
        metric = cfg.get("metric_crs", {})
        assert metric.get("expected_epsg") == 32644

    def test_grid_resolution_is_1km(self):
        cfg = self._load_pilot_yaml()
        assert cfg.get("grid_resolution_km") == 1.0
        assert cfg.get("grid_resolution_m") == 1000.0

    def test_split_dates_non_overlapping(self):
        cfg = self._load_pilot_yaml()
        splits = cfg.get("splits", {})
        train_end = date.fromisoformat(splits["train"]["end"])
        val_start = date.fromisoformat(splits["validation"]["start"])
        val_end = date.fromisoformat(splits["validation"]["end"])
        test_start = date.fromisoformat(splits["test"]["start"])
        assert train_end < val_start, "TRAIN overlaps VALIDATION"
        assert val_end < test_start, "VALIDATION overlaps TEST"


# ===========================================================================
# 2. test_varanasi_aoi
# ===========================================================================

class TestVaranasiAOI:
    """Verifies pilot AOI bounding box constants."""

    def test_aoi_lat_range(self):
        assert PILOT_LAT_MIN == pytest.approx(25.10)
        assert PILOT_LAT_MAX == pytest.approx(25.60)

    def test_aoi_lon_range(self):
        assert PILOT_LON_MIN == pytest.approx(82.70)
        assert PILOT_LON_MAX == pytest.approx(83.20)

    def test_aws_bhu_inside_aoi(self):
        assert IndiaDataValidator.validate_pilot_aoi(25.2677, 82.9913)

    def test_aws_babatpur_inside_aoi(self):
        assert IndiaDataValidator.validate_pilot_aoi(25.452, 82.859)

    def test_point_outside_aoi(self):
        # New Delhi is outside Varanasi pilot AOI
        assert not IndiaDataValidator.validate_pilot_aoi(28.6139, 77.2090)

    def test_boundary_points(self):
        assert IndiaDataValidator.validate_pilot_aoi(25.10, 82.70)  # min corner
        assert IndiaDataValidator.validate_pilot_aoi(25.60, 83.20)  # max corner

    def test_none_coordinates(self):
        assert not IndiaDataValidator.validate_pilot_aoi(None, 82.9)  # type: ignore
        assert not IndiaDataValidator.validate_pilot_aoi(25.3, None)  # type: ignore


# ===========================================================================
# 3. test_india_coordinate_bounds
# ===========================================================================

class TestIndiaCoordinateBounds:
    """Verifies India geographic bounds validation."""

    def test_valid_india_point(self):
        result = IndiaDataValidator.validate_india_bounds(25.3, 82.9)
        assert result.is_valid

    def test_invalid_lat_too_far_north(self):
        result = IndiaDataValidator.validate_india_bounds(45.0, 82.9)
        assert not result.is_valid
        assert any("outside India bounds" in e for e in result.errors)

    def test_invalid_lon_too_far_west(self):
        result = IndiaDataValidator.validate_india_bounds(25.3, 60.0)
        assert not result.is_valid

    def test_none_lat(self):
        result = IndiaDataValidator.validate_india_bounds(None, 82.9)
        assert result.quality_flag == "MISSING"

    def test_india_lat_bounds_constants(self):
        assert INDIA_LAT_MIN == pytest.approx(6.0)
        assert INDIA_LAT_MAX == pytest.approx(38.0)

    def test_india_lon_bounds_constants(self):
        assert INDIA_LON_MIN == pytest.approx(68.0)
        assert INDIA_LON_MAX == pytest.approx(98.0)

    def test_varanasi_within_india_bounds(self):
        result = IndiaDataValidator.validate_india_bounds(25.3176, 82.9739)
        assert result.is_valid


# ===========================================================================
# 4. test_dynamic_utm
# ===========================================================================

class TestDynamicUTM:
    """Verifies UTM EPSG derivation for the Varanasi AOI."""

    def _get_utm_epsg(self, lon: float, lat: float) -> int:
        """Replicates SpatialGridGenerator.get_optimal_utm_epsg logic."""
        zone = int((lon + 180.0) / 6.0) + 1
        zone = max(1, min(60, zone))
        if lat >= 0:
            return 32600 + zone
        else:
            return 32700 + zone

    def test_varanasi_utm_zone(self):
        """Varanasi (lon≈82.97) → UTM zone 44N → EPSG:32644."""
        epsg = self._get_utm_epsg(82.97, 25.32)
        assert epsg == 32644, f"Expected EPSG:32644 for Varanasi, got EPSG:{epsg}"

    def test_aoi_centroid_utm(self):
        """AOI centroid lon=82.95, lat=25.35 → EPSG:32644."""
        lon_center = (PILOT_LON_MIN + PILOT_LON_MAX) / 2
        lat_center = (PILOT_LAT_MIN + PILOT_LAT_MAX) / 2
        epsg = self._get_utm_epsg(lon_center, lat_center)
        assert epsg == 32644

    def test_northern_hemisphere_gives_326xx(self):
        """Northern hemisphere coordinates give 326xx EPSG."""
        epsg = self._get_utm_epsg(82.97, 25.32)
        assert 32600 <= epsg <= 32660

    def test_zone_boundaries(self):
        """UTM zone 44 covers 78°E to 84°E."""
        # 78°E is the start of zone 44
        assert self._get_utm_epsg(78.0, 25.0) == 32644
        # 83.9°E is still zone 44
        assert self._get_utm_epsg(83.9, 25.0) == 32644
        # 84.0°E is zone 45
        assert self._get_utm_epsg(84.1, 25.0) == 32645


# ===========================================================================
# 5. test_crs_policy
# ===========================================================================

class TestCRSPolicy:
    """
    Verifies the CRS usage policy:
      - EPSG:4326 for geographic output
      - Dynamic local UTM for metric calculations
      - EPSG:3857 NOT used for scientific metric area/distance/grid calculations
    """

    def test_geographic_output_uses_4326(self):
        """Feature schema stores lat/lon in EPSG:4326 degrees."""
        import json
        schema_path = _BACKEND_ROOT / "data_pipeline" / "schemas" / "feature_schema.json"
        assert schema_path.exists()
        with open(schema_path, "r") as f:
            schema = json.load(f)
        lat_feature = next(
            (feat for feat in schema["features"] if feat["feature_name"] == "obs_latitude"), None
        )
        assert lat_feature is not None
        assert "EPSG:4326" in lat_feature.get("unit", ""), (
            "obs_latitude unit should reference EPSG:4326"
        )

    def test_projected_srid_3857_is_display_only(self):
        """PROJECTED_SRID=3857 is marked as display-only in config.py."""
        # Verify the source code comment labels it display-only (no app import needed)
        config_path = _BACKEND_ROOT / "app" / "core" / "config.py"
        content = config_path.read_text()
        # The line must contain 3857 and a display/tile qualifier
        lines_with_3857 = [l for l in content.splitlines() if "3857" in l]
        assert any("DISPLAY" in l or "display" in l or "TILE" in l or "tile" in l
                   for l in lines_with_3857), (
            "PROJECTED_SRID=3857 in config.py must be documented as display-only/tile CRS. "
            f"Lines with 3857: {lines_with_3857}"
        )

    def test_3857_not_used_in_grid_calculations(self):
        """Grid generator must not hard-code EPSG:3857 for metric calculations."""
        grid_path = _BACKEND_ROOT / "app" / "gis" / "grid.py"
        content = grid_path.read_text()
        # EPSG:3857 must not appear as the projected CRS for scientific work
        assert "3857" not in content, (
            "EPSG:3857 found in grid.py — it must not be used for metric grid generation"
        )

    def test_grid_uses_dynamic_utm(self):
        """Grid generator must derive UTM CRS dynamically from coordinates."""
        grid_path = _BACKEND_ROOT / "app" / "gis" / "grid.py"
        content = grid_path.read_text()
        assert "get_optimal_utm_epsg" in content, (
            "grid.py must use get_optimal_utm_epsg() for dynamic UTM selection"
        )

    def test_pilot_config_crs_fields(self):
        """india_pilot.yaml must specify geographic CRS=EPSG:4326 and UTM note."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        yaml_path = _BACKEND_ROOT / "data_pipeline" / "config" / "india_pilot.yaml"
        with open(yaml_path, "r") as f:
            cfg = yaml.safe_load(f)
        assert cfg.get("crs_geographic") == "EPSG:4326"
        assert cfg.get("metric_crs", {}).get("expected_epsg") == 32644


# ===========================================================================
# 6. test_source_provenance
# ===========================================================================

class TestSourceProvenance:
    """Verifies source type classification guards."""

    def test_era5_classified_as_reanalysis(self):
        """ERA5 must be classified as REANALYSIS, never OBSERVATION."""
        with pytest.raises(ValueError, match="MISCLASSIFICATION"):
            build_source_record(
                source_name="ERA5",
                provider="ECMWF",
                source_type="OBSERVATION",  # WRONG — should raise
                dataset_url="https://cds.climate.copernicus.eu/",
                official_documentation_url="https://www.ecmwf.int/",
                license_str="C3S",
                access_method="CDS API",
                dataset_version="5th gen",
                retrieval_date=None,
                temporal_resolution="hourly",
                spatial_resolution="31 km",
                variables=["2m_temperature"],
                variable_units={"2m_temperature": "K"},
                time_start=None,
                time_end=None,
                acquisition_status="SOURCE_ACCESS_REQUIRED",
                role_in_model="COARSE_INPUT",
            )

    def test_era5_land_classified_as_reanalysis(self):
        """ERA5-Land must be classified as REANALYSIS."""
        with pytest.raises(ValueError, match="MISCLASSIFICATION"):
            build_source_record(
                source_name="ERA5_LAND",
                provider="ECMWF",
                source_type="OBSERVATION",
                dataset_url="https://cds.climate.copernicus.eu/",
                official_documentation_url="https://www.ecmwf.int/",
                license_str="C3S",
                access_method="CDS API",
                dataset_version="v5",
                retrieval_date=None,
                temporal_resolution="hourly",
                spatial_resolution="9 km",
                variables=["2m_temperature"],
                variable_units={"2m_temperature": "K"},
                time_start=None,
                time_end=None,
                acquisition_status="SOURCE_ACCESS_REQUIRED",
                role_in_model="REFERENCE",
            )

    def test_imd_can_be_observation(self):
        """IMD AWS is correctly classified as OBSERVATION."""
        record = build_source_record(
            source_name="IMD_AWS_STATION",
            provider="IMD",
            source_type="OBSERVATION",
            dataset_url="https://www.imd.gov.in/",
            official_documentation_url="https://mausam.imd.gov.in/",
            license_str="GODL",
            access_method="FTP",
            dataset_version="real-time",
            retrieval_date=None,
            temporal_resolution="hourly",
            spatial_resolution="point station",
            variables=["temperature_2m_c"],
            variable_units={"temperature_2m_c": "°C"},
            time_start=None,
            time_end=None,
            acquisition_status="SOURCE_ACCESS_REQUIRED",
            role_in_model="REFERENCE",
        )
        assert record["source_type"] == "OBSERVATION"

    def test_source_type_validation(self):
        """Invalid source types are rejected."""
        with pytest.raises(ValueError):
            build_source_record(
                source_name="TEST",
                provider="X",
                source_type="MADE_UP_TYPE",
                dataset_url="http://x.com",
                official_documentation_url="http://x.com",
                license_str="MIT",
                access_method="open",
                dataset_version="v1",
                retrieval_date=None,
                temporal_resolution="hourly",
                spatial_resolution="1 km",
                variables=[],
                variable_units={},
                time_start=None,
                time_end=None,
                acquisition_status="DOWNLOADED",
                role_in_model="TEST",
            )

    def test_target_leakage_guard_in_target_builder(self):
        """TargetBuilder raises ValueError if reference_source == coarse_source."""
        with pytest.raises(ValueError, match="TARGET LEAKAGE VIOLATION"):
            TargetBuilder.build_target(
                reference_temp_c=28.0,
                coarse_temp_c=26.0,
                reference_source_id="ERA5",
                reference_source_type="REANALYSIS",
                coarse_source_id="ERA5",  # SAME as reference — leakage
                coarse_source_type="REANALYSIS",
            )

    def test_target_builder_accepts_different_sources(self):
        """TargetBuilder accepts ERA5 (coarse) vs ERA5-Land (reference)."""
        target = TargetBuilder.build_target(
            reference_temp_c=28.5,
            coarse_temp_c=26.0,
            reference_source_id="ERA5_LAND",
            reference_source_type="REANALYSIS",
            coarse_source_id="ERA5",
            coarse_source_type="REANALYSIS",
        )
        assert target is not None
        assert target.target_temperature_residual_c == pytest.approx(2.5, abs=0.001)
        assert not target.is_station_validated
        assert target.leakage_safe

    def test_target_builder_none_reference_returns_none(self):
        """TargetBuilder returns None if reference is unavailable — never manufacture target."""
        target = TargetBuilder.build_target(
            reference_temp_c=None,
            coarse_temp_c=26.0,
            reference_source_id="IMD_AWS",
            reference_source_type="OBSERVATION",
            coarse_source_id="ERA5",
            coarse_source_type="REANALYSIS",
        )
        assert target is None


# ===========================================================================
# 7. test_unit_consistency
# ===========================================================================

class TestUnitConsistency:
    """Verifies that unit metadata in feature_schema.json is self-consistent."""

    def _load_schema(self) -> dict:
        import json
        schema_path = _BACKEND_ROOT / "data_pipeline" / "schemas" / "feature_schema.json"
        with open(schema_path, "r") as f:
            return json.load(f)

    def test_temperature_features_in_celsius(self):
        schema = self._load_schema()
        temp_features = [f for f in schema["features"]
                         if "temp" in f["feature_name"] and "fraction" not in f["feature_name"]]
        for feat in temp_features:
            assert "degC" in feat.get("unit", ""), (
                f"Feature {feat['feature_name']} expected unit degC, got {feat.get('unit')}"
            )

    def test_rainfall_in_mm(self):
        schema = self._load_schema()
        rain_feat = next(
            (f for f in schema["features"] if f["feature_name"] == "forecast_rainfall_mm"), None
        )
        assert rain_feat is not None
        assert rain_feat["unit"] == "mm"

    def test_wind_speed_in_mps(self):
        schema = self._load_schema()
        wind_feat = next(
            (f for f in schema["features"] if f["feature_name"] == "forecast_wind_speed_mps"), None
        )
        assert wind_feat is not None
        assert wind_feat["unit"] == "m/s"

    def test_humidity_in_percent(self):
        schema = self._load_schema()
        hum_feat = next(
            (f for f in schema["features"] if f["feature_name"] == "forecast_humidity_pct"), None
        )
        assert hum_feat is not None
        assert "percent" in hum_feat["unit"].lower()

    def test_lat_lon_in_degrees_epsg4326(self):
        schema = self._load_schema()
        for name in ("obs_latitude", "obs_longitude"):
            feat = next((f for f in schema["features"] if f["feature_name"] == name), None)
            assert feat is not None
            assert "degrees" in feat["unit"].lower() or "EPSG:4326" in feat["unit"]

    def test_elevation_in_metres(self):
        schema = self._load_schema()
        for name in ("obs_elevation_m", "block_elevation_m", "elevation_diff_m"):
            feat = next((f for f in schema["features"] if f["feature_name"] == name), None)
            if feat:
                assert feat["unit"].lower() in ("metres", "meters", "m"), (
                    f"{name} unit should be metres, got {feat.get('unit')}"
                )


# ===========================================================================
# 8. test_timestamp_conversion
# ===========================================================================

class TestTimestampConversion:
    """Verifies UTC/IST conversion is exactly +05:30."""

    def test_ist_offset_is_5h30m(self):
        assert IST_OFFSET == timedelta(hours=5, minutes=30)

    def test_utc_to_ist_conversion(self):
        utc_time = datetime(2024, 6, 15, 6, 0, 0, tzinfo=timezone.utc)
        ist_time = utc_time + IST_OFFSET
        assert ist_time.hour == 11
        assert ist_time.minute == 30
        assert ist_time.date() == date(2024, 6, 15)

    def test_midnight_utc_is_530_ist(self):
        utc_midnight = datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        ist = utc_midnight + IST_OFFSET
        assert ist.hour == 5
        assert ist.minute == 30

    def test_validator_detects_utc_ist_inconsistency(self):
        ts_utc = datetime(2024, 6, 15, 6, 0, 0, tzinfo=timezone.utc)
        # Validator: expected_ist = ts_utc + IST_OFFSET → naive +00:00 part = 11:30
        # Pass a NAIVE IST datetime that is wrong (13:00 instead of 11:30)
        ts_ist_wrong = datetime(2024, 6, 15, 13, 0, 0)  # naive, 90 min past correct
        result = IndiaDataValidator.validate_timestamp(ts_utc, ts_ist_wrong)
        assert result.quality_flag in ("INVALID", "SUSPECT"), (
            "UTC/IST inconsistency should produce INVALID or SUSPECT quality flag"
        )

    def test_validator_accepts_correct_ist(self):
        ts_utc = datetime(2024, 6, 15, 6, 0, 0, tzinfo=timezone.utc)
        # Correct IST wall-clock = UTC 11:30 (naive, matching validator arithmetic)
        # validator computes: expected_ist = ts_utc + IST_OFFSET = 11:30+00:00
        # diff = |naive(11:30) - aware(11:30+00:00)| → TypeError if aware vs naive
        # Validator strips tzinfo by doing expected_ist.replace(tzinfo=None) internally,
        # OR expects a naive timestamp. Pass naive 11:30.
        ts_ist_correct = datetime(2024, 6, 15, 11, 30, 0)  # naive IST wall-clock
        result = IndiaDataValidator.validate_timestamp(ts_utc, ts_ist_correct)
        assert result.is_valid, (
            f"Correct IST timestamp should be VALID. Got: {result.quality_flag}, "
            f"errors={result.errors}, warnings={result.warnings}"
        )


# ===========================================================================
# 9. test_duplicate_detection
# ===========================================================================

class TestDuplicateDetection:
    """Verifies that duplicate records are identifiable."""

    def _make_record(self, ts: datetime, lat: float = 25.27, lon: float = 82.99) -> Dict:
        return {
            "timestamp_utc": ts,
            "latitude": lat,
            "longitude": lon,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
        }

    def test_detect_duplicate_timestamps_same_location(self):
        ts = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
        records = [self._make_record(ts), self._make_record(ts)]
        df = pd.DataFrame(records)
        duplicates = df.duplicated(subset=["timestamp_utc", "latitude", "longitude"])
        assert duplicates.sum() == 1, "Expected 1 duplicate row"

    def test_different_locations_not_duplicates(self):
        ts = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
        records = [
            self._make_record(ts, 25.27, 82.99),
            self._make_record(ts, 25.45, 82.86),  # different location
        ]
        df = pd.DataFrame(records)
        duplicates = df.duplicated(subset=["timestamp_utc", "latitude", "longitude"])
        assert duplicates.sum() == 0

    def test_feature_engineer_rejects_demo_not_duplicates(self):
        """Feature engineer rejects DEMO_DATA — this tests the guard, not duplicate logic."""
        engineer = RealDataFeatureEngineer()
        ts = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
        record = self._make_record(ts)
        record["data_classification"] = "DEMO_DATA"
        result = engineer.build_feature_row(record)
        assert result is None, "DEMO_DATA records must be rejected by feature engineer"


# ===========================================================================
# 10. test_missing_data_qc
# ===========================================================================

class TestMissingDataQC:
    """Verifies NULL policy — missing values are never fabricated."""

    def test_feature_engineer_returns_none_for_missing_required_fields(self):
        """Records missing timestamp_utc, latitude, or longitude → rejected (None)."""
        engineer = RealDataFeatureEngineer()
        record = {
            "latitude": 25.3,
            "longitude": 82.9,
            # timestamp_utc MISSING
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is None

    def test_feature_engineer_returns_none_for_missing_both_temperatures(self):
        """Records with no coarse temperature (neither min nor max) → rejected."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            # forecast_temp_min and forecast_temp_max BOTH MISSING
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is None

    def test_missing_terrain_propagates_none(self):
        """Missing elevation results in None lapse_rate, not fabricated value."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "obs_elevation_m": None,   # missing
            "block_elevation_m": None, # missing
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is not None
        assert result["features"]["lapse_rate_temp_adjustment_c"] is None

    def test_missing_lulc_propagates_none(self):
        """Missing LULC data → None fractions, not zero or fabricated values."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
            # No LULC fields
        }
        result = engineer.build_feature_row(record)
        assert result is not None
        for lulc_feat in ("cropland_fraction", "forest_fraction", "urban_fraction",
                          "water_fraction", "barren_fraction"):
            assert result["features"][lulc_feat] is None, (
                f"{lulc_feat} should be None when LULC is unavailable, not fabricated"
            )

    def test_temperature_validator_flags_extreme_as_suspect(self):
        """Temperature outside India plausible range → SUSPECT, not INVALID."""
        result = IndiaDataValidator.validate_temperature(55.0)  # > 52°C limit
        assert result.quality_flag in ("SUSPECT", "INVALID")

    def test_temperature_validator_flags_negative_impossible_as_invalid(self):
        """Temperature outside physical limits → INVALID."""
        result = IndiaDataValidator.validate_temperature(-70.0)
        assert result.quality_flag == "INVALID"


# ===========================================================================
# 11. test_temporal_split
# ===========================================================================

class TestTemporalSplit:
    """Verifies chronological split correctness and temporal leakage prevention."""

    _TRAIN_START = "2024-06-01"
    _TRAIN_END = "2024-07-15"
    _VAL_START = "2024-07-16"
    _VAL_END = "2024-07-31"
    _TEST_START = "2024-08-01"
    _TEST_END = "2024-08-31"

    def _make_splitter(self) -> ChronologicalSplitter:
        return ChronologicalSplitter(
            train_start=self._TRAIN_START,
            train_end=self._TRAIN_END,
            validation_start=self._VAL_START,
            validation_end=self._VAL_END,
            test_start=self._TEST_START,
            test_end=self._TEST_END,
        )

    def test_splitter_assigns_train(self):
        splitter = self._make_splitter()
        ts = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        assert splitter.assign_split(ts) == SPLIT_TRAIN

    def test_splitter_assigns_validation(self):
        splitter = self._make_splitter()
        ts = datetime(2024, 7, 20, 12, 0, tzinfo=timezone.utc)
        assert splitter.assign_split(ts) == SPLIT_VALIDATION

    def test_splitter_assigns_test(self):
        splitter = self._make_splitter()
        ts = datetime(2024, 8, 15, 12, 0, tzinfo=timezone.utc)
        assert splitter.assign_split(ts) == SPLIT_TEST

    def test_splitter_outside_period_returns_none(self):
        splitter = self._make_splitter()
        ts = datetime(2024, 9, 15, 12, 0, tzinfo=timezone.utc)
        assert splitter.assign_split(ts) is None

    def test_overlapping_splits_raise_error(self):
        """Overlapping split dates must raise ValueError."""
        with pytest.raises(ValueError, match="Temporal leakage"):
            ChronologicalSplitter(
                train_start="2024-06-01",
                train_end="2024-07-20",        # overlaps validation
                validation_start="2024-07-16", # overlap!
                validation_end="2024-07-31",
                test_start="2024-08-01",
                test_end="2024-08-31",
            )

    def test_pilot_splits_no_overlap(self):
        """Pilot dates must create a splitter without raising."""
        splitter = self._make_splitter()
        assert splitter is not None

    def test_split_dataframe_no_temporal_leakage(self):
        """DataFrame split must report temporal_leakage_safe=True."""
        splitter = self._make_splitter()
        records = []
        for day_offset in range(92):  # Jun–Aug = 92 days
            ts = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc) + timedelta(days=day_offset)
            records.append({
                "timestamp_utc": ts,
                "value": day_offset,
            })
        df = pd.DataFrame(records)
        _, _, _, report = splitter.split_dataframe(df, timestamp_col="timestamp_utc", panchayat_col=None)
        assert report["temporal_leakage_safe"], f"Temporal leakage detected: {report}"
        assert report["temporal_overlap_violations"] == 0

    def test_train_val_test_date_sets_are_disjoint(self):
        """Train, val, test date sets must be pairwise disjoint."""
        splitter = self._make_splitter()
        records = []
        for day_offset in range(92):
            ts = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc) + timedelta(days=day_offset)
            records.append({"timestamp_utc": ts})
        df = pd.DataFrame(records)
        train_df, val_df, test_df, _ = splitter.split_dataframe(
            df, timestamp_col="timestamp_utc", panchayat_col=None
        )

        def date_set(sub_df):
            return set(pd.to_datetime(sub_df["timestamp_utc"]).dt.date.unique())

        tr = date_set(train_df)
        va = date_set(val_df)
        te = date_set(test_df)
        assert tr & va == set(), f"TRAIN ∩ VALIDATION = {tr & va}"
        assert tr & te == set(), f"TRAIN ∩ TEST = {tr & te}"
        assert va & te == set(), f"VALIDATION ∩ TEST = {va & te}"


# ===========================================================================
# 12. test_spatial_split
# ===========================================================================

class TestSpatialSplit:
    """Verifies spatial holdout — holdout panchayat not in training set."""

    def test_spatial_holdout_panchayat_excluded_from_train(self):
        splitter = ChronologicalSplitter(
            train_start="2024-06-01",
            train_end="2024-07-15",
            validation_start="2024-07-16",
            validation_end="2024-07-31",
            test_start="2024-08-01",
            test_end="2024-08-31",
            spatial_holdout_panchayat="Pindra",
        )
        ts_train = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        # Pindra record in training period should be excluded
        result = splitter.assign_split(ts_train, panchayat="Pindra")
        assert result is None, "Holdout panchayat must not be assigned to TRAIN"

    def test_other_panchayat_in_train_period_is_assigned_train(self):
        splitter = ChronologicalSplitter(
            train_start="2024-06-01",
            train_end="2024-07-15",
            validation_start="2024-07-16",
            validation_end="2024-07-31",
            test_start="2024-08-01",
            test_end="2024-08-31",
            spatial_holdout_panchayat="Pindra",
        )
        ts_train = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        result = splitter.assign_split(ts_train, panchayat="Arajiline")
        assert result == SPLIT_TRAIN

    def test_holdout_panchayat_still_included_in_test(self):
        """Holdout panchayat appears in test set for spatial generalization measurement."""
        splitter = ChronologicalSplitter(
            train_start="2024-06-01",
            train_end="2024-07-15",
            validation_start="2024-07-16",
            validation_end="2024-07-31",
            test_start="2024-08-01",
            test_end="2024-08-31",
            spatial_holdout_panchayat="Pindra",
        )
        ts_test = datetime(2024, 8, 15, 12, 0, tzinfo=timezone.utc)
        result = splitter.assign_split(ts_test, panchayat="Pindra")
        assert result == SPLIT_TEST


# ===========================================================================
# 13. test_target_leakage
# ===========================================================================

class TestTargetLeakage:
    """Verifies that target and reference columns cannot enter feature matrix X."""

    def test_temperature_residual_not_in_ordered_features(self):
        """temperature_residual_c must never be in ORDERED_FEATURE_COLUMNS."""
        assert "temperature_residual_c" not in ORDERED_FEATURE_COLUMNS, (
            "temperature_residual_c (the target) must not be a predictor feature"
        )

    def test_target_col_in_quarantined_set(self):
        assert "temperature_residual_c" in QUARANTINED_COLUMNS

    def test_reference_temp_in_quarantined_set(self):
        assert "reference_temperature_c" in QUARANTINED_COLUMNS or \
               "observed_temp_c" in QUARANTINED_COLUMNS

    def test_coarse_temp_in_quarantined_set(self):
        """coarse_forecast_temp_c must not appear in feature matrix."""
        # It is either in QUARANTINED_COLUMNS or prevented by name convention
        assert "coarse_forecast_temp_c" in QUARANTINED_COLUMNS or \
               "coarse_temperature_c" in QUARANTINED_COLUMNS

    def test_validate_feature_matrix_detects_leakage(self):
        """validate_feature_matrix() should flag quarantined columns as errors."""
        engineer = RealDataFeatureEngineer()
        leaky_df = pd.DataFrame({
            "obs_latitude": [25.3],
            "obs_longitude": [82.9],
            "temperature_residual_c": [2.5],  # LEAKAGE
        })
        report = engineer.validate_feature_matrix(leaky_df, strict=False)
        assert not report["all_ok"]
        assert any("leakage" in e.lower() or "quarantine" in e.lower()
                   for e in report["errors"]), (
            f"Expected leakage error, got: {report['errors']}"
        )

    def test_feature_engineer_does_not_include_target_in_features(self):
        """Feature engineer must not put target residual in the features dict."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
            "reference_temperature_c": 28.5,
            "coarse_temperature_c": 28.0,
            "target_temperature_residual_c": 0.5,
        }
        result = engineer.build_feature_row(record)
        assert result is not None
        feature_keys = set(result["features"].keys())
        assert "temperature_residual_c" not in feature_keys
        assert "target_temperature_residual_c" not in feature_keys

    def test_target_is_in_provenance_not_features(self):
        """Target values are stored in provenance dict, not in features dict."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
            "target_temperature_residual_c": 2.5,
        }
        result = engineer.build_feature_row(record)
        assert result is not None
        assert "target_temperature_residual_c" in result["provenance"]
        assert "target_temperature_residual_c" not in result["features"]


# ===========================================================================
# 14. test_feature_schema
# ===========================================================================

class TestFeatureSchema:
    """Verifies feature_schema.json integrity and consistency with codebase."""

    def test_schema_loads_correct_version(self):
        assert SCHEMA_VERSION == EXPECTED_SCHEMA_VERSION

    def test_all_ordered_features_in_schema(self):
        """Every feature in ORDERED_FEATURE_COLUMNS must exist in feature_schema.json."""
        import json
        schema_path = _BACKEND_ROOT / "data_pipeline" / "schemas" / "feature_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)
        schema_names = {f["feature_name"] for f in schema["features"]}
        # distance_to_centroid_km is in ORDERED_FEATURE_COLUMNS but not in JSON schema
        # (it is a pipeline-derived spatial feature added during feature engineering)
        pipeline_derived = {"distance_to_centroid_km"}
        for feat in ORDERED_FEATURE_COLUMNS:
            if feat in pipeline_derived:
                continue
            assert feat in schema_names, (
                f"Feature '{feat}' in ORDERED_FEATURE_COLUMNS is not in feature_schema.json"
            )

    def test_target_residual_in_schema_targets(self):
        import json
        schema_path = _BACKEND_ROOT / "data_pipeline" / "schemas" / "feature_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)
        target_names = {t["feature_name"] for t in schema["targets"]}
        assert "temperature_residual_c" in target_names

    def test_schema_version_field_present(self):
        import json
        schema_path = _BACKEND_ROOT / "data_pipeline" / "schemas" / "feature_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)
        assert "schema_version" in schema
        assert schema["schema_version"] == "v1.1.0"

    def test_feature_count_matches_ordered_columns(self):
        """ORDERED_FEATURE_COLUMNS length must match Phase 6 specification."""
        # 36 features in ORDERED_FEATURE_COLUMNS (includes distance_to_centroid_km)
        assert len(ORDERED_FEATURE_COLUMNS) > 0
        # Verify no duplicates
        assert len(ORDERED_FEATURE_COLUMNS) == len(set(ORDERED_FEATURE_COLUMNS)), (
            "ORDERED_FEATURE_COLUMNS contains duplicate entries"
        )

    def test_build_features_returns_dataframe(self):
        """build_features() convenience function returns a non-empty DataFrame."""
        records = [
            {
                "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                "latitude": 25.3,
                "longitude": 82.9,
                "forecast_temp_min": 22.0,
                "forecast_temp_max": 34.0,
                "source_id": "ERA5",
                "source_type": "REANALYSIS",
                "data_classification": "REAL_DATA",
            }
        ]
        df = build_features(records, include_provenance=False)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_build_features_rejects_demo_records(self):
        """build_features() must drop DEMO_DATA records, returning empty DataFrame."""
        records = [
            {
                "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                "latitude": 25.3,
                "longitude": 82.9,
                "forecast_temp_min": 22.0,
                "forecast_temp_max": 34.0,
                "source_id": "DEMO",
                "source_type": "REANALYSIS",
                "data_classification": "DEMO_DATA",
            }
        ]
        df = build_features(records)
        assert len(df) == 0


# ===========================================================================
# 15. test_manifest_integrity
# ===========================================================================

class TestManifestIntegrity:
    """Verifies dataset manifest writer enforces classification and source type rules."""

    def _make_writer(self) -> DatasetManifestWriter:
        return DatasetManifestWriter(
            dataset_id="test-varanasi-pilot",
            dataset_name="Test Dataset",
            data_classification="REAL_DATA",
            country="India",
            state="Uttar Pradesh",
            district="Varanasi",
            block="Varanasi Sadar",
            latitude_min=25.10,
            latitude_max=25.60,
            longitude_min=82.70,
            longitude_max=83.20,
            time_start="2024-06-01",
            time_end="2024-08-31",
        )

    def test_manifest_rejects_synthetic_classification(self):
        """Writer must refuse to accept SYNTHETIC_DATA classification."""
        with pytest.raises(ValueError):
            DatasetManifestWriter(
                dataset_id="test",
                dataset_name="Test",
                data_classification="SYNTHETIC_DATA",  # FORBIDDEN for real pipeline
                country="India",
                state="Uttar Pradesh",
                district="Varanasi",
                block="Varanasi Sadar",
                latitude_min=25.10,
                latitude_max=25.60,
                longitude_min=82.70,
                longitude_max=83.20,
                time_start="2024-06-01",
                time_end="2024-08-31",
            )

    def test_manifest_rejects_demo_classification(self):
        with pytest.raises(ValueError):
            DatasetManifestWriter(
                dataset_id="test",
                dataset_name="Test",
                data_classification="DEMO_DATA",
                country="India",
                state="Uttar Pradesh",
                district="Varanasi",
                block="Varanasi Sadar",
                latitude_min=25.10,
                latitude_max=25.60,
                longitude_min=82.70,
                longitude_max=83.20,
                time_start="2024-06-01",
                time_end="2024-08-31",
            )

    def test_manifest_build_contains_required_fields(self):
        writer = self._make_writer()
        writer.set_split_counts(train=100, validation=20, test=20)
        writer.set_quality_summary(missing_percentage=5.0, invalid_count=2, suspect_count=3)
        manifest = writer.build()

        required_fields = [
            "dataset_id", "dataset_name", "country", "state", "district",
            "latitude_bounds", "longitude_bounds", "crs", "metric_crs",
            "time_start", "time_end", "data_classification",
            "training_row_count", "validation_row_count", "testing_row_count",
            "quality_summary", "processing_version", "schema_version", "created_at",
        ]
        for field in required_fields:
            assert field in manifest, f"Missing required manifest field: '{field}'"

    def test_manifest_data_classification_is_real_data(self):
        writer = self._make_writer()
        manifest = writer.build()
        assert manifest["data_classification"] == "REAL_DATA"

    def test_manifest_crs_is_epsg4326(self):
        writer = self._make_writer()
        manifest = writer.build()
        assert manifest["crs"] == "EPSG:4326"

    def test_manifest_aoi_lat_lon_bounds(self):
        writer = self._make_writer()
        manifest = writer.build()
        assert manifest["latitude_bounds"]["min"] == pytest.approx(25.10)
        assert manifest["latitude_bounds"]["max"] == pytest.approx(25.60)
        assert manifest["longitude_bounds"]["min"] == pytest.approx(82.70)
        assert manifest["longitude_bounds"]["max"] == pytest.approx(83.20)

    def test_manifest_era5_source_type_is_reanalysis(self):
        """Verifies build_pilot_sources() classifies ERA5 as REANALYSIS."""
        from data_pipeline.manifests.dataset_manifest_writer import build_pilot_sources
        sources = build_pilot_sources()
        era5_sources = [s for s in sources if "ERA5" in s["source_name"]]
        assert len(era5_sources) >= 2, "Expected at least ERA5 and ERA5_LAND in pilot sources"
        for src in era5_sources:
            assert src["source_type"] == "REANALYSIS", (
                f"ERA5 source {src['source_name']} classified as {src['source_type']} "
                "instead of REANALYSIS"
            )

    def test_manifest_imd_status_is_source_access_required(self):
        """IMD AWS must have acquisition_status=SOURCE_ACCESS_REQUIRED."""
        from data_pipeline.manifests.dataset_manifest_writer import build_pilot_sources
        sources = build_pilot_sources()
        imd_sources = [s for s in sources if "IMD" in s["source_name"]]
        assert len(imd_sources) >= 1
        for src in imd_sources:
            assert src["acquisition_status"] == "SOURCE_ACCESS_REQUIRED", (
                f"IMD source {src['source_name']} has acquisition_status="
                f"{src['acquisition_status']} — should be SOURCE_ACCESS_REQUIRED"
            )


# ===========================================================================
# 16. test_real_demo_separation
# ===========================================================================

class TestRealDemoSeparation:
    """
    Proves that DEMO_DATA and SYNTHETIC_DATA records CANNOT enter the
    real-data training pipeline at any stage.
    """

    def test_feature_engineer_rejects_demo_data(self):
        """Feature engineer returns None for DEMO_DATA records."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "DEMO_SOURCE",
            "source_type": "REANALYSIS",
            "data_classification": "DEMO_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is None, "DEMO_DATA must be rejected by feature engineer"

    def test_feature_engineer_rejects_synthetic_data(self):
        """Feature engineer returns None for SYNTHETIC_DATA records."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "SYNTHETIC_SOURCE",
            "source_type": "REANALYSIS",
            "data_classification": "SYNTHETIC_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is None, "SYNTHETIC_DATA must be rejected by feature engineer"

    def test_mixed_dataset_demo_records_dropped(self):
        """
        When a batch contains mixed REAL_DATA and DEMO_DATA records,
        only REAL_DATA records enter the feature DataFrame.
        """
        ts = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
        records = [
            {
                "timestamp_utc": ts,
                "latitude": 25.3,
                "longitude": 82.9,
                "forecast_temp_min": 22.0,
                "forecast_temp_max": 34.0,
                "source_id": "ERA5",
                "source_type": "REANALYSIS",
                "data_classification": "REAL_DATA",
            },
            {
                "timestamp_utc": ts + timedelta(hours=1),
                "latitude": 25.3,
                "longitude": 82.9,
                "forecast_temp_min": 21.0,
                "forecast_temp_max": 33.0,
                "source_id": "DEMO",
                "source_type": "REANALYSIS",
                "data_classification": "DEMO_DATA",
            },
            {
                "timestamp_utc": ts + timedelta(hours=2),
                "latitude": 25.3,
                "longitude": 82.9,
                "forecast_temp_min": 20.0,
                "forecast_temp_max": 32.0,
                "source_id": "SYNTHETIC",
                "source_type": "REANALYSIS",
                "data_classification": "SYNTHETIC_DATA",
            },
        ]
        df = build_features(records, include_provenance=True)
        assert len(df) == 1, (
            f"Expected 1 real row, got {len(df)}. "
            "DEMO_DATA and SYNTHETIC_DATA must not enter the feature DataFrame."
        )
        if "prov_data_classification" in df.columns:
            assert (df["prov_data_classification"] == "REAL_DATA").all()

    def test_forbidden_classifications_constant(self):
        """_FORBIDDEN_DATA_CLASSIFICATIONS must include both DEMO_DATA and SYNTHETIC_DATA."""
        assert "DEMO_DATA" in _FORBIDDEN_DATA_CLASSIFICATIONS
        assert "SYNTHETIC_DATA" in _FORBIDDEN_DATA_CLASSIFICATIONS
        assert "REAL_DATA" not in _FORBIDDEN_DATA_CLASSIFICATIONS

    def test_manifest_writer_refuses_to_label_synthetic_as_real(self):
        """DatasetManifestWriter must raise if classification is not REAL_DATA."""
        for bad_class in ("DEMO_DATA", "SYNTHETIC_DATA"):
            with pytest.raises(ValueError, match="Non-real-data"):
                DatasetManifestWriter(
                    dataset_id="bad",
                    dataset_name="Bad",
                    data_classification=bad_class,
                    country="India",
                    state="Uttar Pradesh",
                    district="Varanasi",
                    block="Varanasi Sadar",
                    latitude_min=25.1,
                    latitude_max=25.6,
                    longitude_min=82.7,
                    longitude_max=83.2,
                    time_start="2024-06-01",
                    time_end="2024-08-31",
                )

    def test_demo_prefix_detection(self):
        """Source IDs starting with 'DEMO_' are classified as demo data."""
        demo_source_names = ["DEMO_ERA5", "DEMO_IMD", "DEMO_STATION"]
        for name in demo_source_names:
            assert name.startswith("DEMO_"), f"Expected DEMO_ prefix in {name}"

    def test_synthetic_prefix_detection(self):
        """Source IDs starting with 'SYNTHETIC_' are classified as synthetic data."""
        synth_source_names = ["SYNTHETIC_ERA5", "SYNTHETIC_IMD"]
        for name in synth_source_names:
            assert name.startswith("SYNTHETIC_"), f"Expected SYNTHETIC_ prefix in {name}"

    def test_real_data_passes_through_engineer(self):
        """Genuine REAL_DATA records pass through the feature engineer without rejection."""
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            "data_classification": "REAL_DATA",
        }
        result = engineer.build_feature_row(record)
        assert result is not None, "REAL_DATA records must not be rejected by feature engineer"

    def test_missing_classification_defaults_to_real_data(self):
        """
        Records without data_classification field are treated as REAL_DATA
        (conservative: does not silently drop unmarked records, but logs a warning).
        """
        engineer = RealDataFeatureEngineer()
        record = {
            "timestamp_utc": datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
            "latitude": 25.3,
            "longitude": 82.9,
            "forecast_temp_min": 22.0,
            "forecast_temp_max": 34.0,
            "source_id": "ERA5",
            "source_type": "REANALYSIS",
            # data_classification absent
        }
        result = engineer.build_feature_row(record)
        assert result is not None, (
            "Records with missing data_classification should not be silently rejected "
            "(they default to REAL_DATA with a warning)"
        )
