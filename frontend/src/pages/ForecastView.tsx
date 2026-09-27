import React from 'react';
import { useApp } from '../context/AppContext';
import { LocalizedPrecipitationOutlook } from '../components/weather/LocalizedPrecipitationOutlook';
import { 
  Calendar, 
  CloudRain, 
  Sun, 
  Cloud, 
  Wind, 
  Droplets, 
  ShieldCheck, 
  CheckCircle2, 
  Info,
  Clock,
  Sparkles
} from 'lucide-react';

export const ForecastView: React.FC = () => {
  const {
    forecast,
    forecastLoading,
    selectedLocation,
    targetDate,
    setTargetDate,
    todayDate,
    viewMode,
  } = useApp();

  const renderIcon = (name?: string, size = 'w-6 h-6') => {
    switch (name) {
      case 'sun': return <Sun className={`${size} text-amber-500`} />;
      case 'cloud': return <Cloud className={`${size} text-slate-400`} />;
      case 'cloud-rain': return <CloudRain className={`${size} text-blue-500`} />;
      default: return <Sun className={`${size} text-amber-500`} />;
    }
  };

  const selectedDayCard = forecast?.daily_forecast?.find((d) => d.date === targetDate) || forecast?.daily_forecast?.[0];

  return (
    <div className="space-y-6 pb-12 animate-fade-in" id="forecast-view-page">
      {/* 1. Header with Location & Date Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              Operational NWP Downscaling
            </span>
            <span className="text-xs text-slate-500">
              Panchayat 1-km Micro-Climate Horizon
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            {selectedLocation?.name || 'Selected Location'} Forecast
          </h1>
          <p className="text-xs text-slate-500">
            {selectedLocation?.district_name || 'Varanasi'}, {selectedLocation?.state_name || 'Uttar Pradesh'} • Elevation: {selectedLocation?.elevation_m || 95}m
          </p>
        </div>

        {/* Forecast Metadata Pill */}
        <div className="card-white px-3 py-2 text-xs flex items-center gap-3 font-mono bg-slate-50/70 border-slate-200">
          <div>
            <span className="text-slate-400 text-[10px] block">Requested Date:</span>
            <span className="font-bold text-slate-800">{forecast?.selected_date || targetDate}</span>
          </div>
          <div className="h-6 w-px bg-slate-200" />
          <div>
            <span className="text-slate-400 text-[10px] block">Forecast Valid:</span>
            <span className="font-bold text-emerald-700">{forecast?.selected_date_formatted || targetDate}</span>
          </div>
        </div>
      </div>

      {/* 2. 7-Day Interactive Horizon Selector */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-700 uppercase tracking-wider">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4 text-blue-600" />
            7-Day Operational Horizon
          </span>
          <span className="text-slate-400 font-normal">Click any day to update hourly view</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          {forecast?.daily_forecast?.map((day) => {
            const isSelected = day.date === targetDate;
            return (
              <button
                key={day.date}
                type="button"
                id={`forecast-day-btn-${day.date}`}
                onClick={() => setTargetDate(day.date)}
                className={`p-3 rounded-xl border text-center space-y-2 transition-all text-left ${
                  isSelected
                    ? 'border-blue-600 ring-2 ring-blue-500/20 bg-blue-50/30'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-xs text-slate-900">{day.day_label}</span>
                  {day.is_today && (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 bg-blue-100 text-blue-800 rounded">
                      TODAY
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500">
                  {day.formatted_date.split(',')[0]}
                </div>

                <div className="flex justify-center py-1">
                  {renderIcon(day.icon_name, 'w-6 h-6')}
                </div>

                <div className="text-xs font-bold text-slate-900 font-mono text-center">
                  {day.t_max_c}° / <span className="text-slate-400 font-normal">{day.t_min_c}°</span>
                </div>

                <div className="text-[10px] text-blue-600 font-medium text-center">
                  {day.precip_probability_pct}% rain ({day.precip_sum_mm}mm)
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2b. Localized Precipitation Outlook (Task 6 Observation-Fusion Integration) */}
      <LocalizedPrecipitationOutlook
        nowcast={forecast?.precipitation_nowcast}
        baselineRainfallMm={selectedDayCard?.precip_sum_mm ?? forecast?.current?.precipitation_mm ?? 0}
        baselineProbabilityPct={selectedDayCard?.precip_probability_pct ?? 0}
        panchayatName={selectedLocation?.name}
        panchayatId={selectedLocation?.id}
        blockName={selectedLocation?.block_name}
        districtName={selectedLocation?.district_name}
        targetDate={targetDate}
        isToday={targetDate === todayDate}
        viewMode={viewMode}
      />

      {/* 3. Selected Day Summary Banner */}
      {selectedDayCard && (
        <div className="card-white p-5 bg-gradient-to-r from-blue-50/40 via-white to-emerald-50/30 border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
                Day Overview
              </span>
              <h2 className="text-xl font-bold text-slate-900">
                {selectedDayCard.day_label}, {selectedDayCard.formatted_date}
              </h2>
              <div className="text-xs text-slate-600 flex items-center gap-2">
                {renderIcon(selectedDayCard.icon_name, 'w-4 h-4')}
                <span className="font-medium">{selectedDayCard.condition_text}</span>
              </div>
            </div>

            <div className="flex items-center gap-6 font-mono">
              <div className="text-center">
                <span className="text-[10px] text-slate-400 uppercase">Max Temp</span>
                <div className="text-2xl font-black text-slate-900">{selectedDayCard.t_max_c}°C</div>
              </div>
              <div className="text-center">
                <span className="text-[10px] text-slate-400 uppercase">Min Temp</span>
                <div className="text-2xl font-black text-slate-600">{selectedDayCard.t_min_c}°C</div>
              </div>
              <div className="text-center">
                <span className="text-[10px] text-slate-400 uppercase">Precipitation</span>
                <div className="text-2xl font-black text-blue-600">{selectedDayCard.precip_sum_mm} mm</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Full 24-Hour Diurnal Curve & Hourly Schedule */}
      <div className="card-white p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Full 24-Hour Downscaled Diurnal Schedule
            </h2>
            <p className="text-xs text-slate-500">
              Hour-by-hour physical downscaling for {forecast?.selected_date_label || targetDate}
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {forecast?.full_hourly?.length ?? 24} Forecast Hours
          </span>
        </div>

        {forecastLoading ? (
          <div className="space-y-2 py-4">
            <div className="skeleton h-12 w-full" />
            <div className="skeleton h-12 w-full" />
            <div className="skeleton h-12 w-full" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 font-mono text-[11px] bg-slate-50/50">
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Condition</th>
                  <th className="py-2.5 px-3 text-right">Downscaled Temp</th>
                  {viewMode === 'TECHNICAL' && (
                    <>
                      <th className="py-2.5 px-3 text-right">Coarse NWP</th>
                      <th className="py-2.5 px-3 text-right">Dynamic Residual</th>
                      <th className="py-2.5 px-3">Model</th>
                    </>
                  )}
                  <th className="py-2.5 px-3 text-right">Rain Prob</th>
                  <th className="py-2.5 px-3 text-right">Precip</th>
                  <th className="py-2.5 px-3 text-right">Humidity</th>
                  <th className="py-2.5 px-3 text-right">Wind</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {forecast?.full_hourly?.map((h, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-bold text-slate-800 flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{h.local_time}</span>
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="flex items-center gap-1.5">
                        {renderIcon(h.icon_name, 'w-4 h-4')}
                        <span className="text-slate-700">{h.condition_text}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900 text-sm">
                      {h.downscaled_temperature_c.toFixed(1)}°C
                    </td>
                    {viewMode === 'TECHNICAL' && (
                      <>
                        <td className="py-2.5 px-3 text-right text-slate-500">
                          {(h.coarse_temp_c ?? h.coarse_temperature ?? 0).toFixed(1)}°C
                        </td>
                        <td className="py-2.5 px-3 text-right text-emerald-700 font-semibold">
                          +{((h.dynamic_residual_c ?? h.dynamic_residual ?? 0.74)).toFixed(2)}°C
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                            {h.model_used}
                          </span>
                        </td>
                      </>
                    )}
                    <td className="py-2.5 px-3 text-right text-blue-600 font-semibold">
                      {h.precipitation_probability_pct}%
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700">
                      {h.precipitation_mm > 0 ? `${h.precipitation_mm}mm` : '0'}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700">
                      {h.humidity_pct}%
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700">
                      {h.wind_speed_kmh} km/h
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Agricultural Advisory Consistency Box */}
      <div className="card-white p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Agromet Guidance Aligned to {forecast?.selected_date_label || targetDate}
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Date Match: {forecast?.selected_date === targetDate ? 'VERIFIED' : 'PENDING'}
          </span>
        </div>

        <div className="space-y-2">
          {forecast?.farmer_actions?.map((act, i) => (
            <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-800">{act.title}</span>
                <span className="text-[10px] font-mono text-slate-500">Timing: {act.timing}</span>
              </div>
              <p className="text-slate-600">{act.action}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
