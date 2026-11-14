import React from 'react';

export default function Card({ title, subtitle, action, children, className = '' }) {
  return (
    <div className={`bg-space-850 border border-space-700/80 rounded-xl p-5 shadow-lg backdrop-blur-sm ${className}`}>
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-space-700/60">
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
