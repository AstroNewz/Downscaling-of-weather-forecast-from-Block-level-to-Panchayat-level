import React from 'react';

interface LoadingStateProps {
  message?: string;
  variant?: 'card' | 'table' | 'full';
  count?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Retrieving certified agro-meteorological records...',
  variant = 'card',
  count = 3,
}) => {
  if (variant === 'full') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
        <div className="relative w-16 h-16 mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-sky-500/20 border-b-sky-400 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>
        <p className="text-sm text-slate-300 font-medium">{message}</p>
        <p className="text-xs text-slate-500 mt-1 font-mono">Querying Local Deterministic Pipeline</p>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className="w-full space-y-2 p-4 animate-pulse">
        <div className="h-10 bg-slate-800/60 rounded-lg w-full mb-3" />
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="h-14 bg-slate-800/30 rounded-lg w-full flex items-center px-4 gap-4">
            <div className="h-4 bg-slate-700/50 rounded w-1/6" />
            <div className="h-4 bg-slate-700/50 rounded w-1/4" />
            <div className="h-4 bg-slate-700/50 rounded w-1/5" />
            <div className="h-4 bg-slate-700/50 rounded w-1/6" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass-panel p-5 rounded-xl border border-slate-800/80 space-y-3">
          <div className="flex justify-between items-center">
            <div className="h-4 bg-slate-700/40 rounded w-1/3" />
            <div className="h-6 w-16 bg-slate-700/40 rounded-full" />
          </div>
          <div className="h-8 bg-slate-700/30 rounded w-2/3 my-2" />
          <div className="h-3 bg-slate-700/30 rounded w-full" />
          <div className="h-3 bg-slate-700/30 rounded w-4/5" />
        </div>
      ))}
    </div>
  );
};
