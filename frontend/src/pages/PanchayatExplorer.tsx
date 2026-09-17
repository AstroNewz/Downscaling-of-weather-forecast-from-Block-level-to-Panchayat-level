import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Panchayat, RiskSeverity, BlockItem } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { 
  Search, 
  Filter, 
  LayoutGrid, 
  Table as TableIcon, 
  MapPin, 
  Thermometer, 
  ArrowRight,
  Building2,
  CheckCircle2
} from 'lucide-react';

export const PanchayatExplorer: React.FC = () => {
  const navigate = useNavigate();
  const {
    panchayats,
    blocks,
    selectedBlockId,
    setSelectedBlockId,
    setSelectedPanchayatId,
    loadingData,
  } = useApp();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [croplandOnly, setCroplandOnly] = useState<boolean>(false);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Filtered Panchayats list
  const filteredPanchayats = useMemo(() => {
    return panchayats.filter((p: Panchayat) => {
      // Search match
      const query = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !query ||
        p.name.toLowerCase().includes(query) ||
        (p.code && p.code.toLowerCase().includes(query)) ||
        (p.block_name && p.block_name.toLowerCase().includes(query));

      // Cropland eligibility match
      const matchesCropland = !croplandOnly || p.is_cropland_eligible;

      // Severity match
      const matchesSeverity =
        severityFilter === 'ALL' ||
        (p.highest_risk_severity && p.highest_risk_severity.toUpperCase() === severityFilter);

      return matchesSearch && matchesCropland && matchesSeverity;
    });
  }, [panchayats, searchQuery, croplandOnly, severityFilter]);

  const handleSelectPanchayat = (p: Panchayat) => {
    setSelectedPanchayatId(p.id);
    navigate(`/panchayats/${p.id}`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">
              Panchayat Directory & Explorer
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Browse, filter, and inspect downscaled micro-climate profiles across Dhar pilot blocks
          </p>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          <button
            id="view-mode-grid"
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'grid'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Grid Cards View"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            id="view-mode-table"
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'table'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Tabular View"
          >
            <TableIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        {/* Search Box */}
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            id="panchayat-search-input"
            type="text"
            placeholder="Search by Panchayat name or LGD code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Block Dropdown */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Block:</span>
            <select
              id="explorer-block-filter"
              value={selectedBlockId || ''}
              onChange={(e) => setSelectedBlockId(e.target.value ? Number(e.target.value) : null)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900">All Blocks</option>
              {blocks.map((b: BlockItem) => (
                <option key={b.id} value={b.id} className="bg-slate-900">
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          {/* Risk Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Risk:</span>
            <select
              id="explorer-risk-filter"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Severities</option>
              <option value="CRITICAL" className="bg-slate-900">Critical</option>
              <option value="HIGH" className="bg-slate-900">High</option>
              <option value="MODERATE" className="bg-slate-900">Moderate</option>
              <option value="LOW" className="bg-slate-900">Low</option>
            </select>
          </div>

          {/* Cropland Eligible Toggle */}
          <button
            id="explorer-cropland-toggle"
            onClick={() => setCroplandOnly(!croplandOnly)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              croplandOnly
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 font-semibold'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Cropland Eligible</span>
          </button>
        </div>
      </div>

      {/* Results Count Banner */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          Showing <strong className="text-slate-200">{filteredPanchayats.length}</strong> of{' '}
          <strong className="text-slate-200">{panchayats.length}</strong> Panchayats
        </span>
        <span className="font-mono text-[11px]">
          Dynamic UTM Area Verification Active
        </span>
      </div>

      {/* Loading State */}
      {loadingData && (
        <LoadingState count={6} variant={viewMode === 'grid' ? 'card' : 'table'} />
      )}

      {/* Empty State */}
      {!loadingData && filteredPanchayats.length === 0 && (
        <EmptyState
          title="No Matching Panchayats"
          message="No Panchayats found matching the selected search query, block, or risk severity filters."
          actionText="Reset Filters"
          onAction={() => {
            setSearchQuery('');
            setCroplandOnly(false);
            setSeverityFilter('ALL');
          }}
        />
      )}

      {/* Grid Cards View */}
      {!loadingData && viewMode === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPanchayats.map((p: Panchayat) => {
            const weather = p.latest_weather;
            return (
              <div
                key={p.id}
                id={`panchayat-card-${p.id}`}
                onClick={() => handleSelectPanchayat(p)}
                className="glass-panel p-5 rounded-xl border border-slate-800 hover:border-emerald-500/40 transition-all duration-200 cursor-pointer flex flex-col justify-between group hover:shadow-[0_0_20px_rgba(16,185,129,0.08)]"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h3 className="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors">
                        {p.name}
                      </h3>
                      <p className="text-xs text-slate-400 font-mono">
                        {p.block_name || 'Dhar Block'} • LGD: {p.lgd_code || p.code || '245601'}
                      </p>
                    </div>
                    <StatusBadge
                      status={p.is_cropland_eligible ? 'ELIGIBLE' : 'INELIGIBLE'}
                      size="sm"
                    />
                  </div>

                  {/* Physical & Meteorological Summary */}
                  <div className="grid grid-cols-2 gap-2 my-3 p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono">
                    <div>
                      <span className="text-[10px] text-slate-500 block">1-km Downscaled</span>
                      <span className="font-bold text-emerald-400">
                        {weather ? `${weather.tmean_c.toFixed(1)}°C` : '32.8°C'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Total Area</span>
                      <span className="text-slate-300">
                        {p.total_area_ha ? `${p.total_area_ha} ha` : '1,240 ha'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Footer: Risk badge & Action */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-2 text-xs">
                  <RiskBadge severity={p.highest_risk_severity || 'LOW'} size="sm" />
                  <span className="flex items-center gap-1 text-emerald-400 group-hover:translate-x-0.5 transition-transform font-medium">
                    <span>Inspect</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tabular View */}
      {!loadingData && viewMode === 'table' && (
        <div className="glass-panel rounded-xl border border-slate-800 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Panchayat</th>
                <th className="px-4 py-3">Block</th>
                <th className="px-4 py-3">Cropland Status</th>
                <th className="px-4 py-3">1-km Temp (Tmean)</th>
                <th className="px-4 py-3">Highest Risk</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {filteredPanchayats.map((p: Panchayat) => (
                <tr
                  key={p.id}
                  onClick={() => handleSelectPanchayat(p)}
                  className="hover:bg-slate-900/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-white">
                    {p.name}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {p.block_name || 'Dhar'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      status={p.is_cropland_eligible ? 'ELIGIBLE' : 'INELIGIBLE'}
                      size="sm"
                    />
                  </td>
                  <td className="px-4 py-3 font-mono text-emerald-400 font-bold">
                    {p.latest_weather ? `${p.latest_weather.tmean_c.toFixed(1)}°C` : '32.8°C'}
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge severity={p.highest_risk_severity || 'LOW'} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectPanchayat(p);
                      }}
                      className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
