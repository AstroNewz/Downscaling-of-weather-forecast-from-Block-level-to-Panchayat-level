import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Layers, 
  MapPin, 
  Grid, 
  Info, 
  Filter, 
  ArrowRight,
  Flame,
  Sprout
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { GISMap } from '../components/map/GISMap';
import { Panchayat, GridCell } from '../types';

export const GisMapPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBlockId } = useApp();

  const [panchayats, setPanchayats] = useState<Panchayat[]>([]);
  const [gridCells, setGridCells] = useState<GridCell[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadMapData = async () => {
      setLoading(true);
      try {
        const [pData, gData] = await Promise.all([
          api.getPanchayats(selectedBlockId || undefined),
          api.getGridCells(selectedBlockId || undefined),
        ]);
        setPanchayats(pData);
        setGridCells(gData);
      } catch (err) {
        console.error('Failed to load GIS map data', err);
      } finally {
        setLoading(false);
      }
    };

    loadMapData();
  }, [selectedBlockId]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono">
              1-km ML RESOLUTION
            </span>
            <span className="text-xs text-slate-400">SRTM 30m DEM + Sentinel-2 LULC</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Spatial GIS Agro-Meteorological Map
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Interactive high-resolution 1-km thermal downscaled grid, administrative boundaries & risk heatmaps.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-300 flex items-center gap-2">
            <Grid className="w-4 h-4 text-emerald-400" />
            <span>Click any 1-km cell or marker to inspect</span>
          </div>
        </div>
      </div>

      {/* Main Map Canvas */}
      <GISMap
        panchayats={panchayats}
        gridCells={gridCells}
        height="650px"
        onSelectPanchayat={(p) => navigate(`/panchayats/${p.id}`)}
      />

      {/* Scientific Explainer Callout */}
      <div className="glass-card rounded-2xl p-5 border border-slate-700/60 shadow-xl flex flex-col md:flex-row items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
          <Info className="w-5 h-5" />
        </div>
        <div className="text-xs space-y-1">
          <h4 className="text-sm font-bold text-white">
            Downscaling Methodology & Spatial Provenance
          </h4>
          <p className="text-slate-300 leading-relaxed">
            Temperature fields are generated at 1-km metric resolution by applying our trained XGBoost residual model ($T_{downscaled} = T_{coarse} + \hat{R}$) across SRTM elevation, slope, aspect, and vegetation cover. Rainfall is propagated from the coarse block forecast. Panchayat statistics are computed via area-weighted spatial intersection.
          </p>
        </div>
      </div>
    </div>
  );
};
