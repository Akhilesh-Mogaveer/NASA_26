import axios from 'axios';

// Get API base URL from Vite environment variables.
// When empty or running with Vite proxy, relative '/api' calls route to the backend.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

/**
 * Health check service
 * Retrieves backend health status and data directory verification
 */
export async function getHealthStatus() {
  try {
    const response = await apiClient.get('/api/health');
    return {
      success: true,
      data: response.data,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Cannot connect to backend server',
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * Root endpoint check
 */
export async function getRootInfo() {
  try {
    const response = await apiClient.get('/');
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Trigger data ingestion and validation pipeline
 */
export async function triggerDataIngest() {
  try {
    const response = await apiClient.post('/api/data/ingest');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Ingestion failed',
    };
  }
}

/**
 * Get data processing pipeline status
 */
export async function getDataStatus() {
  try {
    const response = await apiClient.get('/api/data/status');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch status',
    };
  }
}

/**
 * Get latest data quality report
 */
export async function getDataQualityReport() {
  try {
    const response = await apiClient.get('/api/data/quality');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch quality report',
    };
  }
}

/**
 * Preview normalized fire observations
 */
export async function getNormalizedPreview(params = {}) {
  try {
    const response = await apiClient.get('/api/data/preview', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch preview',
    };
  }
}

// ==========================================
// Phase 3 Analytics API Client Functions
// ==========================================

/**
 * Get top-level analytics overview across 22.17M observations
 */
export async function getAnalyticsOverview() {
  try {
    const response = await apiClient.get('/api/analytics/overview');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch analytics overview',
    };
  }
}

/**
 * Get temporal activity analytics (monthly, diurnal hourly, day/night)
 */
export async function getTemporalAnalytics() {
  try {
    const response = await apiClient.get('/api/analytics/temporal');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch temporal analytics',
    };
  }
}

/**
 * Get Fire Radiative Power (MW) parametric statistics and histogram
 */
export async function getFRPAnalytics() {
  try {
    const response = await apiClient.get('/api/analytics/frp');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch FRP analytics',
    };
  }
}

/**
 * Get multi-sensor MODIS vs VIIRS comparison metrics
 */
export async function getSensorComparison() {
  try {
    const response = await apiClient.get('/api/analytics/sensor-comparison');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch sensor comparison',
    };
  }
}

/**
 * Get geographical clustering and latitudinal profile
 */
export async function getGeographicalAnalytics(topN = 20) {
  try {
    const response = await apiClient.get('/api/analytics/geographical', { params: { top_n: topN } });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch geographical analytics',
    };
  }
}

/**
 * Get 2-degree grid cell density for map display
 */
export async function getGridDensity(params = {}) {
  try {
    const response = await apiClient.get('/api/analytics/grid-density', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch grid density',
    };
  }
}

/**
 * =========================================================================
 * Phase 4 Spatial-Temporal Matching API Client Methods
 * =========================================================================
 */

/**
 * Get matching engine status
 */
export async function getMatchingStatus() {
  try {
    const response = await apiClient.get('/api/matching/status');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch matching status',
    };
  }
}

/**
 * Get matching summary and experiment results
 */
export async function getMatchingSummary() {
  try {
    const response = await apiClient.get('/api/matching/summary');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch matching summary',
    };
  }
}

/**
 * Get paginated candidate associations with optional filtering
 */
export async function getMatchingAssociations(params = {}) {
  try {
    const response = await apiClient.get('/api/matching/associations', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch associations',
    };
  }
}

/**
 * Get paginated unmatched observations
 */
export async function getMatchingUnmatched(params = {}) {
  try {
    const response = await apiClient.get('/api/matching/unmatched', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch unmatched observations',
    };
  }
}

/**
 * Get 12-parameter sensitivity evaluation matrix
 */
export async function getMatchingEvaluation() {
  try {
    const response = await apiClient.get('/api/matching/evaluation');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch matching evaluation',
    };
  }
}

/**
 * Run spatial-temporal matching on custom slice or parameters
 */
export async function runMatching(params = {}) {
  try {
    const response = await apiClient.post('/api/matching/run', params);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to execute matching workflow',
    };
  }
}

/**
 * Phase 4.4: Get bounded observation points for interactive map rendering
 */
export async function getMapObservations(params = {}) {
  try {
    const response = await apiClient.get('/api/matching/map-observations', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch map observations',
    };
  }
}

/**
 * Phase 4.4: Get candidate association vector lines for interactive map rendering
 */
export async function getMapLines(params = {}) {
  try {
    const response = await apiClient.get('/api/matching/map-lines', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch map association lines',
    };
  }
}

/**
 * Phase 4.4: Get complete observation detail and candidate edges by observation ID
 */
export async function getObservationDetail(obsId) {
  try {
    const response = await apiClient.get(`/api/matching/observation/${encodeURIComponent(obsId)}`);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch observation details',
    };
  }
}

/**
 * Phase 4.4: Get filtered matching summary for arbitrary viewport or date range
 */
export async function getFilteredMatchingSummary(params = {}) {
  try {
    const response = await apiClient.get('/api/matching/filtered-summary', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch filtered summary',
    };
  }
}

/**
 * Phase 4.5: Start a partitioned full-scale matching job in background
 */
export async function startFullScaleJob(params = {}) {
  try {
    const response = await apiClient.post('/api/matching/full-scale/start', params);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to start full-scale job',
    };
  }
}

/**
 * Phase 4.5: Get live full-scale job progress and partition status
 */
export async function getFullScaleStatus() {
  try {
    const response = await apiClient.get('/api/matching/full-scale/status');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch full-scale status',
    };
  }
}

/**
 * Phase 4.5: Get progressive real-data benchmarks across scales
 */
export async function getFullScaleBenchmarks() {
  try {
    const response = await apiClient.get('/api/matching/full-scale/benchmarks');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch full-scale benchmarks',
    };
  }
}

/**
 * =========================================================================
 * Phase 5.1 & 5.2 Event Intelligence API Client Methods
 * =========================================================================
 */

/**
 * Trigger independent spatial-temporal clustering job
 */
export async function runClustering(params = {}) {
  try {
    const response = await apiClient.post('/api/events/clustering/run', params);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to trigger clustering',
    };
  }
}

/**
 * Get clustering job execution status
 */
export async function getClusteringStatus() {
  try {
    const response = await apiClient.get('/api/events/clustering/status');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch clustering status',
    };
  }
}

/**
 * Get clustering summary metrics and benchmarks
 */
export async function getClusteringSummary() {
  try {
    const response = await apiClient.get('/api/events/clustering/summary');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch clustering summary',
    };
  }
}

/**
 * Get paginated list of clusters
 */
export async function getClusters(params = {}) {
  try {
    const response = await apiClient.get('/api/events/clustering/clusters', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch clusters',
    };
  }
}

/**
 * Get single cluster detail by ID
 */
export async function getClusterDetail(clusterId) {
  try {
    const response = await apiClient.get(`/api/events/clustering/${encodeURIComponent(clusterId)}`);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch cluster details',
    };
  }
}

/**
 * Get observations in a cluster
 */
export async function getClusterObservations(clusterId, params = {}) {
  try {
    const response = await apiClient.get(`/api/events/clustering/${encodeURIComponent(clusterId)}/observations`, { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch cluster observations',
    };
  }
}

/**
 * Trigger cross-sensor event association job
 */
export async function runEventAssociation(params = {}) {
  try {
    const response = await apiClient.post('/api/events/association/run', params);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to trigger event association',
    };
  }
}

/**
 * Get event association job status
 */
export async function getEventAssociationStatus() {
  try {
    const response = await apiClient.get('/api/events/association/status');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch association status',
    };
  }
}

/**
 * Get event association summary metrics and topology breakdown
 */
export async function getEventAssociationSummary() {
  try {
    const response = await apiClient.get('/api/events/association/summary');
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch association summary',
    };
  }
}

/**
 * Get paginated list of candidate cluster relationships
 */
export async function getEventRelationships(params = {}) {
  try {
    const response = await apiClient.get('/api/events/association/relationships', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch relationships',
    };
  }
}

/**
 * Get specific event relationship detail by ID
 */
export async function getEventRelationshipDetail(relationshipId) {
  try {
    const response = await apiClient.get(`/api/events/association/${encodeURIComponent(relationshipId)}`);
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch relationship detail',
    };
  }
}

/**
 * Get cluster centroid points for map display
 */
export async function getEventMapClusters(params = {}) {
  try {
    const response = await apiClient.get('/api/events/map/clusters', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch event map clusters',
    };
  }
}

/**
 * Get relationship vector lines connecting cluster centroids for map display
 */
export async function getEventMapRelationships(params = {}) {
  try {
    const response = await apiClient.get('/api/events/map/relationships', { params });
    return { success: true, data: response.data };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Failed to fetch event map relationships',
    };
  }
}

export default apiClient;
