import React from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-[#070a12] text-slate-100 antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 lg:p-6 bg-gradient-to-b from-[#070a12] to-[#0a0f1d]">
          {children}
        </main>
      </div>
    </div>
  );
};
