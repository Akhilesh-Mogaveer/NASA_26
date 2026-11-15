import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import OverviewView from './components/modules/OverviewView';
import MatchingView from './components/modules/MatchingView';
import EventExplorerView from './components/modules/EventExplorerView';
import EventEvolutionView from './views/EventEvolutionView';
import FireMapView from './components/modules/FireMapView';
import ComparisonView from './components/modules/ComparisonView';
import ActivityView from './components/modules/ActivityView';
import AnomalyView from './components/modules/AnomalyView';
import QualityView from './components/modules/QualityView';
import { getHealthStatus } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [backendStatus, setBackendStatus] = useState({
    online: false,
    data: null,
    error: null,
    lastChecked: null,
  });
  const [checkingBackend, setCheckingBackend] = useState(false);

  const checkHealth = useCallback(async () => {
    setCheckingBackend(true);
    const result = await getHealthStatus();
    if (result.success) {
      setBackendStatus({
        online: true,
        data: result.data,
        error: null,
        lastChecked: result.timestamp,
      });
    } else {
      setBackendStatus({
        online: false,
        data: null,
        error: result.error,
        lastChecked: result.timestamp,
      });
    }
    setCheckingBackend(false);
  }, []);

  useEffect(() => {
    // Initial health check on application mount
    checkHealth();

    // Auto-poll health every 15 seconds
    const interval = setInterval(() => {
      checkHealth();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <div className="min-h-screen flex flex-col bg-space-950 text-space-200 relative overflow-x-hidden">
      {/* Ambient Glassmorphic Background Refraction Layer */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden" aria-hidden="true">
        {/* Warm Orange MODIS Orb (top-left) */}
        <div className="absolute -top-32 -left-32 w-[550px] h-[550px] rounded-full bg-modis/20 blur-[130px] transform-gpu" />
        {/* Instrument Cyan Orb (center-right) */}
        <div className="absolute top-1/3 -right-32 w-[600px] h-[600px] rounded-full bg-accent-blue/15 blur-[140px] transform-gpu" />
        {/* Radiant Red VIIRS Orb (bottom-center) */}
        <div className="absolute -bottom-40 left-1/4 w-[650px] h-[650px] rounded-full bg-viirs/18 blur-[150px] transform-gpu" />
        {/* Subtle CSS Noise Grain Overlay */}
        <div className="absolute inset-0 ambient-grain opacity-40" />
      </div>

      {/* Top Navigation */}
      <div className="relative z-40">
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          backendStatus={backendStatus}
          checkingBackend={checkingBackend}
          onRefreshHealth={checkHealth}
        />
      </div>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'overview' && (
          <OverviewView
            backendStatus={backendStatus}
            checkingBackend={checkingBackend}
            onRefreshHealth={checkHealth}
            setActiveTab={setActiveTab}
          />
        )}
        {activeTab === 'matching' && <MatchingView />}
        {activeTab === 'events' && <EventExplorerView />}
        {activeTab === 'evolution' && <EventEvolutionView />}
        {activeTab === 'map' && <FireMapView setActiveTab={setActiveTab} />}
        {activeTab === 'comparison' && <ComparisonView />}
        {activeTab === 'activity' && <ActivityView />}
        {activeTab === 'anomalies' && <AnomalyView />}
        {activeTab === 'quality' && <QualityView backendStatus={backendStatus} />}
      </main>

      {/* Global Scientific Attribution & Status Footer */}
      <div className="relative z-10">
        <Footer />
      </div>
    </div>
  );
}
