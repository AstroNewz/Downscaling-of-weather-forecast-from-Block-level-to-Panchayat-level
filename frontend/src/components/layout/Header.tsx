import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { 
  Radio, 
  Cpu, 
  Award, 
  Calendar, 
  Layers, 
  ShieldCheck, 
  RefreshCw,
  Sparkles
} from 'lucide-react';

export const Header: React.FC = () => {
  const {
    isLiveApi,
    blocks,
    selectedBlockId,
    setSelectedBlockId,
    panchayats,
    selectedPanchayatId,
    setSelectedPanchayatId,
    targetDate,
    setTargetDate,
    userRole,
    setUserRole,
    triggerRefresh,
    loadingData,
  } = useApp();

  const navigate = useNavigate();
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#070a12]/90 backdrop-blur-md px-4 lg:px-6 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Branding & Status Badges */}
        <div className="flex flex-wrap items-center gap-3">
          <div 
            onClick={() => navigate('/')} 
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-tight text-white group-hover:text-emerald-300 transition-colors">
                  AgroWeather
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950/80 border border-emerald-800/60 text-emerald-400">
                  SIH 26074
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono hidden sm:block">
                Panchayat Micro-Climate Downscaling
              </p>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-800 hidden sm:block" />

          {/* Provenance Badge */}
          <div
            id="header-provenance-badge"
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium border transition-colors ${
              isLiveApi
                ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                : 'bg-amber-950/60 border-amber-500/30 text-amber-300'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLiveApi ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span>
              {isLiveApi
                ? 'LIVE FASTAPI • CANONICAL PILOT DATA'
                : 'OFFLINE • CANONICAL DEMO FIXTURES'}
            </span>
          </div>

          {/* Certified Baseline Badge */}
          <div
            id="header-baseline-badge"
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-sky-950/50 border border-sky-500/30 text-sky-300"
            title="Certified Production Baseline Parameter"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            <span>T_cal = T_coarse + 0.7351°C</span>
          </div>

          {/* XGBoost Challenger Badge */}
          <div
            id="header-xgboost-badge"
            className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950/40 border border-purple-500/30 text-purple-300"
            title="Challenger ML Model (Research Only)"
          >
            <Cpu className="w-3 h-3 text-purple-400" />
            <span>XGBoost: RESEARCH_ONLY</span>
          </div>
        </div>

        {/* Right: Global Filters & Controls */}
        <div className="flex flex-wrap items-center gap-2.5 ml-auto">
          {/* Block Selector */}
          <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg px-2 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Block:</span>
            <select
              id="header-block-select"
              value={selectedBlockId || ''}
              onChange={(e) => setSelectedBlockId(e.target.value ? Number(e.target.value) : null)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer pr-1"
            >
              {blocks.map((b) => (
                <option key={b.id} value={b.id} className="bg-slate-900 text-slate-200">
                  {b.name} ({b.district_name || b.district || 'Dhar'})
                </option>
              ))}
            </select>
          </div>

          {/* Panchayat Selector */}
          <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg px-2 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Panchayat:</span>
            <select
              id="header-panchayat-select"
              value={selectedPanchayatId || ''}
              onChange={(e) => setSelectedPanchayatId(e.target.value ? Number(e.target.value) : null)}
              className="bg-transparent text-emerald-400 font-medium focus:outline-none cursor-pointer max-w-[140px] truncate"
            >
              {panchayats.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Date Selector */}
          <div className="hidden sm:flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg px-2 py-1 text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <input
              id="header-date-input"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="bg-transparent text-slate-200 font-mono focus:outline-none cursor-pointer"
            />
          </div>

          {/* Role Toggle */}
          <div className="flex items-center bg-slate-900/90 border border-slate-800 rounded-lg p-0.5 text-xs">
            {(['FARMER', 'OFFICER', 'ADMIN'] as const).map((role) => (
              <button
                key={role}
                id={`role-btn-${role.toLowerCase()}`}
                onClick={() => setUserRole(role)}
                className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                  userRole === role
                    ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {role}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            id="header-refresh-btn"
            onClick={triggerRefresh}
            disabled={loadingData}
            title="Refresh certified data"
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? 'animate-spin text-emerald-400' : ''}`} />
          </button>

          {/* Judge Mode Button */}
          <button
            id="header-judge-btn"
            onClick={() => navigate('/judge')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all shadow-sm ${
              location.pathname === '/judge'
                ? 'bg-amber-500 text-slate-950 shadow-amber-500/20'
                : 'bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Judge Mode</span>
          </button>
        </div>
      </div>
    </header>
  );
};
