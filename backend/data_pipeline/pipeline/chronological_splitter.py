"""
Chronological Train/Validation/Test Splitter
SIH Problem Statement 26074 — Agroweather-Downscaling

Splits records chronologically to prevent temporal leakage.
Dates come from india_pilot.yaml splits configuration.

Split periods (Varanasi pilot):
  TRAIN     : 2024-06-01 to 2024-07-15  (45 days — early Kharif)
  VALIDATION: 2024-07-16 to 2024-07-31  (16 days — mid Kharif)
  TEST      : 2024-08-01 to 2024-08-31  (31 days — late Kharif, held-out)

Rules:
  - No hourly record from VALIDATION or TEST appears in TRAIN
  - No hourly record from TEST appears in VALIDATION
  - Optional spatial holdout: one panchayat excluded from TRAIN set
  - Temporal overlap is computed and reported (must be 0%)
  - Spatial overlap is computed and reported if holdout used
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd


SPLIT_TRAIN = "train"
SPLIT_VALIDATION = "validation"
SPLIT_TEST = "test"


class ChronologicalSplitter:
    """
    Assigns train/validation/test split labels to records based on timestamp.
    Validates that no temporal leakage exists between splits.
    """

    def __init__(
        self,
        train_start: str,
        train_end: str,
        validation_start: str,
        validation_end: str,
        test_start: str,
        test_end: str,
        spatial_holdout_panchayat: Optional[str] = None,
    ):
        """
        Args:
            train_start/end     : ISO date strings for training period
            validation_start/end: ISO date strings for validation period
            test_start/end      : ISO date strings for test period (held-out)
            spatial_holdout_panchayat: Optional panchayat name to exclude
                                       from training set (for spatial generalization testing)
        """
        self.train_start = date.fromisoformat(train_start)
        self.train_end = date.fromisoformat(train_end)
        self.validation_start = date.fromisoformat(validation_start)
        self.validation_end = date.fromisoformat(validation_end)
        self.test_start = date.fromisoformat(test_start)
        self.test_end = date.fromisoformat(test_end)
        self.spatial_holdout_panchayat = spatial_holdout_panchayat

        self._validate_no_overlap()

    def _validate_no_overlap(self):
        """Raises ValueError if any temporal overlap exists between splits."""
        if self.train_end >= self.validation_start:
            raise ValueError(
                f"Temporal leakage: TRAIN ends {self.train_end} "
                f">= VALIDATION starts {self.validation_start}"
            )
        if self.validation_end >= self.test_start:
            raise ValueError(
                f"Temporal leakage: VALIDATION ends {self.validation_end} "
                f">= TEST starts {self.test_start}"
            )

    def assign_split(
        self,
        timestamp: datetime,
        panchayat: Optional[str] = None,
    ) -> Optional[str]:
        """
        Returns split label for a given timestamp, or None if outside all periods.

        Args:
            timestamp: Record timestamp (UTC).
            panchayat: Panchayat name for spatial holdout check.

        Returns:
            "train" / "validation" / "test" / None
        """
        record_date = timestamp.date() if hasattr(timestamp, "date") else timestamp

        if self.train_start <= record_date <= self.train_end:
            # Spatial holdout: remove this panchayat from training
            if (self.spatial_holdout_panchayat
                    and panchayat == self.spatial_holdout_panchayat):
                return None  # Excluded from training for spatial generalization test
            return SPLIT_TRAIN

        if self.validation_start <= record_date <= self.validation_end:
            return SPLIT_VALIDATION

        if self.test_start <= record_date <= self.test_end:
            return SPLIT_TEST

        return None  # Outside all defined periods

    def split_dataframe(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp_utc",
        panchayat_col: Optional[str] = "panchayat",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Splits a DataFrame into train/validation/test sets.

        Args:
            df: Input DataFrame with timestamp column.
            timestamp_col: Name of the UTC timestamp column.
            panchayat_col: Column for spatial holdout (None to skip).

        Returns:
            (train_df, val_df, test_df, split_report)

        The split_report contains:
            - record counts per split
            - temporal ranges per split
            - temporal overlap (must be 0)
            - spatial overlap if holdout used
            - fraction of records outside all periods
        """
        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])

        splits = []
        for _, row in df.iterrows():
            ts = row[timestamp_col]
            panchayat = row.get(panchayat_col) if panchayat_col and panchayat_col in df.columns else None
            split = self.assign_split(ts, panchayat)
            splits.append(split)

        df["_split"] = splits
        outside = df["_split"].isna().sum()

        train_df = df[df["_split"] == SPLIT_TRAIN].drop(columns=["_split"]).reset_index(drop=True)
        val_df = df[df["_split"] == SPLIT_VALIDATION].drop(columns=["_split"]).reset_index(drop=True)
        test_df = df[df["_split"] == SPLIT_TEST].drop(columns=["_split"]).reset_index(drop=True)

        def ts_range(subset):
            if len(subset) == 0:
                return None, None
            return str(subset[timestamp_col].min()), str(subset[timestamp_col].max())

        tr_min, tr_max = ts_range(train_df)
        va_min, va_max = ts_range(val_df)
        te_min, te_max = ts_range(test_df)

        # Verify zero temporal overlap (strict)
        temporal_overlap = 0
        if tr_max and va_min:
            if pd.Timestamp(tr_max) >= pd.Timestamp(va_min):
                temporal_overlap += 1
        if va_max and te_min:
            if pd.Timestamp(va_max) >= pd.Timestamp(te_min):
                temporal_overlap += 1

        # Spatial overlap check
        spatial_overlap_pct = None
        if self.spatial_holdout_panchayat and panchayat_col and panchayat_col in df.columns:
            train_panchayats = set(train_df[panchayat_col].dropna().unique())
            test_panchayats = set(test_df[panchayat_col].dropna().unique())
            if self.spatial_holdout_panchayat in train_panchayats:
                spatial_overlap_pct = 100.0  # Holdout leaked into training!
            else:
                spatial_overlap_pct = 0.0

        split_report = {
            "train_records": len(train_df),
            "validation_records": len(val_df),
            "test_records": len(test_df),
            "outside_period_records": int(outside),
            "train_period": {"start": str(self.train_start), "end": str(self.train_end)},
            "validation_period": {"start": str(self.validation_start), "end": str(self.validation_end)},
            "test_period": {"start": str(self.test_start), "end": str(self.test_end)},
            "train_actual_range": {"start": tr_min, "end": tr_max},
            "validation_actual_range": {"start": va_min, "end": va_max},
            "test_actual_range": {"start": te_min, "end": te_max},
            "temporal_overlap_violations": temporal_overlap,
            "temporal_leakage_safe": temporal_overlap == 0,
            "spatial_holdout_panchayat": self.spatial_holdout_panchayat,
            "spatial_overlap_pct": spatial_overlap_pct,
        }

        return train_df, val_df, test_df, split_report

    @classmethod
    def from_pilot_config(cls, cfg, spatial_holdout_panchayat: Optional[str] = None):
        """
        Constructs a splitter from a PilotConfig object.

        Args:
            cfg: PilotConfig loaded from india_pilot.yaml
            spatial_holdout_panchayat: Optional panchayat to hold out spatially
        """
        splits = cfg.splits
        return cls(
            train_start=splits["train"].start,
            train_end=splits["train"].end,
            validation_start=splits["validation"].start,
            validation_end=splits["validation"].end,
            test_start=splits["test"].start,
            test_end=splits["test"].end,
            spatial_holdout_panchayat=spatial_holdout_panchayat,
        )
