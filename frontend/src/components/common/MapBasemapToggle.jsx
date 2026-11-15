import React from 'react';
import { Moon, Satellite } from 'lucide-react';

/**
 * MapBasemapToggle — Glassmorphic Switcher between Dark Canvas and Satellite Imagery
 */
export default function MapBasemapToggle({ activeBasemap = 'dark', onChange, className = '' }) {
  return (
    <div
      className={`absolute top-3 right-3 z-[1000] flex items-center p-1 rounded-xl bg-space-950/85 border border-white/10 backdrop-blur-md shadow-2xl text-xs font-medium select-none ${className}`}
    >
      <button
        type="button"
        onClick={() => onChange('dark')}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
          activeBasemap === 'dark'
            ? 'bg-space-800 text-white shadow-sm border border-white/15 font-semibold'
            : 'text-space-400 hover:text-space-200'
        }`}
        title="Switch to Dark Canvas Basemap"
      >
        <Moon className="w-3.5 h-3.5 text-accent-blue" />
        <span>Dark</span>
      </button>
      <button
        type="button"
        onClick={() => onChange('satellite')}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg transition-all ${
          activeBasemap === 'satellite'
            ? 'bg-accent-blue text-white shadow-sm border border-accent-blue/30 font-semibold'
            : 'text-space-400 hover:text-space-200'
        }`}
        title="Switch to Satellite Imagery Basemap"
      >
        <Satellite className="w-3.5 h-3.5 text-amber-400" />
        <span>Satellite</span>
      </button>
    </div>
  );
}
