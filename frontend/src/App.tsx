import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';

// Pages
import { Dashboard } from './pages/Dashboard';
import { ForecastView } from './pages/ForecastView';
import { PanchayatExplorer } from './pages/PanchayatExplorer';
import { PanchayatDetail } from './pages/PanchayatDetail';
import { GisIntelligence } from './pages/GisIntelligence';
import { WeatherAnalysis } from './pages/WeatherAnalysis';
import { AgroAdvisories } from './pages/AgroAdvisories';
import { ScientificGovernance } from './pages/ScientificGovernance';
import { ForecastComparison } from './pages/ForecastComparison';
import { JudgeMode } from './pages/JudgeMode';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppShell>
        <Routes>
          {/* 1. HOME: Weather Intelligence Command Center */}
          <Route path="/" element={<Dashboard />} />

          {/* 2. FORECAST: Operational 7-Day & 24-Hour Diurnal Downscaling */}
          <Route path="/forecast" element={<ForecastView />} />

          {/* 3. PANCHAYATS: Panchayat Explorer & Detail Profiles */}
          <Route path="/panchayats" element={<PanchayatExplorer />} />
          <Route path="/panchayats/:id" element={<PanchayatDetail />} />

          {/* 4. AGRO ADVISORY: Dynamic Rule-Engine Agromet Actions */}
          <Route path="/advisories" element={<AgroAdvisories />} />
          <Route path="/advisory" element={<AgroAdvisories />} />

          {/* 5. MAP: Geospatial 1-km Micro-Grid Intelligence */}
          <Route path="/map" element={<GisIntelligence />} />
          <Route path="/gis" element={<GisIntelligence />} />

          {/* 6. INSIGHTS: Weather Analysis & What-If Scenarios */}
          <Route path="/insights" element={<WeatherAnalysis />} />
          <Route path="/weather-analysis" element={<WeatherAnalysis />} />
          <Route path="/weather" element={<WeatherAnalysis />} />

          {/* 7. SYSTEM: Scientific Governance, Audit & Certification */}
          <Route path="/system-status" element={<ScientificGovernance />} />
          <Route path="/system" element={<ScientificGovernance />} />
          <Route path="/governance" element={<ScientificGovernance />} />

          {/* Diagnostic / Developer Comparison with External Providers */}
          <Route path="/system/forecast-comparison" element={<ForecastComparison />} />

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
