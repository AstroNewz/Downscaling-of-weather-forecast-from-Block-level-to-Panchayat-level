import React, { useState, useEffect, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { getAdvisories } from '../api/advisory';
import { AgroAdvisory, AdvisoryPriority } from '../types';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { 
  ShieldAlert, 
  Filter, 
  Search, 
  Flame, 
  Droplets, 
  Wind, 
  Bug, 
  HelpCircle,
  Building2
} from 'lucide-react';

export const AgroAdvisories: React.FC = () => {
  const {
    selectedPanchayatId,
    selectedPanchayat,
    panchayats,
    setSelectedPanchayatId,
    refreshKey,
  } = useApp();

  const [advisories, setAdvisories] = useState<AgroAdvisory[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoading(true);
        const data = await getAdvisories(selectedPanchayatId ? { panchayat_id: selectedPanchayatId } : undefined);
        if (isMounted) {
          setAdvisories(data);
        }
      } catch (err) {
        console.error('Failed to load advisories:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [selectedPanchayatId, refreshKey]);

  // Filtered advisories
  const filteredAdvisories = useMemo(() => {
    return advisories.filter((adv: AgroAdvisory) => {
      const query = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !query ||
        adv.title.toLowerCase().includes(query) ||
        (adv.headline && adv.headline.toLowerCase().includes(query)) ||
        adv.crop_name.toLowerCase().includes(query) ||
        adv.rationale.toLowerCase().includes(query);

      const matchesCategory =
        categoryFilter === 'ALL' || adv.category.toUpperCase() === categoryFilter;

      const matchesPriority =
        priorityFilter === 'ALL' || (adv.priority && adv.priority.toUpperCase() === priorityFilter);

      return matchesSearch && matchesCategory && matchesPriority;
    });
  }, [advisories, searchQuery, categoryFilter, priorityFilter]);

  const criticalCount = advisories.filter((a: AgroAdvisory) => a.priority === 'CRITICAL').length;
  const highCount = advisories.filter((a: AgroAdvisory) => a.priority === 'HIGH').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">
              Agro-Meteorological Action Advisories
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic rule-engine alerts derived from 1-km downscaled weather observations
          </p>
        </div>

        {/* Panchayat Target Selector */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs">
          <span className="text-slate-400">Target Panchayat:</span>
          <select
            id="advisories-panchayat-select"
            value={selectedPanchayatId || ''}
            onChange={(e) => setSelectedPanchayatId(Number(e.target.value))}
            className="bg-transparent text-emerald-400 font-bold focus:outline-none cursor-pointer"
          >
            {panchayats.map((p) => (
              <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase block">Total Advisories</span>
          <span className="text-xl font-bold font-mono text-white">{advisories.length}</span>
          <span className="text-[10px] text-slate-500 block">Current Cycle</span>
        </div>

        <div className="glass-panel p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/10">
          <span className="text-[10px] font-mono text-rose-400 uppercase block">Critical Priority</span>
          <span className="text-xl font-bold font-mono text-rose-300">{criticalCount}</span>
          <span className="text-[10px] text-rose-400/70 block">Immediate Action Required</span>
        </div>

        <div className="glass-panel p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/10">
          <span className="text-[10px] font-mono text-amber-400 uppercase block">High Priority</span>
          <span className="text-xl font-bold font-mono text-amber-300">{highCount}</span>
          <span className="text-[10px] text-amber-400/70 block">Next 24-48h Execution</span>
        </div>

        <div className="glass-panel p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/10">
          <span className="text-[10px] font-mono text-emerald-400 uppercase block">Explainability Status</span>
          <span className="text-base font-bold font-mono text-emerald-300">100% Traceable</span>
          <span className="text-[10px] text-emerald-400/70 block">5-Step Deterministic</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            id="advisories-search-input"
            type="text"
            placeholder="Search advisories by crop, keyword, or action..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Category Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Category:</span>
            <select
              id="advisories-category-filter"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Hazards</option>
              <option value="HEAT_STRESS" className="bg-slate-900">Heat Stress</option>
              <option value="IRRIGATION" className="bg-slate-900">Irrigation</option>
              <option value="WIND" className="bg-slate-900">Wind / Lodging</option>
              <option value="PEST_DISEASE" className="bg-slate-900">Pest & Disease</option>
            </select>
          </div>

          {/* Priority Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
            <span className="text-slate-400 text-[11px]">Priority:</span>
            <select
              id="advisories-priority-filter"
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Priorities</option>
              <option value="CRITICAL" className="bg-slate-900">Critical</option>
              <option value="HIGH" className="bg-slate-900">High</option>
              <option value="MEDIUM" className="bg-slate-900">Medium</option>
              <option value="LOW" className="bg-slate-900">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Advisories Grid */}
      {loading ? (
        <LoadingState count={4} variant="card" />
      ) : filteredAdvisories.length === 0 ? (
        <EmptyState
          title="No Advisories Match Criteria"
          message="No agro-advisories found for the selected category, priority, or search term."
          actionText="Reset Filters"
          onAction={() => {
            setSearchQuery('');
            setCategoryFilter('ALL');
            setPriorityFilter('ALL');
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredAdvisories.map((advisory: AgroAdvisory) => (
            <AdvisoryCard key={advisory.id} advisory={advisory} />
          ))}
        </div>
      )}
    </div>
  );
};
