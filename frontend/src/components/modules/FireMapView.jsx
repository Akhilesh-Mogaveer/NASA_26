import React from 'react';
import { Map, Layers, Filter, Compass } from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function FireMapView() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Map className="w-5 h-5 text-modis" />
            <span>Interactive Fire Map</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Geospatial exploration of harmonized MODIS and VIIRS active-fire hot spots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge type="modis" label="MODIS Layer (Ready for Phase 7)" />
          <StatusBadge type="viirs" label="VIIRS Layer (Ready for Phase 7)" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          <Card title="Observation Filters" subtitle="Sensor & time selection">
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-space-300 font-medium mb-1.5">Sensor Instrument</label>
                <div className="grid grid-cols-2 gap-2">
                  <button className="px-3 py-2 rounded-lg bg-modis/15 border border-modis/40 text-modis-light font-medium text-center">
                    MODIS (1km)
                  </button>
                  <button className="px-3 py-2 rounded-lg bg-viirs/15 border border-viirs/40 text-viirs-light font-medium text-center">
                    VIIRS (375m)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-space-300 font-medium mb-1.5">Temporal Window</label>
                <input
                  type="date"
                  disabled
                  defaultValue="2026-11-14"
                  className="w-full bg-space-900 border border-space-700 rounded-lg px-3 py-2 text-space-300 text-xs focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-space-300 font-medium mb-1.5">Min FRP (MW)</label>
                <input
                  type="range"
                  min="0"
                  max="500"
                  defaultValue="10"
                  disabled
                  className="w-full accent-modis"
                />
              </div>

              <div className="p-3 rounded-lg bg-space-900 border border-space-800 text-[11px] text-space-400 leading-relaxed">
                Map controls will activate in Phase 7 upon completion of the Ingestion (Phase 2), Normalization (Phase 3), and Harmonization (Phase 4) engines.
              </div>
            </div>
          </Card>
        </div>

        {/* Map Canvas Preview Container */}
        <div className="lg:col-span-3">
          <div className="relative rounded-2xl bg-space-900 border border-space-700/80 h-[520px] flex flex-col items-center justify-center p-6 text-center overflow-hidden">
            {/* Grid background effect */}
            <div 
              className="absolute inset-0 opacity-15"
              style={{
                backgroundImage: 'radial-gradient(#526b91 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />

            <div className="relative z-10 max-w-md space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-space-800 border border-space-700 flex items-center justify-center mx-auto shadow-inner text-modis">
                <Compass className="w-8 h-8 animate-pulse" />
              </div>
              <h3 className="text-lg font-bold text-white">Geospatial Leaflet Container Initialized</h3>
              <p className="text-xs text-space-400 leading-relaxed">
                Leaflet and React-Leaflet dependencies are integrated and verified. During Phase 2, real NASA FIRMS observations will populate this canvas with sensor-distinguishable markers, cluster overlays, and hot-spot inspection popups.
              </p>
              <div className="flex justify-center gap-3 font-mono text-[11px] text-space-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-modis" />
                  MODIS Flame
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-viirs" />
                  VIIRS High-Res
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  Associated Match
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
