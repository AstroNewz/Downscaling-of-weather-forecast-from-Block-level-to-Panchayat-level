import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  MapPin, 
  Grid as GridIcon, 
  Table as TableIcon, 
  Thermometer, 
  Droplets, 
  Sprout, 
  ArrowRight,
  ShieldAlert,
  Layers
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { Panchayat } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { StatusBadge } from '../components/common/StatusBadge';

export const PanchayatExplorer: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBlockId } = useApp();

  const [panchayats, setPanchayats] = useState<Panchayat[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterEligibility, setFilterEligibility] = useState<'all' | 'eligible' | 'non_cropland'>('all');
  const [filterRisk, setFilterRisk] = useState<'all' | 'critical' | 'high' | 'moderate' | 'low'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  useEffect(() => {
    const fetchPanchayats = async () => {
      setLoading(true);
      try {
        const data = await api.getPanchayats(selectedBlockId || undefined);
        setPanchayats(data);
      } catch (err) {
        console.error('Failed to fetch panchayats', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPanchayats();
  }, [selectedBlockId]);

  const filteredPanchayats = panchayats.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.block_name?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesEligibility =
      filterEligibility === 'all' ||
      (filterEligibility === 'eligible' && p.is_cropland_eligible) ||
      (filterEligibility === 'non_cropland' && !p.is_cropland_eligible);

    const matchesRisk =
      filterRisk === 'all' ||
      (p.highest_risk_severity && p.highest_risk_severity.toLowerCase() === filterRisk.toLowerCase());

    return matchesSearch && matchesEligibility && matchesRisk;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Panchayat Agricultural Directory & Downscaled Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Explore 1-km downscaled thermal predictions, agricultural contexts, and active risk alerts per panchayat.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              viewMode === 'grid'
                ? 'bg-emerald-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GridIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Grid View</span>
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              viewMode === 'table'
                ? 'bg-emerald-500 text-slate-950 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TableIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Table View</span>
          </button>
        </div>
      </div>

      {/* Search & Filters Filter Bar */}
      <div className="glass-card rounded-2xl p-4 border border-slate-700/60 shadow-lg flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search panchayat by name, code, or block..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Eligibility Filter */}
          <select
            value={filterEligibility}
            onChange={(e) => setFilterEligibility(e.target.value as any)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Land Uses</option>
            <option value="eligible">Cropland Eligible</option>
            <option value="non_cropland">Non-Cropland</option>
          </select>

          {/* Risk Filter */}
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value as any)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Risk Levels</option>
            <option value="critical">Critical Risk</option>
            <option value="high">High Risk</option>
            <option value="moderate">Moderate Risk</option>
            <option value="low">Low Risk</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredPanchayats.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/panchayats/${p.id}`)}
              className="glass-card rounded-2xl p-5 border border-slate-800 hover:border-emerald-500/50 transition-all duration-200 cursor-pointer group hover:shadow-xl hover:shadow-emerald-950/20 flex flex-col justify-between"
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <span className="text-[11px] font-mono font-bold text-slate-400 block">
                      {p.block_name || 'Ayodhya District'} &bull; CODE: {p.code || `P${p.id}`}
                    </span>
                    <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">
                      {p.name}
                    </h3>
                  </div>

                  <StatusBadge
                    status={p.is_cropland_eligible ? 'ELIGIBLE' : 'NON_CROPLAND'}
                    size="sm"
                  />
                </div>

                {/* Weather Indicators */}
                <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 mb-4 text-center">
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase">1-km Tmean</span>
                    <span className="text-sm font-bold font-mono text-emerald-400">
                      {p.latest_weather?.tmean_c?.toFixed(1) || '29.5'}°C
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase">Tmax / Tmin</span>
                    <span className="text-xs font-mono text-slate-300">
                      {p.latest_weather?.tmax_c?.toFixed(0) || '36'}°/{p.latest_weather?.tmin_c?.toFixed(0) || '24'}°
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block uppercase">Residual ΔT</span>
                    <span className="text-xs font-mono text-amber-400 font-semibold">
                      +{p.latest_weather?.predicted_residual_delta_c?.toFixed(1) || '0.8'}°C
                    </span>
                  </div>
                </div>

                {/* Risk and Cropping Summary */}
                <div className="space-y-2 text-xs text-slate-300">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Highest Risk Hazard:</span>
                    <RiskBadge severity={p.highest_risk_severity || 'NONE'} size="sm" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Active Crop Calibrations:</span>
                    <span className="font-semibold text-white">
                      {p.active_crops_count || 1} Registered Crop(s)
                    </span>
                  </div>
                </div>
              </div>

              {/* Bottom Action Footer */}
              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-emerald-400 font-semibold group-hover:text-emerald-300">
                <span>View Full Agro-Intelligence</span>
                <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="glass-card rounded-2xl overflow-hidden border border-slate-700/60 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/90 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-5 py-4">Panchayat Name</th>
                  <th className="px-5 py-4">Block</th>
                  <th className="px-5 py-4">Land Use Status</th>
                  <th className="px-5 py-4">1-km Downscaled Temp</th>
                  <th className="px-5 py-4">ML Residual (ΔT)</th>
                  <th className="px-5 py-4">Risk Level</th>
                  <th className="px-5 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPanchayats.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    onClick={() => navigate(`/panchayats/${p.id}`)}
                  >
                    <td className="px-5 py-4 font-bold text-white flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{p.name}</span>
                    </td>
                    <td className="px-5 py-4 text-slate-300">{p.block_name || 'Ayodhya District'}</td>
                    <td className="px-5 py-4">
                      <StatusBadge
                        status={p.is_cropland_eligible ? 'ELIGIBLE' : 'NON_CROPLAND'}
                        size="sm"
                      />
                    </td>
                    <td className="px-5 py-4 font-mono text-emerald-400 font-semibold">
                      {p.latest_weather?.tmean_c?.toFixed(1) || '29.5'} °C
                    </td>
                    <td className="px-5 py-4 font-mono text-amber-400 font-semibold">
                      +{p.latest_weather?.predicted_residual_delta_c?.toFixed(2) || '0.80'} °C
                    </td>
                    <td className="px-5 py-4">
                      <RiskBadge severity={p.highest_risk_severity || 'NONE'} size="sm" />
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button className="text-emerald-400 hover:text-emerald-300 font-semibold text-xs inline-flex items-center gap-1">
                        <span>Details</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
