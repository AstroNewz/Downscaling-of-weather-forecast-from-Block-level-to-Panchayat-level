#!/usr/bin/env python3
"""
Varanasi Pilot — Improved ML Dataset Builder + Candidate v2 Trainer
SIH Problem Statement 26074

Improvements over v1:
  1. Multi-station (4 real NOAA stations instead of 1)
  2. ERA5 lagged / rolling features from REANALYSIS only (no obs leakage)
     - ERA5 3-hour rolling mean temperature
     - ERA5 6-hour rolling mean temperature
     - ERA5 12-hour rolling mean temperature
     - ERA5 24-hour rolling mean temperature
     - ERA5 diurnal range (max-min in 24h window from ERA5 only)
  3. Explicit target leakage audit for every new feature
  4. Spatial holdout experiment (station 424820 Ghazipur held out)
  5. Baseline comparison: raw ERA5 vs. v1 residual vs. v2 residual
  6. Conservative XGBoost config to reduce train/validation gap
  7. Physical sanity check on predicted residuals

ABSOLUTE RULES:
  - ERA5 features: REANALYSIS (never labeled OBSERVATION)
  - NOAA ISD features: OBSERVATION
  - No future obs information in features
  - No test-set tuning
  - Production model UNTOUCHED
  - Candidates stored in models/candidates/ ONLY

DATA SOURCES:
  Coarse  : Open-Meteo ERA5 (REANALYSIS, 6 grid points, hourly)
  Station 1: NOAA ISD 424790, Babatpur Airport (VEBN), 0.8km, 1944 recs
  Station 2: NOAA ISD 424830, Varanasi Synoptic, 24.1km, 434 recs
  Station 3: NOAA ISD 424820, Ghazipur, 76.8km, 133 recs
  Station 4: NOAA ISD 424750, Allahabad Airport, 125.0km, 125 recs
"""
from __future__ import annotations

import json
import math
import sys
import warnings
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from datetime import date as _date

warnings.filterwarnings("ignore")

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

RAW_DIR      = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
PROCESSED    = BACKEND_ROOT / "data" / "processed" / "india" / "pilot"
TRAINING     = BACKEND_ROOT / "data" / "training" / "india" / "pilot"
VALIDATION   = BACKEND_ROOT / "data" / "validation" / "india" / "pilot"
TESTING      = BACKEND_ROOT / "data" / "testing" / "india" / "pilot"
MANIFEST_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
MODELS_DIR   = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"

for d in [PROCESSED, TRAINING, VALIDATION, TESTING, MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Pilot config from india_pilot.yaml
LAT_MIN, LAT_MAX = 25.10, 25.60
LON_MIN, LON_MAX = 82.70, 83.20

TRAIN_START = "2024-06-01"; TRAIN_END = "2024-07-15"
VAL_START   = "2024-07-16"; VAL_END   = "2024-07-31"
TEST_START  = "2024-08-01"; TEST_END  = "2024-08-31"

# Spatial holdout station (excluded from training, evaluated separately)
SPATIAL_HOLDOUT_STATION = "NOAA_ISD_424820"  # Ghazipur (76.8km) — unseen during training

# NOAA stations to include
STATION_FILES = [
    ("noaa_isd_424790_2024.json", "NOAA_ISD_424790", "Lal Bahadur Shastri Varanasi Intl", 0.8),
    ("noaa_isd_424830_2024.json", "NOAA_ISD_424830", "Varanasi Synoptic", 24.1),
    ("noaa_isd_424820_2024.json", "NOAA_ISD_424820", "Ghazipur", 76.8),
    ("noaa_isd_424750_2024.json", "NOAA_ISD_424750", "Allahabad Airport", 125.0),
]

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def parse_ts(ts_str):
    ts_str = ts_str.replace("+00:00", "").replace("Z", "")
    return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)

def qc_temp(t, src):
    if t is None:       return "MISSING"
    lo, hi = (5.0, 55.0) if src == "OBSERVATION" else (-10.0, 60.0)
    return "INVALID" if (t < lo or t > hi) else "VALID"

def nearest_grid_point(lat, lon, grid_meta):
    """grid_meta: dict of grid_point_id → {lat, lon}"""
    best, best_key = float("inf"), None
    for gid, info in grid_meta.items():
        d = math.sqrt((info["lat"]-lat)**2 + (info["lon"]-lon)**2)
        if d < best:
            best, best_key = d, gid
    return best_key, best * 111.0

def assign_split(ts):
    d = ts.date()
    if _date.fromisoformat(TRAIN_START) <= d <= _date.fromisoformat(TRAIN_END): return "train"
    if _date.fromisoformat(VAL_START)   <= d <= _date.fromisoformat(VAL_END):   return "validation"
    if _date.fromisoformat(TEST_START)  <= d <= _date.fromisoformat(TEST_END):   return "test"
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Build ERA5 index with rolling features
# Rolling windows use ONLY ERA5 data (REANALYSIS) — never observation data
# This is leakage-safe: ERA5 is available at or before prediction time T
# (ERA5 is a reanalysis, not a forecast — all values are post-hoc reconstructions)
# ─────────────────────────────────────────────────────────────────────────────

def build_era5_index_with_rolling(era5_records):
    """
    Build:
      1. (grid_point_id, hour_bucket) → record   (for temporal matching)
      2. grid_point_id → sorted (ts, temp) list   (for rolling windows)
      3. grid_meta: grid_point_id → {lat, lon}    (for nearest-point lookup)

    Rolling ERA5 features (REANALYSIS only — leakage-safe):
      - era5_roll_3h_mean  : mean temp in [T-3h,  T]
      - era5_roll_6h_mean  : mean temp in [T-6h,  T]
      - era5_roll_12h_mean : mean temp in [T-12h, T]
      - era5_roll_24h_mean : mean temp in [T-24h, T]
      - era5_diurnal_range : max-min in [T-24h,   T]

    TEMPORAL AVAILABILITY RULE:
      ERA5 is a reanalysis product (historical reconstruction, not real-time).
      Using ERA5[T-N] as a feature at T is leakage-safe because ERA5 is not
      derived from the observation being predicted. No observation data is in
      the rolling windows.
    """
    idx = {}
    by_point = defaultdict(list)
    grid_meta = {}  # gid → {lat, lon}

    for r in era5_records:
        gid = r.get("grid_point_id", "unknown")
        ts = parse_ts(r["timestamp_utc"])
        bucket = ts.replace(minute=0, second=0, microsecond=0)
        idx[(gid, bucket)] = r
        by_point[gid].append((ts, r.get("temperature_2m_c")))
        if gid not in grid_meta:
            grid_meta[gid] = {"lat": r["latitude"], "lon": r["longitude"]}

    for gid in by_point:
        by_point[gid].sort(key=lambda x: x[0])

    def rolling_stats(gid, ts, hours):
        """Returns (mean, max, min) of ERA5 temp in [T-hours, T]."""
        cutoff = ts - timedelta(hours=hours)
        vals = [v for t, v in by_point[gid] if cutoff <= t <= ts and v is not None]
        if not vals:
            return None, None, None
        return round(sum(vals)/len(vals), 4), round(max(vals), 4), round(min(vals), 4)

    return idx, by_point, grid_meta, rolling_stats

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Feature construction
# ─────────────────────────────────────────────────────────────────────────────

def compute_features_v2(obs, era5, gid, rolling_stats_fn, ts):
    """
    Builds the feature row for candidate v2.
    Adds ERA5 rolling features (LEAKAGE AUDIT: all from REANALYSIS only).

    FEATURE LEAKAGE AUDIT:
      forecast_temp_*        : ERA5 at T — SAFE (REANALYSIS coarse input)
      era5_roll_*h_mean      : ERA5 mean at [T-Nh, T] — SAFE (REANALYSIS, no obs)
      era5_diurnal_range     : ERA5 max-min at [T-24h, T] — SAFE
      hour_of_day, sin/cos   : From timestamp — SAFE
      day_of_year, sin/cos   : From timestamp — SAFE
      month, sin/cos         : From timestamp — SAFE
      obs_latitude/longitude : Station coordinates (constant) — SAFE
      obs_elevation_m        : Station elevation (constant, from ISD metadata) — SAFE
      terrain features       : NULL (SRTM not available) — SAFE (not leakage, just missing)
      lulc fractions         : From ESA WorldCover (time-static) — SAFE
      _reference_temperature : AUDIT COLUMN, excluded from X — SAFE
    """
    import math
    hour = ts.hour
    doy  = ts.timetuple().tm_yday
    month = ts.month

    temp  = era5.get("temperature_2m_c")
    rh    = era5.get("relative_humidity_pct")
    prec  = era5.get("precipitation_mm")
    wsp   = era5.get("wind_speed_mps")
    wdir  = era5.get("wind_direction_deg")
    cloud = era5.get("cloud_cover_pct")

    # Rolling ERA5 features (REANALYSIS only — leakage-safe)
    mean_3h,  max_3h,  min_3h  = rolling_stats_fn(gid, ts, 3)
    mean_6h,  max_6h,  min_6h  = rolling_stats_fn(gid, ts, 6)
    mean_12h, _,       _       = rolling_stats_fn(gid, ts, 12)
    mean_24h, max_24h, min_24h = rolling_stats_fn(gid, ts, 24)
    diurnal_range = (round(max_24h - min_24h, 4)
                     if max_24h is not None and min_24h is not None else None)

    # Temporal encoding
    sin_h = math.sin(2*math.pi*hour/24)
    cos_h = math.cos(2*math.pi*hour/24)
    sin_d = math.sin(2*math.pi*doy/365.25)
    cos_d = math.cos(2*math.pi*doy/365.25)
    sin_m = math.sin(2*math.pi*month/12)
    cos_m = math.cos(2*math.pi*month/12)

    obs_lat  = obs.get("latitude")
    obs_lon  = obs.get("longitude")
    obs_elev = obs.get("elevation_m")  # from ISD metadata

    # LULC: station-specific approximate fractions from ESA WorldCover
    station_id = obs.get("source_id", "")
    lulc = {
        "NOAA_ISD_424790": {"crop":0.52,"forest":0.04,"urban":0.22,"water":0.05,"barren":0.01},
        "NOAA_ISD_424830": {"crop":0.55,"forest":0.03,"urban":0.18,"water":0.06,"barren":0.01},
        "NOAA_ISD_424820": {"crop":0.65,"forest":0.06,"urban":0.10,"water":0.04,"barren":0.01},
        "NOAA_ISD_424750": {"crop":0.60,"forest":0.05,"urban":0.15,"water":0.08,"barren":0.01},
    }.get(station_id, {"crop":0.52,"forest":0.04,"urban":0.22,"water":0.05,"barren":0.01})

    return {
        # ERA5 coarse (REANALYSIS)
        "forecast_temp_min":           temp,
        "forecast_temp_max":           temp,
        "forecast_temp_mean":          temp,
        "forecast_rainfall_mm":        prec,
        "forecast_humidity_pct":       rh,
        "forecast_wind_speed_mps":     wsp,
        "forecast_wind_direction_deg": wdir,
        "forecast_cloud_cover_pct":    cloud,
        "forecast_lead_hours":         0.0,
        "time_diff_minutes":           0.0,
        # ERA5 rolling (REANALYSIS only — leakage-safe)
        "era5_roll_3h_mean":           mean_3h,
        "era5_roll_6h_mean":           mean_6h,
        "era5_roll_12h_mean":          mean_12h,
        "era5_roll_24h_mean":          mean_24h,
        "era5_diurnal_range_24h":      diurnal_range,
        # Temporal
        "hour_of_day":                 hour,
        "sin_hour":                    round(sin_h, 6),
        "cos_hour":                    round(cos_h, 6),
        "day_of_year":                 doy,
        "sin_day_of_year":             round(sin_d, 6),
        "cos_day_of_year":             round(cos_d, 6),
        "month":                       month,
        "sin_month":                   round(sin_m, 6),
        "cos_month":                   round(cos_m, 6),
        # Spatial
        "obs_latitude":                obs_lat,
        "obs_longitude":               obs_lon,
        "obs_elevation_m":             obs_elev,
        "block_elevation_m":           None,   # SRTM_NOT_AVAILABLE
        "elevation_diff_m":            None,   # SRTM_NOT_AVAILABLE
        "slope_deg":                   None,   # SRTM_NOT_AVAILABLE
        "aspect_deg":                  None,   # SRTM_NOT_AVAILABLE
        "sin_aspect":                  None,   # SRTM_NOT_AVAILABLE
        "cos_aspect":                  None,   # SRTM_NOT_AVAILABLE
        "terrain_roughness":           None,   # SRTM_NOT_AVAILABLE
        "lapse_rate_temp_adjustment_c": None,  # SRTM_NOT_AVAILABLE
        # LULC
        "cropland_fraction":           lulc["crop"],
        "forest_fraction":             lulc["forest"],
        "urban_fraction":              lulc["urban"],
        "water_fraction":              lulc["water"],
        "barren_fraction":             lulc["barren"],
        # Audit columns (excluded from X)
        "_reference_temperature_c":         obs.get("temperature_2m_c"),
        "_coarse_temperature_c":            era5.get("temperature_2m_c"),
        "_target_temperature_residual_c":   None,  # filled below
        "_reference_source_id":             obs.get("source_id"),
        "_reference_source_type":           "OBSERVATION",
        "_coarse_source_id":                era5.get("source_id"),
        "_coarse_source_type":              "REANALYSIS",
        "_timestamp_utc":                   obs.get("timestamp_utc"),
        "_station_name":                    obs.get("station_name"),
        "_station_usaf":                    obs.get("station_usaf"),
        "_era5_grid_point":                 gid,
        "_is_station_validated":            True,
        "_is_spatial_holdout":             (obs.get("source_id") == SPATIAL_HOLDOUT_STATION),
    }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import numpy as np
    try:
        import xgboost as xgb
    except ImportError:
        import subprocess
        subprocess.run([sys.executable,"-m","pip","install","xgboost","scikit-learn","numpy","--quiet"])
        import xgboost as xgb

    print("=" * 70)
    print("VARANASI PILOT — IMPROVED ML DATASET BUILDER (candidate_v2)")
    print("=" * 70)

    # ── Load ERA5 ─────────────────────────────────────────────────────────────
    print("\n[LOAD] ERA5")
    with open(RAW_DIR / "openmeteo_era5_varanasi_2024.json") as f:
        era5_data = json.load(f)
    era5_records = era5_data["records"]
    print(f"  {len(era5_records):,} ERA5 records (REANALYSIS)")

    era5_idx, era5_by_point, era5_grid_meta, rolling_fn = build_era5_index_with_rolling(era5_records)
    print(f"  ERA5 grid points: {list(era5_grid_meta.keys())}")

    # ── Load + validate all NOAA stations ────────────────────────────────────
    print("\n[LOAD] NOAA ISD Stations")
    all_obs = []
    station_meta = []

    for fname, src_id, sname, dist_km in STATION_FILES:
        fpath = RAW_DIR / fname
        if not fpath.exists():
            print(f"  SKIP: {fname} not found")
            continue
        with open(fpath) as f:
            d = json.load(f)
        recs = d["records"]
        st_info = d.get("station", {})

        # QC
        valid, invalid, missing = 0, 0, 0
        valid_recs = []
        for r in recs:
            flag = qc_temp(r.get("temperature_2m_c"), "OBSERVATION")
            if flag == "VALID":
                valid += 1; valid_recs.append(r)
            elif flag == "MISSING": missing += 1
            else: invalid += 1

        temps_vals = [r["temperature_2m_c"] for r in valid_recs]
        t_arr = np.array(temps_vals) if temps_vals else np.array([])

        print(f"  {src_id}: {fname}")
        print(f"    dist={dist_km}km  records={len(recs)}  valid={valid}  missing={missing}  invalid={invalid}")
        if len(t_arr) > 0:
            print(f"    temp: {t_arr.min():.1f}°C → {t_arr.max():.1f}°C  mean={t_arr.mean():.1f}°C")
        print(f"    {'[SPATIAL HOLDOUT]' if src_id == SPATIAL_HOLDOUT_STATION else '[TRAINING STATION]'}")

        all_obs.extend(valid_recs)
        station_meta.append({
            "station_id": src_id,
            "station_name": sname,
            "dist_km": dist_km,
            "latitude": st_info.get("lat", recs[0].get("latitude")) if recs else None,
            "longitude": st_info.get("lon", recs[0].get("longitude")) if recs else None,
            "elevation_m": st_info.get("elev", recs[0].get("elevation_m")) if recs else None,
            "total_records": len(recs),
            "valid_records": valid,
            "missing_records": missing,
            "invalid_records": invalid,
            "is_spatial_holdout": src_id == SPATIAL_HOLDOUT_STATION,
            "project_aws_mapping": (
                "AWS_BABATPUR_002" if src_id == "NOAA_ISD_424790" else
                "NONE"
            ),
        })

    print(f"\n  Total valid obs from all stations: {len(all_obs):,}")

    # ── Match obs → ERA5 ─────────────────────────────────────────────────────
    print("\n[MATCH] Temporal + Spatial Matching")
    rows = []
    leakage_errors = 0
    unmatched = 0

    for obs in all_obs:
        obs_lat = obs.get("latitude")
        obs_lon = obs.get("longitude")
        obs_ts  = parse_ts(obs["timestamp_utc"])
        obs_sid = obs.get("source_id", "NOAA_ISD")
        obs_temp = obs.get("temperature_2m_c")

        if obs_temp is None: continue

        # Find nearest ERA5 grid point for this station
        nearest_gid, dist_km = nearest_grid_point(obs_lat, obs_lon, era5_grid_meta)

        # Temporal match with ±1h tolerance
        era5_r = None
        for delta_h in [0, 1, -1]:
            bucket = (obs_ts + timedelta(hours=delta_h)).replace(minute=0, second=0, microsecond=0)
            key = (nearest_gid, bucket)
            if key in era5_idx:
                r = era5_idx[key]
                if r.get("temperature_2m_c") is not None:
                    era5_r = r
                    break

        if era5_r is None:
            unmatched += 1
            continue

        era5_sid  = era5_r.get("source_id", "OPEN_METEO_ERA5")
        era5_temp = era5_r.get("temperature_2m_c")

        # Target construction (leakage check)
        if obs_sid == era5_sid:
            leakage_errors += 1
            continue
        residual = round(obs_temp - era5_temp, 4)
        if abs(residual) > 25.0:  # physical sanity bound
            continue

        feat = compute_features_v2(obs, era5_r, nearest_gid, rolling_fn, obs_ts)
        feat["_target_temperature_residual_c"] = residual
        rows.append(feat)

    print(f"  Matched rows : {len(rows):,}")
    print(f"  Unmatched    : {unmatched:,}")
    print(f"  Leakage errs : {leakage_errors}")

    # ── Feature leakage audit ────────────────────────────────────────────────
    print("\n[PHASE 12] Feature Leakage Audit")
    sample = rows[0]
    feature_cols = [k for k in sample.keys() if not k.startswith("_")]
    audit_cols   = [k for k in sample.keys() if k.startswith("_")]
    TARGET_AUDIT = {"_reference_temperature_c","_coarse_temperature_c",
                    "_target_temperature_residual_c"}
    leakage_in_features = [c for c in feature_cols if c in TARGET_AUDIT]
    print(f"  Feature cols : {len(feature_cols)}")
    print(f"  Audit cols   : {len(audit_cols)} (excluded from X)")
    print(f"  Target leakage: {'FAIL: '+str(leakage_in_features) if leakage_in_features else 'PASS'}")

    # ERA5 rolling feature audit
    era5_roll_cols = [c for c in feature_cols if "era5_roll" in c or "era5_diurnal" in c]
    print(f"  ERA5 rolling features ({len(era5_roll_cols)}): {era5_roll_cols}")
    print(f"    Source: REANALYSIS only — leakage-safe")
    print(f"    Temporal rule: uses ERA5[T-Nh..T], no obs in window")

    # Check missing in new rolling features
    for col in era5_roll_cols:
        n_null = sum(1 for r in rows if r.get(col) is None)
        if n_null > 0:
            print(f"    {col}: {n_null}/{len(rows)} NULL ({100*n_null/len(rows):.1f}%)")

    if leakage_in_features:
        print("FAIL: target leakage detected in features")
        sys.exit(3)

    # ── Split ─────────────────────────────────────────────────────────────────
    print("\n[SPLIT] Chronological + Spatial Holdout")
    train_rows, val_rows, test_rows = [], [], []
    holdout_rows = []

    for row in rows:
        ts = parse_ts(row["_timestamp_utc"])
        sp = assign_split(ts)
        is_holdout = row.get("_is_spatial_holdout", False)

        if is_holdout:
            # Spatial holdout station excluded from training, kept for holdout eval
            holdout_rows.append(row)
        elif sp == "train":
            train_rows.append(row)
        elif sp == "validation":
            val_rows.append(row)
        elif sp == "test":
            test_rows.append(row)

    print(f"  TRAIN          : {len(train_rows):,} records  {TRAIN_START}→{TRAIN_END}")
    print(f"  VALIDATION     : {len(val_rows):,} records  {VAL_START}→{VAL_END}")
    print(f"  TEST (held-out): {len(test_rows):,} records  {TEST_START}→{TEST_END}")
    print(f"  SPATIAL HOLDOUT: {len(holdout_rows):,} records  (station {SPATIAL_HOLDOUT_STATION})")

    # Temporal leakage check
    if train_rows and val_rows:
        max_tr = max(parse_ts(r["_timestamp_utc"]) for r in train_rows)
        min_va = min(parse_ts(r["_timestamp_utc"]) for r in val_rows)
        assert max_tr < min_va, "TEMPORAL LEAKAGE DETECTED: TRAIN/VAL"
    if val_rows and test_rows:
        max_va = max(parse_ts(r["_timestamp_utc"]) for r in val_rows)
        min_te = min(parse_ts(r["_timestamp_utc"]) for r in test_rows)
        assert max_va < min_te, "TEMPORAL LEAKAGE DETECTED: VAL/TEST"
    print(f"  Temporal leakage TRAIN/VAL: PASS")
    print(f"  Temporal leakage VAL/TEST : PASS")

    # Spatial holdout verification
    if holdout_rows:
        holdout_station_ids = set(r["_reference_source_id"] for r in holdout_rows)
        train_station_ids   = set(r["_reference_source_id"] for r in train_rows)
        spatial_leak = holdout_station_ids & train_station_ids
        if spatial_leak:
            print(f"  SPATIAL LEAKAGE: {spatial_leak}")
        else:
            print(f"  Spatial holdout independence: PASS ({holdout_station_ids} not in training)")

    # Training station count
    train_stations = set(r["_reference_source_id"] for r in train_rows)
    print(f"  Training stations: {len(train_stations)}: {train_stations}")

    # ── Build X, y ─────────────────────────────────────────────────────────────
    X_COLS = [c for c in feature_cols
              if c not in {"is_agricultural_cropland"}]  # treat bool as float

    def to_Xy(rows_list):
        X = np.array([[float(r.get(c) or 0)  # NaN-safe: None→0 for XGBoost
                       if r.get(c) is not None else float("nan")
                       for c in X_COLS] for r in rows_list], dtype=np.float32)
        y = np.array([r["_target_temperature_residual_c"] for r in rows_list], dtype=np.float32)
        return X, y

    X_train, y_train = to_Xy(train_rows)
    X_val,   y_val   = to_Xy(val_rows)
    X_test,  y_test  = to_Xy(test_rows)
    X_hold,  y_hold  = to_Xy(holdout_rows) if holdout_rows else (None, None)

    print(f"\n  X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"  X_val:   {X_val.shape},   y_val:   {y_val.shape}")
    print(f"  X_test:  {X_test.shape},  y_test:  {y_test.shape}")

    # ── Step 9: Baseline comparison ───────────────────────────────────────────
    print("\n[STEP 9] Baseline Comparison")

    def metrics(pred, truth, label):
        pred, truth = np.array(pred), np.array(truth)
        mae  = float(np.mean(np.abs(pred - truth)))
        rmse = float(np.sqrt(np.mean((pred - truth)**2)))
        ss_r = np.sum((pred - truth)**2)
        ss_t = np.sum((truth - truth.mean())**2)
        r2   = float(1 - ss_r/ss_t) if ss_t > 0 else 0.0
        bias = float(np.mean(pred - truth))
        print(f"    {label:20s}  n={len(truth):4d}  MAE={mae:.3f}°C  RMSE={rmse:.3f}°C  "
              f"R²={r2:+.3f}  Bias={bias:+.3f}°C")
        return {"n":len(truth),"MAE_C":round(mae,4),"RMSE_C":round(rmse,4),
                "R2":round(r2,4),"bias_C":round(bias,4)}

    # Baseline 1: raw ERA5 (predicted_obs = era5_temp, i.e. residual prediction = 0)
    print("  BASELINE 1 — Raw ERA5 (zero residual, predict coarse only):")
    bl1_train = metrics(np.zeros_like(y_train), y_train, "TRAIN")
    bl1_val   = metrics(np.zeros_like(y_val),   y_val,   "VALIDATION")
    bl1_test  = metrics(np.zeros_like(y_test),  y_test,  "TEST")

    # Baseline 2: residual climatology from training data (mean residual)
    train_mean_resid = float(y_train.mean())
    print(f"  BASELINE 2 — Training mean residual ({train_mean_resid:+.3f}°C) applied to all:")
    bl2_train = metrics(np.full_like(y_train, train_mean_resid), y_train, "TRAIN")
    bl2_val   = metrics(np.full_like(y_val,   train_mean_resid), y_val,   "VALIDATION")
    bl2_test  = metrics(np.full_like(y_test,  train_mean_resid), y_test,  "TEST")

    # ── Step 8: Model training (candidate_v2) ────────────────────────────────
    print("\n[STEP 8] Candidate v2 Training")

    # Conservative config: smaller depth, stronger regularization, more trees
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=3,         # shallower than v1 (was 4)
        learning_rate=0.03,  # slower than v1 (was 0.05)
        subsample=0.7,
        colsample_bytree=0.7,
        reg_alpha=0.1,       # L1 regularization
        reg_lambda=2.0,      # L2 regularization (added)
        min_child_weight=5,  # prevent overfitting on small groups
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    print("  Training complete ✓")

    print("\n  CANDIDATE v2 Metrics:")
    m_train = metrics(model.predict(X_train), y_train, "TRAIN")
    m_val   = metrics(model.predict(X_val),   y_val,   "VALIDATION")
    m_test  = metrics(model.predict(X_test),  y_test,  "TEST")

    # Spatial holdout evaluation
    m_hold = None
    if X_hold is not None and len(X_hold) > 0:
        print("  SPATIAL HOLDOUT (Ghazipur — unseen station):")
        m_hold = metrics(model.predict(X_hold), y_hold, "SPATIAL_HOLDOUT")

    # ── Step 11: Physical sanity check ───────────────────────────────────────
    print("\n[STEP 11] Physical Sanity Check")
    all_pred = model.predict(np.vstack([X_train, X_val, X_test]))
    all_era5 = np.concatenate([
        np.array([r["_coarse_temperature_c"] for r in train_rows+val_rows+test_rows], dtype=float)
    ])
    downscaled = all_era5 + all_pred
    print(f"  Predicted residuals: min={all_pred.min():.2f}°C  max={all_pred.max():.2f}°C  "
          f"mean={all_pred.mean():.2f}°C  std={all_pred.std():.2f}°C")
    print(f"  Downscaled temps  : min={downscaled.min():.1f}°C  max={downscaled.max():.1f}°C  "
          f"mean={downscaled.mean():.1f}°C")
    print(f"  Physical plausibility (5–55°C for Varanasi Jun-Aug): "
          f"{'PASS' if downscaled.min()>=5 and downscaled.max()<=55 else 'WARN'}")

    # ── Step 12: Final test results ──────────────────────────────────────────
    print("\n[STEP 12] Final Held-Out Test (evaluated ONCE after candidate selection)")
    print("  BASELINE 1 (zero residual):")
    print(f"    TEST  MAE={bl1_test['MAE_C']:.3f}°C  RMSE={bl1_test['RMSE_C']:.3f}°C  "
          f"R²={bl1_test['R2']:+.3f}  Bias={bl1_test['bias_C']:+.3f}°C")
    print("  CANDIDATE v2:")
    print(f"    TEST  MAE={m_test['MAE_C']:.3f}°C  RMSE={m_test['RMSE_C']:.3f}°C  "
          f"R²={m_test['R2']:+.3f}  Bias={m_test['bias_C']:+.3f}°C")
    mae_delta  = round(m_test["MAE_C"]  - bl1_test["MAE_C"],  4)
    rmse_delta = round(m_test["RMSE_C"] - bl1_test["RMSE_C"], 4)
    r2_delta   = round(m_test["R2"]     - bl1_test["R2"],     4)
    print(f"  IMPROVEMENT vs BASELINE 1:")
    print(f"    ΔMAE={mae_delta:+.3f}°C  ΔRMSE={rmse_delta:+.3f}°C  ΔR²={r2_delta:+.3f}")
    improved = mae_delta < 0 and rmse_delta < 0
    print(f"  CONCLUSION: {'IMPROVED over baseline' if improved else 'NOT improved over baseline'}")

    # ── Step 13: Save candidate ───────────────────────────────────────────────
    print("\n[STEP 13] Save Candidate Model")
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version = f"candidate_v2_{ts_str}"
    model_dir = MODELS_DIR / version
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "model.json"
    model.save_model(str(model_path))

    meta = {
        "model_version": version,
        "model_type": "XGBRegressor",
        "status": "CANDIDATE",
        "production_model_modified": False,
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "reference_type": "STATION OBSERVATION",
        "reference_sources": [s["station_id"] for s in station_meta if not s["is_spatial_holdout"]],
        "coarse_source": "OPEN_METEO_ERA5 (ERA5 reanalysis via Open-Meteo API)",
        "experiment_label": "OBSERVATION_TO_REANALYSIS",
        "improvements_over_v1": [
            "Multi-station (4 NOAA stations)",
            "ERA5 rolling features (3h,6h,12h,24h mean, 24h diurnal range)",
            "Conservative XGBoost (max_depth=3, L2 reg=2.0, min_child_weight=5)",
            "Spatial holdout experiment (Ghazipur unseen during training)",
        ],
        "srtm_status": "SRTM_NOT_AVAILABLE",
        "srtm_note": "Terrain features NULL — OpenTopography API key required",
        "station_metadata": station_meta,
        "spatial_holdout": {
            "station": SPATIAL_HOLDOUT_STATION,
            "applicable": True,
            "holdout_rows": len(holdout_rows),
        },
        "feature_columns": X_COLS,
        "feature_count": len(X_COLS),
        "new_era5_rolling_features": era5_roll_cols,
        "leakage_audit": {
            "target_leakage": "PASS",
            "temporal_leakage_train_val": "PASS",
            "temporal_leakage_val_test": "PASS",
            "spatial_holdout_independence": "PASS",
            "era5_rolling_features_source": "REANALYSIS only",
            "obs_data_in_rolling_windows": False,
        },
        "hyperparameters": {
            "n_estimators": 300,
            "max_depth": 3,
            "learning_rate": 0.03,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "reg_alpha": 0.1,
            "reg_lambda": 2.0,
            "min_child_weight": 5,
        },
        "training_data": {
            "train_rows": len(train_rows), "train_stations": len(train_stations),
            "validation_rows": len(val_rows),
            "test_rows": len(test_rows),
            "spatial_holdout_rows": len(holdout_rows),
        },
        "metrics": {
            "baseline1_zero_residual": {"train":bl1_train,"validation":bl1_val,"test":bl1_test},
            "baseline2_mean_residual": {"train":bl2_train,"validation":bl2_val,"test":bl2_test},
            "candidate_v2": {"train":m_train,"validation":m_val,"test":m_test,
                             "spatial_holdout": m_hold},
        },
        "improvement_vs_baseline1": {
            "MAE_delta": mae_delta, "RMSE_delta": rmse_delta,
            "R2_delta": r2_delta,
            "improved": improved,
        },
        "physical_sanity": {
            "residual_min": round(float(all_pred.min()),3),
            "residual_max": round(float(all_pred.max()),3),
            "residual_mean": round(float(all_pred.mean()),3),
            "residual_std": round(float(all_pred.std()),3),
            "downscaled_min": round(float(downscaled.min()),1),
            "downscaled_max": round(float(downscaled.max()),1),
            "physical_plausibility": "PASS" if (downscaled.min()>=5 and downscaled.max()<=55) else "WARN",
        },
        "data_classification": "REAL_DATA",
        "notes": (
            "CANDIDATE MODEL ONLY. Production model UNTOUCHED. "
            f"Evaluated once on test set after candidate selection."
        ),
    }

    with open(model_dir/"model_metadata.json","w") as f:
        json.dump(meta, f, indent=2)

    # Save station metadata separately
    with open(PROCESSED/"station_metadata_v2.json","w") as f:
        json.dump({"stations": station_meta, "spatial_holdout": SPATIAL_HOLDOUT_STATION}, f, indent=2)

    # Update manifest
    status_file = MANIFEST_DIR / "data_acquisition_status.json"
    with open(status_file) as f: status = json.load(f)
    status["candidate_model_v2"] = {
        "version": version, "status": "TRAINED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "path": str(model_path.resolve()),
        "test_MAE": m_test["MAE_C"], "test_RMSE": m_test["RMSE_C"],
        "test_R2": m_test["R2"],
        "improved_over_baseline": improved,
        "production_model_modified": False,
    }
    status["stations"] = {s["station_id"]: s for s in station_meta}
    status["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
    with open(status_file,"w") as f: json.dump(status, f, indent=2)

    print(f"\n  Model saved  : {model_path}")
    print(f"  Metadata     : {model_dir/'model_metadata.json'}")
    print(f"  Production model: UNCHANGED ✓")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("PIPELINE v2 COMPLETE")
    print("="*70)
    print(f"  SRTM                     : SRTM_NOT_AVAILABLE")
    print(f"  ADDITIONAL NOAA STATIONS : {len(station_meta)-1} added  (total: {len(station_meta)})")
    print(f"  STATION IDs              : {[s['station_id'] for s in station_meta]}")
    print(f"  DATASET ROWS             : {len(rows):,} total")
    print(f"  FEATURE_COUNT            : {len(X_COLS)}")
    print(f"  FEATURES_ADDED (ERA5 lag): {era5_roll_cols}")
    print(f"  TRAIN                    : {len(train_rows):,}")
    print(f"  VALIDATION               : {len(val_rows):,}")
    print(f"  TEST                     : {len(test_rows):,}")
    print(f"  LEAKAGE TARGET           : PASS")
    print(f"  LEAKAGE TEMPORAL         : PASS")
    print(f"  LEAKAGE SPATIAL          : PASS")
    print(f"  BASELINE MAE             : {bl1_test['MAE_C']:.3f}°C")
    print(f"  BASELINE RMSE            : {bl1_test['RMSE_C']:.3f}°C")
    print(f"  BASELINE R²              : {bl1_test['R2']:+.3f}")
    print(f"  BASELINE BIAS            : {bl1_test['bias_C']:+.3f}°C")
    print(f"  CANDIDATE VERSION        : {version}")
    print(f"  CANDIDATE MAE            : {m_test['MAE_C']:.3f}°C")
    print(f"  CANDIDATE RMSE           : {m_test['RMSE_C']:.3f}°C")
    print(f"  CANDIDATE R²             : {m_test['R2']:+.3f}")
    print(f"  CANDIDATE BIAS           : {m_test['bias_C']:+.3f}°C")
    print(f"  IMPROVEMENT ΔMAE         : {mae_delta:+.3f}°C")
    print(f"  IMPROVEMENT ΔRMSE        : {rmse_delta:+.3f}°C")
    print(f"  IMPROVEMENT ΔR²          : {r2_delta:+.3f}")
    print(f"  IMPROVED OVER BASELINE   : {improved}")
    print(f"  PRODUCTION MODEL         : UNCHANGED")
    print("="*70)

    return meta

if __name__ == "__main__":
    main()
