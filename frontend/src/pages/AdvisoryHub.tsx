import React, { useEffect, useState } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  AlertTriangle, 
  CheckCircle2, 
  Droplets, 
  Wind, 
  Thermometer, 
  Sprout 
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { AgroAdvisory } from '../types';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { PriorityBadge } from '../components/common/PriorityBadge';

export const AdvisoryHub: React.FC = () => {
  const { selectedBlockId, userRole } = useApp();

  const [advisories, setAdvisories] = useState<AgroAdvisory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [cropFilter, setCropFilter] = useState<string>('all');

  useEffect(() => {
    const fetchAdvisories = async () => {
      setLoading(true);
      try {
        const data = await api.getAdvisories({
          block_id: selectedBlockId || undefined,
        });
        setAdvisories(data);
      } catch (err) {
        console.error('Failed to fetch advisories', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAdvisories();
  }, [selectedBlockId]);

  const filteredAdvisories = advisories.filter((a) => {
    const matchesSearch =
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.action_summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.crop_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.panchayat_name?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      categoryFilter === 'all' ||
      a.category.toLowerCase() === categoryFilter.toLowerCase();

    const matchesPriority =
      priorityFilter === 'all' ||
      a.priority.toLowerCase() === priorityFilter.toLowerCase();

    const matchesCrop =
      cropFilter === 'all' ||
      a.crop_name.toLowerCase() === cropFilter.toLowerCase();

    return matchesSearch && matchesCategory && matchesPriority && matchesCrop;
  });

  const criticalCount = advisories.filter((a) => a.priority === 'CRITICAL').length;
  const conflictCount = advisories.filter((a) => a.conflict_flag).length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
              AGRO-METEOROLOGICAL ADVISORY ENGINE &bull; PHASE 11
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Agro-Meteorological Advisory Hub
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Operational recommendations synthesized from 1-km downscaled weather, crop stage thresholds & soil moisture.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {conflictCount > 0 && (
            <div className="px-3 py-1.5 rounded-xl bg-rose-950/80 border border-rose-500/40 text-rose-300 text-xs font-bold flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>{conflictCount} Conflict Alert(s)</span>
            </div>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-card rounded-2xl p-4 border border-slate-700/60 shadow-lg flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search advisories by action, crop, hazard, or panchayat..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Category Filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Operations</option>
            <option value="irrigation">Irrigation</option>
            <option value="heat_stress">Heat Protection</option>
            <option value="pest_disease">Spraying / Pest</option>
            <option value="harvest">Harvest</option>
          </select>

          {/* Priority Filter */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical Priority</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>

          {/* Crop Filter */}
          <select
            value={cropFilter}
            onChange={(e) => setCropFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
          >
            <option value="all">All Crops</option>
            <option value="rice">Rice (Paddy)</option>
            <option value="maize">Maize (Corn)</option>
            <option value="wheat">Wheat</option>
          </select>
        </div>
      </div>

      {/* Advisory Cards List */}
      <div className="space-y-4">
        {filteredAdvisories.length > 0 ? (
          filteredAdvisories.map((advisory) => (
            <AdvisoryCard
              key={advisory.id}
              advisory={advisory}
              userRole={userRole}
            />
          ))
        ) : (
          <div className="glass-card rounded-2xl p-12 text-center border border-slate-800">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h3 className="text-base font-bold text-white">No Advisories Match Your Filter</h3>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting search terms or resetting priority/category filters.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
