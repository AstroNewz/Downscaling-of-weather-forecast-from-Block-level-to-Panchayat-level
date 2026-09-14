import React, { useState } from 'react';
import { 
  Play, 
  CheckCircle2, 
  ChevronRight, 
  ChevronLeft, 
  CloudSun, 
  Cpu, 
  Grid, 
  MapPin, 
  Sprout, 
  Layers, 
  AlertTriangle, 
  FileText, 
  HelpCircle, 
  TrendingUp,
  Sparkles,
  Info,
  Clock,
  Droplets,
  Wind,
  ShieldCheck,
  RotateCcw
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { RiskBadge } from '../components/common/RiskBadge';
import { StatusBadge } from '../components/common/StatusBadge';

interface PipelineStep {
  step: number;
  title: string;
  badge: string;
  description: string;
  details: React.ReactNode;
}

export const JudgeMode: React.FC = () => {
  const { isLiveApi } = useApp();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedCrop, setSelectedCrop] = useState<'rice' | 'maize'>('rice');
  const [isRunningPipeline, setIsRunningPipeline] = useState<boolean>(false);
  const [pipelineProgress, setPipelineProgress] = useState<number>(0);
  const [pipelineCompleted, setPipelineCompleted] = useState<boolean>(false);

  const runDemoPipeline = () => {
    setIsRunningPipeline(true);
    setPipelineProgress(0);
    setPipelineCompleted(false);

    const interval = setInterval(() => {
      setPipelineProgress((prev) => {
        if (prev >= 6) {
          clearInterval(interval);
          setIsRunningPipeline(false);
          setPipelineCompleted(true);
          return 6;
        }
        return prev + 1;
      });
    }, 450);
  };

  const steps: PipelineStep[] = [
    {
      step: 1,
      title: 'Problem: Block NWP Forecast vs Farm Field Scale',
      badge: 'Step 1: The Challenge',
      description: 'Coarse numerical weather predictions (~25 km resolution) average out terrain elevation and micro-climatic gradients, leading to missed localized heat and moisture shocks at the Panchayat field level.',
      details: (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                Conventional Coarse Block Forecast (~25 km)
              </span>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-slate-400">Block Name:</span><span className="text-slate-200 font-semibold">Maya Bazar Block</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Forecast Tmax:</span><span className="text-amber-400 font-mono font-bold">36.0 °C</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Spatial Resolution:</span><span className="text-slate-300 font-mono">~25 km x 25 km</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Limitation:</span><span className="text-rose-400">Blends valleys & uplands</span></div>
              </div>
            </div>

            <div className="bg-emerald-950/20 p-4 rounded-xl border border-emerald-500/40">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block mb-2">
                Panchayat Agricultural Requirement (~1 km)
              </span>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-slate-400">Target Unit:</span><span className="text-slate-200 font-semibold">Maya Bazar Gram Panchayat</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Terrain Elevation:</span><span className="text-slate-200 font-mono">112 m (Gentle Alluvial Plain)</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Cropland Area:</span><span className="text-emerald-400 font-mono font-bold">1,020 / 1,250 ha (81.6%)</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Target Resolution:</span><span className="text-emerald-300 font-mono font-bold">1-km Spatial Downscaling</span></div>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 2,
      title: 'ML Temperature Residual Downscaling (1-km Metric Grid)',
      badge: 'Step 2: Physics + ML',
      description: 'Our XGBoost engine predicts high-resolution residual temperature anomalies (ΔT) based on SRTM 30m DEM elevation, slope, aspect, and Sentinel-2 vegetation fraction: T_downscaled = T_coarse + ΔT.',
      details: (
        <div className="space-y-4">
          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 text-center">
            <span className="font-mono text-sm sm:text-base font-bold text-white">
              T<sub className="text-xs">downscaled</sub> (1-km) = 36.0°C (Block) + <span className="text-amber-400">+1.8°C (Predicted Residual ΔT)</span> = <span className="text-emerald-400 font-bold">37.8°C</span>
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Elevation Lapse</span>
              <span className="font-mono text-slate-200 font-bold">112 m (SRTM)</span>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Terrain Slope</span>
              <span className="font-mono text-slate-200 font-bold">1.8° Plain</span>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Cropland Fraction</span>
              <span className="font-mono text-emerald-400 font-bold">81.6%</span>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 block uppercase">Model Version</span>
              <span className="font-mono text-amber-400 font-bold">XGBoost v1.0.0</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      step: 3,
      title: 'Panchayat Area-Weighted Weather Aggregation',
      badge: 'Step 3: GIS Aggregation',
      description: 'The 1-km continuous downscaled grid is spatially intersected with administrative Gram Panchayat polygons using area-weighting: T_panchayat = Σ(w_i × T_i) / Σ(w_i).',
      details: (
        <div className="space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
            <span className="text-slate-300 font-semibold">Maya Bazar Demo Gram Panchayat Aggregated Profile:</span>
            <StatusBadge status="COMPLETE" size="sm" />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">1-km Tmax</span>
              <span className="text-lg font-bold font-mono text-rose-400">37.8 °C</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">1-km Tmean</span>
              <span className="text-lg font-bold font-mono text-emerald-400">31.7 °C</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">Wind Speed</span>
              <span className="text-lg font-bold font-mono text-sky-400">28.0 km/h</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">Precipitation</span>
              <span className="text-lg font-bold font-mono text-blue-400">0.0 mm*</span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 italic text-center pt-1">
            *Rainfall is propagated from coarse block NWP and is not downscaled. Temperature is 1-km downscaled.
          </p>
        </div>
      ),
    },
    {
      step: 4,
      title: 'Multi-Crop Phenology & Soil Hydrological Context',
      badge: 'Step 4: Agricultural Context',
      description: 'Enriches weather with calibrated crop calendars, growth stages (DAS & GDD), and soil water holding capacity. Proves complete multi-crop separation.',
      details: (
        <div className="space-y-3">
          <div className="flex items-center gap-2 pb-1">
            <span className="text-xs text-slate-400 font-semibold">Select Demonstration Crop:</span>
            <button
              onClick={() => setSelectedCrop('rice')}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                selectedCrop === 'rice'
                  ? 'bg-emerald-500 text-slate-950 shadow-md'
                  : 'bg-slate-800 text-slate-300'
              }`}
            >
              🌾 Rice (Paddy) — Flowering Stage
            </button>
            <button
              onClick={() => setSelectedCrop('maize')}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                selectedCrop === 'maize'
                  ? 'bg-emerald-500 text-slate-950 shadow-md'
                  : 'bg-slate-800 text-slate-300'
              }`}
            >
              🌽 Maize (Corn) — Tasseling Stage
            </button>
          </div>

          {selectedCrop === 'rice' ? (
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-400">Crop / Variety:</span><span className="text-emerald-400 font-bold">Rice (Paddy) &bull; NDR-359 (HYV)</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Current Phenology:</span><span className="text-slate-200 font-semibold">Flowering / Anthesis (DAS 45, GDD 680)</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Thermal Tolerance:</span><span className="text-amber-400 font-mono">Critical High Tmax Threshold: 35.0 °C</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Soil Profile:</span><span className="text-slate-200">Alluvial Silt Loam (AWC: 145 mm/m)</span></div>
            </div>
          ) : (
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-400">Crop / Variety:</span><span className="text-amber-400 font-bold">Maize (Corn) &bull; HQPM-1</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Current Phenology:</span><span className="text-slate-200 font-semibold">Tasseling / Silking (DAS 38, GDD 590)</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Wind Lodging Threshold:</span><span className="text-sky-400 font-mono">Lodging Hazard Wind: 25.0 km/h</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Soil Profile:</span><span className="text-slate-200">Alluvial Silt Loam (AWC: 145 mm/m)</span></div>
            </div>
          )}
        </div>
      ),
    },
    {
      step: 5,
      title: 'Agricultural Risk Engine (Threshold Hazard Detection)',
      badge: 'Step 5: Risk Detection',
      description: 'Direction-aware threshold evaluation identifies crop-specific hazards without false alarms or missing data conversions.',
      details: (
        <div className="space-y-3">
          {selectedCrop === 'rice' ? (
            <div className="bg-slate-900 p-4 rounded-xl border border-red-500/40 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-rose-400 uppercase tracking-wider block">
                    THERMAL HAZARD &bull; RICE
                  </span>
                  <h4 className="text-base font-bold text-white">Flowering Spikelet Heat Stress</h4>
                </div>
                <RiskBadge severity="HIGH" score={0.82} showScore />
              </div>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                Downscaled maximum temperature (37.8°C) exceeds critical rice flowering threshold (35.0°C), inducing pollen sterility and spikelet abortion risk.
              </p>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="bg-slate-950 p-2 rounded border border-slate-800"><span className="text-slate-400 block">Observed Tmax:</span><span className="text-rose-400 font-bold">37.8 °C</span></div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800"><span className="text-slate-400 block">Stage Threshold:</span><span className="text-slate-300 font-bold">35.0 °C</span></div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 p-4 rounded-xl border border-amber-500/40 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block">
                    WIND HAZARD &bull; MAIZE
                  </span>
                  <h4 className="text-base font-bold text-white">High Wind Lodging & Stem Lodging Risk</h4>
                </div>
                <RiskBadge severity="MODERATE" score={0.55} showScore />
              </div>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                Forecast sustained wind speed (28.0 km/h) creates mechanical bending stress on tall standing maize during reproductive stage.
              </p>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div className="bg-slate-950 p-2 rounded border border-slate-800"><span className="text-slate-400 block">Observed Wind:</span><span className="text-sky-400 font-bold">28.0 km/h</span></div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800"><span className="text-slate-400 block">Lodging Threshold:</span><span className="text-slate-300 font-bold">25.0 km/h</span></div>
              </div>
            </div>
          )}
        </div>
      ),
    },
    {
      step: 6,
      title: 'Actionable Agro-Advisory & "Why This Advisory?" Provenance',
      badge: 'Step 6: Explainable Advisory',
      description: 'Generates structured farming actions with optimal operational timing windows, urgency ratings, and complete provenance traceability.',
      details: (
        <div className="space-y-4">
          {selectedCrop === 'rice' ? (
            <div className="bg-slate-900/90 rounded-xl p-5 border border-emerald-500/40 space-y-3 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-emerald-400 uppercase font-mono">WATER MANAGEMENT</span>
                  <span className="text-slate-500">&bull;</span>
                  <span className="text-xs text-slate-400">Rice &bull; Flowering Stage</span>
                </div>
                <PriorityBadge priority="HIGH" size="sm" />
              </div>

              <h4 className="text-base font-bold text-white leading-snug">
                Maintain Light Standing Water Layer to Buffer Canopy Heat
              </h4>

              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                Maintain 2-3 cm standing water in paddy fields to increase latent heat flux and lower canopy micro-climate temperature by 1.5 - 2.5°C during peak noon thermal hours.
              </p>

              <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">Optimal Window</span>
                    <span className="font-semibold text-slate-200">Early Morning (06:00 - 09:00 AM)</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">Urgency</span>
                    <span className="font-semibold text-emerald-300">IMMEDIATE</span>
                  </div>
                </div>
              </div>

              {/* Complete Provenance Chain Breakdown */}
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
                  Full Scientific Provenance Traceability
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Block Base:</span>
                    <span className="text-slate-200 font-bold">36.0 °C</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">1-km Downscaled:</span>
                    <span className="text-amber-400 font-bold">37.8 °C (+1.8°)</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Risk Rule:</span>
                    <span className="text-emerald-400 font-bold">agri_risk_v1.0</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Advisory Rule:</span>
                    <span className="text-emerald-400 font-bold">agri_advisory_v1.0</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/90 rounded-xl p-5 border border-sky-500/40 space-y-3 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-sky-400 uppercase font-mono">WEATHER PREPAREDNESS</span>
                  <span className="text-slate-500">&bull;</span>
                  <span className="text-xs text-slate-400">Maize &bull; Tasseling Stage</span>
                </div>
                <PriorityBadge priority="MEDIUM" size="sm" />
              </div>

              <h4 className="text-base font-bold text-white leading-snug">
                Withhold Field Irrigation Prior to High Wind Event
              </h4>

              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                Withhold deep field irrigation immediately prior to forecast high wind conditions (28 km/h), as saturated soil softens root anchoring and drastically increases mechanical crop lodging.
              </p>

              <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-sky-400 shrink-0" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">Optimal Window</span>
                    <span className="font-semibold text-slate-200">Before Forecast Wind Event</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase block">Urgency</span>
                    <span className="font-semibold text-sky-300">NEXT 24H</span>
                  </div>
                </div>
              </div>

              {/* Complete Provenance Chain Breakdown */}
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
                  Full Scientific Provenance Traceability
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Forecast Wind:</span>
                    <span className="text-sky-400 font-bold">28.0 km/h</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Threshold Limit:</span>
                    <span className="text-slate-300 font-bold">25.0 km/h</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Risk Rule:</span>
                    <span className="text-emerald-400 font-bold">agri_risk_v1.0</span>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                    <span className="text-slate-400 block text-[10px]">Advisory Rule:</span>
                    <span className="text-emerald-400 font-bold">agri_advisory_v1.0</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ),
    },
  ];

  const currentStepData = steps[currentStep - 1];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner */}
      <div className="glass-card rounded-2xl p-6 border border-emerald-500/50 shadow-2xl bg-gradient-to-r from-slate-900 via-emerald-950/30 to-slate-900">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-emerald-500 text-slate-950 uppercase tracking-wider">
                SIH JUDGE & EVALUATION MODE
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Canonical Demonstration Scenario
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Guided 60-Second Scientific Pipeline Walkthrough
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-3xl">
              Step through the complete data transformation from coarse Block NWP forecast down to 1-km ML temperature downscaling, Panchayat aggregation, crop stage sensitivity, and explainable farming advisories.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={runDemoPipeline}
              disabled={isRunningPipeline}
              className="px-4 py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-extrabold text-sm hover:bg-emerald-400 transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/30 cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-4 h-4 ${isRunningPipeline ? 'animate-spin' : ''}`} />
              <span>{isRunningPipeline ? 'Executing Pipeline...' : 'Run Live Demo Pipeline'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Live Pipeline Execution Progress Box */}
      {(isRunningPipeline || pipelineCompleted) && (
        <div className="bg-slate-900/90 rounded-2xl p-5 border border-emerald-500/40 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold font-mono text-emerald-400 uppercase tracking-wider">
              {pipelineCompleted ? 'Pipeline Execution Complete: All 6 Stages Verified' : 'Executing End-to-End Pipeline...'}
            </span>
            <span className="text-xs font-mono text-slate-400">{pipelineProgress}/6 Completed</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs">
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 1 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 1. Block Weather
            </div>
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 2 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 2. 1-km ML Grid
            </div>
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 3 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 3. Panchayat Agg.
            </div>
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 4 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 4. Crop Context
            </div>
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 5 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 5. Risk Evaluated
            </div>
            <div className={`p-2.5 rounded-lg border text-center font-mono ${pipelineProgress >= 6 ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300' : 'bg-slate-950/40 border-slate-800 text-slate-500'}`}>
              ✓ 6. Advisory Built
            </div>
          </div>
        </div>
      )}

      {/* Step Tabs Navigation */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {steps.map((s) => (
          <button
            key={s.step}
            onClick={() => setCurrentStep(s.step)}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              currentStep === s.step
                ? 'bg-emerald-950/60 border-emerald-500 text-white shadow-lg shadow-emerald-950/40 scale-[1.02]'
                : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono font-bold text-emerald-400">STAGE 0{s.step}</span>
              {currentStep > s.step && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
            </div>
            <span className="text-xs font-bold line-clamp-1 block text-slate-200">
              {s.title.split(':')[0]}
            </span>
          </button>
        ))}
      </div>

      {/* Main Active Stage Showcase Card */}
      <div className="glass-card rounded-2xl p-6 sm:p-8 border border-slate-700/80 shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-emerald-400 border border-slate-700 block w-fit mb-1">
              {currentStepData.badge}
            </span>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              {currentStepData.title}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentStep((prev) => Math.max(prev - 1, 1))}
              disabled={currentStep === 1}
              className="p-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentStep((prev) => Math.min(prev + 1, steps.length))}
              disabled={currentStep === steps.length}
              className="px-4 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs hover:bg-emerald-400 disabled:opacity-40 flex items-center gap-1.5 cursor-pointer"
            >
              <span>Next Stage</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed">
          {currentStepData.description}
        </p>

        {/* Step Interactive Details */}
        <div className="pt-2">
          {currentStepData.details}
        </div>
      </div>

      {/* Value Comparison Panel: "Why This Is Different" */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-slate-400 font-bold text-sm">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span>Conventional Regional Forecast Approach</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Standard systems publish a single coarse block forecast (e.g. 36.0°C). Farmers across diverse micro-climates receive generic weather information without knowing if their specific crop flowering stage will suffer floret sterility or heat shock.
          </p>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-400">
            Block NWP (~25km) &rarr; Generic Weather Bulletin &rarr; Uncalibrated Farmer Decisions
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6 border border-emerald-500/40 space-y-3 bg-emerald-950/10">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
            <Sparkles className="w-4 h-4" />
            <span>Our Localized Agro-Meteorological Intelligence Solution</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            We downscale temperature to a 1-km metric grid using XGBoost terrain residuals, intersect with Gram Panchayat GIS boundaries, and correlate with crop phenology (DAS/GDD) and soil water holding capacity to produce explainable, timed action guidance.
          </p>
          <div className="bg-slate-950/80 p-3 rounded-lg border border-emerald-500/30 text-xs font-mono text-emerald-300 font-bold">
            Block NWP &rarr; 1-km ML Downscaling &rarr; Panchayat Aggregation &rarr; Crop/Soil Stage &rarr; Risk Engine &rarr; Explainable Advisory
          </div>
        </div>
      </div>
    </div>
  );
};
