# Phase 24: Comprehensive Artifact Inventory & Provenance Matrix

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE24_FINAL_AUDIT`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Date**: 2026-09-17  
**Status**: AUDITED & FROZEN  

---

## 1. Inventory Summary

This inventory catalogs every primary artifact across data, models, services, documentation, and evaluation suites in the repository, certifying their classification (Production vs. Research) and cryptographic integrity.

| Artifact Path | Purpose & Description | Experiment / Version | Classification | Mutability | SHA-256 Checksum |
|---|---|---|---|---|---|
| `backend/models/production_baseline/baseline_calibration.json` | Certified production scalar bias parameter ($B = +0.7351\ ^\circ\text{C}$), metrics, and uncertainty | Phase 23 / 24 | **PRODUCTION** | **FROZEN** | `3dcad5fbfd060d47ad9cbf1ec9cbe0df8c99da050e0d5a3ef2c3f76906ea1941` |
| `backend/models/production_baseline/metadata.json` | Production baseline schema, empirical error bounds, and pointer | Phase 23 / 24 | **PRODUCTION** | **FROZEN** | Verified |
| `backend/models/research/xgboost_research_manifest.json` | Research quarantine tracking and rejection rationale for XGBoost | Phase 23 / 24 | **RESEARCH** | **FROZEN** | Verified |
| `backend/models/candidates/temperature_residual/phase21_candidate_20260917/model.json` | 120-tree gradient boosted decision ensemble booster graph | Phase 21 / 22 | **RESEARCH ONLY** | **FROZEN** | `48ca2a9dba5a42b87ad18a51f4cc9a43ff19cf11c678a44ef20e86f52f1ed891` |
| `backend/models/candidates/temperature_residual/phase21_candidate_20260917/metadata.json` | Candidate feature schema and training hyperparameter specification | Phase 21 / 22 | **RESEARCH ONLY** | **FROZEN** | `6b97621c97a552f44778be8d523675e8ef8013e2f4f224976451e06d99723ec0` |
| `backend/data/processed/india/phase24/phase24_audit_results.json` | Phase 24 independent audit, reconciled observation counts, and gate results | Phase 24 | **AUDIT ARTIFACT** | **FROZEN** | Generated deterministically |
| `backend/data/processed/india/phase23/phase23_baseline_results.json` | Phase 23 baseline cross-validation, LOSO, and LORO results | Phase 23 | **EVALUATION** | **FROZEN** | Generated deterministically |
| `backend/data/processed/india/phase22/phase22_certification_results.json` | Phase 22 14-gate certification table, paired statistics, and terrain ablation | Phase 22 | **EVALUATION** | **FROZEN** | Generated deterministically |
| `backend/data/processed/india/phase21/phase21_validation_results.json` | Phase 21 multi-region national validation benchmark results | Phase 21 | **HISTORICAL** | **FROZEN** | Generated deterministically |
| `backend/data/raw/india/phase21/isd_*_2024.json` (17 files) | Genuine NOAA ISD-Lite surface thermometer observations (23,949 records) | Phase 21 Ingestion | **DATASET** | **FROZEN** | Sidecars in `*.provenance.json` |
| `backend/data/raw/india/phase21/era5_*_2024.json` (17 files) | ECMWF ERA5 hourly 2m atmospheric reanalysis | Phase 21 Ingestion | **DATASET** | **FROZEN** | Sidecars in `*.provenance.json` |
| `backend/app/gis/grid.py` | 1-km metric grid generator with dynamic local UTM projection | Phase 5 / 24 | **PRODUCTION CODE** | **FROZEN** | Verified |
| `backend/app/services/panchayat_aggregation.py` | Cadastral polygon area-weighted aggregation engine | Phase 7 / 24 | **PRODUCTION CODE** | **FROZEN** | Verified |
| `backend/app/services/agricultural_context.py` | Multi-crop growth stage and soil hydrological mapping | Phase 9 / 24 | **PRODUCTION CODE** | **FROZEN** | Verified |
| `backend/app/services/agricultural_risk.py` | Direction-aware threshold hazard detection engine | Phase 10 / 24 | **PRODUCTION CODE** | **FROZEN** | Verified |
| `backend/app/services/advisory_engine.py` | Actionable farmer advisory generation with timing windows | Phase 11 / 24 | **PRODUCTION CODE** | **FROZEN** | Verified |
| `frontend/src/pages/JudgeMode.tsx` | SIH Judge Walkthrough featuring model governance & audit flow | Phase 19 / 24 | **FRONTEND UI** | **FROZEN** | Verified |
