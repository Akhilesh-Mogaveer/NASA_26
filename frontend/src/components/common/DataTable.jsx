import React from 'react';

/**
 * DataTable — Glassmorphic Table Wrapper
 * 
 * Provides responsive horizontal scrolling, a sticky frosted glass header,
 * and high-contrast row hover states without heavy per-cell shadows.
 */
export default function DataTable({ headers = [], children, className = '', maxScrollHeight }) {
  return (
    <div
      className={`overflow-x-auto rounded-xl border border-white/10 bg-space-900/60 shadow-inner ${className}`}
      style={maxScrollHeight ? { maxHeight: maxScrollHeight } : undefined}
    >
      <table className="w-full text-left text-xs border-collapse">
        {headers.length > 0 && (
          <thead className="sticky top-0 z-10 bg-space-850/95 backdrop-blur-md border-b border-white/10 text-space-400 font-semibold uppercase tracking-wider text-[11px]">
            <tr>
              {headers.map((h, i) => (
                <th
                  key={i}
                  className={`py-3 px-4 ${h.className || ''}`}
                >
                  {h.label || h}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="divide-y divide-white/[0.05] text-space-300 font-sans">
          {children}
        </tbody>
      </table>
    </div>
  );
}
