# Panchayat Localized Precipitation Observation-Fusion & Short-Horizon Nowcasting
**SIH Problem Statement 26074 (Weather Downscaling - Task 4)**
*Authoritative Architecture & Scientific Governance Document*

---

## 1. Executive Summary & Architectural Overview

Task 4 establishes a scientifically conservative **Panchayat-Level Precipitation Observation-Fusion and Short-Horizon Nowcasting Service** (`PanchayatPrecipitationNowcastService`).

In tropical and monsoon agro-meteorology, Numerical Weather Prediction (NWP) forecasts (such as IMD-GFS, ECMWF, or NCMRWF-IMDAA) provide macroscale atmospheric dynamics over $10\text{–}25\text{ km}$ grid footprints. However, localized convective cells, squall lines, and orographic rainfall initiate on sub-mesoscale dimensions ($1\text{–}5\text{ km}$) and evolve rapidly within minutes to hours.

The Task 4 layer combines coarse-resolution NWP expectations with fresh observational evidence streams—including geostationary satellite thermal infrared / cloud observations, satellite precipitation estimates, optional ground Doppler Weather Radar (DWR), and automatic weather stations (AWS)—using the exact Gram Panchayat administrative polygons from Task 1 and the fractional spatial-masking layer from Task 2.

```
       ┌────────────────────────┐
       │   NWP Block Forecast   │  (Coarse NWP baseline expectation)
       └───────────┬────────────┘
                   │
       ┌───────────┴────────────┐
       │  Satellite Observation │  (Top-of-atmosphere radiance / cloud tops)
       └───────────┬────────────┘
                   │
       ┌───────────┴────────────┐
       │   Optional Radar DWR   │  (Reflectivity & precipitation echoes)
       └───────────┬────────────┘
                   │
       ┌───────────┴────────────┐
       │   Surface AWS / Gauge  │  (Surface precipitation ground confirmation)
       └───────────┬────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│     PanchayatPrecipitationNowcastService                │
│  - Multi-stream evidence component auditing            │
│  - Spatial masking per Panchayat polygon (A vs B)      │
│  - Two-stage precipitation modeling:                   │
│      Stage 1: P(rain >= 0.1 mm)                        │
│      Stage 2: E[rainfall | rain >= 0.1 mm]             │
│  - Source disagreement detection & penalty             │
│  - Multi-horizon time-decay weighting (30m, 60m, 120m) │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
 ┌───────────────────────┐   ┌───────────────────────┐
 │  Panchayat A Outlook  │   │  Panchayat B Outlook  │
 │  - High rain prob     │   │  - Low rain prob      │
 │  - Convective core    │   │  - Clear skies        │
 │  - Full Provenance    │   │  - Full Provenance    │
 └───────────────────────┘   └───────────────────────┘
```

---

## 2. Core Scientific Principles & Mandates

### A. Architecture: Multi-Stream Evidence Combination
The nowcasting service acts as an observational evidence aggregator. It does not replace the baseline NWP forecast; instead, it retains the baseline forecast side-by-side with localized observation-fused outlooks, allowing direct comparison of macroscale expectations against near-real-time sensor evidence.

### B. Evidence Sources Supported
1. **NWP Baseline Forecast**: IMD-GFS / NCMRWF block forecasts providing 3-hour precipitation depths and baseline probability.
2. **Satellite Infrared Radiance (INSAT-3D/3DR TIR1 / TIR2)**: 10.8µm / 12.0µm brightness temperatures identifying convective cloud tops ($T_{\min} < 235\text{ K}$) and cloud fraction.
3. **Satellite Precipitation Retrieval (HEGG / IMERG)**: Algorithmic precipitation estimates labeled strictly as estimates.
4. **Doppler Weather Radar (DWR)**: Pluggable volumetric radar reflectivity (dBZ) and Z-R derived rain rates.
5. **Surface Telemetry (AWS / Rain Gauges)**: Surface tipping-bucket rainfall accumulations in the preceding hour.

### C. Panchayat-Specific Processing (A vs B Separation)
Processing is strictly polygon-first. When a weather system traverses an administrative Block, spatial masking is executed independently for each Panchayat polygon:
- **Panchayat A**: Intersected pixels yield A-specific convective cloud fractions, brightness temperatures, and radar echoes.
- **Panchayat B**: Intersected pixels yield B-specific conditions.
- Adjacent Panchayats A and B inside the same block share the same NWP baseline expectation, but derive distinct nowcast probabilities driven entirely by localized spatial observation evidence.

### D. Two-Stage Precipitation Representation
Precipitation cannot be treated as a single continuous variable like temperature. The physical process involves:
1. **Stage 1: Probability of Measurable Precipitation ($P(\text{rain} \ge 0.1\text{ mm})$)**
   - Normalized between $0.02$ and $0.98$.
   - Fused from weighted evidence components accounting for latency and spatial coverage.
2. **Stage 2: Expected Precipitation Amount ($E[\text{rainfall} \mid \text{rain} \ge 0.1\text{ mm}]$)**
   - Conditional strictly on precipitation occurring.
   - If evidence is insufficient to formulate a reliable quantitative depth (e.g. only cloud mask or thermal IR is available without calibrated radar/gauge retrieval), `expected_amount_mm = null` is emitted. **Fabricating numeric depths is strictly prohibited.**

### E. 30, 60, and 120-Minute Forecast Horizons
Outlooks are generated across three operational horizons reflecting time-decay dynamics:
- **30-Minute Horizon**: Dominated by high-frequency real-time observations (Radar weight: 0.45, Satellite: 0.35, Surface: 0.35, NWP: 0.15).
- **60-Minute Horizon (Primary Headline)**: Balanced observation-fusion and NWP (Radar: 0.35, Satellite: 0.30, Surface: 0.25, NWP: 0.25).
- **120-Minute Horizon**: NWP baseline weight increases as instantaneous observation echoes decorrelate (NWP: 0.45, Satellite: 0.25, Radar: 0.20, Surface: 0.15).

### F. Conservative Confidence Model
Confidence is derived transparently from measurable objective factors, categorized into:
- `HIGH`: $\ge 2$ independent agreeing fresh observation streams + NWP, spatial coverage $\ge 90\%$.
- `MEDIUM`: NWP + Satellite agreeing, fresh data, spatial coverage $\ge 80\%$.
- `LOW`: Single source, high latency, spatial coverage $< 80\%$, or source disagreement.
- `INSUFFICIENT_DATA`: Total spatial coverage $< 20\%$, missing georeferencing, unverified boundary, or missing inputs.

### G. Source Disagreement Detection
When independent evidence streams contradict one another:
- Example: NWP predicts heavy rain ($p = 0.85, 8\text{ mm}$), but geostationary satellite IR observes clear, warm ground ($T_{\min} > 285\text{ K}$, cloud fraction $< 10\%$).
- **Guardrail Action**: The service flags `evidence_disagreement = True`, caps confidence at `LOW`, dampens probability towards uncertainty ($0.50$), and documents the exact conflicting metrics in `disagreement_details`. Blind averaging of contradictory sources is forbidden.

### H. Optional Radar Compatibility
Doppler Weather Radar is treated as a modular, optional enhancement:
- In areas covered by operational IMD DWR stations (e.g., Varanasi, Lucknow, Delhi), radar echoes dramatically boost Stage 2 rain rate accuracy.
- In areas outside radar beams, the pipeline executes seamlessly using Satellite + NWP, reducing confidence appropriately without breaking.

### I. Missing and Stale Data Handling
- Stale observations exceeding the configured threshold ($> 60\text{ min}$) receive an automatic penalty factor ($0.50\times$), decaying their influence.
- Missing satellite or radar data never triggers synthetic fallback or silent substitution of third-party APIs.
- Zero rainfall ($0.0\text{ mm}$) is preserved as dry ground; missing sensor cells are preserved as `null`.

### J. Why Satellite $\ne$ Rainfall Ground Truth
Top-of-atmosphere radiances depict cloud top temperatures and optical thickness. Deep convective cloud tops ($T_b < 220\text{ K}$) strongly indicate convective updrafts, but sub-cloud evaporation (virga), tilted updrafts, and non-precipitating cirrus anvils prevent satellite imagery from serving as a direct ground-truth rain gauge.

### K. Why Deterministic Research Heuristics $\ne$ Certified Nowcasting Accuracy
The current weighting rules are explicitly versioned and documented as `DETERMINISTIC_RESEARCH_HEURISTIC_V1`. They establish a robust, transparent, auditable fusion framework. No claim of certified empirical nowcasting skill or verified sub-kilometer precipitation accuracy is made until multi-year ground gauge validation is completed.

### L. Future Roadmap Toward Machine-Learned Nowcasting
Future tasks will expand upon this foundation:
1. Ingest operational IMD Doppler Weather Radar NetCDF/MDV volumetric feeds.
2. Train localized optical flow / convolutional precipitation nowcasting models.
3. Validate against high-density Automatic Weather Station (AWS) networks across pilot districts.

---

## 3. Provenance & Audit Payload Example

```json
{
  "panchayat_id": "DHOLAKPUR_PANCHAYAT_A",
  "panchayat_name": "Dholakpur Panchayat A",
  "block_name": "Dholakpur Block",
  "issue_time": "2026-09-27T12:00:00Z",
  "baseline_forecast": {
    "source_model": "IMD-GFS-BLOCK-SHARED",
    "forecast_valid_time": "2026-09-27T12:00:00Z",
    "baseline_precipitation_mm": 1.0,
    "baseline_probability": 0.35
  },
  "primary_horizon": {
    "horizon_minutes": 60,
    "valid_time": "2026-09-27T12:00:00Z",
    "rain_probability": 0.76,
    "measurable_rain_threshold_mm": 0.1,
    "is_rain_likely": true,
    "expected_amount_mm": 2.25,
    "confidence": "MEDIUM",
    "confidence_score": 0.65,
    "evidence_sources": [
      "NWP_FORECAST",
      "SATELLITE_CLOUD_INFRARED"
    ],
    "source_state": "NWP_SATELLITE",
    "evidence_disagreement": false,
    "observation_age_minutes": 5.0,
    "spatial_coverage": 1.0,
    "fusion_method": "DETERMINISTIC_RESEARCH_HEURISTIC_V1"
  },
  "provenance": {
    "nwp_source": "IMD-GFS-BLOCK-SHARED (valid=2026-09-27T12:00:00Z)",
    "satellite_source": "SATELLITE_OBSERVATION_ADAPTER INSAT-3DR_TIR1 (obs=2026-09-27T12:00:00Z)",
    "radar_source": "NONE_OR_UNAVAILABLE",
    "evidence_weight_version": "DETERMINISTIC_RESEARCH_HEURISTIC_V1",
    "scientific_disclaimer": "Localized precipitation nowcasting combines NWP baseline expectations with georeferenced satellite and radar evidence. It provides conservative risk estimates; it does NOT constitute certified ground-truth rainfall observations or verified empirical nowcasting accuracy."
  },
  "success": true
}
```
