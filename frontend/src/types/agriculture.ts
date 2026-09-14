export interface CropStageContext {
  phenology_stage_id?: number;
  stage_name?: string;
  stage_order?: number;
  gdd_required?: number;
  water_sensitivity?: string;
  temp_sensitivity?: string;
  stage_derivation_method: string;
  planting_date?: string;
  days_since_planting?: number;
  expected_harvest_date?: string;
  is_stage_resolved: boolean;
}

export interface SoilContextSummary {
  soil_profile_id?: number;
  soil_type?: string;
  texture?: string;
  drainage_class?: string;
  water_holding_capacity_pct?: number;
  ph_level?: number;
  organic_carbon_pct?: number;
  available_nitrogen_kg_ha?: number;
  available_phosphorus_kg_ha?: number;
  available_potassium_kg_ha?: number;
  soil_available: boolean;
  soil_status: string;
}

export interface WeatherContextSummary {
  panchayat_weather_id?: number;
  forecast_valid_time?: string;
  mean_temp_c?: number;
  min_temp_c?: number;
  max_temp_c?: number;
  temp_stddev_c?: number;
  weather_status?: string;
}

export interface PanchayatCropContextSummary {
  id: number;
  panchayat_id: number;
  panchayat_name: string;
  block_id: number;
  block_name?: string;
  crop_id: number;
  crop_name: string;
  scientific_name?: string;
  season?: string;
  crop_stage: CropStageContext;
  soil: SoilContextSummary;
  weather: WeatherContextSummary;
  crop_area_ha?: number;
  agricultural_area_ha?: number;
  crop_fraction?: number;
  is_agricultural_eligible: boolean;
  context_date: string;
  source: string;
  source_version?: string;
  confidence_score?: number;
  status: string;
  quality_flags: string[];
  provenance?: Record<string, any>;
  created_at: string;
}

export interface PanchayatAgriculturalProfile {
  panchayat_id: number;
  panchayat_name: string;
  lgd_code: string;
  block_id: number;
  block_name?: string;
  is_agricultural_eligible: boolean;
  total_cropland_area_ha: number;
  context_date: string;
  crops: PanchayatCropContextSummary[];
}
