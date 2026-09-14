import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  CloudSun,
  Sprout,
  AlertTriangle,
  FileCheck2,
  Map,
  Activity,
  ShieldCheck,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../../context/AppContext.js';

export const Sidebar: React.FC = () => {
  const { userRole } = useApp();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/judge', label: '⭐ SIH Judge Walkthrough', icon: Sparkles },
    { to: '/panchayats', label: 'Panchayats', icon: MapPin },
    { to: '/weather-analysis', label: 'Weather & 1-km ML', icon: CloudSun },
    { to: '/map', label: 'GIS Spatial Map', icon: Map },
    { to: '/advisories', label: 'Advisory Hub', icon: FileCheck2 },
    { to: '/system-status', label: 'System Governance', icon: Activity },
  ];

  return (
    <aside style={{
      width: '260px',
      background: '#090d16',
      borderRight: '1px solid rgba(255, 255, 255, 0.08)',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      flexShrink: 0,
    }}>
      {/* Brand Header */}
      <div style={{ padding: '1.5rem 1.25rem', borderBottom: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.25rem',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
          }}>
            🌾
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em', color: '#f8fafc' }}>
              AgroMet <span style={{ color: '#10b981', fontSize: '0.85rem', fontWeight: 600 }}>26074</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Panchayat Downscaling AI
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ flex: 1, padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem', overflowY: 'auto' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', color: '#64748b', padding: '0.5rem 0.75rem', letterSpacing: '0.05em' }}>
          Main Platform
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.65rem 0.85rem',
                borderRadius: '8px',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#f8fafc' : '#94a3b8',
                background: isActive ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                borderLeft: isActive ? '3px solid #10b981' : '3px solid transparent',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={18} style={{ opacity: 0.9 }} />
              <span style={{ flex: 1 }}>{item.label}</span>
              <ChevronRight size={14} style={{ opacity: 0.4 }} />
            </NavLink>
          );
        })}
      </nav>

      {/* Role Badge Indicator */}
      <div style={{
        padding: '1rem 1.25rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        background: 'rgba(15, 23, 42, 0.6)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <ShieldCheck size={14} color="#10b981" />
          <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Active Viewport
          </span>
        </div>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
          {userRole === 'FARMER' ? '🚜 Farmer Advisory Mode' : userRole === 'OFFICER' ? '📋 Extension Officer View' : '⚙️ Technical Administrator'}
        </div>
      </div>
    </aside>
  );
};
