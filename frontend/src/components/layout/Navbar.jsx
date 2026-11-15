import React from 'react';
import { 
  Flame, 
  Map, 
  GitCompare, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle2, 
  Radio, 
  RefreshCw, 
  GitMerge,
  Layers,
  GitBranch
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, backendStatus, checkingBackend, onRefreshHealth }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'matching', label: 'Matching Engine', icon: GitMerge },
    { id: 'events', label: 'Event Clusters', icon: Layers },
    { id: 'evolution', label: 'Event Evolution', icon: GitBranch },
    { id: 'map', label: 'Fire Map', icon: Map },
    { id: 'comparison', label: 'Sensor Comparison', icon: GitCompare },
    { id: 'activity', label: 'Activity Analysis', icon: Radio },
    { id: 'anomalies', label: 'Anomaly Analysis', icon: AlertTriangle },
    { id: 'quality', label: 'Data Quality', icon: CheckCircle2 },
  ];

  return (
    <header className="sticky top-0 z-50 bg-space-950/80 backdrop-blur-md border-b border-white/[0.08]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => setActiveTab('overview')}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-modis to-viirs flex items-center justify-center shadow-clay text-white transform group-hover:scale-105 transition-transform duration-200">
              <Flame className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-tight">FireLens</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-space-800/80 text-accent-blue border border-white/10 clay-pill">
                  NASA 2026
                </span>
              </div>
              <p className="text-[11px] text-space-400 hidden sm:block">
                Harmonized Satellite Fire Intelligence
              </p>
            </div>
          </div>

          {/* Nav Items Desktop */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  title={item.label}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'clay-button bg-space-800 text-white border border-white/20 shadow-clay-sm'
                      : 'text-space-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-modis' : 'text-space-400'}`} />
                  <span className={isActive ? 'inline' : 'hidden xl:inline'}>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Backend Connection Status Badge */}
          <div className="flex items-center space-x-2">
            <div 
              className={`clay-pill flex items-center space-x-2 px-2.5 py-1 rounded-full text-xs border transition-all duration-200 ${
                backendStatus.online
                  ? 'bg-emerald-950/40 border-emerald-500/35 text-emerald-300 shadow-emerald-950/40'
                  : 'bg-rose-950/40 border-rose-500/35 text-rose-300 shadow-rose-950/40'
              }`}
              title={backendStatus.online ? `API running at ${backendStatus.service}` : backendStatus.error || 'Backend unreachable'}
            >
              {backendStatus.online ? (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              ) : (
                <span className="inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              )}

              <span className="font-mono text-[11px] font-semibold hidden sm:inline">
                {backendStatus.online ? 'API Online' : 'API Offline'}
              </span>

              <button
                onClick={onRefreshHealth}
                disabled={checkingBackend}
                className="text-space-400 hover:text-white transition-transform disabled:opacity-40 ml-1"
                title="Refresh health check"
              >
                <RefreshCw className={`w-3 h-3 ${checkingBackend ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex overflow-x-auto space-x-1 py-2 border-t border-white/[0.08] no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={item.label}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs whitespace-nowrap transition-all duration-150 ${
                  isActive
                    ? 'clay-button bg-space-800 text-white font-semibold border border-white/20 shadow-clay-sm'
                    : 'text-space-400 hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                <Icon className={`w-3 h-3 ${isActive ? 'text-modis' : 'text-space-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
