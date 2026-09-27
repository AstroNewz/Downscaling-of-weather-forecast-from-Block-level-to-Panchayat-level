import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { BlockItem, Panchayat, UserRole } from '../types';
import { subscribeConnectionStatus, getIsLiveBackend, getSystemDataStatus, setSystemDataMode, SystemDataStatus } from '../api/client';
import { getBlocks, getPanchayats } from '../api/panchayat';
import {
  UnifiedForecastResponse,
  LocationItem,
  getUnifiedForecast,
  getSearchableLocations,
} from '../api/forecast';

export type ViewMode = 'FARMER' | 'TECHNICAL';

interface AppContextType {
  // Legacy Panchayat & Block state (preserved for backward compatibility)
  selectedBlockId: number | null;
  setSelectedBlockId: (id: number | null) => void;
  selectedPanchayatId: number | null;
  setSelectedPanchayatId: (id: number | null) => void;
  blocks: BlockItem[];
  panchayats: Panchayat[];
  selectedPanchayat: Panchayat | null;
  loadingData: boolean;

  // Global Date & Dynamic Date state
  todayDate: string;
  targetDate: string;
  setTargetDate: (date: string) => void;

  // Global Location Selection state
  selectedLocationId: string;
  setSelectedLocationId: (id: string) => void;
  selectedLocation: LocationItem | null;
  setSelectedLocation: (loc: LocationItem) => void;
  searchableLocations: LocationItem[];

  // Unified Forecast State Machine
  forecast: UnifiedForecastResponse | null;
  forecastLoading: boolean;
  forecastError: string | null;
  refetchForecast: () => Promise<void>;

  // View Mode: Farmer (Simple) vs Technical (Scientific)
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // System & Connection State
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
  refreshKey: number;
  triggerRefresh: () => void;
  isLiveApi: boolean;
  dataStatus: SystemDataStatus | null;
  dataMode: 'DEMO' | 'LIVE' | 'AUTO';
  switchDataMode: (mode: 'DEMO' | 'LIVE' | 'AUTO') => Promise<void>;
  isLiveWeather: boolean;
  isFallbackActive: boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Dynamically derive today's date in YYYY-MM-DD from system clock
  const getTodayISO = () => new Date().toISOString().split('T')[0];
  const [todayDate] = useState<string>(getTodayISO());
  const [targetDate, setTargetDate] = useState<string>(getTodayISO());

  // Global Location State (defaults to Maya Bazar Panchayat, id='1')
  const [selectedLocationId, setSelectedLocationId] = useState<string>('1');
  const [selectedLocation, setSelectedLocation] = useState<LocationItem | null>(null);
  const [searchableLocations, setSearchableLocations] = useState<LocationItem[]>([]);

  // Unified Forecast State
  const [forecast, setForecast] = useState<UnifiedForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState<boolean>(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // View Mode
  const [viewMode, setViewMode] = useState<ViewMode>('FARMER');

  // Legacy Block/Panchayat state
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(1);
  const [selectedPanchayatId, setSelectedPanchayatId] = useState<number | null>(1);
  const [userRole, setUserRole] = useState<UserRole>('OFFICER');
  const [blocks, setBlocks] = useState<BlockItem[]>([]);
  const [panchayats, setPanchayats] = useState<Panchayat[]>([]);
  const [loadingData, setLoadingData] = useState<boolean>(true);

  // Connection & Provenance
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(getIsLiveBackend());
  const [dataStatus, setDataStatus] = useState<SystemDataStatus | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const triggerRefresh = () => setRefreshKey((prev) => prev + 1);

  // 1. Connection status subscription
  useEffect(() => {
    return subscribeConnectionStatus((isLive) => {
      setIsLiveApi(isLive);
    });
  }, []);

  // 2. Poll system data-source status
  useEffect(() => {
    let isMounted = true;
    async function fetchStatus() {
      try {
        const status = await getSystemDataStatus();
        if (isMounted) {
          setDataStatus(status);
        }
      } catch (err) {
        console.warn('[AppContext] Failed to query system data-status:', err);
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshKey]);

  // 3. Load searchable preset locations
  useEffect(() => {
    let isMounted = true;
    async function loadLocations() {
      try {
        const locs = await getSearchableLocations();
        if (isMounted && locs.length > 0) {
          setSearchableLocations(locs);
          const initial = locs.find((l) => l.id === selectedLocationId) || locs[0];
          setSelectedLocation(initial);
        }
      } catch (err) {
        console.warn('[AppContext] Failed to load preset locations:', err);
      }
    }
    loadLocations();
    return () => {
      isMounted = false;
    };
  }, []);

  // 4. Load Blocks & Initial Panchayats (legacy support)
  useEffect(() => {
    let isMounted = true;
    async function loadInitialData() {
      try {
        setLoadingData(true);
        const [blockList, panchayatList] = await Promise.all([
          getBlocks(),
          getPanchayats(selectedBlockId || undefined),
        ]);
        if (isMounted) {
          setBlocks(blockList);
          setPanchayats(panchayatList);
          if (panchayatList.length > 0 && (!selectedPanchayatId || !panchayatList.some((p) => p.id === selectedPanchayatId))) {
            setSelectedPanchayatId(panchayatList[0].id);
          }
        }
      } catch (err) {
        console.error('[AppContext] Failed to load initial data:', err);
      } finally {
        if (isMounted) setLoadingData(false);
      }
    }

    loadInitialData();
    return () => {
      isMounted = false;
    };
  }, [selectedBlockId, refreshKey]);

  // 5. UNIFIED REACTIVE FORECAST PIPELINE
  // When selectedLocationId, targetDate, or refreshKey changes, trigger live forecast request
  const fetchForecastData = async () => {
    // Abort any ongoing request to prevent stale out-of-order race conditions
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      setForecastLoading(true);
      setForecastError(null);
      // Immediately clear previous forecast state so skeletons show and stale data does not leak
      setForecast(null);

      const mode = dataStatus?.mode || 'AUTO';
      const result = await getUnifiedForecast({
        locationId: selectedLocationId,
        targetDate: targetDate,
        mode: mode,
        signal: controller.signal,
      });

      // Strict validation: verify response location corresponds to current selection
      const matchesLocation =
        result.location_id === selectedLocationId ||
        (result.location && result.location.id === selectedLocationId) ||
        (result.location && result.location.name.toLowerCase().includes(selectedLocationId.toLowerCase())) ||
        (selectedLocation && result.location_name && (
          selectedLocation.name.toLowerCase().includes(result.location_name.toLowerCase()) ||
          result.location_name.toLowerCase().includes(selectedLocation.name.toLowerCase())
        ));

      if (!matchesLocation) {
        console.warn(`[AppContext] Stale response rejected: received ${result.location_name} (${result.location_id}), expected ${selectedLocationId}`);
        return;
      }

      setForecast(result);
      if (result.location) {
        setSelectedLocation(result.location);
        const parsedId = parseInt(result.location.id, 10);
        if (!isNaN(parsedId)) {
          setSelectedPanchayatId(parsedId);
        }
      }
    } catch (err: any) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        // Request was aborted by newer selection; ignore cleanly
        return;
      }
      console.error('[AppContext] Failed to fetch unified forecast:', err);
      setForecastError(err.message || 'Failed to retrieve forecast data');
    } finally {
      setForecastLoading(false);
    }
  };

  useEffect(() => {
    fetchForecastData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [selectedLocationId, targetDate, refreshKey, dataStatus?.mode]);

  const switchDataMode = async (mode: 'DEMO' | 'LIVE' | 'AUTO') => {
    try {
      await setSystemDataMode(mode);
      const updated = await getSystemDataStatus();
      setDataStatus(updated);
      triggerRefresh();
    } catch (err) {
      console.error('[AppContext] Failed to switch data mode:', err);
    }
  };

  // Derived selected Panchayat object (legacy)
  const selectedPanchayat = panchayats.find((p) => p.id === selectedPanchayatId) || panchayats[0] || null;
  const dataMode = dataStatus?.mode || 'DEMO';
  const isLiveWeather = dataStatus?.effective_mode === 'LIVE' || forecast?.provenance?.source_type === 'FORECAST';
  const isFallbackActive = dataStatus?.fallback_active ?? forecast?.provenance?.fallback_active ?? false;

  return (
    <AppContext.Provider
      value={{
        selectedBlockId,
        setSelectedBlockId,
        selectedPanchayatId,
        setSelectedPanchayatId,
        blocks,
        panchayats,
        selectedPanchayat,
        loadingData,

        todayDate,
        targetDate,
        setTargetDate,

        selectedLocationId,
        setSelectedLocationId,
        selectedLocation,
        setSelectedLocation,
        searchableLocations,

        forecast,
        forecastLoading,
        forecastError,
        refetchForecast: fetchForecastData,

        viewMode,
        setViewMode,

        userRole,
        setUserRole,
        refreshKey,
        triggerRefresh,
        isLiveApi,
        dataStatus,
        dataMode,
        switchDataMode,
        isLiveWeather,
        isFallbackActive,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
