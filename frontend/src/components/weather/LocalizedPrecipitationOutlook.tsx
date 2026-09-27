import React from 'react';
import { 
  CloudRain, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Radio, 
  Info, 
  Satellite, 
  Activity, 
  Layers,
  HelpCircle,
  ShieldAlert
} from 'lucide-react';
import { LocalizedPrecipitationNowcast, NowcastConfidence, PrecipitationSourceState } from '../../types';

interface LocalizedPrecipitationOutlookProps {
  nowcast?: LocalizedPrecipitationNowcast | null;
  baselineRainfallMm?: number;
  baselineProbabilityPct?: number;
  panchayatName?: string;
  panchayatId?: string | number;
  blockName?: string;
  districtName?: string;
  targetDate?: string;
  isToday?: boolean;
  viewMode?: 'FARMER' | 'TECHNICAL';
  className?: string;
}

export const LocalizedPrecipitationOutlook: React.FC<LocalizedPrecipitationOutlookProps> = ({
  nowcast,
  baselineRainfallMm = 0,
  baselineProbabilityPct = 0,
  panchayatName,
  panchayatId,
  blockName,
  districtName,
  targetDate,
  isToday = true,
  viewMode = 'FARMER',
  className = '',
}) => {
  // If target date is not today/current horizon, nowcast is not applicable
  if (!isToday) {
    return (
      <div 
        className={`card-white p-4 border-slate-200 bg-slate-50/70 text-xs text-slate-500 flex items-center justify-between gap-3 ${className}`}
        id="localized-nowcast-future-notice"
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <span>
            Localized 30–120 min observation-fused precipitation nowcast is only operationally active for today’s live monitoring window.
          </span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200/60 text-slate-600">
          Scheduled NWP Only
        </span>
      </div>
    );
  }

  // Fail-closed / unavailable state when nowcast is missing or explicitly unsuccessful
  if (!nowcast || !nowcast.success) {
    return (
      <div 
        className={`card-white p-4 border-amber-200 bg-amber-50/40 text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${className}`}
        id="localized-nowcast-unavailable"
      >
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-bold flex items-center gap-2">
              <span>Localized Precipitation Outlook</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-mono border border-amber-200">
                DATA UNAVAILABLE
              </span>
            </div>
            <p className="text-slate-600 text-[11px] mt-0.5">
              {nowcast?.data_quality_notes || 'Observational telemetry or verified Panchayat polygon currently unavailable. Relying on certified baseline forecast.'}
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-500 flex items-center gap-1.5 self-end sm:self-auto">
          <span>Baseline NWP: {baselineRainfallMm} mm ({baselineProbabilityPct}%)</span>
        </div>
      </div>
    );
  }

  // Format confidence badge styling
  const getConfidenceBadge = (confidence: NowcastConfidence) => {
    switch (confidence) {
      case 'HIGH':
        return {
          label: 'Confidence: High',
          className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          dot: 'bg-emerald-500',
        };
      case 'MEDIUM':
        return {
          label: 'Confidence: Medium',
          className: 'bg-blue-50 text-blue-700 border-blue-200',
          dot: 'bg-blue-500',
        };
      case 'LOW':
        return {
          label: 'Confidence: Low',
          className: 'bg-amber-50 text-amber-700 border-amber-200',
          dot: 'bg-amber-500',
        };
      case 'INSUFFICIENT_DATA':
      default:
        return {
          label: 'Confidence: Insufficient Data',
          className: 'bg-slate-100 text-slate-700 border-slate-300',
          dot: 'bg-slate-400',
        };
    }
  };

  // Human-readable source state
  const formatSourceState = (state: PrecipitationSourceState | string) => {
    switch (state) {
      case 'NWP_ONLY':
        return 'NWP Model Only';
      case 'NWP_SATELLITE':
        return 'NWP + Satellite Fusion';
      case 'NWP_SATELLITE_RADAR':
        return 'NWP + Satellite + Radar';
      case 'NWP_SATELLITE_SURFACE_OBS':
        return 'NWP + Satellite + Surface AWS';
      case 'NWP_SATELLITE_RADAR_SURFACE_OBS':
        return 'NWP + Satellite + Radar + Surface AWS';
      case 'INSUFFICIENT_DATA':
      default:
        return 'Insufficient Observational Data';
    }
  };

  // Observation age text
  const formatFreshness = (ageMin?: number | null, isStale?: boolean) => {
    if (isStale) return 'Observation: Stale (penalized)';
    if (ageMin === null || ageMin === undefined) return 'Observation age: unknown';
    if (ageMin < 1) return 'Observation: Just now';
    return `Observation age: ${Math.round(ageMin)} min ago`;
  };

  const confidenceMeta = getConfidenceBadge(nowcast.confidence);
  const primaryHorizon = nowcast.primary_horizon || (nowcast.horizons && nowcast.horizons[0]);
  const horizonsList = nowcast.horizons && nowcast.horizons.length > 0
    ? nowcast.horizons
    : primaryHorizon ? [primaryHorizon] : [];

  const resolvedPanchayatName = nowcast.panchayat_name || panchayatName || `Panchayat ${nowcast.panchayat_id}`;
  const resolvedBlockName = nowcast.block_name || blockName || 'Block';
  const resolvedDistrictName = nowcast.district_name || districtName || 'District';

  return (
    <div 
      className={`card-white p-5 border-slate-200 bg-white space-y-4 shadow-xs ${className}`}
      id="localized-precipitation-outlook-card"
    >
      {/* 1. Header Bar: Explicit Panchayat Identity & Source Metadata */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
              <CloudRain className="w-3.5 h-3.5 text-blue-600" />
              LOCAL PRECIPITATION OUTLOOK
            </span>
            <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold border ${confidenceMeta.className}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${confidenceMeta.dot}`} />
              {confidenceMeta.label}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
              {formatSourceState(nowcast.source_state)}
            </span>
          </div>

          {/* Explicit Panchayat Administrative Identity (Requirement 4) */}
          <div className="mt-1.5 text-xs text-slate-700">
            <span className="font-bold text-slate-900">{resolvedPanchayatName}</span>
            <span className="text-slate-400 font-mono ml-1.5">
              [ID: {nowcast.panchayat_id || panchayatId || 'CANONICAL'}]
            </span>
            <span className="text-slate-500 ml-1.5">
              • Block: <strong className="text-slate-700">{resolvedBlockName}</strong>
              {' '}• District: <strong className="text-slate-700">{resolvedDistrictName}</strong>
            </span>
          </div>
        </div>

        {/* Freshness & Timestamps (Requirement 11) */}
        <div className="text-right text-[11px] text-slate-500 font-mono">
          <div className={nowcast.is_stale ? 'text-amber-600 font-semibold' : 'text-slate-600'}>
            {formatFreshness(nowcast.observation_age_minutes, nowcast.is_stale)}
          </div>
          <div className="text-[10px] text-slate-400">
            Issued: {nowcast.issue_time ? new Date(nowcast.issue_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Live'}
          </div>
        </div>
      </div>

      {/* 2. Baseline NWP Forecast vs Localized Nowcast Comparison Strip (Requirement 3) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50/80 border border-slate-200/80">
        {/* Left: BASELINE FORECAST (Macroscale NWP) */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              BASELINE FORECAST (Block NWP)
            </span>
            <span className="text-[10px] font-mono text-slate-400">Grid scale ~25 km</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-bold text-slate-800">
              {baselineRainfallMm > 0 ? `${baselineRainfallMm.toFixed(1)} mm` : '0.0 mm'}
            </span>
            <span className="text-xs text-slate-500">
              ({baselineProbabilityPct}% rain probability)
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            What the larger-scale operational forecast model indicates for {resolvedBlockName}.
          </p>
        </div>

        {/* Right: LOCALIZED NOWCAST (Observation-Fused) */}
        <div className="space-y-1 sm:border-l sm:border-slate-200 sm:pl-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1">
              <Activity className="w-3 h-3 text-blue-600" />
              LOCALIZED NOWCAST (Panchayat Fusion)
            </span>
            <span className="text-[10px] font-mono text-blue-600">Polygon scale</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-bold text-blue-900">
              Rain risk: {primaryHorizon ? Math.round(primaryHorizon.precipitation_probability * 100) : 0}%
            </span>
            <span className="text-xs text-slate-600">
              {primaryHorizon?.expected_precipitation_mm !== null && primaryHorizon?.expected_precipitation_mm !== undefined
                ? `Expected: ~${primaryHorizon.expected_precipitation_mm.toFixed(1)} mm`
                : 'Expected amount: — (unavailable)'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            What latest satellite &amp; localized observations indicate for {resolvedPanchayatName}.
          </p>
        </div>
      </div>

      {/* 3. Disagreement Banner when Baseline and Local Observations Differ (Requirement 12) */}
      {nowcast.disagreement_detected && (
        <div 
          className="p-3 rounded-xl border border-amber-300 bg-amber-50/60 text-xs text-amber-950 space-y-1.5 animate-fade-in"
          id="nowcast-disagreement-alert"
        >
          <div className="flex items-center gap-1.5 font-bold text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>Forecast and local observations differ.</span>
          </div>
          <p className="text-[11px] text-amber-900/90 leading-relaxed">
            {nowcast.disagreement_reason || 'Macroscale NWP model and localized observation evidence indicate diverging precipitation signals. Displaying both evidence streams conservatively.'}
          </p>
          <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[10px]">
            <div className="p-1.5 rounded bg-white/70 border border-amber-200">
              <span className="text-slate-500 block">Baseline Signal:</span>
              <strong className="text-slate-800">
                {baselineRainfallMm > 0 ? `Rain expected (${baselineRainfallMm} mm)` : 'Low rainfall expected'}
              </strong>
            </div>
            <div className="p-1.5 rounded bg-white/70 border border-amber-200">
              <span className="text-slate-500 block">Local Observation:</span>
              <strong className="text-blue-800">
                {primaryHorizon && primaryHorizon.precipitation_probability >= 0.5 ? 'Convective cloud signal' : 'Lower short-term rain risk'}
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* 4. Multi-Horizon Outlook Cards (30m, 60m, 120m) (Requirements 6, 7, 8) */}
      <div className="space-y-1.5">
        <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wide">
          Short-Horizon Rain Risk Progression
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {horizonsList.map((hz) => {
            const probPct = Math.round(hz.precipitation_probability * 100);
            return (
              <div 
                key={hz.horizon_minutes}
                className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors space-y-1.5"
              >
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-800">Next {hz.horizon_minutes} min</span>
                  <span className="font-mono font-bold text-blue-700 text-sm">{probPct}%</span>
                </div>

                {/* Probability Bar */}
                <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-300 ${
                      probPct >= 70 ? 'bg-blue-600' : probPct >= 40 ? 'bg-sky-500' : 'bg-slate-400'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, probPct))}%` }}
                  />
                </div>

                {/* Expected Rainfall Display (Requirement 8) */}
                <div className="text-[10px] text-slate-500 flex justify-between items-center">
                  <span>Rain risk: {probPct}%</span>
                  <span className="font-mono">
                    {hz.expected_precipitation_mm !== null && hz.expected_precipitation_mm !== undefined
                      ? `~${hz.expected_precipitation_mm.toFixed(1)} mm`
                      : 'Amount: —'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Technical View Evidence Panel (Requirement 21, 22, 23) */}
      {viewMode === 'TECHNICAL' && (
        <div className="mt-3 pt-3 border-t border-slate-200 space-y-2 text-xs text-slate-600 font-mono bg-slate-50/70 p-3 rounded-xl">
          <div className="flex items-center justify-between text-[11px] font-bold text-slate-800 uppercase">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              Observation-Fusion Technical Evidence
            </span>
            <span className="text-slate-400 text-[10px] font-normal">
              Method: {nowcast.method_version || 'FUSION_V1'}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div>
              <span className="text-slate-400 block text-[10px]">Source State:</span>
              <span className="font-semibold text-slate-800">{nowcast.source_state}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Spatial Coverage:</span>
              <span className="font-semibold text-slate-800">
                {nowcast.spatial_coverage_fraction !== null && nowcast.spatial_coverage_fraction !== undefined
                  ? `${(nowcast.spatial_coverage_fraction * 100).toFixed(1)}%`
                  : '100%'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Native Resolution:</span>
              <span className="font-semibold text-slate-800">
                {nowcast.native_source_resolution_km ? `${nowcast.native_source_resolution_km} km` : '4.0 km (INSAT-3D)'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Evidence Contradiction:</span>
              <span className={nowcast.disagreement_detected ? 'text-amber-700 font-bold' : 'text-emerald-700'}>
                {nowcast.disagreement_detected ? 'DETECTED' : 'NONE'}
              </span>
            </div>
          </div>

          {/* Scientific Disclosures (Requirements 23 & 27) */}
          <div className="text-[10px] text-slate-400 border-t border-slate-200/80 pt-2 space-y-0.5">
            <p>• Display grid is finer than source resolution; visualization does not imply finer meteorological observations.</p>
            <p>• Satellite cloud infrared detection indicates convective potential, not certified rain gauge measurements.</p>
          </div>
        </div>
      )}
    </div>
  );
};
