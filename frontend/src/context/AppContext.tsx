import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { BlockItem, Panchayat, UserRole } from '../types';
import { subscribeConnectionStatus, getIsLiveBackend } from '../api/client';
import { getBlocks, getPanchayats } from '../api/panchayat';

interface AppContextType {
  selectedBlockId: number | null;
  setSelectedBlockId: (id: number | null) => void;
  selectedPanchayatId: number | null;
  setSelectedPanchayatId: (id: number | null) => void;
  targetDate: string;
  setTargetDate: (date: string) => void;
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
  blocks: BlockItem[];
  panchayats: Panchayat[];
  selectedPanchayat: Panchayat | null;
  loadingData: boolean;
  refreshKey: number;
  triggerRefresh: () => void;
  isLiveApi: boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(1);
  const [selectedPanchayatId, setSelectedPanchayatId] = useState<number | null>(1);
  const [targetDate, setTargetDate] = useState<string>('2026-07-15');
  const [userRole, setUserRole] = useState<UserRole>('OFFICER');
  const [blocks, setBlocks] = useState<BlockItem[]>([]);
  const [panchayats, setPanchayats] = useState<Panchayat[]>([]);
  const [loadingData, setLoadingData] = useState<boolean>(true);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(getIsLiveBackend());

  const triggerRefresh = () => setRefreshKey((prev) => prev + 1);

  // Connection status subscription
  useEffect(() => {
    return subscribeConnectionStatus((isLive) => {
      setIsLiveApi(isLive);
    });
  }, []);

  // Load Blocks & Initial Panchayats
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

          if (panchayatList.length > 0) {
            // Keep current selection if valid, else pick first
            if (!selectedPanchayatId || !panchayatList.some((p) => p.id === selectedPanchayatId)) {
              setSelectedPanchayatId(panchayatList[0].id);
            }
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

  // Derived selected Panchayat object
  const selectedPanchayat = panchayats.find((p) => p.id === selectedPanchayatId) || panchayats[0] || null;

  return (
    <AppContext.Provider
      value={{
        selectedBlockId,
        setSelectedBlockId,
        selectedPanchayatId,
        setSelectedPanchayatId,
        targetDate,
        setTargetDate,
        userRole,
        setUserRole,
        blocks,
        panchayats,
        selectedPanchayat,
        loadingData,
        refreshKey,
        triggerRefresh,
        isLiveApi,
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
