import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { BlockItem } from '../types/index.js';
import { ApiService, subscribeConnectionStatus, getIsLiveBackend } from '../services/api.js';

export type UserRole = 'FARMER' | 'OFFICER' | 'ADMIN';

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
  loadingBlocks: boolean;
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
  const [loadingBlocks, setLoadingBlocks] = useState<boolean>(true);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(getIsLiveBackend());

  const triggerRefresh = () => setRefreshKey((prev) => prev + 1);

  useEffect(() => {
    const unsubscribe = subscribeConnectionStatus((isLive) => {
      setIsLiveApi(isLive);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    let isMounted = true;
    async function loadBlocks() {
      try {
        setLoadingBlocks(true);
        const data = await ApiService.getBlocks();
        if (isMounted) {
          setBlocks(data);
          if (data.length > 0 && selectedBlockId === null) {
            setSelectedBlockId(data[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load blocks:', err);
      } finally {
        if (isMounted) setLoadingBlocks(false);
      }
    }
    loadBlocks();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

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
        loadingBlocks,
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
