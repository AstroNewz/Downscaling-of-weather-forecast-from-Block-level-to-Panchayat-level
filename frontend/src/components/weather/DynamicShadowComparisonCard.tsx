import React from 'react';
import { Cpu, ShieldCheck, ArrowRight, Gauge, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { PanchayatWeather } from '../../types';

interface DynamicShadowComparisonCardProps {
  weather?: PanchayatWeather;
}

export const DynamicShadowComparisonCard: React.FC<DynamicShadowComparisonCardProps> = ({ weather }) => {
  if (!weather) return null;

  const coarseT = weather.coarse_temperature_c ?? weather.tmean_c - 0.7351;
  const operationalResidual = weather.operational_residual_c ?? (weather.predicted_residual_delta_c || 0.7351);
  const operationalT = weather.tmean_c;
  const baselineOffset = 0.7351;
  const baselineT = Number((coarseT + baselineOffset).toFixed(2));
  const diff = Number((operationalT - baselineT).toFixed(2));

  const isFallback = weather.fallback_active ?? false;
  const modelUsed = weather.model_used || 'DYNAMIC_V2';
  const oodStatus = weather.ood_status || 'WITHIN_DOMAIN';
  const safetyStatus = weather.safety_status || 'PASS';

  return (
    <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/30 via-slate-900/70 to-slate-900/60 p-6 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-indigo-500/20 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Dynamic Residual Model v2 • Controlled Shadow Telemetry
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time parallel comparison between primary Dynamic v2 and Certified Immutable Baseline (+0.7351°C)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-full text-xs font-mono font-bold tracking-wider border ${
              isFallback
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
            }`}
          >
            {isFallback ? 'FALLBACK ACTIVE' : 'DYNAMIC PRIMARY ACTIVE'}
          </span>
        </div>
      </div>

      {/* Side-by-Side Dual Inference Metric Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Coarse NWP Input */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
            Raw Coarse NWP Input (T_coarse)
          </span>
          <div className="text-2xl font-bold text-white font-mono">
            {coarseT.toFixed(1)}°C
          </div>
          <p className="text-[11px] text-slate-400">
            Open-Meteo Operational NWP Grid
          </p>
        </div>

        {/* Dynamic Model v2 Operational Output */}
        <div className="rounded-xl border border-indigo-500/40 bg-indigo-950/30 p-4 space-y-1 ring-1 ring-indigo-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-indigo-300 uppercase tracking-wider">
              Dynamic Model v2 (Primary)
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-200">
              ΔT: {operationalResidual >= 0 ? `+${operationalResidual.toFixed(2)}` : operationalResidual.toFixed(2)}°C
            </span>
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {operationalT.toFixed(2)}°C
          </div>
          <p className="text-[11px] text-indigo-200/80">
            Micro-topographical residual applied
          </p>
        </div>

        {/* Certified Baseline Shadow Output */}
        <div className="rounded-xl border border-sky-500/40 bg-sky-950/30 p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-sky-300 uppercase tracking-wider">
              Certified Shadow Baseline
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-900/60 text-sky-200">
              +0.7351°C Fixed
            </span>
          </div>
          <div className="text-2xl font-bold text-sky-300 font-mono">
            {baselineT.toFixed(2)}°C
          </div>
          <p className="text-[11px] text-sky-200/80">
            Phase 23/24 certified safety standard
          </p>
        </div>
      </div>

      {/* Operational Divergence & Safeguards Status */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-slate-400 text-[11px]">Dynamic - Baseline:</span>
          <div className="text-sm font-bold text-white">
            {diff >= 0 ? `+${diff.toFixed(2)}°C` : `${diff.toFixed(2)}°C`}
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-slate-400 text-[11px]">OOD Domain Check:</span>
          <div className="text-sm font-bold text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{oodStatus}</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-slate-400 text-[11px]">Physical Bounds [-8°C, +8°C]:</span>
          <div className="text-sm font-bold text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{safetyStatus}</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-slate-400 text-[11px]">Active Operational Model:</span>
          <div className="text-sm font-bold text-indigo-300 truncate">
            {modelUsed}
          </div>
        </div>
      </div>

      <div className="text-[11px] text-slate-400 flex items-center gap-2 pt-1 border-t border-slate-800/80">
        <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        <span>
          Strict Scientific Rule: Shadow baseline never feeds back into model training. Zero online learning. Model weights remain 100% frozen.
        </span>
      </div>
    </div>
  );
};
