import React from 'react';

/**
 * StatusBadge — Claymorphic Status Indicator Pill
 * 
 * Supports identical type keys with updated clay dual shadow styling and
 * specular highlights.
 */
export default function StatusBadge({ type, label, size = 'sm' }) {
  const sizeClasses = size === 'xs' 
    ? 'text-[10px] px-2 py-0.5' 
    : size === 'md' 
    ? 'text-xs px-3 py-1 font-semibold' 
    : 'text-xs px-2.5 py-0.5 font-medium';

  let colorClasses = 'bg-space-850 text-space-300 border-white/10 shadow-clay-sm';

  switch (type) {
    case 'modis':
      colorClasses = 'bg-modis/15 text-modis-light border-modis/40 shadow-glow-modis/20';
      break;
    case 'viirs':
      colorClasses = 'bg-viirs/15 text-viirs-light border-viirs/40 shadow-glow-viirs/20';
      break;
    case 'matched':
    case 'healthy':
    case 'success':
      colorClasses = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/35';
      break;
    case 'warning':
    case 'unmatched':
      colorClasses = 'bg-amber-500/15 text-amber-300 border-amber-500/35';
      break;
    case 'error':
    case 'offline':
      colorClasses = 'bg-rose-500/15 text-rose-300 border-rose-500/35';
      break;
    case 'info':
    case 'blue':
      colorClasses = 'bg-sky-500/15 text-sky-300 border-sky-500/35 shadow-glow-blue/20';
      break;
    default:
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border clay-pill ${colorClasses} ${sizeClasses} transition-all duration-150`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-90 shadow-sm" />
      <span className="tracking-tight">{label}</span>
    </span>
  );
}
