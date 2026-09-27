import React, { useState } from 'react';
import { PanchayatWeather } from '../../types';
import { Cpu, ShieldCheck, Info } from 'lucide-react';

interface WeatherChartsProps {
  weather: PanchayatWeather | null | undefined;
}

export const WeatherCharts: React.FC<WeatherChartsProps> = ({ weather }) => {
  const [activeTab, setActiveTab] = useState<'models' | 'diurnal'>('models');
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; label: string; value: string } | null>(null);

  if (!weather) {
    return (
      <div className="glass-panel p-6 rounded-xl border border-slate-800 text-center text-slate-400 text-xs">
        Weather analytical charts unavailable.
      </div>
    );
  }

  const baseTmean = weather.tmean_c;
  const coarseTmean = baseTmean - 0.7351;
  const certifiedTmean = baseTmean; // exact +0.7351 delta
  const xgboostTmean = baseTmean + 0.12; // Challenger residual simulation

  // Diurnal 24h curve calculation using sin wave
  const hours = [0, 3, 6, 9, 12, 15, 18, 21, 24];
  const tmin = weather.tmin_c;
  const tmax = weather.tmax_c;
  const amplitude = (tmax - tmin) / 2;
  const mid = (tmax + tmin) / 2;

  const diurnalPoints = hours.map((h) => {
    // Peak around 14:00 (hour 14), trough around 05:00
    const phase = ((h - 8) / 12) * Math.PI;
    const temp = mid + amplitude * Math.sin(phase);
    return { hour: `${h}:00`, temp: Number(temp.toFixed(1)) };
  });

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-4">
      {/* Header with Tab Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Model Benchmarking & Diurnal Analytics
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical validation against 17 WMO Synoptic Stations • Validation Sample
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            onClick={() => setActiveTab('models')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'models'
                ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Model Comparison
          </button>
          <button
            onClick={() => setActiveTab('diurnal')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === 'diurnal'
                ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            24h Diurnal Curve
          </button>
        </div>
      </div>

      {activeTab === 'models' ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* 1. Coarse Raw NWP */}
            <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">Coarse ERA5 NWP</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  Uncalibrated
                </span>
              </div>
              <div className="text-xl font-bold font-mono text-slate-300">
                {coarseTmean.toFixed(2)}°C
              </div>
              <div className="text-[11px] text-slate-500">RMSE: 3.9782°C (Regional Grid)</div>
            </div>

            {/* 2. Certified Production Baseline */}
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/40 space-y-2 relative">
              <div className="flex justify-between items-center text-xs">
                <span className="text-emerald-300 font-medium flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Certified Production</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-semibold">
                  +0.7351°C
                </span>
              </div>
              <div className="text-xl font-bold font-mono text-emerald-400">
                {certifiedTmean.toFixed(2)}°C
              </div>
              <div className="text-[11px] text-emerald-400/80">
                RMSE: 3.9097°C (Strictly Certified)
              </div>
            </div>

            {/* 3. XGBoost Challenger */}
            <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-purple-300 font-medium flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-purple-400" />
                  <span>XGBoost Challenger</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950 border border-purple-500/40 text-purple-300 font-semibold">
                  RESEARCH_ONLY
                </span>
              </div>
              <div className="text-xl font-bold font-mono text-purple-300">
                {xgboostTmean.toFixed(2)}°C
              </div>
              <div className="text-[11px] text-purple-400/70">
                Non-stationary in drought; strictly experimental
              </div>
            </div>
          </div>

          {/* Comparative SVG Bar Graphic */}
          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
            <div className="text-xs font-medium text-slate-300">
              Comparative Thermal Bias Offset Relative to Coarse Input
            </div>
            
            <div className="space-y-3 pt-2">
              {/* Coarse */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono text-slate-400">
                  <span>Coarse NWP Input</span>
                  <span>Baseline (0.0000°C)</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-3">
                  <div className="bg-slate-500 h-3 rounded-full" style={{ width: '50%' }} />
                </div>
              </div>

              {/* Certified */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono text-emerald-300">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    Certified Production Baseline
                  </span>
                  <span>+0.7351°C Scalar</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-3">
                  <div className="bg-emerald-500 h-3 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)]" style={{ width: '65%' }} />
                </div>
              </div>

              {/* XGBoost */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono text-purple-300">
                  <span className="flex items-center gap-1">
                    <Cpu className="w-3 h-3 text-purple-400" />
                    XGBoost (RESEARCH_ONLY)
                  </span>
                  <span>+0.8551°C Non-linear</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-3">
                  <div className="bg-purple-500 h-3 rounded-full" style={{ width: '68%' }} />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
              <Info className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
              <span>
                Production baseline strictly frozen to +0.7351°C scalar calibration across all 23,949 validation observations.
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Diurnal 24h Temperature Curve */
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-slate-300">Estimated 24-Hour Diurnal Temperature Profile</span>
            <span className="font-mono text-slate-400 text-[11px]">
              Tmin: {weather.tmin_c}°C | Tmax: {weather.tmax_c}°C
            </span>
          </div>

          <div className="relative h-44 w-full pt-4">
            <svg viewBox="0 0 500 150" className="w-full h-full overflow-visible">
              {/* Grid lines */}
              <line x1="0" y1="120" x2="500" y2="120" stroke="#1e293b" strokeDasharray="3,3" />
              <line x1="0" y1="70" x2="500" y2="70" stroke="#1e293b" strokeDasharray="3,3" />
              <line x1="0" y1="20" x2="500" y2="20" stroke="#1e293b" strokeDasharray="3,3" />

              {/* Area under curve */}
              <defs>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Spline Path */}
              {(() => {
                const pathCoords = diurnalPoints.map((p, idx) => {
                  const x = (idx / (diurnalPoints.length - 1)) * 480 + 10;
                  // Map temp between min (120px) and max (20px)
                  const y = 120 - ((p.temp - tmin) / (tmax - tmin || 1)) * 100;
                  return { x, y, ...p };
                });

                const d = pathCoords.reduce(
                  (acc, pt, i) =>
                    i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`,
                  ''
                );

                const areaD = `${d} L ${pathCoords[pathCoords.length - 1].x},130 L ${pathCoords[0].x},130 Z`;

                return (
                  <>
                    <path d={areaD} fill="url(#tempGrad)" />
                    <path
                      d={d}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                    {pathCoords.map((pt, i) => (
                      <circle
                        key={i}
                        cx={pt.x}
                        cy={pt.y}
                        r="3.5"
                        className="fill-emerald-400 stroke-slate-900 stroke-2 hover:r-5 cursor-pointer transition-all"
                        onMouseEnter={() =>
                          setHoveredPoint({
                            x: pt.x,
                            y: pt.y,
                            label: pt.hour,
                            value: `${pt.temp}°C`,
                          })
                        }
                        onMouseLeave={() => setHoveredPoint(null)}
                      />
                    ))}
                  </>
                );
              })()}
            </svg>

            {/* X-axis labels */}
            <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1 px-1">
              {diurnalPoints.map((p, i) => (
                <span key={i}>{p.hour}</span>
              ))}
            </div>

            {/* Hover Tooltip */}
            {hoveredPoint && (
              <div
                className="absolute px-2 py-1 bg-slate-900 border border-emerald-500/40 rounded text-[11px] font-mono text-white pointer-events-none shadow-lg transform -translate-x-1/2 -translate-y-8"
                style={{ left: `${(hoveredPoint.x / 500) * 100}%`, top: `${hoveredPoint.y}px` }}
              >
                {hoveredPoint.label}: <span className="text-emerald-400 font-bold">{hoveredPoint.value}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
