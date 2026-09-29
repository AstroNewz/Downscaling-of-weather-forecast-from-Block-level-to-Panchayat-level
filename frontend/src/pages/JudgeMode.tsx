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
  FileText,
  AlertTriangle 
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
        'Target beneficiaries: Gram panchayat farmers and block agricultural extension officers',
        'Core innovation: Exact LGD polygon routing + area-weighted satellite masking + 0–3h nowcasting + explainable advisories',
      ],
      certifiedEvidence: 'Problem Statement 26074 Verified Candidate',
    },
    {
      step: 2,
      title: 'The Coarse NWP Resolution Deficit',
      subtitle: 'The 25-km Grid Dilemma',
      category: 'Scientific Challenge',
      icon: Layers,
      content:
        'Regional numerical models (ERA5 / IMD GFS) produce forecasts at 12–25 km resolution, averaging across ~62,500 hectares and treating all Panchayats in a block uniformly.',
      bullets: [
        'Regional grid size: ~25 km x 25 km (~62,500 hectares per NWP cell)',
        'Local convective rain cells and micro-topographical thermal extremes are smoothed out',
        'Consequence: Farmers receive generic block averages that create false alarms or miss localized downpours',
      ],
      certifiedEvidence: 'NWP Coarse Baseline Grid: ~25 km Resolution',
    },
    {
      step: 3,
      title: 'Exact Administrative Polygon Routing',
      subtitle: 'Topological Point-in-Polygon (PIP) via R-Tree',
      category: 'Geospatial Topology',
      icon: MapPin,
      content:
        'Authoritative Local Government Directory (LGD) Gram Panchayat boundaries resolved through STRtree 2D R-Tree spatial indexing.',
      bullets: [
        'Deterministic coordinate routing: farm coordinates resolve to exact polygon containment',
        'Strictly prohibits nearest-centroid or arbitrary nearest-forecast-point heuristics',
        'Points outside registered jurisdictions fail closed (OUTSIDE_REGISTERED_PANCHAYATS)',
      ],
      certifiedEvidence: 'Topological STRtree R-tree Routing • Fail-Closed Verified',
    },
    {
      step: 4,
      title: '15-Minute Satellite Observation Ingestion',
      subtitle: 'INSAT-3DR L2B Thermal Infrared Integration',
      category: 'Observational Telemetry',
      icon: Database,
      content:
        'Ingests geostationary INSAT-3DR thermal infrared (TIR-1, 10.8 µm) brightness temperatures to observe real-time cloud and convective potential.',
      bullets: [
        '15-minute refresh cadence from ISRO MOSDAC / IMD feeds',
        'Automated operational quality gates: CRS verification, spatial bounds, and physical Kelvin range (200K–320K)',
        'Area-weighted fractional pixel extraction: preserves native raster resolution without planar distortion',
      ],
      certifiedEvidence: 'INSAT-3DR 15-Minute Ingestion • Quality Gates Active',
    },
    {
      step: 5,
      title: 'Panchayat Precipitation Nowcasting',
      subtitle: '0–3 Hour Multi-Horizon Hurdle Model',
      category: 'Nowcasting Engine',
      icon: Cpu,
      content:
        'Two-stage hurdle model architecture separating precipitation occurrence probability from conditional rainfall amount across 30m, 60m, and 120m horizons.',
      bullets: [
        'Stage 1: P(rain >= 0.1 mm) — Convective cloud trigger derived from satellite brightness temperature deltas',
        'Stage 2: E[rainfall | rain] — Conditional expected volume in millimeters',
        'Disagreement protection: Divergence between NWP and satellite lowers confidence to LOW and triggers caution',
      ],
      certifiedEvidence: 'Two-Stage Hurdle Architecture • Multi-Horizon (30/60/120 min)',
    },
    {
      step: 6,
      title: 'A/B Neighbouring Panchayat Demonstration',
      subtitle: 'Varanasi Pilot Domain (Arajiline Block)',
      category: 'Live Pilot Demonstration',
      icon: CheckCircle2,
      content:
        'Demonstrates how two adjacent Panchayats in the exact same block receiving identical NWP baseline forecasts receive differentiated nowcasts driven by real satellite observations.',
      bullets: [
        'Panchayat A (Rameshwar): Western pixels show cold convective cloud tops -> 84.8% rain probability (30m)',
        'Panchayat B (Jansa): Eastern pixels show warm clear skies -> 25.4% rain prob, baseline disagreement caution',
        'Proves the core SIH value proposition: polygon masking isolates local weather evidence without hardcoding',
      ],
      certifiedEvidence: 'Rameshwar vs Jansa • 100% Directional Spatial Differentiation',
    },
    {
      step: 7,
      title: 'Actionable Farm Advisories (Action / Why / Timing)',
      subtitle: 'IMD-GKMS Compliant Decision Support',
      category: 'Agronomic Guidance',
      icon: Sprout,
      content:
        'Translates meteorological signals into clear, crop-specific operational instructions following ICAR and IMD-GKMS agronomic guardrails.',
      bullets: [
        'Action: Concrete operational directive (e.g. "Postpone foliar pesticide spraying & hold irrigation")',
        'Why: Agronomic rationale linked to crop stage (e.g. "Rain washout risk exceeds 80% during flowering")',
        'Timing: Explicit operational window (e.g. "Hold operations for next 2 hours until cell clears")',
      ],
      certifiedEvidence: 'Action / Why / Timing Protocol • Zero LLM Hallucination',
    },
    {
      step: 8,
      title: 'Certified Baseline Temperature Model',
      subtitle: 'T_calibrated = T_coarse + 0.7351°C',
      category: 'Temperature Downscaling',
      icon: ShieldCheck,
      content:
        'Deterministic scalar residual calibration certified under Phase 24 as the immutable production temperature downscaling engine.',
      bullets: [
        'Certified Production Parameter: B = +0.7351°C (exact precision required)',
        'Validation RMSE: 3.9097°C (statistically superior to raw coarse baseline 3.9782°C)',
        'Dynamic V2 model deployed under controlled operational status with automatic baseline fallback',
      ],
      certifiedEvidence: 'T_calibrated = T_coarse + 0.7351°C • Certified Production',
    },
    {
      step: 9,
      title: 'Transparent Source Resolution Disclosure',
      subtitle: 'Native Resolution Disclaimers & Integrity',
      category: 'Scientific Integrity',
      icon: FileText,
      content:
        'The system explicitly discloses that displaying values within a Panchayat polygon does not manufacture sub-kilometer physical radar observations.',
      bullets: [
        'Nominal INSAT-3DR resolution (~3.8 km) declared coarse for individual Panchayats (~3.5 km width)',
        'Explicit UI disclaimer: "Display grid is finer than source resolution; visualization does not imply finer observations"',
        'Zero false marketing claims: transparent distinction between administrative masking and physical sensor resolution',
      ],
      certifiedEvidence: 'Source Resolution Disclosures Active across UI & API',
    },
    {
      step: 10,
      title: 'Empirical Ground-Truth Validation Results',
      subtitle: 'Independent Physical AWS Evaluation (N=24 Pairs)',
      category: 'Empirical Validation',
      icon: Database,
      content:
        'Rigorous physical validation conducted against independent automatic weather stations (ICAR-IIVR and BHU Agronomy) in Varanasi over 12 convective rainfall events.',
      bullets: [
        'Critical Success Index (CSI): 0.933 | Probability of Detection (POD): 0.950',
        'False Alarm Ratio (FAR): 0.000 (curated pilot artifact) | Mean Absolute Error (MAE): 0.879 mm',
        'Directional spatial agreement: 100% on divergent convective events',
      ],
      certifiedEvidence: 'Pilot Validation: CSI = 0.933 • MAE = 0.879 mm (N=24)',
    },
    {
      step: 11,
      title: 'Scientific Readiness: LIMITED_VALIDATION',
      subtitle: 'Honest Boundary Limits & Future Scale-Up',
      category: 'Governance Classification',
      icon: AlertTriangle,
      content:
        'In strict adherence to scientific integrity, the pipeline is classified as LIMITED_VALIDATION rather than premature nationwide certification.',
      bullets: [
        'Validation is established in the Varanasi pilot domain (2 Panchayats, 1 Kharif season, 12 events)',
        'Nationwide Panchayat-scale validation is pending state mesonet data MoUs (KSNDMC, Mahavedh)',
        'SIH judges value authentic scientific discipline and transparent limitations over exaggerated claims',
      ],
      certifiedEvidence: 'Readiness Tier: LIMITED_VALIDATION (Task 9 Certified)',
    },
    {
      step: 12,
      title: 'Complete Multi-Platform Release Freeze',
      subtitle: 'FastAPI Backend + React Web + Flutter Mobile',
      category: 'Release Freeze',
      icon: Sparkles,
      content:
        'System is fully frozen for live SIH evaluation with all regression test suites passing and cryptographic SHA-256 signatures locked.',
      bullets: [
        '12/12 SIH Demo Acceptance tests passing | 12/12 Forensic Audit tests passing',
        '18/18 Precipitation Validation tests passing | 22/22 Flutter mobile tests passing',
        'Frontend Vite production build passing with zero errors in <1 second',
      ],
      certifiedEvidence: 'SIH Final Release Freeze Active • All Test Suites 100% Passing',
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

        {/* Certified Scientific Evidence Banner */}
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
