"""
Feature Engineer — India Pilot Real-Data Pipeline
SIH Problem Statement 26074 — Agroweather-Downscaling

Converts validated processed Indian weather/geospatial records into the
EXACT feature representation expected by Phase 6 (EngineeredFeatureRecord /
feature_schema.json v1.1.0).

Integration contract
--------------------
This module is a DATA-PIPELINE adapter: it reads feature_schema.json and
maps real acquired data into the Phase 6 feature matrix WITHOUT introducing
new features or removing existing ones.

It does NOT duplicate the app.ml.features.FeatureEngineer (which operates on
live DB objects). Instead it delegates cyclical-encoding arithmetic to the same
mathematical definitions found there, but operates on flat dictionaries/
DataFrames produced by the acquisition pipeline.

RULES
-----
- Never fill missing meteorological observations with fabricated values.
- NULL (float NaN / Python None) is ALWAYS preferred over invented data.
- Every generated row must carry its source provenance fields.
- No feature may be added that is not in feature_schema.json.
- feature_schema.json is read once at import time; schema version is validated.
- Records whose mandatory fields are all-null are rejected (returned as None).
- Records from DEMO / SYNTHETIC data classifications are rejected.

Phase 6 target (for reference — NOT constructed here):
    target_temperature_residual_c = reference_temperature_c - coarse_temperature_c
Target construction is handled by data_pipeline.pipeline.target_builder.TargetBuilder.
"""
from __future__ import annotations

import json
import math
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema constants — must stay in sync with feature_schema.json v1.1.0
# ---------------------------------------------------------------------------
FEATURE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "feature_schema.json"
)
EXPECTED_SCHEMA_VERSION = "v1.1.0"

# Source types that are never allowed in real-data pipeline training
_FORBIDDEN_DATA_CLASSIFICATIONS = {"DEMO_DATA", "SYNTHETIC_DATA"}

# IST offset
_IST_OFFSET = timedelta(hours=5, minutes=30)

# Environmental lapse rate (°C per metre of ascent)
_LAPSE_RATE_C_PER_M = -0.0065


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def _load_feature_schema() -> Tuple[List[str], List[str], str]:
    """
    Loads feature_schema.json and returns:
        (feature_names: List[str], target_names: List[str], schema_version: str)

    Raises FileNotFoundError or ValueError on schema problems.
    """
    if not FEATURE_SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"feature_schema.json not found at {FEATURE_SCHEMA_PATH}. "
            "Run from the backend root or ensure the schemas directory is present."
        )
    with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    version = raw.get("schema_version", "UNKNOWN")
    if version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"Feature schema version mismatch: expected {EXPECTED_SCHEMA_VERSION}, "
            f"got {version}. Update EXPECTED_SCHEMA_VERSION or regenerate schema."
        )

    feature_names = [f["feature_name"] for f in raw.get("features", [])]
    target_names = [t["feature_name"] for t in raw.get("targets", [])]
    return feature_names, target_names, version


# Load once at module import
try:
    FEATURE_NAMES, TARGET_NAMES, SCHEMA_VERSION = _load_feature_schema()
except Exception as _schema_err:
    logger.warning(
        "feature_schema.json could not be loaded at import time: %s. "
        "Call build_features() only after resolving this.", _schema_err
    )
    FEATURE_NAMES = []
    TARGET_NAMES = []
    SCHEMA_VERSION = "UNKNOWN"

# Authoritative ordered feature list — must match app.ml.feature_manifest.ALL_PREDICTOR_FEATURES
# Reproduced here so the data pipeline has no circular dependency on the app package.
ORDERED_FEATURE_COLUMNS: List[str] = [
    # Coarse NWP forecast predictors
    "forecast_temp_min",
    "forecast_temp_max",
    "forecast_temp_mean",
    "forecast_rainfall_mm",
    "forecast_humidity_pct",
    "forecast_wind_speed_mps",
    "forecast_wind_direction_deg",
    "forecast_cloud_cover_pct",
    "forecast_lead_hours",
    "time_diff_minutes",
    # Temporal cyclical
    "hour_of_day",
    "sin_hour",
    "cos_hour",
    "day_of_year",
    "sin_day_of_year",
    "cos_day_of_year",
    "month",
    "sin_month",
    "cos_month",
    # Spatial / topographic
    "obs_latitude",
    "obs_longitude",
    "distance_to_centroid_km",
    "obs_elevation_m",
    "block_elevation_m",
    "elevation_diff_m",
    "slope_deg",
    "aspect_deg",
    "sin_aspect",
    "cos_aspect",
    "terrain_roughness",
    "lapse_rate_temp_adjustment_c",
    # LULC
    "cropland_fraction",
    "forest_fraction",
    "urban_fraction",
    "water_fraction",
    "barren_fraction",
]

# Metadata / target columns — must NEVER enter the feature matrix X
QUARANTINED_COLUMNS: frozenset = frozenset({
    "sample_id",
    "station_id",
    "block_id",
    "block_name",
    "observation_time",
    "forecast_valid_time",
    "forecast_issue_time",
    "source_model",
    "dataset_version",
    "split",
    "observed_temp_c",
    "coarse_forecast_temp_c",
    "temperature_residual_c",
    "reference_temperature_c",
    "is_agricultural_cropland",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_cyclical(dt: datetime) -> Dict[str, Any]:
    """Computes cyclical temporal features — identical math to app.ml.features.FeatureEngineer."""
    hour = dt.hour + dt.minute / 60.0
    doy = dt.timetuple().tm_yday
    month = dt.month
    return {
        "hour_of_day": int(dt.hour),
        "sin_hour":    round(math.sin(2.0 * math.pi * hour / 24.0), 6),
        "cos_hour":    round(math.cos(2.0 * math.pi * hour / 24.0), 6),
        "day_of_year": int(doy),
        "sin_day_of_year": round(math.sin(2.0 * math.pi * doy / 365.25), 6),
        "cos_day_of_year": round(math.cos(2.0 * math.pi * doy / 365.25), 6),
        "month":       int(month),
        "sin_month":   round(math.sin(2.0 * math.pi * month / 12.0), 6),
        "cos_month":   round(math.cos(2.0 * math.pi * month / 12.0), 6),
    }


def _derive_lapse_rate(elevation_m: Optional[float], block_elevation_m: Optional[float]) -> Optional[float]:
    """elevation_diff × lapse_rate (°C). None if either elevation is unavailable."""
    if elevation_m is None or block_elevation_m is None:
        return None
    diff = elevation_m - block_elevation_m
    return round(diff * _LAPSE_RATE_C_PER_M, 4)


def _safe_wind_speed(u: Optional[float], v: Optional[float]) -> Optional[float]:
    """Derives scalar wind speed from u/v components (m/s). None if either component is missing."""
    if u is None or v is None:
        return None
    return round(math.sqrt(u ** 2 + v ** 2), 4)


def _safe_wind_dir(u: Optional[float], v: Optional[float]) -> Optional[float]:
    """Derives meteorological wind direction (0–360°) from u/v components. None if missing."""
    if u is None or v is None:
        return None
    deg = math.degrees(math.atan2(u, v))
    return round((deg + 360.0) % 360.0, 2)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in km between two WGS84 points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class RealDataFeatureEngineer:
    """
    Converts a validated real-data record dictionary into an ordered feature row
    compatible with Phase 6 (feature_schema.json v1.1.0).

    Usage::

        engineer = RealDataFeatureEngineer()
        row = engineer.build_feature_row(record)    # -> Optional[Dict[str, Any]]
        df  = engineer.build_feature_dataframe(records)  # -> pd.DataFrame

    Input record dictionary fields (all optional unless stated):

        timestamp_utc    : datetime (required) — observation UTC timestamp
        latitude         : float (required)    — WGS84 latitude
        longitude        : float (required)    — WGS84 longitude

        # Coarse NWP inputs (at least one temperature required for target)
        forecast_temp_min    : float | None — coarse min 2m temperature (°C)
        forecast_temp_max    : float | None — coarse max 2m temperature (°C)
        forecast_rainfall_mm : float | None — coarse precipitation (mm)
        forecast_humidity_pct: float | None — coarse relative humidity (%)
        forecast_u10_mps     : float | None — coarse 10m u-wind (m/s)
        forecast_v10_mps     : float | None — coarse 10m v-wind (m/s)
        forecast_cloud_cover_fraction: float | None — coarse cloud cover [0,1]
        forecast_valid_time  : datetime | None — forecast valid time (UTC)
        forecast_issue_time  : datetime | None — forecast issue time (UTC)

        # Terrain (from SRTM DEM)
        obs_elevation_m      : float | None
        block_elevation_m    : float | None
        slope_deg            : float | None
        aspect_deg           : float | None
        terrain_roughness    : float | None
        sin_aspect           : float | None  (pre-computed; else derived from aspect_deg)
        cos_aspect           : float | None  (pre-computed; else derived from aspect_deg)

        # Block spatial context
        block_centroid_lat   : float | None
        block_centroid_lon   : float | None

        # LULC (from Bhuvan / ESA WorldCover)
        cropland_fraction    : float | None
        forest_fraction      : float | None
        urban_fraction       : float | None
        water_fraction       : float | None
        barren_fraction      : float | None

        # Provenance (required for audit)
        source_id            : str (required)
        source_type          : str (required) — OBSERVATION / REANALYSIS / etc.
        data_classification  : str — REAL_DATA | DEMO_DATA | SYNTHETIC_DATA

        # Target columns (must be pre-computed by TargetBuilder, NOT engineered here)
        reference_temperature_c  : float | None
        coarse_temperature_c     : float | None
        target_temperature_residual_c: float | None
    """

    def __init__(self) -> None:
        self._schema_version = SCHEMA_VERSION
        self._feature_names = FEATURE_NAMES
        self._target_names = TARGET_NAMES

    # ------------------------------------------------------------------
    # Core build
    # ------------------------------------------------------------------

    def build_feature_row(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Converts a single validated record dict into a flat Phase 6 feature dict.

        Returns None if:
          - data_classification is DEMO_DATA or SYNTHETIC_DATA
          - mandatory fields (timestamp_utc, latitude, longitude) are missing
          - both forecast_temp_min and forecast_temp_max are None

        Never fabricates missing meteorological values.
        """
        # Guard 1: reject demo/synthetic data
        classification = record.get("data_classification", "REAL_DATA")
        if classification in _FORBIDDEN_DATA_CLASSIFICATIONS:
            logger.warning(
                "Rejected record with data_classification='%s'. "
                "Only REAL_DATA may enter the training pipeline. source_id=%s",
                classification, record.get("source_id", "UNKNOWN"),
            )
            return None

        # Guard 2: required spatial/temporal fields
        ts_utc: Optional[datetime] = record.get("timestamp_utc")
        lat: Optional[float] = record.get("latitude")
        lon: Optional[float] = record.get("longitude")

        if ts_utc is None or lat is None or lon is None:
            logger.debug("Record missing timestamp_utc/lat/lon — skipping.")
            return None

        # Guard 3: at least one coarse temperature must be present
        fc_min: Optional[float] = record.get("forecast_temp_min")
        fc_max: Optional[float] = record.get("forecast_temp_max")
        if fc_min is None and fc_max is None:
            logger.debug(
                "Record at (%s, %s) has no coarse temperature — skipping.", lat, lon
            )
            return None

        # ------------------------------------------------------------------
        # Derived forecast fields
        # ------------------------------------------------------------------
        fc_mean: Optional[float] = None
        if fc_min is not None and fc_max is not None:
            fc_mean = round((fc_min + fc_max) / 2.0, 4)
        elif fc_max is not None:
            fc_mean = fc_max
        elif fc_min is not None:
            fc_mean = fc_min

        fc_rain: Optional[float] = record.get("forecast_rainfall_mm")
        fc_hum: Optional[float] = record.get("forecast_humidity_pct")

        # Wind: prefer pre-computed speed/dir, else derive from u/v
        fc_wspd = record.get("forecast_wind_speed_mps") or _safe_wind_speed(
            record.get("forecast_u10_mps"), record.get("forecast_v10_mps")
        )
        fc_wdir = record.get("forecast_wind_direction_deg") or _safe_wind_dir(
            record.get("forecast_u10_mps"), record.get("forecast_v10_mps")
        )

        # Cloud cover: ERA5 stores as fraction [0,1] → convert to %
        raw_cc = record.get("forecast_cloud_cover_fraction")
        fc_cc: Optional[float] = None
        if raw_cc is not None:
            fc_cc = round(float(raw_cc) * 100.0, 2)

        # Lead hours / time diff
        fc_valid: Optional[datetime] = record.get("forecast_valid_time")
        fc_issue: Optional[datetime] = record.get("forecast_issue_time")
        lead_hours: Optional[float] = None
        time_diff_min: Optional[float] = None

        if fc_valid is not None and fc_issue is not None:
            lead_td = fc_valid - fc_issue
            lead_hours = round(lead_td.total_seconds() / 3600.0, 2)
            if lead_hours < 0:
                lead_hours = None  # Bad data

        if fc_valid is not None:
            diff_td = abs(ts_utc - fc_valid)
            time_diff_min = round(diff_td.total_seconds() / 60.0, 2)

        # ------------------------------------------------------------------
        # Temporal cyclical features
        # ------------------------------------------------------------------
        cyc = _compute_cyclical(ts_utc)

        # ------------------------------------------------------------------
        # Terrain features
        # ------------------------------------------------------------------
        elev_m: Optional[float] = record.get("obs_elevation_m")
        blk_elev_m: Optional[float] = record.get("block_elevation_m")
        elev_diff: Optional[float] = None
        if elev_m is not None and blk_elev_m is not None:
            elev_diff = round(elev_m - blk_elev_m, 2)

        slope: Optional[float] = record.get("slope_deg")
        aspect: Optional[float] = record.get("aspect_deg")

        # sin/cos aspect — use pre-computed if given, else derive
        sin_asp: Optional[float] = record.get("sin_aspect")
        cos_asp: Optional[float] = record.get("cos_aspect")
        if aspect is not None and (sin_asp is None or cos_asp is None):
            rad = math.radians(aspect)
            sin_asp = round(math.sin(rad), 6)
            cos_asp = round(math.cos(rad), 6)

        roughness: Optional[float] = record.get("terrain_roughness")
        lapse_adj = _derive_lapse_rate(elev_m, blk_elev_m)

        # Distance to block centroid
        dist_km: Optional[float] = None
        bc_lat: Optional[float] = record.get("block_centroid_lat")
        bc_lon: Optional[float] = record.get("block_centroid_lon")
        if bc_lat is not None and bc_lon is not None:
            dist_km = round(_haversine_km(lat, lon, bc_lat, bc_lon), 4)

        # ------------------------------------------------------------------
        # LULC features (NULL if not yet acquired)
        # ------------------------------------------------------------------
        crop_frac: Optional[float] = record.get("cropland_fraction")
        forest_frac: Optional[float] = record.get("forest_fraction")
        urban_frac: Optional[float] = record.get("urban_fraction")
        water_frac: Optional[float] = record.get("water_fraction")
        barren_frac: Optional[float] = record.get("barren_fraction")

        # ------------------------------------------------------------------
        # Assemble ordered feature dict
        # ------------------------------------------------------------------
        feature_row: Dict[str, Any] = {
            # --- Coarse NWP ---
            "forecast_temp_min":          fc_min,
            "forecast_temp_max":          fc_max,
            "forecast_temp_mean":         fc_mean,
            "forecast_rainfall_mm":       fc_rain,
            "forecast_humidity_pct":      fc_hum,
            "forecast_wind_speed_mps":    fc_wspd,
            "forecast_wind_direction_deg": fc_wdir,
            "forecast_cloud_cover_pct":   fc_cc,
            "forecast_lead_hours":        lead_hours,
            "time_diff_minutes":          time_diff_min,
            # --- Temporal ---
            "hour_of_day":       cyc["hour_of_day"],
            "sin_hour":          cyc["sin_hour"],
            "cos_hour":          cyc["cos_hour"],
            "day_of_year":       cyc["day_of_year"],
            "sin_day_of_year":   cyc["sin_day_of_year"],
            "cos_day_of_year":   cyc["cos_day_of_year"],
            "month":             cyc["month"],
            "sin_month":         cyc["sin_month"],
            "cos_month":         cyc["cos_month"],
            # --- Spatial / topographic ---
            "obs_latitude":               lat,
            "obs_longitude":              lon,
            "distance_to_centroid_km":    dist_km,
            "obs_elevation_m":            elev_m,
            "block_elevation_m":          blk_elev_m,
            "elevation_diff_m":           elev_diff,
            "slope_deg":                  slope,
            "aspect_deg":                 aspect,
            "sin_aspect":                 sin_asp,
            "cos_aspect":                 cos_asp,
            "terrain_roughness":          roughness,
            "lapse_rate_temp_adjustment_c": lapse_adj,
            # --- LULC ---
            "cropland_fraction":  crop_frac,
            "forest_fraction":    forest_frac,
            "urban_fraction":     urban_frac,
            "water_fraction":     water_frac,
            "barren_fraction":    barren_frac,
        }

        # Attach provenance passthrough (quarantined from X but kept for audit)
        provenance: Dict[str, Any] = {
            "timestamp_utc":            ts_utc.isoformat() if ts_utc else None,
            "timestamp_ist":            (ts_utc + _IST_OFFSET).isoformat() if ts_utc else None,
            "latitude":                 lat,
            "longitude":                lon,
            "state":                    record.get("state"),
            "district":                 record.get("district"),
            "block":                    record.get("block"),
            "panchayat":                record.get("panchayat"),
            "source_id":                record.get("source_id"),
            "source_type":              record.get("source_type"),
            "source_dataset":           record.get("source_dataset"),
            "source_version":           record.get("source_version"),
            "data_classification":      classification,
            "quality_flag":             record.get("quality_flag", "VALID"),
            # Auditable target components (passed through — NOT used as features)
            "reference_temperature_c":  record.get("reference_temperature_c"),
            "coarse_temperature_c":     record.get("coarse_temperature_c") or fc_mean,
            "target_temperature_residual_c": record.get("target_temperature_residual_c"),
        }

        return {"features": feature_row, "provenance": provenance}

    def build_feature_dataframe(
        self,
        records: List[Dict[str, Any]],
        include_provenance: bool = True,
    ) -> pd.DataFrame:
        """
        Converts a list of real-data record dicts into a DataFrame with:
            - feature columns (ORDERED_FEATURE_COLUMNS)
            - optional provenance columns (prefixed with 'prov_')

        Rows that fail validation are silently dropped (a count is logged).
        DataFrame columns are in the canonical order expected by Phase 6.

        Args:
            records: List of dictionaries from the acquisition pipeline.
            include_provenance: If True, attach provenance columns to the right
                                of the feature columns (useful for debugging).

        Returns:
            pd.DataFrame with feature columns + optional provenance columns.
            Returns empty DataFrame if all records are rejected.
        """
        rows = []
        rejected = 0
        for rec in records:
            result = self.build_feature_row(rec)
            if result is None:
                rejected += 1
                continue
            flat = dict(result["features"])
            if include_provenance:
                for k, v in result["provenance"].items():
                    flat[f"prov_{k}"] = v
            rows.append(flat)

        if rejected:
            logger.info(
                "Feature engineering: %d/%d records rejected (demo/synthetic/missing required fields).",
                rejected, len(records),
            )

        if not rows:
            logger.warning("Feature engineering produced 0 valid rows from %d input records.", len(records))
            # Return empty DataFrame with correct columns
            cols = list(ORDERED_FEATURE_COLUMNS)
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(rows)

        # Ensure canonical column order (feature columns first, then provenance)
        feature_cols_present = [c for c in ORDERED_FEATURE_COLUMNS if c in df.columns]
        other_cols = [c for c in df.columns if c not in ORDERED_FEATURE_COLUMNS]
        df = df[feature_cols_present + other_cols]

        return df

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_feature_matrix(
        self,
        df: pd.DataFrame,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Validates a feature DataFrame against the loaded feature schema.

        Checks:
        1. Required feature columns exist.
        2. No quarantined/target columns in the feature matrix.
        3. Missing value counts per feature.
        4. Datatype sanity (numeric features are float/int).
        5. Schema version compatibility.
        6. No NaN in latitude/longitude.

        Args:
            df: Feature DataFrame (features only — not the raw provenance subset).
            strict: If True, raises ValueError on schema violations.
                    If False, returns a validation report dict.

        Returns:
            dict with keys:
                schema_version_ok (bool)
                missing_features (List[str])
                quarantine_violations (List[str])
                missing_value_counts (Dict[str, int])
                missing_value_pct (Dict[str, float])
                all_ok (bool)
                errors (List[str])
                warnings (List[str])
        """
        errors: List[str] = []
        warnings: List[str] = []
        n = len(df)

        # 1. Schema version
        sv_ok = self._schema_version == EXPECTED_SCHEMA_VERSION
        if not sv_ok:
            errors.append(
                f"Schema version mismatch: loaded {self._schema_version}, "
                f"expected {EXPECTED_SCHEMA_VERSION}."
            )

        # 2. Missing feature columns
        missing_features = [f for f in ORDERED_FEATURE_COLUMNS if f not in df.columns]
        if missing_features:
            warnings.append(f"Feature columns absent from DataFrame: {missing_features}")

        # 3. Quarantine check
        qv = [c for c in df.columns if c in QUARANTINED_COLUMNS]
        if qv:
            errors.append(
                f"LEAKAGE RISK: quarantined columns found in feature matrix: {qv}. "
                "These must never enter X."
            )

        # 4. Missing value counts
        mv_counts: Dict[str, int] = {}
        mv_pct: Dict[str, float] = {}
        for col in ORDERED_FEATURE_COLUMNS:
            if col in df.columns:
                cnt = int(df[col].isna().sum())
                mv_counts[col] = cnt
                mv_pct[col] = round(cnt / max(n, 1) * 100.0, 2)

        # 5. Lat/lon must not be NaN
        for coord_col in ("obs_latitude", "obs_longitude"):
            if coord_col in df.columns:
                nan_count = int(df[coord_col].isna().sum())
                if nan_count > 0:
                    errors.append(
                        f"{coord_col} has {nan_count} NaN values — "
                        "coordinate is required for spatial features."
                    )

        all_ok = len(errors) == 0
        report = {
            "schema_version_ok": sv_ok,
            "missing_features": missing_features,
            "quarantine_violations": qv,
            "missing_value_counts": mv_counts,
            "missing_value_pct": mv_pct,
            "all_ok": all_ok,
            "errors": errors,
            "warnings": warnings,
            "row_count": n,
        }

        if strict and not all_ok:
            raise ValueError(
                "Feature matrix validation failed:\n" + "\n".join(errors)
            )

        return report

    @staticmethod
    def get_ordered_feature_columns() -> List[str]:
        """Returns the canonical ordered list of predictor feature column names."""
        return list(ORDERED_FEATURE_COLUMNS)

    @staticmethod
    def get_quarantined_columns() -> frozenset:
        """Returns the set of columns that must never enter the feature matrix X."""
        return QUARANTINED_COLUMNS

    @staticmethod
    def get_schema_version() -> str:
        """Returns the loaded feature schema version string."""
        return SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def build_features(
    records: List[Dict[str, Any]],
    include_provenance: bool = True,
) -> pd.DataFrame:
    """
    Convenience wrapper: build feature DataFrame from list of record dicts.

    Args:
        records: List of acquisition pipeline record dicts.
        include_provenance: Attach provenance columns (prov_*) to the DataFrame.

    Returns:
        pd.DataFrame ready for Phase 6 training/inference.
    """
    eng = RealDataFeatureEngineer()
    return eng.build_feature_dataframe(records, include_provenance=include_provenance)


def validate_feature_matrix(
    df: pd.DataFrame,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Convenience wrapper: validate a feature DataFrame.

    Args:
        df: Feature DataFrame.
        strict: If True, raises ValueError on errors.

    Returns:
        Validation report dict.
    """
    eng = RealDataFeatureEngineer()
    return eng.validate_feature_matrix(df, strict=strict)
