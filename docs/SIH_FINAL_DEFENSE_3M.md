# SIH Technical Defense: 3-Minute Comprehensive Presentation
**Problem Statement**: 26074 (Downscaling Weather Forecast from Block to Panchayat Level)  
**Scientific Readiness Classification**: `LIMITED_VALIDATION` (Pilot Domain)  
**Spoken Target Duration**: 180 seconds (~450 words)

---

### Minute 1: The Problem & The Backend Architecture

#### 1. What problem are we solving?
India’s national weather models (IMD-GFS at 0.25° and NCMRWF-IMDAA at 12 km) issue forecasts at the Block scale. Within a single 25 km × 25 km grid cell, dozens of Gram Panchayats experience vastly different microclimates. A summer convective storm can inundate one village while leaving the neighboring village completely dry. When farmers receive generic block-level forecasts, they either spray pesticides before an unexpected downpour washes them away, or withhold irrigation during a false alarm. Our platform bridges this spatial gap from Block to Gram Panchayat.

#### 2. What exactly happens in the backend?
When a farmer opens our app or an official queries a Panchayat:
1. **Topological Boundary Routing**: The user's coordinates are evaluated against authoritative Local Government Directory (LGD) polygons via an STRtree spatial index. Point-in-polygon resolution occurs in under one millisecond with zero centroid-distance approximation.
2. **Dual Meteorological Processing**:
   - **Temperature**: Coarse NWP temperature is adjusted using our certified national baseline calibration ($T_{\text{calibrated}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$).
   - **Precipitation Nowcast**: A two-stage hurdle model fuses the coarse NWP rain forecast with localized satellite infrared observations.
3. **Agronomic Advisory Generation**: Calibrated probabilities feed IMD-GKMS rules to produce structured **Action / Why / Timing** advisories.

---

### Minute 2: Demonstration & Sensor Integration

#### 3. Why does Panchayat A differ from Panchayat B?
In our demonstrated pilot in Arajiline Block (Varanasi District):
- Both **Rameshwar Gram Panchayat** (`UP_VAR_LGD_100801`) and **Jansa Gram Panchayat** (`UP_VAR_LGD_100802`) receive the **exact same block-level forecast**: 2.5 mm rain, 35% probability.
- However, our spatial masking engine intersects their actual polygon footprints with real 4-km INSAT-3DR thermal infrared imagery.
- Over Rameshwar, satellite brightness temperature is **231.85 K** ($-41.3^\circ\text{C}$), identifying deep convective cloud tops. Localized 30-min rain probability surges to **84.8%**, triggering an advisory to **Pause Spraying and Harvesting**.
- Over Jansa, 6 km east, brightness temperature is **278.45 K** ($+5.3^\circ\text{C}$), indicating clear ground. Rain probability drops to **25.4%**, triggering an **Evidence Disagreement Flag** and advising farmers to proceed with caution.

#### 4. Where does satellite data fit?
Satellite infrared data is an **observational convective proxy**, not a rainfall gauge. We ingest the 10.8 µm thermal IR channel every 15 minutes to track cloud-top cooling rates and spatial extent. Cold cloud tops indicate strong vertical updrafts capable of producing localized rain.

#### 5. What happens when radar is unavailable?
Radar is treated strictly as an optional enhancement. If Doppler radar is unavailable or beam-blocked, the system operates in `NWP_SATELLITE` mode, degrades confidence from `HIGH` to `MEDIUM` or `LOW`, and flags unestimable precipitation amounts as `null` rather than generating false precision. The pipeline never fabricates radar data.

---

### Minute 3: Scientific Validation & Honest Limitations

#### 6. How is precipitation validated?
We conducted an independent validation against real agro-meteorological research mesonet stations (ICAR-IIVR Jakhini and BHU Agricultural Farm) across 12 curated weather episodes (24 station-event pairs). 
- Historical training stations were strictly quarantined to prevent data leakage.
- Our model achieved a Probability of Detection of **0.933** and a Critical Success Index of **0.933** across these episodes, with **100% directional accuracy** on divergent convective events.

#### 7. What are the current limitations?
We do not make inflated hackathon claims:
- **Geographic Scope**: Our validation is established in the Varanasi pilot domain. We do not claim nationwide validation; our system status is **`LIMITED_VALIDATION`**.
- **Nationwide Scale-Up**: Scaling to India’s 250,000 Panchayats requires institutional boundary integration with the Ministry of Panchayati Raj and mesonet data-sharing MoUs with state agencies like KSNDMC in Karnataka and Mahavedh in Maharashtra.
- **Economic Claims**: Our advisories follow IMD-GKMS guidelines; we do not claim unproven 30% yield increases.

**In conclusion: AgroWeather provides a transparent, scientifically honest, and topologically verified downscaling platform that turns regional forecasts into actionable village-level intelligence.**
