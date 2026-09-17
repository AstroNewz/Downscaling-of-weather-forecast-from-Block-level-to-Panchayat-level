import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  MapPin,
  CloudSun,
  ShieldAlert,
  FileCheck2,
  Award,
  ChevronRight,
  Info
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { selectedPanchayat } = useApp();

  const navItems = [
    {
      to: '/',
      label: 'Executive Command',
      icon: LayoutDashboard,
      badge: 'Live',
      badgeColor: 'text-emerald-400 bg-emerald-950/60 border-emerald-800/40',
      id: 'nav-dashboard',
    },
    {
      to: '/panchayats',
      label: 'Panchayat Explorer',
      icon: Building2,
      badge: undefined,
      id: 'nav-panchayats',
    },
    {
      to: '/map',
      label: 'GIS Intelligence',
      icon: MapPin,
      badge: '1-km Grid',
      badgeColor: 'text-sky-400 bg-sky-950/60 border-sky-800/40',
      id: 'nav-gis',
    },
    {
      to: '/weather-analysis',
      label: 'Weather & Downscaling',
      icon: CloudSun,
      badge: '+0.7351°C',
      badgeColor: 'text-emerald-400 bg-emerald-950/60 border-emerald-800/40',
      id: 'nav-weather',
    },
    {
      to: '/advisories',
      label: 'Agro-Advisories',
      icon: ShieldAlert,
      badge: selectedPanchayat?.active_risks_count ? `${selectedPanchayat.active_risks_count} Risks` : undefined,
      badgeColor: 'text-rose-400 bg-rose-950/60 border-rose-800/40',
      id: 'nav-advisories',
    },
    {
      to: '/system-status',
      label: 'Scientific Governance',
      icon: FileCheck2,
      badge: 'Phase 24',
      badgeColor: 'text-indigo-400 bg-indigo-950/60 border-indigo-800/40',
      id: 'nav-governance',
    },
    {
      to: '/judge',
      label: 'SIH Judge Mode',
      icon: Award,
      badge: '12 Steps',
      badgeColor: 'text-amber-400 bg-amber-950/60 border-amber-800/40',
      id: 'nav-judge',
    },
  ];

  return (
    <aside className="w-64 flex-shrink-0 bg-[#070a12] border-r border-slate-800/80 flex flex-col justify-between hidden md:flex min-h-[calc(100vh-53px)]">
      {/* Top navigation links */}
      <div className="p-3 space-y-1">
        <div className="px-3 py-2 text-[10px] font-mono tracking-wider text-slate-400 uppercase">
          Navigation Architecture
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to) ||
                  (item.to === '/map' && location.pathname === '/gis') ||
                  (item.to === '/weather-analysis' && location.pathname === '/weather') ||
                  (item.to === '/advisories' && location.pathname === '/advisory') ||
                  (item.to === '/system-status' && location.pathname === '/governance');

            return (
              <NavLink
                key={item.to}
                id={item.id}
                to={item.to}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-emerald-500/10 text-white font-semibold border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.05)]'
                    : 'text-slate-300 hover:text-white hover:bg-slate-900/60 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {item.badge && (
                    <span
                      className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border ${
                        item.badgeColor || 'text-slate-400 bg-slate-800 border-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-emerald-400" />}
                </div>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Context Card */}
      <div className="p-3 border-t border-slate-800/80">
        <div className="glass-panel p-3 rounded-lg border border-slate-800 bg-slate-900/40 text-[11px] space-y-2">
          <div className="flex items-center gap-1.5 text-slate-300 font-medium">
            <Info className="w-3.5 h-3.5 text-emerald-400" />
            <span>Active Pilot Frame</span>
          </div>
          <div className="font-mono text-slate-400 text-[10px] space-y-0.5">
            <div className="flex justify-between">
              <span className="text-slate-500">Panchayat:</span>
              <span className="text-slate-300 font-semibold truncate max-w-[110px]">
                {selectedPanchayat?.name || 'Loading...'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Area Basis:</span>
              <span className="text-slate-300">Local UTM (EPSG:32644)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Calibration:</span>
              <span className="text-emerald-400">+0.7351°C Scalar</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
