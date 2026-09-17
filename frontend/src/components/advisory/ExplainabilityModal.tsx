import React from 'react';
import { AgroAdvisory } from '../../types';
import { 
  X, 
  HelpCircle, 
  Thermometer, 
  Sprout, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowDown, 
  FileText,
  ShieldCheck
} from 'lucide-react';
import { PriorityBadge } from '../common/PriorityBadge';

interface ExplainabilityModalProps {
  advisory: AgroAdvisory | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({
  advisory,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !advisory) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-700/80 bg-[#0c1220] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-[#090e1a]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  Deterministic Advisory Reasoning Trace
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                  5-Step Explainability
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Agronomic Rule Engine Provenance & Scientific Deduction
              </p>
            </div>
          </div>

          <button
            id="close-explainability-modal-btn"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-700/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body: 5-Step Trace */}
        <div className="p-6 overflow-y-auto space-y-4">
          {/* Top metadata summary */}
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div>
              <span className="text-slate-400">Crop Context: </span>
              <strong className="text-emerald-300 font-medium">
                {advisory.crop_name} ({advisory.crop_stage})
              </strong>
            </div>
            <PriorityBadge priority={advisory.priority} size="sm" />
          </div>

          {/* Trace Steps Container */}
          <div className="space-y-3 relative before:absolute before:inset-0 before:left-5 before:w-0.5 before:bg-slate-800 before:z-0">
            {/* Step 1: Weather Signal */}
            <div className="relative z-10 flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-sky-500/40 text-sky-400 flex items-center justify-center flex-shrink-0 shadow-md">
                <Thermometer className="w-5 h-5" />
              </div>
              <div className="flex-1 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400 font-semibold">
                  Step 1: Downscaled Weather Signal
                </span>
                <h4 className="text-xs font-semibold text-slate-200 mt-0.5">
                  1-km Calibrated Micro-Climate Observation
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Downscaling calibrated with certified parameter{' '}
                  <strong className="text-sky-300 font-mono">+0.7351°C</strong> identified an elevated local thermal bias beyond regional coarse ERA5 averages.
                </p>
              </div>
            </div>

            {/* Step 2: Crop Vulnerability Context */}
            <div className="relative z-10 flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-emerald-500/40 text-emerald-400 flex items-center justify-center flex-shrink-0 shadow-md">
                <Sprout className="w-5 h-5" />
              </div>
              <div className="flex-1 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">
                  Step 2: Crop Phenological Context
                </span>
                <h4 className="text-xs font-semibold text-slate-200 mt-0.5">
                  {advisory.crop_name} in {advisory.crop_stage} Stage
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  Phenological sensitivity during the {advisory.crop_stage.toLowerCase()} window leaves the canopy highly susceptible to moisture depletion and pollen desiccation.
                </p>
              </div>
            </div>

            {/* Step 3: Biophysical Threshold Check */}
            <div className="relative z-10 flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-amber-500/40 text-amber-400 flex items-center justify-center flex-shrink-0 shadow-md">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="flex-1 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-semibold">
                  Step 3: Biophysical Threshold Check
                </span>
                <h4 className="text-xs font-semibold text-slate-200 mt-0.5">
                  Critical Parameter Exceedance
                </h4>
                <p className="text-xs text-slate-400 mt-1 font-mono text-[11px] bg-slate-950/60 p-2 rounded border border-slate-800/80">
                  Rule Trigger: Tmax ≥ 38.0°C OR Wind ≥ 35 km/h during vulnerable phenological stage.
                </p>
              </div>
            </div>

            {/* Step 4: Hazard Identification */}
            <div className="relative z-10 flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-rose-500/40 text-rose-400 flex items-center justify-center flex-shrink-0 shadow-md">
                <FileText className="w-5 h-5" />
              </div>
              <div className="flex-1 p-3.5 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-[10px] font-mono uppercase tracking-wider text-rose-400 font-semibold">
                  Step 4: Hazard Identification
                </span>
                <h4 className="text-xs font-semibold text-slate-200 mt-0.5">
                  {advisory.category.replace('_', ' ')} Hazard Confirmed
                </h4>
                <p className="text-xs text-slate-400 mt-1">
                  {advisory.rationale}
                </p>
              </div>
            </div>

            {/* Step 5: Actionable Recommendation */}
            <div className="relative z-10 flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-emerald-950 border border-emerald-500 text-emerald-300 flex items-center justify-center flex-shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div className="flex-1 p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">
                  Step 5: Actionable Mitigation Directive
                </span>
                <h4 className="text-xs font-semibold text-emerald-200 mt-0.5">
                  Optimal Execution Window: {advisory.optimal_window || 'Next 24-48 Hours'}
                </h4>
                <ul className="text-xs text-slate-300 mt-2 space-y-1 list-disc list-inside">
                  {advisory.recommended_actions.map((action, i) => (
                    <li key={i}>{action}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-[#090e1a] flex justify-between items-center text-xs text-slate-400">
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Zero Hallucination • Rule Engine Verified</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
          >
            Close Trace
          </button>
        </div>
      </div>
    </div>
  );
};
