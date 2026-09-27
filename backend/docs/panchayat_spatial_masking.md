# Panchayat Spatial Masking: Technical Architecture & Operational Semantics
**SIH Problem Statement 26074**: *Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services*  
**Module**: `app.gis.spatial_masking` | **Author**: Backend Engineering (Task 2)

---

## 1. Executive Summary

The **Panchayat Spatial Masking Service** provides the canonical bridge between administrative boundaries and gridded meteorological fields (NWP, satellite reanalysis, radar grids, or high-resolution downscaled surfaces). 

It accepts a target Panchayat polygon (resolved via the canonical [`PanchayatBoundaryRegistry`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/app/gis/boundary_registry.py)) and intersects it with a georeferenced weather field. Each Panchayat polygon operates as an independent spatial mask, computing exact geometric intersections, fractional cell overlaps, and area-weighted statistics with strict provenance preservation.

---

## 2. Core Scientific Concepts (Sections A–F)

### A. Panchayat Polygon → Source-Grid Intersection
The masking pipeline maps continuous polygon geometries $\mathcal{P} \subset \mathbb{R}^2$ to discrete spatial grid cells $\{C_i\}_{i=1}^M$:
1. **Candidate Cell Filtering**: Bounding box query ($\text{bbox}(\mathcal{P}) \cap \text{bbox}(C_i)$) reduces $M$ source cells to candidates $K \ll M$ in $O(\log M)$ time.
2. **Topological Intersection**: For each candidate cell, exact geometric intersection is computed:
   $$I_i = \mathcal{P} \cap C_i$$
   Cells with empty intersection ($I_i = \emptyset$ or $\text{Area}(I_i) \le 0$) are excluded.
3. **Geodesic Metric Area**: The true ellipsoidal surface area of $I_i$ and $C_i$ is computed using the **WGS84 ellipsoid** via `pyproj.Geod(ellps="WGS84")`, eliminating the severe high-latitude/low-latitude distortion associated with planar or Web Mercator projections.

---

### B. Why Adjacent Panchayats Can Share a Source Cell
Meteorological observations and NWP grids (e.g. 1-km, 4-km, or 12-km cells) are generated on regular Cartesian, rotated, or coordinate grids that **do not align with irregular administrative borders**.

When a grid cell $C_k$ straddles the cadastral dividing line between adjacent Panchayats $\mathcal{P}_A$ and $\mathcal{P}_B$:
$$C_k \cap \mathcal{P}_A \neq \emptyset \quad \text{and} \quad C_k \cap \mathcal{P}_B \neq \emptyset$$
- It is physically and mathematically legitimate for $C_k$ to contribute to both $\mathcal{P}_A$ and $\mathcal{P}_B$.
- Cell $C_k$ contributes with fractional weight $w_{A, k} = \text{Area}(C_k \cap \mathcal{P}_A)$ to Panchayat A, and $w_{B, k} = \text{Area}(C_k \cap \mathcal{P}_B)$ to Panchayat B.
- Neither Panchayat "owns" the cell, and neither Panchayat is artificially deprived of the weather observation.

---

### C. Why Overlap Weighting Matters (Fractional vs. Simple Averaging)
Assigning grid cells to a polygon without accounting for fractional overlap introduces substantial spatial distortion:
- **Simple Arithmetic Averaging**: Assumes every intersecting cell contributes equally ($w_i = \frac{1}{N}$), regardless of whether 95% or 5% of the cell lies within the boundary.
- **Area-Weighted Averaging**: Weights each observation strictly by its intersecting geodesic area:
  $$\bar{v}_{\text{weighted}} = \frac{\sum_{i \in \text{valid}} w_i v_i}{\sum_{i \in \text{valid}} w_i}, \quad \text{where } w_i = \text{Area}(\mathcal{P} \cap C_i)$$

#### Quantitative Impact Proof
Consider two cells intersecting Panchayat A:
- Cell 1 (temperature $10.0^\circ\text{C}$): 80% inside A ($\text{Area} = 0.80\,\text{km}^2$).
- Cell 2 (temperature $20.0^\circ\text{C}$): 20% inside A ($\text{Area} = 0.20\,\text{km}^2$).

$$\bar{v}_{\text{weighted}} = \frac{0.80 \times 10.0 + 0.20 \times 20.0}{0.80 + 0.20} = 12.0^\circ\text{C}$$
$$\bar{v}_{\text{simple}} = \frac{10.0 + 20.0}{2} = 15.0^\circ\text{C}$$
Simple averaging produces an error of $+3.0^\circ\text{C}$ (+25%), erroneously pulling the Panchayat estimate toward the outside cell. Fractional overlap weighting eliminates this distortion.

---

### D. Why Masking Does NOT Increase Native Weather Resolution

> [!IMPORTANT]
> **Spatial polygon masking is an aggregation and routing operation; it does NOT synthesize atmospheric information finer than the native resolution of the input data source.**

To maintain scientific integrity and auditability, the service strictly records and differentiates three distinct resolution scales in [`SourceResolutionProvenance`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/app/schemas/spatial_masking.py#L30-L51):
1. **Native Source Resolution** (`native_resolution_km`): The true physical resolution of the atmospheric sensor or NWP grid (e.g., 12 km for coarse GFS, 4 km for NCMRWF, 1 km for high-resolution downscaled output).
2. **Processing Resolution** (`processing_resolution_km`): The grid spacing at which spatial geometry intersection was evaluated.
3. **Visualization Resolution** (`visualization_resolution_km`): Nominal rendering or tile resolution on maps.

Masking a 4-km rainfall grid with a 2-km Panchayat polygon produces an area-weighted estimate of the 4-km field within that polygon; it **must never be reported as a genuine 250-m microclimate observation**. Every extraction payload attaches an explicit resolution disclaimer.

---

### E. How Coverage & Quality are Reported

To ensure downstream advisory models do not act on unrepresentative spatial data, every extraction returns explicit coverage metrics:
- `cells_considered`: Number of candidate cells evaluated.
- `cells_intersecting`: Number of cells with non-zero geometric overlap.
- `valid_cells_intersecting`: Number of intersecting cells with finite, non-NaN values.
- `coverage_fraction`: $\frac{\text{Total Intersecting Area}}{\text{Panchayat Area}}$ (clamped to $[0, 1]$).
- `valid_coverage_fraction`: $\frac{\text{Valid Non-NaN Intersecting Area}}{\text{Panchayat Area}}$.

#### Quality Tiers ([`CoverageQuality`](file:///Users/prajjwalpatel/Documents/SIH%202/Agroweather-Downscaling/backend/app/schemas/spatial_masking.py#L20-L27))
| Quality Tier | Valid Coverage Threshold | Agronomic Meaning |
| :--- | :--- | :--- |
| `COMPLETE` | $\ge 95\%$ | Authoritative; suitable for all crop advisory models |
| `HIGH` | $\ge 80\%$ | High confidence; minor boundary clipping |
| `MODERATE` | $\ge 50\%$ | Usable; flags partial spatial coverage |
| `PARTIAL` | $\ge 20\%$ | Caution; significant portions of Panchayat unobserved |
| `INSUFFICIENT` | $< 20\%$ | Unreliable; triggers fail-closed warning |
| `ZERO_COVERAGE` | $0\%$ | No overlap; fails closed |

---

### F. How Missing & Insufficient Data Fails Closed

The service implements strict **fail-closed** policies:
1. **Empty/Non-Intersecting Grid**: Returns `status="NO_INTERSECTING_CELLS"`, `coverage_quality="ZERO_COVERAGE"`, `features={}`, and `success=False`.
2. **All Values Missing (NaN)**: If all intersecting cells contain NaN/nulls, returns `status="ALL_VALUES_MISSING"` and `success=False`.
3. **Invalid CRS**: Rejects non-conforming projections with `status="INVALID_CRS"`.
4. **Invalid Geometry**: Rejects non-areal geometries (LineString, Point) with `status="INVALID_GEOMETRY"`.
5. **Unverified Geometry**: When `require_verified=True`, unverified boundaries fail closed with `status="UNVERIFIED_GEOMETRY"`.
6. **Precipitation 0.0 mm vs. NaN Semantic Distinction**:
   - $0.0\,\text{mm}$ rainfall is a valid zero measurement (no rain detected: `is_rain_detected = False`, `rain_area_fraction = 0.0`).
   - $\text{NaN}$ represents missing data and is excluded from the denominator.
   - The two are **never** interchangeable.

---

## 3. Programmatic Usage

```python
from app.gis import extract_panchayat_spatial_features, SourceWeatherGrid

# Execute extraction
result = extract_panchayat_spatial_features(
    panchayat_id="PANCHAYAT_CHIRAIGAON",
    source_grid=source_grid,
    valid_time="2026-09-27T12:00:00Z",
    require_verified=False,
    include_cell_details=True,
)

if result.success and result.coverage_quality in ("COMPLETE", "HIGH"):
    weighted_temp = result.features["weighted_mean"]
    print(f"Panchayat {result.panchayat_id} temperature: {weighted_temp}°C")
else:
    print(f"Spatial extraction failed/insufficient: {result.status} - {result.message}")
```
