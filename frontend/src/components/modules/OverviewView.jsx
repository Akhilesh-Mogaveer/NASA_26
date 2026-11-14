import React from 'react';
import { 
  Satellite, 
  Activity, 
  Layers, 
  Server, 
  ShieldCheck, 
  FolderCheck, 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight,
  Flame,
  Radio,
  Clock,
  Compass
} from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function OverviewView({ backendStatus, checkingBackend, onRefreshHealth, setActiveTab }) {
  return (
    <div className="space-y-6">
      {/* Platform Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-space-900 via-space-850 to-space-900 border border-space-700/80 p-6 sm:p-8">
        <div className="absolute top-0 right-0 -mt-6 -mr-6 w-56 h-56 bg-modis/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 -mb-8 w-48 h-48 bg-viirs/10 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <StatusBadge type="modis" label="MODIS 1km" />
            <StatusBadge type="viirs" label="VIIRS 375m" />
            <StatusBadge type="healthy" label="Phase 2.5: Real NASA Data Verified" />
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Harmonized Satellite Fire Intelligence
          </h1>
          <p className="mt-2 text-sm sm:text-base text-space-300 leading-relaxed">
            FireLens bridges observations from NASA&apos;s MODIS and VIIRS satellite sensors.
            By reconciling differing spatial footprints and overpass schedules, the platform provides a unified observation space while preserving original sensor integrity.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setActiveTab('map')}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-modis hover:bg-modis-dark text-white text-xs font-semibold shadow-md shadow-modis/25 transition-all"
            >
              <span>Explore Fire Map</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActiveTab('comparison')}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-space-800 hover:bg-space-700 text-space-200 border border-space-600 text-xs font-medium transition-all"
            >
              <span>Sensor Harmonization</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Live Backend Telemetry & Quick Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Backend API Health Card */}
        <Card
          title="Backend API Connectivity"
          subtitle="Real-time FastAPI verification probe"
          action={
            <button
              onClick={onRefreshHealth}
              disabled={checkingBackend}
              className="text-xs text-space-400 hover:text-white px-2 py-1 rounded bg-space-800 border border-space-700 hover:border-space-600 transition-colors disabled:opacity-50"
            >
              {checkingBackend ? 'Testing...' : 'Test Connection'}
            </button>
          }
          className="lg:col-span-1"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-space-900 border border-space-800">
              <div className="flex items-center space-x-2.5">
                <Server className="w-4 h-4 text-accent-blue" />
                <span className="text-xs font-medium text-space-300">FastAPI Service</span>
              </div>
              <StatusBadge
                type={backendStatus.online ? 'healthy' : 'error'}
                label={backendStatus.online ? 'Healthy' : 'Disconnected'}
              />
            </div>

            {backendStatus.online ? (
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-space-800">
                  <span className="text-space-400">API Endpoint</span>
                  <span className="font-mono text-space-200">GET /api/health</span>
                </div>
                <div className="flex justify-between py-1 border-b border-space-800">
                  <span className="text-space-400">Service Name</span>
                  <span className="font-mono text-space-200">{backendStatus.data?.service || 'FireLens API'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-space-800">
                  <span className="text-space-400">API Version</span>
                  <span className="font-mono text-space-200">{backendStatus.data?.version || '0.1.0'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-space-800">
                  <span className="text-space-400">Last Probed</span>
                  <span className="font-mono text-space-300">
                    {backendStatus.lastChecked ? new Date(backendStatus.lastChecked).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>

                <div className="pt-2">
                  <span className="text-[11px] font-semibold text-space-300 uppercase tracking-wider block mb-2">
                    Storage Directories Verified
                  </span>
                  <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                    {backendStatus.data?.data_directories &&
                      Object.entries(backendStatus.data.data_directories).map(([dir, exists]) => (
                        <div key={dir} className="flex items-center space-x-1.5 p-1.5 rounded bg-space-900/60 border border-space-800">
                          {exists ? (
                            <FolderCheck className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                          )}
                          <span className="text-space-300 truncate">{dir}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-rose-950/20 border border-rose-500/20 text-xs text-rose-300 space-y-2">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span className="font-semibold">Backend Unreachable</span>
                </div>
                <p className="text-space-400 text-[11px] leading-relaxed">
                  Start the FastAPI backend with:
                </p>
                <code className="block bg-space-950 p-2 rounded text-space-300 font-mono text-[11px]">
                  cd backend<br />
                  .\venv\Scripts\activate<br />
                  uvicorn app.main:app --reload
                </code>
              </div>
            )}
          </div>
        </Card>

        {/* Sensor Characteristics Card */}
        <Card
          title="Instrument Specifications"
          subtitle="Optical & radiometer comparison"
          className="lg:col-span-2"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* MODIS Box */}
            <div className="p-4 rounded-xl bg-space-900/80 border border-modis/30 hover:border-modis/60 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-modis" />
                  <h4 className="font-bold text-space-100 text-sm">MODIS</h4>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-modis/10 text-modis-light border border-modis/30">
                  Terra &bull; Aqua
                </span>
              </div>
              <ul className="space-y-2 text-xs text-space-300">
                <li className="flex justify-between">
                  <span className="text-space-400">Spatial Resolution:</span>
                  <span className="font-mono text-space-200">1 km nominal (at nadir)</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Detection Bands:</span>
                  <span className="font-mono text-space-200">4 &mu;m &amp; 11 &mu;m</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Confidence Scale:</span>
                  <span className="font-mono text-space-200">0% – 100% (Numeric)</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Overpass Coverage:</span>
                  <span className="font-mono text-space-200">~4 passes / day</span>
                </li>
              </ul>
            </div>

            {/* VIIRS Box */}
            <div className="p-4 rounded-xl bg-space-900/80 border border-viirs/30 hover:border-viirs/60 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-viirs" />
                  <h4 className="font-bold text-space-100 text-sm">VIIRS</h4>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-viirs/10 text-viirs-light border border-viirs/30">
                  Suomi-NPP &bull; NOAA-20
                </span>
              </div>
              <ul className="space-y-2 text-xs text-space-300">
                <li className="flex justify-between">
                  <span className="text-space-400">Spatial Resolution:</span>
                  <span className="font-mono text-space-200">375 m high resolution</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Detection Bands:</span>
                  <span className="font-mono text-space-200">I-4 (3.74 &mu;m) &amp; I-5 (11.45 &mu;m)</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Confidence Scale:</span>
                  <span className="font-mono text-space-200">Low, Nominal, High</span>
                </li>
                <li className="flex justify-between">
                  <span className="text-space-400">Footprint Advantage:</span>
                  <span className="font-mono text-space-200">Reduced edge-of-scan distortion</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-4 p-3 rounded-lg bg-space-900/60 border border-space-800 text-xs text-space-400 flex items-start space-x-2.5">
            <ShieldCheck className="w-4 h-4 text-accent-blue mt-0.5 flex-shrink-0" />
            <p>
              <strong className="text-space-200">Scientific Responsibility:</strong> Because MODIS and VIIRS differ in spatial resolution, detection thresholds, and confidence representations, FireLens does not simply merge them or average coordinates. Instead, it computes spatial-temporal associations with preserved provenance.
            </p>
          </div>
        </Card>
      </div>

      {/* System Pipeline & Phase Roadmap */}
      <Card
        title="Harmonization Pipeline & Development Lifecycle"
        subtitle="End-to-end data processing workflow for NASA Space Apps 2026"
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-space-900/70 border border-emerald-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                PHASE 1 &bull; COMPLETE
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <h5 className="font-semibold text-white text-sm">System Foundation</h5>
            <p className="text-xs text-space-400 mt-1 leading-relaxed">
              React + Vite frontend, FastAPI backend, CORS, health probes, Pydantic schemas, and data folder hierarchy.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-900/70 border border-emerald-500/40 relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                PHASE 2 &bull; VERIFIED
              </span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <h5 className="font-semibold text-white text-sm">Real NASA Data Validated</h5>
            <p className="text-xs text-space-400 mt-1 leading-relaxed">
              22.17M real NASA observations ingested, validated, and normalized without dropping invalid records.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-900/70 border border-space-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-space-800 text-space-300 font-bold">
                PHASE 3 &ndash; 4
              </span>
              <Layers className="w-4 h-4 text-space-500" />
            </div>
            <h5 className="font-semibold text-space-200 text-sm">Harmonization Engine</h5>
            <p className="text-xs text-space-400 mt-1 leading-relaxed">
              Geodesic spatial distance &amp; &Delta;t temporal association matrix. Classify observations as matched, unmatched, or uncertain.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-space-900/70 border border-space-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-space-800 text-space-300 font-bold">
                PHASE 5 &ndash; 7
              </span>
              <Radio className="w-4 h-4 text-space-500" />
            </div>
            <h5 className="font-semibold text-space-200 text-sm">Analytics &amp; Map</h5>
            <p className="text-xs text-space-400 mt-1 leading-relaxed">
              Leaflet geospatial fire layers, sensor comparison metrics, statistical Z-score anomaly detection, and data quality reports.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
