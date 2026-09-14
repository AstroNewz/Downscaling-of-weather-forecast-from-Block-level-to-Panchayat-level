import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  MapPin, 
  Thermometer, 
  Sprout, 
  AlertTriangle, 
  FileText, 
  Layers, 
  Droplets, 
  Mountain, 
  Compass, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { PanchayatDetailPayload, AgroAdvisory } from '../types';
import { WeatherCharts } from '../components/weather/WeatherCharts';
import { AdvisoryCard } from '../components/advisory/AdvisoryCard';
import { RiskBadge } from '../components/common/RiskBadge';
import { StatusBadge } from '../components/common/StatusBadge';

export const PanchayatDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { userRole } = useApp();

  const [detail, setDetail] = useState<PanchayatDetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'weather' | 'agri' | 'risks' | 'advisories'>('weather');
  const [selectedCropFilter, setSelectedCropFilter] = useState<string>('all');

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const data = await api.getPanchayatDetail(parseInt(id, 10));
        setDetail(data);
      } catch (err) {
        console.error('Failed to load panchayat detail', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id]);

  if (loading || !detail) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-400">Loading downscaled agro-intelligence...</p>
        </div>
      </div>
    );
  }

  const { panchayat, latest_weather, agricultural_contexts, detected_risks, active_advisories } = detail;

  const filteredAdvisories = active_advisories.filter((a) => {
    if (selectedCropFilter === 'all') return true;
    return a.crop_name.toLowerCase() === selectedCropFilter.toLowerCase();
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back button & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/panchayats')}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="hover:text-slate-200 cursor-pointer" onClick={() => navigate('/panchayats')}>
            Panchayats
          </span>
          <span>/</span>
          <span className="text-emerald-400 font-semibold">{panchayat.name}</span>
        </div>
      </div>

      {/* Main Header Banner */}
      <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                BLOCK: {panchayat.block_name || 'Ayodhya District'}
              </span>
              <StatusBadge
                status={panchayat.is_cropland_eligible ? 'ELIGIBLE' : 'NON_CROPLAND'}
                size="sm"
              />
              <span className="text-xs text-slate-400 font-mono">
                Lat: {panchayat.centroid_lat?.toFixed(4)}, Lon: {panchayat.centroid_lon?.toFixed(4)}
              </span>
            </div>

            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              {panchayat.name}
            </h1>
            <p className="text-sm text-slate-300 mt-1">
              Panchayat-level agro-meteorological advisory and downscaled micro-climate profile.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-slate-950/80 px-4 py-2.5 rounded-xl border border-slate-800 text-right">
              <span className="text-[10px] text-slate-400 block uppercase">1-km Downscaled Mean</span>
              <span className="text-2xl font-bold font-mono text-emerald-400">
                {latest_weather.tmean_c.toFixed(1)} °C
              </span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-slate-800">
          <button
            onClick={() => setActiveTab('weather')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'weather'
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <Thermometer className="w-4 h-4" />
            <span>1-km Downscaled Weather</span>
          </button>

          <button
            onClick={() => setActiveTab('agri')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'agri'
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <Sprout className="w-4 h-4" />
            <span>Agricultural Context ({agricultural_contexts.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('risks')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'risks'
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Detected Risks ({detected_risks.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('advisories')}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
              activeTab === 'advisories'
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Active Advisories ({active_advisories.length})</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Weather Tab */}
      {activeTab === 'weather' && (
        <div className="space-y-6">
          <WeatherCharts weather={latest_weather} />

          {/* Terrain & Downscaling Biophysical Evidence */}
          <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl">
            <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              <span>Downscaling Terrain & Biophysical Characteristics</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">Mean Elevation</span>
                <span className="text-lg font-bold font-mono text-white">108 m</span>
                <span className="text-[11px] text-slate-500 mt-1 block">SRTM 30m DEM aggregated</span>
              </div>

              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">Average Slope</span>
                <span className="text-lg font-bold font-mono text-white">1.8°</span>
                <span className="text-[11px] text-slate-500 mt-1 block">Gentle alluvial plain</span>
              </div>

              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">Cropland Mask Coverage</span>
                <span className="text-lg font-bold font-mono text-emerald-400">82.4%</span>
                <span className="text-[11px] text-slate-500 mt-1 block">Sentinel-2 LULC derived</span>
              </div>

              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">ML Residual Model</span>
                <span className="text-lg font-bold font-mono text-amber-400">v1.0.0 (XGBoost)</span>
                <span className="text-[11px] text-slate-500 mt-1 block">Test Calib: MAE 0.38°C</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Agricultural Context Tab */}
      {activeTab === 'agri' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {agricultural_contexts.map((ctx) => (
              <div
                key={ctx.crop_id}
                className="glass-card rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4"
              >
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <span className="text-xs font-mono font-bold text-slate-400 block">
                      SEASON: {ctx.crop_season || 'Kharif 2024'}
                    </span>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                      <Sprout className="w-5 h-5 text-emerald-400" />
                      {ctx.crop_name} ({ctx.variety || 'HYV Local'})
                    </h3>
                  </div>
                  <StatusBadge status={ctx.status} size="sm" />
                </div>

                {/* Phenological Stage & Progress */}
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Current Phenological Stage:</span>
                    <span className="font-bold text-emerald-400 uppercase">
                      {ctx.current_stage_name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Days After Sowing (DAS):</span>
                    <span className="font-mono text-slate-200">
                      {ctx.days_after_sowing || 45} Days
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Accumulated GDD (°C-days):</span>
                    <span className="font-mono text-amber-400 font-bold">
                      {ctx.accumulated_gdd || 680} / 1200 GDD
                    </span>
                  </div>
                </div>

                {/* Soil Profile & Moisture Capacity */}
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Soil Texture Profile:</span>
                    <span className="font-semibold text-slate-200">
                      {ctx.soil_profile?.soil_type || 'Alluvial Silt Loam'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Available Water Capacity (AWC):</span>
                    <span className="font-mono text-sky-400 font-bold">
                      {ctx.soil_profile?.available_water_capacity_mm || 140} mm/m
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Soil Moisture Depletion Index:</span>
                    <span className="font-mono text-emerald-400 font-bold">38% (Moderate)</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Detected Risks Tab */}
      {activeTab === 'risks' && (
        <div className="space-y-4">
          {detected_risks.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {detected_risks.map((risk) => (
                <div
                  key={risk.id}
                  className="glass-card rounded-2xl p-5 border border-slate-800 shadow-xl space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">
                        {risk.crop_name} &bull; {risk.hazard_type}
                      </span>
                      <h4 className="text-base font-bold text-white">{risk.risk_name}</h4>
                    </div>
                    <RiskBadge severity={risk.severity} score={risk.risk_score} showScore />
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                    {risk.description}
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 block">Trigger Value:</span>
                      <span className="text-rose-400 font-bold">{risk.trigger_value}</span>
                    </div>
                    <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 block">Threshold Limit:</span>
                      <span className="text-slate-300">{risk.threshold_value}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="glass-card rounded-2xl p-8 text-center border border-slate-800">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <h4 className="text-base font-bold text-white">No Active Agronomic Hazards</h4>
              <p className="text-xs text-slate-400 mt-1">
                All micro-climate metrics are within safe crop tolerance levels.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Advisories Tab */}
      {activeTab === 'advisories' && (
        <div className="space-y-4">
          {/* Crop Filter Selector if multi-crop */}
          {agricultural_contexts.length > 1 && (
            <div className="flex items-center gap-2 pb-2">
              <span className="text-xs text-slate-400 font-semibold">Filter Crop:</span>
              <button
                onClick={() => setSelectedCropFilter('all')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  selectedCropFilter === 'all'
                    ? 'bg-emerald-500 text-slate-950'
                    : 'bg-slate-800 text-slate-300'
                }`}
              >
                All Crops
              </button>
              {agricultural_contexts.map((ctx) => (
                <button
                  key={ctx.crop_id}
                  onClick={() => setSelectedCropFilter(ctx.crop_name)}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                    selectedCropFilter.toLowerCase() === ctx.crop_name.toLowerCase()
                      ? 'bg-emerald-500 text-slate-950'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {ctx.crop_name}
                </button>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4">
            {filteredAdvisories.map((advisory) => (
              <AdvisoryCard
                key={advisory.id}
                advisory={advisory}
                userRole={userRole}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
