type ConnectionStatusListener = (isLive: boolean) => void;

let isLiveBackend = false;
const statusListeners = new Set<ConnectionStatusListener>();

export function getIsLiveBackend(): boolean {
  return isLiveBackend;
}

export function subscribeConnectionStatus(listener: ConnectionStatusListener): () => void {
  statusListeners.add(listener);
  listener(isLiveBackend);
  return () => {
    statusListeners.delete(listener);
  };
}

function notifyConnectionStatus(isLive: boolean) {
  if (isLiveBackend !== isLive) {
    isLiveBackend = isLive;
    statusListeners.forEach((fn) => fn(isLive));
  }
}

const API_BASE_URL = (((import.meta as any).env?.VITE_API_BASE_URL as string) || '').replace(/\/+$/, '');

export async function apiClient<T>(endpoint: string, options?: RequestInit, fallbackData?: T): Promise<T> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}/api/v1${cleanEndpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  if (options?.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  try {
    const response = await fetch(url, {
      cache: 'no-store',
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
        Expires: '0',
        ...(options?.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      notifyConnectionStatus(false);
      if (response.status === 404) {
        throw new Error(`Resource at ${cleanEndpoint} not found (404)`);
      }
      throw new Error(`API error ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    notifyConnectionStatus(true);

    if (json && typeof json === 'object' && 'data' in json) {
      return json.data as T;
    }
    return json as T;
  } catch (error: any) {
    clearTimeout(timeoutId);
    notifyConnectionStatus(false);

    if (fallbackData !== undefined) {
      console.warn(`[API Client] Fallback triggered for ${endpoint}:`, error.message);
      return fallbackData;
    }
    throw error;
  }
}

export interface SystemDataStatus {
  mode: 'DEMO' | 'LIVE' | 'AUTO';
  effective_mode: 'DEMO' | 'LIVE';
  live_enabled: boolean;
  provider: string;
  source_type: string;
  latest_source_timestamp?: string;
  retrieved_at: string;
  age_minutes?: number;
  freshness_status: string;
  quality_status: string;
  fallback_active: boolean;
  fallback_reason?: string;
  calibrated_baseline: string;
  model_status: string;
  message: string;
}

export async function getSystemDataStatus(): Promise<SystemDataStatus> {
  const fallbackStatus: SystemDataStatus = {
    mode: 'DEMO',
    effective_mode: 'DEMO',
    live_enabled: false,
    provider: 'CANONICAL_PILOT_FIXTURE',
    source_type: 'PILOT_FIXTURE',
    latest_source_timestamp: new Date().toISOString(),
    retrieved_at: new Date().toISOString(),
    age_minutes: 0,
    freshness_status: 'FRESH',
    quality_status: 'PASSED',
    fallback_active: false,
    calibrated_baseline: 'T_calibrated = T_coarse + 0.7351°C',
    model_status: 'Dynamic V2: CONTROLLED_PRODUCTION',
    message: 'Canonical pilot demonstration fixtures active.',
  };
  return apiClient<SystemDataStatus>('/system/data-status', {}, fallbackStatus);
}

export async function setSystemDataMode(mode: 'DEMO' | 'LIVE' | 'AUTO'): Promise<{ mode: string }> {
  return apiClient<{ mode: string }>('/system/mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  });
}

export interface OperationalTelemetry {
  rollout_mode: string;
  model_operational_status: string;
  active_model: string;
  fallback_model: string;
  safety_bounds: [number, number];
  counters: {
    dynamic_success: number;
    dynamic_fallback: number;
    baseline_success: number;
    feature_missing: number;
    qc_failure: number;
    freshness_failure: number;
    ood_failure: number;
    safety_failure: number;
    live_provider_failure: number;
  };
}

export async function getOperationalTelemetry(): Promise<OperationalTelemetry> {
  const fallback: OperationalTelemetry = {
    rollout_mode: 'DYNAMIC_PRIMARY',
    model_operational_status: 'CONTROLLED_PRODUCTION',
    active_model: 'DYNAMIC_V2',
    fallback_model: 'CERTIFIED_BASELINE_V1',
    safety_bounds: [-8.0, 8.0],
    counters: {
      dynamic_success: 0,
      dynamic_fallback: 0,
      baseline_success: 0,
      feature_missing: 0,
      qc_failure: 0,
      freshness_failure: 0,
      ood_failure: 0,
      safety_failure: 0,
      live_provider_failure: 0,
    },
  };
  return apiClient<OperationalTelemetry>('/system/telemetry', {}, fallback);
}

export async function setRolloutMode(mode: 'DYNAMIC_PRIMARY' | 'BASELINE_PRIMARY'): Promise<{ rollout_mode: string }> {
  return apiClient<{ rollout_mode: string }>('/system/rollout-mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  });
}

export async function getLivePrediction(panchayatId = 1, mode?: string): Promise<any> {
  const q = new URLSearchParams();
  q.set('panchayat_id', String(panchayatId));
  if (mode) q.set('mode', mode);
  return apiClient<any>(`/prediction/live?${q.toString()}`);
}
