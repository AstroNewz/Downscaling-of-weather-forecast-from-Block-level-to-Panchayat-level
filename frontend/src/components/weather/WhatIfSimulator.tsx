import React, { useState } from 'react';
import { PanchayatWeather } from '../../types';
import { Sliders, RotateCcw, Flame, CloudLightning, Wind, Sparkles, AlertTriangle } from 'lucide-react';

interface WhatIfSimulatorProps {
  weather: PanchayatWeather | null | undefined;
  panchayatName: string;
}

export const WhatIfSimulator: React.FC<WhatIfSimulatorProps> = ({
  weather,
  panchayatName,
}) => {
  const [tempDelta, setTempDelta] = useState<number>(0);
  const [windDelta, setWindDelta] = useState<number>(0);
  const [rainDelta, setRainDelta] = useState<number>(0);

  const resetSimulation = () => {
    setTempDelta(0);
    setWindDelta(0);
    setRainDelta(0);
  };

  const applyPreset = (preset: 'normal' | 'heatwave' | 'monsoon' | 'gale') => {
    switch (preset) {
      case 'normal':
        resetSimulation();
        break;
      case 'heatwave':
        setTempDelta(3.5);
        setWindDelta(5);
        setRainDelta(-10);
        break;
      case 'monsoon':
        setTempDelta(-2.0);
        setWindDelta(15);
        setRainDelta(35);
        break;
      case 'gale':
        setTempDelta(0.5);
        setWindDelta(25);
        setRainDelta(5);
        break;
    }
  };

  if (!weather) return null;

  // Calculate simulated parameters
  const simTmax = Number((weather.tmax_c + tempDelta).toFixed(1));
  const simTmean = Number((weather.tmean_c + tempDelta).toFixed(1));
  const simWind = Math.max(0, Number((weather.wind_speed_kmh + windDelta).toFixed(1)));
  const simRain = Math.max(0, Number((weather.rainfall_mm + rainDelta).toFixed(1)));

  // Determine simulated hazard impacts
  const heatStressRisk = simTmax >= 38.0;
  const windLodgingRisk = simWind >= 35.0;
  const waterloggingRisk = simRain >= 40.0;

  const isModified = tempDelta !== 0 || windDelta !== 0 || rainDelta !== 0;

  return (
    <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-indigo-500/15 text-indigo-400">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <span>Agro-Microclimate "What-If" Scenario Engine</span>
              {isModified && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  Simulation Active
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              Interactive in-memory stress-testing for {panchayatName}
            </p>
          </div>
        </div>

        <button
          id="whatif-reset-btn"
          onClick={resetSimulation}
          disabled={!isModified}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            isModified
              ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-600'
              : 'bg-slate-900/50 text-slate-500 border-slate-800 cursor-not-allowed'
          }`}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Scenario</span>
        </button>
      </div>

      {/* Quick Scenario Presets */}
      <div className="space-y-1.5">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Quick Meteorological Presets:
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button
            onClick={() => applyPreset('normal')}
            className={`p-2 rounded-lg text-xs font-medium border transition-all text-center ${
              !isModified
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
            }`}
          >
            Baseline Normal
          </button>
          <button
            onClick={() => applyPreset('heatwave')}
            className="p-2 rounded-lg text-xs font-medium border bg-rose-950/30 border-rose-500/30 text-rose-300 hover:bg-rose-900/40 transition-all text-center flex items-center justify-center gap-1.5"
          >
            <Flame className="w-3.5 h-3.5 text-rose-400" />
            <span>Heat Wave (+3.5°C)</span>
          </button>
          <button
            onClick={() => applyPreset('monsoon')}
            className="p-2 rounded-lg text-xs font-medium border bg-sky-950/30 border-sky-500/30 text-sky-300 hover:bg-sky-900/40 transition-all text-center flex items-center justify-center gap-1.5"
          >
            <CloudLightning className="w-3.5 h-3.5 text-sky-400" />
            <span>Monsoon Deluge (+35mm)</span>
          </button>
          <button
            onClick={() => applyPreset('gale')}
            className="p-2 rounded-lg text-xs font-medium border bg-indigo-950/30 border-indigo-500/30 text-indigo-300 hover:bg-indigo-900/40 transition-all text-center flex items-center justify-center gap-1.5"
          >
            <Wind className="w-3.5 h-3.5 text-indigo-400" />
            <span>High Gale (+25km/h)</span>
          </button>
        </div>
      </div>

      {/* Sliders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        {/* Temp Slider */}
        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Temperature Delta:</span>
            <span className="font-mono font-bold text-amber-300">
              {tempDelta > 0 ? `+${tempDelta}` : tempDelta}°C
            </span>
          </div>
          <input
            id="whatif-temp-slider"
            type="range"
            min="-5"
            max="6"
            step="0.5"
            value={tempDelta}
            onChange={(e) => setTempDelta(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500">
            <span>-5°C</span>
            <span>0°C</span>
            <span>+6°C</span>
          </div>
        </div>

        {/* Wind Slider */}
        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Wind Speed Delta:</span>
            <span className="font-mono font-bold text-indigo-300">
              {windDelta > 0 ? `+${windDelta}` : windDelta} km/h
            </span>
          </div>
          <input
            id="whatif-wind-slider"
            type="range"
            min="-15"
            max="35"
            step="1"
            value={windDelta}
            onChange={(e) => setWindDelta(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-400"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500">
            <span>-15</span>
            <span>0</span>
            <span>+35</span>
          </div>
        </div>

        {/* Rain Slider */}
        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Rainfall Delta:</span>
            <span className="font-mono font-bold text-teal-300">
              {rainDelta > 0 ? `+${rainDelta}` : rainDelta} mm
            </span>
          </div>
          <input
            id="whatif-rain-slider"
            type="range"
            min="-30"
            max="60"
            step="5"
            value={rainDelta}
            onChange={(e) => setRainDelta(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-teal-400"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500">
            <span>-30</span>
            <span>0</span>
            <span>+60</span>
          </div>
        </div>
      </div>

      {/* Simulated Output & Agronomic Impact */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
        <div className="flex justify-between items-center text-xs">
          <span className="font-medium text-slate-300">Simulated Micro-Climate Response</span>
          <span className="font-mono text-[11px] text-slate-400">
            Downscaled Tmax: <strong className="text-white">{simTmax}°C</strong> | Wind: <strong className="text-white">{simWind} km/h</strong> | Rain: <strong className="text-white">{simRain} mm</strong>
          </span>
        </div>

        {/* Simulated Impact Alerts */}
        <div className="space-y-2">
          {heatStressRisk && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>
                <strong>CRITICAL HEAT STRESS DETECTED:</strong> Tmax ({simTmax}°C) exceeds the 38.0°C cotton/soybean reproductive threshold. Triggering pulse irrigation advisory.
              </span>
            </div>
          )}

          {windLodgingRisk && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/40 text-amber-300 text-xs">
              <Wind className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span>
                <strong>HIGH WIND LODGING HAZARD:</strong> Wind ({simWind} km/h) exceeds 35 km/h limit. Delay spraying operations and check physical field supports.
              </span>
            </div>
          )}

          {waterloggingRisk && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-sky-950/40 border border-sky-500/40 text-sky-300 text-xs">
              <CloudLightning className="w-4 h-4 text-sky-400 flex-shrink-0" />
              <span>
                <strong>WATERLOGGING THREAT:</strong> Cumulative precipitation ({simRain} mm) may saturate root zones. Ensure field drainage channels are cleared.
              </span>
            </div>
          )}

          {!heatStressRisk && !windLodgingRisk && !waterloggingRisk && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs">
              <Sparkles className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>
                <strong>NORMAL AGRONOMIC WINDOW:</strong> Parameters remain within standard tolerance boundaries. Standard cultivation schedule recommended.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
