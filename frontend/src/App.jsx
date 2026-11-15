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
    <div className="min-h-screen flex flex-col bg-space-950 text-space-200">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        backendStatus={backendStatus}
        checkingBackend={checkingBackend}
        onRefreshHealth={checkHealth}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
      <Footer />
    </div>
  );
}
