import React from 'react';
import { 
  Flame, 
  Map, 
  GitCompare, 
  BarChart3, 
  AlertTriangle, 
  CheckCircle2, 
  Radio, 
  Wifi, 
  WifiOff, 
  RefreshCw 
} from 'lucide-react';
import StatusBadge from '../common/StatusBadge';

export default function Navbar({ activeTab, setActiveTab, backendStatus, checkingBackend, onRefreshHealth }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'map', label: 'Fire Map', icon: Map },
    { id: 'comparison', label: 'Sensor Comparison', icon: GitCompare },
    { id: 'activity', label: 'Activity Analysis', icon: Radio },
    { id: 'anomalies', label: 'Anomaly Analysis', icon: AlertTriangle },
    { id: 'quality', label: 'Data Quality', icon: CheckCircle2 },
  ];

  return (
    <header className="sticky top-0 z-50 bg-space-900/90 backdrop-blur-md border-b border-space-700/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('overview')}>
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-modis to-viirs flex items-center justify-center shadow-md shadow-modis/20">
              <Flame className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-tight">FireLens</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-space-800 text-accent-blue border border-space-700">
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
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-space-800 text-white border border-space-600 shadow-sm'
                      : 'text-space-400 hover:text-space-200 hover:bg-space-850/60'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-modis' : 'text-space-500'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Backend Connection Status Badge */}
          <div className="flex items-center space-x-2">
            <div 
              className={`flex items-center space-x-2 px-2.5 py-1 rounded-full text-xs border transition-all ${
                backendStatus.online
                  ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
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

              <span className="font-mono text-[11px] hidden sm:inline">
                {backendStatus.online ? 'API Online' : 'API Offline'}
              </span>

              <button
                onClick={onRefreshHealth}
                disabled={checkingBackend}
                className="text-space-400 hover:text-white transition-transform disabled:opacity-50 ml-1"
                title="Refresh health check"
              >
                <RefreshCw className={`w-3 h-3 ${checkingBackend ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex overflow-x-auto space-x-1 py-2 border-t border-space-800">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs whitespace-nowrap ${
                  isActive
                    ? 'bg-space-800 text-white font-medium'
                    : 'text-space-400 hover:text-space-200'
                }`}
              >
                <Icon className={`w-3 h-3 ${isActive ? 'text-modis' : 'text-space-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
