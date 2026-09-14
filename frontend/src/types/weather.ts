export interface PanchayatWeatherSummary {
  panchayat_id: number;
  panchayat_name: string;
  lgd_code: string;
  block_id: number;
  block_name: string;
  forecast_valid_time: string;
  forecast_issue_time: string;
  source_model: string;
  model_version: string;
  grid_resolution_km: number;
  mean_temperature_c?: number;
  min_temperature_c?: number;
  max_temperature_c?: number;
  median_temperature_c?: number;
  temperature_stddev_c?: number;
  temperature_p10_c?: number;
  temperature_p90_c?: number;
  mean_residual_c?: number;
  total_panchayat_area_sqkm?: number;
  covered_area_sqkm?: number;
  coverage_percentage?: number;
  contributing_grid_cells?: number;
  valid_grid_cells?: number;
  quality_status: 'COMPLETE' | 'PARTIAL' | 'UNAVAILABLE';
  quality_flags: string[];
  aggregation_method: string;
  aggregation_crs: string;
  cropland_weighted_mean_temp_c?: number;
  created_at: string;
}

export interface GridCellRecord {
  cell_id: string;
  latitude: number;
  longitude: number;
  elevation_m?: number;
  slope_deg?: number;
  aspect_deg?: number;
  cropland_fraction?: number;
  coarse_temperature_c?: number;
  predicted_residual_c?: number;
  downscaled_temperature_c?: number;
  model_version?: string;
  quality_flag?: string;
}
