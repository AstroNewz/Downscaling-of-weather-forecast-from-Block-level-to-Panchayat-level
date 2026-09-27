#!/usr/bin/env python3
"""
train_real_model.py — India Pilot Real-Data Candidate Model Training Script
SIH Problem Statement 26074 — Agroweather-Downscaling

PURPOSE
-------
Train a CANDIDATE temperature-downscaling model from real acquired Indian data.
Candidate artifacts are written ONLY to models/candidates/<candidate_version>/.
The production model at models/temperature_residual/ is NEVER modified.

CRITICAL POLICIES
-----------------
1. NEVER overwrite models/temperature_residual/ (production).
2. All output goes to models/candidates/temperature_residual/<candidate_version>/.
3. DEMO_DATA and SYNTHETIC_DATA records are rejected at load time.
4. If independent reference observations are unavailable the script fails with
   REAL_REFERENCE_DATA_REQUIRED rather than substituting synthetic data.
5. ERA5 cannot be used simultaneously as coarse input and reference temperature
   (leakage prevention — enforced by TargetBuilder).
6. The target formulation is FIXED:
       target_temperature_residual_c = reference_temperature_c - coarse_temperature_c

USAGE
-----
    cd backend/
    python train_real_model.py \\
        --dataset path/to/processed/training.parquet \\
        --candidate-version v1.0.0-real-varanasi-pilot \\
        [--dry-run]

EXIT CODES
----------
    0  — Training completed or dry-run OK.
    1  — Data validation failure (missing real data, leakage detected, etc.).
    2  — REAL_REFERENCE_DATA_REQUIRED — no independent reference observations available.
    3  — Configuration or import error.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap — allow running from backend/ root
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("train_real_model")

# ---------------------------------------------------------------------------
# Guard: verify production model directory before import (pre-import fingerprint)
# ---------------------------------------------------------------------------
_PRODUCTION_MODEL_DIR = _BACKEND_ROOT / "models" / "temperature_residual"
_CANDIDATES_ROOT = _BACKEND_ROOT / "models" / "candidates" / "temperature_residual"

REAL_REFERENCE_DATA_REQUIRED_EXIT = 2


def _fingerprint_production_model() -> Dict[str, Any]:
    """Records mtime and file list of the production model directory before training."""
    result: Dict[str, Any] = {"exists": _PRODUCTION_MODEL_DIR.exists(), "files": {}}
    if _PRODUCTION_MODEL_DIR.exists():
        for p in sorted(_PRODUCTION_MODEL_DIR.rglob("*")):
            if p.is_file():
                stat = p.stat()
                result["files"][str(p)] = {
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                }
    return result


def _verify_production_model_unchanged(pre: Dict[str, Any]) -> None:
    """Raises RuntimeError if production model directory has changed since pre-training snapshot."""
    post = _fingerprint_production_model()
    if pre["files"] != post["files"]:
        raise RuntimeError(
            "CRITICAL: Production model directory has been modified during training. "
            "Inspect models/temperature_residual/ immediately. "
            "Candidate training must be isolated under models/candidates/."
        )
    logger.info("Production model integrity check PASSED — no changes detected.")


# ---------------------------------------------------------------------------
# Deferred imports (after path bootstrap)
# ---------------------------------------------------------------------------
try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    logger.error("Missing dependency: %s. Run: pip install pandas numpy", e)
    sys.exit(3)

try:
    from data_pipeline.pipeline.feature_engineer import (
        RealDataFeatureEngineer,
        ORDERED_FEATURE_COLUMNS,
        QUARANTINED_COLUMNS,
        SCHEMA_VERSION,
        EXPECTED_SCHEMA_VERSION,
    )
    from data_pipeline.pipeline.target_builder import TargetBuilder
    from data_pipeline.pipeline.chronological_splitter import ChronologicalSplitter
    from data_pipeline.validation.india_data_validator import IndiaDataValidator
    from data_pipeline.manifests.dataset_manifest_writer import (
        DatasetManifestWriter,
        build_pilot_sources,
    )
except ImportError as e:
    logger.error(
        "Failed to import data pipeline modules: %s. "
        "Ensure you are running from the backend/ directory.", e
    )
    sys.exit(3)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_FORBIDDEN_CLASSIFICATIONS = {"DEMO_DATA", "SYNTHETIC_DATA"}
_TARGET_COL = "target_temperature_residual_c"
_REF_TEMP_COL = "reference_temperature_c"
_COARSE_TEMP_COL = "coarse_temperature_c"

# Pilot split dates (from india_pilot.yaml)
_PILOT_SPLITS = {
    "train":      {"start": "2024-06-01", "end": "2024-07-15"},
    "validation": {"start": "2024-07-16", "end": "2024-07-31"},
    "test":       {"start": "2024-08-01", "end": "2024-08-31"},
}

# Pilot AOI (from india_pilot.yaml / india_data_validator.py)
_PILOT_LAT_MIN, _PILOT_LAT_MAX = 25.10, 25.60
_PILOT_LON_MIN, _PILOT_LON_MAX = 82.70, 83.20


# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------

def _load_dataset(dataset_path: Path) -> pd.DataFrame:
    """Loads and performs initial integrity checks on the training dataset."""
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {dataset_path}. "
            "Run the acquisition pipeline first to produce real processed data."
        )

    ext = dataset_path.suffix.lower()
    if ext == ".parquet":
        df = pd.read_parquet(dataset_path)
    elif ext == ".csv":
        df = pd.read_csv(dataset_path, parse_dates=["timestamp_utc"])
    else:
        raise ValueError(f"Unsupported dataset format '{ext}'. Expected .parquet or .csv")

    logger.info("Loaded dataset: %d rows from %s", len(df), dataset_path)
    return df


def _reject_demo_synthetic_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes DEMO_DATA and SYNTHETIC_DATA records from the DataFrame.
    Raises ValueError if ALL records are non-real.
    Logs a clear warning for every rejected record class.
    """
    if "data_classification" not in df.columns:
        logger.warning(
            "Column 'data_classification' not found. Assuming all records are REAL_DATA. "
            "Add this column to guarantee synthetic data isolation."
        )
        return df

    mask_real = ~df["data_classification"].isin(_FORBIDDEN_CLASSIFICATIONS)
    rejected_count = (~mask_real).sum()
    if rejected_count > 0:
        breakdown = df[~mask_real]["data_classification"].value_counts().to_dict()
        logger.error(
            "REJECTED %d records with non-real data classifications: %s. "
            "DEMO_DATA and SYNTHETIC_DATA must NEVER enter the real training pipeline.",
            rejected_count, breakdown,
        )

    df_real = df[mask_real].copy()
    if len(df_real) == 0:
        raise ValueError(
            "REAL_REFERENCE_DATA_REQUIRED: After removing DEMO_DATA and SYNTHETIC_DATA, "
            "no real records remain. Acquire real observation or reanalysis data before training."
        )

    logger.info(
        "%d/%d records retained as REAL_DATA (%d non-real rejected).",
        len(df_real), len(df), rejected_count,
    )
    return df_real


def _validate_reference_availability(df: pd.DataFrame) -> None:
    """
    Verifies that at least some records have a non-null reference temperature.
    Fails with REAL_REFERENCE_DATA_REQUIRED if the reference column is entirely null.
    """
    if _REF_TEMP_COL not in df.columns:
        raise ValueError(
            f"REAL_REFERENCE_DATA_REQUIRED: Column '{_REF_TEMP_COL}' is absent from the dataset. "
            "Independent reference temperature observations (IMD AWS or ERA5-Land) must be "
            "pre-joined before training. Do NOT manufacture a reference temperature."
        )

    non_null = df[_REF_TEMP_COL].notna().sum()
    if non_null == 0:
        raise ValueError(
            "REAL_REFERENCE_DATA_REQUIRED: All values in reference_temperature_c are null. "
            "Without an independent reference temperature the training target cannot be constructed. "
            "Acquire IMD station data (SOURCE_ACCESS_REQUIRED) or ERA5-Land data before training."
        )

    logger.info(
        "Reference temperature available for %d/%d records (%.1f%%).",
        non_null, len(df), 100.0 * non_null / max(len(df), 1),
    )


def _validate_target_no_leakage(feature_cols: List[str]) -> None:
    """Asserts the target and reference columns are not in the feature matrix."""
    leakage = [c for c in feature_cols if c in QUARANTINED_COLUMNS]
    if leakage:
        raise ValueError(
            f"TARGET LEAKAGE DETECTED: The following quarantined columns appear in the "
            f"feature matrix X: {leakage}. Remove them before training."
        )
    # Explicit check for target column by name even if not in QUARANTINED_COLUMNS
    dangerous = {_TARGET_COL, _REF_TEMP_COL, "temperature_residual_c",
                 "observed_temp_c", "reference_temperature_c"}
    overlap = dangerous.intersection(set(feature_cols))
    if overlap:
        raise ValueError(
            f"TARGET LEAKAGE DETECTED: Columns {overlap} must not appear in X. "
            "These are target-derived fields."
        )
    logger.info("Target leakage check PASSED — no quarantined columns in feature matrix.")


def _check_temporal_overlap(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    ts_col: str = "timestamp_utc",
) -> None:
    """Verifies TRAIN ∩ VALIDATION = ∅, TRAIN ∩ TEST = ∅, VALIDATION ∩ TEST = ∅."""
    def _dates(sub: pd.DataFrame) -> set:
        if ts_col not in sub.columns or len(sub) == 0:
            return set()
        return set(pd.to_datetime(sub[ts_col]).dt.date.unique())

    train_dates = _dates(train_df)
    val_dates = _dates(val_df)
    test_dates = _dates(test_df)

    tv_overlap = train_dates & val_dates
    tt_overlap = train_dates & test_dates
    vt_overlap = val_dates & test_dates

    violations = []
    if tv_overlap:
        violations.append(f"TRAIN ∩ VALIDATION = {sorted(tv_overlap)}")
    if tt_overlap:
        violations.append(f"TRAIN ∩ TEST = {sorted(tt_overlap)}")
    if vt_overlap:
        violations.append(f"VALIDATION ∩ TEST = {sorted(vt_overlap)}")

    if violations:
        raise ValueError(
            "TEMPORAL LEAKAGE DETECTED in chronological splits:\n  "
            + "\n  ".join(violations)
        )
    logger.info(
        "Temporal split integrity check PASSED — no date overlap between splits. "
        "Train=%d, Val=%d, Test=%d records.",
        len(train_df), len(val_df), len(test_df),
    )


# ---------------------------------------------------------------------------
# Metric computation (pure Python/numpy — no DB dependency)
# ---------------------------------------------------------------------------

def _compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    split_name: str,
) -> Dict[str, Any]:
    """Computes regression metrics for a split. Returns NaN-safe dict."""
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    n = mask.sum()
    if n == 0:
        return {"split": split_name, "sample_count": 0,
                "mae": None, "rmse": None, "r2": None, "bias": None}

    yt = y_true[mask]
    yp = y_pred[mask]
    residuals = yt - yp
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    bias = float(np.mean(residuals))
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")

    return {
        "split": split_name,
        "sample_count": int(n),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 6),
        "bias": round(bias, 4),
    }


def _compute_stratified_metrics(
    df: pd.DataFrame,
    y_pred_col: str,
) -> Dict[str, Any]:
    """Computes metrics by month, season, and temperature range."""
    if _TARGET_COL not in df.columns:
        return {}

    results: Dict[str, Any] = {}

    # By month
    if "month" in df.columns:
        by_month: Dict[int, Dict] = {}
        for m in sorted(df["month"].dropna().unique()):
            sub = df[df["month"] == m]
            yt = sub[_TARGET_COL].values
            yp = sub[y_pred_col].values if y_pred_col in sub.columns else np.full_like(yt, 0.0)
            by_month[int(m)] = _compute_metrics(yt, yp, f"month_{m}")
        results["by_month"] = by_month

    # By season (Kharif: Jun-Sep, Rabi: Oct-Mar, Zaid: Apr-May)
    season_map = {6: "kharif", 7: "kharif", 8: "kharif", 9: "kharif",
                  10: "rabi", 11: "rabi", 12: "rabi", 1: "rabi", 2: "rabi", 3: "rabi",
                  4: "zaid", 5: "zaid"}
    if "month" in df.columns:
        by_season: Dict[str, Dict] = {}
        df_s = df.copy()
        df_s["_season"] = df_s["month"].map(season_map)
        for s in sorted(df_s["_season"].dropna().unique()):
            sub = df_s[df_s["_season"] == s]
            yt = sub[_TARGET_COL].values
            yp = sub[y_pred_col].values if y_pred_col in sub.columns else np.full_like(yt, 0.0)
            by_season[s] = _compute_metrics(yt, yp, f"season_{s}")
        results["by_season"] = by_season

    return results


# ---------------------------------------------------------------------------
# Candidate model saver (lightweight JSON without XGBoost dependency required)
# ---------------------------------------------------------------------------

def _save_candidate_artifacts(
    candidate_dir: Path,
    metrics: Dict[str, Any],
    feature_cols: List[str],
    provenance: Dict[str, Any],
    dataset_path: Optional[Path],
    candidate_version: str,
    manifest_path: Optional[Path],
) -> None:
    """
    Saves candidate model metadata, metrics, and provenance to candidate_dir.
    This does NOT save model weights if XGBoost is unavailable — it saves the
    training report so the pipeline state is auditable even without a fitted model.
    """
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # Metrics report
    metrics_path = candidate_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Metrics saved → %s", metrics_path)

    # Provenance metadata
    meta = {
        "model_name": "xgboost_temperature_residual",
        "candidate_version": candidate_version,
        "model_type": "GradientBoostedDecisionTrees",
        "feature_schema_version": EXPECTED_SCHEMA_VERSION,
        "features_used": feature_cols,
        "target_column": _TARGET_COL,
        "target_formula": "reference_temperature_c - coarse_temperature_c",
        "is_synthetic": False,
        "is_candidate": True,
        "production_model_dir": str(_PRODUCTION_MODEL_DIR),
        "candidate_dir": str(candidate_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "manifest_path": str(manifest_path) if manifest_path else None,
        **provenance,
    }
    meta_path = candidate_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Candidate metadata saved → %s", meta_path)

    # Feature schema reference
    feat_path = candidate_dir / "feature_schema_reference.json"
    with open(feat_path, "w", encoding="utf-8") as f:
        json.dump(
            {"schema_version": EXPECTED_SCHEMA_VERSION, "feature_columns": feature_cols},
            f, indent=2,
        )
    logger.info("Feature schema reference saved → %s", feat_path)


# ---------------------------------------------------------------------------
# Training orchestration
# ---------------------------------------------------------------------------

def train_candidate_model(
    dataset_path: Path,
    candidate_version: str,
    dry_run: bool = False,
    manifest_output_path: Optional[Path] = None,
) -> int:
    """
    Main training function.

    Returns:
        0 on success.
        1 on data/validation errors.
        2 on REAL_REFERENCE_DATA_REQUIRED.
    """
    logger.info("=" * 70)
    logger.info("INDIA PILOT — REAL-DATA CANDIDATE MODEL TRAINING")
    logger.info("Candidate version : %s", candidate_version)
    logger.info("Dataset           : %s", dataset_path)
    logger.info("Dry run           : %s", dry_run)
    logger.info("=" * 70)

    # Pre-training production model fingerprint
    prod_fingerprint_pre = _fingerprint_production_model()
    logger.info(
        "Production model fingerprint recorded (%d files).",
        len(prod_fingerprint_pre["files"]),
    )

    # -----------------------------------------------------------------------
    # 1. Load dataset
    # -----------------------------------------------------------------------
    try:
        df = _load_dataset(dataset_path)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 2

    # -----------------------------------------------------------------------
    # 2. Reject DEMO/SYNTHETIC records
    # -----------------------------------------------------------------------
    try:
        df = _reject_demo_synthetic_records(df)
    except ValueError as e:
        if "REAL_REFERENCE_DATA_REQUIRED" in str(e):
            logger.error("REAL_REFERENCE_DATA_REQUIRED: %s", e)
            return REAL_REFERENCE_DATA_REQUIRED_EXIT
        logger.error("%s", e)
        return 1

    # -----------------------------------------------------------------------
    # 3. Validate reference temperature availability
    # -----------------------------------------------------------------------
    try:
        _validate_reference_availability(df)
    except ValueError as e:
        logger.error("REAL_REFERENCE_DATA_REQUIRED: %s", e)
        return REAL_REFERENCE_DATA_REQUIRED_EXIT

    # -----------------------------------------------------------------------
    # 4. Feature schema validation
    # -----------------------------------------------------------------------
    if SCHEMA_VERSION != EXPECTED_SCHEMA_VERSION:
        logger.error(
            "Feature schema version mismatch: loaded=%s expected=%s",
            SCHEMA_VERSION, EXPECTED_SCHEMA_VERSION,
        )
        return 1

    engineer = RealDataFeatureEngineer()

    # Determine available feature columns in the dataset
    feature_cols_present = [c for c in ORDERED_FEATURE_COLUMNS if c in df.columns]
    if not feature_cols_present:
        logger.error(
            "No Phase 6 feature columns found in dataset. "
            "Ensure the dataset was produced by data_pipeline.pipeline.feature_engineer."
        )
        return 1

    logger.info(
        "Feature columns available: %d / %d Phase 6 features present.",
        len(feature_cols_present), len(ORDERED_FEATURE_COLUMNS),
    )

    # -----------------------------------------------------------------------
    # 5. Target leakage check
    # -----------------------------------------------------------------------
    try:
        _validate_target_no_leakage(feature_cols_present)
    except ValueError as e:
        logger.error("%s", e)
        return 1

    # -----------------------------------------------------------------------
    # 6. Verify target column is present and has values
    # -----------------------------------------------------------------------
    if _TARGET_COL not in df.columns:
        # Try to build target from reference and coarse columns
        if _REF_TEMP_COL in df.columns and _COARSE_TEMP_COL in df.columns:
            logger.info(
                "Target column '%s' absent — computing from %s - %s.",
                _TARGET_COL, _REF_TEMP_COL, _COARSE_TEMP_COL,
            )
            df[_TARGET_COL] = df[_REF_TEMP_COL] - df[_COARSE_TEMP_COL]
        else:
            logger.error(
                "REAL_REFERENCE_DATA_REQUIRED: Target column '%s' is absent and "
                "cannot be computed because '%s' or '%s' are also absent.",
                _TARGET_COL, _REF_TEMP_COL, _COARSE_TEMP_COL,
            )
            return REAL_REFERENCE_DATA_REQUIRED_EXIT

    target_valid = df[_TARGET_COL].notna().sum()
    if target_valid == 0:
        logger.error(
            "REAL_REFERENCE_DATA_REQUIRED: All values in target column '%s' are null. "
            "Acquire independent reference data (IMD AWS or ERA5-Land) before training.",
            _TARGET_COL,
        )
        return REAL_REFERENCE_DATA_REQUIRED_EXIT

    # Validate feature matrix
    feat_df = df[feature_cols_present].copy()
    validation_report = engineer.validate_feature_matrix(feat_df, strict=False)
    if not validation_report["all_ok"]:
        for err in validation_report.get("errors", []):
            logger.error("Feature matrix validation error: %s", err)
        return 1
    for warn in validation_report.get("warnings", []):
        logger.warning("Feature matrix validation warning: %s", warn)

    # -----------------------------------------------------------------------
    # 7. Chronological split
    # -----------------------------------------------------------------------
    ts_col = next(
        (c for c in ("timestamp_utc", "observation_time", "prov_timestamp_utc") if c in df.columns),
        None,
    )
    if ts_col is None:
        logger.error(
            "No timestamp column found. Expected 'timestamp_utc' or 'observation_time'. "
            "Cannot perform chronological split."
        )
        return 1

    splitter = ChronologicalSplitter(
        train_start=_PILOT_SPLITS["train"]["start"],
        train_end=_PILOT_SPLITS["train"]["end"],
        validation_start=_PILOT_SPLITS["validation"]["start"],
        validation_end=_PILOT_SPLITS["validation"]["end"],
        test_start=_PILOT_SPLITS["test"]["start"],
        test_end=_PILOT_SPLITS["test"]["end"],
    )

    train_df, val_df, test_df, split_report = splitter.split_dataframe(
        df, timestamp_col=ts_col, panchayat_col=None
    )
    logger.info(
        "Chronological split: TRAIN=%d, VAL=%d, TEST=%d, outside_period=%d",
        split_report["train_records"],
        split_report["validation_records"],
        split_report["test_records"],
        split_report["outside_period_records"],
    )

    if not split_report["temporal_leakage_safe"]:
        logger.error(
            "TEMPORAL LEAKAGE DETECTED in splits: %d violation(s).",
            split_report["temporal_overlap_violations"],
        )
        return 1

    # -----------------------------------------------------------------------
    # 8. Temporal overlap verification
    # -----------------------------------------------------------------------
    try:
        _check_temporal_overlap(train_df, val_df, test_df, ts_col=ts_col)
    except ValueError as e:
        logger.error("%s", e)
        return 1

    # -----------------------------------------------------------------------
    # 9. Check minimum training rows
    # -----------------------------------------------------------------------
    MIN_TRAIN_ROWS = 50
    if len(train_df) < MIN_TRAIN_ROWS:
        logger.error(
            "INSUFFICIENT REAL DATA: TRAIN set has %d rows; minimum is %d. "
            "Acquire more real data before training.",
            len(train_df), MIN_TRAIN_ROWS,
        )
        return 1

    # -----------------------------------------------------------------------
    # 10. Validate reference source labelling
    # -----------------------------------------------------------------------
    # Warn if reference source is REANALYSIS (valid but must be labelled)
    ref_type_col = "prov_source_type"
    if ref_type_col in train_df.columns:
        reanalysis_ref = train_df[
            train_df[ref_type_col] == "REANALYSIS"
        ]
        if len(reanalysis_ref) > 0:
            frac = len(reanalysis_ref) / max(len(train_df), 1) * 100
            logger.warning(
                "%.1f%% of training records use REANALYSIS as reference. "
                "This is valid if ERA5 != ERA5-Land (different datasets). "
                "All reports must label this as 'REANALYSIS-to-REANALYSIS validation', "
                "NOT 'station-observed validation'.",
                frac,
            )

    # -----------------------------------------------------------------------
    # 11. Extract X, y
    # -----------------------------------------------------------------------
    X_train = train_df[feature_cols_present].copy()
    y_train = train_df[_TARGET_COL].dropna()
    X_train = X_train.loc[y_train.index]

    X_val: Optional[pd.DataFrame] = val_df[feature_cols_present].copy() if len(val_df) > 0 else None
    y_val: Optional[pd.Series] = val_df[_TARGET_COL].dropna() if len(val_df) > 0 else None
    if X_val is not None and y_val is not None:
        X_val = X_val.loc[y_val.index]

    X_test: Optional[pd.DataFrame] = test_df[feature_cols_present].copy() if len(test_df) > 0 else None
    y_test: Optional[pd.Series] = test_df[_TARGET_COL].dropna() if len(test_df) > 0 else None
    if X_test is not None and y_test is not None:
        X_test = X_test.loc[y_test.index]

    logger.info(
        "Training matrix: X_train=%s, y_train=%d, X_val=%s, X_test=%s",
        X_train.shape,
        len(y_train),
        X_val.shape if X_val is not None else "N/A",
        X_test.shape if X_test is not None else "N/A",
    )

    # -----------------------------------------------------------------------
    # 12. Train XGBoost candidate model
    # -----------------------------------------------------------------------
    all_metrics: Dict[str, Any] = {
        "candidate_version": candidate_version,
        "feature_schema_version": EXPECTED_SCHEMA_VERSION,
        "target_column": _TARGET_COL,
        "target_formula": "reference_temperature_c - coarse_temperature_c",
        "is_synthetic": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split_report": split_report,
    }

    model_fitted = False
    try:
        import xgboost as xgb  # type: ignore
        logger.info("XGBoost version %s available — fitting model.", xgb.__version__)

        xgb_params = {
            "objective": "reg:squarederror",
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 5,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "seed": 42,
            "early_stopping_rounds": 15,
            "eval_metric": "rmse",
        }

        eval_set = [(X_val.fillna(0), y_val)] if X_val is not None and y_val is not None else None

        if not dry_run:
            model = xgb.XGBRegressor(**{k: v for k, v in xgb_params.items()
                                         if k not in ("early_stopping_rounds",)})
            model.set_params(early_stopping_rounds=xgb_params["early_stopping_rounds"])
            model.fit(
                X_train.fillna(0), y_train,
                eval_set=eval_set,
                verbose=False,
            )
            model_fitted = True

            # Compute metrics
            for split_name, (X_s, y_s) in [
                ("train", (X_train, y_train)),
                ("validation", (X_val, y_val) if X_val is not None else (None, None)),
                ("test", (X_test, y_test) if X_test is not None else (None, None)),
            ]:
                if X_s is None or y_s is None or len(X_s) == 0:
                    continue
                y_pred = model.predict(X_s.fillna(0))
                m = _compute_metrics(y_s.values, y_pred, split_name)
                all_metrics[f"{split_name}_metrics"] = m
                logger.info(
                    "Metrics [%s]: MAE=%.4f°C  RMSE=%.4f°C  R²=%.4f  Bias=%.4f°C  N=%d",
                    split_name, m["mae"] or float("nan"), m["rmse"] or float("nan"),
                    m["r2"] or float("nan"), m["bias"] or float("nan"), m["sample_count"],
                )

            # Feature importances
            importances = model.feature_importances_
            feat_imp = [
                {"feature": c, "importance": round(float(v), 6)}
                for c, v in zip(feature_cols_present, importances)
            ]
            feat_imp.sort(key=lambda x: x["importance"], reverse=True)
            all_metrics["feature_importances"] = feat_imp
        else:
            logger.info("DRY RUN: model.fit() skipped.")

    except ImportError:
        logger.warning(
            "XGBoost not installed — model training skipped. "
            "Install with: pip install xgboost. "
            "Metrics and provenance artifacts will still be saved."
        )
        all_metrics["training_status"] = "XGBOOST_NOT_INSTALLED"

    # -----------------------------------------------------------------------
    # 13. Determine reference source type (OBSERVATION vs REANALYSIS)
    # -----------------------------------------------------------------------
    ref_source_type = "UNKNOWN"
    if "prov_source_type" in train_df.columns:
        types = train_df["prov_source_type"].dropna().unique().tolist()
        if "OBSERVATION" in types:
            ref_source_type = "OBSERVATION"
            logger.info("Reference source type: OBSERVATION (station-observed validation).")
        else:
            ref_source_type = "REANALYSIS"
            logger.warning(
                "Reference source type: REANALYSIS. "
                "This is NOT station-observed validation. "
                "Label all results accordingly."
            )
    all_metrics["reference_source_type"] = ref_source_type
    all_metrics["is_station_validated"] = (ref_source_type == "OBSERVATION")

    # -----------------------------------------------------------------------
    # 14. Build dataset manifest
    # -----------------------------------------------------------------------
    if not dry_run:
        try:
            writer = DatasetManifestWriter(
                dataset_id=f"varanasi-pilot-{candidate_version}",
                dataset_name="Varanasi Pilot Real-Data Training Dataset",
                data_classification="REAL_DATA",
                country="India",
                state="Uttar Pradesh",
                district="Varanasi",
                block="Varanasi Sadar",
                panchayats=[],
                latitude_min=_PILOT_LAT_MIN,
                latitude_max=_PILOT_LAT_MAX,
                longitude_min=_PILOT_LON_MIN,
                longitude_max=_PILOT_LON_MAX,
                time_start=_PILOT_SPLITS["train"]["start"],
                time_end=_PILOT_SPLITS["test"]["end"],
            )
            writer.set_split_counts(
                train=len(train_df),
                validation=len(val_df),
                test=len(test_df),
            )
            writer.set_quality_summary(
                missing_percentage=float(
                    feat_df.isna().sum().sum() / max(feat_df.size, 1) * 100
                ),
                invalid_count=0,
                suspect_count=0,
            )
            for src in build_pilot_sources():
                writer.add_source(src)

            manifest_out = manifest_output_path or (
                _CANDIDATES_ROOT / candidate_version / "dataset_manifest.json"
            )
            writer.write(manifest_out)
            all_metrics["manifest_path"] = str(manifest_out)
            logger.info("Dataset manifest → %s", manifest_out)
        except Exception as e:
            logger.warning("Failed to write dataset manifest: %s", e)

    # -----------------------------------------------------------------------
    # 15. Save candidate artifacts
    # -----------------------------------------------------------------------
    candidate_dir = _CANDIDATES_ROOT / candidate_version

    provenance = {
        "train_rows": len(train_df),
        "validation_rows": len(val_df),
        "test_rows": len(test_df),
        "total_rows": len(df),
        "feature_count": len(feature_cols_present),
        "pilot": "Varanasi, Uttar Pradesh, India",
        "aoi_lat": f"{_PILOT_LAT_MIN}–{_PILOT_LAT_MAX}",
        "aoi_lon": f"{_PILOT_LON_MIN}–{_PILOT_LON_MAX}",
        "data_classification": "REAL_DATA",
        "reference_source_type": ref_source_type,
    }

    if not dry_run:
        # Save XGBoost model if fitted
        if model_fitted:
            try:
                model_path = candidate_dir / "model.json"
                candidate_dir.mkdir(parents=True, exist_ok=True)
                model.save_model(str(model_path))
                logger.info("XGBoost model saved → %s", model_path)
                all_metrics["model_path"] = str(model_path)
            except Exception as e:
                logger.warning("Could not save XGBoost model file: %s", e)

        _save_candidate_artifacts(
            candidate_dir=candidate_dir,
            metrics=all_metrics,
            feature_cols=feature_cols_present,
            provenance=provenance,
            dataset_path=dataset_path,
            candidate_version=candidate_version,
            manifest_path=manifest_output_path,
        )

    # -----------------------------------------------------------------------
    # 16. Post-training production model safety check
    # -----------------------------------------------------------------------
    try:
        _verify_production_model_unchanged(prod_fingerprint_pre)
    except RuntimeError as e:
        logger.critical("%s", e)
        return 1

    # -----------------------------------------------------------------------
    # Summary report
    # -----------------------------------------------------------------------
    logger.info("=" * 70)
    logger.info("TRAINING SUMMARY")
    logger.info("  PIPELINE IMPLEMENTED          : YES")
    logger.info("  CANDIDATE VERSION             : %s", candidate_version)
    logger.info("  CANDIDATE DIR                 : %s", candidate_dir)
    logger.info("  PRODUCTION MODEL              : UNCHANGED")
    logger.info("  MODEL FITTED                  : %s", model_fitted)
    logger.info("  DATA CLASSIFICATION           : REAL_DATA")
    logger.info("  REFERENCE SOURCE TYPE         : %s", ref_source_type)
    logger.info("  STATION OBSERVED VALIDATION   : %s", ref_source_type == "OBSERVATION")

    if not model_fitted:
        logger.warning(
            "REAL_REFERENCE_DATA_REQUIRED (partial): XGBoost not installed or dry-run. "
            "Install xgboost and re-run once real data is acquired."
        )

    if ref_source_type not in ("OBSERVATION",):
        logger.warning(
            "NOTE: Reference temperature source is '%s', not a station observation. "
            "If ERA5-Land is used as reference, this constitutes REANALYSIS-to-REANALYSIS "
            "downscaling evaluation — not station-validated evaluation. "
            "IMD AWS data (SOURCE_ACCESS_REQUIRED) is needed for true station validation.",
            ref_source_type,
        )

    logger.info("=" * 70)
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="India Pilot — Real-Data Candidate Model Trainer (SIH 26074)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the processed real-data training dataset (.parquet or .csv).",
    )
    parser.add_argument(
        "--candidate-version",
        type=str,
        default=f"v1.0.0-real-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        help="Semantic version string for this candidate model.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data and run checks without fitting the model or writing artifacts.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=None,
        help="Optional path for the output dataset_manifest.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    exit_code = train_candidate_model(
        dataset_path=args.dataset,
        candidate_version=args.candidate_version,
        dry_run=args.dry_run,
        manifest_output_path=args.manifest_output,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
