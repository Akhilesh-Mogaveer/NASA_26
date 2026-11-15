import React, { useState, useEffect, useCallback } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Database, 
  ShieldCheck, 
  Play, 
  RefreshCw, 
  FileSpreadsheet,
  AlertTriangle,
  FolderOpen
} from 'lucide-react';
import Card from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import ClayButton from '../common/ClayButton';
import { triggerDataIngest, getDataStatus, getDataQualityReport } from '../../api/client';

export default function QualityView({ backendStatus }) {
  const [dataStatus, setDataStatus] = useState(null);
  const [qualityReport, setQualityReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchStatusAndReport = useCallback(async () => {
    setLoading(true);
    const [statusRes, qualityRes] = await Promise.all([
      getDataStatus(),
      getDataQualityReport(),
    ]);

    if (statusRes.success) {
      setDataStatus(statusRes.data);
    }
    if (qualityRes.success) {
      setQualityReport(qualityRes.data);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStatusAndReport();
  }, [fetchStatusAndReport]);

  const handleRunIngest = async () => {
    setIngesting(true);
    setActionMessage(null);
    const res = await triggerDataIngest();
    if (res.success) {
      setActionMessage({
        type: 'success',
        text: `Ingestion complete! Processed ${res.data.total_records} records (${res.data.valid_records} valid, ${res.data.invalid_records} invalid) from ${res.data.number_of_source_files} files.`,
      });
      await fetchStatusAndReport();
    } else {
      setActionMessage({
        type: 'error',
        text: res.error || 'Ingestion failed.',
      });
    }
    setIngesting(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Data Ingestion &amp; Quality Control</span>
          </h2>
          <p className="text-xs text-space-400 mt-1">
            Automated validation engine for NASA FIRMS MODIS &amp; VIIRS active-fire observations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <ClayButton
            variant="secondary"
            size="sm"
            onClick={fetchStatusAndReport}
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </ClayButton>

          <ClayButton
            variant="primary"
            size="sm"
            onClick={handleRunIngest}
            disabled={ingesting || !backendStatus.online}
          >
            <Play className={`w-3.5 h-3.5 mr-1.5 ${ingesting ? 'animate-spin' : ''}`} />
            <span>{ingesting ? 'Processing...' : 'Run Ingestion Pipeline'}</span>
          </ClayButton>
        </div>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center space-x-2.5 transition-all shadow-clay-sm ${
            actionMessage.type === 'success'
              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/30 border-rose-500/40 text-rose-200'
          }`}
        >
          {actionMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          )}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Pipeline Status Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Raw Source Files" subtitle="data/raw/ directory">
          <div className="text-xs space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-space-400 flex items-center gap-1.5">
                <FileSpreadsheet className="w-3.5 h-3.5 text-modis" />
                MODIS CSVs:
              </span>
              <span className="font-mono text-space-100 font-semibold">
                {dataStatus?.modis_raw_files ?? 0} files
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-space-400 flex items-center gap-1.5">
                <FileSpreadsheet className="w-3.5 h-3.5 text-viirs" />
                VIIRS CSVs:
              </span>
              <span className="font-mono text-space-100 font-semibold">
                {dataStatus?.viirs_raw_files ?? 0} files
              </span>
            </div>
            <p className="text-[11px] text-space-400 pt-1">
              Place new FIRMS CSV files in <code className="bg-space-950 px-1 py-0.5 rounded border border-white/10 font-mono text-[10px]">data/raw/modis/</code> and <code className="bg-space-950 px-1 py-0.5 rounded border border-white/10 font-mono text-[10px]">data/raw/viirs/</code>.
            </p>
          </div>
        </Card>

        <Card title="Validation Engine" subtitle="Quality gate rules">
          <ul className="text-xs text-space-300 space-y-1 font-mono text-[11px]">
            <li className="text-space-400">&bull; Lat: [-90, +90] deg</li>
            <li className="text-space-400">&bull; Lon: [-180, +180] deg</li>
            <li className="text-space-400">&bull; Acq Date &amp; Time (UTC)</li>
            <li className="text-space-400">&bull; Duplicate observation flag</li>
            <li className="text-space-400">&bull; Missing values preserved</li>
          </ul>
        </Card>

        <Card title="Pipeline Status" subtitle="State tracking">
          <div className="space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-space-400">Current State:</span>
              <StatusBadge
                type={dataStatus?.status === 'completed' ? 'healthy' : dataStatus?.status === 'processing' ? 'warning' : 'info'}
                label={dataStatus?.status || 'idle'}
              />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-space-400">Processed Data:</span>
              <span className="font-mono text-space-200">
                {dataStatus?.has_processed_data ? 'Available' : 'Pending'}
              </span>
            </div>
            <div className="text-[11px] text-space-400 truncate" title={dataStatus?.message}>
              {dataStatus?.message || 'Ready for ingestion'}
            </div>
          </div>
        </Card>

        <Card title="Zero Silent Deletion" subtitle="Scientific provenance">
          <p className="text-xs text-space-300 leading-relaxed">
            Per development rule #9, invalid or corrupted records are cataloged in <code className="bg-space-950 px-1 py-0.5 rounded border border-white/10 font-mono text-[10px]">data/reports/data_quality_report.json</code> with detailed flags rather than silently removed.
          </p>
        </Card>
      </div>

      {/* Live Data Quality Report Dashboard */}
      {qualityReport ? (
        <Card
          title="Latest Data Quality Report"
          subtitle={`Generated at: ${new Date(qualityReport.report_generated_at).toLocaleString()}`}
        >
          <div className="space-y-6">
            {/* Top Metric Counters */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-space-900/80 border border-white/[0.08] shadow-clay-sm">
                <span className="text-xs text-space-400 block">Total Ingested</span>
                <span className="text-2xl font-bold font-mono text-white mt-1 block">
                  {qualityReport.total_records.toLocaleString()}
                </span>
                <span className="text-[10px] text-space-400">Across {qualityReport.number_of_source_files} files</span>
              </div>

              <div className="p-3.5 rounded-xl bg-space-900/80 border border-emerald-500/35 shadow-clay-sm">
                <span className="text-xs text-emerald-400 block">Valid Records</span>
                <span className="text-2xl font-bold font-mono text-emerald-300 mt-1 block">
                  {qualityReport.valid_records.toLocaleString()}
                </span>
                <span className="text-[10px] text-emerald-400 font-mono">
                  {qualityReport.total_records > 0
                    ? `${((qualityReport.valid_records / qualityReport.total_records) * 100).toFixed(1)}% pass rate`
                    : '100%'}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-space-900/80 border border-rose-500/35 shadow-clay-sm">
                <span className="text-xs text-rose-400 block">Invalid Records</span>
                <span className="text-2xl font-bold font-mono text-rose-300 mt-1 block">
                  {qualityReport.invalid_records.toLocaleString()}
                </span>
                <span className="text-[10px] text-rose-400 font-mono">Flagged &amp; documented</span>
              </div>

              <div className="p-3.5 rounded-xl bg-space-900/80 border border-amber-500/35 shadow-clay-sm">
                <span className="text-xs text-amber-400 block">Flagged Duplicates</span>
                <span className="text-2xl font-bold font-mono text-amber-300 mt-1 block">
                  {qualityReport.duplicate_counts?.total_flagged_duplicates?.toLocaleString() ?? 0}
                </span>
                <span className="text-[10px] text-amber-400 font-mono">Exact &amp; spatial-temporal</span>
              </div>
            </div>

            {/* Sensor Breakdown & Quality Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Sensor Breakdown */}
              <div className="p-4 rounded-xl bg-space-900/60 border border-white/[0.08] shadow-clay-sm space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-space-300 flex items-center justify-between">
                  <span>Sensor Ingestion Breakdown</span>
                  <span className="text-[11px] font-mono text-space-400">MODIS vs VIIRS</span>
                </h4>

                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-xl bg-space-950/60 border border-modis/30 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-modis-light flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-modis" />
                        MODIS (1km)
                      </div>
                      <div className="text-[11px] text-space-400 mt-0.5">
                        {qualityReport.sensor_statistics?.MODIS?.source_files ?? 0} source files
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="text-sm font-bold text-white">
                        {qualityReport.sensor_statistics?.MODIS?.total ?? 0}
                      </div>
                      <div className="text-[10px] text-emerald-400">
                        {qualityReport.sensor_statistics?.MODIS?.valid ?? 0} valid
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-space-950/60 border border-viirs/30 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-viirs-light flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-viirs" />
                        VIIRS (375m)
                      </div>
                      <div className="text-[11px] text-space-400 mt-0.5">
                        {qualityReport.sensor_statistics?.VIIRS?.source_files ?? 0} source files
                      </div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="text-sm font-bold text-white">
                        {qualityReport.sensor_statistics?.VIIRS?.total ?? 0}
                      </div>
                      <div className="text-[10px] text-emerald-400">
                        {qualityReport.sensor_statistics?.VIIRS?.valid ?? 0} valid
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Specific Anomaly Counters */}
              <div className="p-4 rounded-xl bg-space-900/60 border border-white/[0.08] shadow-clay-sm space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-space-300">
                  Integrity Audit Details
                </h4>

                <div className="space-y-2 text-xs font-mono">
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-space-400">Coordinate Errors (Out of bounds/NaN):</span>
                    <span className={qualityReport.invalid_coordinate_count > 0 ? "text-rose-400 font-bold" : "text-space-300"}>
                      {qualityReport.invalid_coordinate_count}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-space-400">Timestamp Parse Errors:</span>
                    <span className={qualityReport.timestamp_errors > 0 ? "text-rose-400 font-bold" : "text-space-300"}>
                      {qualityReport.timestamp_errors}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-space-400">Exact Duplicate Records:</span>
                    <span className="text-space-300">
                      {qualityReport.duplicate_counts?.exact_duplicates ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/[0.06]">
                    <span className="text-space-400">Spatial-Temporal Duplicate Clusters:</span>
                    <span className="text-space-300">
                      {qualityReport.duplicate_counts?.spatial_temporal_duplicates ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-space-400">Processing Exceptions:</span>
                    <span className={qualityReport.processing_errors?.length > 0 ? "text-rose-400 font-bold" : "text-space-300"}>
                      {qualityReport.processing_errors?.length ?? 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Processed Files Generated */}
            <div className="p-3.5 rounded-xl bg-space-950/60 border border-white/[0.08] text-xs">
              <span className="text-space-400 block mb-2 font-semibold">Processed Output Files Generated:</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 font-mono text-[11px]">
                <div className="p-2.5 rounded-xl bg-space-900/60 border border-white/[0.06] flex items-center justify-between">
                  <span className="text-modis-light">modis_normalized.csv</span>
                  <StatusBadge type="healthy" label="Saved" size="xs" />
                </div>
                <div className="p-2.5 rounded-xl bg-space-900/60 border border-white/[0.06] flex items-center justify-between">
                  <span className="text-viirs-light">viirs_normalized.csv</span>
                  <StatusBadge type="healthy" label="Saved" size="xs" />
                </div>
                <div className="p-2.5 rounded-xl bg-space-900/60 border border-white/[0.06] flex items-center justify-between">
                  <span className="text-white">unified_observations.csv</span>
                  <StatusBadge type="healthy" label="Saved" size="xs" />
                </div>
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <Card title="No Quality Report Generated Yet">
          <div className="p-8 text-center space-y-3">
            <FolderOpen className="w-10 h-10 text-space-600 mx-auto" />
            <h4 className="text-base font-semibold text-white">Dataset Ready For Ingestion</h4>
            <p className="text-xs text-space-400 max-w-md mx-auto leading-relaxed">
              Place your NASA FIRMS CSV files in <code>data/raw/modis/</code> and <code>data/raw/viirs/</code>, then click <strong>&quot;Run Ingestion Pipeline&quot;</strong> above or call <code>POST /api/data/ingest</code> to generate the first validation report.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
