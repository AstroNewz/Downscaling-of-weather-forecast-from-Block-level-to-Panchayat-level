# SIH Final Evaluation — 3-Minute Live Demo Script

**Problem Statement 26074**: Downscaling Weather Forecast from Block Level to Panchayat Level  
**Total Target Duration**: 3 Minutes (180 Seconds)  
**Presenter Roles**: Technical Lead (Screen & Architecture) + Agronomic Specialist (UI & Advisories)  

---

### [0:00 – 0:30] Phase 1: The Problem — The 25-km NWP Resolution Deficit
*(Screen: Show the nationwide map overview or opening slide with block-level forecast)*

**Speaker 1:**  
> *"Good morning, respected judges. In India today, IMD and NCMRWF issue operational numerical weather forecasts at the Block scale—a 12 to 25 kilometer grid cell encompassing over 50,000 hectares.  
> 
> But farming decisions—whether to spray a costly fungicide, postpone pulse irrigation, or protect flowering paddy—happen at the Gram Panchayat scale of roughly 1,000 hectares.  
> 
> A block forecast paints the entire block with one broad brush. If a localized convective cloud dumps rain over the western edge, farmers in the east receive a false alarm, while farmers in the west get caught completely unprepared."*

---

### [0:30 – 1:00] Phase 2: The Core Spatial Architecture — Block to Polygon
*(Action: Navigate to Panchayat Explorer / Map, select "Arajiline Block" in Varanasi District)*

**Speaker 2:**  
> *"Our solution does not simply copy-paste or linearly interpolate block forecasts.  
> 
> First, we ingest official Local Government Directory (LGD) boundaries and resolve user GPS coordinates using exact topological Point-in-Polygon containment via an R-tree spatial index.  
> 
> Second, we ingest 15-minute INSAT-3DR geostationary satellite observational rasters.  
> 
> Third, we perform area-weighted geometric spatial masking. Each Panchayat polygon extracts the exact fractional pixels that overlap its administrative boundaries.  
> 
> The polygon defines the administrative boundary; the underlying observation field defines the meteorological detail."*

---

### [1:00 – 1:45] Phase 3: The Live A/B Panchayat Demonstration
*(Action: In Arajiline Block, click on **Panchayat A: Rameshwar Gram Panchayat**)*

**Speaker 1:**  
> *"Here is our verified pilot demonstration in Arajiline Block, Varanasi.  
> 
> We select **Panchayat A: Rameshwar Gram Panchayat**. Both Panchayats in this block share the identical IMD-GFS baseline forecast: 2.5 mm rain, 35% probability.  
> 
> But looking at the 15-minute INSAT-3DR thermal infrared feed, the western pixels over Rameshwar exhibit cold cloud tops at 235 Kelvin. Our two-stage hurdle nowcast generates an **84.8% rain probability** within 30 minutes.  
> 
> Now, we switch to neighboring **Panchayat B: Jansa Gram Panchayat**, located immediately adjacent to the east across meridian 82.875° E."*

*(Action: Click on **Panchayat B: Jansa Gram Panchayat**; map boundary transitions from Rameshwar to Jansa)*

**Speaker 1:**  
> *"Notice the map boundary transitions cleanly to Jansa's canonical polygon. Jansa shares the exact same block baseline. But over Jansa's polygon, the satellite indicates warm, clear skies at 292 Kelvin.  
> 
> The nowcast produces a **25.4% rain probability** and flags an operational **evidence disagreement banner** because satellite observations diverge from the coarse baseline.  
> 
> Two neighboring Panchayats in the exact same block receive distinct, scientifically grounded weather evidence."*

---

### [1:45 – 2:15] Phase 4: Downstream Agricultural Advisory Integration
*(Action: Toggle to "Farmer View" and highlight the Advisory Card)*

**Speaker 2:**  
> *"Weather data alone is useless to a farmer unless translated into protective agronomic action.  
> 
> In **Farmer View**, we eliminate technical jargon and provide three clear outputs: **Action**, **Why**, and **Timing**.  
> 
> For **Rameshwar**, where convective rain is imminent:  
> - **Action**: Postpone foliar pesticide spraying and nitrogen top-dressing.  
> - **Why**: Rain washout risk exceeds 80%, wasting expensive inputs.  
> - **Timing**: Hold operations for the next 2 hours until the cell passes.  
> 
> For **Jansa**, where skies are clear:  
> - **Action**: Continue scheduled field intercultural operations with operational monitoring.  
> 
> Every advisory strictly adheres to ICAR and IMD-GKMS agronomic guardrails."*

---

### [2:15 – 2:45] Phase 5: Empirical Ground-Truth Validation
*(Action: Navigate to Technical / Scientific Governance page)*

**Speaker 1:**  
> *"We do not present hypothetical numbers. Under Task 8 and Task 9 forensic audits, this pipeline was validated against physical ground observations from independent automatic weather stations at ICAR-IIVR and BHU Agronomy over 12 convective rainfall events.  
> 
> - **Critical Success Index (CSI)**: **0.933**  
> - **Probability of Detection (POD)**: **0.950**  
> - **Mean Absolute Error (MAE)**: **0.879 mm**  
> - **Directional Spatial Agreement**: **100%** on divergent events.  
> 
> In addition, our temperature downscaling engine operates under a certified, immutable baseline ($+0.7351^\circ\text{C}$) with an XGBoost Dynamic V2 model under controlled operational guardrails."*

---

### [2:45 – 3:00] Phase 6: Honest Limitations & Scale-Up Path
*(Screen: Show Scientific Governance / Limitations Disclosure)*

**Speaker 2:**  
> *"In strict adherence to scientific integrity, our system is classified as **`LIMITED_VALIDATION`**.  
> 
> Ground-truth validation is established in the Varanasi pilot domain across 24 station-event pairs. We do not claim nationwide validation today.  
> 
> Nationwide scale-up requires state mesonet MoUs with agencies like KSNDMC in Karnataka and Mahavedh in Maharashtra.  
> 
> We have built the complete, auditable, fail-closed pipeline to power Gram Panchayat-scale agricultural intelligence across India. Thank you, and we welcome your questions."*
