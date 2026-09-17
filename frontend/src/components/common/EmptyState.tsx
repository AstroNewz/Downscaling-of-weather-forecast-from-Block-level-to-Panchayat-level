import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: LucideIcon;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Records Found',
  message = 'No data available matching the current search parameters or geospatial filters.',
  icon: Icon = Inbox,
  actionText,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`glass-panel p-8 rounded-xl border border-slate-800 text-center flex flex-col items-center justify-center max-w-md mx-auto my-6 ${className}`}
    >
      <div className="p-3 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-sm font-semibold text-slate-200 mb-1">{title}</h4>
      <p className="text-xs text-slate-400 max-w-xs mb-4">{message}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs font-medium border border-emerald-500/30 transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
