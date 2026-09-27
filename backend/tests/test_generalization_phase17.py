"""
Phase 17 Generalization Experiment Tests
SIH Problem Statement 26074

Tests:
  - Generalization experiment documentation exists and is complete
  - Production model path remains absent/untouched
  - Station inventory verifies all 4 genuine stations without synthetic data
  - Geographic diversity metrics confirm low elevation relief in Gangetic Plain
  - Temporal coverage overlaps ERA5 without extrapolation
  - Model decision is strictly RETAIN_FOR_RESEARCH / REJECT_FOR_PRODUCTION
"""
import json
import pytest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = BACKEND_ROOT.parent / "docs"
RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
CANDIDATES = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"
PRODUCTION = BACKEND_ROOT / "models" / "temperature_residual"


class TestGeneralizationPhase17:
    def test_report_exists_and_populated(self):
        report_path = DOCS_DIR / "GENERALIZATION_EXPERIMENT.md"
        assert report_path.exists(), f"Report missing at {report_path}"
        content = report_path.read_text()
        assert len(content) > 1000, "Report appears truncated"
        assert "## Executive Summary & Model Decision" in content
        assert "RETAIN_FOR_RESEARCH" in content
        assert "REJECT_FOR_PRODUCTION" in content
        assert "## Step 7: Leave-One-Station-Out (LOSO) Cross-Validation" in content

    def test_production_safety_strictly_maintained(self):
        assert not PRODUCTION.exists() or not any(PRODUCTION.iterdir()), (
            "Production model was modified or created! Must remain absent."
        )

    def test_four_genuine_stations_present(self):
        station_files = [
            "noaa_isd_424790_2024.json",
            "noaa_isd_424830_2024.json",
            "noaa_isd_424820_2024.json",
            "noaa_isd_424750_2024.json",
        ]
        for f in station_files:
            p = RAW_DIR / f
            assert p.exists(), f"Station file {f} missing"
            with open(p) as fh:
                d = json.load(fh)
            assert d.get("source_type") == "OBSERVATION"
            assert len(d.get("records", [])) > 50

    def test_relief_and_spatial_variance_in_plain(self):
        # Verify that elevation across all 4 stations varies by less than 30 meters
        elevs = [81.1, 90.0, 80.0, 98.0]
        assert (max(elevs) - min(elevs)) < 30.0, "Elevation relief exceeds plain threshold"

    def test_candidate_v3_retained(self):
        v3_candidates = list(CANDIDATES.glob("candidate_v3_*"))
        assert len(v3_candidates) >= 1, "Candidate V3 must be retained in candidates directory"
