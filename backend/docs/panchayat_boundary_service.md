# Panchayat Boundary Service: Technical Architecture & Operational Semantics
**SIH Problem Statement 26074**: *Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services*  
**Module**: `app.gis.boundary_service` | **Author**: Backend Engineering (Task 1)

---

## 1. Executive Summary & Problem Scope

In rural agro-meteorological advisory delivery, associating user GPS coordinates (farm plots, farmer mobile queries, ground sensors) with the correct administrative **Gram Panchayat** is the critical foundation. Prior systems often relied on nearest-centroid Euclidean distance or fixed circular search radii. 

Such proximity heuristics fail in administrative geography because:
- Administrative boundaries are non-convex, elongated, or multi-part polygons.
- Asymmetric geometries cause points inside one Panchayat to be geometrically closer to the centroid of an adjacent Panchayat.
- Topographic divides, microclimatic agro-zones, and local governance policies (e.g. crop insurance payouts, disaster compensation, subsidized fertilizer allocation) follow cadastral boundary lines, not geometric radial buffers.

The **Panchayat Boundary Service** implements authoritative, deterministic **Point-in-Polygon (PIP)** spatial routing, backed by an R-tree spatial index (`shapely.STRtree`), rigorous boundary-edge ambiguity resolution, and strict fail-closed governance.

---

## 2. Core Scientific Concepts

### 2.1 Why Exact Polygons are Preferable to Centroid/Radius Assignment

| Dimension | Nearest Centroid / Radius Heuristic | Exact Polygon (Point-in-Polygon) |
| :--- | :--- | :--- |
| **Assignment Mechanism** | $\min_i \|\mathbf{x} - \mathbf{c}_i\|_2$ | $\mathbf{x} \in \mathcal{P}_i$ where $\mathcal{P}_i$ is the closed polygon |
| **Boundary Realism** | Circular/Voronoi partitions (ignores true cadastral shapes) | Cadastral/LGD administrative truth |
| **Asymmetric / L-Shapes** | High error rate: assigns points in narrow arms to neighbouring centroids | Zero assignment error for interior points |
| **Shared Boundary Handling** | Arbitrary Voronoi bisector | Explicit numerical ambiguity zone ($\delta \approx 10^{-5\circ}$) |
| **Legal / Agronomic Accountability**| Unverifiable; fails administrative audits | Traceable to official survey source & version |

#### Mathematical Proof of Centroid Heuristic Failure
Consider an L-shaped Panchayat $\mathcal{P}_A$ adjacent to a convex rectangular Panchayat $\mathcal{P}_B$:
- $\mathcal{P}_A$: Bottom arm spanning $[82.40^\circ, 82.60^\circ] \times [25.00^\circ, 25.05^\circ]$ and vertical arm $[82.40^\circ, 82.45^\circ] \times [25.05^\circ, 25.20^\circ]$.
- $\mathcal{P}_B$: Occupies $[82.45^\circ, 82.60^\circ] \times [25.05^\circ, 25.20^\circ]$.
- Centroids: $\mathbf{c}_A \approx (82.4679^\circ, 25.0679^\circ)$, $\mathbf{c}_B = (82.5250^\circ, 25.1250^\circ)$.

For an interior query point $\mathbf{x} = (82.5800^\circ, 25.0400^\circ) \in \mathcal{P}_A$:
$$\|\mathbf{x} - \mathbf{c}_A\|_2 \approx 0.1156^\circ \quad > \quad \|\mathbf{x} - \mathbf{c}_B\|_2 \approx 0.1012^\circ$$
A nearest-centroid algorithm assigns $\mathbf{x}$ to $\mathcal{P}_B$—a false administrative assignment. Exact point-in-polygon containment assigns $\mathbf{x} \in \mathcal{P}_A$ with 100% mathematical fidelity.

---

### 2.2 Point-in-Polygon (PIP) Semantics

The coordinate space is standardized to **WGS84 (EPSG:4326)** latitude and longitude:
- For a query coordinate $\mathbf{x} = (\lambda, \phi)$ where $\lambda \in [-180^\circ, 180^\circ]$ is longitude and $\phi \in [-90^\circ, 90^\circ]$ is latitude:
  - **Containment Predicate**: $\text{Contains}(\mathcal{P}, \mathbf{x}) \iff \mathbf{x} \in \text{int}(\mathcal{P})$.
  - **Covers Predicate**: $\text{Covers}(\mathcal{P}, \mathbf{x}) \iff \mathbf{x} \in \mathcal{P}$ (including boundary $\partial\mathcal{P}$).
- **Spatial Indexing**: All registered geometries are indexed in an **STRtree** (Sort-Tile-Recursive R-Tree). Point queries execute in $O(\log N)$ bounding-box intersection time, followed by $O(V)$ exact crossing tests on candidate polygons where $V$ is the vertex count.

---

### 2.3 Boundary Ambiguity & Edge Handling

In real-world geographic coordinates, GPS inaccuracy (multipath error, ionospheric delay) and floating-point discretization mean coordinates frequently lie directly on or centimeters away from cadastral dividing lines.

Silently selecting a random polygon or picking the first encountered in iteration is unacceptable in administrative systems. The service implements an explicit **Numerical Boundary Tolerance**:
$$\delta_{\text{boundary}} = 1.0 \times 10^{-5\circ} \approx 1.11 \text{ meters}$$

#### Decision Workflow:
1. For each spatial candidate polygon $\mathcal{P}_k$:
   $$d_k = \text{dist}(\mathbf{x}, \partial\mathcal{P}_k) = \inf_{\mathbf{y} \in \partial\mathcal{P}_k} \|\mathbf{x} - \mathbf{y}\|_2$$
2. If $d_k \le \delta_{\text{boundary}}$ for one or more polygons:
   - Status: `ON_BOUNDARY`
   - Returns sorted `candidate_panchayat_ids = [ID_1, ID_2, ...]`
   - Does NOT guess; downstream workflows prompt user clarification or evaluate joint advisories.
3. If $d_k > \delta_{\text{boundary}}$ and $\text{Contains}(\mathcal{P}_k, \mathbf{x})$:
   - If exactly one polygon satisfies this: Status `RESOLVED`, `boundary_status = "INSIDE_POLYGON"`.
   - If multiple polygons satisfy this: Status `OVERLAPPING_POLYGONS` (fail-closed, flags topology corruption).
4. If no candidate contains $\mathbf{x}$:
   - Status: `OUTSIDE_REGISTERED_PANCHAYATS`.

---

### 2.4 Data Ingestion & Provenance Requirements

Every polygon ingested into the canonical registry must satisfy:
1. **Geometric Validity**: Non-empty areal geometries (`Polygon` or `MultiPolygon`). Degenerate geometries (points, lines) are rejected.
2. **Self-Intersection Healing**: Minor mechanical imperfections (e.g. self-touching rings from digitization artifacts) are repaired using `shapely.validation.make_valid` without altering the administrative boundary intent.
3. **Internal Canonical CRS**: Automatically reprojected to EPSG:4326 from source formats (GeoJSON, GeoPackage, Shapefile).
4. **Geodesic Metrics**: Centroid $(\phi_c, \lambda_c)$ and surface area ($A_{\text{sqkm}}$) are calculated using the WGS84 geoid (`pyproj.Geod(ellps="WGS84")`), avoiding the severe area distortions of Web Mercator (EPSG:3857).
5. **Auditability & Traceability**: Each record captures:
   - `panchayat_id`
   - `lgd_code` (Local Government Directory code from Ministry of Panchayati Raj)
   - `geometry_source`
   - `geometry_version`
   - `geometry_status` (`VERIFIED`, `UNVERIFIED`, `TEST_FIXTURE_ONLY`)
   - `is_verified` (Boolean flag; must be backed by authoritative survey certificates)
   - `_source_sha256` (cryptographic checksum of source file)
   - `ingestion_timestamp` (ISO 8601 UTC)

---

### 2.5 Separation of Administrative Routing vs. Meteorological Downscaling

> [!IMPORTANT]
> **A boundary polygon does NOT synthesize meteorological resolution finer than the underlying data sources.**

It is vital to distinguish between:
1. **Administrative Spatial Routing** (This Task): Mapping a latitude/longitude coordinate to a discrete governance unit (Gram Panchayat ID).
2. **Physical/Numerical Weather Downscaling**: Disaggregating coarse atmospheric numerical weather prediction (NWP) models (e.g. 12-km GFS, 9-km ECMWF, 4-km NCMRWF) to 1-km grids using terrain elevation (SRTM DEM), lapse rates, surface roughness, and machine learning residuals.

Assigning a coordinate to a Panchayat polygon routes the farmer to the appropriate crop phenology calendars, local soil types, and administrative risk rules. It does **NOT** imply that sub-grid atmospheric turbulence or hyper-local rainfall cells exist independently within that boundary unless supported by radar, mesonet observations, or physical downscaling models.

---

## 3. API Contract Reference

### 3.1 Point-in-Polygon Coordinate Resolution
- **HTTP Method**: `GET`
- **Endpoints**:
  - `/api/panchayats/resolve?lat=<LAT>&lon=<LON>`
  - `/api/v1/panchayat/resolve?lat=<LAT>&lon=<LON>`
- **Query Parameters**:
  - `lat` (float, required): Latitude in decimal degrees [-90, +90]
  - `lon` (float, required): Longitude in decimal degrees [-180, +180]
  - `tolerance` (float, optional): Boundary buffer in degrees (default: `1e-5`)
  - `require_verified` (bool, optional): Fails closed if boundary is unverified

#### Example 1: Successful Interior Resolution (`RESOLVED`)
```json
{
  "status": "RESOLVED",
  "boundary_status": "INSIDE_POLYGON",
  "panchayat_id": "PANCHAYAT_090720_001",
  "lgd_code": "243120",
  "panchayat_name": "Chiraigaon Gram Panchayat",
  "block": "Chiraigaon Block",
  "district": "Varanasi",
  "state": "Uttar Pradesh",
  "centroid_lat": 25.385210,
  "centroid_lon": 83.021450,
  "area_sq_km": 8.4215,
  "matched_geometry_version": "1.0",
  "source": "LGD_BHUVAN_NRSC_2024",
  "is_verified": true,
  "candidate_panchayat_ids": null,
  "distance_to_boundary_m": null,
  "message": "Unambiguously resolved to Panchayat 'Chiraigaon Gram Panchayat'.",
  "success": true
}
```

#### Example 2: Shared-Boundary Ambiguity (`ON_BOUNDARY`)
```json
{
  "status": "ON_BOUNDARY",
  "boundary_status": "ON_BOUNDARY",
  "panchayat_id": null,
  "candidate_panchayat_ids": [
    "PANCHAYAT_090720_001",
    "PANCHAYAT_090720_002"
  ],
  "distance_to_boundary_m": 0.045,
  "message": "Coordinate lies within 0.045m of the boundary for Panchayat(s): PANCHAYAT_090720_001, PANCHAYAT_090720_002. Cannot assign single Panchayat.",
  "success": true
}
```

#### Example 3: Outside Registered Coverage (`OUTSIDE_REGISTERED_PANCHAYATS`)
```json
{
  "status": "OUTSIDE_REGISTERED_PANCHAYATS",
  "boundary_status": "OUTSIDE_POLYGON",
  "panchayat_id": null,
  "candidate_panchayat_ids": null,
  "message": "Coordinates fall outside all registered Panchayat polygons.",
  "success": true
}
```

---

### 3.2 Canonical Boundary GeoJSON Endpoint
- **HTTP Method**: `GET`
- **Endpoints**:
  - `/api/panchayats/{panchayat_id}/boundary`
  - `/api/v1/panchayat/{panchayat_id}/boundary`
- **Response**: Standard RFC 7946 GeoJSON Feature
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [83.0102, 25.3781],
        [83.0315, 25.3781],
        [83.0315, 25.3920],
        [83.0102, 25.3920],
        [83.0102, 25.3781]
      ]
    ]
  },
  "properties": {
    "panchayat_id": "PANCHAYAT_090720_001",
    "lgd_code": "243120",
    "panchayat_name": "Chiraigaon Gram Panchayat",
    "block": "Chiraigaon Block",
    "district": "Varanasi",
    "state": "Uttar Pradesh",
    "centroid_lat": 25.385210,
    "centroid_lon": 83.021450,
    "area_sq_km": 8.4215,
    "geometry_source": "LGD_BHUVAN_NRSC_2024",
    "geometry_version": "1.0",
    "geometry_status": "VERIFIED",
    "is_verified": true,
    "ingestion_timestamp": "2026-09-27T06:00:00Z"
  }
}
```

---

## 4. Downstream Integration Architecture

Downstream forecast and advisory pipelines can consume the boundary service via the programmatic primitive:
```python
from app.gis import resolve_panchayat_from_coordinates, PanchayatBoundaryRecord

record: Optional[PanchayatBoundaryRecord] = resolve_panchayat_from_coordinates(
    lat=user_lat,
    lon=user_lon,
    tolerance_deg=1e-5,
    require_verified=False
)
if record:
    panchayat_id = record.panchayat_id
    panchayat_poly = record.geometry
    # Proceed to spatial weather masking & advisory generation
else:
    # Fail closed or handle boundary ambiguity explicitly
    pass
```
