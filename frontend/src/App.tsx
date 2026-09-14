import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';

import { Overview } from './pages/Overview';
import { PanchayatExplorer } from './pages/PanchayatExplorer';
import { PanchayatDetail } from './pages/PanchayatDetail';
import { GisMapPage } from './pages/GisMapPage';
import { WeatherAnalysis } from './pages/WeatherAnalysis';
import { AdvisoryHub } from './pages/AdvisoryHub';
import { SystemGovernance } from './pages/SystemGovernance';
import { JudgeMode } from './pages/JudgeMode';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-emerald-500 selection:text-slate-950">
          {/* Sidebar */}
          <Sidebar />

          {/* Main Layout Area */}
          <div className="flex-1 flex flex-col min-w-0">
            <Header />

            <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/judge" element={<JudgeMode />} />
                <Route path="/panchayats" element={<PanchayatExplorer />} />
                <Route path="/panchayats/:id" element={<PanchayatDetail />} />
                <Route path="/map" element={<GisMapPage />} />
                <Route path="/weather-analysis" element={<WeatherAnalysis />} />
                <Route path="/advisories" element={<AdvisoryHub />} />
                <Route path="/system-status" element={<SystemGovernance />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-800/80 py-4 px-6 text-center text-xs text-slate-500 bg-slate-950/80">
              <p>
                Smart India Hackathon (SIH) &bull; Problem Statement 26074 &bull; Downscaling Weather Forecasts for Agro-Meteorological Advisory Services
              </p>
            </footer>
          </div>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
