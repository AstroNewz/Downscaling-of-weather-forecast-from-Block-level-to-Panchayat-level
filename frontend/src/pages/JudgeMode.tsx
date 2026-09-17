import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { 
  Award, 
  ChevronRight, 
  ChevronLeft, 
  RotateCcw, 
  Play, 
  Pause, 
  X, 
  ShieldCheck, 
  Cpu, 
  Database, 
  MapPin, 
  Sparkles, 
  CheckCircle2, 
  Layers, 
  Sprout, 
  FileText 
} from 'lucide-react';

interface PresentationStep {
  step: number;
  title: string;
  subtitle: string;
  category: string;
  icon: any;
  content: string;
  bullets: string[];
  certifiedEvidence: string;
}

export const JudgeMode: React.FC = () => {
  const navigate = useNavigate();
  const { selectedPanchayat } = useApp();

  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const timerRef = useRef<any>(null);

  const presentationSteps: PresentationStep[] = [
    {
      step: 1,
      title: 'SIH Problem Statement 26074 Overview',
      subtitle: 'Downscaling of Weather Forecast from Block Level to Panchayat Level',
      category: 'Mission & Scope',
      icon: Award,
      content:
        'Bridging the 25-km regional NWP grid resolution gap to deliver actionable 1-km micro-climate agro-meteorological advisories directly to gram panchayats.',
      bullets: [
        'Problem Statement: Downscaling of Weather Forecast from Block Level to Panchayat Level for Agro-Meteorological Advisory Services',
        'Target beneficiaries: Gram panchayat farmers and block agricultural officers',
        'Core innovation: Deterministic physics-informed spatial downscaling + 100% explainable agronomic rule engine',
      ],
      certifiedEvidence: 'Problem Statement 26074 Verified Candidate',
    },
    {
      step: 2,
      title: 'Empirical Dataset Authenticity & Provenance',
      subtitle: '23,949 Genuine Synoptic Observations',
      category: 'Data Provenance',
      icon: Database,
      content:
        'Rigorous empirical validation conducted on genuine IMD synoptic ground stations without synthetic fabrication or data leakage.',
      bullets: [
        '23,949 genuine meteorological observation records',
        '17 WMO synoptic stations across India',
        '11 States/UTs representing 6 diverse physiographic regimes',
        'Zero temporal leakage: strict train/validation splits across Kharif season',
      ],
      certifiedEvidence: '23,949 Genuine Synoptic Observations • 0.00% Leakage',
    },
    {
      step: 3,
      title: 'Regional NWP Spatial Resolution Deficit',
      subtitle: 'The 25-km Coarse Resolution Challenge',
      category: 'Scientific Challenge',
      icon: Layers,
      content:
        'Regional numerical models (ERA5 / IMD GFS) average across ~625 km² cells, concealing local micro-climatic thermal extremes critical to crop health.',
      bullets: [
        'Regional grid size: ~25 km x 25 km (~62,500 hectares per cell)',
        'Local micro-topography, elevation variation, and water bodies are smoothed out',
        'Consequence: Farmers receive generic block averages that fail during localized heat or wind shocks',
      ],
      certifiedEvidence: 'Baseline NWP Uncalibrated RMSE: 3.9782°C',
    },
    {
      step: 4,
      title: 'Certified Production Baseline Model',
      subtitle: 'T_calibrated = T_coarse + 0.7351°C',
      category: 'Production Baseline',
      icon: ShieldCheck,
      content:
        'Deterministic scalar residual calibration certified under Phase 24 as the sole active production downscaling engine.',
      bullets: [
        'Certified Production Parameter: B = +0.7351°C (exact precision required)',
        'Validation RMSE: 3.9097°C (statistically superior to raw coarse baseline)',
        '100% reproducible, physically bounded, and zero danger of out-of-distribution catastrophic failures',
      ],
      certifiedEvidence: 'T_calibrated = T_coarse + 0.7351°C • Certified Production',
    },
    {
      step: 5,
      title: 'Challenger Model: XGBoost (RESEARCH_ONLY)',
      subtitle: 'Scientific Integrity & Safe Model Governance',
      category: 'Scientific Model Governance',
      icon: Cpu,
      content:
        'Experimental gradient boosting decision tree challenger model rigorously benchmarked but restricted from production due to non-stationarity. RETAINED FOR RESEARCH and benchmarking purposes only.',
      bullets: [
        'Strictly designated as RESEARCH_ONLY across all systems; RETAINED FOR RESEARCH evaluation',
        'Demonstrates instability and risk of overfitting under extreme drought stress conditions',
        'Showcases true scientific maturity: SIH judges value honest safety audits over blind ML promotion',
      ],
      certifiedEvidence: 'XGBoost: RESEARCH_ONLY • Strict Guardrails Active • RETAINED FOR RESEARCH',
    },
    {
      step: 6,
      title: 'Geospatial Area Conservation Standards',
      subtitle: 'Dynamic Local UTM (EPSG:32644) Metric Integrity',
      category: 'Geospatial Topology',
      icon: MapPin,
      content:
        'Rigorous geospatial projection protocol ensuring exact physical metric area calculations without planar distortions.',
      bullets: [
        'Dynamic UTM Zone 44N (EPSG:32644) used for all area-weighted polygon intersections and cropland hectares',
        'Web Mercator (EPSG:3857) restricted strictly to screen visual rendering',
        'Preserves exact physical land-use geometry across complex panchayat borders',
      ],
      certifiedEvidence: 'EPSG:32644 Metric Projection Verified',
    },
    {
      step: 7,
      title: '1-km Micro-Grid Field Topology',
      subtitle: 'High-Resolution 1000m x 1000m Cell Matrix',
      category: 'Micro-Climate Grid',
      icon: Layers,
      content:
        'Panchayats subdivided into 1-km physical micro-cells integrating local elevation, aspect, and cropland fractions.',
      bullets: [
        'Every cell receives calibrated downscaled thermal and atmospheric projections',
        'Interactive cell inspector reveals elevation and local micro-climate deltas',
        'Empowers field-level cluster zoning for targeted farm extension services',
      ],
      certifiedEvidence: '1-km Micro-Grid Resolution Active',
    },
    {
      step: 8,
      title: 'Crop Phenology & Vulnerability Context',
      subtitle: 'Kharif 2024 Pilot Framework in Dhar',
      category: 'Agronomic Intelligence',
      icon: Sprout,
      content:
        'Downscaled meteorological signals contextualized with crop species, phenological stage, days after sowing (DAS), and soil moisture capacity.',
      bullets: [
        'Primary pilot crops: Cotton, Soybean, Wheat (Vertisol / Black Cotton Soil)',
        'Stage-dependent vulnerability matrix (Germination, Vegetative, Flowering, Pod Development)',
        'Ensures advisories correspond to biological vulnerability windows rather than raw numbers alone',
      ],
      certifiedEvidence: 'Crop Context Framework • Kharif 2024',
    },
    {
      step: 9,
      title: 'Biophysical Risk Detection & Thresholds',
      subtitle: 'Automated Multi-Hazard Identification',
      category: 'Risk Engine',
      icon: Award,
      content:
        'Deterministic comparison of downscaled micro-climate forecasts against empirical agronomic stress thresholds.',
      bullets: [
        'Extreme Heat Stress: Tmax >= 38.0°C during reproductive phase triggers flower drop alert',
        'Wind Lodging: Wind speed >= 35 km/h triggers spray postponement and physical staking alert',
        'Moisture Deficit: Consecutive dry days + elevated VPD triggers pulse irrigation advisory',
      ],
      certifiedEvidence: 'Empirical Biophysical Thresholds Verified',
    },
    {
      step: 10,
      title: 'Deterministic 5-Step Explainability Trace',
      subtitle: 'Zero-Hallucination Decision Provenance',
      category: 'Explainable AI',
      icon: FileText,
      content:
        'Every single advisory is backed by an auditable 5-step deterministic reasoning trace that farmers and officers can inspect and trust.',
      bullets: [
        'Step 1: 1-km Calibrated Weather Signal (+0.7351°C)',
        'Step 2: Crop Phenological Stage & Vulnerability',
        'Step 3: Agronomic Biophysical Threshold Check',
        'Step 4: Hazard Identification & Priority Assignment',
        'Step 5: Actionable Mitigation Directive with Operational Execution Window',
      ],
      certifiedEvidence: '5-Step Explainability Trace • Zero LLM Hallucination',
    },
    {
      step: 11,
      title: 'Actionable Farm-Level Advisories',
      subtitle: 'Targeted Guidance with Optimal Operational Windows',
      category: 'Field Impact',
      icon: CheckCircle2,
      content:
        'Clear, concise, high-priority agronomic instructions tailored to protect farmer yield and optimize input resources.',
      bullets: [
        'Prioritized action categories (Heat Stress, Irrigation, Wind, Pest/Disease)',
        'Specific execution windows (e.g. "Apply light sprinkler pulse between 05:00 - 08:00 AM")',
        'Eliminates generic advice by integrating local soil and canopy physics',
      ],
      certifiedEvidence: 'Targeted Operational Execution Windows',
    },
    {
      step: 12,
      title: 'Phase 24 Production Certification & Release Freeze',
      subtitle: 'System Ready for Live Smart India Hackathon Demonstration',
      category: 'Release Freeze',
      icon: Sparkles,
      content:
        'Complete end-to-end audit passed with 50/50 automated tests, zero leakage, certified baseline integrity, and frozen release state.',
      bullets: [
        'FastAPI backend + React/Vite command-center frontend fully verified',
        'T_calibrated = T_coarse + 0.7351°C strictly enforced across all components',
        'XGBoost maintained as RESEARCH_ONLY',
        'Ready for comprehensive judge evaluation across all 6 user journeys',
      ],
      certifiedEvidence: 'PRODUCTION_BASELINE_CERTIFIED = YES • Phase 24 Release Freeze',
    },
  ];

  const current = presentationSteps[currentStepIndex];

  // Auto-play interval management
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= presentationSteps.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 5000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, presentationSteps.length]);

  const handleNext = () => {
    if (currentStepIndex < presentationSteps.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  };

  const handleRestart = () => {
    setCurrentStepIndex(0);
    setIsPlaying(false);
  };

  const handleExit = () => {
    setIsPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);
    navigate('/');
  };

  const StepIcon = current.icon;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Top Banner & Exit */}
      <div className="flex flex-wrap items-center justify-between gap-4 glass-panel p-4 rounded-xl border border-slate-800 bg-[#090e1a]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white">
                SIH Problem Statement 26074 • 12-Step Judge Presentation
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 border border-amber-500/40 text-amber-300 font-bold">
                Judge Mode
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Step {current.step} of 12 • {current.category}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Restart */}
          <button
            id="judge-restart-btn"
            onClick={handleRestart}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white"
            title="Restart Presentation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Autoplay toggle */}
          <button
            id="judge-autoplay-btn"
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              isPlaying
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-white'
            }`}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? 'Pause Auto' : 'Auto Play'}</span>
          </button>

          {/* Exit */}
          <button
            id="judge-exit-btn"
            onClick={handleExit}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
          >
            <X className="w-4 h-4" />
            <span>Exit</span>
          </button>
        </div>
      </div>

      {/* 12-Step Progress Stepper */}
      <div className="grid grid-cols-6 sm:grid-cols-12 gap-1.5">
        {presentationSteps.map((s, idx) => (
          <button
            key={s.step}
            onClick={() => {
              setCurrentStepIndex(idx);
              setIsPlaying(false);
            }}
            className={`h-2 rounded-full transition-all ${
              idx === currentStepIndex
                ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.6)]'
                : idx < currentStepIndex
                ? 'bg-emerald-500/70'
                : 'bg-slate-800'
            }`}
            title={`Step ${s.step}: ${s.title}`}
          />
        ))}
      </div>

      {/* Active Presentation Card */}
      <div className="glass-panel p-8 rounded-2xl border border-slate-700 bg-gradient-to-b from-[#0e1628] to-[#090e1a] shadow-2xl space-y-6">
        {/* Step Header */}
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
              Stage {current.step} / 12 • {current.category}
            </span>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              {current.title}
            </h2>
            <p className="text-sm text-slate-300 font-medium">
              {current.subtitle}
            </p>
          </div>

          <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <StepIcon className="w-8 h-8" />
          </div>
        </div>

        {/* Narrative & Explanation */}
        <p className="text-sm text-slate-300 leading-relaxed font-sans">
          {current.content}
        </p>

        {/* Bullet Verification Points */}
        <div className="space-y-2.5 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            SIH Evaluation Deliverables:
          </span>
          <ul className="space-y-2 text-xs text-slate-200">
            {current.bullets.map((bullet, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span className="leading-normal">{bullet}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Certified Ground Truth Banner */}
        <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2 text-emerald-300 font-bold">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Certified Evidence:</span>
          </div>
          <span className="text-emerald-400">{current.certifiedEvidence}</span>
        </div>

        {/* Navigation Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            id="judge-prev-btn"
            onClick={handlePrev}
            disabled={currentStepIndex === 0}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium border transition-colors ${
              currentStepIndex === 0
                ? 'bg-slate-900/40 text-slate-600 border-slate-800/40 cursor-not-allowed'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous Stage</span>
          </button>

          {currentStepIndex === 0 && (
            <button
              id="judge-start-btn"
              onClick={handleNext}
              className="px-6 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all"
            >
              Start Walkthrough
            </button>
          )}

          {currentStepIndex > 0 && currentStepIndex < presentationSteps.length - 1 && (
            <button
              id="judge-next-btn"
              onClick={handleNext}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all"
            >
              <span>Next Stage</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          )}

          {currentStepIndex === presentationSteps.length - 1 && (
            <button
              id="judge-finish-btn"
              onClick={handleExit}
              className="flex items-center gap-1.5 px-6 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all"
            >
              <span>Finish Presentation</span>
              <CheckCircle2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
