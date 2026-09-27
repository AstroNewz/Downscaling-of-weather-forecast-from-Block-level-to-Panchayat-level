import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { 
  Cloud, 
  CloudRain, 
  Sun, 
  Wind, 
  Droplets, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle,
  Calendar, 
  ChevronRight, 
  ExternalLink,
  RefreshCw,
  Sparkles,
  Info
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    forecast,
    forecastLoading,
    forecastError,
    selectedLocation,
    todayDate,
    targetDate,
    setTargetDate,
    viewMode,
    refetchForecast,
  } = useApp();

  // Helper for weather icons
  const renderWeatherIcon = (iconName?: string, className: string = 'w-6 h-6') => {
    switch (iconName) {
      case 'sun':
        return <Sun className={`${className} text-amber-500`} />;
      case 'cloud-sun':
        return <CloudSunIcon className={`${className} text-amber-500`} />;
      case 'cloud':
        return <Cloud className={`${className} text-slate-400`} />;
      case 'cloud-rain':
      case 'cloud-rain-heavy':
        return <CloudRain className={`${className} text-blue-500`} />;
      default:
        return <Sun className={`${className} text-amber-500`} />;
    }
  };

  // Severity styling
  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH':
      case 'SEVERE':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'MODERATE':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'LOW':
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const getSeverityBorder = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH':
      case 'SEVERE':
        return 'border-l-4 border-l-red-500';
      case 'MODERATE':
        return 'border-l-4 border-l-amber-500';
      case 'LOW':
      default:
        return 'border-l-4 border-l-emerald-500';
    }
  };

  // Advisory Consistency Engine: strictly verify forecast data matches current selection
  const isDataConsistent = Boolean(
    forecast &&
    !forecastLoading &&
    (forecast.selected_date === targetDate || forecast.forecast_date === targetDate)
  );

  return (
    <div className="space-y-6 pb-12 animate-fade-in" id="dashboard-main">
      {/* 1. HERO SECTION: CURRENT WEATHER & LOCALITY */}
      <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden">
        {forecastLoading || !forecast ? (
          <div className="space-y-4 py-4 animate-pulse">
            <div className="h-6 w-48 bg-slate-200 rounded-md" />
            <div className="h-14 w-64 bg-slate-200 rounded-lg" />
            <div className="h-5 w-80 bg-slate-200 rounded-md" />
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div className="h-16 bg-slate-100 rounded-xl" />
              <div className="h-16 bg-slate-100 rounded-xl" />
              <div className="h-16 bg-slate-100 rounded-xl" />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {/* Location & Title */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
                    {forecast.is_today ? 'Weather NOW & Today' : 'Forecast Horizon'}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    {forecast.selected_date_formatted || targetDate}
                  </span>
                </div>

                <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
                  {selectedLocation?.name || forecast.location_name || forecast.location?.name}
                </h1>

                <p className="text-xs text-slate-500">
                  {selectedLocation?.block_name || forecast.location?.block_name} •{' '}
                  {selectedLocation?.district_name || forecast.location?.district_name},{' '}
                  {selectedLocation?.state_name || forecast.location?.state_name} •{' '}
                  Elevation: {selectedLocation?.elevation_m || forecast.location?.elevation_m || 95}m
                </p>
              </div>

              {/* Quick Actions & Live Status */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Live Operational NWP</span>
                </div>
                <button
                  id="dashboard-refresh-btn"
                  onClick={() => refetchForecast()}
                  title="Reload live forecast"
                  className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Main Temperature & Micro-Climate Metrics */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pt-2">
              <div className="flex items-baseline gap-4">
                <div className="text-5xl md:text-6xl font-black text-slate-900 tracking-tight">
                  {forecast.current ? `${forecast.current.temperature_c.toFixed(1)}°C` : '--'}
                </div>
                <div>
                  <div className="text-base font-semibold text-slate-800 flex items-center gap-1.5">
                    {renderWeatherIcon(forecast.current?.icon_name, 'w-5 h-5')}
                    <span>{forecast.current?.condition_text || 'Clear Sky'}</span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Feels like {forecast.current?.feels_like_c ?? forecast.current?.temperature_c}°C
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 min-w-[320px]">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-0.5">
                    <Droplets className="w-3.5 h-3.5 text-blue-500" />
                    <span>Humidity</span>
                  </div>
                  <div className="text-base font-bold text-slate-900">
                    {forecast.current ? `${forecast.current.humidity_pct}%` : '--'}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-0.5">
                    <Wind className="w-3.5 h-3.5 text-teal-500" />
                    <span>Wind</span>
                  </div>
                  <div className="text-base font-bold text-slate-900">
                    {forecast.current ? `${forecast.current.wind_speed_kmh} km/h` : '--'}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-0.5">
                    <CloudRain className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Rainfall</span>
                  </div>
                  <div className="text-base font-bold text-slate-900">
                    {forecast.current ? `${forecast.current.precipitation_mm} mm` : '0 mm'}
                  </div>
                </div>
              </div>
            </div>

            {/* Technical View Details Banner */}
            {viewMode === 'TECHNICAL' && forecast.current && (
              <div className="mt-4 pt-3 border-t border-slate-200 text-xs text-slate-600 bg-slate-50 -mx-6 -mb-6 p-4 rounded-b-2xl flex flex-wrap items-center justify-between gap-4 font-mono">
                <div>
                  <span className="text-slate-500">Coarse NWP: </span>
                  <span className="font-semibold text-slate-800">{forecast.current.coarse_temp_c}°C</span>
                  <span className="mx-2 text-slate-300">|</span>
                  <span className="text-slate-500">Dynamic Residual: </span>
                  <span className="font-semibold text-emerald-700">+{forecast.current.dynamic_residual_c}°C</span>
                  <span className="mx-2 text-slate-300">|</span>
                  <span className="text-slate-500">Downscaled: </span>
                  <span className="font-bold text-blue-700">{forecast.current.temperature_c}°C</span>
                </div>
                <div>
                  <span className="text-slate-500">Model: </span>
                  <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                    {forecast.current.model_used}
                  </span>
                  <span className="mx-2 text-slate-300">|</span>
                  <span className="text-slate-500">Fallback: </span>
                  <span className={`font-semibold ${forecast.current.fallback_active ? 'text-amber-600' : 'text-slate-600'}`}>
                    {forecast.current.fallback_active ? 'ACTIVE' : 'NO'}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 2. DYNAMIC DATE HORIZON SELECTOR (TODAY, TOMORROW, +2 to +6) */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wider">
            <Calendar className="w-4 h-4 text-blue-600" />
            <span>Select Forecast Horizon</span>
          </div>
          <span className="text-xs text-slate-400">Multi-day NWP operational downscaling</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none" id="date-selector-bar">
          {forecast?.daily_forecast?.map((day) => {
            const isSelected = day.date === targetDate;
            const maxTemp = day.temp_max_c ?? day.t_max_c;
            const minTemp = day.temp_min_c ?? day.t_min_c;
            const rainProb = day.rain_probability_pct ?? day.precip_probability_pct ?? 0;

            return (
              <button
                key={day.date}
                type="button"
                id={`date-tab-${day.date}`}
                onClick={() => setTargetDate(day.date)}
                className={`flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium border transition-all text-left min-w-[110px] ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="font-bold truncate">{day.day_label || day.display_label}</div>
                <div className={`text-[10px] ${isSelected ? 'text-blue-100' : 'text-slate-500'}`}>
                  {day.formatted_date ? day.formatted_date.split(',')[0] : day.date}
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] font-mono">
                  <span>{maxTemp}°</span>
                  <span className={isSelected ? 'text-blue-200' : 'text-slate-400'}>
                    {minTemp}°
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. TODAY'S HOURLY FORECAST PROFILE */}
      <section className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Hourly Downscaled Profile
            </h2>
            <p className="text-xs text-slate-500">
              Diurnal temperature curve & rain probability for {forecast?.selected_date_label || targetDate}
            </p>
          </div>
          <span className="text-[11px] font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200 font-medium">
            1-km Resolution
          </span>
        </div>

        {forecastLoading || !isDataConsistent ? (
          <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 py-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 overflow-x-auto pb-1" id="hourly-forecast-grid">
            {forecast?.today_hourly_chart?.map((hour, idx) => {
              const hTemp = hour.downscaled_temperature ?? hour.downscaled_temperature_c ?? hour.temperature_c;
              const hProb = hour.rain_probability ?? hour.rain_probability_pct ?? hour.precipitation_probability_pct ?? 0;
              const hWind = hour.wind_speed ?? hour.wind_speed_kmh ?? 12;

              return (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl bg-slate-50/70 border border-slate-200 text-center space-y-1.5 flex flex-col justify-between hover:bg-slate-50 transition-colors"
                >
                  <div className="text-[11px] font-mono text-slate-500 font-medium">
                    {hour.local_time || hour.hour_label || `${hour.hour}:00`}
                  </div>

                  <div className="flex justify-center py-0.5">
                    {renderWeatherIcon(hour.icon_name, 'w-5 h-5')}
                  </div>

                  <div className="text-sm font-bold text-slate-900 font-mono">
                    {hTemp ? hTemp.toFixed(1) : '--'}°
                  </div>

                  <div className="text-[10px] text-blue-600 font-medium flex items-center justify-center gap-0.5">
                    <Droplets className="w-2.5 h-2.5" />
                    <span>{hProb}%</span>
                  </div>

                  <div className="text-[9px] text-slate-400 font-mono">
                    {hWind} km/h
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 4. AGRICULTURAL RISK ENGINE */}
      <section className="space-y-3" id="agricultural-risks-section">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-emerald-700" />
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Today's Agricultural Risk
            </h2>
          </div>
          <span className="text-xs text-slate-500 font-medium">
            Stage-specific Kharif crop vulnerability
          </span>
        </div>

        {forecastLoading || !isDataConsistent ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="h-28 bg-slate-100 rounded-xl animate-pulse" />
            <div className="h-28 bg-slate-100 rounded-xl animate-pulse" />
            <div className="h-28 bg-slate-100 rounded-xl animate-pulse" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {forecast?.agricultural_risks?.map((risk, index) => {
              return (
                <div
                  key={index}
                  className={`bg-white rounded-xl p-4 border border-slate-200 shadow-sm space-y-2 ${getSeverityBorder(risk.severity)}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800">
                      {risk.title || risk.risk_type.replace(/_/g, ' ')}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getSeverityBadge(risk.severity)}`}>
                      {risk.severity}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    {risk.condition}
                  </p>

                  <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100">
                    <span>Crop: <strong className="text-slate-700">{risk.crop}</strong></span>
                    <span>Stage: <strong className="text-slate-700">{risk.crop_stage}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 5. WHAT TO DO TODAY: ACTIONABLE FARMER GUIDANCE */}
      <section className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4" id="farmer-actions-section">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                What To Do {forecast?.selected_date_label || 'Today'}
              </h2>
              <p className="text-xs text-slate-500">
                Actionable agronomic guidance aligned with localized micro-climate downscaling
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/advisories')}
            className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1"
          >
            <span>View All Advisories</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {forecastLoading || !isDataConsistent ? (
          <div className="space-y-3">
            <div className="h-16 bg-slate-100 rounded-xl animate-pulse" />
            <div className="h-16 bg-slate-100 rounded-xl animate-pulse" />
          </div>
        ) : (
          <div className="space-y-2.5">
            {forecast?.farmer_actions?.map((act, index) => (
              <div
                key={index}
                className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100/70 transition-colors flex items-start gap-3"
              >
                <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                  {index + 1}
                </div>
                <div className="space-y-0.5 flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900">
                      {act.title}
                    </h3>
                    <span className="text-[10px] font-mono text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                      Timing: {act.timing}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {act.action}
                  </p>
                  <p className="text-[11px] text-slate-500 italic">
                    Why: {act.why}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 6. 7-DAY FORECAST OVERVIEW */}
      <section className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4" id="seven-day-forecast-section">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              7-Day Panchayat Outlook
            </h2>
            <p className="text-xs text-slate-500">
              Click any card to inspect that day's hourly diurnal curve & risks
            </p>
          </div>
          <button
            onClick={() => navigate('/forecast')}
            className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1"
          >
            <span>Detailed Forecast</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          {forecast?.daily_forecast?.map((day) => {
            const isSelected = day.date === targetDate;
            const maxTemp = day.temp_max_c ?? day.t_max_c;
            const minTemp = day.temp_min_c ?? day.t_min_c;
            const rainProb = day.rain_probability_pct ?? day.precip_probability_pct ?? 0;

            return (
              <div
                key={day.date}
                onClick={() => setTargetDate(day.date)}
                className={`p-3 rounded-xl border text-center space-y-2 cursor-pointer transition-all hover:shadow-sm ${
                  isSelected
                    ? 'border-blue-600 ring-2 ring-blue-500/20 bg-blue-50/30'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="font-bold text-xs text-slate-800">
                  {day.day_label || day.display_label}
                </div>
                <div className="text-[10px] text-slate-500">
                  {day.formatted_date ? day.formatted_date.split(',')[0] : day.date}
                </div>

                <div className="flex justify-center py-1">
                  {renderWeatherIcon(day.icon_name, 'w-6 h-6')}
                </div>

                <div className="text-xs font-bold text-slate-900 font-mono">
                  {maxTemp}° / <span className="text-slate-500 font-normal">{minTemp}°</span>
                </div>

                <div className="text-[10px] text-blue-600 font-medium">
                  {rainProb}% rain
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 7. COMPACT LIVE PROVENANCE & TRANSPARENCY NOTE */}
      <footer className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 text-xs space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono font-semibold text-slate-800">
              {forecast?.provenance?.source_provider || 'OPEN_METEO_OPERATIONAL_NWP'} • LIVE
            </span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-500 font-mono text-[11px]">
              Req ID: {forecast?.provenance?.live_request_id || forecast?.request_id || 'req_live_...' }
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/system/forecast-comparison')}
              className="text-blue-600 hover:text-blue-800 font-medium text-xs flex items-center gap-1"
            >
              <span>Provider Comparison</span>
              <ExternalLink className="w-3 h-3" />
            </button>
            <button
              onClick={() => navigate('/system-status')}
              className="text-slate-600 hover:text-slate-900 font-medium text-xs"
            >
              System Governance
            </button>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-200 pt-2">
          Forecasts may differ between providers because weather services use different numerical models, model runs, spatial grids and processing methods.
        </p>
      </footer>
    </div>
  );
};

// Weather icon subcomponent
const CloudSunIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 2v2" />
    <path d="m4.93 4.93 1.41 1.41" />
    <path d="M20 12h2" />
    <path d="m19.07 4.93-1.41 1.41" />
    <path d="M15.947 12.65a4 4 0 0 0-5.925-4.128" />
    <path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z" />
  </svg>
);
