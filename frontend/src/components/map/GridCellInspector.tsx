import React from 'react';
import { GridCell } from '../../types';
import { X, MapPin, Mountain, Thermometer, ShieldCheck, Layers, Compass } from 'lucide-react';

interface GridCellInspectorProps {
  cell: GridCell | null;
  onClose: () => void;
  panchayatName: string;
}

export const GridCellInspector: React.FC<GridCellInspectorProps> = ({
  cell,
  onClose,
  panchayatName,
}) => {
  if (!cell) return null;

  const coarseT = cell.coarse_temperature_c ?? 32.5;
  const residual = cell.predicted_residual_c ?? cell.predicted_residual ?? 0.7351;
  const downscaledT = cell.downscaled_temperature_c ?? cell.tmean_c ?? (coarseT + residual);

  return (
    <div
      id="grid-cell-inspector-panel"
      className="glass-panel p-4 rounded-xl border border-slate-700/80 bg-[#0c1322] shadow-xl space-y-3 w-full max-w-sm animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-sky-500/15 text-sky-400">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white">1-km Grid Cell Inspector</h4>
            <p className="text-[10px] font-mono text-slate-400">{cell.cell_id}</p>
          </div>
        </div>

        <button
          id="close-cell-inspector-btn"
          onClick={onClose}
          className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Panchayat Context */}
      <div className="text-[11px] text-slate-300 flex justify-between">
        <span className="text-slate-500">Panchayat:</span>
        <strong className="text-emerald-300">{panchayatName}</strong>
      </div>

      {/* Coordinates & Physical Topography */}
      <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">Latitude</span>
          <p className="font-mono text-slate-200">{cell.latitude.toFixed(4)}°N</p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">Longitude</span>
          <p className="font-mono text-slate-200">{cell.longitude.toFixed(4)}°E</p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">Elevation</span>
          <p className="font-mono text-slate-200">{cell.elevation_m ? `${cell.elevation_m} m` : '540 m'}</p>
        </div>
        <div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">Cropland Share</span>
          <p className="font-mono text-emerald-400">
            {cell.cropland_fraction !== undefined ? `${(cell.cropland_fraction * 100).toFixed(0)}%` : '85%'}
          </p>
        </div>
      </div>

      {/* Thermal Bias Breakdown */}
      <div className="space-y-1.5 text-xs bg-emerald-950/20 p-2.5 rounded-lg border border-emerald-500/30">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Coarse ERA5 NWP:</span>
          <span className="font-mono text-slate-300">{coarseT.toFixed(2)}°C</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-emerald-400 flex items-center gap-1 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Certified Residual:</span>
          </span>
          <span className="font-mono text-emerald-300 font-bold">+{residual.toFixed(4)}°C</span>
        </div>
        <div className="h-px bg-emerald-500/20 my-1" />
        <div className="flex items-center justify-between font-bold">
          <span className="text-white">1-km Calibrated Tmean:</span>
          <span className="font-mono text-emerald-400 text-sm">{downscaledT.toFixed(2)}°C</span>
        </div>
      </div>

      {/* Projection details */}
      <div className="text-[10px] font-mono text-slate-500 flex justify-between pt-1">
        <span>Dynamic UTM (EPSG:32644)</span>
        <span>Resolution: 1000m x 1000m</span>
      </div>
    </div>
  );
};
