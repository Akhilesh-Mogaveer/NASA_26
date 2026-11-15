/**
 * FireLens Design Tokens
 * 
 * Centralized color tokens, thresholds, and chart themes for Recharts, Leaflet,
 * and dynamic styling where Tailwind utility classes cannot be used.
 */

// Core Sensor Identity (Strictly Unified Across All Views)
export const SENSOR_COLORS = {
  modis: '#f97316',        // Warm Orange (1km nadir)
  modisDark: '#ea580c',
  modisLight: '#fdba74',
  modisSubtle: 'rgba(249, 115, 22, 0.15)',

  viirs: '#ef4444',        // Radiant Red (375m nadir)
  viirsDark: '#dc2626',
  viirsLight: '#fca5a5',
  viirsSubtle: 'rgba(239, 68, 68, 0.15)',

  matched: '#10b981',      // Emerald (verified cross-sensor association)
  matchedSubtle: 'rgba(16, 185, 129, 0.15)',

  ambiguous: '#f59e0b',    // Amber (competing candidate / uncertainty)
  ambiguousSubtle: 'rgba(245, 158, 11, 0.15)',

  unmatched: '#64748b',    // Slate / Neutral
  neutral: '#64748b',
};

// Temporal Event Graph Lineage & Branching Colors
export const EVENT_COLORS = {
  continuation: '#10b981', // Emerald (clean 1-to-1 continuity)
  split: '#a855f7',        // Purple (1-to-N cluster branching)
  merge: '#ec4899',        // Pink (N-to-1 cluster convergence)
  complex: '#6366f1',      // Indigo (multi-front complex network)
  isolated: '#64748b',     // Neutral gray (single overpass detection)
};

// 5-Step FireMap Active Fire Observation Density Ramp
export const DENSITY_RAMP = [
  { threshold: 25000, color: '#ef4444', label: '> 25,000 obs', level: 'Extreme' },
  { threshold: 10000, color: '#f97316', label: '10,000 – 25,000', level: 'High' },
  { threshold: 5000,  color: '#fb923c', label: '5,000 – 10,000', level: 'Elevated' },
  { threshold: 1000,  color: '#facc15', label: '1,000 – 5,000', level: 'Moderate' },
  { threshold: 0,     color: '#38bdf8', label: '< 1,000 obs', level: 'Low' },
];

/**
 * Returns marker color for FireMap density grid cells
 */
export function getDensityColor(count) {
  for (const step of DENSITY_RAMP) {
    if (count > step.threshold) return step.color;
  }
  return '#38bdf8';
}

/**
 * Returns marker radius for FireMap density grid cells
 */
export function getDensityRadius(count) {
  if (count > 25000) return 11;
  if (count > 10000) return 9;
  if (count > 5000) return 7;
  if (count > 1000) return 5;
  return 3.5;
}

// Recharts Global Theme Styling Tokens
// Note: Axis/tick text is strictly #8ba2c4 (space-400), grid stroke is #23334d (space-700)
export const CHART_THEME = {
  gridStroke: '#23334d',
  gridOpacity: 0.6,
  axisStroke: '#8ba2c4',
  tickText: '#8ba2c4',
  fontSize: 11,
  fontFamily: '"JetBrains Mono", monospace',
  tooltip: {
    backgroundColor: 'rgba(11, 17, 30, 0.88)',
    borderColor: 'rgba(255, 255, 255, 0.12)',
    borderRadius: '12px',
    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
    color: '#e1e9f4',
    fontSize: '12px',
    padding: '10px 14px',
  },
};

// Canvas Surfaces and Ambient Light
export const CANVAS_THEME = {
  bgDeep: '#070b12',
  bgCard: 'rgba(16, 25, 42, 0.75)',
  bgGlass: 'rgba(11, 17, 30, 0.70)',
  borderGlass: 'rgba(255, 255, 255, 0.10)',
};

// Leaflet Map Theme Tokens (Esri Dark Gray Canvas by default; optional CARTO key via VITE_CARTO_API_KEY)
const cartoKey = typeof import.meta !== 'undefined' && import.meta.env?.VITE_CARTO_API_KEY;

export const MAP_THEME = {
  backgroundColor: '#070b12',
  tileUrl: cartoKey 
    ? `https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${cartoKey}`
    : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
  attribution: cartoKey
    ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    : 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, DeLorme, NAVTEQ',
  maxZoom: 16,
};
