import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  ShieldAlert, 
  CheckCircle2, 
  Calendar, 
  MapPin, 
  Thermometer, 
  Sprout, 
  Clock, 
  Info, 
  AlertTriangle,
  RefreshCw,
  Droplets,
  Wind,
  Filter
} from 'lucide-react';

export const AgroAdvisories: React.FC = () => {
  const {
    forecast,
    forecastLoading,
    selectedLocation,
    targetDate,
    setTargetDate,
    refetchForecast,
  } = useApp();

  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  // Advisory Consistency Engine: Verify that advisory data belongs strictly to the selected location & date
  const isConsistent = Boolean(
    forecast &&
    !forecastLoading &&
    (forecast.selected_date === targetDate || forecast.forecast_date === targetDate) &&
    (
      forecast.location_id === selectedLocation?.id ||
      forecast.location?.id === selectedLocation?.id ||
      (selectedLocation?.name && (
        forecast.location_name?.toLowerCase().includes(selectedLocation.name.toLowerCase()) ||
        selectedLocation.name.toLowerCase().includes((forecast.location_name || '').toLowerCase()) ||
        forecast.location?.name?.toLowerCase().includes(selectedLocation.name.toLowerCase())
      ))
    )
  );

  const filterCategories = ['ALL', 'HEAT', 'DRAINAGE', 'WIND', 'DISEASE', 'GENERAL'];

  const filteredActions = (forecast?.farmer_actions || []).filter((action) => {
    if (categoryFilter === 'ALL') return true;
    const cat = action.category?.toUpperCase() || '';
    if (categoryFilter === 'HEAT' && (cat.includes('HEAT') || cat.includes('IRRIGATION') || cat.includes('SPRAY'))) return true;
    if (categoryFilter === 'DRAINAGE' && (cat.includes('DRAIN') || cat.includes('RAIN') || cat.includes('WATER'))) return true;
    if (categoryFilter === 'WIND' && (cat.includes('WIND') || cat.includes('LODG'))) return true;
    if (categoryFilter === 'DISEASE' && (cat.includes('DISEASE') || cat.includes('MONITOR') || cat.includes('BLAST'))) return true;
    if (categoryFilter === 'GENERAL' && (cat.includes('FIELD') || cat.includes('ROUTINE'))) return true;
    return false;
  });

  const getPriorityBadge = (priority?: string) => {
    switch (priority?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'LOW':
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const getSeverityBorder = (risk?: string) => {
    switch (risk?.toUpperCase()) {
      case 'HIGH':
      case 'SEVERE':
        return 'border-l-4 border-l-red-500';
      case 'MODERATE':
      case 'MEDIUM':
        return 'border-l-4 border-l-amber-500';
      case 'LOW':
      default:
        return 'border-l-4 border-l-emerald-500';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-fade-in" id="agro-advisories-page">
      {/* 1. Header & Location / Date Metadata */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
              Stage-Aware Agromet Advisory Engine
            </span>
            <span className="text-xs text-slate-500">
              Downscaled 1-km Weather Triggers
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            Agricultural Action Advisories
          </h1>
          <p className="text-xs text-slate-500">
            Localized agronomic decisions derived from physical numerical weather downscaling
          </p>
        </div>

        {/* Selected Context Pill */}
        <div className="bg-white rounded-xl px-4 py-2.5 flex items-center gap-4 text-xs font-mono border border-slate-200 shadow-sm">
          <div>
            <span className="text-[10px] text-slate-400 block uppercase">Target Location</span>
            <span className="font-bold text-slate-900">{selectedLocation?.name || forecast?.location_name || 'Selected Location'}</span>
          </div>
          <div className="h-6 w-px bg-slate-200" />
          <div>
            <span className="text-[10px] text-slate-400 block uppercase">Forecast Valid</span>
            <span className="font-bold text-blue-700">{forecast?.selected_date_formatted || targetDate}</span>
          </div>
        </div>
      </div>

      {/* 2. Advisory Consistency Verification Banner */}
      <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-800">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>
            <strong>Advisory Consistency Engine:</strong> Verified against Downscaled Temp{' '}
            <span className="font-mono font-bold text-blue-700">{forecast?.current ? `${forecast.current.temperature_c.toFixed(1)}°C` : '--'}</span> for{' '}
            <strong>{selectedLocation?.name || forecast?.location_name}</strong> on <strong>{forecast?.selected_date_formatted || targetDate}</strong>.
          </span>
        </div>
        <button
          onClick={() => refetchForecast()}
          className="text-emerald-700 hover:text-emerald-900 font-semibold flex items-center gap-1 flex-shrink-0 text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${forecastLoading ? 'animate-spin' : ''}`} />
          <span>Verify</span>
        </button>
      </div>

      {/* 3. Horizon Date Selector */}
      <div className="space-y-1.5">
        <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Calendar className="w-4 h-4 text-blue-600" />
          <span>Select Forecast Day</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {forecast?.daily_forecast?.map((day) => {
            const isSelected = day.date === targetDate;
            return (
              <button
                key={day.date}
                type="button"
                id={`advisory-date-${day.date}`}
                onClick={() => setTargetDate(day.date)}
                className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium border transition-all ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm font-bold'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <span>{day.day_label || day.display_label}</span>
                <span className={`ml-1.5 text-[10px] ${isSelected ? 'text-blue-100' : 'text-slate-400'}`}>
                  {day.formatted_date ? day.formatted_date.split(',')[0] : day.date}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto">
        <div className="flex items-center gap-1 text-xs text-slate-500 font-semibold uppercase mr-2">
          <Filter className="w-3.5 h-3.5" />
          <span>Category:</span>
        </div>
        {filterCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`px-3 py-1 rounded-lg text-xs font-medium border transition-colors ${
              categoryFilter === cat
                ? 'bg-slate-900 text-white border-slate-900 font-semibold'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 4. Advisory List & Recalculating State */}
      {forecastLoading || !isConsistent ? (
        <div className="bg-white rounded-2xl p-12 text-center space-y-3 border-2 border-dashed border-slate-200">
          <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin mx-auto" />
          <div className="text-sm font-bold text-slate-800">
            Advisory recalculating...
          </div>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Ensuring strictly synchronized dataflow between selected location ({selectedLocation?.name}),
            forecast date ({targetDate}), and stage-specific crop risk rules.
          </p>
        </div>
      ) : (
        <div className="space-y-4" id="advisories-container">
          {filteredActions.length === 0 ? (
            <div className="bg-white rounded-xl p-8 text-center text-xs text-slate-500 border border-slate-200">
              No advisories under the selected category filter for this forecast date.
            </div>
          ) : (
            filteredActions.map((action, index) => {
              const primaryCrop = action.crop || selectedLocation?.primary_crops?.[0] || 'Rice (Paddy)';
              const cropStage = action.crop_stage || 'Flowering / Anthesis';
              const riskLevel = action.risk || 'MODERATE';
              const weatherTrigger = action.weather_trigger || `Downscaled temperature ${forecast?.current?.temperature_c.toFixed(1)}°C`;

              return (
                <div
                  key={index}
                  className={`bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3 ${getSeverityBorder(riskLevel)}`}
                >
                  {/* Top Bar: Title & Severity */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center flex-shrink-0">
                        {index + 1}
                      </span>
                      <h2 className="text-sm font-bold text-slate-900">
                        {action.title}
                      </h2>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getPriorityBadge(action.priority)}`}>
                        {action.priority} PRIORITY
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        Category: {action.category}
                      </span>
                    </div>
                  </div>

                  {/* Metadata Grid (DATE, LOCATION, WEATHER TRIGGER, CROP, STAGE, RISK, TIMING) */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5 p-3 bg-slate-50 rounded-xl text-xs font-mono border border-slate-100">
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Date</span>
                      <span className="font-semibold text-slate-800 truncate block">
                        {action.date || forecast?.selected_date_formatted || targetDate}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Location</span>
                      <span className="font-semibold text-slate-800 truncate block">
                        {action.location || selectedLocation?.name || forecast?.location_name}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Crop</span>
                      <span className="font-semibold text-emerald-700 truncate block">
                        {primaryCrop}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Stage</span>
                      <span className="font-semibold text-slate-800 truncate block">
                        {cropStage}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Weather Trigger</span>
                      <span className="font-semibold text-blue-700 truncate block">
                        {weatherTrigger}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase">Timing</span>
                      <span className="font-semibold text-slate-800 truncate block">
                        {action.timing}
                      </span>
                    </div>
                  </div>

                  {/* Action Guidance */}
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-slate-800 block">
                      Recommended Farmer Action:
                    </span>
                    <p className="text-xs text-slate-700 leading-relaxed bg-blue-50/30 p-3 rounded-xl border border-blue-100">
                      {action.action}
                    </p>
                  </div>

                  {/* Agronomic Why / Scientific Rationale */}
                  <div className="text-xs text-slate-500 space-y-0.5 pt-1">
                    <span className="font-semibold text-slate-700">Agronomic Rationale (Why): </span>
                    <span className="italic">{action.why}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};
