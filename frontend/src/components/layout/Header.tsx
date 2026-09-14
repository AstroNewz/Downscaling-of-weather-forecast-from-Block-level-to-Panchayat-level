import React from 'react';
import { Calendar, Layers, UserCheck, RefreshCw, Activity } from 'lucide-react';
import { useApp, UserRole } from '../../context/AppContext.js';

export const Header: React.FC<{ title?: string; subtitle?: string }> = ({
  title = 'Panchayat Agro-Meteorological Intelligence',
  subtitle = 'SIH PS 26074 — Block to 1-km Panchayat Weather & Advisory Platform',
}) => {
  const {
    blocks,
    selectedBlockId,
    setSelectedBlockId,
    targetDate,
    setTargetDate,
    userRole,
    setUserRole,
    triggerRefresh,
    isLiveApi,
  } = useApp();

  return (
    <header style={{
      padding: '1rem 1.5rem',
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
      flexWrap: 'wrap',
      position: 'sticky',
      top: 0,
      zIndex: 20,
    }}>
      {/* Title block & Persistent API / Demo Mode Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              {title}
            </h1>
            {/* Live API vs Synthetic Demo Badge */}
            {isLiveApi ? (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.15rem 0.5rem',
                borderRadius: '9999px',
                fontSize: '0.65rem',
                fontWeight: 700,
                background: 'rgba(6, 78, 59, 0.6)',
                color: '#6ee7b7',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                fontFamily: 'monospace',
              }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
                LIVE FASTAPI BACKEND
              </span>
            ) : (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.15rem 0.5rem',
                borderRadius: '9999px',
                fontSize: '0.65rem',
                fontWeight: 700,
                background: 'rgba(120, 53, 15, 0.6)',
                color: '#fde68a',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                fontFamily: 'monospace',
              }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#f59e0b' }} />
                DEMO / SYNTHETIC DATA MODE (Offline Fixtures)
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.1rem' }}>
            {subtitle}
          </p>
        </div>
      </div>

      {/* Global Controls & Filters */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        {/* Block Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(30, 41, 59, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '0.35rem 0.65rem', borderRadius: '8px' }}>
          <Layers size={14} color="#10b981" />
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Block:</span>
          <select
            value={selectedBlockId || ''}
            onChange={(e) => setSelectedBlockId(e.target.value ? Number(e.target.value) : null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f8fafc',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="" style={{ background: '#0f172a' }}>All Blocks</option>
            {blocks.map((b) => (
              <option key={b.id} value={b.id} style={{ background: '#0f172a' }}>
                {b.name}
              </option>
            ))}
          </select>
        </div>

        {/* Forecast Date Picker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(30, 41, 59, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '0.35rem 0.65rem', borderRadius: '8px' }}>
          <Calendar size={14} color="#06b6d4" />
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Date:</span>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f8fafc',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
            }}
          />
        </div>

        {/* User Role Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'rgba(30, 41, 59, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '0.35rem 0.65rem', borderRadius: '8px' }}>
          <UserCheck size={14} color="#f59e0b" />
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Role:</span>
          <select
            value={userRole}
            onChange={(e) => setUserRole(e.target.value as UserRole)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f8fafc',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="FARMER" style={{ background: '#0f172a' }}>Farmer View</option>
            <option value="OFFICER" style={{ background: '#0f172a' }}>Extension Officer</option>
            <option value="ADMIN" style={{ background: '#0f172a' }}>Scientist / Admin</option>
          </select>
        </div>

        {/* Refresh button */}
        <button
          onClick={triggerRefresh}
          title="Refresh Data"
          style={{
            background: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '0.45rem',
            borderRadius: '8px',
            color: '#94a3b8',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <RefreshCw size={14} />
        </button>
      </div>
    </header>
  );
};
