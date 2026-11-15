import React from 'react';
import { SENSOR_COLORS } from '../../theme/tokens';

/**
 * GlassTooltip — Custom Frosted Glass Tooltip for Recharts
 * 
 * Replaces hardcoded contentStyle objects with a translucent, blurred container,
 * specular border, and tabular mono values. Honors both formatter and labelFormatter.
 */
export default function GlassTooltip({
  active,
  payload,
  label,
  formatter,
  labelFormatter
}) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const displayLabel = labelFormatter ? labelFormatter(label, payload) : label;

  return (
    <div className="glass-panel rounded-xl p-3 text-xs shadow-2xl border border-white/15 min-w-[160px] animate-in fade-in zoom-in-95 duration-100">
      {displayLabel !== undefined && displayLabel !== null && displayLabel !== '' && (
        <div className="font-semibold text-white border-b border-white/10 pb-1.5 mb-2 font-mono">
          {displayLabel}
        </div>
      )}
      <div className="space-y-1.5">
        {payload.map((entry, index) => {
          const color = entry.color || entry.fill || entry.stroke || SENSOR_COLORS.neutral;
          let displayValue = typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value;
          let displayName = entry.name || 'Value';

          if (formatter) {
            const res = formatter(entry.value, entry.name, entry, index);
            if (Array.isArray(res)) {
              displayValue = res[0];
              if (res[1]) displayName = res[1];
            } else {
              displayValue = res;
            }
          }

          return (
            <div key={`item-${index}`} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 text-space-300">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="font-sans text-[11px]">{displayName}:</span>
              </div>
              <span className="font-mono font-bold text-white tabular-nums">
                {displayValue}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
