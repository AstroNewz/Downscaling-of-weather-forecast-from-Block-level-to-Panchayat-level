# Dynamic Residual Model v2 — Controlled Production Cutover Specification
**Smart India Hackathon Problem Statement 26074 — Agro-Meteorological Downscaling**
**Release Target**: `CONTROLLED_PRODUCTION`  
**Cutover Date**: September 18, 2026  
**Primary Operational Model**: `Dynamic Residual Downscaling Model v2 (Candidate C)`  
**Certified Automatic Fallback**: `CERTIFIED_FALLBACK_BASELINE (T_coarse + 0.7351°C)`  

---

## 1. Context & Motivation for Controlled Production Cutover

Since the Phase 23/24 national validation, the Smart India Hackathon operational platform utilized the constant scalar calibration:

$$T_{\text{baseline}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$$

While this constant baseline provided unconditional stability and guaranteed zero risk of divergent extrapolation, it remains available as `CERTIFIED_FALLBACK_BASELINE`. Real atmospheric dynamics in heterogeneous terrains exhibit non-uniform local anomalies influenced by:
- Solar aspect and topographic slope
- Relative humidity and evaporative cooling
- Surface roughness and wind shear
- Elevation difference and adiabatic lapse rates

The **Dynamic Residual Downscaling Model v2** incorporates these physical parameters into an XGBoost gradient boosted decision tree architecture. This document specifies the controlled operational cutover where Dynamic Model v2 becomes the primary operational downscaling path under strict runtime safeguards with automatic, transparent fallback to the certified baseline.

---

## 2. Mathematical Formulation & Architecture

$$T_{\text{operational}}(t, x) = T_{\text{coarse}}(t, x) + \Delta T_{\text{operational}}(t, x)$$

### Primary Path: Dynamic Model v2
When all runtime safeguards pass:
$$\Delta T_{\text{operational}}(t, x) = f_{\text{XGBoost}}\Big(\mathbf{x}_{\text{weather}}(t, x), \mathbf{x}_{\text{terrain}}(x), \mathbf{x}_{\text{time}}(t)\Big)$$

Where:
- $\mathbf{x}_{\text{weather}} = \big[T_{\text{coarse}}, \text{RH}, U_{10}, \sin(\theta_{\text{wind}}), \cos(\theta_{\text{wind}}), P\big]$
- $\mathbf{x}_{\text{terrain}} = \big[z_{\text{obs}}, z_{\text{coarse}}, \Delta z, \Delta T_{\text{lapse}}, \sigma_{\text{slope}}, \sin(\alpha_{\text{aspect}}), \cos(\alpha_{\text{aspect}}), \text{LULC}, \phi, \lambda\big]$
- $\mathbf{x}_{\text{time}} = \big[\sin(2\pi h / 24), \cos(2\pi h / 24), \sin(2\pi d / 365.25), \cos(2\pi d / 365.25)\big]$

### Fallback Path: Certified Baseline v1
When any runtime safeguard check fails or operator triggers rollback:
$$\Delta T_{\text{operational}}(t, x) = +0.7351^\circ\text{C}$$

---

## 3. Important Scientific Disclosure: Research Performance vs Operational Deployment

We maintain strict scientific transparency:
- **Historical Benchmark Result**: In the Phase 24 frozen benchmark across 5,288 observations (August 11–31, 2024), Candidate C achieved a test MAE of `1.1690°C` vs Baseline MAE of `1.2661°C` (an improvement of `+0.0971°C`).
- **Research Promotion Gate Verdict**: Because the historical promotion criterion required $\Delta\text{MAE} \ge +0.1000^\circ\text{C}$ and LOSO mean $\le 1.40^\circ\text{C}$ (observed: `1.4304°C`), the gate verdict was recorded honestly and immutably as **`RETAIN_FOR_RESEARCH`**.
- **Controlled Operational Deployment**: The deployment of Dynamic Model v2 under `CONTROLLED_PRODUCTION` does *not* claim that historical validation thresholds were retroactively passed. Rather, it activates dynamic downscaling strictly bounded by multi-stage runtime safeguards that guarantee agronomic safety by falling back to the certified $+0.7351^\circ\text{C}$ baseline whenever uncertainty arises.

---

## 4. Multi-Stage Runtime Safeguards Architecture

Every operational request passes sequentially through 5 runtime gates before dynamic inference is accepted:

```
                  Live Weather NWP Feed
                           |
                           v
           [Gate 1: Meteorological QC Check]
           (Temp, RH, Wind in physical limits)
              /                         \
           PASS                         FAIL ---> [FALLBACK: +0.7351°C]
            |
            v
           [Gate 2: Freshness Verification]
           (Source timestamp age <= 180 min)
              /                         \
           PASS                         FAIL ---> [FALLBACK: +0.7351°C]
            |
            v
           [Gate 3: Feature Completeness]
           (All required weather & terrain vars)
              /                         \
           PASS                         FAIL ---> [FALLBACK: +0.7351°C]
            |
            v
           [Gate 4: OOD Operational Envelope]
           (Within Kharif 2024 training domain)
              /                         \
           PASS                         FAIL ---> [FALLBACK: +0.7351°C]
            |
            v
           [Candidate C Model Prediction]
           (Calculate raw model residual ΔT)
                           |
                           v
           [Gate 5: Residual Safety Check]
           (-8.0°C <= raw ΔT <= +8.0°C)
              /                         \
           PASS                         FAIL ---> [FALLBACK: +0.7351°C]
            |                                    (NO silent clipping)
            v
    T_operational = T_coarse + ΔT_dynamic
```

### Gate Definitions:
1. **Meteorological QC**: Input variables must be physically plausible ($-15^\circ\text{C} \le T \le 60^\circ\text{C}$, $0\% \le \text{RH} \le 100\%$, $0 \le U_{10} \le 60\text{ m/s}$, $P \ge 0$).
2. **Freshness Verification**: Operational forecasts older than 180 minutes are flagged as `STALE`, preventing stale NWP inputs from driving dynamic corrections.
3. **Feature Completeness**: Classifies each feature as `AVAILABLE`, `MISSING`, `INVALID`, or `STALE`. If any essential dynamic feature is unavailable, dynamic inference is marked `NOT_ELIGIBLE`.
4. **Out-of-Distribution (OOD) Envelope**: Validates inputs against empirical training extremes:
   - Temperature: $[5.0^\circ\text{C}, 52.0^\circ\text{C}]$
   - Relative Humidity: $[10.0\%, 100.0\%]$
   - Wind Speed: $[0.0\text{ m/s}, 28.0\text{ m/s}]$
   - Elevation: $[0\text{ m}, 2800\text{ m}]$
   - Slope: $[0^\circ, 35^\circ]$
   If out of distribution, model extrapolation is prohibited.
5. **Residual Safety Check**: Raw residual must satisfy $-8.0^\circ\text{C} \le \Delta T \le +8.0^\circ\text{C}$. **Violations are NEVER silently clipped**; a violation marks `safety_status = FAILED` and triggers baseline fallback.

---

## 5. Agricultural Advisory & GIS Integration

A single operational temperature ($T_{\text{operational}}$) is computed and propagated across the entire downstream stack:
1. **1-km Spatial Representation**: Local UTM metric grid (EPSG:32644 for Varanasi pilot).
2. **Panchayat Polygon Aggregation**: Area-weighted geometric intersection with Gram Panchayat boundaries.
3. **Crop Phenology & Risk Engine**:
   - Rice Heat Stress during Flowering Anthesis evaluates $T_{\text{operational\_max}} \ge 35.0^\circ\text{C}$.
   - Maize High Wind Lodging evaluates $U_{10} \ge 25\text{ km/h}$.
4. **Explainable Advisories**: Generated with complete provenance detailing whether $T_{\text{operational}}$ derived from Dynamic v2 or the Certified Baseline Fallback.

---

## 6. Rollout Configuration & Operator Rollback Protocol

An instant, zero-downtime configuration switch governs rollout:
- **Default Mode**: `ROLLOUT_MODE = "DYNAMIC_PRIMARY"`
- **Rollback Mode**: `ROLLOUT_MODE = "BASELINE_PRIMARY"`

### Rollback Execution:
Operators can instantly revert to the pure certified baseline via API without code edits:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/rollout-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "BASELINE_PRIMARY"}'
```
Response:
```json
{
  "success": true,
  "message": "Controlled production rollout mode successfully set to [BASELINE_PRIMARY].",
  "data": {
    "rollout_mode": "BASELINE_PRIMARY",
    "model_operational_status": "CONTROLLED_PRODUCTION",
    "active_model": "CERTIFIED_BASELINE_V1"
  }
}
```

---

## 7. Operational Immutability & No Online Retraining

Under no circumstances does incoming live operational data modify model weights, scaling factors, or calibration constants. The XGBoost candidate model artifact is completely frozen:
- File: `models/candidates/temperature_residual/dynamic_temperature_residual_v2/xgboost_model.json`
- SHA256: `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294`
- Certified Fallback Baseline Offset: `+0.7351°C` (Immutable)
