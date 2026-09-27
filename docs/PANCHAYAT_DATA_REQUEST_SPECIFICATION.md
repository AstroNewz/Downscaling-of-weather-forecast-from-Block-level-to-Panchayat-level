# Panchayat-Scale High-Resolution Agricultural Data Request Specification
## Technical Specification for Institutional Observational Network Access
**Project**: AgroWeather (Smart India Hackathon Problem Statement 26074)  
**Problem Statement Title**: Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services  
**Document ID**: SPEC-AGRO-2026-PANCHAYAT-DATA-01  
**Status**: APPROVED SCIENTIFIC DATA REQUEST SPECIFICATION  

---

## 1. Project Purpose & Scientific Context
The AgroWeather initiative addresses Smart India Hackathon Problem Statement 26074, which mandates providing hyper-local agro-meteorological advisories downscaled from coarse numerical weather prediction (NWP / ERA5 at ~25 km resolution) or block-level forecasts to Gram Panchayat spatial scales (~1 km to 5 km).

While coarse-scale and national synoptic station validation has been rigorously established across 42 WMO/IMD synoptic stations in 21 Indian States/UTs, scientific validation at the Gram Panchayat scale requires dense in-situ surface weather observations from state and national agricultural mesonets. 

This specification defines the exact technical data schema, parameters, metadata, temporal windows, and security protocols required to ingest authorized observational data from institutional custodians (e.g., KSNDMC, Mahavedh, IMD Agro-AWS, IMD DAMU/KVK, ICAR KVK, State Agricultural Universities) for the sole purpose of independent downscaling validation.

---

## 2. Intended Scientific Use & Non-Retraining Statement
### 2.1 Authorized Research Use Only
All requested observational datasets will be utilized strictly for independent, out-of-sample scientific validation of downscaled agro-meteorological products against physical ground truth. 

### 2.2 Explicit Non-Retraining Commitment
- **Zero Model Retraining**: The requested observational data will **not** be incorporated into training sets, model fitting, parameter tuning, or weight updates.
- **Frozen Model Architecture**: The physical operational baseline ($T_{\text{downscaled}} = T_{\text{coarse}} + 0.7351^\circ\text{C}$) and the research-grade Dynamic Residual Model V2 remain strictly frozen.
- **Fair Model Evaluation**: The data will be used purely as independent holdout benchmarks to evaluate spatial gradient fidelity, same-cell microclimatic variance, and localized bias across diverse agricultural physiographic zones.
- **No Commercial Exploitation**: Data will remain within the authorized project validation sandbox with strict provenance logging.

---

## 3. Requested Observational Variables
To evaluate temperature downscaling and agro-meteorological indices, the following surface variables are requested:

### 3.1 Primary Core Variables (Mandatory)
| Variable Code | Parameter Name | Target Accuracy / Precision | Standard S.I. Units | Height Above Ground |
| :--- | :--- | :--- | :--- | :--- |
| `TA_2M` | Air Temperature (Dry Bulb) | $\pm 0.1^\circ\text{C}$ (Resolution: $0.01^\circ\text{C}$) | Celsius ($^\circ\text{C}$) | 2.0 m (WMO standard) |
| `RH_2M` | Relative Humidity | $\pm 2\%$ (Resolution: $0.1\%$) | Percent ($\%$) | 2.0 m |
| `TIME_UTC` | Observation Timestamp | Synchronized to NTP | ISO 8601 UTC / IST | N/A |

### 3.2 Secondary Agro-Meteorological Variables (Highly Desirable)
| Variable Code | Parameter Name | Target Precision | Standard S.I. Units | Sensor Placement / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `PRECIP_ACC` | Rainfall / Precipitation Accumulation | $\pm 0.2\text{ mm}$ (Resolution: $0.1\text{ mm}$) | Millimeters ($\text{mm}$) | 1.0 m rim height (Tipping bucket/Optical) |
| `WSPD_10M` | Horizontal Wind Speed | $\pm 0.2\text{ m/s}$ (Resolution: $0.01\text{ m/s}$) | Meters/second ($\text{m/s}$) | 10.0 m (or 2.0–3.0 m agro-tower) |
| `WDIR_10M` | Horizontal Wind Direction | $\pm 3^\circ$ (Resolution: $1^\circ$) | Degrees ($0^\circ–360^\circ$) | 10.0 m (or 2.0–3.0 m agro-tower) |
| `RAD_GLOBAL` | Incoming Global Solar Radiation | $\pm 5\text{ W/m}^2$ | $\text{W/m}^2$ | Pyranometer atop tripod |
| `TSOIL_10CM` | Soil Temperature | $\pm 0.2^\circ\text{C}$ | Celsius ($^\circ\text{C}$) | Depth: $-10\text{ cm}$ root zone |
| `MSOIL_10CM` | Volumetric Soil Moisture | $\pm 2\%\text{ VWC}$ | $\text{m}^3/\text{m}^3$ or $\%$ | Depth: $-10\text{ cm}$ root zone |

---

## 4. Station Metadata Requirements
Physical downscaling verification requires complete station geographic and exposure metadata to prevent spatial misattribution:

1. **Station Unique Identifier**: Permanent institutional network station ID (e.g., KSNDMC station code, Mahavedh telemetry ID, IMD AWS ID).
2. **Station Official Name**: Administrative and village/hobli/taluk location name.
3. **Geographic Coordinates**:
   - Latitude: WGS-84 decimal degrees (minimum 5 decimal places, e.g., $15.36471^\circ\text{N}$).
   - Longitude: WGS-84 decimal degrees (minimum 5 decimal places, e.g., $75.12458^\circ\text{E}$).
   - Elevation: Height above mean sea level (AMSL) in meters ($\pm 1\text{ m}$).
4. **Administrative Hierarchy**:
   - State
   - District
   - Block / Taluk / Tehsil / Hobli
   - Gram Panchayat (LGD code if available)
   - Village / Site Name
5. **Site Classification / Microclimatic Setting**:
   - Classification categories: `AGRICULTURAL`, `RURAL`, `SUBURBAN`, `URBAN_CANOPY`, `AIRPORT`, `FOREST`, `COASTAL`, `MOUNTAIN`, `VALLEY`.
   - Surrounding land use / land cover within 500 m radius (e.g., irrigated paddy, rainfed dryland, orchard, built-up).
6. **Instrument & Tower Configuration**:
   - Sensor manufacturer & model number.
   - Sensor height above ground level (m).
   - Radiation shield type (naturally aspirated multi-plate vs motor-aspirated).
   - Calibration history & last field maintenance date.

---

## 5. Temporal Resolution & Target Historical Windows
### 5.1 Temporal Resolution
- **Standard Preferred**: Hourly synchronized observations ($00:00, 01:00, \dots, 23:00\text{ UTC}$).
- **Acceptable**: Sub-hourly intervals ($15\text{-minute}$ or $30\text{-minute}$ continuous log).
- **Daily Aggregates (Supplemental)**: Daily maximum temperature ($T_{\max}$), minimum temperature ($T_{\min}$), and 24-hour total rainfall.

### 5.2 Target Historical Validation Windows
To validate cross-season multi-temporal performance without seasonal bias, data is requested for three multi-season periods:
1. **Window A (Kharif Monsoon)**: 01-June-2024 to 31-October-2024 (Peak active agricultural season; high convective cloudiness & rainfall).
2. **Window B (Rabi Post-Monsoon / Winter)**: 01-November-2024 to 28-February-2025 (Strong nocturnal radiational cooling and valley inversions).
3. **Window C (Zaid Pre-Monsoon / Summer)**: 01-March-2025 to 31-May-2025 (Extreme surface heating and dry convective thermal gradients).

---

## 6. Quality Control & Data Integrity Flags
Where available from the custodian's telemetry automated quality control (AQC) system, quality flags should accompany each observation:
- `QC_VALID` (0): Passed all automated range, persistence, and step-test checks.
- `QC_SUSPECT` (1): Failed spatial consistency or rate-of-change check.
- `QC_ERRONEOUS` (2): Sensor saturated, open circuit, or physically impossible reading ($T < -10^\circ\text{C}$ or $T > 55^\circ\text{C}$).
- `QC_MISSING` (9): Missing data / communication dropout.

If institutional QC flags are absent, raw readings will be processed through the standard AgroWeather automated fail-closed physical consistency audit.

---

## 7. Preferred Data Delivery & Interface Formats
Data may be transferred through any of the following standard data protocols:
1. **RESTful API**:
   - HTTPS endpoint with OAuth2 / API Token bearer authentication.
   - JSON response format conforming to standard time-series schema.
2. **Direct SFTP / Secure Object Storage**:
   - Secure File Transfer Protocol (SFTP) or authorized AWS S3 / NIC Cloud bucket.
   - Daily or monthly partition files in Apache Parquet or CSV format.
3. **Offline Flat Archives**:
   - Standard UTF-8 encoded CSV or netCDF4 archives provided via authenticated portal download with SHA-256 integrity checksums.

### CSV Format Schema Specification
```csv
station_id,timestamp_utc,latitude,longitude,elevation_m,temp_c,rh_pct,precip_mm,wind_spd_mps,wind_dir_deg,qc_flag
KSNDMC_10421,2024-07-15T06:00:00Z,13.0827,77.5877,920.0,24.3,78.2,0.0,3.2,240,0
```

---

## 8. Data Privacy, Governance & Cyber-Security Compliance
1. **Institutional Compliance**: The project strictly adheres to the National Data Sharing and Accessibility Policy (NDSAP) and all institutional data governance guidelines of the Ministry of Earth Sciences (MoES), Indian Council of Agricultural Research (ICAR), and State Governments.
2. **No Reverse Engineering / No Redistribution**: Raw station-level telemetry feeds will remain encrypted in the research environment and will not be redistributed to third parties or exposed on public client interfaces.
3. **No Web Scraping or Perimeter Bypass**: The team will never use automated scrapers, session hijackers, or firewall bypassing scripts against government weather portals (`aws.imd.gov.in`, `ksndmc.org`, `mahavehd.maharashtra.gov.in`).
4. **Audit Trail**: Every imported record is tagged with an immutable provenance record:
   - Source agency code
   - Ingestion timestamp
   - Cryptographic SHA-256 hash of original payload
   - Pipeline version identifier

---

## 9. Verification & Ingestion Protocol
Upon delivery of authorized data, the AgroWeather validation runner ([run_panchayat_validation_pipeline.py](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/data_pipeline/scripts/run_panchayat_validation_pipeline.py)) executes the following steps:
1. Cryptographic validation of raw file SHA-256 hashes against manifest.
2. Physical bounds check ($-10.0^\circ\text{C} \le T \le 55.0^\circ\text{C}$).
3. Station pairwise distance calculation and Panchayat boundary assignment.
4. Coarse ERA5 cell association ($0.25^\circ \times 0.25^\circ$).
5. Frozen model inference (Certified Baseline & Dynamic Residual V2).
6. Multi-station gradient and within-cell microclimatic variance evaluation.
7. Automated generation of reproducibility forensic reports.
