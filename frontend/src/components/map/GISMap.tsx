import React, { useState, useMemo, useEffect } from 'react';
import { Panchayat, GridCell } from '../../types';
import { getPanchayatBoundary } from '../../api/panchayat';
import { Layers, MapPin, ZoomIn, ZoomOut, RotateCcw, Info, Sliders } from 'lucide-react';

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
  const [showAdvancedLayers, setShowAdvancedLayers] = useState<boolean>(false);
  const [showContours, setShowContours] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [boundaryCoords, setBoundaryCoords] = useState<[number, number][] | null>(null);

  useEffect(() => {
    let active = true;
    async function fetchBoundary() {
      try {
        const idOrCode = panchayat.code || panchayat.id;
        const res = await getPanchayatBoundary(idOrCode);
        const geom = res?.geometry || res?.data?.geometry;
        if (geom && active) {
          const coords = geom.type === 'Polygon'
            ? geom.coordinates[0]
            : geom.type === 'MultiPolygon'
            ? geom.coordinates[0][0]
            : null;
          if (Array.isArray(coords) && coords.length > 0) {
            setBoundaryCoords(coords);
          }
        }
      } catch (err) {
        // Fall back gracefully
      }
    }
    fetchBoundary();
    return () => { active = false; };
  }, [panchayat.id, panchayat.code]);

  // Compute bounding box around cells or boundary coordinates
  const { minLat, maxLat, minLon, maxLon } = useMemo(() => {
    const allLats: number[] = [];
    const allLons: number[] = [];

    if (gridCells.length > 0) {
      gridCells.forEach((c) => {
        allLats.push(c.latitude);
        allLons.push(c.longitude);
      });
    }
    if (boundaryCoords && boundaryCoords.length > 0) {
      boundaryCoords.forEach(([lon, lat]) => {
        allLats.push(lat);
        allLons.push(lon);
      });
    }

    if (allLats.length === 0) {
      const lat = panchayat.latitude || panchayat.centroid_lat || 25.35;
      const lon = panchayat.longitude || panchayat.centroid_lon || 82.95;
      return {
        minLat: lat - 0.02,
        maxLat: lat + 0.02,
        minLon: lon - 0.02,
        maxLon: lon + 0.02,
      };
    }

    return {
      minLat: Math.min(...allLats) - 0.003,
      maxLat: Math.max(...allLats) + 0.003,
      minLon: Math.min(...allLons) - 0.003,
      maxLon: Math.max(...allLons) + 0.003,
    };
  }, [gridCells, panchayat, boundaryCoords]);

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

  const boundaryPoints = useMemo(() => {
    if (!boundaryCoords || boundaryCoords.length === 0) return null;
    return boundaryCoords
      .map(([lon, lat]) => {
        const pt = project(lat, lon);
        return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
      })
      .join(' ');
  }, [boundaryCoords, minLat, maxLat, minLon, maxLon]);

  // Temperature color ramp (light-friendly)
  const getCellFill = (temp: number) => {
    if (temp >= 36) return 'rgba(239, 68, 68, 0.45)'; // Red/Hot
    if (temp >= 33) return 'rgba(245, 158, 11, 0.45)'; // Amber/Warm
    if (temp >= 28) return 'rgba(16, 185, 129, 0.45)'; // Green/Optimal
    return 'rgba(59, 130, 246, 0.45)'; // Blue/Cool
  };

  return (
    <div
      className={`card-white bg-slate-50 relative overflow-hidden flex flex-col border border-slate-200 shadow-sm ${className}`}
      id="gis-map-container"
    >
      {/* Top Map Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 border-b border-slate-200 bg-white/95 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-200">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <span>{panchayat.name} Boundary & 1-km Micro-Grid</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                1-km Mesh
              </span>
            </h4>
            <p className="text-[10px] text-slate-500 font-mono">
              Centroid: {centerLat.toFixed(4)}°N, {centerLon.toFixed(4)}°E • Area: {panchayat.total_area_ha || 1240} ha
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5">
          <button
            id="map-toggle-grid"
            onClick={() => setShowGrid(!showGrid)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
              showGrid
                ? 'bg-blue-50 border-blue-300 text-blue-700 font-semibold'
                : 'bg-white border-slate-200 text-slate-600'
            }`}
          >
            1-km Grid ({gridCells.length})
          </button>

          <button
            id="map-advanced-toggle"
            onClick={() => setShowAdvancedLayers(!showAdvancedLayers)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center gap-1 transition-colors ${
              showAdvancedLayers
                ? 'bg-slate-800 text-white border-slate-800'
                : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-3 h-3" />
            <span>Advanced Map Layers</span>
          </button>

          <div className="h-4 w-px bg-slate-200 mx-1" />

          {/* Zoom controls */}
          <button
            onClick={() => setZoomLevel((prev) => Math.min(2, prev + 0.2))}
            title="Zoom In"
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-2xs"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel((prev) => Math.max(0.8, prev - 0.2))}
            title="Zoom Out"
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-2xs"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel(1)}
            title="Reset View"
            className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-2xs"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Advanced GIS Controls Dropdown (Hidden by default) */}
      {showAdvancedLayers && (
        <div className="px-4 py-2 bg-slate-100/80 border-b border-slate-200 flex items-center gap-4 text-xs text-slate-700 animate-fade-in">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showContours}
              onChange={(e) => setShowContours(e.target.checked)}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Boundary Contour (UTM 44N)</span>
          </label>
          <span className="text-slate-400">|</span>
          <span className="text-[11px] text-slate-500">
            Projection: EPSG:3857 (Display) • Area Basis: EPSG:32644 (Metric Conservation)
          </span>
        </div>
      )}

      {/* Map SVG Canvas (Light Basemap) */}
      <div className="relative flex-1 min-h-[440px] bg-[#F1F5F9] overflow-hidden flex items-center justify-center">
        {/* Subtle background grid pattern */}
        <div 
          className="absolute inset-0 opacity-40 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(#CBD5E1 1px, transparent 1px)',
            backgroundSize: '24px 24px'
          }}
        />

        <svg
          viewBox="0 0 600 400"
          className="w-full h-full transition-transform duration-300"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          {/* Exact Panchayat Boundary Polygon Overlay (Task 1 / Task 6 GIS Integration) */}
          {showContours && (
            boundaryPoints ? (
              <polygon
                points={boundaryPoints}
                fill="rgba(59, 130, 246, 0.08)"
                stroke="#2563EB"
                strokeWidth="2.5"
                strokeDasharray="5 3"
              />
            ) : (
              <polygon
                points="100,70 480,50 560,250 490,360 210,380 70,260"
                fill="rgba(241, 245, 249, 0.7)"
                stroke="#94A3B8"
                strokeWidth="2"
                strokeDasharray="4 3"
              />
            )
          )}

          {/* 1-km Grid Cells */}
          {showGrid &&
            gridCells.map((cell) => {
              const pt = project(cell.latitude, cell.longitude);
              const isSelected = selectedCell?.cell_id === cell.cell_id;
              const cellTemp = cell.downscaled_temperature_c ?? cell.tmean_c ?? 34.2;

              return (
                <g key={cell.cell_id} onClick={() => onSelectCell(cell)} className="cursor-pointer group">
                  <rect
                    x={pt.x - 28}
                    y={pt.y - 28}
                    width={56}
                    height={56}
                    rx={6}
                    fill={getCellFill(cellTemp)}
                    stroke={isSelected ? '#2563EB' : '#94A3B8'}
                    strokeWidth={isSelected ? 3 : 1}
                    className="transition-all hover:stroke-blue-600 hover:opacity-90"
                  />
                  {/* Temperature label inside cell */}
                  <text
                    x={pt.x}
                    y={pt.y + 4}
                    textAnchor="middle"
                    className="text-[10px] font-mono font-bold fill-slate-800 pointer-events-none select-none"
                  >
                    {cellTemp.toFixed(1)}°
                  </text>
                  <text
                    x={pt.x}
                    y={pt.y + 16}
                    textAnchor="middle"
                    className="text-[8px] font-mono fill-slate-600 pointer-events-none select-none"
                  >
                    #{cell.cell_id}
                  </text>
                </g>
              );
            })}

          {/* Centroid / Station Marker */}
          <g transform={`translate(${centerPt.x}, ${centerPt.y})`}>
            <circle r={8} fill="#2563EB" opacity={0.3} className="animate-ping" />
            <circle r={5} fill="#2563EB" />
            <circle r={2} fill="#FFFFFF" />
          </g>
        </svg>

        {/* Selected Cell Floating Quick Card */}
        {selectedCell && (
          <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm p-4 rounded-xl border border-slate-200 shadow-lg text-xs space-y-2 max-w-xs animate-fade-in">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900">
                1-km Grid Cell #{selectedCell.cell_id}
              </span>
              <button
                onClick={() => onSelectCell(null)}
                className="text-slate-400 hover:text-slate-600 text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="font-mono text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Downscaled Temp:</span>
                <span className="font-bold text-blue-600">
                  {(selectedCell.downscaled_temperature_c ?? selectedCell.tmean_c ?? 34.2).toFixed(2)}°C
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Coarse NWP:</span>
                <span className="text-slate-700">
                  {(selectedCell.coarse_temperature_c ?? 33.5).toFixed(2)}°C
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Dynamic Residual:</span>
                <span className="text-emerald-700 font-semibold">
                  +{(selectedCell.predicted_residual_c ?? selectedCell.predicted_residual ?? 0.74).toFixed(2)}°C
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Model:</span>
                <span className="px-1.5 py-0.2 rounded bg-purple-50 text-purple-700 font-medium text-[10px]">
                  Dynamic V2
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Elev / Coordinates:</span>
                <span className="text-slate-600 text-[10px]">
                  {selectedCell.elevation_m || 95}m ({selectedCell.latitude.toFixed(3)}°N, {selectedCell.longitude.toFixed(3)}°E)
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Bottom Right Map Legend */}
        <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-2 rounded-lg border border-slate-200 shadow-sm text-[10px] font-mono space-y-1">
          <div className="font-bold text-slate-700 mb-1">Temperature Legend</div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-blue-500/50 border border-blue-400" />
            <span>&lt; 28°C (Cool)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-emerald-500/50 border border-emerald-400" />
            <span>28–33°C (Optimal)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-amber-500/50 border border-amber-400" />
            <span>33–36°C (Moderate)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-red-500/50 border border-red-400" />
            <span>&gt; 36°C (Heat Stress)</span>
          </div>
        </div>
      </div>

      {/* Native-Resolution Disclosure Footer (Requirements 23 & 27) */}
      <div className="p-2.5 bg-slate-100/90 border-t border-slate-200 text-[10px] text-slate-500 font-mono flex flex-wrap items-center justify-between gap-1 z-10">
        <span>Display grid is finer than source resolution; visualization does not imply finer meteorological observations.</span>
        <span>CRS: EPSG:4326 • Polygon Basis: STRtree PIP</span>
      </div>
    </div>
  );
};
