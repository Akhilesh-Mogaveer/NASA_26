import React from 'react';

/**
 * StatCard — Tactile Claymorphic KPI Card
 * 
 * Displays prominent statistical values with dual shadows, specular highlights,
 * and sensor/accent themed icon tiles.
 */
export default function StatCard({
  label,
  value,
  unit,
  subtitle,
  icon: Icon,
  trend,
  accentColor = 'blue',
  className = '',
}) {
  const accentStyles = {
    modis: {
      border: 'border-modis/30',
      text: 'text-modis',
      glow: 'shadow-glow-modis',
      iconBg: 'bg-modis/15 text-modis border-modis/30',
    },
    viirs: {
      border: 'border-viirs/30',
      text: 'text-viirs',
      glow: 'shadow-glow-viirs',
      iconBg: 'bg-viirs/15 text-viirs border-viirs/30',
    },
    blue: {
      border: 'border-accent-blue/30',
      text: 'text-white',
      glow: 'shadow-glow-blue',
      iconBg: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
    },
    emerald: {
      border: 'border-emerald-500/30',
      text: 'text-emerald-300',
      glow: 'shadow-emerald-950/40',
      iconBg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    },
    amber: {
      border: 'border-amber-500/30',
      text: 'text-amber-300',
      glow: 'shadow-amber-950/40',
      iconBg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    },
    neutral: {
      border: 'border-white/10',
      text: 'text-white',
      glow: 'shadow-black/40',
      iconBg: 'bg-space-800 text-space-300 border-white/10',
    },
  };

  const style = accentStyles[accentColor] || accentStyles.blue;

  return (
    <div
      className={`clay-card rounded-2xl p-4 sm:p-5 relative overflow-hidden flex flex-col justify-between ${style.border} ${className}`}
    >
      {/* Top row: Label and Icon Tile */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-space-400 uppercase tracking-wider">
          {label}
        </span>
        {Icon && (
          <div
            className={`w-8 h-8 rounded-xl flex items-center justify-center border ${style.iconBg} clay-pill`}
          >
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Main Metric Value */}
      <div className="mt-1 flex items-baseline gap-2">
        <span
          className={`font-mono text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums ${style.text}`}
        >
          {value}
        </span>
        {unit && (
          <span className="text-xs font-sans font-medium text-space-400">
            {unit}
          </span>
        )}
      </div>

      {/* Footer / Subtitle / Trend */}
      {(subtitle || trend) && (
        <div className="mt-3 pt-2.5 border-t border-white/[0.06] text-xs text-space-400 flex items-center justify-between">
          {subtitle && <span>{subtitle}</span>}
          {trend && <span className="font-medium text-space-300 ml-auto">{trend}</span>}
        </div>
      )}
    </div>
  );
}
