import React from 'react';

export default function Card({ title, subtitle, action, children, className = '' }) {
  return (
    <div className={`relative overflow-hidden bg-space-850/80 border border-white/[0.08] rounded-2xl p-5 shadow-lg shadow-black/40 transition-all duration-200 before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/15 before:to-transparent ${className}`}>
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-white/[0.06]">
          <div>
            {title && <h3 className="text-base font-semibold text-space-100 tracking-tight">{title}</h3>}
            {subtitle && <p className="text-xs text-space-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="flex items-center space-x-2">{action}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
}
