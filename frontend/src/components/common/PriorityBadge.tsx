import React from 'react';
import { AdvisoryPriority } from '../../types';

interface PriorityBadgeProps {
  priority: AdvisoryPriority | string;
  size?: 'sm' | 'md' | 'lg';
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  size = 'md',
}) => {
  const norm = (priority || 'LOW').toUpperCase();

  let bgClass = 'bg-slate-800 text-slate-300 border-slate-700';

  if (norm === 'CRITICAL' || norm === '1') {
    bgClass = 'bg-red-950/70 text-red-200 border-red-500/50 shadow-sm shadow-red-900/40';
  } else if (norm === 'HIGH' || norm === '2') {
    bgClass = 'bg-amber-950/60 text-amber-200 border-amber-500/40';
  } else if (norm === 'MEDIUM' || norm === '3') {
    bgClass = 'bg-sky-950/50 text-sky-200 border-sky-500/30';
  } else if (norm === 'LOW' || norm === '4') {
    bgClass = 'bg-emerald-950/40 text-emerald-200 border-emerald-500/30';
  } else {
    bgClass = 'bg-slate-800 text-slate-400 border-slate-700';
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] font-bold',
    md: 'px-2.5 py-1 text-xs font-bold',
    lg: 'px-3 py-1.5 text-sm font-bold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border ${bgClass} ${sizeClasses[size]} uppercase tracking-wider font-mono`}
    >
      <span>PRIORITY:</span>
      <span className="font-extrabold">{norm}</span>
    </span>
  );
};
