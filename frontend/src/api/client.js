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

export default apiClient;
