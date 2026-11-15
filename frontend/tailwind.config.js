/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Satellite Intelligence Dark Palette
        space: {
          950: '#070b12', // Deepest background
          900: '#0b111e', // Dark charcoal/navy canvas
          850: '#10192a', // Card surface
          800: '#172338', // Elevated surface / panel
          700: '#23334d', // Subtle borders
          600: '#344766', // Muted borders
          500: '#526b91', // Supporting text
          400: '#8ba2c4', // Secondary text
          300: '#b8c9e0', // High contrast text
          200: '#e1e9f4',
          100: '#f0f5fc',
        },
        // Sensor Accents
        modis: {
          DEFAULT: '#f97316', // Warm Orange
          dark: '#ea580c',
          light: '#fdba74',
          subtle: 'rgba(249, 115, 22, 0.12)',
        },
        viirs: {
          DEFAULT: '#ef4444', // Radiant Red
          dark: '#dc2626',
          light: '#fca5a5',
          subtle: 'rgba(239, 68, 68, 0.12)',
        },
        matched: {
          DEFAULT: '#10b981', // Emerald for verified associations
          subtle: 'rgba(16, 185, 129, 0.12)',
        },
        accent: {
          blue: '#38bdf8', // Instrument telemetry cyan
          amber: '#f59e0b',
        },
        // 5-Step FireMap Observation Density Ramp
        density: {
          extreme: '#ef4444',
          high: '#f97316',
          medium: '#fb923c',
          moderate: '#facc15',
          low: '#38bdf8',
        },
        // Event Graph & Lineage Colors
        event: {
          split: '#a855f7',
          merge: '#ec4899',
          continuation: '#10b981',
          complex: '#6366f1',
        },
        // Glassmorphism Surface Tokens
        glass: {
          surface: 'rgba(16, 25, 42, 0.70)',
          card: 'rgba(11, 17, 30, 0.80)',
          overlay: 'rgba(7, 11, 18, 0.85)',
          border: 'rgba(255, 255, 255, 0.10)',
          highlight: 'rgba(255, 255, 255, 0.16)',
        },
      },
      boxShadow: {
        'clay': '8px 8px 20px rgba(0, 0, 0, 0.55), inset 1px 1px 1.5px rgba(255, 255, 255, 0.18), inset -2px -2px 4px rgba(0, 0, 0, 0.45)',
        'clay-sm': '4px 4px 10px rgba(0, 0, 0, 0.45), inset 1px 1px 1px rgba(255, 255, 255, 0.20), inset -1px -1px 2px rgba(0, 0, 0, 0.40)',
        'clay-pressed': 'inset 2px 2px 5px rgba(0, 0, 0, 0.65), inset -1px -1px 2px rgba(255, 255, 255, 0.08)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glow-modis': '0 0 24px -4px rgba(249, 115, 22, 0.35)',
        'glow-viirs': '0 0 24px -4px rgba(239, 68, 68, 0.35)',
        'glow-blue': '0 0 24px -4px rgba(56, 189, 248, 0.35)',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
