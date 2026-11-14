import React from 'react';
import { AlertTriangle, TrendingUp, HelpCircle, ShieldAlert } from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function AnomalyView() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <span>Statistical Anomaly Analysis</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Detecting statistically unusual spikes in active-fire observations against historical baselines.
          </p>
        </div>

        <StatusBadge type="warning" label="Statistical Observation &bull; Not Fire Prediction" />
      </div>

      <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-start space-x-3 text-xs text-amber-200">
        <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-white block mb-0.5">Scientific Principle (Prompt Rule #17 &amp; Docs Section 12):</strong>
          Anomaly detection flags unusual statistical deviations in satellite-observed fire counts relative to a historical baseline. It is strictly an observational quality &amp; surge metric, <em>not</em> an algorithmic forecast of future fire outbreaks.
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Detection Methodology" subtitle="Parametric & non-parametric tests">
          <div className="space-y-3 text-xs text-space-300">
            <div className="p-2.5 rounded bg-space-900 border border-space-800 font-mono text-[11px]">
              Z-score: Z = (X - &mu;) / &sigma;
            </div>
            <p className="text-space-400 text-[11px] leading-relaxed">
              Flags observation days where the count X deviates by more than 2 or 3 standard deviations (&sigma;) from the rolling historical seasonal mean (&mu;).
            </p>
          </div>
        </Card>

        <Card title="Seasonal Baseline" subtitle="Controlled historical window">
          <div className="space-y-2 text-xs text-space-400 leading-relaxed">
            <p>
              Baselines account for normal fire season cycles, cloud obscuration variations, and regional agricultural burning patterns.
            </p>
            <p className="text-space-300 font-medium">
              Target Baseline: 30-day rolling window or multi-year seasonal window.
            </p>
          </div>
        </Card>

        <Card title="Output Schema" subtitle="Target /api/analytics/anomalies">
          <ul className="text-xs text-space-300 space-y-1.5 font-mono text-[11px]">
            <li className="text-space-400">&bull; anomaly_date (ISO)</li>
            <li className="text-space-400">&bull; region / bounding_box</li>
            <li className="text-space-400">&bull; observed_count (int)</li>
            <li className="text-space-400">&bull; historical_mean (&mu;)</li>
            <li className="text-space-400">&bull; z_score (float)</li>
            <li className="text-space-400">&bull; status &amp; explanation</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
