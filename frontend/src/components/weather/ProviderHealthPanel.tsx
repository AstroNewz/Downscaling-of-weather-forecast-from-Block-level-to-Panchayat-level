import React, { useState, useEffect } from 'react';
import {
  Server,
  Activity,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  KeyRound,
  ShieldAlert,
  Clock,
  Radio,
} from 'lucide-react';
import { ProviderInfo, ProviderHealth } from '../../types';
import { getProviders, getProviderHealth } from '../../api/system';

export const ProviderHealthPanel: React.FC = () => {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [healthMap, setHealthMap] = useState<Record<string, ProviderHealth>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [probing, setProbing] = useState<Record<string, boolean>>({});

  const loadAll = async () => {
    setLoading(true);
    try {
      const list = await getProviders();
      setProviders(list);

      // Probe health for each provider
      const healthPromises = list.map(async (p) => {
        try {
          const h = await getProviderHealth(p.code);
          return { code: p.code, health: h };
        } catch (e) {
          return { code: p.code, health: null };
        }
      });

      const results = await Promise.all(healthPromises);
      const newMap: Record<string, ProviderHealth> = {};
      results.forEach((r) => {
        if (r.health) newMap[r.code] = r.health;
      });
      setHealthMap(newMap);
    } catch (err) {
      console.error('Failed to load weather providers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const probeSingle = async (code: string) => {
    setProbing((prev) => ({ ...prev, [code]: true }));
    try {
      const h = await getProviderHealth(code);
      setHealthMap((prev) => ({ ...prev, [code]: h }));
    } catch (err) {
      console.error(`Health probe failed for ${code}:`, err);
    } finally {
      setProbing((prev) => ({ ...prev, [code]: false }));
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md p-6 shadow-xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5 text-sky-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Weather Data Ingestion & Provider Health
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative tracking of operational meteorological feeds (IMD, Open-Meteo, Canonical Fixtures)
          </p>
        </div>

        <button
          onClick={loadAll}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-300 text-xs font-medium transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Probe All Providers</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {providers.map((p) => {
          const h = healthMap[p.code];
          const isProbingThis = probing[p.code];

          const isLive = h?.status === 'LIVE';
          const isNotConfigured = h?.status === 'NOT_CONFIGURED';
          const isUnavailable = h?.status === 'UNAVAILABLE' || h?.status === 'AUTH_FAILED';

          return (
            <div
              key={p.code}
              className={`rounded-xl border p-4 transition-all flex flex-col justify-between ${
                isLive
                  ? 'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50'
                  : isNotConfigured
                  ? 'border-amber-500/30 bg-amber-950/10 hover:border-amber-500/50'
                  : 'border-red-500/30 bg-red-950/10'
              }`}
            >
              <div className="space-y-3">
                {/* Header Badge */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-white">{p.name}</h3>
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                      {p.source_type} • {p.code}
                    </span>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-bold tracking-wider ${
                      isLive
                        ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300'
                        : isNotConfigured
                        ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300'
                        : 'bg-red-500/20 border border-red-500/40 text-red-300'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isLive
                          ? 'bg-emerald-400 animate-pulse'
                          : isNotConfigured
                          ? 'bg-amber-400'
                          : 'bg-red-400'
                      }`}
                    />
                    {h?.status || p.status}
                  </span>
                </div>

                <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                  {p.description}
                </p>

                {/* Status & Diagnostic Details */}
                <div className="space-y-1.5 pt-2 border-t border-slate-800/80 text-xs">
                  <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                    <span>Authentication:</span>
                    <span className={p.auth_configured ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                      {p.requires_auth ? (p.auth_configured ? 'Configured' : 'Credentials Required') : 'Public / None'}
                    </span>
                  </div>

                  {h?.latency_ms !== null && h?.latency_ms !== undefined && (
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                      <span>Latency:</span>
                      <span className="text-sky-300">{h.latency_ms} ms</span>
                    </div>
                  )}

                  {h?.data_age_minutes !== null && h?.data_age_minutes !== undefined && (
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                      <span>Data Freshness:</span>
                      <span className="text-slate-200">{h.data_age_minutes.toFixed(1)} min ago</span>
                    </div>
                  )}

                  {h?.source_timestamp && (
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                      <span>Source Time:</span>
                      <span className="text-slate-300 truncate max-w-[150px]">{h.source_timestamp}</span>
                    </div>
                  )}

                  {h?.request_id && (
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[10px]">
                      <span>Diagnostic ID:</span>
                      <span className="text-indigo-300 truncate max-w-[140px]">{h.request_id}</span>
                    </div>
                  )}
                </div>

                {/* IMD Credentials Warning Notice */}
                {isNotConfigured && (
                  <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/30 text-[11px] text-amber-200/90 space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-amber-300">
                      <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                      <span>Not Configured (Scientific Safeguard)</span>
                    </div>
                    <p className="text-[10px] text-amber-200/80 leading-normal">
                      Formal IMD credentials (<code>IMD_API_KEY</code>) are unset. The system strictly adheres to scientific integrity by never fabricating IMD responses.
                    </p>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="pt-4 mt-2">
                <button
                  onClick={() => probeSingle(p.code)}
                  disabled={isProbingThis}
                  className="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-white text-xs font-mono transition-all disabled:opacity-50"
                >
                  <Activity className={`w-3.5 h-3.5 ${isProbingThis ? 'animate-spin text-sky-400' : 'text-slate-400'}`} />
                  <span>{isProbingThis ? 'Probing Gateway...' : 'Test Connection'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
