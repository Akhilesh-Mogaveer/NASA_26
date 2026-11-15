import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  GitBranch, 
  GitMerge, 
  Flame, 
  MapPin, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Sliders, 
  Search, 
  ArrowRight,
  TrendingUp,
  Activity,
  Compass,
  Cpu,
  Play,
  Share2,
  Database,
  ShieldAlert,
  Info,
  Maximize2,
  Calendar,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip as MapTooltip } from 'react-leaflet';
import Card from '../components/common/Card';
import StatusBadge from '../components/common/StatusBadge';
import SubTabs from '../components/common/SubTabs';
import DataTable from '../components/common/DataTable';
import GlassTooltip from '../components/common/GlassTooltip';
import ClayButton from '../components/common/ClayButton';
import ChangeMapView from '../components/common/ChangeMapView';
import { SENSOR_COLORS, EVENT_COLORS, CHART_THEME, MAP_THEME } from '../theme/tokens';
import { 
  getEvolutionSummary,
  getEvolutionTracks,
  getEvolutionTrackDetail,
  getEvolutionTrackTimeline,
  getEvolutionTrackLineage,
  getEvolutionRelationships,
  getEvolutionMap,
  runEvolution,
  getEvolutionStatus,
  getEvolutionExperiments
} from '../api/client';


export default function EventEvolutionView() {
  const [loading, setLoading] = useState(true);
  const [subTab, setSubTab] = useState('overview'); // 'overview' | 'map' | 'timeline' | 'lineage' | 'runner'
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  // Tracks State
  const [tracksList, setTracksList] = useState([]);
  const [tracksTotal, setTracksTotal] = useState(0);
  const [trackSensorFilter, setTrackSensorFilter] = useState('ALL');
  const [trackTypeFilter, setTrackTypeFilter] = useState('ALL');
  const [trackMinClusters, setTrackMinClusters] = useState(1);
  const [trackPage, setTrackPage] = useState(1);
  const [selectedTrackId, setSelectedTrackId] = useState(null);
  const [selectedTrackDetail, setSelectedTrackDetail] = useState(null);

  // Timeline & Lineage State
  const [timelineData, setTimelineData] = useState([]);
  const [lineageData, setLineageData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Relationships State
  const [relationshipsList, setRelationshipsList] = useState([]);
  const [relationshipsTotal, setRelationshipsTotal] = useState(0);
  const [relSensorFilter, setRelSensorFilter] = useState('ALL');
  const [relClassFilter, setRelClassFilter] = useState('ALL');
  const [relPage, setRelPage] = useState(1);

  // Map State
  const [mapCenter, setMapCenter] = useState([55.5, -104.5]);
  const [mapZoom, setMapZoom] = useState(8);
  const [mapNodes, setMapNodes] = useState([]);
  const [mapEdges, setMapEdges] = useState([]);
  const [mapLoading, setMapLoading] = useState(false);
  const [showModisNodes, setShowModisNodes] = useState(true);
  const [showViirsNodes, setShowViirsNodes] = useState(true);
  const [mapFilterTrackId, setMapFilterTrackId] = useState('');

  // Runner & Experiments State
  const [experiments, setExperiments] = useState([]);
  const [jobStatus, setJobStatus] = useState(null);
  const [runConfig, setRunConfig] = useState({
    max_temporal_gap_hours: 24.0,
    max_spatial_distance_km: 5.0,
    use_extent_aware: true,
    max_centroid_cap_km: 7.5,
    candidate_selection_strategy: 'successive_period',
    ambiguity_delta_threshold: 0.15,
    experiment_name: 'regional_boreal_evolution',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load Initial Summary
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const sumRes = await getEvolutionSummary();
      if (sumRes.success) {
        setSummary(sumRes.data);
      } else {
        setError(sumRes.error);
      }
    } catch (err) {
      setError(err.message || 'Failed to initialize event evolution view');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load Tracks List
  const fetchTracks = useCallback(async () => {
    try {
      const params = {
        sensor: trackSensorFilter,
        track_type: trackTypeFilter,
        min_clusters: trackMinClusters,
        limit: 15,
        offset: (trackPage - 1) * 15,
      };
      const res = await getEvolutionTracks(params);
      if (res.success) {
        setTracksList(res.data.items);
        setTracksTotal(res.data.total_count);
        if (!selectedTrackId && res.data.items.length > 0) {
          setSelectedTrackId(res.data.items[0].track_id);
        }
      }
    } catch (err) {
      console.error('Error fetching tracks:', err);
    }
  }, [trackSensorFilter, trackTypeFilter, trackMinClusters, trackPage, selectedTrackId]);

  useEffect(() => {
    if (subTab === 'timeline' || subTab === 'lineage' || subTab === 'overview') {
      fetchTracks();
    }
  }, [fetchTracks, subTab]);

  // Load Selected Track Detail & Timeline & Lineage
  useEffect(() => {
    if (!selectedTrackId) return;

    let isMounted = true;
    async function loadTrackDetails() {
      setDetailLoading(true);
      try {
        const [detRes, timeRes, linRes] = await Promise.all([
          getEvolutionTrackDetail(selectedTrackId),
          getEvolutionTrackTimeline(selectedTrackId),
          getEvolutionTrackLineage(selectedTrackId)
        ]);

        if (isMounted) {
          if (detRes.success) setSelectedTrackDetail(detRes.data);
          if (timeRes.success) setTimelineData(timeRes.data.timeline || []);
          if (linRes.success) setLineageData(linRes.data);
        }
      } catch (err) {
        console.error('Error loading track details:', err);
      } finally {
        if (isMounted) setDetailLoading(false);
      }
    }

    loadTrackDetails();
    return () => { isMounted = false; };
  }, [selectedTrackId]);

  // Load Map Data
  const fetchMapData = useCallback(async () => {
    setMapLoading(true);
    try {
      const params = {
        limit: 300,
        track_id: mapFilterTrackId.trim() || undefined,
      };
      const res = await getEvolutionMap(params);
      if (res.success) {
        setMapNodes(res.data.nodes || []);
        setMapEdges(res.data.edges || []);
        if (res.data.nodes.length > 0 && mapFilterTrackId.trim()) {
          setMapCenter([res.data.nodes[0].latitude, res.data.nodes[0].longitude]);
          setMapZoom(10);
        }
      }
    } catch (err) {
      console.error('Error loading evolution map:', err);
    } finally {
      setMapLoading(false);
    }
  }, [mapFilterTrackId]);

  useEffect(() => {
    if (subTab === 'map') {
      fetchMapData();
    }
  }, [fetchMapData, subTab]);

  // Load Experiments
  const fetchExperiments = useCallback(async () => {
    try {
      const res = await getEvolutionExperiments();
      if (res.success) {
        setExperiments(res.data);
      }
    } catch (err) {
      console.error('Error fetching experiments:', err);
    }
  }, []);

  useEffect(() => {
    if (subTab === 'runner') {
      fetchExperiments();
    }
  }, [fetchExperiments, subTab]);

  // Handle Trigger Evolution Job
  const handleTriggerRun = async () => {
    setIsSubmitting(true);
    try {
      const res = await runEvolution(runConfig);
      if (res.success) {
        setJobStatus(res.data);
        // Start polling
        const interval = setInterval(async () => {
          const stRes = await getEvolutionStatus();
          if (stRes.success) {
            setJobStatus(stRes.data);
            if (stRes.data.status === 'completed' || stRes.data.status === 'failed') {
              clearInterval(interval);
              setIsSubmitting(false);
              loadInitialData();
              fetchExperiments();
            }
          }
        }, 1500);
      } else {
        alert(`Failed to start job: ${res.error}`);
        setIsSubmitting(false);
      }
    } catch (err) {
      alert(`Error starting job: ${err.message}`);
      setIsSubmitting(false);
    }
  };

  // Helper formatting
  const formatMW = (val) => (val !== undefined && val !== null ? `${Number(val).toLocaleString(undefined, { maximumFractionDigits: 1 })} MW` : '0 MW');
  const formatKm = (val) => (val !== undefined && val !== null ? `${Number(val).toFixed(2)} km` : '0 km');
  const formatHours = (val) => (val !== undefined && val !== null ? `${Number(val).toFixed(1)} h` : '0 h');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-space-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <GitBranch className="w-7 h-7 text-emerald-400" />
              Temporal Event Evolution & Lifecycle Tracking
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Phase 6 Scientific Engine
            </span>
          </div>
          <p className="text-space-400 text-sm mt-1">
            Tracks candidate temporal continuity, lineage, and branching graph structures across successive satellite overpasses.
          </p>
        </div>

        {/* SubTab Navigation */}
        <SubTabs
          tabs={[
            { id: 'overview', label: 'Overview' },
            { id: 'map', label: 'Interactive Map', icon: Compass },
            { id: 'timeline', label: 'Event Timeline', icon: Clock },
            { id: 'lineage', label: 'Lineage & Splits', icon: GitMerge },
            { id: 'runner', label: 'Runner & Benchmarks', icon: Sliders },
          ]}
          activeTab={subTab}
          onChange={setSubTab}
        />
      </div>

      {/* Scientific Principle Banner */}
      <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-4 text-xs text-space-300 flex items-start gap-3">
        <Info className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-emerald-300">Scientific Integrity Notice: Candidate Continuity vs. Physical Fires</p>
          <p>
            Temporal event tracks are empirical graph structures linking discrete satellite hotspot clusters across successive overpass intervals.
            They do <strong>not</strong> prove confirmed physical wildfire perimeters, ignition, spread direction, or extinguishment.
            Absence of detections does not confirm a fire has ended. Summed snapshot FRP represents instantaneous reported power in <strong>Megawatts (MW)</strong>, not Fire Radiative Energy (MJ).
          </p>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SUBTAB 1: OVERVIEW METRICS & DISTRIBUTIONS */}
      {/* ========================================================================= */}
      {subTab === 'overview' && summary && (
        <div className="space-y-6">
          {/* Key Metric KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-space-900 border-space-800">
              <div className="flex items-center justify-between">
                <span className="text-space-400 text-xs uppercase font-medium">MODIS Event Tracks</span>
                <span className="px-2 py-0.5 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">MODIS</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">{summary.modis.total_event_tracks}</span>
                <span className="text-xs text-space-400">({summary.modis.multi_cluster_tracks_count} multi-cluster)</span>
              </div>
              <div className="mt-3 text-xs text-space-400 space-y-1 border-t border-space-800/60 pt-2">
                <div className="flex justify-between">
                  <span>Median Track Duration:</span>
                  <span className="text-white font-medium">{formatHours(summary.modis.median_observed_track_duration_hours)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Clusters Represented:</span>
                  <span className="text-white font-medium">{summary.modis.clusters_represented}</span>
                </div>
                <div className="flex justify-between">
                  <span>Isolated Single Clusters:</span>
                  <span className="text-amber-400 font-medium">{summary.modis.isolated_clusters_count} ({summary.modis.isolated_cluster_rate_pct}%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Cross-Sensor Evidence:</span>
                  <span className="text-emerald-400 font-medium">{summary.modis.clusters_with_cross_sensor_evidence_count || 0} ({summary.modis.cross_sensor_evidence_rate_pct || 0}%)</span>
                </div>
              </div>
            </Card>

            <Card className="bg-space-900 border-space-800">
              <div className="flex items-center justify-between">
                <span className="text-space-400 text-xs uppercase font-medium">VIIRS Event Tracks</span>
                <span className="px-2 py-0.5 text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded">VIIRS</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">{summary.viirs.total_event_tracks}</span>
                <span className="text-xs text-space-400">({summary.viirs.multi_cluster_tracks_count} multi-cluster)</span>
              </div>
              <div className="mt-3 text-xs text-space-400 space-y-1 border-t border-space-800/60 pt-2">
                <div className="flex justify-between">
                  <span>Median Track Duration:</span>
                  <span className="text-white font-medium">{formatHours(summary.viirs.median_observed_track_duration_hours)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Clusters Represented:</span>
                  <span className="text-white font-medium">{summary.viirs.clusters_represented}</span>
                </div>
                <div className="flex justify-between">
                  <span>Isolated Single Clusters:</span>
                  <span className="text-cyan-400 font-medium">{summary.viirs.isolated_clusters_count} ({summary.viirs.isolated_cluster_rate_pct}%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Cross-Sensor Evidence:</span>
                  <span className="text-emerald-400 font-medium">{summary.viirs.clusters_with_cross_sensor_evidence_count || 0} ({summary.viirs.cross_sensor_evidence_rate_pct || 0}%)</span>
                </div>
              </div>
            </Card>

            <Card className="bg-space-900 border-space-800">
              <div className="flex items-center justify-between">
                <span className="text-space-400 text-xs uppercase font-medium">Temporal Continuity Edges</span>
                <GitBranch className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">{summary.benchmarks.total_relationships_generated}</span>
                <span className="text-xs text-emerald-400 font-medium">Directed Edges</span>
              </div>
              <div className="mt-3 text-xs text-space-400 space-y-1 border-t border-space-800/60 pt-2">
                <div className="flex justify-between">
                  <span>MODIS Continuity Edges:</span>
                  <span className="text-white font-medium">{summary.modis.total_temporal_relationships}</span>
                </div>
                <div className="flex justify-between">
                  <span>VIIRS Continuity Edges:</span>
                  <span className="text-white font-medium">{summary.viirs.total_temporal_relationships}</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Window Allowed:</span>
                  <span className="text-emerald-400 font-medium">{summary.parameters.max_temporal_gap_hours} hours</span>
                </div>
              </div>
            </Card>

            <Card className="bg-space-900 border-space-800">
              <div className="flex items-center justify-between">
                <span className="text-space-400 text-xs uppercase font-medium">Graph Lineage Topologies</span>
                <GitMerge className="w-4 h-4 text-purple-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">
                  {summary.modis.splits_count + summary.viirs.splits_count}
                </span>
                <span className="text-xs text-purple-400 font-medium">Splits / {summary.modis.merges_count + summary.viirs.merges_count} Merges</span>
              </div>
              <div className="mt-3 text-xs text-space-400 space-y-1 border-t border-space-800/60 pt-2">
                <div className="flex justify-between">
                  <span>MODIS Splits / Merges:</span>
                  <span className="text-white font-medium">{summary.modis.splits_count} / {summary.modis.merges_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>VIIRS Splits / Merges:</span>
                  <span className="text-white font-medium">{summary.viirs.splits_count} / {summary.viirs.merges_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cross-Sensor Evidence Links:</span>
                  <span className="text-purple-400 font-medium">{summary.combined_cross_sensor.modis_relationships_with_cross_evidence + summary.combined_cross_sensor.viirs_relationships_with_cross_evidence}</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Charts: Track Types & Lineage Classifications */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-space-900 border-space-800 p-5">
              <h3 className="text-sm font-semibold text-space-200 mb-4 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                Track Topology Classification Distribution
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    {
                      name: 'Complex Network',
                      MODIS: summary.modis.track_type_breakdown.complex_network || 0,
                      VIIRS: summary.viirs.track_type_breakdown.complex_network || 0,
                    },
                    {
                      name: 'Isolated Cluster',
                      MODIS: summary.modis.track_type_breakdown.isolated_cluster || 0,
                      VIIRS: summary.viirs.track_type_breakdown.isolated_cluster || 0,
                    },
                    {
                      name: 'Linear Track',
                      MODIS: summary.modis.track_type_breakdown.linear_track || 0,
                      VIIRS: summary.viirs.track_type_breakdown.linear_track || 0,
                    },
                    {
                      name: 'Branching Split',
                      MODIS: summary.modis.track_type_breakdown.branching_split || 0,
                      VIIRS: summary.viirs.track_type_breakdown.branching_split || 0,
                    },
                    {
                      name: 'Branching Merge',
                      MODIS: summary.modis.track_type_breakdown.branching_merge || 0,
                      VIIRS: summary.viirs.track_type_breakdown.branching_merge || 0,
                    },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid.stroke} />
                    <XAxis dataKey="name" stroke={CHART_THEME.axis.stroke} tick={{ fill: CHART_THEME.tick.fill, fontSize: 11 }} />
                    <YAxis stroke={CHART_THEME.axis.stroke} tick={{ fill: CHART_THEME.tick.fill, fontSize: 11 }} />
                    <Tooltip content={<GlassTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Bar dataKey="MODIS" fill={SENSOR_COLORS.modis} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="VIIRS" fill={SENSOR_COLORS.viirs} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-space-400 mt-2">
                Topology classifications are graph-level structural properties of connected overpass detections.
              </p>
            </Card>

            <Card className="bg-space-900 border-space-800 p-5">
              <h3 className="text-sm font-semibold text-space-200 mb-4 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-purple-400" />
                Continuity Relationship Evidence Classifications
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    {
                      name: 'Complex Lineage',
                      MODIS: summary.modis.classification_breakdown.complex_lineage || 0,
                      VIIRS: summary.viirs.classification_breakdown.complex_lineage || 0,
                    },
                    {
                      name: 'Possible Split',
                      MODIS: summary.modis.classification_breakdown.possible_split || 0,
                      VIIRS: summary.viirs.classification_breakdown.possible_split || 0,
                    },
                    {
                      name: 'Possible Merge',
                      MODIS: summary.modis.classification_breakdown.possible_merge || 0,
                      VIIRS: summary.viirs.classification_breakdown.possible_merge || 0,
                    },
                    {
                      name: 'Continuation',
                      MODIS: summary.modis.classification_breakdown.continuation_candidate || 0,
                      VIIRS: summary.viirs.classification_breakdown.continuation_candidate || 0,
                    },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid.stroke} />
                    <XAxis dataKey="name" stroke={CHART_THEME.axis.stroke} tick={{ fill: CHART_THEME.tick.fill, fontSize: 11 }} />
                    <YAxis stroke={CHART_THEME.axis.stroke} tick={{ fill: CHART_THEME.tick.fill, fontSize: 11 }} />
                    <Tooltip content={<GlassTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Bar dataKey="MODIS" fill={SENSOR_COLORS.modis} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="VIIRS" fill={SENSOR_COLORS.viirs} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-space-400 mt-2">
                Evaluates in-degree and out-degree connectivity between successive observation clusters.
              </p>
            </Card>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUBTAB 2: INTERACTIVE LEAFLET MAP */}
      {/* ========================================================================= */}
      {subTab === 'map' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="bg-space-900 p-4 rounded-lg border border-space-800 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-2 cursor-pointer text-space-300">
                <input
                  type="checkbox"
                  checked={showModisNodes}
                  onChange={(e) => setShowModisNodes(e.target.checked)}
                  className="rounded bg-space-800 border-space-700 text-amber-500 focus:ring-0"
                />
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                MODIS Clusters
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-space-300">
                <input
                  type="checkbox"
                  checked={showViirsNodes}
                  onChange={(e) => setShowViirsNodes(e.target.checked)}
                  className="rounded bg-space-800 border-space-700 text-cyan-500 focus:ring-0"
                />
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-500"></span>
                VIIRS Clusters
              </label>

              <div className="flex items-center gap-2 ml-4">
                <span className="text-space-400">Filter Single Track:</span>
                <input
                  type="text"
                  placeholder="e.g. TRACK-VIIRS-00001"
                  value={mapFilterTrackId}
                  onChange={(e) => setMapFilterTrackId(e.target.value)}
                  className="bg-space-800 border border-space-700 text-white px-2 py-1 rounded text-xs w-48"
                />
                {mapFilterTrackId && (
                  <button
                    onClick={() => setMapFilterTrackId('')}
                    className="text-space-400 hover:text-white"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchMapData}
                disabled={mapLoading}
                className="px-3 py-1 bg-space-800 hover:bg-space-700 text-space-200 rounded border border-space-700 flex items-center gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${mapLoading ? 'animate-spin' : ''}`} />
                Reload Viewport
              </button>
            </div>
          </div>

          {/* Map Container */}
          <Card className="bg-space-900 border-space-800 p-0 overflow-hidden relative" style={{ height: '620px' }}>
            <MapContainer
              center={mapCenter}
              zoom={mapZoom}
              style={{ height: '100%', width: '100%', background: MAP_THEME.backgroundColor }}
            >
              <ChangeMapView center={mapCenter} zoom={mapZoom} />
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution="&copy; OpenStreetMap contributors &copy; CARTO"
                maxZoom={18}
              />

              {/* Directed Temporal Vectors (Edges) */}
              {mapEdges.map((edge) => {
                const isModis = edge.sensor === 'MODIS';
                const strokeColor = edge.classification === 'possible_split' 
                  ? EVENT_COLORS.split
                  : edge.classification === 'possible_merge'
                  ? EVENT_COLORS.merge
                  : isModis ? SENSOR_COLORS.modis : SENSOR_COLORS.viirs;

                return (
                  <Polyline
                    key={edge.relationship_id}
                    positions={edge.coordinates}
                    pathOptions={{
                      color: strokeColor,
                      weight: 2,
                      opacity: 0.75,
                      dashArray: edge.is_ambiguous ? '4, 4' : undefined,
                    }}
                  >
                    <MapTooltip sticky>
                      <div className="p-1 text-xs">
                        <p className="font-bold text-white">{edge.relationship_id}</p>
                        <p className="text-space-400">Track: {edge.track_id}</p>
                        <p className="text-space-300">Gap: {formatHours(edge.temporal_gap_hours)} | Dist: {formatKm(edge.centroid_distance_km)}</p>
                        <p className="text-emerald-400 font-semibold">{edge.classification}</p>
                        <p className="text-space-400">Score: {edge.heuristic_score}</p>
                      </div>
                    </MapTooltip>
                  </Polyline>
                );
              })}

              {/* Cluster Centroid Nodes */}
              {mapNodes.map((node) => {
                const isModis = node.sensor === 'MODIS';
                if (isModis && !showModisNodes) return null;
                if (!isModis && !showViirsNodes) return null;

                const fillColor = isModis ? SENSOR_COLORS.modis : SENSOR_COLORS.viirs;
                const radius = Math.min(10, Math.max(4, Math.log2(node.observation_count + 1) * 2));

                return (
                  <CircleMarker
                    key={node.cluster_id}
                    center={[node.latitude, node.longitude]}
                    radius={radius}
                    pathOptions={{
                      fillColor: fillColor,
                      fillOpacity: 0.85,
                      color: 'white',
                      weight: 1,
                    }}
                  >
                    <MapTooltip sticky>
                      <div className="p-1 text-xs space-y-0.5">
                        <p className="font-bold text-white">{node.cluster_id}</p>
                        <p className="text-space-400">Track: {node.track_id}</p>
                        <p className="text-space-300">Time: {node.timestamp_utc}</p>
                        <p className="text-space-300">Obs: {node.observation_count} | FRP: {formatMW(node.sum_frp_mw)}</p>
                        <p className="text-emerald-400">Type: {node.track_type}</p>
                      </div>
                    </MapTooltip>
                  </CircleMarker>
                );
              })}
            </MapContainer>

            {/* Map Legend Overlay */}
            <div className="absolute bottom-4 left-4 z-[1000] bg-space-900/90 backdrop-blur-sm p-3 rounded-md border border-space-800 text-xs text-space-300 space-y-1.5 shadow-lg">
              <p className="font-semibold text-white mb-1">Temporal Evolution Legend</p>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
                <span>MODIS Cluster Centroid</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-cyan-500 inline-block"></span>
                <span>VIIRS Cluster Centroid</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-emerald-500 inline-block"></span>
                <span>Continuation Vector</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-purple-500 inline-block"></span>
                <span>Possible Split Vector</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-pink-500 inline-block"></span>
                <span>Possible Merge Vector</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUBTAB 3: EVENT TIMELINE & TRACKS EXPLORER */}
      {/* ========================================================================= */}
      {subTab === 'timeline' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tracks List Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <Card className="bg-space-900 border-space-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Flame className="w-4 h-4 text-emerald-400" />
                  Candidate Event Tracks ({tracksTotal})
                </h3>
              </div>

              {/* Filters */}
              <div className="space-y-2 mb-3 text-xs">
                <div className="flex gap-2">
                  <select
                    value={trackSensorFilter}
                    onChange={(e) => { setTrackSensorFilter(e.target.value); setTrackPage(1); }}
                    className="bg-space-800 border border-space-700 text-white rounded px-2 py-1 text-xs w-1/2"
                  >
                    <option value="ALL">All Sensors</option>
                    <option value="MODIS">MODIS</option>
                    <option value="VIIRS">VIIRS</option>
                  </select>
                  <select
                    value={trackTypeFilter}
                    onChange={(e) => { setTrackTypeFilter(e.target.value); setTrackPage(1); }}
                    className="bg-space-800 border border-space-700 text-white rounded px-2 py-1 text-xs w-1/2"
                  >
                    <option value="ALL">All Topologies</option>
                    <option value="complex_network">Complex Network</option>
                    <option value="linear_track">Linear Track</option>
                    <option value="branching_split">Branching Split</option>
                    <option value="branching_merge">Branching Merge</option>
                    <option value="isolated_cluster">Isolated Cluster</option>
                  </select>
                </div>
              </div>

              {/* Tracks Scroll List */}
              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {tracksList.map((track) => {
                  const isSelected = track.track_id === selectedTrackId;
                  const isModis = track.sensor === 'MODIS';
                  return (
                    <div
                      key={track.track_id}
                      onClick={() => setSelectedTrackId(track.track_id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-emerald-950/30 border-emerald-500/50'
                          : 'bg-space-850 border-space-800 hover:bg-space-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-white flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${isModis ? 'bg-amber-400' : 'bg-cyan-400'}`} />
                          {track.track_id}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-space-800 text-space-300 border border-space-700">
                          {track.track_type}
                        </span>
                      </div>
                      <div className="mt-2 text-[11px] text-space-400 grid grid-cols-2 gap-1">
                        <div>Clusters: <span className="text-white font-medium">{track.cluster_count}</span></div>
                        <div>Obs: <span className="text-white font-medium">{track.observation_count}</span></div>
                        <div>Span: <span className="text-white font-medium">{formatHours(track.total_duration_hours)}</span></div>
                        <div>FRP: <span className="text-amber-400 font-medium">{formatMW(track.sum_snapshot_frp_mw)}</span></div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between pt-3 border-t border-space-800 text-xs text-space-400">
                <span>Page {trackPage} of {Math.ceil(tracksTotal / 15) || 1}</span>
                <div className="flex gap-1">
                  <button
                    disabled={trackPage <= 1}
                    onClick={() => setTrackPage((p) => p - 1)}
                    className="px-2 py-1 bg-space-800 rounded disabled:opacity-40"
                  >
                    Prev
                  </button>
                  <button
                    disabled={trackPage >= Math.ceil(tracksTotal / 15)}
                    onClick={() => setTrackPage((p) => p + 1)}
                    className="px-2 py-1 bg-space-800 rounded disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            </Card>
          </div>

          {/* Timeline Detail View */}
          <div className="lg:col-span-2 space-y-4">
            {selectedTrackDetail && (
              <Card className="bg-space-900 border-space-800 p-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-space-800 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Clock className="w-5 h-5 text-emerald-400" />
                      Track Timeline: {selectedTrackDetail.track_id}
                    </h3>
                    <p className="text-xs text-space-400 mt-1">
                      {selectedTrackDetail.first_observed_utc} &rarr; {selectedTrackDetail.last_observed_utc} ({formatHours(selectedTrackDetail.total_duration_hours)})
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 text-xs rounded bg-space-800 text-space-200 border border-space-700">
                      {selectedTrackDetail.track_type}
                    </span>
                    <button
                      onClick={() => {
                        setMapFilterTrackId(selectedTrackDetail.track_id);
                        setSubTab('map');
                      }}
                      className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs flex items-center gap-1 font-medium"
                    >
                      <MapPin className="w-3.5 h-3.5" />
                      View on Map
                    </button>
                  </div>
                </div>

                {/* Timeline Step Sequence */}
                <div className="mt-6 space-y-6 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-space-800">
                  {timelineData.map((step) => (
                    <div key={step.step_index} className="relative flex items-start gap-4 ml-1">
                      {/* Timeline node marker */}
                      <div className="w-6 h-6 rounded-full bg-emerald-600 border-2 border-space-900 flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0 z-10">
                        {step.step_index}
                      </div>

                      {/* Content Box */}
                      <div className="flex-1 bg-space-850 p-4 rounded-lg border border-space-800 text-xs">
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-space-800/60 pb-2">
                          <span className="font-semibold text-white text-sm">{step.cluster_id}</span>
                          <span className="text-space-400">{step.timestamp_utc} ({step.primary_satellite})</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3 text-space-300">
                          <div>
                            <span className="text-space-500 block text-[10px]">Observations</span>
                            <span className="font-medium text-white">{step.observation_count} points</span>
                          </div>
                          <div>
                            <span className="text-space-500 block text-[10px]">Snapshot FRP</span>
                            <span className="font-medium text-amber-400">{formatMW(step.sum_frp_mw)}</span>
                          </div>
                          <div>
                            <span className="text-space-500 block text-[10px]">Centroid</span>
                            <span className="font-medium text-space-300">{step.centroid_latitude.toFixed(3)}, {step.centroid_longitude.toFixed(3)}</span>
                          </div>
                          <div>
                            <span className="text-space-500 block text-[10px]">Degree In/Out</span>
                            <span className="font-medium text-space-300">{step.in_degree} in / {step.out_degree} out</span>
                          </div>
                        </div>

                        {/* Transition from previous */}
                        {step.temporal_gap_to_prev_hours !== null && (
                          <div className="mt-3 bg-space-900/60 p-2 rounded border border-space-800/80 flex flex-wrap items-center justify-between text-[11px] text-space-400">
                            <span>Gap from prev step: <strong className="text-white">{formatHours(step.temporal_gap_to_prev_hours)}</strong></span>
                            <span>Centroid shift: <strong className="text-white">{formatKm(step.centroid_dist_to_prev_km)}</strong></span>
                            <span>&Delta; FRP: <strong className={step.delta_frp_from_prev_mw >= 0 ? 'text-amber-400' : 'text-blue-400'}>{step.delta_frp_from_prev_mw >= 0 ? `+${step.delta_frp_from_prev_mw}` : step.delta_frp_from_prev_mw} MW</strong></span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUBTAB 4: TRACK LINEAGE & SPLIT/MERGE EXPLORER */}
      {/* ========================================================================= */}
      {subTab === 'lineage' && (
        <div className="space-y-4">
          <Card className="bg-space-900 border-space-800 p-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-space-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <GitMerge className="w-5 h-5 text-purple-400" />
                  Lineage Graph Transitions: {selectedTrackId || 'None Selected'}
                </h3>
                <p className="text-xs text-space-400 mt-1">
                  Directed continuity transitions showing predecessor clusters, successors, branching splits, and converging merges.
                </p>
              </div>
            </div>

            {/* Lineage Table */}
            {lineageData && lineageData.edges.length > 0 ? (
              <div className="mt-4">
                <DataTable
                  headers={[
                    'Predecessor (Earlier)',
                    'Successor (Later)',
                    'Temporal Gap',
                    'Centroid Dist',
                    'Lineage Classification',
                    'Heuristic Score',
                    'Ambiguity',
                  ]}
                >
                  {lineageData.edges.map((edge, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.04] transition-colors">
                      <td className="py-2.5 px-4 font-mono font-semibold text-white">{edge.source_cluster_id}</td>
                      <td className="py-2.5 px-4 font-mono font-semibold text-white">{edge.target_cluster_id}</td>
                      <td className="py-2.5 px-4 font-mono text-space-300">{formatHours(edge.temporal_gap_hours)}</td>
                      <td className="py-2.5 px-4 font-mono text-space-300">{formatKm(edge.centroid_distance_km)}</td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                          edge.classification === 'possible_split'
                            ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            : edge.classification === 'possible_merge'
                            ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        }`}>
                          {edge.classification}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono font-medium text-white">{edge.heuristic_score.toFixed(4)}</td>
                      <td className="py-2.5 px-4">
                        {edge.is_ambiguous ? (
                          <span className="text-amber-400 font-semibold flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> Ambiguous
                          </span>
                        ) : (
                          <span className="text-space-500">Unambiguous</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </DataTable>
              </div>
            ) : (
              <div className="py-12 text-center text-space-500 text-sm">
                No lineage edges found for this track. This is an isolated cluster without multi-overpass continuity.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUBTAB 5: RUNNER & EXPERIMENTS */}
      {/* ========================================================================= */}
      {subTab === 'runner' && (
        <div className="space-y-6">
          <Card className="bg-space-900 border-space-800 p-5">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-400" />
              Configure & Trigger Temporal Evolution Tracking
            </h3>
            <p className="text-xs text-space-400 mb-4">
              Executes same-sensor spatial-temporal continuity candidate generation and track construction using DuckDB and spherical Haversine distance.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 text-xs">
              <div>
                <label className="text-space-400 block mb-1">Max Temporal Gap (hours)</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  max="72"
                  value={runConfig.max_temporal_gap_hours}
                  onChange={(e) => setRunConfig({ ...runConfig, max_temporal_gap_hours: parseFloat(e.target.value) || 24.0 })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                />
              </div>

              <div>
                <label className="text-space-400 block mb-1">Max Centroid Dist (km)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="30"
                  value={runConfig.max_spatial_distance_km}
                  onChange={(e) => setRunConfig({ ...runConfig, max_spatial_distance_km: parseFloat(e.target.value) || 5.0 })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                />
              </div>

              <div>
                <label className="text-space-400 block mb-1">Max Centroid Cap (km)</label>
                <input
                  type="number"
                  step="0.5"
                  min="1.0"
                  max="50.0"
                  value={runConfig.max_centroid_cap_km}
                  onChange={(e) => setRunConfig({ ...runConfig, max_centroid_cap_km: parseFloat(e.target.value) || 7.5 })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                />
              </div>

              <div>
                <label className="text-space-400 block mb-1">Candidate Strategy</label>
                <select
                  value={runConfig.candidate_selection_strategy}
                  onChange={(e) => setRunConfig({ ...runConfig, candidate_selection_strategy: e.target.value })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                >
                  <option value="successive_period">Successive Period (SOP)</option>
                  <option value="all_in_window">All in Window (Dense)</option>
                </select>
              </div>

              <div>
                <label className="text-space-400 block mb-1">Ambiguity Delta</label>
                <input
                  type="number"
                  step="0.05"
                  min="0.01"
                  max="0.5"
                  value={runConfig.ambiguity_delta_threshold}
                  onChange={(e) => setRunConfig({ ...runConfig, ambiguity_delta_threshold: parseFloat(e.target.value) || 0.15 })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                />
              </div>

              <div>
                <label className="text-space-400 block mb-1">Experiment Name</label>
                <input
                  type="text"
                  value={runConfig.experiment_name}
                  onChange={(e) => setRunConfig({ ...runConfig, experiment_name: e.target.value })}
                  className="w-full bg-space-950/80 border border-white/10 rounded-xl px-3 py-2 text-white text-xs font-mono shadow-inner focus:outline-none focus:border-accent-blue/50"
                />
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between pt-4 border-t border-space-800">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-space-300">
                <input
                  type="checkbox"
                  checked={runConfig.use_extent_aware}
                  onChange={(e) => setRunConfig({ ...runConfig, use_extent_aware: e.target.checked })}
                  className="rounded bg-space-800 border-space-700 text-emerald-500 focus:ring-0"
                />
                Use cluster spatial extent when evaluating candidate continuity
              </label>

              <ClayButton
                onClick={handleTriggerRun}
                disabled={isSubmitting}
                variant="primary"
                size="sm"
                className="flex items-center gap-2"
              >
                <Play className="w-3.5 h-3.5" />
                {isSubmitting ? 'Processing Evolution...' : 'Trigger Evolution Tracking'}
              </ClayButton>
            </div>

            {/* Live Status Bar */}
            {jobStatus && (
              <div className="mt-4 p-3 bg-space-850 rounded border border-space-750 text-xs flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white">Status: {jobStatus.status}</span>
                  <span className="text-space-400 ml-2">({jobStatus.message})</span>
                </div>
                <span className="text-emerald-400 font-bold">{jobStatus.progress_percent || 0}%</span>
              </div>
            )}
          </Card>

          {/* Historical Experiments Log */}
          <Card className="bg-space-900 border-space-800 p-5">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              Evolution Benchmark & Experiment History
            </h3>
            <DataTable
              headers={[
                'Experiment',
                'Executed At',
                'Window (h)',
                'Radius (km)',
                { label: 'MODIS Tracks', className: 'text-modis' },
                { label: 'VIIRS Tracks', className: 'text-viirs' },
                'Total Rel.',
                'Runtime',
              ]}
            >
              {experiments.map((exp, idx) => (
                <tr key={idx} className="hover:bg-white/[0.04] transition-colors">
                  <td className="py-2.5 px-4 font-mono font-semibold text-white">{exp.experiment_name}</td>
                  <td className="py-2.5 px-4 font-mono text-space-400">{exp.executed_at}</td>
                  <td className="py-2.5 px-4 font-mono text-space-300">{exp.max_temporal_gap_hours}</td>
                  <td className="py-2.5 px-4 font-mono text-space-300">{exp.max_spatial_distance_km}</td>
                  <td className="py-2.5 px-4 font-mono font-medium text-modis">{exp.modis_tracks_count}</td>
                  <td className="py-2.5 px-4 font-mono font-medium text-viirs">{exp.viirs_tracks_count}</td>
                  <td className="py-2.5 px-4 font-mono font-bold text-white">{exp.modis_relationships_count + exp.viirs_relationships_count}</td>
                  <td className="py-2.5 px-4 font-mono text-emerald-400 font-medium">{exp.runtime_seconds}s</td>
                </tr>
              ))}
            </DataTable>
          </Card>
        </div>
      )}
    </div>
  );
}
