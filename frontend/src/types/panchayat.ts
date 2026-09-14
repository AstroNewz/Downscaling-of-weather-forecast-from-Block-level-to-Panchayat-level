export interface LandUseComposition {
  total_area_hectares: number;
  cropland_area_hectares: number;
  forest_area_hectares?: number;
  urban_area_hectares?: number;
  water_bodies_hectares?: number;
  barren_area_hectares?: number;
  is_agricultural_eligible: boolean;
}

export interface PanchayatResponse {
  panchayat_id: string;
  name: string;
  block_id: string;
  district_name: string;
  state_name: string;
  latitude: number;
  longitude: number;
  elevation_meters?: number;
  land_use?: LandUseComposition | null;
}

export interface BlockItem {
  id: number;
  lgd_code: string;
  name: string;
  district_name: string;
  state_name: string;
  panchayats_count: number;
}

export interface PanchayatFullDetail {
  panchayat: {
    id: number;
    lgd_code: string;
    name: string;
    block_id: number;
    block_name?: string;
    district_name?: string;
    state_name?: string;
    elevation_meters?: number;
    latitude: number;
    longitude: number;
  };
  land_use?: {
    total_area_ha: number;
    cropland_area_ha: number;
    forest_area_ha: number;
    urban_area_ha: number;
    water_area_ha: number;
    barren_area_ha: number;
    is_agricultural_eligible: boolean;
  } | null;
  latest_weather?: {
    mean_temp_c?: number;
    min_temp_c?: number;
    max_temp_c?: number;
    temp_stddev_c?: number;
    mean_residual_c?: number;
    coverage_pct?: number;
    quality_status?: string;
    contributing_grid_cells?: number;
    valid_grid_cells?: number;
    forecast_valid_time?: string;
    source_model?: string;
    model_version?: string;
  } | null;
  crop_contexts: any[];
  risks: any[];
  advisories: any[];
}
