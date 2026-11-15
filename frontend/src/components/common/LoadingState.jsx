import React from 'react';
import { RefreshCw } from 'lucide-react';

/**
 * LoadingState — Unified Glassmorphic Loading Indicator
 */
export default function LoadingState({
  message = 'Loading telemetry data...',
  icon: Icon = RefreshCw,
  className = '',
}) {
  return (
    <div
      className={`p-12 rounded-2xl glass-panel flex flex-col items-center justify-center text-center gap-3 ${className}`}
    >
      <div className="relative flex items-center justify-center">
        <span className="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-modis/30 opacity-75" />
        <div className="w-10 h-10 rounded-xl bg-space-800 border border-white/10 flex items-center justify-center clay-pill">
          <Icon className="w-5 h-5 text-modis animate-spin" />
        </div>
      </div>
      <p className="text-xs font-medium text-space-300 tracking-tight mt-1">{message}</p>
    </div>
  );
}
