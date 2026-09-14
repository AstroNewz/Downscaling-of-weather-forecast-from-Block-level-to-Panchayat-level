import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  MapPin, 
  Grid, 
  AlertTriangle, 
  CheckCircle2, 
  FileText, 
  TrendingUp, 
  ArrowRight, 
  Cpu, 
  ShieldCheck,
  Thermometer,
  CloudSun
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { MetricCard } from '../components/common/MetricCard';
import { PipelineVisualizer } from '../components/common/PipelineVisualizer';
import { RiskBadge } from '../components/common/RiskBadge';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { GISMap } from '../components/map/GISMap';
import { api } from '../services/api';
import { Panchayat, AgroAdvisory, AgriculturalRisk } from '../types';

export const Overview: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBlockId, targetDate, userRole } = useApp();

  const [panchayats, setPanchayats] = useState<Panchayat[]>([]);
  const [advisories, setAdvisories] = useState<AgroAdvisory[]>([]);
  const [risks, setRisks] = useState<AgriculturalRisk[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [panchayatList, advisoryList, riskList] = await Promise.all([
          api.getPanchayats(selectedBlockId || undefined),
          api.getAdvisories({ block_id: selectedBlockId || undefined }),
          api.getRisks({ block_id: selectedBlockId || undefined }),
        ]);
        setPanchayats(panchayatList);
        setAdvisories(advisoryList);
        setRisks(riskList);
      } catch (err) {
        console.error('Failed to load overview data', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedBlockId, targetDate]);

  const criticalRisks = risks.filter((r) => r.severity === 'CRITICAL' || r.severity === 'HIGH');
  const criticalAdvisories = advisories.filter(
    (a) => a.priority === 'CRITICAL' || a.priority === 'HIGH' || a.conflict_flag
  );

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner / Role Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900/90 via-emerald-950/20 to-slate-900/90 border border-slate-700/60 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wider">
              {userRole} Mode
            </span>
            <span className="text-xs text-slate-400 font-mono">
              SIH Problem Statement 26074
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Panchayat Agro-Meteorological Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-300 mt-1 max-w-3xl">
            1-km ML Temperature Downscaling &bull; Area-Weighted Boundary Aggregation &bull; Agricultural Risk & Agro-Advisories
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => navigate('/panchayats')}
            className="px-4 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-sm hover:bg-emerald-400 transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/20"
          >
            <span>Explore Panchayats</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Monitored Panchayats"
          value={panchayats.length}
          subtitle="Ayodhya District (Maya Bazar & Sohawal)"
          icon={MapPin}
          color="emerald"
        />

        <MetricCard
          title="1-km Downscaled Grid Cells"
          value={panchayats.length * 4}
          subtitle="SRTM DEM & LULC Residual Inferred"
          icon={Grid}
          color="blue"
        />

        <MetricCard
          title="Active Agronomic Risks"
          value={criticalRisks.length}
          subtitle={`${criticalRisks.length} critical/high hazards requiring action`}
          icon={AlertTriangle}
          color={criticalRisks.length > 0 ? 'rose' : 'emerald'}
        />

        <MetricCard
          title="Agro-Advisories Active"
          value={advisories.length}
          subtitle="Priority ranked with operational timing"
          icon={FileText}
          color="amber"
        />
      </div>

      {/* Interactive 12-Phase Pipeline Journey */}
      <PipelineVisualizer />

      {/* Grid: Map & Critical Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Spatial GIS Map Overview (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Spatial Thermal & Risk Field (1-km Resolution)
              </h2>
            </div>
            <button
              onClick={() => navigate('/map')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>Full Screen GIS</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <GISMap
            panchayats={panchayats}
            height="460px"
            onSelectPanchayat={(p) => navigate(`/panchayats/${p.id}`)}
          />
        </div>

        {/* Right Column: High-Priority Advisories & Conflict Feed (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Urgent Action & Risk Alerts
              </h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-500/40">
                {criticalAdvisories.length} Urgent
              </span>
            </div>
            <button
              onClick={() => navigate('/advisories')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
            {criticalAdvisories.length > 0 ? (
              criticalAdvisories.map((advisory) => (
                <AdvisoryCard
                  key={advisory.id}
                  advisory={advisory}
                  userRole={userRole}
                />
              ))
            ) : (
              <div className="glass-card rounded-2xl p-8 text-center border border-slate-800">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                <h4 className="text-sm font-bold text-white">No Critical Hazards</h4>
                <p className="text-xs text-slate-400 mt-1">
                  All monitored panchayats are operating within normal agronomic thresholds.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
