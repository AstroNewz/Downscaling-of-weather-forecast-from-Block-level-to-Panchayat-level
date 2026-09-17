import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getGridCells } from '../api/weather';
import { GridCell } from '../types';
import { GISMap } from '../components/map/GISMap';
import { GridCellInspector } from '../components/map/GridCellInspector';
import { LoadingState } from '../components/common/LoadingState';
import { MapPin, Layers, Info, ShieldCheck, Compass } from 'lucide-react';

export const GisIntelligence: React.FC = () => {
  const {
    panchayats,
    selectedPanchayatId,
    setSelectedPanchayatId,
    selectedPanchayat,
  } = useApp();

  const [gridCells, setGridCells] = useState<GridCell[]>([]);
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // When Panchayat selection changes, fetch its grid cells and reset inspector
  useEffect(() => {
    if (!selectedPanchayatId) return;

    let isMounted = true;
    async function loadCells() {
      try {
        setLoading(true);
        setSelectedCell(null); // Reset inspector on change

        const cells = await getGridCells(selectedPanchayatId!);
        if (isMounted) {
          setGridCells(cells);
        }
      } catch (err) {
        console.error('Failed to load GIS grid cells:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadCells();
    return () => {
      isMounted = false;
    };
  }, [selectedPanchayatId]);

  const currentPanchayat = selectedPanchayat || panchayats[0];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">
              Geospatial 1-km Micro-Grid Intelligence
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-0.5 font-mono">
            Metric Projection: Local UTM (EPSG:32644) Area Weighted • Resolution: 1000m x 1000m
          </p>
        </div>

        {/* Global Panchayat Switcher inside GIS */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs">
          <span className="text-slate-400">Panchayat Target:</span>
          <select
            id="gis-panchayat-select"
            value={selectedPanchayatId || ''}
            onChange={(e) => setSelectedPanchayatId(Number(e.target.value))}
            className="bg-transparent text-emerald-400 font-bold focus:outline-none cursor-pointer"
          >
            {panchayats.map((p) => (
              <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                {p.name} ({p.block_name || 'Dhar'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Map & Inspector Canvas */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Map Canvas (8 or 12 cols) */}
        <div className={selectedCell ? 'lg:col-span-8' : 'lg:col-span-12'}>
          {loading ? (
            <LoadingState message="Loading geospatial polygon layers & 1-km cells..." variant="card" />
          ) : currentPanchayat ? (
            <GISMap
              panchayat={currentPanchayat}
              gridCells={gridCells}
              selectedCell={selectedCell}
              onSelectCell={(cell: GridCell | null) => setSelectedCell(cell)}
              className="min-h-[500px]"
            />
          ) : null}
        </div>

        {/* Side Inspector Panel (4 cols when active) */}
        {selectedCell && (
          <div className="lg:col-span-4">
            <GridCellInspector
              cell={selectedCell}
              onClose={() => setSelectedCell(null)}
              panchayatName={currentPanchayat?.name || 'Selected'}
            />
          </div>
        )}
      </div>

      {/* Geospatial Governance Metadata Footer */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 bg-slate-900/40 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Geometric Transformation</span>
          <p className="text-slate-300">
            UTM Zone 44N (EPSG:32644) ensures strict metric area conservation (m²) during polygon intersection.
          </p>
        </div>
        <div className="space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Web Map Projection</span>
          <p className="text-slate-300">
            EPSG:3857 (Spherical Mercator) utilized strictly for interactive UI rendering to prevent spatial distortion.
          </p>
        </div>
        <div className="space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Thermal Calibration</span>
          <p className="text-emerald-400 font-semibold">
            T_calibrated = T_coarse + 0.7351°C applied to each intersected 1-km micro-cell.
          </p>
        </div>
      </div>
    </div>
  );
};
