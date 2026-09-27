import React from 'react';

interface LoadingStateProps {
  message?: string;
  variant?: 'card' | 'table' | 'full';
  count?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Retrieving forecast and downscaling intelligence...',
  variant = 'card',
  count = 3,
}) => {
  if (variant === 'full') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
        <div className="relative w-14 h-14 mb-4">
          <div className="absolute inset-0 rounded-full border-3 border-blue-100 border-t-blue-600 animate-spin" />
        </div>
        <p className="text-sm text-slate-800 font-semibold">{message}</p>
        <p className="text-xs text-slate-500 mt-1 font-mono">Connecting to NWP Downscaling Pipeline</p>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className="w-full space-y-2 p-4 animate-pulse">
        <div className="h-10 bg-slate-200 rounded-lg w-full mb-3" />
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="h-12 bg-slate-100 rounded-lg w-full flex items-center px-4 gap-4">
            <div className="h-4 bg-slate-200 rounded w-1/6" />
            <div className="h-4 bg-slate-200 rounded w-1/4" />
            <div className="h-4 bg-slate-200 rounded w-1/5" />
            <div className="h-4 bg-slate-200 rounded w-1/6" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card-white p-5 rounded-xl border border-slate-200 space-y-3 bg-white">
          <div className="flex justify-between items-center">
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-6 w-16 bg-slate-200 rounded-full" />
          </div>
          <div className="h-8 bg-slate-100 rounded w-2/3 my-2" />
          <div className="h-3 bg-slate-100 rounded w-full" />
          <div className="h-3 bg-slate-100 rounded w-4/5" />
        </div>
      ))}
    </div>
  );
};
