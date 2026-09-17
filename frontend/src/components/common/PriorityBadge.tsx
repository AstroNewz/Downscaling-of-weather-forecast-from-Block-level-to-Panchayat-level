import React from 'react';
import { AdvisoryPriority } from '../../types';

interface PriorityBadgeProps {
  priority: AdvisoryPriority;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  size = 'md',
  className = '',
}) => {
  const normPriority = (priority || 'LOW').toUpperCase() as AdvisoryPriority;

  const config = {
    CRITICAL: {
      label: 'Critical Priority',
      bg: 'bg-rose-500/15 border-rose-500/40 text-rose-300',
      dot: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)] animate-pulse',
    },
    HIGH: {
      label: 'High Priority',
      bg: 'bg-amber-500/15 border-amber-500/40 text-amber-300',
      dot: 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]',
    },
    MEDIUM: {
      label: 'Medium Priority',
      bg: 'bg-sky-500/15 border-sky-500/40 text-sky-300',
      dot: 'bg-sky-400',
    },
    LOW: {
      label: 'Low Priority',
      bg: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300',
      dot: 'bg-emerald-400',
    },
  }[normPriority] || {
    label: normPriority,
    bg: 'bg-slate-700/30 border-slate-600/40 text-slate-300',
    dot: 'bg-slate-400',
  };

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 gap-1.5',
    md: 'text-xs px-2.5 py-1 gap-2',
    lg: 'text-sm px-3.5 py-1.5 gap-2.5 font-medium',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border tracking-wide uppercase ${config.bg} ${sizeClasses} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
};
