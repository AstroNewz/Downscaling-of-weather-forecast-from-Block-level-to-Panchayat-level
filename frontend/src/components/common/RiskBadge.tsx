import React from 'react';
import { RiskSeverity } from '../../types';
import { AlertTriangle, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface RiskBadgeProps {
  severity: RiskSeverity | string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  severity,
  size = 'md',
  showIcon = true,
}) => {
  const norm = (severity || 'NONE').toUpperCase();

  let bg = 'bg-slate-800/80 text-slate-300 border-slate-700';
  let icon = <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />;

  switch (norm) {
    case 'CRITICAL':
    case 'EXTREME':
      bg = 'bg-rose-950/80 text-rose-300 border-rose-500/50 shadow-sm shadow-rose-950/40';
      icon = <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />;
      break;
    case 'HIGH':
      bg = 'bg-red-950/80 text-red-300 border-red-500/40';
      icon = <AlertTriangle className="w-3.5 h-3.5 text-red-400" />;
      break;
    case 'MODERATE':
      bg = 'bg-amber-950/80 text-amber-300 border-amber-500/40';
      icon = <AlertCircle className="w-3.5 h-3.5 text-amber-400" />;
      break;
    case 'LOW':
      bg = 'bg-blue-950/80 text-blue-300 border-blue-500/40';
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />;
      break;
    default:
      bg = 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30';
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      break;
  }

  const padding = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-bold uppercase tracking-wider rounded-full border ${padding} ${bg}`}
    >
      {showIcon && icon}
      <span>{norm === 'NONE' ? 'LOW RISK' : norm}</span>
    </span>
  );
};
