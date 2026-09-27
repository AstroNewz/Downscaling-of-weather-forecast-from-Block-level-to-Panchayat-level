import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { GlobalLocationSearch } from '../common/GlobalLocationSearch';
import { 
  CloudSun, 
  RefreshCw, 
  Sparkles,
  UserCheck,
  Cpu
} from 'lucide-react';

export const Header: React.FC = () => {
  const {
    forecast,
    forecastLoading,
    refetchForecast,
    viewMode,
    setViewMode,
    isLiveApi,
    dataMode,
    isFallbackActive,
  } = useApp();

  const navigate = useNavigate();

  // Status badge logic
  const isLive = isLiveApi && dataMode === 'LIVE' && !isFallbackActive;
  const isFallback = isFallbackActive;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur-sm px-4 lg:px-6 py-2.5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 max-w-7xl mx-auto">
        {/* Left: Branding */}
        <div className="flex items-center gap-3">
          <div 
            onClick={() => navigate('/')} 
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 group-hover:scale-105 transition-transform shadow-xs">
              <CloudSun className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-slate-900 group-hover:text-blue-600 transition-colors">
                  AgroWeather
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700">
                  SIH 26074
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden sm:block">
                Live Agricultural Weather Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Center: Global Location Selector */}
        <div className="flex-1 max-w-md hidden sm:block">
          <GlobalLocationSearch />
        </div>

        {/* Right: Farmer vs Technical Toggle, Provenance Pill & Refresh */}
        <div className="flex items-center gap-2.5 ml-auto">
          {/* Mobile Location Selector fallback */}
          <div className="sm:hidden">
            <GlobalLocationSearch />
          </div>

          {/* Farmer View / Technical View Toggle */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              id="view-mode-farmer-btn"
              type="button"
              onClick={() => setViewMode('FARMER')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                viewMode === 'FARMER'
                  ? 'bg-white text-emerald-800 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Farmer View</span>
            </button>
            <button
              id="view-mode-technical-btn"
              type="button"
              onClick={() => setViewMode('TECHNICAL')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                viewMode === 'TECHNICAL'
                  ? 'bg-white text-blue-800 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Cpu className="w-3.5 h-3.5 text-blue-600" />
              <span>Technical View</span>
            </button>
          </div>

          {/* Compact Provenance Indicator */}
          <div
            id="header-provenance-indicator"
            title={
              forecast?.provenance
                ? `Source: ${forecast.provenance.source_provider} (${forecast.provenance.source_type}) | Retrieved: ${forecast.provenance.retrieved_utc}`
                : 'Connecting to NWP pipeline...'
            }
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium border cursor-help ${
              isLive
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : isFallback
                ? 'bg-amber-50 border-amber-200 text-amber-700'
                : 'bg-blue-50 border-blue-200 text-blue-700'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLive
                  ? 'bg-emerald-500 animate-pulse'
                  : isFallback
                  ? 'bg-amber-500'
                  : 'bg-blue-500'
              }`}
            />
            <span>
              {isLive
                ? 'LIVE • EXTERNAL NWP'
                : isFallback
                ? 'FALLBACK • BASELINE'
                : 'LIVE • EXTERNAL NWP'}
            </span>
          </div>

          {/* Refresh Action */}
          <button
            id="header-refresh-btn"
            onClick={() => refetchForecast()}
            disabled={forecastLoading}
            title="Refresh forecast data"
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-4 h-4 ${forecastLoading ? 'animate-spin text-blue-600' : ''}`} />
          </button>

          {/* Judge Mode Button */}
          <button
            id="header-judge-btn"
            onClick={() => navigate('/judge')}
            className="hidden lg:flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            <span>Judge Mode</span>
          </button>
        </div>
      </div>
    </header>
  );
};
