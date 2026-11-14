import React from 'react';
import { CheckCircle2, AlertCircle, FileText, Database, ShieldCheck } from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';

export default function QualityView({ backendStatus }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Data Quality &amp; Provenance</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Data validation logs, coordinate sanity checks, missing value tracking, and source fidelity.
          </p>
        </div>

        <StatusBadge type="info" label="Target Endpoint: /api/quality" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card title="Raw Ingestion" subtitle="Data storage">
          <div className="text-xs space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-space-400">data/raw/modis/</span>
              <StatusBadge type="healthy" label="Ready" size="xs" />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-space-400">data/raw/viirs/</span>
              <StatusBadge type="healthy" label="Ready" size="xs" />
            </div>
            <p className="text-[11px] text-space-500 pt-1">
              Preserves unedited original NASA FIRMS CSV source files.
            </p>
          </div>
        </Card>

        <Card title="Validation Rules" subtitle="Integrity criteria">
          <ul className="text-xs text-space-300 space-y-1.5 font-mono text-[11px]">
            <li className="text-space-400">&bull; Lat &isin; [-90.0, +90.0]</li>
            <li className="text-space-400">&bull; Lon &isin; [-180.0, +180.0]</li>
            <li className="text-space-400">&bull; ISO-8601 timestamps</li>
            <li className="text-space-400">&bull; Null value tracking</li>
            <li className="text-space-400">&bull; Deduplication checks</li>
          </ul>
        </Card>

        <Card title="Preservation Rule" subtitle="Zero silent deletion">
          <p className="text-xs text-space-300 leading-relaxed">
            Per development rule #9, invalid or corrupted records are never silently dropped; they are cataloged with validation flags in <code>data/reports/</code>.
          </p>
        </Card>

        <Card title="Processed Lake" subtitle="Harmonized output">
          <div className="text-xs space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-space-400">data/processed/</span>
              <StatusBadge type="healthy" label="Configured" size="xs" />
            </div>
            <p className="text-[11px] text-space-500 pt-1">
              Stores normalized observations, matched pairs, and unassociated detections.
            </p>
          </div>
        </Card>
      </div>

      <Card title="Data Quality Pipeline (Phase 2 Preview)">
        <div className="p-4 rounded-xl bg-space-900 border border-space-800 text-xs text-space-300 space-y-3 leading-relaxed">
          <p>
            When NASA FIRMS CSV files are ingested during Phase 2, this view will show interactive metrics for:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-[11px]">
            <div className="p-3 rounded-lg bg-space-950 border border-space-800">
              <div className="text-space-400">total_records</div>
              <div className="text-lg font-bold text-white mt-1">Pending Ingest</div>
            </div>
            <div className="p-3 rounded-lg bg-space-950 border border-space-800">
              <div className="text-space-400">valid_records</div>
              <div className="text-lg font-bold text-emerald-400 mt-1">Phase 2</div>
            </div>
            <div className="p-3 rounded-lg bg-space-950 border border-space-800">
              <div className="text-space-400">invalid_records</div>
              <div className="text-lg font-bold text-rose-400 mt-1">Logged to JSON</div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
