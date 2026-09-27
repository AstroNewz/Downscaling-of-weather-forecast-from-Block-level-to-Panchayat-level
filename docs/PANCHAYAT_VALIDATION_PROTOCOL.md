# Panchayat-Scale / Fine-Scale Meteorological Validation Protocol
## AgroWeather / SIH Problem Statement 26074
### Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services

**Standard Operating Procedure (SOP) & Scientific Specification**  
**Document Code:** `AGY-VAL-PROTO-2026-V1`  
**Governance State:** Governed & Frozen Scientific Protocol  

---

## 1. Objective and Scientific Scope

This protocol establishes the rigorous, fail-closed experimental standards for validating downscaled temperature and agro-meteorological variables at **Panchayat / sub-5 km spatial scales**.

### Foundational Scientific Invariant:
$$\text{Forecast Location Resolution} \neq \text{Observational Validation Resolution}$$

Executing mathematical inference at arbitrary 1-km coordinates (e.g. Maya Bazar Gram Panchayat centroid) produces a fine-scale downscaled product, but *does not constitute scientific validation* until physical measurements are observed at that density.

---

## 2. Formal Validation Readiness Levels (Levels 1 to 6)

Validation readiness across any Indian geographic domain is formally categorized into six hierarchical levels:

| Validation Level | Machine-Readable Code | Formal Definition | Scientific Capability |
|---|---|---|---|
| **Level 1** | `LEVEL_1_NO_IN_SITU` | Zero independent in-situ weather stations within a 50-km radius of the target domain. | Unvalidated domain; regional reanalysis estimates only. |
| **Level 2** | `LEVEL_2_SINGLE_MACRO` | Exactly one active physical weather station within 25–150 km. | Regional macro-calibration only; cannot validate spatial gradients or intra-block microclimates. |
| **Level 3** | `LEVEL_3_SUB_10KM_PAIR` | $\ge 2$ independent physical stations separated by $\le 10\text{ km}$. | Meso-scale block-level spatial gradient validation. |
| **Level 4** | `LEVEL_4_SUB_5KM_PAIR` | $\ge 2$ independent physical stations separated by $\le 5\text{ km}$. | Panchayat-boundary scale spatial gradient validation. |
| **Level 5** | `LEVEL_5_SUB_5KM_AGRI` | $\ge 2$ independent physical stations located inside active agricultural cropping fields within $\le 5\text{ km}$. | Agricultural canopy microclimatic validation. |
| **Level 6** | `LEVEL_6_INTRA_PANCHAYAT` | $\ge 2$ independent physical agricultural stations located *within the same or adjacent Gram Panchayat boundaries*. | Full intra-Panchayat micro-zone validation. |

> [!CRITICAL]
> **Anti-Inflation Rule:** A Panchayat cannot be classified into Level 3, 4, 5, or 6 based on downscaled model predictions, satellite proxies, or interpolated points. Promotion requires genuine physical thermometer hardware in the ground.

---

## 3. Minimum Observational Data Requirements

To qualify for evaluation at Levels 3 to 6, incoming observational datasets must satisfy four strict validation criteria:

### 3.1 Spatial Criteria
1. **Precise Geodetic Coordinates:** WGS84 latitude and longitude recorded to $\ge 4$ decimal places ($\approx 11\text{ m}$ precision).
2. **Station Independence:** Stations must have independent physical sensor masts, independent loggers, and distinct site footprints ($\ge 100\text{ m}$ separation). Multiple sensors on the same tower do not constitute spatial validation pairs.
3. **Panchayat Mapping:** Explicit assignment to State, District, Block, and LGD Gram Panchayat Code.
4. **Coarse Cell Assignment:** Exact determination of parent $0.25^\circ \times 0.25^\circ$ ERA5/NWP grid cell center and distance to cell center.

### 3.2 Temporal Criteria
1. **Standardized Timestamp:** UTC timestamps formatted according to ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`).
2. **Synchronized Sampling:** Simultaneous hourly sampling matched to exact UTC hour ($\pm 15\text{ minutes}$ tolerance). Observations $>15\text{ minutes}$ apart cannot be paired for spatial gradient evaluation.
3. **Minimum Temporal Density:** Minimum 80% valid hourly observations per 24-hour cycle.
4. **Continuous Duration:** Minimum 30 consecutive days for single-season evaluation; minimum 90 days for seasonal monsoon evaluation.

### 3.3 Meteorological & Physical Criteria
1. **Instrument Standard:** WMO Class-1 / IMD AWS equivalent RTD (PT100) or high-precision thermistor housed inside an aspirated or multi-plate radiation shield at standard height ($1.5\text{ m}$ to $2.0\text{ m}$ above ground).
2. **Essential Variable:** 2m dry-bulb air temperature ($T_{\text{ambient}}$ in ${^\circ}\text{C}$, precision $\pm 0.1{^\circ}\text{C}$, accuracy $\pm 0.2{^\circ}\text{C}$).
3. **Supporting Covariates (where equipped):**
   - 2m Relative Humidity ($\text{RH}$ in $\%$, accuracy $\pm 3\%$)
   - 10m Wind Speed ($U_{10}$ in $\text{m/s}$) and Wind Direction ($\theta$ in degrees)
   - Precipitation ($P$ in $\text{mm}$, tipping bucket resolution $0.5\text{ mm}$)
   - Barometric Pressure ($P_{\text{sfc}}$ in $\text{hPa}$)
   - Sub-surface Soil Temperature at $5\text{ cm}$ and $10\text{ cm}$ depth.

### 3.4 Site Context Classification
Every station must be classified into one of the following authoritative site categories:
- `AIRPORT`: Civil or military aerodrome runway/tarmac environment.
- `URBAN`: Paved city center with high building density and artificial heat flux.
- `SUBURBAN`: Residential/institutional campus with mixed vegetation and asphalt.
- `RURAL`: Non-urban agrarian hinterland.
- `AGRICULTURAL`: Sited directly within or adjacent to cultivated cropland/pasture.
- `FOREST`: Sited beneath or adjacent to continuous tree canopy.
- `COASTAL`: Situated $\le 5\text{ km}$ from open marine sea or ocean shoreline.
- `WETLAND`: Situated within permanent backwaters, estuaries, or marshlands.
- `MOUNTAIN`: Situated on steep orographic ridges ($\text{slope} \ge 15^\circ$).
- `OTHER`: Unclassified / unverified site footprint.

---

## 4. Minimum Statistical Sample Requirements

To prevent reporting statistically meaningless metrics on sparse data, the following thresholds are enforced:

| Evaluation Scope | Minimum Station Count | Minimum Simultaneous Observations | Minimum Duration | Rule if Threshold Not Met |
|---|---|---|---|---|
| **Station-Pair Validation** | 2 independent stations | 100 synchronized hours | 10 active days | Output `INSUFFICIENT_OBSERVATIONS` |
| **Spatial Cluster Validation** | $\ge 2$ independent stations | 500 synchronized hours | 30 active days | Output `INSUFFICIENT_OBSERVATIONS` |
| **Seasonal Holdout Validation** | $\ge 5$ stations in cluster | 2,000 synchronized hours | 1 full season (90 days) | Output `SEASONAL_EVALUATION_INCOMPLETE` |
| **Panchayat-Scale Claim** | $\ge 2$ agricultural stations | 500 synchronized hours | 30 active days | Claim status remains `NOT_SUPPORTED` |
| **Strong Panchayat-Scale Claim**| $\ge 3$ agricultural stations | 1,500 synchronized hours | 90 active days | Claim status remains `NOT_SUPPORTED` |
| **Plot/Field-Scale Claim** | Multi-point micro-array | Dedicated flux experiment | Continuous growing cycle | Claim status remains `NOT_SUPPORTED` |

---

## 5. Mathematical Validation Experiments

When authorized observational datasets are ingested, the runner executes four mandatory mathematical evaluations:

### 5.1 Model Comparison Framework
For every timestamp $t$ and station $i$, evaluate four parallel estimates:
1. **Observation ($T_{\text{obs}, i}(t)$):** Genuine physical ground truth thermometer measurement.
2. **Raw Coarse NWP ($T_{\text{coarse}}(t)$):** Interpolated coarse reanalysis/forecast ($0.25^\circ$).
3. **Certified Baseline ($T_{\text{base}, i}(t)$):** Frozen production baseline:
   $$T_{\text{base}, i}(t) = T_{\text{coarse}}(t) + 0.7351^\circ\text{C}$$
4. **Dynamic Residual V2 ($T_{\text{dyn}, i}(t)$):** Topographic XGBoost candidate:
   $$T_{\text{dyn}, i}(t) = T_{\text{coarse}}(t) + \text{clamp}\left(f_{\text{XGB}}(\mathbf{x}_i, t), -8.0, +8.0\right)$$

### 5.2 Pairwise Spatial Gradient Test
For any station pair $(i, j)$ at simultaneous timestamp $t$:
$$\Delta T_{\text{obs}}(i, j, t) = T_{\text{obs}, j}(t) - T_{\text{obs}, i}(t)$$
$$\Delta T_{\text{base}}(i, j, t) = T_{\text{base}, j}(t) - T_{\text{base}, i}(t)$$
$$\Delta T_{\text{dyn}}(i, j, t) = T_{\text{dyn}, j}(t) - T_{\text{dyn}, i}(t)$$

Gradient Error:
$$\epsilon_{\text{base}}(i, j, t) = \left|\Delta T_{\text{base}}(i, j, t) - \Delta T_{\text{obs}}(i, j, t)\right|$$
$$\epsilon_{\text{dyn}}(i, j, t) = \left|\Delta T_{\text{dyn}}(i, j, t) - \Delta T_{\text{obs}}(i, j, t)\right|$$

### 5.3 Dedicated Same-ERA5-Cell Test
When multiple independent stations fall within the same $0.25^\circ \times 0.25^\circ$ ERA5 cell:
- **Certified Baseline Invariant Property:** Because $T_{\text{coarse}}$ is constant within the cell:
  $$\Delta T_{\text{base}}(i, j, t) = 0.0000^\circ\text{C} \quad \implies \quad \sigma^2_{\text{within}}(\text{base}) = 0.0000^\circ\text{C}^2$$
  $$\text{Baseline Gradient Error} = \left|0.0 - \Delta T_{\text{obs}}(i, j, t)\right| = \left|\Delta T_{\text{obs}}(i, j, t)\right|$$
- **Dynamic V2 Property:** Evaluates whether local terrain features (elevation difference, slope, aspect) accurately capture $\Delta T_{\text{obs}}$. Dynamic V2 only receives scientific credit if:
  $$\text{MAE}(\epsilon_{\text{dyn}}) < \text{MAE}(\epsilon_{\text{base}})$$

### 5.4 Agricultural vs Airport Siting Test
Paired analysis between collocated rural agricultural stations and aerodrome synoptic stations to quantify tarmac thermal re-radiation and daytime sensible heat flux bias.

---

## 6. Fail-Closed Error States

The validation pipeline enforces zero-tolerance fail-closed reporting:
- Source firewalled or unreachable: Record `ACCESS_RESTRICTED`.
- Sample size below threshold: Record `INSUFFICIENT_OBSERVATIONS`.
- Station coordinates absent or vague: Record `PANCHAYAT_MAPPING_UNAVAILABLE`.
- Physical mast collocated on same tower: Record `INDEPENDENCE_UNVERIFIED`.
- Timestamps unaligned: Record `TEMPORAL_ALIGNMENT_FAILED`.
- Any synthetic or interpolated substitution attempt: Immediate **FATAL AUDIT FAILURE**.
