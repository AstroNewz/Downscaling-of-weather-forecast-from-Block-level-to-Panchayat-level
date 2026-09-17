export type UserRole = 'FARMER' | 'OFFICER' | 'ADMIN';

export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'NONE';

export type AdvisoryPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface BlockItem {
  id: number;
  name: string;
  lgd_code?: string;
  district?: string;
  district_name?: string;
  state_name?: string;
  panchayat_count?: number;
  panchayats_count?: number;
}

export interface PanchayatWeather {
  tmean_c: number;
  tmax_c: number;
  tmin_c: number;
  relative_humidity_pct: number;
  wind_speed_kmh: number;
  rainfall_mm: number;
  predicted_residual_delta_c: number;
  coverage_pct?: number;
  quality_status?: 'VALID' | 'DEGRADED' | 'MISSING';
  source_model?: string;
  model_version?: string;
  forecast_valid_time?: string;
}

export interface PanchayatLandUse {
  total_area_ha: number;
  cropland_area_ha: number;
  forest_area_ha?: number;
  urban_area_ha?: number;
  water_area_ha?: number;
  barren_area_ha?: number;
  is_agricultural_eligible: boolean;
}

export interface CropContext {
  crop_id?: number;
  crop_name: string;
  stage_name: string;
  variety?: string;
  sowing_date?: string;
  vulnerability_level?: 'EXTREME' | 'HIGH' | 'MODERATE' | 'LOW';
  critical_temperature_c?: number;
  critical_wind_speed_kmh?: number;
  soil_texture?: string;
  available_water_capacity_mm_m?: number;
  gdd_accumulated?: number;
  das?: number;
}

export interface AgriculturalRisk {
  id: number | string;
  panchayat_id: number | string;
  panchayat_name?: string;
  crop_name: string;
  stage_name: string;
  risk_type: string;
  risk_category: 'TEMPERATURE' | 'WIND' | 'MOISTURE' | 'PEST_DISEASE' | 'GENERAL';
  severity: RiskSeverity;
  status: 'DETECTED' | 'MONITORING' | 'RESOLVED' | 'CRITICAL';
  risk_score: number;
  observed_value?: number;
  threshold_value?: number;
  unit?: string;
  condition_description: string;
}

export interface AgroAdvisory {
  id: number | string;
  panchayat_id: number | string;
  crop_name: string;
  crop_stage: string;
  category: 'HEAT_STRESS' | 'IRRIGATION' | 'WIND' | 'PEST_DISEASE' | 'GENERAL';
  priority: AdvisoryPriority;
  priority_rank?: number;
  title: string;
  headline?: string;
  action_summary?: string;
  rationale: string;
  recommended_actions: string[];
  valid_from: string;
  valid_until: string;
  optimal_window?: string;
  conflict_flag?: boolean;
  expert_review_required?: boolean;
  evidence_metrics?: {
    tmax_c?: number;
    tmin_c?: number;
    rainfall_mm?: number;
    wind_kmh?: number;
    soil_moisture_pct?: number;
  };
  rule_version?: string;
  model_version?: string;
}

export interface GridCell {
  cell_id: string;
  latitude: number;
  longitude: number;
  elevation_m?: number;
  slope_deg?: number;
  aspect_deg?: number;
  cropland_fraction?: number;
  coarse_temperature_c?: number;
  predicted_residual?: number;
  predicted_residual_c?: number;
  downscaled_temperature_c?: number;
  tmean_c?: number;
  tmax_c?: number;
  tmin_c?: number;
  model_version?: string;
  quality_flag?: string;
}

export interface Panchayat {
  id: number;
  code: string;
  name: string;
  lgd_code?: string;
  block_id: number;
  block_name?: string;
  district_name?: string;
  state_name?: string;
  elevation_m?: number;
  latitude?: number;
  longitude?: number;
  centroid_lat?: number;
  centroid_lon?: number;
  is_cropland_eligible: boolean;
  cropland_ha?: number;
  total_area_ha?: number;
  active_crops_count?: number;
  active_risks_count?: number;
  highest_risk_severity?: RiskSeverity;
  latest_weather?: PanchayatWeather;
}

export interface PanchayatDetailPayload {
  panchayat: Panchayat;
  land_use?: PanchayatLandUse;
  latest_weather?: PanchayatWeather;
  agricultural_contexts: CropContext[];
  detected_risks: AgriculturalRisk[];
  active_advisories: AgroAdvisory[];
}
