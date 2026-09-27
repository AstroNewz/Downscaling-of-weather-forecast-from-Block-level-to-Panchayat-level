/**
 * Unified Forecast API Client
 * SIH Problem Statement 26074 (Weather Downscaling & Agromet Advisory)
 */
import { apiClient } from './client';

export interface LocationItem {
  id: string;
  name: string;
  type: string;
  block_name: string;
  district_name: string;
  state_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  primary_crops?: string[];
}

export interface CurrentWeather {
  temperature_c: number;
  coarse_temp_c: number;
  dynamic_residual_c: number;
  feels_like_c: number;
  humidity_pct: number;
  wind_speed_kmh: number;
  wind_direction_deg: number;
  precipitation_mm: number;
  weather_code: number;
  condition_text: string;
  icon_name: string;
  timestamp: string;
  model_used: string;
  fallback_active: boolean;
  fallback_reason?: string | null;
}

export interface HourlyForecastPoint {
  timestamp: string;
  local_time: string;
  hour: number;
  hour_label?: string;
  temperature_c: number;
  coarse_temp_c?: number;
  coarse_temperature?: number;
  coarse_temperature_c?: number;
  dynamic_residual_c?: number;
  dynamic_residual?: number;
  downscaled_temperature_c: number;
  downscaled_temperature?: number;
  humidity_pct: number;
  humidity?: number;
  precipitation_probability_pct: number;
  rain_probability?: number;
  rain_probability_pct?: number;
  precipitation_mm: number;
  precipitation?: number;
  weather_code: number;
  condition_text: string;
  icon_name: string;
  wind_speed_kmh: number;
  wind_speed?: number;
  wind_direction_deg: number;
  wind_direction?: number;
  model_used: string;
  fallback_active: boolean;
  risk?: string;
  advisory?: string;
}

export interface DailyForecastCard {
  date: string;
  formatted_date: string;
  day_label: string;
  display_label?: string;
  day_name?: string;
  is_today: boolean;
  t_max_c: number;
  temp_max_c?: number;
  t_min_c: number;
  temp_min_c?: number;
  coarse_max_c?: number;
  coarse_min_c?: number;
  precip_probability_pct: number;
  rain_probability_pct?: number;
  precip_sum_mm: number;
  rainfall_mm?: number;
  weather_code: number;
  condition_text: string;
  icon_name: string;
  primary_risk?: 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';
  is_selected?: boolean;
}

export interface AgriculturalRiskItem {
  id?: string;
  risk_type: string;
  category?: string;
  title?: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';
  status?: string;
  observed_value?: number;
  threshold_value?: number;
  unit?: string;
  trigger?: string;
  crop: string;
  crop_stage: string;
  condition: string;
  why: string;
  date?: string;
  location?: string;
}

export interface FarmerActionItem {
  id: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  category: string;
  title: string;
  timing: string;
  action: string;
  why: string;
  crop?: string;
  crop_stage?: string;
  risk?: string;
  weather_trigger?: string;
  date?: string;
  location?: string;
}

export interface ForecastProvenance {
  source_provider: string;
  source_type: string;
  issued_utc: string;
  retrieved_utc: string;
  data_age_minutes: number;
  live_request_id: string;
  model_used: string;
  candidate_id: string;
  certified_baseline_invariant: string;
  fallback_active: boolean;
  fallback_reason?: string | null;
  data_mode: 'DEMO' | 'LIVE' | 'AUTO';
  effective_mode: string;
  quality_status: string;
}

export interface UnifiedForecastResponse {
  location_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  forecast_date: string;
  forecast_hour: number;
  request_id: string;
  generated_at?: string;
  source_timestamp?: string;
  forecast_valid_time?: string;
  location: LocationItem;
  selected_date: string;
  selected_date_formatted: string;
  selected_date_label: string;
  is_today: boolean;
  current: CurrentWeather;
  today_hourly_chart: HourlyForecastPoint[];
  full_hourly: HourlyForecastPoint[];
  daily_forecast: DailyForecastCard[];
  agricultural_risks: AgriculturalRiskItem[];
  farmer_actions: FarmerActionItem[];
  provenance: ForecastProvenance;
  execution_latency_ms: number;
  precipitation_nowcast?: import('../types').LocalizedPrecipitationNowcast | null;
}

export interface LocationsResponse {
  locations: LocationItem[];
  total: number;
}

/**
 * Fetch unified forecast with anti-stale headers and abort signal support.
 */
export async function getUnifiedForecast(params: {
  locationId?: string;
  locationType?: string;
  targetDate?: string;
  startDate?: string;
  endDate?: string;
  timezone?: string;
  latitude?: number;
  longitude?: number;
  mode?: string;
  signal?: AbortSignal;
}): Promise<UnifiedForecastResponse> {
  const query = new URLSearchParams();
  if (params.locationId) query.append('location_id', params.locationId);
  if (params.locationType) query.append('location_type', params.locationType);
  if (params.targetDate) query.append('target_date', params.targetDate);
  if (params.startDate) query.append('start_date', params.startDate);
  if (params.endDate) query.append('end_date', params.endDate);
  if (params.timezone) query.append('timezone', params.timezone);
  if (params.latitude !== undefined) query.append('latitude', params.latitude.toString());
  if (params.longitude !== undefined) query.append('longitude', params.longitude.toString());
  if (params.mode) query.append('mode', params.mode);

  const endpoint = `/forecast?${query.toString()}`;
  return apiClient<UnifiedForecastResponse>(endpoint, {
    signal: params.signal,
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
    },
  });
}

/**
 * Fetch searchable preset locations (Panchayats, Blocks, Cities).
 */
export async function getSearchableLocations(): Promise<LocationItem[]> {
  try {
    const res = await apiClient<LocationsResponse>('/forecast/locations', {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
      },
    });
    return res.locations || [];
  } catch (err) {
    console.warn('[ForecastAPI] Failed to fetch searchable locations:', err);
    return [];
  }
}
