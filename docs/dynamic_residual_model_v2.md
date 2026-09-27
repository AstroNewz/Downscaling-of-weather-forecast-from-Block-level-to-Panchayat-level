# Dynamic Residual Downscaling Model v2 — Architectural & Operational Specification

## 1. Overview & Objective

The **Dynamic Residual Downscaling Model v2** is a research-grade gradient boosted decision tree (XGBoost) model designed to capture spatio-temporal, meteorological, and topographic dependencies in coarse numerical weather prediction (ERA5 / IMD NWP) residual errors.

### Production Baseline Separation
- **Production Baseline**: $T_{\text{calibrated}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$ (certified, tamper-evident, invariant).
- **Research Candidate**: $\Delta T_{\text{dynamic}}(t, x) = f(\mathbf{x})$ with $[-8.0^\circ\text{C}, +8.0^\circ\text{C}]$ physical safety guardrail.
- **Current Governance Status**: `RESEARCH_ONLY`.

---

## 2. Mathematical Formulation

$$T_{\text{dynamic}}(t, x) = T_{\text{coarse}}(t, x) + \Delta T_{\text{dynamic}}(t, x)$$

where:

$$\Delta T_{\text{dynamic}}(t, x) = \text{clamp}\left( \sum_{k=1}^K f_k(\mathbf{x}(t, x)), -8.0, +8.0 \right)$$

### Input Feature Vector $\mathbf{x}(t, x)$
1. **Atmospheric State**:
   - $T_{\text{coarse}}$: Coarse 2m temperature (°C)
   - $\text{RH}$: Relative humidity (%)
   - $U_{10}$: Wind speed at 10m (m/s)
   - $\sin(\theta_{\text{wind}}), \cos(\theta_{\text{wind}})$: Cyclical wind direction components
   - $P$: Surface precipitation (mm)
2. **Temporal Cycles**:
   - $\sin(2\pi h / 24), \cos(2\pi h / 24)$: Diurnal hour encoding
   - $\sin(2\pi d / 365.25), \cos(2\pi d / 365.25)$: Seasonal day-of-year encoding
3. **Static Geography & Relief**:
   - $z_{\text{obs}}$: Local surface elevation (meters ASL)
   - $z_{\text{coarse}}$: Coarse grid model elevation (meters ASL)
   - $\Delta z = z_{\text{obs}} - z_{\text{coarse}}$: Elevation relief offset
   - $\Delta T_{\text{lapse}} = -0.0065 \times \Delta z$: Standard environmental adiabatic lapse rate adjustment (°C)
   - $\sigma_{\text{slope}}$: Surface slope inclination (degrees)
   - $\sin(\alpha_{\text{aspect}}), \cos(\alpha_{\text{aspect}})$: Solar terrain aspect orientation
   - $\text{LULC}$: ESA WorldCover land use / land cover code
   - $\phi, \lambda$: Geographic latitude and longitude
4. **Physical Interactions**:
   - $T_{\text{coarse}} \times (\text{RH} / 100.0)$: Evaporative cooling / wet-bulb proxy
   - $T_{\text{coarse}} \times \sin(2\pi h / 24)$: Solar radiation diurnal amplitude proxy
   - $\Delta T_{\text{lapse}} \times (1.0 + U_{10} / 5.0)$: Wind-sheared thermal boundary layer coupling

---

## 3. Architectural Design & Runtime API

### Backend Integration
- **Service**: `app.services.dynamic_downscaling_service.DynamicDownscalingService`
- **Endpoints**:
  - `POST /api/v1/research/dynamic-downscaling`: Compute live dynamic residual with guardrail check.
  - `GET /api/v1/research/diagnostic`: Inspect candidate model status, parameter hashes, and governance audit scores.
  - `POST /api/v1/research/compare`: Side-by-side comparison of Candidate A (+0.7351°C) vs Dynamic Model v2.

### Safety Guardrail Implementation
```python
raw_residual = float(model.predict(feature_matrix)[0])
is_clamped = raw_residual < -8.0 or raw_residual > 8.0
final_residual = max(-8.0, min(8.0, raw_residual))
guardrail_status = "CLAMPED" if is_clamped else "PASS"
```

---

## 4. Verification and Governance Traceability
- Training artifacts saved in: `models/candidates/temperature_residual/dynamic_temperature_residual_v2/`
- Checksums recorded in: `reports/dynamic_residual_v2_manifest.json`
- Production pipeline remains protected against unauthorized promotion.
