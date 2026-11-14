import React from 'react';

export default function StatusBadge({ type, label, size = 'sm' }) {
  const sizeClasses = size === 'xs' 
    ? 'text-[10px] px-2 py-0.5' 
    : size === 'md' 
    ? 'text-xs px-3 py-1 font-semibold' 
    : 'text-xs px-2.5 py-0.5 font-medium';

  let colorClasses = 'bg-space-800 text-space-300 border-space-700';

  switch (type) {
    case 'modis':
      colorClasses = 'bg-modis/15 text-modis-light border-modis/40';
      break;
    case 'viirs':
      colorClasses = 'bg-viirs/15 text-viirs-light border-viirs/40';
      break;
    case 'matched':
    case 'healthy':
    case 'success':
      colorClasses = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      break;
    case 'warning':
    case 'unmatched':
      colorClasses = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      break;
    case 'error':
    case 'offline':
      colorClasses = 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      break;
    case 'info':
    case 'blue':
      colorClasses = 'bg-sky-500/15 text-sky-300 border-sky-500/30';
      break;
    default:
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${colorClasses} ${sizeClasses} transition-colors`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      {label}
    </span>
  );
}
