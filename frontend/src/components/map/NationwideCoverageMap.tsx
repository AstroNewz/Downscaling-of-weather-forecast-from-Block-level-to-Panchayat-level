import React, { useState, useEffect } from 'react';
import {
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Layers,
  ChevronRight,
  TrendingDown,
  Info,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { NationalValidationSummary } from '../../types';
import { getNationalValidationSummary } from '../../api/system';

export const NationwideCoverageMap: React.FC = () => {
  const [summary, setSummary] = useState<NationalValidationSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await getNationalValidationSummary();
        setSummary(data);
      } catch (err) {
        console.error('Failed to load national validation summary:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex items-center justify-center min-h-[300px]">
        <div className="flex items-center gap-3 text-sky-400 font-mono text-xs">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
          <span>Loading Nationwide Multi-Region Validation Manifest...</span>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md p-6 shadow-xl space-y-6">
      {/* Title & Automated Claim Header */}
      <div className="space-y-3 border-b border-slate-800 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Nationwide Multi-Region Validation Coverage (SIH PS 26074)
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 font-mono text-xs font-semibold">
              {summary.total_observations.toLocaleString()} Genuine Ground Observations
            </span>
            <span className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-mono text-xs font-semibold">
              17 WMO Stations • 11 States
            </span>
          </div>
        </div>

        {/* Mandatory Automated Claim Language Banner */}
        <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold font-mono uppercase tracking-wider text-amber-300">
                Official Claim Audit Classification:
              </span>
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-200 text-xs font-mono font-bold">
                {summary.claim_language}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Scientific Transparency Policy: The system validates across 6 major Indian geographical regimes (North, Indo-Gangetic Plain, West, Central, East, Northeast). South India (Peninsular) is explicitly reported as <strong>INSUFFICIENT_OBSERVATIONS</strong> due to lack of public station downloads. Unvalidated Panchayats are never colored as validated.
            </p>
          </div>
        </div>
      </div>

      {/* Model Benchmark Comparison (Model A vs B vs C) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Model A */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Model A</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">Coarse</span>
          </div>
          <h4 className="text-sm font-bold text-white">Raw Coarse NWP (ERA5)</h4>
          <div className="pt-2 border-t border-slate-800 space-y-1 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Test MAE:</span>
              <span className="text-red-300 font-bold">1.5907°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Test RMSE:</span>
              <span className="text-slate-200">1.9922°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>R² Score:</span>
              <span className="text-slate-200">0.6128</span>
            </div>
          </div>
        </div>

        {/* Model B */}
        <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-sky-400">Model B</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">Certified Baseline</span>
          </div>
          <h4 className="text-sm font-bold text-white">Scalar Offset (+0.7351°C)</h4>
          <div className="pt-2 border-t border-sky-500/20 space-y-1 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Test MAE:</span>
              <span className="text-sky-300 font-bold">1.2661°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Test RMSE:</span>
              <span className="text-slate-200">1.6842°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Improvement vs A:</span>
              <span className="text-emerald-400">+0.3246°C</span>
            </div>
          </div>
        </div>

        {/* Model C */}
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-indigo-400">Model C</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">Dynamic v2</span>
          </div>
          <h4 className="text-sm font-bold text-white">Dynamic Residual Model v2</h4>
          <div className="pt-2 border-t border-indigo-500/20 space-y-1 text-xs font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Test MAE:</span>
              <span className="text-emerald-300 font-bold">1.1690°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Test RMSE:</span>
              <span className="text-slate-200">1.5580°C</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>ΔMAE vs Baseline:</span>
              <span className="text-emerald-400 font-bold">+0.0971°C</span>
            </div>
          </div>
        </div>
      </div>

      {/* Regional Hierarchy & Stations Explorer */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <span>7-Region Physiographic Regime Validation Matrix</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {summary.regional_breakdown.map((r) => {
            const isUnvalidated = r.status === 'INSUFFICIENT_OBSERVATIONS';
            const isSelected = selectedRegion === r.region;

            return (
              <div
                key={r.region}
                onClick={() => setSelectedRegion(isSelected ? null : r.region)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  isUnvalidated
                    ? 'border-dashed border-amber-500/40 bg-amber-950/10 hover:bg-amber-950/20'
                    : isSelected
                    ? 'border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/40'
                    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/80'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-xs font-bold text-white truncate">{r.region}</h4>
                  <span
                    className={`text-[9px] font-mono px-2 py-0.5 rounded-full font-bold uppercase ${
                      isUnvalidated
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {isUnvalidated ? 'Unvalidated' : 'Validated'}
                  </span>
                </div>

                <div className="mt-2.5 pt-2 border-t border-slate-800/80 space-y-1 text-[11px] font-mono">
                  <div className="flex justify-between text-slate-400">
                    <span>Stations:</span>
                    <span className="text-slate-200">{r.station_count} WMO Nodes</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Observations:</span>
                    <span className="text-slate-200">{r.sample_count ? r.sample_count.toLocaleString() : '0 (Data Gap)'}</span>
                  </div>
                  {r.baseline_mae !== null && r.baseline_mae !== undefined && (
                    <div className="flex justify-between text-slate-400">
                      <span>Baseline MAE:</span>
                      <span className="text-sky-300">{r.baseline_mae.toFixed(2)}°C</span>
                    </div>
                  )}
                  {r.dynamic_v2_mae !== null && r.dynamic_v2_mae !== undefined && (
                    <div className="flex justify-between text-slate-400">
                      <span>Dynamic v2 MAE:</span>
                      <span className="text-emerald-300 font-bold">{r.dynamic_v2_mae.toFixed(2)}°C</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 17 WMO Synoptic Ground Stations Catalog Table */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-bold text-white">Station Ground Truth Network (17 WMO Synoptic Stations)</span>
          <span className="font-mono text-[11px]">100% Genuine NOAA ISD / WMO Ground Observations</span>
        </div>

        <div className="overflow-x-auto max-h-[260px] overflow-y-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
              <tr>
                <th className="p-2.5">WMO ID</th>
                <th className="p-2.5">Station Name</th>
                <th className="p-2.5">State</th>
                <th className="p-2.5">Region</th>
                <th className="p-2.5">Coordinates</th>
                <th className="p-2.5">Elevation</th>
                <th className="p-2.5">Physiographic Regime</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/40 text-slate-300">
              {summary.stations_catalog.map((st) => (
                <tr key={st.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-2.5 text-indigo-300 font-bold">{st.id}</td>
                  <td className="p-2.5 font-sans font-medium text-white">{st.name}</td>
                  <td className="p-2.5 text-slate-300">{st.state}</td>
                  <td className="p-2.5 text-slate-400">{st.region}</td>
                  <td className="p-2.5 text-slate-400">{st.lat.toFixed(2)}°N, {st.lon.toFixed(2)}°E</td>
                  <td className="p-2.5 text-sky-300">{st.elev.toFixed(0)}m</td>
                  <td className="p-2.5 text-slate-400 font-sans text-[11px]">{st.physiographic_regime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
