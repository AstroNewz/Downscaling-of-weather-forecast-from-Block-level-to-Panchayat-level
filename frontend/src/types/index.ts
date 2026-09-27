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

export type NowcastConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_DATA';

export type PrecipitationSourceState =
  | 'NWP_ONLY'
  | 'NWP_SATELLITE'
  | 'NWP_SATELLITE_RADAR'
  | 'NWP_SATELLITE_SURFACE_OBS'
  | 'NWP_SATELLITE_RADAR_SURFACE_OBS'
  | 'INSUFFICIENT_DATA';

export interface NowcastHorizon {
  horizon_minutes: number;
  precipitation_probability: number;
  expected_precipitation_mm: number | null;
  confidence: NowcastConfidence;
  evidence_sources: string[];
  disagreement_detected: boolean;
  baseline_probability: number;
  baseline_precipitation_mm: number | null;
  satellite_derived_rate_mmh?: number | null;
  radar_derived_rate_mmh?: number | null;
}

export interface LocalizedPrecipitationNowcast {
  panchayat_id: string;
  panchayat_name?: string | null;
  block_id?: number | string | null;
  block_name?: string | null;
  district_name?: string | null;
  state_name?: string | null;
  issue_time: string;
  source_state: PrecipitationSourceState;
  primary_horizon: NowcastHorizon;
  horizons: NowcastHorizon[];
  confidence: NowcastConfidence;
  disagreement_detected: boolean;
  disagreement_reason?: string | null;
  observation_age_minutes?: number | null;
  satellite_observation_timestamp?: string | null;
  radar_observation_timestamp?: string | null;
  surface_observation_timestamp?: string | null;
  is_stale: boolean;
  spatial_coverage_fraction?: number | null;
  spatial_coverage_status?: string | null;
  native_source_resolution_km?: number | null;
  display_resolution_note?: string | null;
  method_version?: string | null;
  provenance?: {
    satellite_provider?: string | null;
    satellite_product_id?: string | null;
    radar_station_id?: string | null;
    nwp_model?: string | null;
    fusion_algorithm?: string | null;
    pipeline_step?: string | null;
  };
  success: boolean;
  data_quality_notes?: string | null;
}

export interface LocalizedAdvisoryEvidence {
  panchayat_id: string;
  valid_time: string;
  horizon_minutes: number;
  rain_probability: number;
  expected_amount_mm: number | null;
  confidence: string;
  source_state: string;
  evidence_sources: string[];
  evidence_disagreement: boolean;
  disagreement_reason?: string | null;
  spatial_coverage: number;
  observation_age_minutes: number;
  method_version?: string;
  provenance?: Record<string, any>;
}

export interface NowcastAdvisoryExplanation {
  primary_reason: string;
  localized_precipitation_signal: string;
  baseline_signal: string;
  evidence_agreement: boolean;
  confidence: string;
  action_strength: string;
  recommended_horizon_minutes: number;
  short_horizon_recommendation?: string | null;
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
  model_used?: string;
  model_status?: string;
  operational_residual_c?: number;
  coarse_temperature_c?: number;
  fallback_active?: boolean;
  fallback_reason?: string;
  safety_status?: string;
  ood_status?: string;
  source_provider?: string;
  source_type?: string;
  source_timestamp?: string;
  retrieval_timestamp?: string;
  live_request_id?: string;
  data_mode?: string;
  effective_mode?: string;
  target_date?: string;
  precipitation_nowcast?: LocalizedPrecipitationNowcast | null;
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
  model_used?: string;
  source_provider?: string;
  source_timestamp?: string;
  retrieval_timestamp?: string;
  forecast_timestamp?: string;
  live_request_id?: string;
  fallback_active?: boolean;
  localized_nowcast_context?: LocalizedAdvisoryEvidence | null;
  baseline_precipitation_context?: Record<string, any> | null;
  nowcast_advisory_state?: string | null;
  nowcast_explanation?: NowcastAdvisoryExplanation | null;
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
  precipitation_nowcast?: LocalizedPrecipitationNowcast | null;
}

export interface ProviderInfo {
  name: string;
  code: string;
  status: 'LIVE' | 'NOT_CONFIGURED' | 'UNAVAILABLE' | 'STALE' | 'QC_FAILED' | 'AUTH_FAILED';
  source_type: string;
  configured: boolean;
  requires_auth: boolean;
  auth_configured: boolean;
  endpoint: string;
  supported_products: string[];
  description: string;
  coverage: string;
  geographic_coverage: string;
  licensing: string;
  configuration_instructions?: string;
}

export interface ProviderHealth {
  provider: string;
  status: 'LIVE' | 'NOT_CONFIGURED' | 'UNAVAILABLE' | 'STALE' | 'QC_FAILED' | 'AUTH_FAILED';
  source_type: string;
  configured: boolean;
  latency_ms?: number | null;
  source_timestamp?: string | null;
  retrieved_at: string;
  data_age_minutes?: number | null;
  location?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  variables: string[];
  qc_status: string;
  freshness_status: string;
  fallback_active: boolean;
  fallback_reason?: string | null;
  request_id?: string | null;
  error_message?: string | null;
  required_configuration?: Record<string, string> | null;
}

export interface NationalValidationSummary {
  system: string;
  evaluation_date: string;
  claim_language: string;
  coverage_status: string;
  total_observations: number;
  test_observations: number;
  station_count: number;
  states_covered: number;
  regions_evaluated: number;
  regions_unvalidated: number;
  regional_hierarchy: Record<string, any>;
  stations_catalog: Array<{
    id: string;
    name: string;
    region: string;
    lat: number;
    lon: number;
    elev: number;
    state: string;
    physiographic_regime: string;
  }>;
  overall_models: Record<string, any>;
  paired_eval: Record<string, any>;
  regional_breakdown: Array<{
    region: string;
    sample_count: number;
    station_count: number;
    raw_nwp_mae?: number | null;
    baseline_mae?: number | null;
    dynamic_v2_mae?: number | null;
    improvement?: number | null;
    ci_95?: number[] | null;
    status: string;
  }>;
  elevation_breakdown: Array<any>;
  holdouts: Record<string, any>;
  critical_findings: Record<string, any>;
}

export interface PromotionEvaluationSummary {
  evaluation_title: string;
  date: string;
  active_certified_baseline: string;
  evaluated_candidate: string;
  models_evaluated: Record<string, any>;
  paired_performance: Record<string, any>;
  promotion_gates: Array<{
    gate_id: string;
    name: string;
    description: string;
    threshold: string;
    actual_value: string;
    passed: boolean;
    scientific_note: string;
  }>;
  passed_gates_count: number;
  failed_gates_count: number;
  sensor_uncertainty_analysis: Record<string, any>;
  final_scientific_decision: 'PRODUCTION_CANDIDATE' | 'RETAIN_FOR_RESEARCH';
  operational_deployment_state: string;
  rollout_architecture: string;
  actionable_recommendation: string;
}

export interface BlockAggregationPayload {
  block_id: number;
  block_name: string;
  panchayat_count: number;
  target_date: string;
  forecast_time: string;
  aggregation_method: string;
  temperature_statistics: {
    mean_downscaled_c: number;
    min_downscaled_c: number;
    max_downscaled_c: number;
    spatial_spread_c: number;
    mean_coarse_nwp_c: number;
    mean_dynamic_residual_c: number;
  };
  atmospheric_statistics: {
    mean_relative_humidity_pct: number;
    mean_wind_speed_kmh: number;
  };
  risk_statistics: {
    total_detected_risks: number;
    severity_breakdown: Record<string, number>;
  };
  advisories_summary: {
    total_advisories_emitted: number;
    sample_advisories: any[];
  };
  constituent_panchayats: Array<{
    panchayat_id: number;
    panchayat_name: string;
    latitude: number;
    longitude: number;
    elevation_m: number;
    downscaled_temperature_c: number;
    dynamic_residual_c: number;
    coarse_temperature_c: number;
    relative_humidity_pct: number;
    wind_speed_kmh: number;
    rainfall_mm: number;
    model_used: string;
    live_request_id?: string;
  }>;
  data_provenance: {
    mode: string;
    model_used: string;
    fallback_active: boolean;
    latest_request_id?: string;
  };
}
