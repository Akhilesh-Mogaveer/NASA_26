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

export default apiClient;
