"""
India-First Real-Data Pipeline for Agroweather-Downscaling (SIH 26074)
-----------------------------------------------------------------------
Pilot AOI: Varanasi Sadar Block, Varanasi District, Uttar Pradesh, India
UTM Zone : EPSG:32644 (WGS 84 / UTM zone 44N)

This package implements:
  - AOI-scoped data acquisition (real data only)
  - Indian-source-priority ordering
  - Canonical India weather schema
  - Data quality validation
  - Chronological train/val/test splitting
  - Dataset manifests with full provenance
  - Candidate model training (never overwrites production)

Rule: Never fabricate data. Never mix synthetic records with real data.
"""
__version__ = "1.0.0"
