import React, { useState } from 'react';
import { 
  Cpu, 
  TrendingUp, 
  Layers, 
  Thermometer, 
  Mountain, 
  Compass, 
  Sliders, 
  Sparkles,
  Info
} from 'lucide-react';
import { WeatherCharts } from '../components/weather/WeatherCharts';

export const WeatherAnalysis: React.FC = () => {
  // Interactive Simulation state
  const [simCoarseTemp, setSimCoarseTemp] = useState<number>(34.0);
  const [simElevation, setSimElevation] = useState<number>(120);
  const [simSlope, setSimSlope] = useState<number>(3.5);
  const [simCropland, setSimCropland] = useState<number>(0.85);

  // Environmental lapse rate + terrain effect simulator
  // Standard environmental lapse rate ~ -0.0065 C/m, plus slope/aspect warming & vegetation evapotranspiration cooling
  const elevationDelta = (100 - simElevation) * 0.0065;
  const vegCoolingDelta = -0.6 * simCropland;
  const slopeDelta = simSlope * 0.08;
  const calculatedResidual = elevationDelta + vegCoolingDelta + slopeDelta;
  const downscaledOutput = simCoarseTemp + calculatedResidual;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                MATHEMATICAL ENGINE &bull; PHASE 6 & 7
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Physical & Machine Learning Weather Downscaling Analysis
            </h1>
            <p className="text-sm text-slate-300 mt-1">
              Deep dive into the 1-km XGBoost residual correction model, terrain lapse rates, and validation metrics.
            </p>
          </div>

          <div className="bg-slate-950/80 px-4 py-2.5 rounded-xl border border-slate-800 text-right font-mono">
            <span className="text-[10px] text-slate-400 uppercase block">Calibration Benchmark</span>
            <span className="text-sm font-bold text-emerald-400">R²: 0.94 &bull; MAE: 0.38°C</span>
            <span className="text-[10px] text-amber-400 block mt-0.5">Pipeline Test Set</span>
          </div>
        </div>
      </div>

      {/* Simulator Explanatory Disclaimer */}
      <div className="bg-slate-900/80 border border-slate-700/80 p-4 rounded-xl text-xs text-slate-300 flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-emerald-400 shrink-0" />
        <div>
          <span className="font-bold text-white block">Illustrative / What-if Sensitivity Explorer</span>
          <span className="text-slate-400">
            This interactive panel illustrates the biophysical response (elevation lapse rates, slope heating, and vegetation evapotranspiration) without modifying registered production ML model artifacts.
          </span>
        </div>
      </div>

      {/* Core Mathematical Equation Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">
          Core Residual Downscaling Formulation
        </h3>
        <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-center">
          <span className="text-lg sm:text-2xl font-mono font-bold text-white tracking-wide">
            T<sub className="text-xs">downscaled</sub>(x, y) = T<sub className="text-xs">coarse</sub> + <span className="text-amber-400">f<sub className="text-xs">XGBoost</sub>(Elev, Slope, Aspect, LULC, Veg)</span>
          </span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Rather than predicting absolute temperatures directly (which leads to spatial drift), our architecture predicts the <strong>residual temperature delta (&Delta;T)</strong> based on high-resolution SRTM DEM terrain attributes and Sentinel-2 land cover physics, anchoring the baseline to official IMD/NWP block forecasts. <em>Note: Rainfall is preserved from coarse block NWP and is not downscaled.</em>
        </p>
      </div>

      {/* Interactive What-If Residual Simulator */}
      <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-bold text-white">
              Interactive 1-km Downscaling Sensitivity Simulator
            </h3>
          </div>
          <span className="text-xs text-emerald-400 font-mono">Sensitivity Analysis</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-300">Coarse Block Temperature (T_coarse)</span>
                <span className="text-emerald-400 font-mono">{simCoarseTemp.toFixed(1)} °C</span>
              </div>
              <input
                type="range"
                min="20"
                max="45"
                step="0.5"
                value={simCoarseTemp}
                onChange={(e) => setSimCoarseTemp(parseFloat(e.target.value))}
                className="w-full accent-emerald-500 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-300">Grid Cell Elevation (SRTM DEM)</span>
                <span className="text-sky-400 font-mono">{simElevation} m</span>
              </div>
              <input
                type="range"
                min="80"
                max="250"
                step="5"
                value={simElevation}
                onChange={(e) => setSimElevation(parseInt(e.target.value, 10))}
                className="w-full accent-sky-500 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-300">Terrain Slope</span>
                <span className="text-amber-400 font-mono">{simSlope.toFixed(1)}°</span>
              </div>
              <input
                type="range"
                min="0"
                max="15"
                step="0.5"
                value={simSlope}
                onChange={(e) => setSimSlope(parseFloat(e.target.value))}
                className="w-full accent-amber-500 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span className="text-slate-300">Cropland & Vegetation Fraction</span>
                <span className="text-emerald-400 font-mono">{(simCropland * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={simCropland}
                onChange={(e) => setSimCropland(parseFloat(e.target.value))}
                className="w-full accent-emerald-500 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          {/* Computed Output Card (5 cols) */}
          <div className="lg:col-span-5 bg-slate-950/80 rounded-xl p-5 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                Simulated Inference Output
              </span>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Predicted ML Residual (ΔT):</span>
                  <span className={`font-mono font-bold text-base ${calculatedResidual >= 0 ? 'text-amber-400' : 'text-sky-400'}`}>
                    {calculatedResidual >= 0 ? `+${calculatedResidual.toFixed(2)}` : calculatedResidual.toFixed(2)} °C
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Elevation Lapse Delta:</span>
                  <span className="font-mono text-slate-300">
                    {elevationDelta >= 0 ? `+${elevationDelta.toFixed(2)}` : elevationDelta.toFixed(2)} °C
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Vegetation Evapotranspiration:</span>
                  <span className="font-mono text-emerald-400">
                    {vegCoolingDelta.toFixed(2)} °C
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 mt-4">
              <span className="text-[11px] text-slate-400 uppercase block">
                Final 1-km Downscaled Output
              </span>
              <span className="text-3xl font-extrabold font-mono text-emerald-400">
                {downscaledOutput.toFixed(2)} °C
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
