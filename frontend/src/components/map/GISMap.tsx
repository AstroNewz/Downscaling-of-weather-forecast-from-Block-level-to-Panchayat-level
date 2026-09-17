import React, { useState, useMemo } from 'react';
import { Panchayat, GridCell } from '../../types';
import { Layers, MapPin, Eye, Maximize2, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface GISMapProps {
  panchayat: Panchayat;
  gridCells: GridCell[];
  selectedCell: GridCell | null;
  onSelectCell: (cell: GridCell | null) => void;
  className?: string;
}

export const GISMap: React.FC<GISMapProps> = ({
  panchayat,
  gridCells,
  selectedCell,
  onSelectCell,
  className = '',
}) => {
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showContours, setShowContours] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  // Compute bounding box around cells or default
  const { minLat, maxLat, minLon, maxLon } = useMemo(() => {
    if (gridCells.length === 0) {
      const lat = panchayat.latitude || panchayat.centroid_lat || 22.5978;
      const lon = panchayat.longitude || panchayat.centroid_lon || 75.3039;
      return {
        minLat: lat - 0.02,
        maxLat: lat + 0.02,
        minLon: lon - 0.02,
        maxLon: lon + 0.02,
      };
    }
    const lats = gridCells.map((c) => c.latitude);
    const lons = gridCells.map((c) => c.longitude);
    return {
      minLat: Math.min(...lats) - 0.005,
      maxLat: Math.max(...lats) + 0.005,
      minLon: Math.min(...lons) - 0.005,
      maxLon: Math.max(...lons) + 0.005,
    };
  }, [gridCells, panchayat]);

  // Coordinate projection to SVG space (viewBox: 0 0 600 400)
  const project = (lat: number, lon: number) => {
    const latSpan = maxLat - minLat || 0.01;
    const lonSpan = maxLon - minLon || 0.01;
    const x = ((lon - minLon) / lonSpan) * 520 + 40;
    const y = (1 - (lat - minLat) / latSpan) * 320 + 40;
    return { x, y };
  };

  const centerLat = (minLat + maxLat) / 2;
  const centerLon = (minLon + maxLon) / 2;
  const centerPt = project(centerLat, centerLon);

  return (
    <div
      className={`glass-panel rounded-xl border border-slate-800 bg-[#070d18] relative overflow-hidden flex flex-col ${className}`}
    >
      {/* Top Map Bar Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 border-b border-slate-800/80 bg-[#0a1122]/90 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-emerald-500/20 text-emerald-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>{panchayat.name} Boundary & 1-km Micro-Grid</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                EPSG:32644 (UTM Zone 44N)
              </span>
            </h4>
            <p className="text-[10px] text-slate-400 font-mono">
              Center: {centerLat.toFixed(4)}°N, {centerLon.toFixed(4)}°E • Area: {panchayat.total_area_ha || 1240} ha
            </p>
          </div>
        </div>

        {/* Layer & Zoom Controls */}
        <div className="flex items-center gap-1.5">
          <button
            id="map-toggle-grid"
            onClick={() => setShowGrid(!showGrid)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium border transition-colors ${
              showGrid
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 font-semibold'
                : 'bg-slate-900 border-slate-800 text-slate-400'
            }`}
          >
            1-km Grid ({gridCells.length})
          </button>
          <button
            id="map-toggle-contours"
            onClick={() => setShowContours(!showContours)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium border transition-colors ${
              showContours
                ? 'bg-sky-500/20 border-sky-500/40 text-sky-300 font-semibold'
                : 'bg-slate-900 border-slate-800 text-slate-400'
            }`}
          >
            Boundary Contour
          </button>

          <div className="h-4 w-px bg-slate-800 mx-1" />

          <button
            onClick={() => setZoomLevel((prev) => Math.min(2, prev + 0.2))}
            title="Zoom In"
            className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel((prev) => Math.max(0.8, prev - 0.2))}
            title="Zoom Out"
            className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setZoomLevel(1);
              onSelectCell(null);
            }}
            title="Reset View"
            className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* SVG GIS Canvas */}
      <div className="relative flex-1 w-full min-h-[360px] bg-[#050811] flex items-center justify-center overflow-hidden">
        <svg
          viewBox="0 0 600 400"
          className="w-full h-full select-none"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center', transition: 'transform 0.2s ease-out' }}
        >
          {/* Subtle GIS coordinate grid lines */}
          <defs>
            <pattern id="gis-grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#10192e" strokeWidth="0.75" />
            </pattern>
            <radialGradient id="panchayat-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </radialGradient>
          </defs>

          <rect width="600" height="400" fill="url(#gis-grid-pattern)" />

          {/* Panchayat Region Glow & Simulated Boundary Polygon */}
          {showContours && (
            <g>
              <ellipse
                cx={centerPt.x}
                cy={centerPt.y}
                rx="180"
                ry="130"
                fill="url(#panchayat-glow)"
              />
              <path
                d={`M ${centerPt.x - 160} ${centerPt.y - 60} 
                   Q ${centerPt.x - 80} ${centerPt.y - 120} ${centerPt.x + 80} ${centerPt.y - 110} 
                   Q ${centerPt.x + 170} ${centerPt.y - 50} ${centerPt.x + 160} ${centerPt.y + 70} 
                   Q ${centerPt.x + 50} ${centerPt.y + 130} ${centerPt.x - 90} ${centerPt.y + 110} 
                   Q ${centerPt.x - 170} ${centerPt.y + 40} ${centerPt.x - 160} ${centerPt.y - 60} Z`}
                fill="rgba(16, 185, 129, 0.05)"
                stroke="#10b981"
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />
            </g>
          )}

          {/* 1-km Grid Cells */}
          {showGrid &&
            gridCells.map((cell) => {
              const pt = project(cell.latitude, cell.longitude);
              const isSelected = selectedCell?.cell_id === cell.cell_id;
              const temp = cell.downscaled_temperature_c ?? cell.tmean_c ?? 32.5;

              // Color cell by temperature (mild emerald -> warm amber -> hot rose)
              const fillColor =
                temp > 35
                  ? 'rgba(244, 63, 94, 0.35)'
                  : temp > 33
                  ? 'rgba(245, 158, 11, 0.35)'
                  : 'rgba(16, 185, 129, 0.35)';

              const strokeColor = isSelected
                ? '#38bdf8'
                : temp > 35
                ? '#f43f5e'
                : temp > 33
                ? '#f59e0b'
                : '#10b981';

              return (
                <g
                  key={cell.cell_id}
                  id={`grid-cell-${cell.cell_id}`}
                  onClick={() => onSelectCell(isSelected ? null : cell)}
                  className="cursor-pointer transition-all duration-150 group"
                >
                  <rect
                    x={pt.x - 22}
                    y={pt.y - 22}
                    width="44"
                    height="44"
                    rx="6"
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 3 : 1.2}
                    className="hover:opacity-90 hover:stroke-white"
                  />
                  {/* Temperature label */}
                  <text
                    x={pt.x}
                    y={pt.y + 3}
                    textAnchor="middle"
                    className="text-[10px] font-mono fill-slate-200 font-bold pointer-events-none"
                  >
                    {temp.toFixed(1)}°
                  </text>
                </g>
              );
            })}

          {/* Centroid Marker */}
          <g transform={`translate(${centerPt.x}, ${centerPt.y})`}>
            <circle r="6" fill="#10b981" className="animate-ping opacity-30" />
            <circle r="4" fill="#10b981" stroke="#050811" strokeWidth="2" />
            <text
              y="-10"
              textAnchor="middle"
              className="text-[10px] font-bold fill-white font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]"
            >
              {panchayat.name} (HQ)
            </text>
          </g>
        </svg>

        {/* Bottom map overlay legend */}
        <div className="absolute bottom-3 left-3 bg-[#0a1122]/90 backdrop-blur-md border border-slate-800 rounded-lg p-2 text-[10px] font-mono flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-emerald-500/40 border border-emerald-500" />
            <span className="text-slate-300">&lt; 33°C (Normal)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-amber-500/40 border border-amber-500" />
            <span className="text-slate-300">33-35°C (Warm)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-rose-500/40 border border-rose-500" />
            <span className="text-slate-300">&gt; 35°C (Elevated)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
