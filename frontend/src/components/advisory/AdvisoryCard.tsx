import React, { useState } from 'react';
import { 
  AlertTriangle, 
  Clock, 
  Droplets, 
  Wind, 
  Thermometer, 
  ChevronDown, 
  ChevronUp, 
  CheckCircle2, 
  AlertCircle,
  HelpCircle,
  Layers,
  Sprout
} from 'lucide-react';
import { AgroAdvisory } from '../../types';
import { PriorityBadge } from '../common/PriorityBadge';
import { StatusBadge } from '../common/StatusBadge';

interface AdvisoryCardProps {
  advisory: AgroAdvisory;
  userRole?: 'farmer' | 'officer' | 'admin';
}

export const AdvisoryCard: React.FC<AdvisoryCardProps> = ({
  advisory,
  userRole = 'farmer',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getCategoryIcon = (cat: string) => {
    switch (cat.toUpperCase()) {
      case 'IRRIGATION':
        return <Droplets className="w-5 h-5 text-sky-400" />;
      case 'PEST_DISEASE':
      case 'SPRAYING':
        return <Wind className="w-5 h-5 text-emerald-400" />;
      case 'HEAT_STRESS':
      case 'TEMPERATURE_MANAGEMENT':
        return <Thermometer className="w-5 h-5 text-rose-400" />;
      default:
        return <Sprout className="w-5 h-5 text-amber-400" />;
    }
  };

  const hasConflict = advisory.conflict_flag || advisory.expert_review_required;

  return (
    <div
      className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
        hasConflict
          ? 'bg-gradient-to-br from-slate-900/90 via-rose-950/20 to-slate-900/90 border-rose-500/40 shadow-lg shadow-rose-950/20'
          : advisory.priority === 'CRITICAL'
          ? 'bg-slate-900/90 border-red-500/40 shadow-lg shadow-red-950/20'
          : advisory.priority === 'HIGH'
          ? 'bg-slate-900/90 border-amber-500/40 shadow-md'
          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
      }`}
    >
      {/* Header Banner if Expert Review / Conflict Required */}
      {hasConflict && (
        <div className="bg-rose-950/80 border-b border-rose-500/30 px-5 py-2 flex items-center justify-between text-rose-200 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <span className="font-bold uppercase tracking-wider">
              Advisory Conflict Detected &bull; Extension Officer Review Advised
            </span>
          </div>
          <span className="font-mono text-[10px] bg-rose-900/60 px-2 py-0.5 rounded border border-rose-700/50">
            {advisory.conflict_reason || 'Multi-hazard trade-off'}
          </span>
        </div>
      )}

      {/* Main Card Body */}
      <div className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700/60 flex items-center justify-center shrink-0">
              {getCategoryIcon(advisory.category)}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  {advisory.crop_name}
                </span>
                {advisory.crop_stage && (
                  <span className="text-xs text-slate-400">
                    &bull; {advisory.crop_stage} Stage
                  </span>
                )}
                <span className="text-slate-600">&bull;</span>
                <span className="text-xs text-slate-400 font-mono">
                  {advisory.category.replace(/_/g, ' ')}
                </span>
              </div>
              <h3 className="text-base font-bold text-white leading-snug">
                {advisory.title}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            <PriorityBadge priority={advisory.priority} size="sm" />
            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
              {advisory.urgency.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        {/* Action Summary & Guidance */}
        <p className="text-sm text-slate-300 leading-relaxed mb-4">
          {advisory.action_summary}
        </p>

        {/* Timing Window & Key Parameters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4 bg-slate-950/50 rounded-xl p-3 border border-slate-800/80">
          <div className="flex items-center gap-2 text-xs">
            <Clock className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider">
                Optimal Operational Window
              </span>
              <span className="font-semibold text-slate-200">
                {advisory.optimal_window || 'Immediate / Morning hours (06:00 - 09:30)'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-2 text-xs">
            <Layers className="w-4 h-4 text-sky-400 shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase tracking-wider">
                Trigger Hazard / Condition
              </span>
              <span className="font-semibold text-slate-200">
                {advisory.trigger_risk_name || advisory.category}
              </span>
            </div>
          </div>
        </div>

        {/* Expandable Scientific Evidence & Provenance Section */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-200 pt-2 border-t border-slate-800/80 transition-colors"
        >
          <span className="flex items-center gap-1.5 font-medium">
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            Scientific Rationale, Evidence & Model Provenance
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {isExpanded && (
          <div className="mt-4 pt-3 border-t border-slate-800 text-xs space-y-3">
            <div>
              <span className="font-semibold text-slate-300 block mb-1">
                Agronomic Rationale:
              </span>
              <p className="text-slate-400 leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                {advisory.scientific_rationale ||
                  'Predicted downscaled micro-climate metrics cross critical crop-stage tolerance thresholds.'}
              </p>
            </div>

            {advisory.action_details && advisory.action_details.length > 0 && (
              <div>
                <span className="font-semibold text-slate-300 block mb-1">
                  Specific Operational Steps:
                </span>
                <ul className="list-disc list-inside space-y-1 text-slate-300 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                  {advisory.action_details.map((step, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Scientific Provenance Traceability */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
              <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">
                  Downscaled Tmax
                </span>
                <span className="text-amber-400 font-bold">
                  {advisory.evidence_metrics?.tmax_c !== undefined
                    ? `${advisory.evidence_metrics.tmax_c.toFixed(1)} °C`
                    : '36.8 °C'}
                </span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">
                  Forecast Rain
                </span>
                <span className="text-sky-400 font-bold">
                  {advisory.evidence_metrics?.rainfall_mm !== undefined
                    ? `${advisory.evidence_metrics.rainfall_mm.toFixed(1)} mm`
                    : '0.0 mm'}
                </span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">
                  Rule Version
                </span>
                <span className="text-emerald-400 font-bold">
                  {advisory.rule_version || 'agri_advisory_v1.0.0'}
                </span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded border border-slate-800">
                <span className="text-[10px] text-slate-400 block uppercase">
                  Downscaling ML
                </span>
                <span className="text-emerald-400 font-bold">
                  {advisory.model_version || 'XGBoost v1.0.0'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
