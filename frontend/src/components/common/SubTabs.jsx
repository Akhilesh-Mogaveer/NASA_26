import React from 'react';

/**
 * SubTabs — Frosted Glass Container with Clay Active Pill
 * 
 * Reusable subtab bar replacing duplicated tab logic across MatchingView,
 * EventExplorerView, and EventEvolutionView.
 */
export default function SubTabs({ tabs = [], activeTab, onChange, className = '' }) {
  return (
    <div
      className={`glass-panel p-1.5 rounded-2xl flex items-center gap-1.5 overflow-x-auto max-w-full ${className}`}
      role="tablist"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
              isActive
                ? 'clay-button bg-space-800 text-white border border-white/20 shadow-clay-sm'
                : 'text-space-400 hover:text-white hover:bg-white/[0.05]'
            }`}
          >
            {Icon && (
              <Icon
                className={`w-3.5 h-3.5 transition-colors ${
                  isActive ? 'text-modis' : 'text-space-400'
                }`}
              />
            )}
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
