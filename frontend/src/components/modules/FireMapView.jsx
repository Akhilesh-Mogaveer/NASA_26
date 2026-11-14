import React, { useState, useEffect } from 'react';
import { 
  Map as MapIcon, 
  Layers, 
  Filter, 
  Compass, 
  Flame, 
  Eye, 
  ZoomIn, 
  AlertCircle,
  Globe,
  Radio
} from 'lucide-react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip } from 'react-leaflet';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import { getGridDensity, getGeographicalAnalytics } from '../../api/client';

export default function FireMapView() {
  const [gridCells, setGridCells] = useState([]);
  const [topHotspots, setTopHotspots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [minCount, setMinCount] = useState(500);
  const [sensorFilter, setSensorFilter] = useState('all'); // all, modis, viirs
  const [mapCenter, setMapCenter] = useState([10.0, 20.0]); // Centered globally
  const [mapZoom, setMapZoom] = useState(2);

  useEffect(() => {
    async function fetchMapData() {
      setLoading(true);
      const [densityRes, geoRes] = await Promise.all([
        getGridDensity({ min_count: minCount, limit: 1200 }),
        getGeographicalAnalytics(10)
      ]);

      if (densityRes.success) setGridCells(densityRes.data);
      if (geoRes.success) setTopHotspots(geoRes.data?.top_cells || []);
      if (!densityRes.success && !geoRes.success) {
        setError(densityRes.error || geoRes.error);
      }
      setLoading(false);
    }
    fetchMapData();
  }, [minCount]);

  // Color mapping based on observation count in the 2-degree cell
  const getMarkerColor = (count) => {
    if (count > 25000) return '#ef4444'; // deep red
    if (count > 10000) return '#f97316'; // orange-red
    if (count > 5000) return '#fb923c';  // orange
    if (count > 1000) return '#facc15';  // amber-yellow
    return '#38bdf8';                    // cyan-blue
  };

  // Radius mapping (logarithmic scale)
  const getMarkerRadius = (count) => {
    if (count > 25000) return 11;
    if (count > 10000) return 9;
    if (count > 5000) return 7;
    if (count > 1000) return 5;
    return 3.5;
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <MapIcon className="w-5 h-5 text-modis" />
            <span>Global Active Fire Density Map</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Standardized 2-degree spatial density grid aggregating 22.18M observations from MODIS C6.1 and VIIRS C2 (2025).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge type="modis" label="MODIS Grid" />
          <StatusBadge type="viirs" label="VIIRS Grid" />
          <StatusBadge type="healthy" label={`${gridCells.length} Active 2° Cells`} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters & Navigation Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          <Card title="Observation Filters" subtitle="Density threshold & layer controls">
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-space-300 font-medium mb-1.5 flex justify-between">
                  <span>Min Hot Spots / Cell:</span>
                  <span className="font-mono text-modis font-bold">{minCount.toLocaleString()}</span>
                </label>
                <input
                  type="range"
                  min="50"
                  max="5000"
                  step="50"
                  value={minCount}
                  onChange={(e) => setMinCount(Number(e.target.value))}
                  className="w-full accent-modis cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-space-500 font-mono mt-1">
                  <span>50 (Sparse)</span>
                  <span>5,000 (Megafires)</span>
                </div>
              </div>

              {/* Legend */}
              <div className="pt-2 border-t border-space-800">
                <span className="text-[11px] font-semibold text-space-300 block mb-2">
                  Observation Density Scale (per 2° Cell)
                </span>
                <div className="space-y-1.5 font-mono text-[11px]">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                      &gt; 25,000 obs
                    </span>
                    <span className="text-space-400">Extreme</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full bg-orange-500 inline-block" />
                      10,000 – 25,000
                    </span>
                    <span className="text-space-400">High</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full bg-amber-400 inline-block" />
                      1,000 – 10,000
                    </span>
                    <span className="text-space-400">Moderate</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full bg-sky-400 inline-block" />
                      &lt; 1,000 obs
                    </span>
                    <span className="text-space-400">Low</span>
                  </div>
                </div>
              </div>

              {/* Quick Jump Hotspot Regions */}
              <div className="pt-2 border-t border-space-800">
                <span className="text-[11px] font-semibold text-space-300 block mb-2">
                  Regional Hotspot Bookmarks
                </span>
                <div className="space-y-1">
                  <button
                    onClick={() => { setMapCenter([-6.0, 20.0]); setMapZoom(4); }}
                    className="w-full text-left p-2 rounded bg-space-900 hover:bg-space-800 text-space-300 hover:text-white transition-colors flex items-center justify-between"
                  >
                    <span>Central Africa (Savanna)</span>
                    <span className="font-mono text-modis text-[10px]">#1 Global</span>
                  </button>
                  <button
                    onClick={() => { setMapCenter([-12.0, -55.0]); setMapZoom(4); }}
                    className="w-full text-left p-2 rounded bg-space-900 hover:bg-space-800 text-space-300 hover:text-white transition-colors flex items-center justify-between"
                  >
                    <span>Amazon / Cerrado (Brazil)</span>
                    <span className="font-mono text-viirs text-[10px]">#2 Global</span>
                  </button>
                  <button
                    onClick={() => { setMapCenter([16.0, 100.0]); setMapZoom(4); }}
                    className="w-full text-left p-2 rounded bg-space-900 hover:bg-space-800 text-space-300 hover:text-white transition-colors flex items-center justify-between"
                  >
                    <span>Southeast Asia (Agri)</span>
                    <span className="font-mono text-space-400 text-[10px]">Seasonal</span>
                  </button>
                  <button
                    onClick={() => { setMapCenter([58.0, 100.0]); setMapZoom(3); }}
                    className="w-full text-left p-2 rounded bg-space-900 hover:bg-space-800 text-space-300 hover:text-white transition-colors flex items-center justify-between"
                  >
                    <span>Siberian Boreal Zone</span>
                    <span className="font-mono text-space-400 text-[10px]">Wildfire</span>
                  </button>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Live Leaflet Map Canvas */}
        <div className="lg:col-span-3 space-y-4">
          <div className="relative rounded-2xl bg-space-900 border border-space-700/80 h-[520px] overflow-hidden shadow-lg">
            {loading && (
              <div className="absolute inset-0 bg-space-950/70 z-20 flex items-center justify-center text-xs text-space-300 space-x-2">
                <Compass className="w-5 h-5 animate-spin text-modis" />
                <span>Loading 2° active-fire grid clusters...</span>
              </div>
            )}

            <MapContainer
              center={mapCenter}
              zoom={mapZoom}
              style={{ height: '100%', width: '100%', backgroundColor: '#070b12' }}
              scrollWheelZoom={true}
            >
              {/* CartoDB Dark Matter Basemap */}
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                maxZoom={18}
              />

              {/* Render 2-Degree Grid Circles */}
              {gridCells.map((cell, idx) => {
                const centerLat = cell.lat_bin + 1.0;
                const centerLon = cell.lon_bin + 1.0;
                const color = getMarkerColor(cell.total_count);
                const radius = getMarkerRadius(cell.total_count);

                return (
                  <CircleMarker
                    key={`${cell.lat_bin}_${cell.lon_bin}_${idx}`}
                    center={[centerLat, centerLon]}
                    radius={radius}
                    pathOptions={{
                      color: color,
                      fillColor: color,
                      fillOpacity: 0.65,
                      weight: 1,
                    }}
                  >
                    <Popup>
                      <div className="p-1 space-y-2 text-xs">
                        <div className="flex items-center justify-between border-b border-space-800 pb-1.5">
                          <span className="font-bold text-white font-mono">
                            Cell [{cell.lat_bin}°, {cell.lon_bin}°]
                          </span>
                          <span className="text-[10px] font-mono text-modis font-semibold">2° × 2° Grid</span>
                        </div>
                        <div className="space-y-1 font-mono text-[11px]">
                          <div className="flex justify-between">
                            <span className="text-space-400 font-sans">Total Hot Spots:</span>
                            <span className="font-bold text-white">{cell.total_count.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-modis font-sans">MODIS Detections:</span>
                            <span className="text-modis">{cell.modis_count.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-viirs font-sans">VIIRS Detections:</span>
                            <span className="text-viirs">{cell.viirs_count.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-space-400 font-sans">Mean FRP:</span>
                            <span className="text-space-200">{cell.mean_frp} MW</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-space-400 font-sans">Total Power:</span>
                            <span className="text-amber-400">{(cell.total_frp / 1000).toFixed(1)} GW</span>
                          </div>
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          </div>

          {/* Top 5 Global Hotspot Cells Table */}
          <Card 
            title="Top Global Hotspot Clusters (2025)" 
            subtitle="The highest active-fire density cells recorded across 22.18M observations"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left font-mono">
                <thead className="bg-space-900 border-b border-space-800 text-space-400 font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3 font-sans">Rank</th>
                    <th className="py-2.5 px-3">2° Grid Center</th>
                    <th className="py-2.5 px-3 text-modis">MODIS</th>
                    <th className="py-2.5 px-3 text-viirs">VIIRS</th>
                    <th className="py-2.5 px-3 text-white">Active-Fire Observations</th>
                    <th className="py-2.5 px-3 text-amber-400">Mean FRP</th>
                    <th className="py-2.5 px-3 font-sans">Geographic Locus (2° Cell Bounds)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-space-800/60">
                  {topHotspots.slice(0, 5).map((hotspot, idx) => (
                    <tr key={idx} className="hover:bg-space-900/40">
                      <td className="py-2 px-3 font-sans font-bold text-space-300">#{idx + 1}</td>
                      <td className="py-2 px-3 text-space-200">{hotspot.lat_bin + 1}°, {hotspot.lon_bin + 1}°</td>
                      <td className="py-2 px-3 text-modis">{hotspot.modis_count.toLocaleString()}</td>
                      <td className="py-2 px-3 text-viirs">{hotspot.viirs_count.toLocaleString()}</td>
                      <td className="py-2 px-3 font-bold text-white">{hotspot.total_count.toLocaleString()}</td>
                      <td className="py-2 px-3 text-amber-400">{hotspot.mean_frp} MW</td>
                      <td className="py-2 px-3 font-sans text-space-300 text-[11px]">
                        [{hotspot.lat_bin}°, {hotspot.lat_bin + 2}°] Lat, [{hotspot.lon_bin}°, {hotspot.lon_bin + 2}°] Lon
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
