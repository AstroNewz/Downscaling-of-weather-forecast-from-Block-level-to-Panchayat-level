import React, { useState } from 'react';
import { 
  CloudSun, 
  Cpu, 
  Grid, 
  MapPin, 
  Sprout, 
  AlertTriangle, 
  FileText, 
  Monitor, 
  ChevronRight,
  Info,
  CheckCircle2
} from 'lucide-react';

interface StageInfo {
  phase: number;
  name: string;
  shortName: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  input: string;
  output: string;
  resolution: string;
  status: 'operational' | 'ready';
}

const stages: StageInfo[] = [
  {
    phase: 3,
    name: 'Block Forecast Ingestion',
    shortName: 'Block Forecast',
    icon: CloudSun,
    description: 'Ingests coarse NWP forecasts (IMD/GFS/ECMWF) at block scale.',
    input: 'NWP raw forecast files / APIs',
    output: 'Coarse block-level Tmax, Tmin, Tmean, RH, Wind, Rain',
    resolution: '~10-25 km block polygon',
    status: 'operational',
  },
  {
    phase: 6,
    name: 'XGBoost ML Residual Engine',
    shortName: 'ML Residuals',
    icon: Cpu,
    description: 'Predicts high-resolution temperature residual corrections via gradient boosting.',
    input: 'Coarse T + SRTM DEM + LULC features (elevation, slope, aspect, veg fraction)',
    output: 'Residual temperature delta (ΔT)',
    resolution: 'Point / Grid level',
    status: 'operational',
  },
  {
    phase: 7,
    name: '1-km Spatial Weather Grid',
    shortName: '1-km Grid',
    icon: Grid,
    description: 'Combines coarse block temperature with ML residual to generate 1-km continuous field.',
    input: 'Block T + Predicted residual ΔT',
    output: 'Continuous 1-km Downscaled Temperature field',
    resolution: '1-km x 1-km projected metric grid',
    status: 'operational',
  },
  {
    phase: 8,
    name: 'Panchayat Area-Weighted Aggregation',
    shortName: 'Panchayat Weather',
    icon: MapPin,
    description: 'Intersects 1-km grid with administrative panchayat boundaries using area weights.',
    input: '1-km temperature grid + Panchayat GIS boundary polygons',
    output: 'Panchayat Tmax, Tmin, Tmean, RH, Wind + Coarse Rainfall',
    resolution: 'Panchayat administrative boundary',
    status: 'operational',
  },
  {
    phase: 9,
    name: 'Agricultural Context Engine',
    shortName: 'Crop Context',
    icon: Sprout,
    description: 'Enriches localized weather with active crops, phenological stage, soil profiles & cropland mask.',
    input: 'Panchayat weather + Crop calendar + Phenology + Soil water capacity',
    output: 'Panchayat Agricultural Context (COMPLETE / PARTIAL / UNAVAILABLE)',
    resolution: 'Crop-stage-soil tuple per Panchayat',
    status: 'operational',
  },
  {
    phase: 10,
    name: 'Agricultural Risk Engine',
    shortName: 'Risk Engine',
    icon: AlertTriangle,
    description: 'Evaluates multi-hazard agronomic thresholds (heat stress, drought, disease, waterlogging).',
    input: 'Panchayat Agricultural Context + Stage-specific thresholds',
    output: 'Detected agricultural risks with severity (CRITICAL, HIGH, MODERATE, LOW)',
    resolution: 'Ranked risk list per crop',
    status: 'operational',
  },
  {
    phase: 11,
    name: 'Agro-Advisory Generation Engine',
    shortName: 'Advisory Engine',
    icon: FileText,
    description: 'Synthesizes explainable, prioritized advisories with conflict detection & operational timing.',
    input: 'Detected risks + Advisory rule catalog (v1.0.0)',
    output: 'Actionable farming advisories with urgency, window & evidence',
    resolution: 'Structured Advisory Cards',
    status: 'operational',
  },
  {
    phase: 12,
    name: 'Panchayat Delivery Dashboard',
    shortName: 'Delivery Layer',
    icon: Monitor,
    description: 'Interactive web dashboard, GIS map & multi-stakeholder delivery layer.',
    input: 'End-to-end pipeline outputs (Phases 3-11)',
    output: 'Farmer views, Extension Officer dashboards, Admin governance & GIS explorer',
    resolution: 'Web & GIS interface',
    status: 'operational',
  },
];

export const PipelineVisualizer: React.FC = () => {
  const [selectedStage, setSelectedStage] = useState<StageInfo>(stages[6]); // Default to advisory/delivery

  return (
    <div className="glass-card rounded-2xl p-6 border border-slate-700/60 shadow-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              End-to-End Scientific Architecture
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
              Phases 1–12 Integrated
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            From coarse block NWP down to 1-km ML temperature grid, panchayat aggregation, and actionable agro-advisories.
          </p>
        </div>
      </div>

      {/* Pipeline Stages Flow */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 mb-6">
        {stages.map((stage, idx) => {
          const isSelected = selectedStage.phase === stage.phase;
          const Icon = stage.icon;

          return (
            <button
              key={stage.phase}
              onClick={() => setSelectedStage(stage)}
              className={`relative flex flex-col items-center text-center p-3 rounded-xl border transition-all duration-200 cursor-pointer ${
                isSelected
                  ? 'bg-emerald-950/40 border-emerald-500/60 shadow-md shadow-emerald-950/40 scale-[1.03]'
                  : 'bg-slate-900/50 border-slate-800 hover:bg-slate-800/60 hover:border-slate-700'
              }`}
            >
              <div className="absolute top-1.5 right-1.5 flex items-center">
                <span className="text-[10px] font-mono text-slate-400">P{stage.phase}</span>
              </div>
              
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center mb-2 transition-colors ${
                  isSelected
                    ? 'bg-emerald-500 text-slate-950 shadow-sm'
                    : 'bg-slate-800 text-slate-300'
                }`}
              >
                <Icon className="w-5 h-5" />
              </div>

              <span className="text-xs font-bold text-slate-200 line-clamp-1 mb-0.5">
                {stage.shortName}
              </span>
              <span className="text-[10px] text-slate-400 line-clamp-1">
                {stage.resolution}
              </span>

              {idx < stages.length - 1 && (
                <div className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-600">
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected Stage Detail Panel */}
      <div className="bg-slate-900/80 rounded-xl border border-slate-800 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <selectedStage.icon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-800 text-emerald-400 border border-slate-700">
                  PHASE {selectedStage.phase}
                </span>
                <h3 className="text-base font-bold text-white">
                  {selectedStage.name}
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Spatial Resolution: <span className="text-slate-200 font-medium">{selectedStage.resolution}</span>
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              {selectedStage.status}
            </span>
          </div>
        </div>

        <p className="text-sm text-slate-300 my-4 leading-relaxed">
          {selectedStage.description}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="bg-slate-950/60 rounded-lg p-3.5 border border-slate-800/80">
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] block mb-1">
              Input Ingestion / Feature Inputs
            </span>
            <p className="text-slate-200 font-mono text-[11px] leading-relaxed">
              {selectedStage.input}
            </p>
          </div>
          <div className="bg-slate-950/60 rounded-lg p-3.5 border border-slate-800/80">
            <span className="font-semibold text-emerald-400 uppercase tracking-wider text-[10px] block mb-1">
              Generated Pipeline Output
            </span>
            <p className="text-slate-200 font-mono text-[11px] leading-relaxed">
              {selectedStage.output}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
