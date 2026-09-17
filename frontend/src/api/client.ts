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
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
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
