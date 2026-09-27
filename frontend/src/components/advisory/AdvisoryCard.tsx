import React, { useState } from 'react';
import { AgroAdvisory } from '../../types';
import { PriorityBadge } from '../common/PriorityBadge';
import { ExplainabilityModal } from './ExplainabilityModal';
import { 
  Clock, 
  HelpCircle, 
  CheckCircle, 
  AlertCircle, 
  Sprout, 
  ShieldAlert, 
  ArrowRight,
  CloudRain
} from 'lucide-react';

interface AdvisoryCardProps {
  advisory: AgroAdvisory;
  className?: string;
}

export const AdvisoryCard: React.FC<AdvisoryCardProps> = ({
  advisory,
  className = '',
}) => {
  const [showModal, setShowModal] = useState(false);

  const priorityStyles = {
    CRITICAL: 'border-rose-500/40 bg-rose-950/10 hover:border-rose-500/60',
    HIGH: 'border-amber-500/40 bg-amber-950/10 hover:border-amber-500/60',
    MEDIUM: 'border-sky-500/30 bg-sky-950/10 hover:border-sky-500/50',
    LOW: 'border-slate-800 bg-slate-900/30 hover:border-slate-700',
  }[advisory.priority || 'LOW'];

  return (
    <>
      <div
        className={`glass-panel p-5 rounded-xl border transition-all duration-200 flex flex-col justify-between ${priorityStyles} ${className}`}
      >
        <div>
          {/* Top Row: Crop info and Priority badge */}
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-500/15 text-emerald-400">
                <Sprout className="w-4 h-4" />
              </span>
              <div>
                <span className="text-xs font-bold text-slate-200">
                  {advisory.crop_name}
                </span>
                <span className="text-xs text-slate-400 ml-1.5 font-medium">
                  • {advisory.crop_stage}
                </span>
              </div>
            </div>

            <PriorityBadge priority={advisory.priority} size="sm" />
          </div>

          {/* Title & Headline */}
          <h4 className="text-sm font-bold text-white mb-2 leading-snug">
            {advisory.headline || advisory.title}
          </h4>

          {/* Rationale */}
          <p className="text-xs text-slate-300 mb-3.5 leading-relaxed">
            {advisory.rationale}
          </p>

          {/* Action List */}
          {advisory.recommended_actions && advisory.recommended_actions.length > 0 && (
            <div className="space-y-1.5 mb-4">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Directives:
              </span>
              <ul className="space-y-1">
                {advisory.recommended_actions.slice(0, 3).map((act, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{act}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Localized Precipitation Evidence Context (Task 5 / Task 6 Integration) */}
          {advisory.localized_nowcast_context && (
            <div className="my-2.5 p-2.5 rounded-lg bg-blue-950/20 border border-blue-500/30 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-blue-300 flex items-center gap-1.5 text-[11px]">
                  <CloudRain className="w-3.5 h-3.5 text-blue-400" />
                  Localized Nowcast Evidence ({advisory.localized_nowcast_context.horizon_minutes}m)
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-900/40 text-blue-300 border border-blue-700/50">
                  Confidence: {advisory.localized_nowcast_context.confidence}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 flex items-center justify-between font-mono">
                <span>
                  Rain risk: {Math.round(advisory.localized_nowcast_context.rain_probability * 100)}%
                  {advisory.localized_nowcast_context.expected_amount_mm !== null
                    ? ` (~${advisory.localized_nowcast_context.expected_amount_mm.toFixed(1)} mm)`
                    : ' (Amount: —)'}
                </span>
                <span className="text-slate-400 text-[10px]">
                  Sources: {advisory.localized_nowcast_context.source_state}
                </span>
              </div>
              {advisory.localized_nowcast_context.evidence_disagreement && (
                <div className="text-[10px] text-amber-300 flex items-center gap-1 mt-1">
                  <AlertCircle className="w-3 h-3 text-amber-400 flex-shrink-0" />
                  <span>Forecast and local observations differ (cautious guidance applied).</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Advisory Provenance Strip (Requirement 10) */}
        <div className="my-2.5 p-2 rounded-lg bg-slate-950/40 border border-slate-800/70 text-[10px] font-mono text-slate-400 grid grid-cols-2 sm:grid-cols-3 gap-1.5">
          <div>
            <span className="text-slate-500">Model:</span>{' '}
            <span className="text-purple-300 font-semibold">{advisory.model_used || 'DYNAMIC_V2'}</span>
          </div>
          <div>
            <span className="text-slate-500">Provider:</span>{' '}
            <span className="text-emerald-300 font-semibold">{advisory.source_provider || 'CANONICAL_PILOT_FIXTURE'}</span>
          </div>
          <div>
            <span className="text-slate-500">Fallback:</span>{' '}
            <span className={advisory.fallback_active ? 'text-amber-300 font-semibold' : 'text-slate-300'}>
              {advisory.fallback_active ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>
          <div className="col-span-2 truncate">
            <span className="text-slate-500">Forecast Time:</span>{' '}
            <span className="text-slate-300">{advisory.forecast_timestamp || advisory.valid_from?.substring(0, 16)}</span>
          </div>
          <div className="truncate">
            <span className="text-slate-500">Loc:</span>{' '}
            <span className="text-slate-300">Panchayat {advisory.panchayat_id}</span>
          </div>
        </div>

        {/* Bottom Metadata & Explainability Action */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 mt-2">
          <div className="flex items-center gap-1.5 text-slate-400 text-xs font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>
              Window: <strong className="text-slate-300">{advisory.optimal_window || 'Next 24-48h'}</strong>
            </span>
          </div>

          <button
            id={`explain-advisory-${advisory.id}`}
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-all shadow-sm"
          >
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span>Why this advisory?</span>
          </button>
        </div>
      </div>

      {/* 5-Step Explainability Modal */}
      <ExplainabilityModal
        advisory={advisory}
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </>
  );
};
