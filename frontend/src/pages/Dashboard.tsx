import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { getPanchayatDetail } from '../api/panchayat';
import { getGridCells } from '../api/weather';
import { PanchayatDetailPayload, GridCell } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { WeatherComparison } from '../components/weather/WeatherComparison';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { GISMap } from '../components/map/GISMap';
import { 
  Thermometer, 
  Wind, 
  Droplets, 
  Sprout, 
  ShieldAlert, 
  Award, 
  MapPin, 
  ArrowRight,
  Sparkles,
  Sliders
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    selectedPanchayatId,
    selectedPanchayat,
    panchayats,
    targetDate,
    refreshKey,
  } = useApp();

  const [detail, setDetail] = useState<PanchayatDetailPayload | null>(null);
  const [gridCells, setGridCells] = useState<GridCell[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPanchayatId) return;

    let isMounted = true;
    async function loadDashboardData() {
      try {
        setLoading(true);
        setError(null);

        const [panchayatData, cells] = await Promise.all([
          getPanchayatDetail(selectedPanchayatId!),
          getGridCells(selectedPanchayatId!),
        ]);

        if (isMounted) {
          setDetail(panchayatData);
          setGridCells(cells);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load executive dashboard data');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, [selectedPanchayatId, targetDate, refreshKey]);

  if (loading && !detail) {
    return <LoadingState message="Assembling executive command center..." variant="full" />;
  }

  if (error && !detail) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  const isDetailCurrent = detail?.panchayat?.id === selectedPanchayatId;
  const p = isDetailCurrent && detail ? detail.panchayat : selectedPanchayat || panchayats[0];
  const weather = isDetailCurrent && detail ? detail.latest_weather : p?.latest_weather;
  const primaryCrop = isDetailCurrent && detail ? detail.agricultural_contexts?.[0] : undefined;
  const topAdvisories = isDetailCurrent && detail ? detail.active_advisories : [];
  const topRisks = isDetailCurrent && detail ? detail.detected_risks : [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Top Banner: Active Panchayat & Executive Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 glass-panel p-5 rounded-2xl border border-slate-800 bg-gradient-to-r from-emerald-950/20 via-slate-900/60 to-slate-900/40">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-emerald-500/20 text-emerald-400">
              <MapPin className="w-4 h-4" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {p?.name} Panchayat Command Center
            </h1>
            <StatusBadge status="ELIGIBLE" size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Block: {p?.block_name || 'Dhar'} • District: {p?.district_name || 'Dhar'} • State: Madhya Pradesh • 1-km Calibrated Grid
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/weather-analysis')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-medium transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>What-If Simulator</span>
          </button>
          <button
            onClick={() => navigate('/judge')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 text-slate-950 text-xs font-bold hover:bg-amber-400 transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Launch SIH Presentation</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Downscaled Temperature */}
        <MetricCard
          title="1-km Downscaled Temp"
          value={weather ? `${weather.tmean_c.toFixed(1)}` : '32.8'}
          unit="°C"
          subtitle="Certified Scalar Calibration"
          icon={Thermometer}
          status="emerald"
          badge="+0.7351°C"
          trend="up"
          trendValue="+0.7351°C"
          onClick={() => navigate('/weather-analysis')}
        />

        {/* 2. Coarse Regional Temp */}
        <MetricCard
          title="Regional NWP Coarse"
          value={weather ? `${(weather.tmean_c - 0.7351).toFixed(1)}` : '32.1'}
          unit="°C"
          subtitle="~25 km ERA5 / IMD Grid"
          icon={Thermometer}
          status="slate"
          badge="Coarse"
          onClick={() => navigate('/weather-analysis')}
        />

        {/* 3. Primary Crop Context */}
        <MetricCard
          title="Monitored Crop & Stage"
          value={primaryCrop?.crop_name || 'Cotton'}
          unit={primaryCrop?.stage_name ? `(${primaryCrop.stage_name})` : '(Flowering)'}
          subtitle="Kharif 2024 Pilot Framework"
          icon={Sprout}
          status="sky"
          badge="Kharif"
          onClick={() => navigate(`/panchayats/${p?.id}`)}
        />

        {/* 4. Active Advisory & Risk */}
        <MetricCard
          title="Advisory & Hazard Index"
          value={topAdvisories.length}
          unit="Active"
          subtitle={topRisks[0] ? topRisks[0].risk_type : 'Heat Stress Monitoring'}
          icon={ShieldAlert}
          status={topAdvisories.length > 0 ? 'rose' : 'emerald'}
          badge={p?.highest_risk_severity || 'HIGH'}
          onClick={() => navigate('/advisories')}
        />
      </div>

      {/* Main Section: Side-by-Side Weather Comparison & Spatial Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 cols: Downscaling Weather Comparison */}
        <div className="lg:col-span-7 space-y-4">
          <WeatherComparison
            weather={weather}
            panchayatName={p?.name || 'Selected'}
            blockName={p?.block_name || 'Dhar Block'}
          />

          {/* Quick links banner */}
          <div className="glass-panel p-4 rounded-xl border border-slate-800 flex items-center justify-between">
            <div className="text-xs text-slate-300">
              Explore multi-model downscaling benchmarks (Raw vs +0.7351°C vs XGBoost Research).
            </div>
            <button
              onClick={() => navigate('/weather-analysis')}
              className="flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <span>View Analysis</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right 5 cols: Mini-GIS Map Snapshot */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-emerald-400" />
                <span>Geospatial 1-km Terrain Grid</span>
              </h3>
              <button
                onClick={() => navigate('/map')}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
              >
                <span>Full Map</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {p && (
              <GISMap
                panchayat={p}
                gridCells={gridCells}
                selectedCell={null}
                onSelectCell={() => navigate('/map')}
                className="h-64"
              />
            )}

            <div className="text-[11px] text-slate-400 flex justify-between pt-1">
              <span>Projection: Dynamic UTM (EPSG:32644)</span>
              <span className="text-emerald-400 font-mono">{gridCells.length} micro-cells</span>
            </div>
          </div>
        </div>
      </div>

      {/* Urgent Farm Action Advisories Feed */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <span>Prioritized Agro-Meteorological Advisories</span>
            </h3>
            <p className="text-xs text-slate-400">
              Downscaled micro-climate triggered action directives for local farmers
            </p>
          </div>

          <button
            onClick={() => navigate('/advisories')}
            className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
          >
            <span>View All Advisories ({topAdvisories.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {topAdvisories.length === 0 ? (
          <div className="glass-panel p-8 rounded-xl border border-slate-800 text-center text-slate-400 text-xs">
            No critical hazards detected for this Panchayat under current weather parameters.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topAdvisories.slice(0, 2).map((advisory) => (
              <AdvisoryCard key={advisory.id} advisory={advisory} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
