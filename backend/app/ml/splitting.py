from typing import List
from app.ml.schemas import EngineeredFeatureRecord


class TimeSeriesSplitter:
    """
    Chronological time-series dataset splitter.
    Guarantees no future-to-past information leakage across train/validation/test partitions.
    """

    @staticmethod
    def split_chronologically(
        records: List[EngineeredFeatureRecord],
        train_ratio: float = 0.70,
        validation_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> List[EngineeredFeatureRecord]:
        """
        Sorts records by observation timestamp and partitions them into train, val, test splits.
        """
        if not records:
            return []

        # Sort strictly by observation_time
        sorted_records = sorted(records, key=lambda r: (r.observation_time, r.forecast_issue_time))
        n = len(sorted_records)

        train_end_idx = int(n * train_ratio)
        val_end_idx = train_end_idx + int(n * validation_ratio)

        for i, rec in enumerate(sorted_records):
            if i < train_end_idx:
                rec.split = "train"
            elif i < val_end_idx:
                rec.split = "val"
            else:
                rec.split = "test"

        return sorted_records
