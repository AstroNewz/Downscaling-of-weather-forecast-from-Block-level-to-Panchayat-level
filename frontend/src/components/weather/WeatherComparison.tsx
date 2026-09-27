import React from 'react';
import { PanchayatWeather } from '../../types';
import { Thermometer, Wind, Droplets, CloudRain, ShieldCheck, Cpu, AlertTriangle, ArrowRight } from 'lucide-react';

interface WeatherComparisonProps {
  weather: PanchayatWeather | null | undefined;
  panchayatName: string;
  blockName?: string;
}

export const WeatherComparison: React.FC<WeatherComparisonProps> = ({
  weather,
  panchayatName,
  blockName = 'Dhar Block',
}) => {
  if (!weather) {
    return (
      <div className="glass-panel p-6 rounded-xl border border-slate-800 text-center text-slate-400 text-xs">
        No weather comparison records available for this Panchayat.
      </div>
    );
  }

  const isDynamicActive = weather.model_used === 'DYNAMIC_V2' && !weather.fallback_active;
  const operationalResidual = weather.operational_residual_c ?? weather.predicted_residual_delta_c ?? 0.7351;
  const coarseTmean = weather.coarse_temperature_c ?? Number((weather.tmean_c - operationalResidual).toFixed(2));
  const downscaledTmean = Number(weather.tmean_c.toFixed(2));

  const coarseTmax = Number((weather.tmax_c - operationalResidual).toFixed(2));
  const downscaledTmax = Number(weather.tmax_c.toFixed(2));

  const coarseTmin = Number((weather.tmin_c - operationalResidual).toFixed(2));
  const downscaledTmin = Number(weather.tmin_c.toFixed(2));

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-4">
      {/* Section Header with Mandatory Operational Status Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <span>Spatial Resolution Downscaling Comparison</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Regional NWP Grid vs Operational Panchayat Micro-Scale (1-km Calibrated)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {isDynamicActive ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-500/40 text-purple-300 shadow-sm shadow-purple-900/30">
              <Cpu className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
              <span className="font-bold">DYNAMIC DOWNSCALING ACTIVE</span>
              <span className="text-[10px] text-purple-400/80">(CONTROLLED_PRODUCTION)</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-500/40 text-amber-300">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-bold">CERTIFIED BASELINE FALLBACK ACTIVE</span>
              <span className="text-[10px] text-amber-400/80">(T_coarse + 0.7351°C)</span>
            </div>
          )}
        </div>
      </div>

      {/* Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Coarse Regional Model (~25 km) */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3 relative">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase tracking-wider">
                Coarse Regional Forecast (NWP)
              </span>
              <h4 className="text-sm font-bold text-slate-200 mt-1">{blockName}</h4>
              <p className="text-[11px] text-slate-400 font-mono">~25 km Operational Grid</p>
            </div>
            <div className="p-2 rounded-lg bg-slate-800/60 text-slate-400">
              <Thermometer className="w-5 h-5" />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/60 space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-slate-400">Coarse NWP Mean:</span>
              <span className="text-xl font-bold font-mono text-slate-300">{coarseTmean}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Coarse Max / Min:</span>
              <span className="font-mono text-slate-300">{coarseTmax}°C / {coarseTmin}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Resolution Quality:</span>
              <span className="font-mono text-amber-400/90 text-[11px]">Regional Aggregate</span>
            </div>
          </div>
        </div>

        {/* Right: Operational Downscaled Panchayat Level (1 km) */}
        <div className={`p-4 rounded-xl border space-y-3 relative ${
          isDynamicActive 
            ? 'border-purple-500/40 bg-purple-950/15 shadow-[0_0_20px_rgba(168,85,247,0.08)]' 
            : 'border-emerald-500/30 bg-emerald-950/10 shadow-[0_0_20px_rgba(16,185,129,0.05)]'
        }`}>
          <div className="flex justify-between items-start">
            <div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase tracking-wider font-semibold ${
                isDynamicActive
                  ? 'bg-purple-950 border border-purple-500/40 text-purple-300'
                  : 'bg-emerald-950 border border-emerald-500/40 text-emerald-300'
              }`}>
                {isDynamicActive ? 'Panchayat Dynamic v2' : 'Panchayat Baseline Fallback'}
              </span>
              <h4 className="text-sm font-bold text-white mt-1">{panchayatName}</h4>
              <p className="text-[11px] text-emerald-400/80 font-mono">1-km Operational Micro-Grid</p>
            </div>
            <div className={`p-2 rounded-lg ${isDynamicActive ? 'bg-purple-500/15 text-purple-400' : 'bg-emerald-500/15 text-emerald-400'}`}>
              <Thermometer className="w-5 h-5" />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/60 space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-slate-300">Downscaled Temperature:</span>
              <div className="flex items-baseline gap-1.5">
                <span className={`text-xl font-bold font-mono ${isDynamicActive ? 'text-purple-300' : 'text-emerald-300'}`}>
                  {downscaledTmean}°C
                </span>
                <span className={`text-xs font-mono font-medium ${isDynamicActive ? 'text-purple-400' : 'text-emerald-400'}`}>
                  ({operationalResidual >= 0 ? `+${operationalResidual.toFixed(2)}` : operationalResidual.toFixed(2)}°C)
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Downscaled Max / Min:</span>
              <span className="font-mono text-slate-200">{downscaledTmax}°C / {downscaledTmin}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Operational Pathway:</span>
              <span className={`font-mono font-semibold text-[11px] ${isDynamicActive ? 'text-purple-400' : 'text-emerald-400'}`}>
                {isDynamicActive ? 'Dynamic Model v2 (Controlled)' : 'Certified Baseline Fallback (+0.7351°C)'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Exact Downscaling Formula Line */}
      <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <span>Formula Resolution:</span>
          <span className="text-slate-200 font-bold">
            Coarse ({coarseTmean}°C) {operationalResidual >= 0 ? '+' : '-'} {Math.abs(operationalResidual).toFixed(2)}°C = {downscaledTmean}°C
          </span>
        </div>
        <div className="text-slate-400 flex items-center gap-1.5">
          <span>Active Policy:</span>
          <span className="text-purple-300 font-semibold">
            {isDynamicActive ? 'Primary Dynamic Path' : 'Automatic Baseline Fallback'}
          </span>
        </div>
      </div>

      {/* Atmospheric Secondary Parameters */}
      <div className="grid grid-cols-3 gap-3 pt-1">
        <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
            <Droplets className="w-3.5 h-3.5 text-sky-400" />
            <span>Rel Humidity</span>
          </div>
          <span className="text-sm font-bold font-mono text-slate-200">
            {weather.relative_humidity_pct}%
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
            <Wind className="w-3.5 h-3.5 text-indigo-400" />
            <span>Wind Speed</span>
          </div>
          <span className="text-sm font-bold font-mono text-slate-200">
            {weather.wind_speed_kmh} km/h
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
          <div className="flex items-center justify-center gap-1 text-slate-400 text-xs mb-1">
            <CloudRain className="w-3.5 h-3.5 text-teal-400" />
            <span>Rainfall</span>
          </div>
          <span className="text-sm font-bold font-mono text-slate-200">
            {weather.rainfall_mm} mm
          </span>
        </div>
      </div>
    </div>
  );
};
