import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Connection Alert',
  message = 'Unable to fetch data from the agro-meteorological downscaling engine.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`glass-panel p-6 rounded-xl border border-rose-500/30 bg-rose-950/10 text-center flex flex-col items-center justify-center max-w-lg mx-auto ${className}`}
    >
      <div className="p-3 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-100 mb-1">{title}</h3>
      <p className="text-xs text-slate-400 mb-4 max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Query</span>
        </button>
      )}
    </div>
  );
};
