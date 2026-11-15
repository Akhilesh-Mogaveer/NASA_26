import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * EmptyState — Unified Glassmorphic Empty / Error State Container
 */
export default function EmptyState({
  title = 'No Data Available',
  message,
  icon: Icon = AlertCircle,
  action,
  isError = false,
  className = '',
}) {
  return (
    <div
      className={`p-8 rounded-2xl border flex flex-col items-center justify-center text-center gap-3 ${
        isError
          ? 'bg-rose-950/25 border-rose-500/30 text-rose-200'
          : 'glass-panel text-space-300'
      } ${className}`}
    >
      <div
        className={`w-10 h-10 rounded-xl flex items-center justify-center border clay-pill ${
          isError
            ? 'bg-rose-900/40 border-rose-500/40 text-rose-400'
            : 'bg-space-800 border-white/10 text-space-400'
        }`}
      >
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-white tracking-tight">{title}</h4>
        {message && <p className="text-xs text-space-400 mt-1 max-w-md">{message}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
