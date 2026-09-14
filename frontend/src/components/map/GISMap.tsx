import React, { useState, useRef, useEffect } from 'react';
import { 
  Layers, 
  Eye, 
  EyeOff, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  MapPin, 
  Grid, 
  Flame, 
  Sprout, 
  ShieldAlert, 
  Navigation,
  Info
} from 'lucide-react';
import { Panchayat, GridCell, RiskSeverity } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { GridCellInspector } from './GridCellInspector';

interface GISMapProps {
  panchayats: Panchayat[];
  gridCells?: GridCell[];
  selectedPanchayatId?: number | null;
  onSelectPanchayat?: (p: Panchayat) => void;
  height?: string;
}

export const GISMap: React.FC<GISMapProps> = ({
  panchayats,
  gridCells = [],
  selectedPanchayatId,
  onSelectPanchayat,
  height = '600px',
}) => {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Layer toggles
  const [showGridOverlay, setShowGridOverlay] = useState(true);
  const [showPanchayatMarkers, setShowPanchayatMarkers] = useState(true);
  const [showRiskHeatmap, setShowRiskHeatmap] = useState(true);
  const [showCroplandMask, setShowCroplandMask] = useState(false);
  const [activeBaseLayer, setActiveBaseLayer] = useState<'dark' | 'satellite' | 'terrain'>('dark');

  // Selected Grid Cell Inspector
  const [inspectedCell, setInspectedCell] = useState<GridCell | null>(null);
  const [hoveredPanchayat, setHoveredPanchayat] = useState<Panchayat | null>(null);

  // Compute bounding box coordinates for mapping
  const centerLat = 26.78;
  const centerLon = 82.15;
  const latSpan = 0.45;
  const lonSpan = 0.55;

  const latToY = (lat: number) => {
    const norm = (lat - (centerLat - latSpan / 2)) / latSpan;
    return (1 - norm) * 500;
  };

  const lonToX = (lon: number) => {
    const norm = (lon - (centerLon - lonSpan / 2)) / lonSpan;
    return norm * 800;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPanOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const zoomIn = () => setZoomLevel((z) => Math.min(z + 0.3, 3));
  const zoomOut = () => setZoomLevel((z) => Math.max(z - 0.3, 0.7));
  const resetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Generate fallback 1-km grid points if not provided
  const cellsToRender: GridCell[] = gridCells.length > 0
    ? gridCells
    : panchayats.flatMap((p, pIdx) => {
        const pLat = p.centroid_lat || centerLat;
        const pLon = p.centroid_lon || centerLon;
        return [
          {
            cell_id: pIdx * 10 + 1,
            panchayat_id: p.id,
            panchayat_name: p.name,
            latitude: pLat + 0.005,
            longitude: pLon - 0.005,
            tmax_c: (p.latest_weather?.tmax_c || 35) + 0.4,
            tmin_c: (p.latest_weather?.tmin_c || 24) - 0.2,
            tmean_c: (p.latest_weather?.tmean_c || 29.5) + 0.1,
            predicted_residual: (p.latest_weather?.predicted_residual_delta_c || 0.8) + 0.2,
            elevation_m: 110 + (pIdx % 5) * 8,
            slope_deg: 2.1 + (pIdx % 4) * 0.5,
            aspect_deg: 135,
            cropland_fraction: p.is_cropland_eligible ? 0.85 : 0.2,
          },
          {
            cell_id: pIdx * 10 + 2,
            panchayat_id: p.id,
            panchayat_name: p.name,
            latitude: pLat - 0.005,
            longitude: pLon + 0.005,
            tmax_c: (p.latest_weather?.tmax_c || 35) - 0.3,
            tmin_c: (p.latest_weather?.tmin_c || 24) + 0.1,
            tmean_c: (p.latest_weather?.tmean_c || 29.5) - 0.1,
            predicted_residual: (p.latest_weather?.predicted_residual_delta_c || 0.8) - 0.3,
            elevation_m: 104 + (pIdx % 3) * 6,
            slope_deg: 1.5,
            aspect_deg: 190,
            cropland_fraction: p.is_cropland_eligible ? 0.78 : 0.15,
          },
        ];
      });

  const getHeatmapColor = (temp: number) => {
    if (temp >= 36) return 'rgba(239, 68, 68, 0.45)'; // High Heat Red
    if (temp >= 32) return 'rgba(245, 158, 11, 0.40)'; // Moderate Amber
    if (temp >= 28) return 'rgba(16, 185, 129, 0.35)'; // Optimal Green
    return 'rgba(56, 189, 248, 0.35)'; // Cool Blue
  };

  return (
    <div
      className="relative rounded-2xl overflow-hidden border border-slate-700/80 shadow-2xl bg-slate-950 select-none"
      style={{ height }}
    >
      {/* GIS Base Map Surface */}
      <div
        className="w-full h-full cursor-grab active:cursor-grabbing overflow-hidden"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          className="w-full h-full"
          viewBox="0 0 800 500"
          preserveAspectRatio="xMidYMid slice"
          style={{
            transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.15s ease-out',
          }}
        >
          {/* Base Map Background & District Contours */}
          <defs>
            <radialGradient id="mapGlow" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stopColor="#0f172a" />
              <stop offset="100%" stopColor="#020617" />
            </radialGradient>
            <pattern id="gisGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.75" />
            </pattern>
          </defs>

          <rect width="800" height="500" fill="url(#mapGlow)" />
          <rect width="800" height="500" fill="url(#gisGrid)" opacity="0.6" />

          {/* Block boundary polygons (Ayodhya District simulation) */}
          <g className="block-boundaries" opacity="0.8">
            <path
              d="M 120,80 L 380,60 L 420,240 L 220,280 L 100,200 Z"
              fill="rgba(30, 41, 59, 0.3)"
              stroke="#334155"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
            <text x="230" y="150" fill="#475569" fontSize="13" fontWeight="bold" fontFamily="monospace">
              BLOCK: MAYA BAZAR
            </text>

            <path
              d="M 420,60 L 700,90 L 680,310 L 440,300 L 420,180 Z"
              fill="rgba(30, 41, 59, 0.3)"
              stroke="#334155"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
            <text x="520" y="170" fill="#475569" fontSize="13" fontWeight="bold" fontFamily="monospace">
              BLOCK: SOHAWAL
            </text>

            <path
              d="M 180,280 L 450,300 L 480,460 L 220,450 Z"
              fill="rgba(30, 41, 59, 0.3)"
              stroke="#334155"
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
            <text x="300" y="380" fill="#475569" fontSize="13" fontWeight="bold" fontFamily="monospace">
              BLOCK: BIKAPUR
            </text>
          </g>

          {/* 1-km Grid Cells Heatmap / Grid Overlay Layer */}
          {showGridOverlay && (
            <g className="grid-layer">
              {cellsToRender.map((cell) => {
                const x = lonToX(cell.longitude);
                const y = latToY(cell.latitude);
                const isInspected = inspectedCell?.cell_id === cell.cell_id;

                return (
                  <g key={cell.cell_id} className="cursor-pointer">
                    {showRiskHeatmap && (
                      <circle
                        cx={x}
                        cy={y}
                        r="24"
                        fill={getHeatmapColor(cell.tmean_c)}
                        opacity="0.8"
                      />
                    )}
                    <rect
                      x={x - 12}
                      y={y - 12}
                      width="24"
                      height="24"
                      rx="3"
                      fill={isInspected ? '#10b981' : 'rgba(15, 23, 42, 0.75)'}
                      stroke={isInspected ? '#34d399' : '#059669'}
                      strokeWidth={isInspected ? '2' : '1'}
                      className="transition-all hover:stroke-emerald-300 hover:stroke-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        setInspectedCell(cell);
                      }}
                    />
                    <text
                      x={x}
                      y={y + 3}
                      fill={isInspected ? '#0f172a' : '#a7f3d0'}
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                      textAnchor="middle"
                      pointerEvents="none"
                    >
                      {cell.tmean_c.toFixed(1)}°
                    </text>
                  </g>
                );
              })}
            </g>
          )}

          {/* Panchayat Markers & Polygons */}
          {showPanchayatMarkers && (
            <g className="panchayat-markers">
              {panchayats.map((p) => {
                const x = lonToX(p.centroid_lon || centerLon);
                const y = latToY(p.centroid_lat || centerLat);
                const isSelected = selectedPanchayatId === p.id;
                const maxRisk = p.highest_risk_severity || 'NONE';

                let markerColor = '#10b981'; // green
                if (maxRisk === 'CRITICAL') markerColor = '#ef4444';
                else if (maxRisk === 'HIGH') markerColor = '#f97316';
                else if (maxRisk === 'MODERATE') markerColor = '#f59e0b';

                return (
                  <g
                    key={p.id}
                    className="cursor-pointer group"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onSelectPanchayat) onSelectPanchayat(p);
                    }}
                    onMouseEnter={() => setHoveredPanchayat(p)}
                    onMouseLeave={() => setHoveredPanchayat(null)}
                  >
                    {/* Pulsing ring if selected or critical */}
                    {(isSelected || maxRisk === 'CRITICAL') && (
                      <circle
                        cx={x}
                        cy={y}
                        r="18"
                        fill="none"
                        stroke={markerColor}
                        strokeWidth="1.5"
                        opacity="0.6"
                        className="animate-ping"
                      />
                    )}

                    <circle
                      cx={x}
                      cy={y}
                      r={isSelected ? '9' : '7'}
                      fill={markerColor}
                      stroke="#0f172a"
                      strokeWidth="2"
                    />

                    {/* Panchayat Label */}
                    <rect
                      x={x - 45}
                      y={y - 28}
                      width="90"
                      height="18"
                      rx="4"
                      fill="rgba(15, 23, 42, 0.85)"
                      stroke={isSelected ? '#10b981' : '#334155'}
                      strokeWidth="1"
                    />
                    <text
                      x={x}
                      y={y - 16}
                      fill="#f8fafc"
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {p.name.length > 13 ? `${p.name.substring(0, 11)}..` : p.name}
                    </text>
                  </g>
                );
              })}
            </g>
          )}
        </svg>
      </div>

      {/* Hover Info Tooltip */}
      {hoveredPanchayat && (
        <div className="absolute top-4 left-4 bg-slate-900/95 backdrop-blur-md border border-slate-700 px-4 py-3 rounded-xl shadow-xl pointer-events-none text-xs z-20">
          <div className="flex items-center gap-2 mb-1">
            <MapPin className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-bold text-white text-sm">{hoveredPanchayat.name}</span>
          </div>
          <div className="text-slate-400 space-y-0.5">
            <div>Block: <span className="text-slate-200">{hoveredPanchayat.block_name || 'Ayodhya District'}</span></div>
            <div>
              1-km Downscaled Temp:{' '}
              <span className="text-emerald-400 font-mono font-bold">
                {hoveredPanchayat.latest_weather?.tmean_c?.toFixed(1) || 29.5}°C
              </span>
            </div>
            <div>
              Cropland:{' '}
              <span className="text-slate-200">
                {hoveredPanchayat.is_cropland_eligible ? 'Eligible' : 'Non-Cropland'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Layer Control Panel (Top Right) */}
      <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-xl p-3 shadow-xl z-20 space-y-2 text-xs">
        <div className="flex items-center gap-2 font-bold text-slate-300 pb-2 border-b border-slate-800">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>GIS Layer Controls</span>
        </div>

        <button
          onClick={() => setShowGridOverlay(!showGridOverlay)}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all ${
            showGridOverlay
              ? 'bg-emerald-950/50 text-emerald-300 border-emerald-500/40'
              : 'bg-slate-800/50 text-slate-400 border-slate-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <Grid className="w-3.5 h-3.5" />
            1-km Spatial Grid
          </span>
          {showGridOverlay ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        <button
          onClick={() => setShowRiskHeatmap(!showRiskHeatmap)}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all ${
            showRiskHeatmap
              ? 'bg-amber-950/50 text-amber-300 border-amber-500/40'
              : 'bg-slate-800/50 text-slate-400 border-slate-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <Flame className="w-3.5 h-3.5" />
            Thermal Heatmap
          </span>
          {showRiskHeatmap ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        <button
          onClick={() => setShowPanchayatMarkers(!showPanchayatMarkers)}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all ${
            showPanchayatMarkers
              ? 'bg-sky-950/50 text-sky-300 border-sky-500/40'
              : 'bg-slate-800/50 text-slate-400 border-slate-700'
          }`}
        >
          <span className="flex items-center gap-2">
            <MapPin className="w-3.5 h-3.5" />
            Panchayat Markers
          </span>
          {showPanchayatMarkers ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Floating 1-km Cell Inspector Modal */}
      {inspectedCell && (
        <div className="absolute bottom-4 left-4 z-30">
          <GridCellInspector cell={inspectedCell} onClose={() => setInspectedCell(null)} />
        </div>
      )}

      {/* Map Legend (Bottom Right) */}
      <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-xl p-3 shadow-xl z-20 text-[11px] text-slate-300 space-y-1.5">
        <span className="font-bold text-[10px] text-slate-400 uppercase tracking-wider block">
          Downscaled Temp Scale
        </span>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span>&gt;36°C (Extreme)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>32–36°C</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>&lt;32°C (Optimal)</span>
          </div>
        </div>
      </div>

      {/* Zoom / Navigation Controls (Top Left) */}
      <div className="absolute top-4 left-4 flex flex-col gap-1.5 z-20">
        <button
          onClick={zoomIn}
          className="w-8 h-8 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-center shadow-lg transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          className="w-8 h-8 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-center shadow-lg transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={resetView}
          className="w-8 h-8 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-center shadow-lg transition-colors"
          title="Reset View"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
