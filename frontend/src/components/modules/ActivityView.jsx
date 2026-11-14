import React from 'react';
import { Radio, Calendar, TrendingUp } from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function ActivityView() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Radio className="w-5 h-5 text-modis" />
            <span>Fire Activity Analysis</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Temporal fire observation cycles: daily, weekly, and seasonal observation patterns.
          </p>
        </div>

        <StatusBadge type="info" label="Target Endpoint: /api/analytics/activity" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Temporal Aggregations" subtitle="Time-series resolution">
          <ul className="text-xs text-space-300 space-y-2">
            <li className="flex justify-between">
              <span className="text-space-400">Daily Counts:</span>
              <span className="font-mono text-space-200">24-hour observation frequency</span>
            </li>
            <li className="flex justify-between">
              <span className="text-space-400">Diurnal Cycle:</span>
              <span className="font-mono text-space-200">Day vs. Night detection share</span>
            </li>
            <li className="flex justify-between">
              <span className="text-space-400">Monthly Baseline:</span>
              <span className="font-mono text-space-200">Seasonal trend analysis</span>
            </li>
          </ul>
        </Card>

        <Card title="Sensor-Wise Breakdown" subtitle="Instrument detection share">
          <ul className="text-xs text-space-300 space-y-2">
            <li className="flex justify-between">
              <span className="text-space-400">MODIS Share:</span>
              <span className="font-mono text-modis">Tracked separately</span>
            </li>
            <li className="flex justify-between">
              <span className="text-space-400">VIIRS Share:</span>
              <span className="font-mono text-viirs">Tracked separately</span>
            </li>
            <li className="flex justify-between">
              <span className="text-space-400">Co-observed:</span>
              <span className="font-mono text-emerald-400">Matched associations</span>
            </li>
          </ul>
        </Card>

        <Card title="Fire Radiative Power (FRP)" subtitle="Radiant energy release">
          <div className="text-xs text-space-400 space-y-2">
            <p className="leading-relaxed">
              FRP distributions describe the radiant power output (in Megawatts) at the moment of satellite overpass.
            </p>
            <p className="text-[11px] text-space-500 italic">
              Scientific note: FRP is not burned area and does not represent total fire perimeter.
            </p>
          </div>
        </Card>
      </div>

      <Card title="Activity Analytics Canvas (Phase 5)">
        <div className="p-8 rounded-xl bg-space-900 border border-space-800 text-center space-y-3">
          <TrendingUp className="w-10 h-10 text-space-600 mx-auto" />
          <h4 className="text-base font-semibold text-white">Recharts Time-Series Engine Prepared</h4>
          <p className="text-xs text-space-400 max-w-md mx-auto leading-relaxed">
            Recharts is loaded into the project bundle. In Phase 5 and 6, this module will render daily bar charts, sensor breakdown stacked area plots, and regional fire frequency histograms.
          </p>
        </div>
      </Card>
    </div>
  );
}
