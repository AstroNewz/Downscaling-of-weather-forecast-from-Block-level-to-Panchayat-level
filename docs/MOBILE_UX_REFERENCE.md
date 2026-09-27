# AgroWeather Mobile UX Reference Guide
**Reference Client:** `mobile/` (Flutter Application)  
**Target Clients:** Mobile App & Technical Web Portal  
**Date:** September 26, 2026

---

## 1. Information Hierarchy

The AgroWeather mobile application follows an **agronomic, action-first hierarchy**:
1. **Where & When:** Clear Panchayat name, block, district, and active forecast date at the top.
2. **Current Microclimate Conditions:** Instant thermal, humidity, and wind readings with an explicit 1-km downscale badge.
3. **Actionable Farm Advisories:** Immediate answer to *"What should I do on my farm today?"*—presented as clear cards before technical readouts.
4. **Diurnal Horizon (24 Hours):** Hourly progression illustrating critical agricultural time windows (e.g., peak heat hours, early morning spraying windows).
5. **Synoptic Outlook (7 Days):** Multi-day trend allowing farmers to plan irrigation or harvesting operations.
6. **Provenance & Disclosures:** Non-intrusive transparency badges (Data Mode, Last Updated, Downscaling Model Used).

---

## 2. Farmer Forecast Structure

In the farmer persona (`FarmerShell`):
- **Hero Card:**
  - Displays large downscaled temperature (e.g. `32.9°C`), condition title, weather emoji, humidity percentage.
  - Green pill badge: `1-km Downscaled Weather`.
- **Quick Stats Row:**
  - Three compact indicator tiles: Wind speed (km/h), Rainfall (mm), and Humidity (%).
- **Diurnal Hourly Strip:**
  - Horizontal scrollable card row displaying time, condition icon, and temperature. Hot hours (>35°C) are tinted with a subtle amber/red warning border.
- **Farmer Guidance Actions:**
  - Large cards detailing:
    - **Action:** Exactly what the farmer should do in plain language.
    - **Timing:** Exact time window (e.g., *Early morning 05:00 - 08:00 IST*).
    - **Why:** The agronomic reason (e.g., *Prevent floret sterility during anthesis*).
    - **Crop & Stage Tag:** Identifies applicable crop and phenological phase.

---

## 3. Official Forecast & Operational Structure

In the government official persona (`OfficialShell`):
- **Surveillance KPIs:**
  - Quick counters for Total Monitored Panchayats, High-Risk Areas, and Action Conflicts.
- **Field Action Conflict Alert Box:**
  - Highlights mutually conflicting agronomic rules (e.g. heat mitigation vs. lodging prevention) that require human extension officer intervention.
- **1-km GIS Microclimate Grid:**
  - Interactive grid viewer supporting 4 analytical layers:
    1. Downscaled Temperature Layer
    2. Model Residual Anomaly Layer ($\Delta T$)
    3. Satellite Cropland Mask Layer
    4. Multi-Hazard Risk Zones Layer
  - Cell Inspector modal revealing elevation, slope, aspect, and coarse vs. downscaled temperatures.
- **Administrative Explorer:**
  - Card & table views for searching and sorting all Panchayats across the jurisdiction.

---

## 4. Advisory Structure & Standardization

Every advisory item—across mobile and web—must adhere to this uniform schema:
- **Title:** Clear, imperative summary (e.g., *Protect Rice During Flowering Heat*).
- **Priority:** `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
- **Crop & Stage:** Target crop and phenological stage.
- **Action:** Actionable, non-medicalized agronomic steps.
- **When (Timing):** Operational execution window.
- **Why (Rationale):** Meteorological and physiological basis.
- **Provenance:** Model version, issued timestamp, data mode.

---

## 5. Risk Presentation

Agricultural risks are classified into 4 standard categories:
1. **Heat Stress:** Thresholded against crop flowering and vegetative tolerance.
2. **Heavy Rain & Waterlogging:** Thresholded against soil infiltration and drainage capacity.
3. **Wind Lodging:** Thresholded against canopy height and stem strength.
4. **Pathogen / Disease Window:** Evaluated from persistent humidity and temperature duration.

Visual indicators use semantic color coding:
- `LOW / NONE`: Subtle green / neutral slate
- `MODERATE`: Amber / orange
- `HIGH / CRITICAL`: Crimson / red

---

## 6. Selection Behaviors & Synchronization

### A. Location Switching:
- Triggered by dropdown or search selection.
- **State Machine Rule:** The previous forecast and advisory state are immediately invalidated (`isLoading = true`), preventing stale data display. Superseded asynchronous requests are discarded using cancellation tokens.

### B. Date Switching:
- Triggered by selecting a day in the 7-day outlook strip or date picker.
- **Rule:** The hourly curve, weather metrics, and advisory items update synchronously to that exact selected date. Forecast for Date A must **never** be displayed alongside an advisory for Date B.

### C. Crop & Stage Selection:
- Filter chips allow isolating advice for Rice (Paddy) vs Maize. Selecting a crop filters out unrelated advice without altering the underlying downscaled weather metrics.

---

## 7. Data Freshness, Modes & Error Handling

- **DEMO Mode:** Explicitly displays `DEMO • CANONICAL PILOT DATA` banner.
- **LIVE Mode:** Displays `LIVE • METEOROLOGICAL INGESTION`.
- **Offline / Stale:** Displays `Data may be stale • Last updated at <time>`.
- **Backend Error / 503:** Shows an informative retry card without fabricated weather numbers.

---

## 8. Patterns Influencing the Technical Website

The technical web portal (`frontend/` / `web/`) adopts these UX patterns from mobile:
1. **Where $\rightarrow$ When $\rightarrow$ Weather $\rightarrow$ Risk $\rightarrow$ Action** sequence.
2. Identical **Advisory Card structure** (Action, Best Time, Why, Crop, Stage).
3. Consistent **Diurnal hourly temperature curve** styling.
4. Unified **7-day outlook strip** with active day selection.
5. Strict **synchronized date/location state machine**.
