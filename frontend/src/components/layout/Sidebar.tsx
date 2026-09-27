import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Home,
  CloudRain,
  Building2,
  ShieldAlert,
  MapPin,
  TrendingUp,
  Settings,
  ChevronRight,
  Info,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { forecast, selectedLocation } = useApp();

  const navItems = [
    {
      to: '/',
      label: 'HOME',
      icon: Home,
      id: 'nav-home',
    },
    {
      to: '/forecast',
      label: 'FORECAST',
      icon: CloudRain,
      id: 'nav-forecast',
    },
    {
      to: '/panchayats',
      label: 'PANCHAYATS',
      icon: Building2,
      id: 'nav-panchayats',
    },
    {
      to: '/advisories',
      label: 'AGRO ADVISORY',
      icon: ShieldAlert,
      badge: forecast?.agricultural_risks?.length ? `${forecast.agricultural_risks.length} Risks` : undefined,
      badgeColor: 'text-amber-700 bg-amber-50 border-amber-200',
      id: 'nav-advisories',
    },
    {
      to: '/map',
      label: 'MAP',
      icon: MapPin,
      badge: '1-km Grid',
      badgeColor: 'text-blue-700 bg-blue-50 border-blue-200',
      id: 'nav-map',
    },
    {
      to: '/insights',
      label: 'INSIGHTS',
      icon: TrendingUp,
      id: 'nav-insights',
    },
    {
      to: '/system-status',
      label: 'SYSTEM',
      icon: Settings,
      badge: 'Certified',
      badgeColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
      id: 'nav-system',
    },
  ];

  return (
    <aside className="w-60 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col justify-between hidden md:flex min-h-[calc(100vh-57px)]">
      {/* Navigation links */}
      <div className="p-3 space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          Navigation
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to) ||
                  (item.to === '/map' && location.pathname === '/gis') ||
                  (item.to === '/advisories' && location.pathname === '/advisory') ||
                  (item.to === '/system-status' && (location.pathname === '/governance' || location.pathname.startsWith('/system')));

            return (
              <NavLink
                key={item.to}
                id={item.id}
                to={item.to}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-bold border-l-4 border-blue-600 rounded-l-none shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-l-4 border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {item.badge && (
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${
                        item.badgeColor || 'text-slate-500 bg-slate-100 border-slate-200'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-blue-600" />}
                </div>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Context Card */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/50">
        <div className="p-3 rounded-lg border border-slate-200 bg-white text-xs space-y-2 shadow-xs">
          <div className="flex items-center gap-1.5 text-slate-700 font-semibold text-[11px]">
            <Info className="w-3.5 h-3.5 text-blue-600" />
            <span>Target Location</span>
          </div>
          <div className="text-[11px] text-slate-600 space-y-1">
            <div className="font-bold text-slate-900 truncate">
              {selectedLocation?.name || forecast?.location?.name || 'Maya Bazar Panchayat'}
            </div>
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>District:</span>
              <span className="font-medium text-slate-700">{selectedLocation?.district_name || 'Varanasi'}</span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>Current Temp:</span>
              <span className="font-bold text-blue-600">
                {forecast?.current?.temperature_c !== undefined ? `${forecast.current.temperature_c}°C` : '--'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
