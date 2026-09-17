import React from 'react';
import { useApp } from '../context/AppContext';
import { WeatherComparison } from '../components/weather/WeatherComparison';
import { WeatherCharts } from '../components/weather/WeatherCharts';
import { WhatIfSimulator } from '../components/weather/WhatIfSimulator';
import { CloudSun, ShieldCheck, Cpu, Database } from 'lucide-react';

export const WeatherAnalysis: React.FC = () => {
  const { selectedPanchayat, panchayats } = useApp();

  const currentPanchayat = selectedPanchayat || panchayats[0];
  const weather = currentPanchayat?.latest_weather;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CloudSun className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">
              Weather Intelligence & Downscaling Analysis
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Empirical validation of certified +0.7351°C scalar downscaling vs regional NWP for {currentPanchayat?.name}
          </p>
        </div>

        {/* Certified Parameter Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-medium">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>T_calibrated = T_coarse + 0.7351°C</span>
        </div>
      </div>

      {/* Side-by-Side Comparison */}
      <WeatherComparison
        weather={weather}
        panchayatName={currentPanchayat?.name || 'Selected Panchayat'}
        blockName={currentPanchayat?.block_name || 'Dhar Block'}
      />

      {/* Model Benchmarking & Diurnal Curve Charts */}
      <WeatherCharts weather={weather} />

      {/* What-If Scenario Simulator */}
      <WhatIfSimulator
        weather={weather}
        panchayatName={currentPanchayat?.name || 'Selected Panchayat'}
      />

      {/* Empirical Dataset Scientific Facts */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Database className="w-4 h-4 text-sky-400" />
          <span>Scientific Calibration Dataset Provenance</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Total Observations</span>
            <span className="text-lg font-bold text-slate-200">23,949</span>
            <span className="text-[10px] text-slate-400 block">Strictly Zero Leakage</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Ground Stations</span>
            <span className="text-lg font-bold text-slate-200">17 WMO</span>
            <span className="text-[10px] text-slate-400 block">IMD Synoptic Calibrated</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase block">Geographic Spread</span>
            <span className="text-lg font-bold text-slate-200">11 States/UTs</span>
            <span className="text-[10px] text-slate-400 block">6 Physiographic Regimes</span>
          </div>
          <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
            <span className="text-slate-500 text-[10px] uppercase block">Production Param</span>
            <span className="text-lg font-bold text-emerald-400">+0.7351°C</span>
            <span className="text-[10px] text-emerald-400/80 block">RMSE: 3.9097°C</span>
          </div>
        </div>
      </div>
    </div>
  );
};
