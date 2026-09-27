# Institutional Data Access Operational Checklist
## Procedural Guide for Acquiring Authorized Mesonet Observations for Panchayat Validation
**Project**: AgroWeather (Smart India Hackathon Problem Statement 26074)  
**Document ID**: SOP-AGRO-2026-DATA-ACCESS-01  
**Status**: APPROVED OPERATIONAL CHECKLIST  

---

## 1. General Operating Principles
1. **Zero Evasion**: Never scrape, probe ports, spoof headers, or attempt to bypass firewalls or authentication on government portals.
2. **Formal Scientific Route**: Access must be requested via institutional memorandums of understanding (MoU), official academic/research request forms, or open-government data APIs where officially published.
3. **Reproducible Traceability**: Every dataset received must have verified provenance, cryptographically signed SHA-256 checksums, and explicit licensing/permission terms recorded in `reports/PANCHAYAT_DATA_ACCESS_REGISTRY.json`.
4. **Frozen Model Commitment**: Reiterate in all formal communications that data is used strictly for out-of-sample physical validation, with zero model retraining or commercial redistribution.

---

## 2. Institutional Checklists

### 2.1 Karnataka State Natural Disaster Monitoring Centre (KSNDMC)
**Network**: Telemetric Weather Station (TWS) Network (6,000+ Hobli/Gram Panchayat stations across Karnataka)  
**Status**: `ACCESS_REQUEST_REQUIRED`

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | Director, KSNDMC, Major Sandeep Unnikrishnan Road, Bengaluru, Karnataka | Verified |
| 2 | **Identify Official Request Mechanism** | Formal institutional requisition under KSDC research data sharing guidelines or Open City / KGIS portal | Standard Protocol |
| 3 | **Request Historical Observations** | Hourly air temp ($T$), relative humidity ($RH$), rainfall ($P$) for target pilot hoblis/panchayats (e.g., Dharwad, Belagavi, Mandya) | Drafted in Request Spec |
| 4 | **Request Station Metadata** | Station ID, Hobli, Gram Panchayat name, LGD code, elevation | Schema Defined |
| 5 | **Request QC Flags** | Ingestion of KSNDMC automated telemetry QA/QC range and step check flags | Schema Defined |
| 6 | **Request Coordinates** | WGS-84 latitude/longitude to 5 decimal places | Schema Defined |
| 7 | **Request Instrument Details** | Sensor height (standard 2m agro-mast), rain gauge orifice height, tower exposure | Schema Defined |
| 8 | **Request Research Permission** | Formal undertaking confirming use solely for SIH 26074 academic/research downscaling validation | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Secure transfer via official media, SFTP, or state portal authenticated credential | Pending Authorization |
| 10 | **Verify Checksum / Provenance** | Generate SHA-256 hash, log in `PANCHAYAT_DATA_ACCESS_REGISTRY.json` | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Execute `run_panchayat_validation_pipeline.py` with KSNDMC input profile | Ready |

---

### 2.2 Maharashtra Agriculture Weather Information Network (Mahavedh)
**Network**: Skymet / MahaAgri PPP Mesonet (2,060+ Mandal-level AWS across Maharashtra)  
**Status**: `ACCESS_REQUEST_REQUIRED`

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | Commissionerate of Agriculture, Government of Maharashtra, Pune | Verified |
| 2 | **Identify Official Request Mechanism** | Formal research application via Department of Agriculture / MSWAN authenticated gateway | Standard Protocol |
| 3 | **Request Historical Observations** | Hourly $T$, $RH$, wind, rainfall across Vidarbha, Marathwada, and Western Ghats pilot mandals | Drafted in Request Spec |
| 4 | **Request Station Metadata** | Station ID, Revenue Circle (Mandal), Taluka, District, Gram Panchayat | Schema Defined |
| 5 | **Request QC Flags** | Missing value indicators, sensor fault codes, calibration timestamps | Schema Defined |
| 6 | **Request Coordinates** | Precise decimal degree WGS-84 coordinates for mandal AWS masts | Schema Defined |
| 7 | **Request Instrument Details** | AWS hardware model, radiation shield configuration, mast height (2m/3m/10m) | Schema Defined |
| 8 | **Request Research Permission** | Non-commercial research clearance under State Agri-Data Policy | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Ingestion of authorized CSV/Parquet dumps via secure channel | Pending Authorization |
| 10 | **Verify Checksum / Provenance** | Validate checksum against official dispatch manifest | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Ingest into `run_panchayat_validation_pipeline.py` under Maharashtra pilot profile | Ready |

---

### 2.3 IMD Agro-AWS & Urban Mesonet Network
**Network**: Division of Agricultural Meteorology, IMD Pune / MoES (~700 Agro-AWS stations nationwide)  
**Status**: `ACCESS_REQUEST_REQUIRED`

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | Head, Agromet Division, IMD Pune / National Data Centre (NDC), IMD | Verified |
| 2 | **Identify Official Request Mechanism** | Official data indent via IMD NDC Web Portal (`ndc.imd.gov.in`) or MoES research clearance | Standard Protocol |
| 3 | **Request Historical Observations** | 15-minute or hourly observations ($T$, $RH$, wind, rain, soil temperature at $10\text{ cm}$) | Drafted in Request Spec |
| 4 | **Request Station Metadata** | WMO/Agro station index, district, Agro-Climatic Zone (ACZ) code | Schema Defined |
| 5 | **Request QC Flags** | IMD Automated Quality Control (AQC) validation flags (valid, suspicious, erroneous) | Schema Defined |
| 6 | **Request Coordinates** | Station latitude, longitude, and benchmark elevation AMSL | Schema Defined |
| 7 | **Request Instrument Details** | Standard IMD Agro-meteorological observatory instrumentation schedule | Schema Defined |
| 8 | **Request Research Permission** | Student/Academic subsidized research data concession approval letter | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Download official NDC netCDF4 or formatted ASCII/CSV archive | Pending Authorization |
| 10 | **Verify Checksum / Provenance** | Verify archive MD5/SHA-256 against IMD dispatch manifest | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Ingest into `run_panchayat_validation_pipeline.py` under IMD Agro profile | Ready |

---

### 2.4 IMD DAMU & Gramin Krishi Mausam Sewa (GKMS) / KVK Network
**Network**: District Agromet Units established at KVKs (330+ DAMU units)  
**Status**: `ACCESS_REQUEST_REQUIRED`

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | Subject Matter Specialist (Agrometeorology) / Senior Scientist & Head, respective KVK | Verified |
| 2 | **Identify Official Request Mechanism** | Direct research collaboration request through ICAR-ATARI (Agricultural Technology Application Research Institute) | Standard Protocol |
| 3 | **Request Historical Observations** | In-situ daily and hourly agromet observations, soil moisture, microclimatic field readings | Drafted in Request Spec |
| 4 | **Request Station Metadata** | KVK farm name, village, block, district, soil type, major cropping pattern | Schema Defined |
| 5 | **Request QC Flags** | Manual observer validation logs and sensor calibration certificates | Schema Defined |
| 6 | **Request Coordinates** | GPS coordinates of agromet observatory plot within KVK campus | Schema Defined |
| 7 | **Request Instrument Details** | Stevensor screen height, soil thermometer depths (5cm, 10cm, 20cm), anemometer mast | Schema Defined |
| 8 | **Request Research Permission** | Collaborative validation clearance under SIH research framework | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Validated field registers / digital spreadsheets signed by Agromet SMS | Pending Authorization |
| 10 | **Verify Checksum / Provenance** | Compute cryptographic SHA-256 and store in raw pilot repository | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Process through automated pipeline for KVK field vs downscaling validation | Ready |

---

### 2.5 State Agricultural Universities (SAUs) Observatories
**Network**: Department of Agronomy / Agrometeorology observatories across SAUs (e.g., UAS Dharwad, TNAU Coimbatore, PAU Ludhiana, BCKV Mohanpur, MPKV Rahuri)  
**Status**: `ACCESS_REQUEST_REQUIRED`

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | Professor & Head, Department of Agricultural Meteorology / Director of Research | Verified |
| 2 | **Identify Official Request Mechanism** | Academic research data request letter endorsed by institution | Standard Protocol |
| 3 | **Request Historical Observations** | Principal & Ordinary agrometeorological observatory records (07:00 IST & 14:00 IST + continuous AWS) | Drafted in Request Spec |
| 4 | **Request Station Metadata** | Research farm plot ID, agro-climatic sub-zone, surrounding crop canopy characteristics | Schema Defined |
| 5 | **Request QC Flags** | Certified observatory inspection records and thermometer correction cards | Schema Defined |
| 6 | **Request Coordinates** | High-precision DGPS/RTK coordinates of research station enclosure | Schema Defined |
| 7 | **Request Instrument Details** | Standard IMD-spec Stevenson screen, Robinson cup counter anemometer, Campbell-Stokes recorder | Schema Defined |
| 8 | **Request Research Permission** | Academic data-sharing agreement for downscaling model verification | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Digital agromet observatory returns | Pending Authorization |
| 10 | **Verify Checksum / Provenance** | SHA-256 verification and directory archival | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Ingest into pipeline runner under SAU observatory profile | Ready |

---

### 2.6 ISRO MOSDAC / Bhuvan In-Situ Networks
**Network**: ISRO Automatic Weather Station Network (~800 stations)  
**Status**: `PARTIALLY_ACCESSIBLE` (Requires portal authentication)

| Step | Action Item | Verification Method / Artifact | Status |
| :--- | :--- | :--- | :--- |
| 1 | **Identify Official Custodian** | MOSDAC Data Manager, Space Applications Centre (SAC), ISRO, Ahmedabad | Verified |
| 2 | **Identify Official Request Mechanism** | Registered user access on `mosdac.gov.in` portal with research proposal submission | Standard Protocol |
| 3 | **Request Historical Observations** | Hourly in-situ AWS parameters ($T$, $RH$, solar radiation, wind) | Drafted in Request Spec |
| 4 | **Request Station Metadata** | Station code, site location name, payload configuration | Schema Defined |
| 5 | **Request QC Flags** | MOSDAC automated quality flags (`GOOD`, `SUSPICIOUS`, `BAD`) | Schema Defined |
| 6 | **Request Coordinates** | Station latitude, longitude, and elevation | Schema Defined |
| 7 | **Request Instrument Details** | Solar-powered AWS satellite-linked telemetry mast specifications | Schema Defined |
| 8 | **Request Research Permission** | Terms of Reference acceptance on MOSDAC user registration portal | Standard Undertaking |
| 9 | **Receive Authorized Dataset** | Portal bulk download or authorized REST API query | Ready upon Login |
| 10 | **Verify Checksum / Provenance** | Ingestion hash validation | Pipeline Ingestion Check |
| 11 | **Run Validation Pipeline** | Run `run_panchayat_validation_pipeline.py` with MOSDAC parser | Ready |

---

## 3. Summary of Procedural Readiness
The AgroWeather pipeline is architected such that once any authorized dataset from Steps 1–10 is placed into `backend/data/raw/panchayat_mesonet/<source_network>/`, Step 11 (`run_panchayat_validation_pipeline.py`) can execute immediately without writing a single line of new validation code, and without modifying any model weights.
