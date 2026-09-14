export * from './panchayat.js';
export * from './weather.js';
export * from './agriculture.js';
export * from './risk.js';
export * from './advisory.js';
export * from './ml.js';

import { PanchayatResponse, LandUseComposition } from './panchayat.js';
import { AdvisoryResult, AdvisoryAction, AdvisoryPriority, AdvisoryStatus } from './advisory.js';
import { RiskResult, RiskSeverity, RiskStatus } from './risk.js';
import { ModelMetricsSummary, ModelSummary, FeatureImportanceItem } from './ml.js';

export interface PanchayatWeather {
  tmax_c: number;
  tmin_c: number;
  tmean_c: number;
  relative_humidity_pct?: number;
  wind_speed_kmh?: number;
  rainfall_mm?: number;
  predicted_residual_delta_c?: number;
  coverage_pct?: number;
  quality_status?: string;
  source_model?: string;
  model_version?: string;
  contributing_grid_cells?: number;
}

export interface Panchayat {
  id: number;
  code?: string;
  name: string;
  block_id?: number | string;
  block_name?: string;
  district_name?: string;
  state_name?: string;
  centroid_lat?: number;
  centroid_lon?: number;
  latitude?: number;
  longitude?: number;
  elevation_meters?: number;
  is_cropland_eligible: boolean;
  active_crops_count?: number;
  highest_risk_severity?: string;
  latest_weather?: PanchayatWeather;
}

export interface AgroAdvisory {
  id: number;
  panchayat_id: number;
  panchayat_name?: string;
  crop_name: string;
  crop_stage?: string;
  category: string;
  priority: AdvisoryPriority;
  urgency: string;
  title: string;
  action_summary: string;
  action_details?: string[];
  optimal_window?: string;
  trigger_risk_name?: string;
  scientific_rationale?: string;
  conflict_flag?: boolean;
  conflict_reason?: string;
  expert_review_required?: boolean;
  rule_version?: string;
  model_version?: string;
  evidence_metrics?: Record<string, any>;
}

export interface AgriculturalRisk {
  id: number;
  panchayat_id: number;
  panchayat_name?: string;
  crop_name: string;
  hazard_type: string;
  risk_name: string;
  severity: RiskSeverity;
  risk_score: number;
  description: string;
  trigger_value: string;
  threshold_value: string;
  confidence?: string;
}

export interface GridCell {
  cell_id: number;
  panchayat_id?: number;
  panchayat_name?: string;
  latitude: number;
  longitude: number;
  tmax_c: number;
  tmin_c: number;
  tmean_c: number;
  predicted_residual: number;
  elevation_m: number;
  slope_deg: number;
  aspect_deg: number;
  cropland_fraction: number;
}

export interface ModelMetrics {
  version: string;
  algorithm: string;
  test_mae: number;
  test_rmse: number;
  test_r2: number;
  feature_importances: Record<string, number>;
  status?: string;
}

export interface PanchayatDetailPayload {
  panchayat: Panchayat;
  latest_weather: PanchayatWeather;
  agricultural_contexts: any[];
  detected_risks: AgriculturalRisk[];
  active_advisories: AgroAdvisory[];
}
