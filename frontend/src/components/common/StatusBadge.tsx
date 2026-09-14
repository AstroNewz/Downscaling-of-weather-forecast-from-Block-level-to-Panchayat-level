import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showDot = true,
}) => {
  const normalized = status.toUpperCase();

  let bgClass = 'bg-slate-800/80 text-slate-300 border-slate-700';
  let dotClass = 'bg-slate-400';
  let label = status;

  switch (normalized) {
    case 'COMPLETE':
    case 'EXCELLENT':
    case 'ACTIVE':
    case 'HEALTHY':
    case 'PASS':
      bgClass = 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30';
      dotClass = 'bg-emerald-400';
      break;
    case 'PARTIAL':
    case 'GOOD':
    case 'IN_PROGRESS':
    case 'WARNING':
      bgClass = 'bg-amber-950/40 text-amber-300 border-amber-500/30';
      dotClass = 'bg-amber-400';
      break;
    case 'UNAVAILABLE':
    case 'POOR':
    case 'FAILED':
    case 'CRITICAL':
    case 'EXPERT_REVIEW_REQUIRED':
      bgClass = 'bg-rose-950/40 text-rose-300 border-rose-500/30';
      dotClass = 'bg-rose-400';
      break;
    case 'ELIGIBLE':
      bgClass = 'bg-teal-950/40 text-teal-300 border-teal-500/30';
      dotClass = 'bg-teal-400';
      break;
    case 'NON_CROPLAND':
    case 'INELIGIBLE':
      bgClass = 'bg-slate-800 text-slate-400 border-slate-700';
      dotClass = 'bg-slate-500';
      break;
    default:
      bgClass = 'bg-blue-950/40 text-blue-300 border-blue-500/30';
      dotClass = 'bg-blue-400';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-medium',
    md: 'px-2.5 py-1 text-xs font-semibold',
    lg: 'px-3 py-1.5 text-sm font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${bgClass} ${sizeClasses[size]} transition-all`}
    >
      {showDot && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${dotClass} animate-pulse`}
        />
      )}
      <span>{label.replace(/_/g, ' ')}</span>
    </span>
  );
};
