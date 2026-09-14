import {
  PanchayatResponse,
  BlockItem,
  PanchayatFullDetail,
  PanchayatWeatherSummary,
  GridCellRecord,
  RiskResult,
  AdvisoryResult,
  RiskSubsystemStatus,
  AdvisorySubsystemStatus,
  ModelSummary,
  ModelMetricsSummary,
  FeatureImportanceItem,
  Panchayat,
  PanchayatWeather,
  AgroAdvisory,
  AgriculturalRisk,
  GridCell,
  ModelMetrics,
  PanchayatDetailPayload,
} from '../types/index.js';
import {
  mockBlocks,
  mockPanchayats,
  mockRisks,
  mockAdvisories,
  mockGridCells,
  mockModelMetrics,
  mockFeatureImportances,
} from './mockData.js';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

// Global Live vs Demo Tracking
let isLiveBackend = false;
type ModeChangeListener = (isLive: boolean) => void;
const listeners: Set<ModeChangeListener> = new Set();

function updateConnectionStatus(isLive: boolean) {
  if (isLiveBackend !== isLive) {
    isLiveBackend = isLive;
    listeners.forEach((fn) => fn(isLive));
  }
}

export function subscribeConnectionStatus(fn: ModeChangeListener): () => void {
  listeners.add(fn);
  fn(isLiveBackend);
  return () => listeners.delete(fn);
}

export function getIsLiveBackend(): boolean {
  return isLiveBackend;
}

async function fetchJson<T>(endpoint: string, fallbackData: T): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      console.warn(`API [${url}] returned status ${res.status}. Using fallback fixtures.`);
      updateConnectionStatus(false);
      return fallbackData;
    }
    const json = await res.json();
    updateConnectionStatus(true);
    if (json && json.data !== undefined) {
      return json.data as T;
    }
    return json as T;
  } catch (err) {
    console.warn(`API call failed for [${url}]. Using offline demonstration fixtures.`, err);
    updateConnectionStatus(false);
    return fallbackData;
  }
}

async function postJson<T, P = any>(endpoint: string, payload: P, fallbackData: T): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      console.warn(`POST API [${url}] returned status ${res.status}. Using fallback fixtures.`);
      updateConnectionStatus(false);
      return fallbackData;
    }
    const json = await res.json();
    updateConnectionStatus(true);
    return (json.data !== undefined ? json.data : json) as T;
  } catch (err) {
    console.warn(`POST call failed for [${url}]. Using offline demonstration fixtures.`, err);
    updateConnectionStatus(false);
    return fallbackData;
  }
}

// Convert mock data to UI structures
function adaptMockPanchayat(p: any, idx: number): Panchayat {
  const isCropland = p.land_use?.is_agricultural_eligible ?? true;
  return {
    id: idx + 1,
    code: p.panchayat_id,
    name: p.name,
    block_id: Number(p.block_id) || 1,
    block_name: p.block_name || (Number(p.block_id) === 2 ? 'Sohawal Block' : 'Maya Bazar Block'),
    district_name: p.district_name || 'Ayodhya',
    state_name: p.state_name || 'Uttar Pradesh',
    centroid_lat: p.latitude,
    centroid_lon: p.longitude,
    latitude: p.latitude,
    longitude: p.longitude,
    elevation_meters: p.elevation_meters || 110,
    is_cropland_eligible: isCropland,
    active_crops_count: 2,
    highest_risk_severity: idx === 1 ? 'CRITICAL' : idx === 3 ? 'LOW' : 'HIGH',
    latest_weather: {
      tmax_c: idx === 1 ? 40.5 : 36.8,
      tmin_c: idx === 1 ? 28.5 : 24.2,
      tmean_c: idx === 1 ? 34.5 : 30.5,
      relative_humidity_pct: 68,
      wind_speed_kmh: 14.5,
      rainfall_mm: 0.0,
      predicted_residual_delta_c: 0.85,
      coverage_pct: 100.0,
      quality_status: 'COMPLETE',
      source_model: 'IMD-GFS',
      model_version: 'v1.0.0',
    },
  };
}

export const ApiService = {
  // Blocks
  async getBlocks(): Promise<BlockItem[]> {
    return fetchJson<BlockItem[]>('/panchayat/blocks', mockBlocks);
  },

  // Panchayats
  async getPanchayats(blockId?: number, search?: string): Promise<Panchayat[]> {
    let query = '/panchayat/list?page=1&page_size=100';
    if (blockId) query += `&block_id=${blockId}`;
    if (search) query += `&name=${encodeURIComponent(search)}`;

    const fallbackList = mockPanchayats.map((p, idx) => adaptMockPanchayat(p, idx));
    const res = await fetchJson<{ items: PanchayatResponse[] } | PanchayatResponse[]>(query, fallbackList as any);
    
    let rawItems: any[] = [];
    if (Array.isArray(res)) {
      rawItems = res;
    } else if (res && Array.isArray((res as any).items)) {
      rawItems = (res as any).items;
    } else {
      rawItems = fallbackList;
    }

    let adapted = rawItems.map((p, idx) => adaptMockPanchayat(p, idx));
    if (blockId) adapted = adapted.filter((p) => p.block_id === blockId);
    if (search) adapted = adapted.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()));
    return adapted;
  },

  // Single Panchayat Detail
  async getPanchayatDetail(panchayatId: number, date?: string): Promise<PanchayatDetailPayload> {
    const fallbackPanchayat = mockPanchayats.find((p) => p.panchayat_id.endsWith(String(panchayatId))) || mockPanchayats[0];
    const adaptedPanchayat = adaptMockPanchayat(fallbackPanchayat, panchayatId - 1);

    const fallback: PanchayatDetailPayload = {
      panchayat: adaptedPanchayat,
      latest_weather: adaptedPanchayat.latest_weather || {
        tmax_c: 36.8,
        tmin_c: 24.2,
        tmean_c: 30.5,
        relative_humidity_pct: 68,
        wind_speed_kmh: 14.5,
        rainfall_mm: 0.0,
        predicted_residual_delta_c: 0.85,
        coverage_pct: 100.0,
      },
      agricultural_contexts: [
        {
          crop_id: 1,
          crop_name: 'Rice (Paddy)',
          variety: 'NDR-359 (HYV)',
          crop_season: 'Kharif 2026',
          current_stage_name: 'Flowering / Anthesis',
          days_after_sowing: 45,
          accumulated_gdd: 680,
          status: 'COMPLETE',
          soil_profile: {
            soil_type: 'Alluvial Silt Loam',
            available_water_capacity_mm: 145,
          },
        },
        {
          crop_id: 2,
          crop_name: 'Maize (Corn)',
          variety: 'HQPM-1',
          crop_season: 'Kharif 2026',
          current_stage_name: 'Tasseling / Silking',
          days_after_sowing: 38,
          accumulated_gdd: 590,
          status: 'COMPLETE',
          soil_profile: {
            soil_type: 'Alluvial Silt Loam',
            available_water_capacity_mm: 145,
          },
        },
      ],
      detected_risks: [
        {
          id: 1,
          panchayat_id: panchayatId,
          panchayat_name: adaptedPanchayat.name,
          crop_name: 'Rice',
          hazard_type: 'THERMAL',
          risk_name: 'Flowering Spikelet Heat Stress',
          severity: 'HIGH',
          risk_score: 0.78,
          description: 'Maximum temperature (36.8°C) exceeds critical flowering tolerance threshold (35.0°C), creating floret sterility risk.',
          trigger_value: '36.8 °C (Tmax)',
          threshold_value: '35.0 °C (Threshold)',
          confidence: 'HIGH',
        },
      ],
      active_advisories: [
        {
          id: 1,
          panchayat_id: panchayatId,
          panchayat_name: adaptedPanchayat.name,
          crop_name: 'Rice',
          crop_stage: 'Flowering',
          category: 'IRRIGATION',
          priority: 'HIGH',
          urgency: 'IMMEDIATE',
          title: 'Maintain Light Standing Water Layer to Buffer Canopy Heat',
          action_summary: 'Apply light irrigation to maintain 2-3 cm standing water in paddy fields during daytime peak thermal hours.',
          action_details: [
            'Maintain a 2-3 cm water layer to provide evaporative cooling during peak sunshine hours (11:00 - 15:00).',
            'Avoid letting the field soil surface crack or dry during anthesis.',
          ],
          optimal_window: 'Early Morning (06:00 - 09:00 AM)',
          trigger_risk_name: 'Flowering Spikelet Heat Stress',
          scientific_rationale: 'Standing water layer increases latent heat flux and buffers canopy micro-climate temperature by 1.5 - 2.5°C.',
          conflict_flag: false,
          rule_version: 'agri_advisory_v1.0.0',
          model_version: 'XGBoost v1.0.0',
          evidence_metrics: { tmax_c: 36.8, rainfall_mm: 0.0 },
        },
      ],
    };

    let query = `/panchayat/${panchayatId}/detail`;
    if (date) query += `?date=${encodeURIComponent(date)}`;
    return fetchJson<PanchayatDetailPayload>(query, fallback);
  },

  // GeoJSON
  async getPanchayatsGeoJson(blockId?: number): Promise<any> {
    const query = blockId ? `/panchayat/geojson?block_id=${blockId}` : '/panchayat/geojson';
    const fallbackGeoJson = {
      type: 'FeatureCollection',
      features: mockPanchayats.map((p, idx) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [p.longitude, p.latitude],
        },
        properties: {
          id: idx + 1,
          lgd_code: p.panchayat_id,
          name: p.name,
          block_id: Number(p.block_id),
          block_name: 'Faizabad Sadar Block',
          is_cropland_eligible: p.land_use?.is_agricultural_eligible ?? true,
          cropland_ha: p.land_use?.cropland_area_hectares ?? 0,
          latest_temp_c: idx === 1 ? 40.5 : 36.8,
          weather_status: 'COMPLETE',
          coverage_pct: 100.0,
          active_risks_count: idx === 3 ? 0 : 2,
          top_advisory_priority: idx === 1 ? 'CRITICAL' : idx === 3 ? 'LOW' : 'HIGH',
        },
      })),
    };
    return fetchJson<any>(query, fallbackGeoJson);
  },

  // 1-km Grid Cells
  async getGridCells(blockId?: number): Promise<GridCell[]> {
    const query = blockId ? `/ml/grid/cells?block_id=${blockId}` : '/ml/grid/cells';
    const fallback: GridCell[] = mockGridCells.map((g) => ({
      cell_id: g.cell_id,
      panchayat_id: 1,
      panchayat_name: 'Maya Bazar',
      latitude: g.latitude,
      longitude: g.longitude,
      tmax_c: g.downscaled_temperature_c + 4.5,
      tmin_c: g.downscaled_temperature_c - 5.5,
      tmean_c: g.downscaled_temperature_c,
      predicted_residual: g.predicted_residual_c,
      elevation_m: g.elevation_m,
      slope_deg: g.slope_deg,
      aspect_deg: g.aspect_deg,
      cropland_fraction: g.cropland_fraction,
    }));
    return fetchJson<GridCell[]>(query, fallback);
  },

  // Risks
  async getRisks(filter?: { block_id?: number; panchayat_id?: number; severity?: string }): Promise<AgriculturalRisk[]> {
    let query = '/agriculture/risk?limit=100';
    if (filter?.panchayat_id) query += `&panchayat_id=${filter.panchayat_id}`;
    if (filter?.block_id) query += `&block_id=${filter.block_id}`;
    if (filter?.severity) query += `&severity=${filter.severity}`;

    const fallback: AgriculturalRisk[] = mockRisks.map((r, idx) => ({
      id: idx + 1,
      panchayat_id: r.panchayat_id,
      panchayat_name: r.panchayat_name,
      crop_name: r.crop_name,
      hazard_type: r.risk_category,
      risk_name: r.risk_type.replace(/_/g, ' '),
      severity: r.severity as any,
      risk_score: r.risk_score || 0.75,
      description: r.evidence?.condition_description || 'Micro-climate variable crosses critical crop stage tolerance.',
      trigger_value: `${r.observed_value !== null ? r.observed_value : 36.8} ${r.unit}`,
      threshold_value: `${r.threshold_value !== null ? r.threshold_value : 35.0} ${r.unit}`,
      confidence: r.confidence,
    }));
    return fetchJson<AgriculturalRisk[]>(query, fallback);
  },

  // Advisories
  async getAdvisories(filter?: { block_id?: number; panchayat_id?: number; priority?: string }): Promise<AgroAdvisory[]> {
    let query = '/advisory?limit=100';
    if (filter?.panchayat_id) query += `&panchayat_id=${filter.panchayat_id}`;
    if (filter?.block_id) query += `&block_id=${filter.block_id}`;
    if (filter?.priority) query += `&priority=${filter.priority}`;

    const fallback: AgroAdvisory[] = mockAdvisories.map((a, idx) => ({
      id: idx + 1,
      panchayat_id: a.panchayat_id,
      panchayat_name: a.panchayat_name,
      crop_name: a.crop_name,
      crop_stage: a.stage_name || 'Flowering',
      category: a.advisory_category,
      priority: a.priority,
      urgency: a.action?.urgency || 'IMMEDIATE',
      title: a.title,
      action_summary: a.message,
      action_details: [a.action?.action_text || a.message],
      optimal_window: a.action?.timing || 'Early Morning',
      trigger_risk_name: a.advisory_type.replace(/_/g, ' '),
      scientific_rationale: a.rationale || 'Conditions exceed physiological tolerance.',
      conflict_flag: a.is_expert_review_required,
      conflict_reason: a.is_expert_review_required ? 'Multi-hazard operational trade-off' : undefined,
      expert_review_required: a.is_expert_review_required,
      rule_version: a.advisory_rule_version,
      model_version: 'v1.0.0',
      evidence_metrics: { tmax_c: 36.8, rainfall_mm: 0.0 },
    }));
    return fetchJson<AgroAdvisory[]>(query, fallback);
  },

  // Model Metrics
  async getModelMetrics(version = 'v1.0.0'): Promise<ModelMetrics> {
    const fallback: ModelMetrics = {
      version: 'v1.0.0',
      algorithm: 'XGBoost Regressor (Residual Bias Formulation)',
      test_mae: 0.38,
      test_rmse: 0.52,
      test_r2: 0.942,
      feature_importances: {
        'elevation_m (DEM Height)': 0.38,
        'coarse_tmean_c (Block Base)': 0.24,
        'cropland_fraction (Sentinel-2 LULC)': 0.16,
        'slope_deg (Topographic Slope)': 0.12,
        'aspect_deg (Terrain Aspect)': 0.06,
        'solar_radiation_index': 0.04,
      },
      status: 'CALIBRATION_TEST_VALIDATED',
    };
    return fetchJson<ModelMetrics>(`/ml/models/${version}/metrics`, fallback);
  },

  async getSystemHealth(): Promise<any> {
    return fetchJson<any>('/health', {
      status: 'healthy',
      app_name: 'Agro-Meteorological Downscaling Intelligence',
      environment: 'production',
      services: { database: 'connected', postgis: 'enabled', spatial_index: 'active' },
    });
  },
};

export const api = ApiService;
export default ApiService;
