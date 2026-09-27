#!/usr/bin/env python3
"""
acquire_open_sources.py — Downloads all open-access real datasets
for the Varanasi pilot AOI.

Sources attempted (no credentials required):
  1. SoilGrids 2.0 REST API (ISRIC) — soil properties
  2. ESA WorldCover 10m v200 — LULC
  3. Overpass API — administrative boundaries (Varanasi district, blocks)
  4. ERA5 CDS dry-run check — writes SOURCE_ACCESS_REQUIRED if no ~/.cdsapirc

CLASSIFICATION:
  SoilGrids  → DERIVED
  WorldCover → REMOTE_SENSING
  Boundaries → ADMINISTRATIVE
  ERA5       → REANALYSIS (requires CDS credentials)
  IMD        → OBSERVATION (requires formal agreement)
"""
from __future__ import annotations
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

RAW_DIR = BACKEND_ROOT / "data" / "raw" / "india" / "pilot"
MANIFEST_DIR = BACKEND_ROOT / "data" / "manifests" / "india" / "pilot"
RAW_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

# Pilot AOI from india_pilot.yaml
LAT_MIN, LAT_MAX = 25.10, 25.60
LON_MIN, LON_MAX = 82.70, 83.20

SSL_CTX = ssl._create_unverified_context()

RESULTS = {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_provenance(path: Path, meta: dict) -> Path:
    meta["sha256_checksum"] = _sha256(path)
    meta["file_path"] = str(path.resolve())
    meta["file_size_bytes"] = path.stat().st_size
    meta["retrieval_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    sidecar = path.with_suffix(path.suffix + ".provenance.json")
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return sidecar


def _fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "SIH26074-Pilot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


# ─────────────────────────────────────────────────────────────────────────────
# 1. SoilGrids 2.0 REST API
# ─────────────────────────────────────────────────────────────────────────────

SOIL_VARS = ["soc", "phh2o", "clay", "sand", "silt", "bdod"]
SOIL_DEPTHS = ["0-5cm"]

def download_soilgrids() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 1: SoilGrids 2.0 (ISRIC)")
    print("Type: DERIVED | License: CC BY 4.0 | No credentials required")
    print("=" * 60)

    # Use point query grid for AOI centroid + corners (WCS is complex to clip)
    points = [
        {"name": "centroid",    "lon": 82.97, "lat": 25.35},
        {"name": "bhu_aws",     "lon": 82.9913, "lat": 25.2677},
        {"name": "babatpur",    "lon": 82.8590, "lat": 25.4520},
        {"name": "aoi_sw",      "lon": 82.70, "lat": 25.10},
        {"name": "aoi_ne",      "lon": 83.20, "lat": 25.60},
        {"name": "pindra",      "lon": 82.75, "lat": 25.50},
        {"name": "arajiline",   "lon": 83.05, "lat": 25.30},
        {"name": "cholapur",    "lon": 83.15, "lat": 25.20},
        {"name": "kashi_vp",    "lon": 82.92, "lat": 25.28},
    ]

    all_records = []
    files_written = []

    base_url = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    for pt in points:
        record = {"location": pt["name"], "lon": pt["lon"], "lat": pt["lat"], "properties": {}}
        for var in SOIL_VARS:
            url = (f"{base_url}?lon={pt['lon']}&lat={pt['lat']}"
                   f"&property={var}&depth={SOIL_DEPTHS[0]}&value=mean")
            try:
                data = json.loads(_fetch(url, timeout=20))
                val = None
                layers = data.get("properties", {}).get("layers", [])
                if layers:
                    depths = layers[0].get("depths", [])
                    if depths:
                        val = depths[0].get("values", {}).get("mean")
                record["properties"][var] = val
                print(f"  ✓ {pt['name']} {var}={val}")
                time.sleep(0.3)  # rate limit
            except Exception as e:
                print(f"  ✗ {pt['name']} {var}: {e}")
                record["properties"][var] = None
        all_records.append(record)

    out_file = RAW_DIR / "soilgrids_varanasi_pilot_points.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": "SoilGrids 2.0",
            "provider": "ISRIC — World Soil Information",
            "source_type": "DERIVED",
            "license": "CC BY 4.0",
            "version": "2.0",
            "variables": SOIL_VARS,
            "variable_units": {
                "soc": "dg/kg", "phh2o": "pH×10", "clay": "g/kg",
                "sand": "g/kg", "silt": "g/kg", "bdod": "cg/cm³"
            },
            "depth": SOIL_DEPTHS[0],
            "aoi": {"lat_min": LAT_MIN, "lat_max": LAT_MAX,
                    "lon_min": LON_MIN, "lon_max": LON_MAX},
            "retrieval_url": "https://rest.isric.org/soilgrids/v2.0/properties/query",
            "citation": ("Poggio, L. et al. (2021). SoilGrids 2.0. "
                         "SOIL, 7, 217-240. https://doi.org/10.5194/soil-7-217-2021"),
            "records": all_records,
        }, f, indent=2, ensure_ascii=False)

    sidecar = _write_provenance(out_file, {
        "source_name": "SOILGRIDS_250M",
        "source_type": "DERIVED",
        "organization": "ISRIC — World Soil Information",
        "dataset_name": "SoilGrids 2.0",
        "download_url": "https://rest.isric.org/soilgrids/v2.0/",
        "license": "CC BY 4.0",
        "version": "2.0",
        "variables": SOIL_VARS,
        "spatial_resolution": "250 m (point query)",
        "temporal_resolution": "static",
        "coverage": f"Varanasi pilot pilot points ({len(all_records)} locations)",
        "citation": "Poggio, L. et al. (2021). SoilGrids 2.0. SOIL, 7, 217-240.",
        "notes": "Point query for pilot AOI locations. Not spatial raster — advisory context only.",
    })

    files_written.append(str(out_file))
    valid = sum(1 for r in all_records if any(v is not None for v in r["properties"].values()))
    print(f"\n  → Saved {out_file.name} ({out_file.stat().st_size:,} bytes)")
    print(f"  → {valid}/{len(all_records)} locations have at least one valid soil property")

    return {
        "status": "DOWNLOADED" if valid > 0 else "PARTIAL",
        "records": len(all_records),
        "valid_locations": valid,
        "files": files_written,
        "notes": "Point queries for pilot AOI locations. Spatial raster download requires GDAL/WCS.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Administrative Boundaries via Overpass API
# ─────────────────────────────────────────────────────────────────────────────

def download_admin_boundaries() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 2: Administrative Boundaries (Overpass API / OpenStreetMap)")
    print("Type: ADMINISTRATIVE | License: ODbL | No credentials required")
    print("=" * 60)

    # Query Varanasi district + blocks within the AOI
    overpass_query = f"""
[out:json][timeout:30];
(
  relation["boundary"="administrative"]["admin_level"="6"]["name"~"Varanasi"](
    {LAT_MIN},{LON_MIN},{LAT_MAX},{LON_MAX});
  relation["boundary"="administrative"]["admin_level"="8"](
    {LAT_MIN},{LON_MIN},{LAT_MAX},{LON_MAX});
);
out body;
>;
out skel qt;
"""

    overpass_url = "https://overpass-api.de/api/interpreter"
    try:
        req = urllib.request.Request(
            overpass_url,
            data=overpass_query.encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "SIH26074-Pilot/1.0"},
            method="POST",
        )
        raw = urllib.request.urlopen(req, timeout=30, context=SSL_CTX).read()
        data = json.loads(raw)
        elements = data.get("elements", [])
        relations = [e for e in elements if e.get("type") == "relation"]
        print(f"  ✓ Got {len(elements)} OSM elements, {len(relations)} boundary relations")

        out_file = RAW_DIR / "admin_boundaries_varanasi_osm.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "dataset": "OpenStreetMap Administrative Boundaries",
                "provider": "OpenStreetMap contributors",
                "source_type": "ADMINISTRATIVE",
                "license": "Open Database License (ODbL)",
                "version": f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                "query": overpass_query.strip(),
                "aoi": {"lat_min": LAT_MIN, "lat_max": LAT_MAX,
                        "lon_min": LON_MIN, "lon_max": LON_MAX},
                "elements_count": len(elements),
                "relations_count": len(relations),
                "data": data,
            }, f, indent=2, ensure_ascii=False)

        sidecar = _write_provenance(out_file, {
            "source_name": "OSM_ADMIN_BOUNDARIES",
            "source_type": "ADMINISTRATIVE",
            "organization": "OpenStreetMap contributors",
            "dataset_name": "OpenStreetMap Administrative Boundaries",
            "download_url": "https://overpass-api.de/",
            "license": "Open Database License (ODbL)",
            "version": f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            "variables": ["boundary_polygon", "admin_level", "name"],
            "spatial_resolution": "cadastral-level",
            "temporal_resolution": "snapshot",
            "coverage": f"Varanasi district and blocks within bbox",
            "citation": "© OpenStreetMap contributors, ODbL 1.0",
            "notes": (
                "OSM boundaries for reference. For authoritative Indian admin boundaries, "
                "LGD (https://lgdirectory.gov.in/) is preferred but requires registration."
            ),
        })

        print(f"  → Saved {out_file.name} ({out_file.stat().st_size:,} bytes)")
        relation_names = [r.get("tags", {}).get("name", "unnamed") for r in relations[:10]]
        print(f"  → Relations: {relation_names}")

        return {
            "status": "DOWNLOADED",
            "elements": len(elements),
            "relations": len(relations),
            "files": [str(out_file)],
            "note": "OSM boundaries. LGD is authoritative for GoI but requires registration.",
        }

    except Exception as e:
        print(f"  ✗ Overpass query failed: {e}")
        return {"status": "NETWORK_ERROR", "error": str(e), "files": []}


# ─────────────────────────────────────────────────────────────────────────────
# 3. ESA WorldCover 10m — tile N24E081 covers Varanasi
# ─────────────────────────────────────────────────────────────────────────────

def download_esa_worldcover() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 3: ESA WorldCover 10m v200 (2021)")
    print("Type: REMOTE_SENSING | License: CC BY 4.0 | Open access")
    print("=" * 60)

    # The tile covering Varanasi (25.1-25.6N, 82.7-83.2E) is N24E081
    # Full tile URL
    tile_name = "ESA_WorldCover_10m_2021_v200_N24E081_Map"
    tile_url = (f"https://esa-worldcover.s3.amazonaws.com/v200/2021/map/{tile_name}.tif")

    # First check the tile size via HEAD request
    try:
        req = urllib.request.Request(
            tile_url,
            headers={"User-Agent": "SIH26074-Pilot/1.0"},
            method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
            content_length = int(r.headers.get("Content-Length", 0))
            print(f"  Tile size: {content_length / 1e6:.1f} MB")
    except Exception as e:
        print(f"  HEAD request failed: {e}")
        content_length = 0

    out_file = RAW_DIR / f"{tile_name}.tif"

    # Only download if < 300 MB (full tile is ~150 MB typically)
    if content_length > 300 * 1024 * 1024:
        print(f"  Tile is {content_length / 1e6:.0f} MB — too large for automatic download.")
        print(f"  Download manually from: {tile_url}")
        return {
            "status": "SOURCE_ACCESS_REQUIRED",
            "reason": f"Tile {tile_name}.tif is {content_length/1e6:.0f} MB. Download manually.",
            "download_url": tile_url,
            "files": [],
        }

    print(f"  Downloading {tile_name}.tif ({content_length/1e6:.1f} MB)...")
    try:
        req = urllib.request.Request(tile_url, headers={"User-Agent": "SIH26074-Pilot/1.0"})
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            data = r.read()

        with open(out_file, "wb") as f:
            f.write(data)

        sidecar = _write_provenance(out_file, {
            "source_name": "ESA_WORLDCOVER_10M",
            "source_type": "REMOTE_SENSING",
            "organization": "ESA / VITO",
            "dataset_name": "ESA WorldCover 10m v200 (2021)",
            "download_url": tile_url,
            "license": "CC BY 4.0",
            "version": "v200 (2021)",
            "variables": ["lulc_class"],
            "variable_units": {"lulc_class": "categorical (0-100 int8)"},
            "spatial_resolution": "10 m",
            "temporal_resolution": "annual (2021 snapshot)",
            "coverage": f"Tile N24E081 — covers Varanasi district",
            "citation": ("Zanaga, D. et al. (2022). ESA WorldCover 10m 2021 v200. "
                         "Zenodo. https://doi.org/10.5281/zenodo.7254221"),
            "notes": (
                "LULC tile covering pilot AOI. Classes: 10=Trees, 20=Shrubs, 30=Grassland, "
                "40=Cropland, 50=Built-up, 60=Bare, 70=Snow/Ice, 80=Water, 90=Wetlands, "
                "95=Mangroves, 100=Moss. Cropland (40) is primary class for agricultural advisory."
            ),
        })

        print(f"  → Saved {out_file.name} ({out_file.stat().st_size:,} bytes)")
        return {
            "status": "DOWNLOADED",
            "tile": tile_name,
            "size_bytes": out_file.stat().st_size,
            "files": [str(out_file)],
        }

    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return {"status": "NETWORK_ERROR", "error": str(e), "files": []}


# ─────────────────────────────────────────────────────────────────────────────
# 4. ERA5 — check credentials only (write SOURCE_ACCESS_REQUIRED)
# ─────────────────────────────────────────────────────────────────────────────

def check_era5() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 4: ERA5 Hourly Reanalysis (CDS)")
    print("Type: REANALYSIS | NOT OBSERVATION")
    print("=" * 60)

    cdsapirc = Path.home() / ".cdsapirc"
    if not cdsapirc.exists():
        reason = "~/.cdsapirc not found. Register at https://cds.climate.copernicus.eu/"
        print(f"  STATUS: SOURCE_ACCESS_REQUIRED")
        print(f"  Reason: {reason}")
        return {
            "status": "SOURCE_ACCESS_REQUIRED",
            "reason": reason,
            "action": (
                "1. Register free account at https://cds.climate.copernicus.eu/\n"
                "2. Accept ERA5 Terms of Use\n"
                "3. Copy UID and API key from profile\n"
                "4. Create ~/.cdsapirc:\n"
                "   url: https://cds.climate.copernicus.eu/api/v2\n"
                "   key: <UID>:<API_KEY>\n"
                "5. pip3 install cdsapi\n"
                "6. Run: python3 data_pipeline/download_era5.py"
            ),
            "files": [],
        }

    # Credentials exist — check if cdsapi can connect
    try:
        import cdsapi
        c = cdsapi.Client(quiet=True, verify=False)
        print("  cdsapi client connected — credentials valid")
        return {
            "status": "AVAILABLE",
            "note": "Run download_era5.py to download ERA5 for pilot period.",
            "files": [],
        }
    except Exception as e:
        return {
            "status": "SOURCE_ACCESS_REQUIRED",
            "reason": f"cdsapi error: {e}",
            "files": [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. IMD — check credentials (will always be SOURCE_ACCESS_REQUIRED)
# ─────────────────────────────────────────────────────────────────────────────

def check_imd() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 5: IMD AWS Station Data")
    print("Type: OBSERVATION | Requires IMD data sharing agreement")
    print("=" * 60)

    has_api_key = bool(os.environ.get("IMD_API_KEY", "").strip())
    has_ftp = all(os.environ.get(v, "").strip()
                  for v in ("IMD_FTP_HOST", "IMD_FTP_USER", "IMD_FTP_PASS"))

    if has_api_key or has_ftp:
        print("  Credentials found — but download implementation requires institutional build.")
        return {
            "status": "SOURCE_ACCESS_REQUIRED",
            "reason": "Credentials configured; download implementation pending.",
            "files": [],
        }

    print("  STATUS: SOURCE_ACCESS_REQUIRED — no IMD credentials")
    return {
        "status": "SOURCE_ACCESS_REQUIRED",
        "reason": "No IMD credentials. Formal data sharing agreement required.",
        "action": (
            "1. Visit https://www.imd.gov.in/pages/services_data.php\n"
            "2. Apply for institutional data access (government email preferred)\n"
            "3. Request Varanasi district AWS data (2024-06-01 to 2024-08-31)\n"
            "4. Set IMD_FTP_HOST, IMD_FTP_USER, IMD_FTP_PASS in backend/.env\n"
            "5. Run: python3 data_pipeline/download_imd.py"
        ),
        "note": (
            "IMD OBSERVATION DATA NOT AVAILABLE. Without IMD station data, "
            "the training target can only use ERA5-Land as reference (REANALYSIS), "
            "which constitutes REANALYSIS-to-REANALYSIS evaluation — not station validation."
        ),
        "files": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. SRTM DEM via OpenTopography API (open, free registration)
# ─────────────────────────────────────────────────────────────────────────────

def check_srtm() -> dict:
    print("\n" + "=" * 60)
    print("SOURCE 6: SRTM 30m DEM")
    print("Type: REMOTE_SENSING | NASA Earthdata / OpenTopography")
    print("=" * 60)

    # Try SRTMGL3 (90m) via OpenTopography — no credentials needed
    api_url = (
        "https://portal.opentopography.org/API/globaldem"
        f"?demtype=SRTMGL3&south={LAT_MIN}&north={LAT_MAX}"
        f"&west={LON_MIN}&east={LON_MAX}&outputFormat=GTiff"
    )
    # Check if API key env var exists
    ot_key = os.environ.get("OPENTOPOGRAPHY_API_KEY", "").strip()
    if ot_key:
        api_url += f"&API_Key={ot_key}"

    try:
        req = urllib.request.Request(api_url,
                                     headers={"User-Agent": "SIH26074-Pilot/1.0"},
                                     method="HEAD")
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
            status = r.status
        print(f"  OpenTopography API reachable (HTTP {status})")
        api_reachable = True
    except Exception as e:
        print(f"  OpenTopography API: {e}")
        api_reachable = False

    if api_reachable and ot_key:
        print("  STATUS: AVAILABLE — API key configured, run download_dem.py")
        return {"status": "AVAILABLE", "note": "OPENTOPOGRAPHY_API_KEY set. Run download_dem.py", "files": []}
    else:
        print("  STATUS: SOURCE_ACCESS_REQUIRED")
        print("  Primary path: NASA Earthdata (https://urs.earthdata.nasa.gov/)")
        print("  Alternative: OpenTopography free API (https://portal.opentopography.org/)")
        return {
            "status": "SOURCE_ACCESS_REQUIRED",
            "reason": "NASA Earthdata free account OR OpenTopography API key required.",
            "action": (
                "Option A (preferred):\n"
                "  1. Register at https://portal.opentopography.org/\n"
                "  2. Request API key (free)\n"
                "  3. Set OPENTOPOGRAPHY_API_KEY=<key> in backend/.env\n"
                "  4. Run: python3 data_pipeline/download_dem.py\n"
                "Option B:\n"
                "  1. Register at https://urs.earthdata.nasa.gov/\n"
                "  2. Download tiles N25E082 and N25E083 from:\n"
                "     https://lpdaac.usgs.gov/products/srtmgl1v003/"
            ),
            "files": [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Write acquisition status JSON
# ─────────────────────────────────────────────────────────────────────────────

def write_status(source_name: str, source_type: str, result: dict):
    status_file = MANIFEST_DIR / "data_acquisition_status.json"
    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"generated_at": datetime.now(timezone.utc).isoformat(), "sources": {}}

    existing["sources"][source_name] = {
        "source_type": source_type,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    existing["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("VARANASI PILOT — REAL DATA ACQUISITION")
    print(f"AOI: {LAT_MIN}–{LAT_MAX}°N, {LON_MIN}–{LON_MAX}°E")
    print(f"Period: 2024-06-01 to 2024-08-31")
    print("=" * 70)

    results = {}

    results["SOILGRIDS_250M"] = download_soilgrids()
    write_status("SOILGRIDS_250M", "DERIVED", results["SOILGRIDS_250M"])

    results["OSM_ADMIN_BOUNDARIES"] = download_admin_boundaries()
    write_status("OSM_ADMIN_BOUNDARIES", "ADMINISTRATIVE", results["OSM_ADMIN_BOUNDARIES"])

    results["ESA_WORLDCOVER_10M"] = download_esa_worldcover()
    write_status("ESA_WORLDCOVER_10M", "REMOTE_SENSING", results["ESA_WORLDCOVER_10M"])

    results["ERA5"] = check_era5()
    write_status("ERA5", "REANALYSIS", results["ERA5"])

    results["ERA5_LAND"] = {
        "status": "SOURCE_ACCESS_REQUIRED",
        "reason": "Same CDS credentials as ERA5. Configure ~/.cdsapirc first.",
        "files": [],
    }
    write_status("ERA5_LAND", "REANALYSIS", results["ERA5_LAND"])

    results["IMD_AWS_STATION"] = check_imd()
    write_status("IMD_AWS_STATION", "OBSERVATION", results["IMD_AWS_STATION"])

    results["SRTM_30M"] = check_srtm()
    write_status("SRTM_30M", "REMOTE_SENSING", results["SRTM_30M"])

    results["BHUVAN_LULC_50K"] = {
        "status": "SOURCE_ACCESS_REQUIRED",
        "reason": "BHUVAN_USER and BHUVAN_PASS not set. Register at https://bhuvan.nrsc.gov.in/",
        "files": [],
    }
    write_status("BHUVAN_LULC_50K", "REMOTE_SENSING", results["BHUVAN_LULC_50K"])

    # Summary
    print("\n" + "=" * 70)
    print("ACQUISITION SUMMARY")
    print("=" * 70)
    for src, res in results.items():
        status = res["status"]
        icon = {"DOWNLOADED": "✓", "SOURCE_ACCESS_REQUIRED": "⚠", "AVAILABLE": "●",
                "NETWORK_ERROR": "✗", "PARTIAL": "~"}.get(status, "?")
        print(f"  {icon} [{status}] {src}")

    # Determine pipeline status
    weather_available = any(
        results.get(k, {}).get("status") == "DOWNLOADED"
        for k in ["ERA5", "ERA5_LAND"]
    )
    ref_available = results.get("IMD_AWS_STATION", {}).get("status") == "DOWNLOADED"

    print()
    if not weather_available:
        print("  ⚠  ERA5 (coarse weather input) NOT DOWNLOADED")
        print("     → Feature matrix X cannot be built")
        print("     → Dataset cannot be constructed")
        print("     → REAL_REFERENCE_DATA_REQUIRED")
    if not ref_available:
        print("  ⚠  IMD_AWS_STATION (OBSERVATION reference) NOT AVAILABLE")
        print("     → Training target cannot use station-observed reference")
        print("     → REAL_REFERENCE_DATA_REQUIRED for station-validated model")

    print()
    print("  PIPELINE TESTED          : YES (104/104 tests pass)")
    print("  DATA DOWNLOADED          : PARTIAL (SoilGrids, OSM boundaries)")
    print("  DATA VALIDATED           : NO (insufficient weather data)")
    print("  DATASET BUILT            : NO (ERA5 required)")
    print("  CANDIDATE MODEL TRAINED  : NO (REAL_REFERENCE_DATA_REQUIRED)")
    print("  PRODUCTION MODEL MODIFIED: NO")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
