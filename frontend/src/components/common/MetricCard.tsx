import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  status?: 'emerald' | 'amber' | 'rose' | 'sky' | 'indigo' | 'slate';
  className?: string;
  badge?: string;
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  status = 'slate',
  className = '',
  badge,
  onClick,
}) => {
  const statusColors = {
    emerald: {
      border: 'border-emerald-500/30 hover:border-emerald-500/50',
      iconBg: 'bg-emerald-500/10 text-emerald-400',
      valueColor: 'text-emerald-300',
      glow: 'shadow-[0_0_20px_rgba(16,185,129,0.08)]',
    },
    amber: {
      border: 'border-amber-500/30 hover:border-amber-500/50',
      iconBg: 'bg-amber-500/10 text-amber-400',
      valueColor: 'text-amber-300',
      glow: 'shadow-[0_0_20px_rgba(245,158,11,0.08)]',
    },
    rose: {
      border: 'border-rose-500/30 hover:border-rose-500/50',
      iconBg: 'bg-rose-500/10 text-rose-400',
      valueColor: 'text-rose-300',
      glow: 'shadow-[0_0_20px_rgba(244,63,94,0.08)]',
    },
    sky: {
      border: 'border-sky-500/30 hover:border-sky-500/50',
      iconBg: 'bg-sky-500/10 text-sky-400',
      valueColor: 'text-sky-300',
      glow: 'shadow-[0_0_20px_rgba(14,165,233,0.08)]',
    },
    indigo: {
      border: 'border-indigo-500/30 hover:border-indigo-500/50',
      iconBg: 'bg-indigo-500/10 text-indigo-400',
      valueColor: 'text-indigo-300',
      glow: 'shadow-[0_0_20px_rgba(99,102,241,0.08)]',
    },
    slate: {
      border: 'border-slate-800 hover:border-slate-700',
      iconBg: 'bg-slate-800/60 text-slate-300',
      valueColor: 'text-white',
      glow: 'shadow-[0_0_15px_rgba(15,23,42,0.5)]',
    },
  }[status];

  return (
    <div
      onClick={onClick}
      className={`glass-panel p-4.5 rounded-xl border transition-all duration-200 relative overflow-hidden ${
        statusColors.border
      } ${statusColors.glow} ${onClick ? 'cursor-pointer hover:translate-y-[-2px]' : ''} ${className}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider line-clamp-1">
          {title}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {badge && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700/80 text-slate-300 font-semibold">
              {badge}
            </span>
          )}
          {Icon && (
            <div className={`p-2 rounded-lg ${statusColors.iconBg}`}>
              <Icon className="w-4 h-4" />
            </div>
          )}
        </div>
      </div>

      <div className="flex items-baseline gap-1.5 mb-1.5">
        <span className={`text-2xl font-bold tracking-tight font-mono ${statusColors.valueColor}`}>
          {value}
        </span>
        {unit && (
          <span className="text-xs font-mono font-medium text-slate-400">{unit}</span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400 mt-2">
        {subtitle && <span className="line-clamp-1">{subtitle}</span>}
        {trend && trendValue && (
          <div
            className={`flex items-center gap-1 font-mono text-xs ml-auto ${
              trend === 'up'
                ? 'text-rose-400'
                : trend === 'down'
                ? 'text-emerald-400'
                : 'text-slate-400'
            }`}
          >
            <span>{trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—'}</span>
            <span>{trendValue}</span>
          </div>
        )}
      </div>
    </div>
  );
};
