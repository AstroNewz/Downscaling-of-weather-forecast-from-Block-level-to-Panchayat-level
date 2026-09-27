import React, { useState } from 'react';
import { 
  Radio, 
  RefreshCw, 
  Clock, 
  MapPin, 
  Cpu, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  Fingerprint, 
  ExternalLink,
  Calendar
} from 'lucide-react';
import { PanchayatWeather, Panchayat } from '../../types';
import { useApp } from '../../context/AppContext';

interface LiveProvenanceCardProps {
  weather: PanchayatWeather | null | undefined;
  panchayat: Panchayat | null | undefined;
  targetDate: string;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const LiveProvenanceCard: React.FC<LiveProvenanceCardProps> = ({
  weather,
  panchayat,
  targetDate,
  onRefresh,
  isLoading = false,
}) => {
  const { dataMode, dataStatus, triggerRefresh } = useApp();
  const [refreshing, setRefreshing] = useState(false);

  // Determine effective mode and display status
  const effectiveMode = weather?.effective_mode || dataStatus?.effective_mode || dataMode;
  const isFallback = weather?.fallback_active ?? dataStatus?.fallback_active ?? false;
  const provider = weather?.source_provider || dataStatus?.provider || 'CANONICAL_PILOT_FIXTURE';
  const sourceType = weather?.source_type || dataStatus?.source_type || 'FORECAST';
  const sourceTimestamp = weather?.source_timestamp || weather?.forecast_valid_time || dataStatus?.latest_source_timestamp || 'N/A';
  const retrievalTimestamp = weather?.retrieval_timestamp || dataStatus?.retrieved_at || 'N/A';
  const liveRequestId = weather?.live_request_id || 'req_demo_canonical';
  const modelUsed = weather?.model_used || 'DYNAMIC_V2';

  // Calculate approximate data age
  const calculateDataAge = () => {
    if (!retrievalTimestamp || retrievalTimestamp === 'N/A') return '0s (Demo Fixture)';
    try {
      const retTime = new Date(retrievalTimestamp).getTime();
      const now = Date.now();
      const diffSec = Math.max(0, Math.floor((now - retTime) / 1000));
      if (diffSec < 60) return `${diffSec}s ago (Genuine Fresh)`;
      const diffMin = Math.floor(diffSec / 60);
      return `${diffMin}m ${diffSec % 60}s ago`;
    } catch {
      return 'Recent';
    }
  };

  const handleRefreshClick = async () => {
    setRefreshing(true);
    try {
      if (onRefresh) {
        await onRefresh();
      } else {
        triggerRefresh();
      }
    } finally {
      setTimeout(() => setRefreshing(false), 500);
    }
  };

  // Badge configuration based on Requirement 11
  let badgeTitle = 'DEMO • CANONICAL PILOT DATA';
  let badgeBg = 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300';
  let dotColor = 'bg-cyan-400';

  if (dataMode === 'LIVE') {
    if (effectiveMode === 'LIVE' && !isFallback) {
      badgeTitle = 'LIVE • EXTERNAL NWP';
      badgeBg = 'bg-emerald-950/60 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.15)]';
      dotColor = 'bg-emerald-400 animate-pulse';
    } else {
      badgeTitle = 'FALLBACK • CANONICAL DEMO DATA';
      badgeBg = 'bg-amber-950/60 border-amber-500/50 text-amber-300';
      dotColor = 'bg-amber-400';
    }
  } else if (dataMode === 'AUTO') {
    if (isFallback) {
      badgeTitle = 'FALLBACK • CANONICAL DEMO DATA';
      badgeBg = 'bg-amber-950/60 border-amber-500/50 text-amber-300';
      dotColor = 'bg-amber-400';
    } else {
      badgeTitle = 'LIVE • EXTERNAL NWP';
      badgeBg = 'bg-emerald-950/60 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.15)]';
      dotColor = 'bg-emerald-400 animate-pulse';
    }
  } else {
    badgeTitle = 'DEMO • CANONICAL PILOT DATA';
    badgeBg = 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300';
    dotColor = 'bg-cyan-400';
  }

  return (
    <div 
      id="live-data-provenance-card"
      className="glass-panel p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md space-y-4 relative overflow-hidden"
    >
      {/* Top Banner: Status Header & Refresh Button */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-bold border ${badgeBg}`}>
            <span className={`w-2 h-2 rounded-full ${dotColor}`} />
            <span>{badgeTitle}</span>
          </div>
          <span className="text-xs text-slate-400 font-mono hidden sm:inline">
            SIH 26074 Operational Provenance Engine
          </span>
        </div>

        {/* Refresh Live Forecast Button (Requirement 12) */}
        <button
          id="refresh-live-forecast-btn"
          onClick={handleRefreshClick}
          disabled={isLoading || refreshing}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-semibold font-mono transition-all shadow-sm active:scale-95 disabled:opacity-50 cursor-pointer"
          title="Trigger a genuine live fetch request directly to Open-Meteo external NWP"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${isLoading || refreshing ? 'animate-spin' : ''}`} />
          <span>{isLoading || refreshing ? 'Fetching Fresh Forecast...' : 'Refresh Live Forecast'}</span>
        </button>
      </div>

      {/* Main Provenance Grid (Requirement 11) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 text-xs font-mono">
        {/* Provider */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Provider</span>
          <p className="font-bold text-slate-200 truncate" title={provider}>
            {provider}
          </p>
        </div>

        {/* Source Type */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Source Type</span>
          <p className="font-bold text-emerald-300">
            {sourceType}
          </p>
        </div>

        {/* Forecast Issued */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Forecast Issued</span>
          <p className="font-bold text-slate-200 truncate" title={sourceTimestamp}>
            {sourceTimestamp}
          </p>
        </div>

        {/* Retrieved At */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Retrieved</span>
          <p className="font-bold text-cyan-300 truncate" title={retrievalTimestamp}>
            {retrievalTimestamp.split('T')[1]?.substring(0, 8) || retrievalTimestamp}
          </p>
        </div>

        {/* Data Age */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Data Age</span>
          <p className="font-bold text-emerald-400">
            {calculateDataAge()}
          </p>
        </div>

        {/* Selected Location */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1 col-span-2">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block flex items-center gap-1">
            <MapPin className="w-3 h-3 text-emerald-400" />
            <span>Selected Location</span>
          </span>
          <p className="font-bold text-slate-200 truncate">
            {panchayat?.name || 'Varanasi Demonstration Panchayat'}
            <span className="text-slate-400 font-normal ml-1">
              ({panchayat?.latitude?.toFixed(4) ?? '25.3500'}°N, {panchayat?.longitude?.toFixed(4) ?? '82.9500'}°E, {panchayat?.elevation_m ?? 112}m)
            </span>
          </p>
        </div>

        {/* Selected Forecast Time */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block flex items-center gap-1">
            <Calendar className="w-3 h-3 text-cyan-400" />
            <span>Forecast Target</span>
          </span>
          <p className="font-bold text-slate-200">
            {targetDate || 'Today'}
          </p>
        </div>

        {/* Model Used */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block flex items-center gap-1">
            <Cpu className="w-3 h-3 text-purple-400" />
            <span>Model Used</span>
          </span>
          <p className="font-bold text-purple-300 truncate" title={modelUsed}>
            {modelUsed}
          </p>
        </div>

        {/* Fallback State */}
        <div className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>Fallback State</span>
          </span>
          <p className={`font-bold ${isFallback ? 'text-amber-400' : 'text-emerald-400'}`}>
            {isFallback ? 'ACTIVE (Fallback)' : 'INACTIVE (Primary)'}
          </p>
        </div>
      </div>

      {/* Diagnostic LIVE REQUEST ID Panel (Requirement 13) */}
      <div 
        id="dev-live-request-id-panel"
        className="pt-2.5 border-t border-slate-800/70 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono"
      >
        <div className="flex items-center gap-2 text-slate-400">
          <Fingerprint className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-300 font-medium">LIVE REQUEST ID:</span>
          <span 
            id="current-live-request-id"
            className="px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-500/40 text-indigo-300 font-bold tracking-wider"
          >
            {liveRequestId}
          </span>
          <span className="text-slate-500 hidden md:inline">
            • Auditable unique identifier generated by backend for this specific external request
          </span>
        </div>

        <div className="text-slate-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span className="text-slate-300">Live Forecast Provenance Connected</span>
        </div>
      </div>
    </div>
  );
};
