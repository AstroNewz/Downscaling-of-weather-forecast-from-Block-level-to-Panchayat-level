import React from 'react';
import { RiskSeverity } from '../../types';

interface RiskBadgeProps {
  severity: RiskSeverity | string;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  score?: number;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  severity,
  size = 'md',
  showScore = false,
  score,
}) => {
  const norm = (severity || 'NONE').toUpperCase();

  let bgClass = 'bg-slate-800 text-slate-300 border-slate-700';
  let dotColor = 'bg-slate-400';

  if (norm === 'CRITICAL') {
    bgClass = 'bg-rose-950/60 text-rose-300 border-rose-500/40 shadow-sm shadow-rose-950/30';
    dotColor = 'bg-rose-400';
  } else if (norm === 'HIGH') {
    bgClass = 'bg-orange-950/50 text-orange-300 border-orange-500/30';
    dotColor = 'bg-orange-400';
  } else if (norm === 'MODERATE' || norm === 'MEDIUM') {
    bgClass = 'bg-amber-950/40 text-amber-300 border-amber-500/30';
    dotColor = 'bg-amber-400';
  } else if (norm === 'LOW') {
    bgClass = 'bg-emerald-950/30 text-emerald-300 border-emerald-500/20';
    dotColor = 'bg-emerald-400';
  } else {
    bgClass = 'bg-slate-800/80 text-slate-400 border-slate-700/50';
    dotColor = 'bg-slate-500';
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-medium',
    md: 'px-2.5 py-1 text-xs font-semibold',
    lg: 'px-3 py-1.5 text-sm font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${bgClass} ${sizeClasses[size]} uppercase tracking-wider`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span>{norm}</span>
      {showScore && score !== undefined && (
        <span className="opacity-75 font-mono text-[10px] lowercase">
          ({score.toFixed(2)})
        </span>
      )}
    </span>
  );
};
