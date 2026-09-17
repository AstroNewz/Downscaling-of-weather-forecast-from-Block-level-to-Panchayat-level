import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';

// Pages
import { Dashboard } from './pages/Dashboard';
import { PanchayatExplorer } from './pages/PanchayatExplorer';
import { PanchayatDetail } from './pages/PanchayatDetail';
import { GisIntelligence } from './pages/GisIntelligence';
import { WeatherAnalysis } from './pages/WeatherAnalysis';
import { AgroAdvisories } from './pages/AgroAdvisories';
import { ScientificGovernance } from './pages/ScientificGovernance';
import { JudgeMode } from './pages/JudgeMode';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppShell>
        <Routes>
          {/* 1. Executive Command Center */}
          <Route path="/" element={<Dashboard />} />

          {/* 2. Panchayat Explorer Directory */}
          <Route path="/panchayats" element={<PanchayatExplorer />} />

          {/* 3. Detailed Panchayat Profile */}
          <Route path="/panchayats/:id" element={<PanchayatDetail />} />

          {/* 4. Geospatial 1-km Micro-Grid Intelligence (with legacy alias) */}
          <Route path="/map" element={<GisIntelligence />} />
          <Route path="/gis" element={<GisIntelligence />} />

          {/* 5. Weather Downscaling & What-If Analysis (with legacy alias) */}
          <Route path="/weather-analysis" element={<WeatherAnalysis />} />
          <Route path="/weather" element={<WeatherAnalysis />} />

          {/* 6. Agro-Meteorological Advisories & Explainability (with legacy alias) */}
          <Route path="/advisories" element={<AgroAdvisories />} />
          <Route path="/advisory" element={<AgroAdvisories />} />

          {/* 7. Phase 24 Scientific Governance & Audit (with legacy alias) */}
          <Route path="/system-status" element={<ScientificGovernance />} />
          <Route path="/governance" element={<ScientificGovernance />} />

          {/* 8. Guided SIH Judge Presentation Mode */}
          <Route path="/judge" element={<JudgeMode />} />

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </AppProvider>
  );
};

export default App;
