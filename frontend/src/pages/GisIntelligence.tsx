import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getGridCells } from '../api/weather';
import { GridCell } from '../types';
import { GISMap } from '../components/map/GISMap';
import { LoadingState } from '../components/common/LoadingState';
import { MapPin, Layers, Info } from 'lucide-react';

export const GisIntelligence: React.FC = () => {
  const {
    panchayats,
    selectedPanchayatId,
    setSelectedPanchayatId,
    selectedPanchayat,
    selectedLocation,
  } = useApp();

  const [gridCells, setGridCells] = useState<GridCell[]>([]);
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!selectedPanchayatId) return;

    let isMounted = true;
    async function loadCells() {
      try {
        setLoading(true);
        setSelectedCell(null);

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
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in" id="gis-intelligence-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              1-km Micro-Grid GIS
            </span>
            <span className="text-xs text-slate-500 font-mono">
              EPSG:32644 Area-Conserving Mesh
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            Geospatial Micro-Climate Grid
          </h1>
          <p className="text-xs text-slate-500">
            Click any 1-km cell to inspect downscaled thermal residuals, elevation, and model outputs
          </p>
        </div>

        {/* Target Panchayat Selector */}
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs shadow-2xs">
          <span className="text-slate-500 font-medium">Target:</span>
          <select
            id="gis-panchayat-select"
            value={selectedPanchayatId || ''}
            onChange={(e) => setSelectedPanchayatId(Number(e.target.value))}
            className="bg-transparent text-slate-900 font-bold focus:outline-none cursor-pointer"
          >
            {panchayats.map((p) => (
              <option key={p.id} value={p.id} className="bg-white text-slate-900">
                {p.name} ({p.block_name || 'Varanasi'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Map */}
      <div>
        {loading ? (
          <LoadingState message="Loading geospatial polygon layers & 1-km cells..." variant="card" />
        ) : currentPanchayat ? (
          <GISMap
            panchayat={currentPanchayat}
            gridCells={gridCells}
            selectedCell={selectedCell}
            onSelectCell={(cell: GridCell | null) => setSelectedCell(cell)}
            className="min-h-[520px]"
          />
        ) : null}
      </div>

      {/* Geospatial Governance Metadata Footer */}
      <div className="card-white p-4 bg-slate-50/60 border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="space-y-1">
          <span className="text-slate-400 uppercase text-[10px] font-semibold">Geometric Projection</span>
          <p className="text-slate-700">
            UTM Zone 44N (EPSG:32644) ensures strict metric area conservation (m²) during polygon intersection.
          </p>
        </div>
        <div className="space-y-1">
          <span className="text-slate-400 uppercase text-[10px] font-semibold">Display Projection</span>
          <p className="text-slate-700">
            EPSG:3857 (Spherical Mercator) utilized strictly for interactive UI rendering to prevent spatial distortion.
          </p>
        </div>
        <div className="space-y-1">
          <span className="text-slate-400 uppercase text-[10px] font-semibold">Thermal Calibration</span>
          <p className="text-emerald-700 font-bold">
            T_calibrated = T_coarse + 0.7351°C applied to each intersected 1-km micro-cell.
          </p>
        </div>
      </div>
    </div>
  );
};
