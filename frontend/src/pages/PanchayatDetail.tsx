import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { getPanchayatDetail } from '../api/panchayat';
import { getGridCells } from '../api/weather';
import { 
  PanchayatDetailPayload, 
  GridCell, 
  CropContext, 
  AgriculturalRisk, 
  AgroAdvisory 
} from '../types';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { StatusBadge } from '../components/common/StatusBadge';
import { RiskBadge } from '../components/common/RiskBadge';
import { WeatherComparison } from '../components/weather/WeatherComparison';
import { WeatherCharts } from '../components/weather/WeatherCharts';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { GISMap } from '../components/map/GISMap';
import { GridCellInspector } from '../components/map/GridCellInspector';
import { 
  ArrowLeft, 
  MapPin, 
  Sprout, 
  ShieldAlert, 
  CloudSun, 
  Layers, 
  CheckCircle2, 
  Calendar,
  Thermometer,
  Wind
} from 'lucide-react';

export const PanchayatDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { targetDate, setSelectedPanchayatId } = useApp();

  const [detail, setDetail] = useState<PanchayatDetailPayload | null>(null);
  const [gridCells, setGridCells] = useState<GridCell[]>([]);
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'crops' | 'risks' | 'advisories' | 'gis'>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const panchayatId = id ? Number(id) : 1;

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        setSelectedCell(null); // Auto reset cell inspector on ID change

        const [payload, cells] = await Promise.all([
          getPanchayatDetail(panchayatId),
          getGridCells(panchayatId),
        ]);

        if (isMounted) {
          setDetail(payload);
          setGridCells(cells);
          setSelectedPanchayatId(panchayatId);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load Panchayat intelligence');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [panchayatId, targetDate]);

  if (loading) {
    return <LoadingState message="Loading high-resolution Panchayat profile..." variant="full" />;
  }

  if (error || !detail) {
    return (
      <ErrorState
        message={error || 'Panchayat profile not found.'}
        onRetry={() => window.location.reload()}
      />
    );
  }

  const { panchayat, latest_weather, agricultural_contexts, detected_risks, active_advisories, land_use } = detail;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Top Navigation & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/panchayats')}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
          <span className="hover:underline cursor-pointer" onClick={() => navigate('/panchayats')}>
            Panchayats
          </span>
          <span>/</span>
          <span className="text-slate-200">{panchayat.name}</span>
        </div>
      </div>

      {/* Main Header Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 bg-gradient-to-r from-emerald-950/25 via-slate-900/60 to-slate-900/40 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {panchayat.name}
            </h1>
            <StatusBadge
              status={panchayat.is_cropland_eligible ? 'ELIGIBLE' : 'INELIGIBLE'}
              size="sm"
            />
            <RiskBadge severity={panchayat.highest_risk_severity || 'LOW'} size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono">
            LGD Code: {panchayat.lgd_code || panchayat.code} • Block: {panchayat.block_name || 'Dhar'} • Centroid: {panchayat.centroid_lat?.toFixed(4) || '22.5978'}°N, {panchayat.centroid_lon?.toFixed(4) || '75.3039'}°E
          </p>
        </div>

        {/* Certified Parameter Badge */}
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
            Calibration Parameter:
          </span>
          <span className="font-mono text-emerald-400 font-bold text-sm bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-500/30">
            +0.7351°C Certified Scalar
          </span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2">
        {[
          { id: 'overview', label: 'Downscaling & Weather', icon: CloudSun },
          { id: 'crops', label: `Crop Contexts (${agricultural_contexts.length})`, icon: Sprout },
          { id: 'risks', label: `Hazard Matrix (${detected_risks.length})`, icon: ShieldAlert },
          { id: 'advisories', label: `Agro-Advisories (${active_advisories.length})`, icon: CheckCircle2 },
          { id: 'gis', label: `1-km Micro-Grid (${gridCells.length})`, icon: Layers },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.08)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview & Downscaling */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <WeatherComparison
            weather={latest_weather}
            panchayatName={panchayat.name}
            blockName={panchayat.block_name}
          />
          <WeatherCharts weather={latest_weather} />
        </div>
      )}

      {/* Tab 2: Crops & Agricultural Profiles */}
      {activeTab === 'crops' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agricultural_contexts.map((crop: CropContext, i: number) => (
            <div
              key={i}
              className="glass-panel p-5 rounded-xl border border-slate-800 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-400">
                    <Sprout className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{crop.crop_name}</h3>
                    <p className="text-xs text-slate-400">Phenological Stage: {crop.stage_name}</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  DAS: {crop.das || 45}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/50 p-3 rounded-lg border border-slate-800/80 font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Soil Texture:</span>
                  <p className="text-slate-200">{crop.soil_texture || 'Clay Loam (Vertisol)'}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Critical Temp:</span>
                  <p className="text-amber-400">{crop.critical_temperature_c ? `${crop.critical_temperature_c}°C` : '38.0°C'}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Sowing Date:</span>
                  <p className="text-slate-200">{crop.sowing_date || '2024-06-25'}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">AWC (mm/m):</span>
                  <p className="text-slate-200">{crop.available_water_capacity_mm_m || 140}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Detected Risk Matrix */}
      {activeTab === 'risks' && (
        <div className="space-y-3">
          {detected_risks.map((risk: AgriculturalRisk) => (
            <div
              key={risk.id}
              className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3"
            >
              <div className="space-y-1 max-w-xl">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-white">{risk.risk_type}</h4>
                  <RiskBadge severity={risk.severity} size="sm" />
                  <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-slate-800 text-slate-300">
                    Score: {risk.risk_score}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{risk.condition_description}</p>
              </div>

              <div className="text-right text-xs font-mono">
                <span className="text-slate-500 text-[10px] block">Trigger Value:</span>
                <span className="text-rose-400 font-bold">
                  {risk.observed_value} {risk.unit} (Threshold: {risk.threshold_value} {risk.unit})
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 4: Active Advisories */}
      {activeTab === 'advisories' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {active_advisories.map((adv: AgroAdvisory) => (
            <AdvisoryCard key={adv.id} advisory={adv} />
          ))}
        </div>
      )}

      {/* Tab 5: GIS & 1-km Grid */}
      {activeTab === 'gis' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8">
            <GISMap
              panchayat={panchayat}
              gridCells={gridCells}
              selectedCell={selectedCell}
              onSelectCell={(cell: GridCell | null) => setSelectedCell(cell)}
              className="h-[420px]"
            />
          </div>
          <div className="lg:col-span-4">
            {selectedCell ? (
              <GridCellInspector
                cell={selectedCell}
                onClose={() => setSelectedCell(null)}
                panchayatName={panchayat.name}
              />
            ) : (
              <div className="glass-panel p-6 rounded-xl border border-slate-800 text-center text-slate-400 text-xs flex flex-col items-center justify-center h-full min-h-[240px]">
                <Layers className="w-8 h-8 text-slate-600 mb-2" />
                <p className="font-medium text-slate-300">No Grid Cell Selected</p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Click on any 1-km micro-grid square on the map to inspect elevation, slope, and local calibration breakdown.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
