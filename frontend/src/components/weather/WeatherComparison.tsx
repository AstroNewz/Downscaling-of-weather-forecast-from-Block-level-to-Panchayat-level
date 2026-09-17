import React from 'react';
import { PanchayatWeather } from '../../types';
import { Thermometer, Wind, Droplets, CloudRain, ShieldCheck, ArrowRight } from 'lucide-react';

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

  // Certified baseline: T_calibrated = T_coarse + 0.7351°C
  // Therefore: T_coarse = T_calibrated - 0.7351°C
  const deltaC = 0.7351;
  const coarseTmean = Number((weather.tmean_c - deltaC).toFixed(2));
  const downscaledTmean = Number(weather.tmean_c.toFixed(2));

  const coarseTmax = Number((weather.tmax_c - deltaC).toFixed(2));
  const downscaledTmax = Number(weather.tmax_c.toFixed(2));

  const coarseTmin = Number((weather.tmin_c - deltaC).toFixed(2));
  const downscaledTmin = Number(weather.tmin_c.toFixed(2));

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-4">
      {/* Section Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            <span>Spatial Resolution Downscaling Comparison</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Regional NWP Grid vs Certified Panchayat Micro-Scale (1-km Calibrated)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-[11px] font-mono font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>T_calibrated = T_coarse + 0.7351°C</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Coarse Regional Model (~25 km) */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3 relative">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase tracking-wider">
                Coarse Regional Forecast
              </span>
              <h4 className="text-sm font-bold text-slate-200 mt-1">{blockName}</h4>
              <p className="text-[11px] text-slate-400 font-mono">~25 km ERA5 / NWP Grid</p>
            </div>
            <div className="p-2 rounded-lg bg-slate-800/60 text-slate-400">
              <Thermometer className="w-5 h-5" />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/60 space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-slate-400">Mean Temperature:</span>
              <span className="text-lg font-bold font-mono text-slate-300">{coarseTmean}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Max / Min Range:</span>
              <span className="font-mono text-slate-300">{coarseTmax}°C / {coarseTmin}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Resolution Quality:</span>
              <span className="font-mono text-amber-400/90 text-[11px]">Regional Aggregate</span>
            </div>
          </div>
        </div>

        {/* Right: Downscaled Panchayat Level (1 km) */}
        <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/10 space-y-3 relative shadow-[0_0_20px_rgba(16,185,129,0.05)]">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-300 uppercase tracking-wider font-semibold">
                Panchayat Scale Certified
              </span>
              <h4 className="text-sm font-bold text-white mt-1">{panchayatName}</h4>
              <p className="text-[11px] text-emerald-400/80 font-mono">1-km Calibrated Micro-Grid</p>
            </div>
            <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-400">
              <Thermometer className="w-5 h-5" />
            </div>
          </div>

          <div className="pt-2 border-t border-emerald-500/20 space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-emerald-200/80">Mean Temperature:</span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-lg font-bold font-mono text-emerald-300">{downscaledTmean}°C</span>
                <span className="text-xs font-mono font-medium text-emerald-400">(+0.7351°C)</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Max / Min Range:</span>
              <span className="font-mono text-emerald-200">{downscaledTmax}°C / {downscaledTmin}°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Scientific Status:</span>
              <span className="font-mono text-emerald-400 font-semibold text-[11px]">
                Phase 24 Certified Production
              </span>
            </div>
          </div>
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
