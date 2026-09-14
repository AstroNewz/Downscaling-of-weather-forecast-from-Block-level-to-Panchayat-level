import React from 'react';
import { X, Grid, Mountain, Compass, Eye, Sprout, Thermometer } from 'lucide-react';
import { GridCell } from '../../types';

interface GridCellInspectorProps {
  cell: GridCell | null;
  onClose: () => void;
}

export const GridCellInspector: React.FC<GridCellInspectorProps> = ({
  cell,
  onClose,
}) => {
  if (!cell) return null;

  return (
    <div className="bg-slate-900/95 backdrop-blur-xl border border-emerald-500/40 rounded-2xl p-5 shadow-2xl max-w-sm w-full text-slate-200">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Grid className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white leading-none">
              1-km Grid Cell #{cell.cell_id}
            </h4>
            <span className="text-[10px] text-slate-400 font-mono">
              Lat: {cell.latitude.toFixed(4)}, Lon: {cell.longitude.toFixed(4)}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Temperature & Downscaling Residual */}
      <div className="my-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 flex items-center gap-1.5">
            <Thermometer className="w-3.5 h-3.5 text-emerald-400" />
            Downscaled Tmean:
          </span>
          <span className="text-sm font-bold font-mono text-emerald-400">
            {cell.tmean_c.toFixed(2)} °C
          </span>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Predicted ML Residual (ΔT):</span>
          <span
            className={`font-mono font-bold ${
              cell.predicted_residual >= 0 ? 'text-amber-400' : 'text-sky-400'
            }`}
          >
            {cell.predicted_residual >= 0
              ? `+${cell.predicted_residual.toFixed(2)}`
              : cell.predicted_residual.toFixed(2)}{' '}
            °C
          </span>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Tmax / Tmin:</span>
          <span className="font-mono text-slate-300">
            {cell.tmax_c.toFixed(1)}° / {cell.tmin_c.toFixed(1)}° C
          </span>
        </div>
      </div>

      {/* Topographic & Terrain Features */}
      <div className="space-y-2 text-xs">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
          Terrain & Surface Biophysical Parameters
        </span>

        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-800/80 flex items-center gap-2">
            <Mountain className="w-3.5 h-3.5 text-amber-400" />
            <div>
              <span className="text-[10px] text-slate-500 block">Elevation</span>
              <span className="font-mono font-semibold text-slate-200">
                {cell.elevation_m.toFixed(0)} m
              </span>
            </div>
          </div>

          <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-800/80 flex items-center gap-2">
            <Compass className="w-3.5 h-3.5 text-sky-400" />
            <div>
              <span className="text-[10px] text-slate-500 block">Slope</span>
              <span className="font-mono font-semibold text-slate-200">
                {cell.slope_deg.toFixed(1)}°
              </span>
            </div>
          </div>
        </div>

        {/* Cropland & LULC Coverage */}
        <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sprout className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-300">Cropland Fraction:</span>
          </div>
          <span className="font-mono font-bold text-emerald-400">
            {(cell.cropland_fraction * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {cell.panchayat_name && (
        <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span>Parent Panchayat:</span>
          <span className="font-semibold text-slate-200">{cell.panchayat_name}</span>
        </div>
      )}
    </div>
  );
};
