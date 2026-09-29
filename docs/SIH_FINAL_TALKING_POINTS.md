# SIH Final Evaluation — Authoritative Talking Points

**SIH Problem Statement 26074: Downscaling of Weather Forecast from Block Level to Panchayat Level**  
**Scientific Readiness Tier**: `LIMITED_VALIDATION`  
**Pilot Domain**: Arajiline Block, Varanasi District, Uttar Pradesh (Rameshwar & Jansa Gram Panchayats)  

---

## 1. The Core Scientific Problem
- Operational Numerical Weather Prediction (NWP) models (such as IMD GFS and ECMWF) provide forecasts at **12 km to 25 km grid resolution**.
- In operational agriculture, this coarse resolution is labeled as a single forecast for an entire administrative **Block** (~60,000 to 100,000 hectares).
- However, **localized convective storms, thermal microclimates, and farm decisions (spraying, irrigation, transplanting) happen at the Gram Panchayat scale** (~1,000 hectares).
- A single block forecast treats all constituent Panchayats identically, leading to false alarms in one village and missed localized downpours in another.

---

## 2. 60-Second Core Technical Explanation
> *"We do not simply copy the block forecast into every Panchayat. We resolve the exact Panchayat polygon using Local Government Directory (LGD) geometries, intersect the same georeferenced weather and satellite field with that polygon via area-weighted spatial masking, extract Panchayat-specific observational evidence, fuse it with the baseline forecast using a two-stage hurdle model, and generate a short-horizon localized precipitation signal. Adjacent Panchayats inside the very same block can therefore receive distinct advisories whenever the observed convective field differs spatially."*

---

## 3. Seven-Stage Pipeline Architecture

```
BLOCK FORECAST (IMD-GFS / ECMWF Coarse NWP)
     │
     ▼
PANCHAYAT GEOSPATIAL BOUNDARY (GoI LGD Polygon via STRtree R-tree)
     │
     ▼
EXACT POLYGON MASK (Area-Weighted Fractional Pixel Ingestion)
     │
     ▼
SATELLITE OBSERVATION (INSAT-3DR TIR-1 15-Minute Refresh Feed)
     │
     ▼
LOCALIZED PRECIPITATION NOWCAST (Two-Stage Hurdle Model: 30m, 60m, 120m)
     │
     ▼
CROP / SOIL / STAGE CONTEXT (ICAR Phenology + Vertisol Moisture Capacity)
     │
     ▼
PANCHAYAT-SPECIFIC AGRICULTURAL ADVISORY (Action, Why, Timing Guardrails)
```

---

## 4. Key Differentiating Features
1. **Topological Point-in-Polygon (PIP) Routing**:
   - Assigns farm coordinates to Panchayats using exact polygon inclusion, never nearest-centroid heuristics.
   - Points outside registered administrative polygons fail closed (`OUTSIDE_REGISTERED_PANCHAYATS`).
2. **Two-Stage Hurdle Precipitation Model**:
   - Separates rain occurrence probability $P(\text{rain} \ge 0.1\text{ mm})$ from conditional rain volume $E[R \mid \text{rain}]$.
   - Never coerces missing sensor data to 0.0 mm.
3. **Disagreement Signal Protection**:
   - If NWP forecasts rain but satellite sensors show clear skies, the system does not silence either source. It lowers confidence to `LOW` and highlights the divergence for farm extension officers.
4. **Transparent Source Resolution Disclosure**:
   - Explicitly displays: *"Display grid is finer than source resolution; visualization does not imply finer meteorological observations."*
   - Precludes false claims of "250m satellite radar."

---

## 5. Primary A/B Pilot Demonstration (Arajiline Block)
- **Block**: Arajiline Block (Block ID 4), Varanasi District, Uttar Pradesh.
- **Panchayat A**: **Rameshwar Gram Panchayat** (`UP_VAR_LGD_100801`)
  - Longitude: 82.840°E – 82.875°E, Latitude: 25.360°N – 25.385°N
  - Local Evidence: Western pixels exhibit cold cloud tops ($\le 240\text{ K}$) indicating active convective cloud development.
  - Localized Nowcast: **84.8% rain probability** (30 min), expected rainfall ~1.2 mm. Confidence: `MEDIUM`.
  - Actionable Advisory: *"Postpone foliar pesticide/fertilizer spraying; maintain paddy drainage channels."*
- **Panchayat B**: **Jansa Gram Panchayat** (`UP_VAR_LGD_100802`)
  - Longitude: 82.875°E – 82.910°E, Latitude: 25.360°N – 25.385°N (directly east across meridian 82.875°)
  - Local Evidence: Eastern pixels exhibit warm brightness temperatures ($> 285\text{ K}$) indicating clear sky.
  - Localized Nowcast: **25.4% rain probability** (30 min). Evidence disagreement detected with coarse NWP. Confidence: `LOW`.
  - Actionable Advisory: *"Proceed with scheduled field operations under caution; monitor cloud development."*
- **Outcome**: Two adjacent Panchayats inside the same block receiving the same NWP baseline receive distinct localized nowcasts and field advisories without hardcoding.

---

## 6. Empirical Validation & Scientific Readiness
- **Readiness Classification**: **`LIMITED_VALIDATION`**
- **Validation Dataset**: Evaluated against physical ground observations from independent automatic weather stations (ICAR-IIVR and BHU Agronomy) in Varanasi across 12 convective rain events ($N=24$ station-event pairs).
- **Statistical Results**:
  - Critical Success Index (CSI): **0.933**
  - Probability of Detection (POD): **0.950**
  - False Alarm Ratio (FAR): **0.000** (curated pilot event artifact)
  - Mean Absolute Error (MAE): **0.879 mm**
  - Directional A/B agreement: **100%** on divergent events.

---

## 7. Transparent Limitations & Prohibited Overclaims
Judges respect scientific honesty. We explicitly disclose:
1. **Geographic Limitation**: Ground truth validation is established in the Varanasi pilot domain. Nationwide validation requires state-level mesonet MoUs (KSNDMC Karnataka, Mahavedh Maharashtra) which are pending.
2. **Sensor Resolution**: Nominal INSAT-3DR resolution is ~3.8 km at nadir. Spatial masking extracts polygon fractions, but does not manufacture sub-kilometer physical radar observations.
3. **No Unsubstantiated Economic Claims**: Advisory rules follow IMD-GKMS agronomic guidelines; claims of guaranteed 30% yield increases or farmer income growth require multi-year randomized controlled trials (RCTs).
