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
          DEFAULT: '#f97316', // Orange-500
          dark: '#ea580c',
          light: '#fdba74',
          subtle: 'rgba(249, 115, 22, 0.12)',
        },
        viirs: {
          DEFAULT: '#ef4444', // Red-500
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
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
