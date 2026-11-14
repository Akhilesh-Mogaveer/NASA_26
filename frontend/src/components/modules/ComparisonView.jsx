import React from 'react';
import { GitCompare, Sliders, CheckCircle2, AlertCircle } from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function ComparisonView() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-accent-blue" />
            <span>Sensor Comparison &amp; Association</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Compare MODIS vs. VIIRS observations and inspect spatial-temporal association metrics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge type="info" label="Methodology: Section 7 & 8" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Spatial Threshold (D)" subtitle="Configurable matching radius">
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center text-space-300">
              <span>Default Threshold:</span>
              <span className="font-mono text-modis font-semibold">1.5 km</span>
            </div>
            <p className="text-space-400 text-[11px] leading-relaxed">
              Based on nominal 1km MODIS footprint and 375m VIIRS resolution with scan angle variation.
            </p>
          </div>
        </Card>

        <Card title="Temporal Window (Δt)" subtitle="Maximum observation time delta">
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center text-space-300">
              <span>Default Window:</span>
              <span className="font-mono text-accent-blue font-semibold">&plusmn; 90 minutes</span>
            </div>
            <p className="text-space-400 text-[11px] leading-relaxed">
              Reconciles Terra/Aqua and Suomi-NPP/NOAA-20 orbit crossing times for identical wildfire events.
            </p>
          </div>
        </Card>

        <Card title="Matching Categories" subtitle="Association classifications">
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 font-medium">Matched:</span>
              <span className="text-space-400 text-[11px]">D &le; 1.5km &amp; &Delta;t &le; 90m</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-amber-400 font-medium">Uncertain:</span>
              <span className="text-space-400 text-[11px]">Multiple ambiguous candidates</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-space-300 font-medium">Unmatched:</span>
              <span className="text-space-400 text-[11px]">Isolated sensor detection</span>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Harmonization Methodology Architecture">
        <div className="p-4 rounded-xl bg-space-900 border border-space-800 text-xs text-space-300 space-y-3 leading-relaxed">
          <p>
            <strong className="text-white">Core Innovation:</strong> Traditional wildfire dashboards either display raw dots or naively merge datasets, artificially doubling fire counts or obscuring differing sensor sensitivities. FireLens builds a clean bipartite association graph:
          </p>
          <div className="p-3 bg-space-950 rounded-lg font-mono text-[11px] text-space-300 border border-space-800">
            Candidate Pair Condition: D(MODIS_i, VIIRS_j) &le; D_threshold AND |t_MODIS_i - t_VIIRS_j| &le; T_threshold
          </div>
          <p className="text-space-400 text-[11px]">
            This engine will be fully implemented in Phase 4 and exposed through the <code>/api/comparison</code> endpoint.
          </p>
        </div>
      </Card>
    </div>
  );
}
