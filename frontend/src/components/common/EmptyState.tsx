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
      className={`card-white p-8 rounded-xl border border-slate-200 text-center flex flex-col items-center justify-center max-w-md mx-auto my-6 bg-white ${className}`}
    >
      <div className="p-3 rounded-full bg-slate-100 border border-slate-200 text-slate-500 mb-3">
        <Icon className="w-6 h-6 text-slate-600" />
      </div>
      <h4 className="text-sm font-bold text-slate-900 mb-1">{title}</h4>
      <p className="text-xs text-slate-500 max-w-xs mb-4">{message}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200 transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
