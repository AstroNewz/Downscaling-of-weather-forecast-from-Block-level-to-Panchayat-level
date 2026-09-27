# Frontend & Mobile: Localized Precipitation Nowcast Integration Guide

**SIH Problem Statement 26074 — Weather Downscaling & Agromet Advisory**  
**Task 6 — Panchayat-Specific Nowcast Exposure in React & Flutter**

> **Strict UI Freeze:** This document describes additive, read-only integration only.
> No visual redesigns, no layout changes, no existing advisory logic was altered.

---

## 1. Backend Fields Consumed

### 1.1 Unified Forecast Response (`GET /api/v1/forecast`)

`precipitation_nowcast` is appended to the existing response. It is **null** for any non-today date.

```json
{
  "precipitation_nowcast": {
    "panchayat_id": "DHOLAKPUR_PANCHAYAT_A",
    "panchayat_name": "Dholakpur Panchayat A",
    "block_id": "dholakpur_block",
    "block_name": "Dholakpur Block",
    "issue_time": "2026-09-27T09:45:00Z",
    "success": true,
    "status": "NOWCAST_HIGH_CONFIDENCE",
    "overall_confidence": "HIGH",
    "evidence_disagreement": false,
    "primary_horizon": { ... },
    "horizons": [ ... ],
    "baseline_forecast": { ... },
    "source_state": "SATELLITE_ONLY",
    "provenance": { ... }
  }
}
```

**Rules:**
- `precipitation_nowcast` is **null** when `target_date` ≠ today.
- `success: false` signals a computation failure — display gracefully.
- Never use `precipitation_nowcast` values to overwrite `current.precipitation_mm`.

### 1.2 Dedicated Endpoint (`GET /api/v1/panchayat/{panchayat_id}/precipitation-nowcast`)

- `date` (optional): defaults to today UTC.
- Future date → `success: false` + message containing `"only operationally applicable for current/short horizons"`.

### 1.3 Panchayat Detail (`GET /api/v1/panchayat/{panchayat_id}/detail`)

Returns `data.precipitation_nowcast` alongside the boundary polygon.

---

## 2. Horizon Schema — Field Reference

| Field | Type | Notes |
|---|---|---|
| `horizon_minutes` | int | 30, 60, or 120 |
| `rain_probability` | float [0–1] | **Use this key — NOT `precipitation_probability`** |
| `is_rain_likely` | bool | Derived threshold flag |
| `expected_amount_mm` | float \| null | **null = unavailable, never display as 0 mm** |
| `confidence` | string | HIGH / MEDIUM / LOW / VERY_LOW |
| `confidence_score` | float [0–1] | Numeric confidence for badge rendering |
| `source_state` | string | SATELLITE_ONLY, NWP_ONLY, etc. |
| `evidence_disagreement` | bool | Sources disagree flag |
| `observation_age_minutes` | float \| null | Staleness of satellite/obs data |
| `spatial_coverage` | float [0–1] | Fraction of Panchayat polygon covered |
| `fusion_method` | string | e.g. BAYESIAN_FUSION |

`primary_horizon` = 30-minute horizon (most actionable for farming).

---

## 3. Null Expected Rainfall — Display Contract

> **CAUTION:** `null` expected_amount_mm ≠ "0 mm". It means amount is not computable.

| Value | Display |
|---|---|
| `null` | `"—"` or `"Amount unavailable"` |
| `0.0` | `"< 0.1 mm"` (trace) |
| positive float | `"{value.toFixed(1)} mm"` |

```typescript
// React
function formatExpectedAmount(mm: number | null): string {
  if (mm === null || mm === undefined) return "—";
  if (mm < 0.1) return "< 0.1 mm";
  return `${mm.toFixed(1)} mm`;
}
```

```dart
// Flutter
String formatExpectedAmount(double? mm) {
  if (mm == null) return '—';
  if (mm < 0.1) return '< 0.1 mm';
  return '${mm.toStringAsFixed(1)} mm';
}
```

---

## 4. Conservative Probability Language

Never display probability as certainty. Always use hedged language:

| Range | Label |
|---|---|
| 0.00–0.29 | "Rain risk: Low" |
| 0.30–0.59 | "Rain risk: Moderate" |
| 0.60–0.79 | "Rain risk: High" |
| 0.80–1.00 | "Rain risk: Very High" |

✅ `"Rain risk: 72% (High)"` — ❌ `"Rain will occur"` / `"Rain confirmed"`

---

## 5. Baseline vs Localized — Strict Distinction

| Dimension | Baseline (NWP) | Localized Nowcast |
|---|---|---|
| Source | IMD-GFS Block-level | Satellite IR + NWP fusion |
| Resolution | Block (~25 km) | Panchayat polygon (exact) |
| Horizon | 24–168 hours | 30 / 60 / 120 min |
| Amount field | `current.precipitation_mm` | `primary_horizon.expected_amount_mm` |

**Never add nowcast probabilities to baseline amounts. They are independent signals.**

---

## 6. Point-in-Polygon Routing — Never Centroid

The `/api/v1/panchayat/resolve?lat=&lon=` endpoint uses exact polygon containment.

| Response status | Meaning |
|---|---|
| `RESOLVED` | Unambiguous single-polygon interior match |
| `ON_BOUNDARY` | Within tolerance of shared boundary edge |
| `OUTSIDE_REGISTERED_PANCHAYATS` | No polygon contains the coordinate |
| `OVERLAPPING_POLYGONS` | Fail-closed: two interiors overlap (data error) |

The frontend must use `panchayat_id` from resolve — **never derive from nearest centroid**.

---

## 7. Adjacent Panchayat A/B Separation (Dholakpur Proof)

| | Dholakpur A | Dholakpur B |
|---|---|---|
| ID | `DHOLAKPUR_PANCHAYAT_A` | `DHOLAKPUR_PANCHAYAT_B` |
| Polygon | L-shape lat [25.50–25.70] | Rectangle lat [25.55–25.70] |
| Block NWP | Identical | Identical |
| 30-min rain probability | ~0.795 (HIGH) | ~0.322 (LOW) |
| Advisory | Delay spraying | Favorable spray window |

Both Panchayats share the same block baseline but receive distinct localized advisories. This is the core SIH 26074 deliverable.

---

## 8. Map Boundary Rendering & Native Resolution Disclosure

`GET /api/v1/panchayat/{panchayat_id}/boundary` returns GeoJSON Feature with:
- `properties.geometry_source` — data origin
- `properties.native_resolution_m` — native data resolution in metres

**Required footer disclosure on every map boundary view:**
> *"Boundary source: [geometry_source]. Native resolution: [native_resolution_m]m. Display projected to screen resolution."*

---

## 9. Confidence States & Source States

| Confidence | Meaning |
|---|---|
| HIGH | Multiple consistent sources, observation < 30 min old |
| MEDIUM | Single source or data 30–60 min old |
| LOW | Source disagreement or data 60–120 min old |
| VERY_LOW | Highly stale (> 120 min) or no coverage |

| Source State | Meaning |
|---|---|
| SATELLITE_ONLY | Only satellite IR/precipitation product |
| NWP_ONLY | Only block NWP (no satellite coverage) |
| NWP_AND_SATELLITE | Both sources fused |
| NO_DATA | No usable observation source |

---

## 10. Observation Freshness

`observation_age_minutes` → staleness indicator:

| Age | Indicator |
|---|---|
| < 15 min | 🟢 Live |
| 15–30 min | 🟡 Recent |
| 30–60 min | 🟠 Aging |
| > 60 min | 🔴 Stale |
| null | ⚪ Unknown |

---

## 11. Disagreement Indicator

When `evidence_disagreement: true`, display a visible warning strip with `disagreement_reason` text.

---

## 12. Panchayat Identity — Required Fields

Every nowcast card must display:
- **Name**: `panchayat_name`
- **Block**: `block_name`
- **District**: from boundary record `district` field
- **State**: `state`

---

## 13. DEMO / LIVE / AUTO Mode Disclosure

Current deployment: **DEMO** — synthetic satellite simulation.

Required disclosure text:
> *"Nowcast generated from synthetic satellite simulation. Not based on real-time satellite data."*

---

## 14. Limitations

1. No real satellite ingestion (INSAT-3DR/MOSDAC architecturally ready but not connected).
2. No radar integration (interface exists, no feed connected).
3. Nowcast today-only — future dates return `success: false`.
4. Panchayat must be registered in `boundary_registry` for nowcast to work.
5. No sub-Panchayat spatial downscaling — single polygon-aggregated value.
6. Temperature model (Dynamic V2) is entirely unmodified by Tasks 1–6.
