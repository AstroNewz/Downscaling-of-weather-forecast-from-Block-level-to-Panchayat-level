# Phase 23: Uncertainty Quantification & Propagation Protocol

**Experiment**: `EXP_PRODUCTION_BASELINE_PHASE23`  
**Problem Statement**: SIH 26074 — Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Document**: Scientific Uncertainty Quantification & Risk Engine Propagation  

---

## 1. Empirical Uncertainty Quantification

The production baseline refuses to treat downscaled weather estimates as deterministic physical truth. Every forecast is paired with rigorous, empirical error statistics derived from the frozen chronological test set ($N = 5,288$ synchronous ground-truth observations):

| Uncertainty Metric | Empirical Value | Operational Interpretation |
|---|---|---|
| **Mean Absolute Error (MAE)** | **±1.2661 °C** | Average expected error magnitude across India |
| **Residual Standard Deviation ($\sigma$)** | **±1.6354 °C** | Gaussian dispersion around true temperature |
| **Median Expected Error ($P_{50}$)** | **±0.9649 °C** | 50% of all forecasts lie within ~0.96°C of actual |
| **80th Percentile Error ($P_{80}$)** | **±1.9649 °C** | Recommended operational tolerance band for advisory thresholds |
| **90th Percentile Error ($P_{90}$)** | **±2.7351 °C** | Conservative bounds for critical extreme weather alerts |
| **95th Percentile Error ($P_{95}$)** | **±3.4649 °C** | Extreme outlier envelope |
| **90% Empirical Error Interval** | **[-3.0649 °C, +2.2351 °C]** | 5th to 95th percentile residual span |
| **95% Empirical Error Interval** | **[-3.6649 °C, +3.1351 °C]** | 2.5th to 97.5th percentile residual span |

---

## 2. API Response Schema with Uncertainty

Every temperature estimate returned by the backend includes explicit uncertainty bounds and calibration provenance:

```json
{
  "panchayat_id": "PANCHAYAT_001",
  "panchayat_name": "Maya Bazar",
  "forecast_timestamp": "2026-09-17T12:00:00Z",
  "temperature_celsius": 36.7,
  "uncertainty": {
    "expected_error_mae_c": 1.27,
    "confidence_interval_80_c": [34.7, 38.7],
    "confidence_interval_90_c": [33.6, 38.9],
    "coverage_percent": 80.0,
    "uncertainty_description": "estimated uncertainty based on frozen multi-region Indian validation"
  },
  "provenance": {
    "model_type": "CALIBRATED_ERA5_PHYSICAL_BASELINE",
    "calibration_offset_c": 0.7351,
    "source_dataset": "ECMWF ERA5 + 17 WMO Indian Surface Stations",
    "data_quality_status": "CALIBRATED_OPERATIONAL"
  }
}
```

---

## 3. Agronomic Risk Propagation

When evaluating crop risk (e.g., Rice flowering heat stress threshold = $38.0\ ^\circ\text{C}$):

1. **Definitive Stress**:
   - Forecast temperature $- P_{80}$ uncertainty exceeds threshold ($T_{\text{forecast}} - 1.96^\circ\text{C} \ge 38.0^\circ\text{C}$).
   - **Risk Status**: `HIGH_RISK` (High Confidence: $\ge 85\%$).
2. **Marginal / Probable Stress**:
   - Point forecast exceeds threshold, but lower uncertainty bound is below threshold ($T_{\text{forecast}} \ge 38.0^\circ\text{C}$ but $T_{\text{forecast}} - 1.96^\circ\text{C} < 38.0^\circ\text{C}$).
   - **Risk Status**: `MODERATE_RISK` (Warning: "Temperatures approaching critical boundary; monitor soil moisture").
3. **Insufficient Confidence**:
   - Weather record is stale, raw fallback is active, or uncertainty envelope exceeds $\pm 3.0^\circ\text{C}$.
   - **Risk Status**: `INSUFFICIENT_DATA` (Precautionary principle: No false-alarm chemical advice).
