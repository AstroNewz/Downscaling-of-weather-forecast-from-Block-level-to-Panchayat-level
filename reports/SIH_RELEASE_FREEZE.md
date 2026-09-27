# SIH Scientific Release Freeze Protocol

**Project**: AgroWeather — SIH PS 26074  
**Freeze Timestamp**: `2026-09-25T08:20:00Z`  
**Git Release Commit**: `b88552421dabf38ba927060cd5e359a923af85e7`  
**Release Classification**: **`SIH_RELEASE_READY_WITH_LIMITATIONS`**

---

## 1. Release Invariants & Immutable Baselines

The following parameters and constraints are frozen for the Smart India Hackathon final evaluation and cannot be altered without violating scientific governance:

1. **Certified Baseline Model Invariant**:
   $$T_{\text{calibrated}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$$
   - Fused exclusively from $N=14,418$ training records (Kharif June 1 – July 25, 2024).
   - Artifact SHA-256: `3dcad5fbfd060d47ad9cbf1ec9cbe0df8c99da050e0d5a3ef2c3f76906ea1941`.
   - Production Status: **Active Operational Production Standard**.

2. **Dynamic Residual Model v2 Governance**:
   - Model Checksum (SHA-256): `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294`.
   - Scientific Decision: **`RETAIN_FOR_RESEARCH`**.
   - Deployment State: **`CONTROLLED_PRODUCTION`** (Shadow mode with dual inference).
   - Non-negotiable gates: Fails Gate 1 ($0.0971^\circ\text{C} < 0.1000^\circ\text{C}$), Gate 2 ($1.4304^\circ\text{C} > 1.4000^\circ\text{C}$), and Gate 3 ($0.1898^\circ\text{C} > 0.1500^\circ\text{C}$).
   - Sensor Noise Floor: PT100 PRT instrument noise ($\pm 0.10^\circ\text{C}$ to $\pm 0.20^\circ\text{C}$) exceeds nominal model improvement.

3. **Weather Provider Truthfulness**:
   - Operational Live Provider: `OPEN_METEO_OPERATIONAL_NWP` via verified certifi SSL.
   - IMD Status: Strictly **`NOT_CONFIGURED`**. Zero simulated or fake credentials permitted.
   - Demo Provider: 100% deterministic offline canonical pilot fixtures.

4. **Nationwide Validation Scope**:
   - Sample Size: 17 WMO synoptic stations across 6 physiographic regimes (23,949 genuine records).
   - Permitted Claim: `"NATIONWIDE MULTI-REGION VALIDATION COMPLETED; COVERAGE LIMITATIONS REMAIN"`.
   - Prohibited Claim: Any phrasing asserting unconstrained all-India accuracy certification.
   - Data Limitation: South / Peninsular India public ISD records contained 0 valid observations.

---

## 2. Integrity Lock & System Freezing Checklist

| Vector | Frozen Value | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Model Checksum** | `d75aeb2ac895666fd981ee7ead29da36f8279215f6279331d0dca084ceadb294` | SHA-256 hash | **LOCKED** |
| **Baseline Offset** | `+0.7351 °C` | Unit assertion & config | **LOCKED** |
| **Promotion Gate Thresholds** | $\ge 0.1000^\circ\text{C}, \le 1.4000^\circ\text{C}, \le 0.1500^\circ\text{C}$ | Service definition | **LOCKED** |
| **Safety Clamping** | $[-8.0^\circ\text{C}, +8.0^\circ\text{C}]$ | `OperationalSafeguardsEngine` | **LOCKED** |
| **Fallback Target** | $T_{\text{coarse}} + 0.7351^\circ\text{C}$ | `LivePredictionService` | **LOCKED** |
| **IMD Status** | `NOT_CONFIGURED` | Health check endpoint | **LOCKED** |
| **Regression Suite** | 291 / 291 passed (100%) | `pytest` runner | **LOCKED** |
| **Frontend Production Build** | 0 TS errors, 0 build errors | `vite build` | **LOCKED** |
