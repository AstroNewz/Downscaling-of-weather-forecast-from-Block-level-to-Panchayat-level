import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase();

  let colors = 'bg-slate-800 text-slate-300 border-slate-700';
  let label = status;

  if (normalized === 'ELIGIBLE' || normalized === 'CROPLAND' || normalized === 'VALID' || normalized === 'OPERATIONAL') {
    colors = 'bg-emerald-950/70 text-emerald-300 border-emerald-500/40';
    label = normalized === 'ELIGIBLE' ? 'Cropland Eligible' : normalized;
  } else if (normalized === 'NON_CROPLAND' || normalized === 'INELIGIBLE' || normalized === 'DEGRADED') {
    colors = 'bg-amber-950/70 text-amber-300 border-amber-500/40';
    label = normalized === 'NON_CROPLAND' ? 'Non-Cropland' : normalized;
  } else if (normalized === 'MISSING' || normalized === 'OFFLINE') {
    colors = 'bg-rose-950/70 text-rose-300 border-rose-500/40';
  } else if (normalized === 'RESEARCH_ONLY') {
    colors = 'bg-amber-950/80 text-amber-300 border-amber-600/50';
    label = 'RESEARCH ONLY';
  } else if (normalized === 'CERTIFIED') {
    colors = 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50';
    label = 'CERTIFIED PRODUCTION';
  }

  const padding = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center font-mono font-bold uppercase tracking-wider rounded-full border ${padding} ${colors}`}
    >
      {label}
    </span>
  );
};
