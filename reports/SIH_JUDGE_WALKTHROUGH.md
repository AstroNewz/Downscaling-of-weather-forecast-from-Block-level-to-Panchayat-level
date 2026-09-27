# SIH 5-Minute Technical Judge Walkthrough Protocol

**Project**: AgroWeather — SIH PS 26074  
**Audience**: SIH Technical Judges, Ministry of Agriculture Evaluators  
**Execution Environment**: `http://localhost:5173` (Frontend) & `http://localhost:8000` (Backend API)  
**Total Duration**: Exactly 5 Minutes

---

## Walkthrough Timeline & Demonstration Script

### Minute 0:00 – 1:00: Live NWP Ingestion & Provenance Proof
1. **Open Dashboard (`http://localhost:5173`)**:
   - Point out the **Live Provenance Card** in the top-left section.
   - Show the pulsing emerald badge: `LIVE • EXTERNAL NWP`.
   - Point to provider identity: `Open-Meteo Operational NWP (certifi SSL)`.
   - Highlight the **Issued UTC**, **Retrieved UTC**, and **Live Data Age** (typically < 30 minutes).
2. **Hit "Refresh Live Forecast"**:
   - Show the loading spinner and instantaneous update of the `live_request_id` (e.g. `req_live_b271...`).
   - Demonstrate that the response headers strictly carry `Cache-Control: no-cache, no-store, must-revalidate` (zero stale browser caching).

---

### Minute 1:00 – 2:00: Geographic Differentiation & Topographical Downscaling
3. **Change Panchayat Selection**:
   - In the Panchayat dropdown, switch from **Chiraigaon** (Elevation: 85m) to **Baragaon** (Elevation: 92m) and **Pindra** (Elevation: 98m).
   - Show that coordinates immediately change:
     - Chiraigaon: `25.3500°N, 82.9500°E` ($27.09^\circ\text{C}$)
     - Baragaon: `25.4500°N, 82.8200°E` ($27.61^\circ\text{C}$)
     - Pindra: `25.5200°N, 82.7800°E` ($27.31^\circ\text{C}$)
   - Prove that zero hardcoded coordinates exist and temperatures vary according to local topography.
4. **Change Forecast Horizon (Date Attack)**:
   - Select "Tomorrow" and "Day 3".
   - Show the numerical weather forecast updating with date-specific atmospheric regimes.
   - Demonstrate that previous-day advisories do not leak into future dates.

---

### Minute 2:00 – 3:00: Dual-Inference Shadow Mode & Baselines
5. **Inspect Dynamic Shadow Comparison Card**:
   - Point to the side-by-side comparison:
     - **Certified Operational Baseline**: $T_{\text{calibrated}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$
     - **Dynamic Residual Model v2**: XGBoost micro-topographical residual.
   - Show the delta offset ($\Delta T \approx 0.15^\circ\text{C}$).
   - Explain why the Certified Baseline remains the primary operational standard: the model's nominal gain ($0.0971^\circ\text{C}$) falls within the physical uncertainty band of station PT100 sensors ($\pm 0.10^\circ\text{C}$ to $\pm 0.20^\circ\text{C}$).
   - Show the physical safety bounds active: $[-8.0^\circ\text{C}, +8.0^\circ\text{C}]$ with instant fallback.

---

### Minute 3:00 – 4:00: Agro-Advisory Provenance & Panchayat-to-Block Aggregation
6. **Inspect Emitted Agro-Advisories**:
   - Click on an active advisory (e.g. *Maize Tasseling Stage: Wind Lodging Caution*).
   - Point to the **Advisory Provenance Strip**:
     - `Model: DYNAMIC_V2`
     - `Provider: OPEN_METEO_OPERATIONAL_NWP`
     - `Forecast Time: [Current UTC]`
     - `Location: [Selected Panchayat]`
     - `Request ID: req_live_...`
   - Point out that under mild live weather conditions ($26.9^\circ\text{C}$), zero demo heat-stress warnings leaked into production.
7. **Show Panchayat-to-Block Aggregation**:
   - Highlight the block spatial statistics ($0.22^\circ\text{C}$ thermal variance across 3 Panchayats).
   - Demonstrate that block values are dynamically calculated from constituent spatial nodes, preserving area-weighted micro-topography.

---

### Minute 4:00 – 5:00: Scientific Governance & Honest Limitation Disclosure
8. **Navigate to Scientific Governance Tab (`/governance`)**:
   - Show the **Provider Health Matrix**:
     - `Open-Meteo`: LIVE (Green)
     - `IMD`: NOT CONFIGURED (Amber) — show that the system truthfully states that institutional API credentials (`IMD_API_KEY`) are required without faking credentials.
   - Show the **17-Station Multi-Region Validation Sample**:
     - Display the 6 validated agro-climatic zones across 23,949 genuine records.
     - Show the **South India Data Limitation Banner**: explains transparently that Peninsular India ISD records contained 0 valid observations.
   - Show the **Dynamic V2 8-Gate Scientific Promotion Matrix**:
     - Point out the 3 legitimately failed gates (Gate 1, Gate 2, Gate 3).
     - Conclude with the formal governance verdict: **`RETAIN_FOR_RESEARCH`** under **`CONTROLLED_PRODUCTION`**.
