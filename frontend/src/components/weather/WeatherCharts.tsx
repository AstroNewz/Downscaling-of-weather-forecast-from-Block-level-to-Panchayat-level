import React, { useState } from 'react';
import { 
  TrendingUp, 
  Thermometer, 
  Droplets, 
  Wind, 
  Layers, 
  HelpCircle,
  CloudRain
} from 'lucide-react';
import { PanchayatWeather } from '../../types';

interface WeatherChartsProps {
  weather: PanchayatWeather;
  blockWeather?: {
    tmax_c: number;
    tmin_c: number;
    tmean_c: number;
    relative_humidity_pct: number;
    wind_speed_kmh: number;
    rainfall_mm: number;
  };
}

export const WeatherCharts: React.FC<WeatherChartsProps> = ({
  weather,
  blockWeather = {
    tmax_c: (weather.tmax_c || 35.0) - (weather.predicted_residual_delta_c || 1.2),
    tmin_c: (weather.tmin_c || 24.0) - (weather.predicted_residual_delta_c || 0.8),
    tmean_c: (weather.tmean_c || 29.5) - (weather.predicted_residual_delta_c || 1.0),
    relative_humidity_pct: weather.relative_humidity_pct || 65,
    wind_speed_kmh: weather.wind_speed_kmh || 12,
    rainfall_mm: weather.rainfall_mm || 0,
  },
}) => {
  const [activeTab, setActiveTab] = useState<'comparison' | 'metrics'>('comparison');

  const residualDelta = (weather.predicted_residual_delta_c !== undefined && weather.predicted_residual_delta_c !== null)
    ? weather.predicted_residual_delta_c
    : (weather.tmean_c - blockWeather.tmean_c);

  // Hourly simulated curve for visual temperature representation
  const hourlyHours = ['03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '00:00'];
  const tmin = weather.tmin_c;
  const tmax = weather.tmax_c;
  const blockTmin = blockWeather.tmin_c;
  const blockTmax = blockWeather.tmax_c;

  // Diurnal curve interpolation
  const downscaledHourly = [
    tmin + 0.5,
    tmin,
    tmin + (tmax - tmin) * 0.45,
    tmin + (tmax - tmin) * 0.88,
    tmax,
    tmin + (tmax - tmin) * 0.65,
    tmin + (tmax - tmin) * 0.35,
    tmin + 1.2,
  ];

  const blockHourly = [
    blockTmin + 0.5,
    blockTmin,
    blockTmin + (blockTmax - blockTmin) * 0.45,
    blockTmin + (blockTmax - blockTmin) * 0.88,
    blockTmax,
    blockTmin + (blockTmax - blockTmin) * 0.65,
    blockTmin + (blockTmax - blockTmin) * 0.35,
    blockTmin + 1.2,
  ];

  const minPlotTemp = Math.floor(Math.min(tmin, blockTmin) - 2);
  const maxPlotTemp = Math.ceil(Math.max(tmax, blockTmax) + 2);
  const tempRange = maxPlotTemp - minPlotTemp;

  return (
    <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl space-y-6">
      {/* Header with methodology reminder */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white tracking-tight">
              Spatial Weather Downscaling & Micro-climate Analytics
            </h3>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
              1-km ML Inferred
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Panchayat area-weighted aggregation derived from 1-km XGBoost residual corrected thermal grid.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('comparison')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'comparison'
                ? 'bg-emerald-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Resolution Comparison
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'metrics'
                ? 'bg-emerald-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Agro-Weather Indicators
          </button>
        </div>
      </div>

      {activeTab === 'comparison' ? (
        <div className="space-y-6">
          {/* Temperature Diurnal Curve Chart */}
          <div className="bg-slate-950/70 rounded-xl p-5 border border-slate-800/80">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Thermometer className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Diurnal Temperature Profile: Coarse Block vs 1-km Panchayat
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs font-medium">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-emerald-400" />
                  <span className="text-slate-300">1-km Downscaled ({weather.tmean_c.toFixed(1)}°C mean)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-slate-500" />
                  <span className="text-slate-400">Coarse Block ({blockWeather.tmean_c.toFixed(1)}°C mean)</span>
                </div>
              </div>
            </div>

            {/* Visual SVG Chart */}
            <div className="relative h-48 w-full pt-4">
              <svg className="w-full h-full overflow-visible" viewBox="0 0 700 160">
                {/* Horizontal Grid lines */}
                {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
                  const y = 140 - ratio * 120;
                  const tempVal = minPlotTemp + ratio * tempRange;
                  return (
                    <g key={idx}>
                      <line
                        x1="40"
                        y1={y}
                        x2="680"
                        y2={y}
                        stroke="#334155"
                        strokeDasharray="4 4"
                        strokeWidth="1"
                      />
                      <text
                        x="30"
                        y={y + 4}
                        fill="#64748b"
                        fontSize="10"
                        textAnchor="end"
                        fontFamily="monospace"
                      >
                        {tempVal.toFixed(0)}°
                      </text>
                    </g>
                  );
                })}

                {/* Coarse Block Curve (Grey Line) */}
                <path
                  d={blockHourly.reduce((acc, temp, idx) => {
                    const x = 60 + idx * 85;
                    const y = 140 - ((temp - minPlotTemp) / tempRange) * 120;
                    return `${acc} ${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
                  }, '')}
                  fill="none"
                  stroke="#64748b"
                  strokeWidth="2"
                  strokeDasharray="5 5"
                />

                {/* 1-km Downscaled Curve (Emerald Line) */}
                <path
                  d={downscaledHourly.reduce((acc, temp, idx) => {
                    const x = 60 + idx * 85;
                    const y = 140 - ((temp - minPlotTemp) / tempRange) * 120;
                    return `${acc} ${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
                  }, '')}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3.5"
                />

                {/* Downscaled Data Points */}
                {downscaledHourly.map((temp, idx) => {
                  const x = 60 + idx * 85;
                  const y = 140 - ((temp - minPlotTemp) / tempRange) * 120;
                  return (
                    <g key={idx} className="group cursor-pointer">
                      <circle
                        cx={x}
                        cy={y}
                        r="4.5"
                        fill="#10b981"
                        stroke="#0f172a"
                        strokeWidth="2"
                      />
                      <text
                        x={x}
                        y={y - 8}
                        fill="#34d399"
                        fontSize="10"
                        fontWeight="bold"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {temp.toFixed(1)}°
                      </text>
                      <text
                        x={x}
                        y={155}
                        fill="#94a3b8"
                        fontSize="10"
                        textAnchor="middle"
                      >
                        {hourlyHours[idx]}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Mathematical Residual Correction Breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800">
              <span className="text-xs text-slate-400 block mb-1">Coarse Block Mean Temp</span>
              <span className="text-2xl font-bold font-mono text-slate-300">
                {blockWeather.tmean_c.toFixed(1)} °C
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">
                Regional ~25 km NWP grid
              </span>
            </div>

            <div className="bg-slate-900/90 rounded-xl p-4 border border-emerald-500/30">
              <div className="flex items-center justify-between">
                <span className="text-xs text-emerald-400 font-semibold block mb-1">
                  ML Residual Delta (ΔT)
                </span>
                <span className="text-[10px] font-mono bg-emerald-950 px-1.5 py-0.5 rounded text-emerald-400 border border-emerald-500/30">
                  XGBoost
                </span>
              </div>
              <span className={`text-2xl font-bold font-mono ${residualDelta >= 0 ? 'text-amber-400' : 'text-sky-400'}`}>
                {residualDelta >= 0 ? `+${residualDelta.toFixed(2)}` : residualDelta.toFixed(2)} °C
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">
                SRTM DEM terrain + LULC effect
              </span>
            </div>

            <div className="bg-slate-900/90 rounded-xl p-4 border border-emerald-500/50 bg-emerald-950/10">
              <span className="text-xs text-emerald-300 font-bold block mb-1">
                Final 1-km Downscaled Mean
              </span>
              <span className="text-2xl font-bold font-mono text-emerald-400">
                {weather.tmean_c.toFixed(1)} °C
              </span>
              <span className="text-[11px] text-emerald-400/80 block mt-1">
                Panchayat boundary aggregated
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Agro-Weather Indicators Tab */
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 mb-2 text-rose-400">
              <Thermometer className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Tmax / Tmin</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {weather.tmax_c.toFixed(1)}° / {weather.tmin_c.toFixed(1)}°
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">1-km Downscaled</span>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 mb-2 text-sky-400">
              <Droplets className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Rel. Humidity</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {weather.relative_humidity_pct?.toFixed(0) || 65}%
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">Agro-meteorological</span>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 mb-2 text-teal-400">
              <Wind className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Wind Speed</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {weather.wind_speed_kmh?.toFixed(1) || 12.0} km/h
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">Spray condition metric</span>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 mb-2 text-blue-400">
              <CloudRain className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Rainfall</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {weather.rainfall_mm?.toFixed(1) || 0.0} mm
            </div>
            <span className="text-[10px] text-amber-400/80 mt-1 block font-medium">
              *Coarse Block Forecast
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
