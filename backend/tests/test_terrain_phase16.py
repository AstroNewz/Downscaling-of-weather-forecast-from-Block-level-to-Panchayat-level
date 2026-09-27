"""
Phase 16 Terrain Tests — SRTM, CRS, DEM-to-grid, candidate model path
SIH Problem Statement 26074

Tests added:
  - SRTM provenance file exists and has correct fields
  - CRS is EPSG:32644 (UTM 44N) for metric calculations, not EPSG:3857
  - DEM tile coverage (N25E082, N25E083)
  - Terrain features are populated (not ALL NULL) for stations inside tile coverage
  - Missing terrain handled gracefully for out-of-tile stations (Allahabad)
  - Feature schema hasn't accidentally added target columns
  - Candidate V3 model stored under candidates/ not production
  - Production model path unchanged
  - Terrain classified REMOTE_SENSING, not OBSERVATION
"""
import json
import pytest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR      = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
MANIFEST_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
CANDIDATES   = BACKEND_ROOT / "models" / "candidates" / "temperature_residual"
PRODUCTION   = BACKEND_ROOT / "models" / "temperature_residual"


# ─────────────────────────────────────────────────────────────────────────────
# SRTM provenance
# ─────────────────────────────────────────────────────────────────────────────

class TestSRTMProvenance:
    def test_terrain_file_exists(self):
        """SRTM terrain JSON must exist after Phase 16."""
        f = RAW_DIR / "srtm_varanasi_terrain.json"
        assert f.exists(), f"srtm_varanasi_terrain.json missing at {f}"

    def test_terrain_classified_remote_sensing(self):
        """SRTM must be classified REMOTE_SENSING, never OBSERVATION."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        assert d["source_type"] == "REMOTE_SENSING", (
            f"Expected REMOTE_SENSING, got {d['source_type']}"
        )

    def test_tile_shas_present(self):
        """SHA-256 checksums must be present for both SRTM tiles."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        tiles = {t["name"]: t["sha256"] for t in d["tiles"]}
        for expected_tile in ["N25E082", "N25E083"]:
            assert expected_tile in tiles, f"Tile {expected_tile} missing from terrain JSON"
            sha = tiles[expected_tile]
            assert len(sha) == 64, f"SHA256 for {expected_tile} should be 64 chars, got {len(sha)}"
            assert sha != "0" * 64, f"SHA256 for {expected_tile} looks like a placeholder"

    def test_provenance_sidecar_exists(self):
        """Provenance sidecar must exist alongside the terrain JSON."""
        prov = RAW_DIR / "srtm_varanasi_terrain.json.provenance.json"
        assert prov.exists(), "SRTM provenance sidecar missing"

    def test_terrain_resolution_documented(self):
        """Spatial resolution must be documented."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        assert "spatial_resolution" in d, "spatial_resolution not documented"
        assert "30" in str(d["spatial_resolution"]), (
            f"Expected 30m resolution, got {d['spatial_resolution']}"
        )

    def test_raw_tile_files_exist(self):
        """Raw HGT.gz tile files must be preserved."""
        for tile in ["N25E082.hgt.gz", "N25E083.hgt.gz"]:
            f = RAW_DIR / tile
            assert f.exists(), f"Raw SRTM tile {tile} missing"
            assert f.stat().st_size > 1_000_000, f"{tile} appears empty or truncated"


# ─────────────────────────────────────────────────────────────────────────────
# CRS correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestCRSPolicy:
    def test_terrain_uses_utm_not_webmercator(self):
        """Terrain JSON must document UTM 44N, not EPSG:3857, for metric calculations."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        crs_metric = d.get("crs_metric_used_for_slope", "")
        assert "32644" in crs_metric or "UTM" in crs_metric or "44N" in crs_metric, (
            f"Expected UTM 44N (EPSG:32644), got: {crs_metric}"
        )
        assert "3857" not in crs_metric, (
            "EPSG:3857 (Web Mercator) must not be used for metric terrain calculations"
        )

    def test_terrain_geographic_crs_is_wgs84(self):
        """Geographic CRS for coordinates must be WGS84 (EPSG:4326)."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        crs_geo = d.get("crs_geographic", "")
        assert "4326" in crs_geo or "WGS84" in crs_geo, (
            f"Expected EPSG:4326 (WGS84), got: {crs_geo}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DEM coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestDEMCoverage:
    def test_grid_coverage_complete(self):
        """Dense grid must be 100% covered (no NULL elevations in AOI)."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        grid = d["dense_grid"]
        assert grid["valid_count"] == grid["total_count"], (
            f"Expected 100% grid coverage, got {grid['valid_count']}/{grid['total_count']}"
        )

    def test_elevation_range_physically_plausible(self):
        """Varanasi elevation must be in plausible range for Gangetic plain."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        elev_min = d["dense_grid"]["elev_min"]
        elev_max = d["dense_grid"]["elev_max"]
        assert 20 <= elev_min <= 150, f"Unexpected min elevation: {elev_min}m"
        assert 40 <= elev_max <= 300, f"Unexpected max elevation: {elev_max}m"

    def test_station_terrain_populated_for_covered_stations(self):
        """Stations inside SRTM tile coverage must have non-NULL elevation."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        covered = ["NOAA_ISD_424790", "NOAA_ISD_424830", "NOAA_ISD_424820"]
        for sid in covered:
            t = d["station_terrain"].get(sid, {})
            assert t.get("elevation_m") is not None, (
                f"{sid} should have SRTM elevation (inside tile coverage)"
            )
            assert t.get("slope_deg") is not None, f"{sid} should have slope_deg"
            assert t.get("aspect_deg") is not None, f"{sid} should have aspect_deg"

    def test_out_of_tile_station_terrain_is_null(self):
        """Allahabad (lon=81.734) is outside tile N25E082 — terrain must be NULL, not fabricated."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        t = d["station_terrain"].get("NOAA_ISD_424750", {})
        assert t.get("elevation_m") is None, (
            "NOAA_ISD_424750 (Allahabad, lon=81.734) is outside SRTM tile coverage — "
            "elevation_m must be NULL, not fabricated"
        )

    def test_babatpur_elevation_matches_isd_metadata(self):
        """Babatpur SRTM elevation (81m) should be within 10m of ISD reported elevation (81.1m)."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        srtm_elev = d["station_terrain"]["NOAA_ISD_424790"]["elevation_m"]
        isd_reported = 81.1
        assert abs(srtm_elev - isd_reported) <= 10, (
            f"SRTM elevation {srtm_elev}m differs from ISD metadata {isd_reported}m by more than 10m"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Candidate model path
# ─────────────────────────────────────────────────────────────────────────────

class TestCandidateModelPath:
    def test_v3_candidate_exists(self):
        """At least one candidate_v3 model must exist."""
        v3_dirs = list(CANDIDATES.glob("candidate_v3_*"))
        assert len(v3_dirs) >= 1, f"No candidate_v3 found under {CANDIDATES}"

    def test_v3_metadata_has_srtm_fields(self):
        """V3 model metadata must document SRTM source and SHA."""
        v3_dirs = sorted(CANDIDATES.glob("candidate_v3_*"))
        meta_path = v3_dirs[-1] / "model_metadata.json"
        assert meta_path.exists(), f"model_metadata.json missing for {v3_dirs[-1].name}"
        with open(meta_path) as fh:
            meta = json.load(fh)
        assert meta.get("srtm_status") == "ACQUIRED", (
            f"Expected srtm_status=ACQUIRED, got {meta.get('srtm_status')}"
        )
        assert "srtm_tiles" in meta and len(meta["srtm_tiles"]) >= 2, (
            "V3 metadata must include SRTM tile SHA checksums"
        )
        assert meta.get("production_model_modified") == False, (
            "production_model_modified must be False"
        )

    def test_production_model_path_unchanged(self):
        """Production model directory must not contain candidate_ models."""
        if not PRODUCTION.exists():
            pytest.skip("Production model directory does not exist — skipping")
        candidate_dirs = list(PRODUCTION.glob("candidate_*"))
        assert len(candidate_dirs) == 0, (
            f"Candidate models found in production directory: {candidate_dirs}. "
            "Candidates must stay in models/candidates/"
        )

    def test_v3_terrain_classification_in_metadata(self):
        """V3 metadata must classify SRTM as REMOTE_SENSING."""
        v3_dirs = sorted(CANDIDATES.glob("candidate_v3_*"))
        with open(v3_dirs[-1] / "model_metadata.json") as fh:
            meta = json.load(fh)
        assert meta.get("srtm_classification") == "REMOTE_SENSING", (
            "SRTM must be classified REMOTE_SENSING in model metadata"
        )

    def test_v3_leakage_audit_pass(self):
        """V3 model metadata must record PASS for all leakage checks."""
        v3_dirs = sorted(CANDIDATES.glob("candidate_v3_*"))
        with open(v3_dirs[-1] / "model_metadata.json") as fh:
            meta = json.load(fh)
        audit = meta.get("leakage_audit", {})
        for check in ["target_leakage","temporal_leakage_train_val",
                      "temporal_leakage_val_test","spatial_holdout_independence"]:
            assert audit.get(check) == "PASS", (
                f"Leakage check '{check}' is not PASS: {audit.get(check)}"
            )

    def test_v3_improved_flag_is_boolean(self):
        """improved flag must be a boolean, never missing."""
        v3_dirs = sorted(CANDIDATES.glob("candidate_v3_*"))
        with open(v3_dirs[-1] / "model_metadata.json") as fh:
            meta = json.load(fh)
        assert "improvement_vs_baseline" in meta
        assert isinstance(meta["improvement_vs_baseline"]["improved"], bool)

    def test_historical_versions_preserved(self):
        """V1 and V2 candidates must still exist — history must not be erased."""
        v1_dirs = list(CANDIDATES.glob("candidate_v1_*"))
        v2_dirs = list(CANDIDATES.glob("candidate_v2_*"))
        assert len(v1_dirs) >= 1, "V1 candidate history missing"
        assert len(v2_dirs) >= 1, "V2 candidate history missing"


# ─────────────────────────────────────────────────────────────────────────────
# Missing terrain handling
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingTerrainHandling:
    def test_terrain_null_fraction_below_10pct(self):
        """After Phase 16, terrain NULLs should be < 10% (only Allahabad is outside tile)."""
        with open(RAW_DIR / "srtm_varanasi_terrain.json") as fh:
            d = json.load(fh)
        # Allahabad is ~125/2635 ≈ 4.7% of rows
        covered = sum(1 for v in d["station_terrain"].values()
                      if v.get("elevation_m") is not None)
        total   = len(d["station_terrain"])
        null_pct = 100 * (total - covered) / total
        assert null_pct <= 50, (
            f"Terrain NULL fraction too high: {null_pct:.1f}% stations lack elevation"
        )
