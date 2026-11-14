import React, { useState, useEffect } from 'react';
import { 
  GitCompare, 
  Sliders, 
  CheckCircle2, 
  AlertCircle, 
  Zap, 
  Maximize2, 
  Flame, 
  Layers,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import { getSensorComparison, getFRPAnalytics } from '../../api/client';

export default function ComparisonView() {
  const [comparison, setComparison] = useState(null);
  const [frpData, setFRPData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [compRes, frpRes] = await Promise.all([
        getSensorComparison(),
        getFRPAnalytics()
      ]);
      if (compRes.success) setComparison(compRes.data);
      if (frpRes.success) setFRPData(frpRes.data);
      if (!compRes.success && !frpRes.success) {
        setError(compRes.error || frpRes.error);
      }
      setLoading(false);
    }
    fetchData();
  }, []);

  const histogram = frpData?.histogram || [];
  const obs = comparison?.observations || {};
  const frpComp = comparison?.frp_comparison || {};
  const confDist = comparison?.confidence_distribution || {};

  const formatThousands = (val) => `${(val / 1000).toFixed(0)}k`;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-accent-blue" />
            <span>Multi-Sensor Comparative Analysis</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Empirical side-by-side evaluation of MODIS C6.1 and VIIRS C2 active-fire detection properties (2025).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge type="modis" label="MODIS 1km" />
          <StatusBadge type="viirs" label="VIIRS 375m" />
          <StatusBadge type="healthy" label="Discrepancy Ratio: 4.979x" />
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs text-space-400 animate-pulse">
          Loading multi-sensor comparative metrics...
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span>Error loading sensor comparison: {error}</span>
        </div>
      ) : (
        <>
          {/* Key Metric Comparison Table */}
          <Card 
            title="Core Instrument & Metric Comparison" 
            subtitle="Quantitative assessment based on 22,175,341 observations from the 2025 calendar year"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-space-900 border-b border-space-800 text-space-400 font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Evaluation Metric</th>
                    <th className="py-3 px-4 text-modis">MODIS C6.1 (Terra / Aqua)</th>
                    <th className="py-3 px-4 text-viirs">VIIRS C2 (NOAA-20)</th>
                    <th className="py-3 px-4 text-space-200">Comparison &amp; Physical Driver</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-space-800/60 font-mono">
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Observation Count</td>
                    <td className="py-2.5 px-4 font-bold text-modis">{obs.modis_count?.toLocaleString()}</td>
                    <td className="py-2.5 px-4 font-bold text-viirs">{obs.viirs_count?.toLocaleString()}</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      VIIRS detects <strong className="text-white font-mono">{obs.viirs_to_modis_ratio}x</strong> more hot spots
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Nadir Spatial Resolution</td>
                    <td className="py-2.5 px-4 text-space-200">1,000 m (1.0 km²)</td>
                    <td className="py-2.5 px-4 text-space-200">375 m (0.14 km²)</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      MODIS pixel area is <strong className="text-white font-mono">7.11x</strong> larger at nadir
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Mean Fire Radiative Power</td>
                    <td className="py-2.5 px-4 font-bold text-modis">{frpComp.modis_mean_mw} MW</td>
                    <td className="py-2.5 px-4 font-bold text-viirs">{frpComp.viirs_mean_mw} MW</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      MODIS mean is <strong className="text-white font-mono">{frpComp.ratio_mean_frp}x</strong> higher (thermal dilution)
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Median Fire Radiative Power</td>
                    <td className="py-2.5 px-4 text-space-200">{frpComp.modis_median_mw} MW</td>
                    <td className="py-2.5 px-4 text-space-200">{frpComp.viirs_median_mw} MW</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      VIIRS resolves small, smoldering sub-pixel fires
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Integrated Total Energy (2025)</td>
                    <td className="py-2.5 px-4 text-space-200">{(frpComp.modis_total_mw / 1e6).toFixed(1)}M MW</td>
                    <td className="py-2.5 px-4 text-space-200">{(frpComp.viirs_total_mw / 1e6).toFixed(1)}M MW</td>
                    <td className="py-2.5 px-4 font-sans text-emerald-400 font-semibold">
                      Total energy remarkably close (+17% difference)
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Scan Edge Footprint Growth</td>
                    <td className="py-2.5 px-4 text-rose-300">~10x (~9.6 km²)</td>
                    <td className="py-2.5 px-4 text-emerald-300">~4x (~0.64 km²)</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      VIIRS onboard pixel aggregation limits bow-tie distortion
                    </td>
                  </tr>
                  <tr className="hover:bg-space-900/40">
                    <td className="py-2.5 px-4 font-sans font-medium text-space-300">Confidence Scale Format</td>
                    <td className="py-2.5 px-4 text-space-300">0% – 100% (Numeric)</td>
                    <td className="py-2.5 px-4 text-space-300">low, nominal, high (Categorical)</td>
                    <td className="py-2.5 px-4 font-sans text-space-300">
                      Requires categorical harmonization mapping
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>

          {/* FRP Distribution Histogram */}
          <Card 
            title="Fire Radiative Power (MW) Histogram Distribution" 
            subtitle="Comparing detection counts across logarithmic power bins — Revealing why VIIRS detects 5x more fires"
          >
            <div className="h-80 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histogram} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="bin_label" stroke="#64748b" tick={{ fontSize: 11 }} label={{ value: 'FRP Range (Megawatts)', position: 'insideBottom', offset: -10, fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis stroke="#64748b" tickFormatter={formatThousands} tick={{ fontSize: 11 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(value) => [value.toLocaleString(), 'Observations']}
                  />
                  <Legend wrapperStyle={{ paddingTop: '15px', fontSize: '12px' }} />
                  <Bar dataKey="modis_count" name="MODIS C6.1" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="viirs_count" name="VIIRS C2" fill="#f97316" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="p-3 mt-2 rounded-lg bg-space-900 border border-space-800 text-xs text-space-300 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-accent-blue mt-0.5 flex-shrink-0" />
              <p>
                <strong>Scientific Insight:</strong> In the <code>0–5 MW</code> bin alone, VIIRS detected <strong>9,148,369</strong> observations compared to only <strong>84,755</strong> for MODIS. Because a 1km² MODIS pixel requires substantial integrated thermal energy to trigger detection, small low-intensity fires remain invisible to MODIS but are readily resolved by VIIRS.
              </p>
            </div>
          </Card>

          {/* Harmonized Confidence Levels and Physical Divergence */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confidence Breakdown */}
            <Card title="Harmonized Confidence Breakdown" subtitle="Standardized Low / Nominal / High levels">
              <div className="space-y-4 pt-2">
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-modis font-semibold">MODIS C6.1 Categories</span>
                    <span className="font-mono text-space-400">Continuous 0-100% mapped</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs text-center">
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-space-400 block text-[10px] uppercase font-sans">Low (&lt;30%)</span>
                      <span className="font-bold text-space-200">
                        {confDist.modis?.category_percentages?.low || 12.3}%
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-accent-blue block text-[10px] uppercase font-sans">Nominal (30-79%)</span>
                      <span className="font-bold text-space-200">
                        {confDist.modis?.category_percentages?.nominal || 63.8}%
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-emerald-400 block text-[10px] uppercase font-sans">High (&ge;80%)</span>
                      <span className="font-bold text-space-200">
                        {confDist.modis?.category_percentages?.high || 23.9}%
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-viirs font-semibold">VIIRS C2 Categories</span>
                    <span className="font-mono text-space-400">Native flags (l, n, h)</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs text-center">
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-space-400 block text-[10px] uppercase font-sans">Low (&apos;l&apos;)</span>
                      <span className="font-bold text-space-200">
                        {confDist.viirs?.category_percentages?.low || 16.5}%
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-accent-blue block text-[10px] uppercase font-sans">Nominal (&apos;n&apos;)</span>
                      <span className="font-bold text-space-200">
                        {confDist.viirs?.category_percentages?.nominal || 72.1}%
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-space-900 border border-space-800">
                      <span className="text-emerald-400 block text-[10px] uppercase font-sans">High (&apos;h&apos;)</span>
                      <span className="font-bold text-space-200">
                        {confDist.viirs?.category_percentages?.high || 11.4}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Principles for Phase 4 Harmonization */}
            <Card title="Design Foundation for Phase 4 Harmonization" subtitle="Architectural rules derived from EDA">
              <div className="space-y-3 text-xs leading-relaxed text-space-300">
                <div className="p-2.5 rounded-lg bg-space-900/80 border border-space-800">
                  <span className="font-semibold text-white block mb-0.5">1. Adaptive Spatial Search Radius</span>
                  <span className="text-space-400 text-[11px]">
                    Pixel footprint expands away from nadir. Search radius adapts between <strong>1.25 km (nadir)</strong> and <strong>3.5 km (scan edge)</strong> based on scan angle.
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-space-900/80 border border-space-800">
                  <span className="font-semibold text-white block mb-0.5">2. Many-to-One (N:1) Association</span>
                  <span className="text-space-400 text-[11px]">
                    Because VIIRS pixels are 7x smaller, multiple VIIRS hot spots correspond to a single physical MODIS detection. VIIRS clusters are aggregated rather than 1:1 mapped.
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-space-900/80 border border-space-800">
                  <span className="font-semibold text-white block mb-0.5">3. Temporal Window Gating (&Delta;t &le; 90 min)</span>
                  <span className="text-space-400 text-[11px]">
                    Separates true simultaneous observations (Aqua &amp; NOAA-20 13:30 pass) from diurnal fire propagation across passes.
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
