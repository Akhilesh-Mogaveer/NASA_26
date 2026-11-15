import React from 'react';
import { Satellite, ShieldCheck, Database, ExternalLink } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-white/[0.08] bg-space-950/70 backdrop-blur-md py-8 text-xs text-space-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-6 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center space-x-2 text-space-200 font-semibold mb-2">
              <Satellite className="w-4 h-4 text-modis" />
              <span>FireLens Platform</span>
            </div>
            <p className="text-space-400 leading-relaxed">
              Harmonized satellite active-fire observation intelligence for MODIS and VIIRS instruments.
              Developed for the NASA Space Apps Challenge 2026.
            </p>
          </div>

          <div>
            <div className="flex items-center space-x-2 text-space-200 font-semibold mb-2">
              <ShieldCheck className="w-4 h-4 text-accent-blue" />
              <span>Scientific Notice</span>
            </div>
            <p className="text-space-400 leading-relaxed">
              Spatial-temporal associations do not confirm physical fire identity.
              Fire Radiative Power (FRP) represents radiant intensity, not burned area. Anomaly detection flags statistical deviation, not future fire predictions.
            </p>
          </div>

          <div>
            <div className="flex items-center space-x-2 text-space-200 font-semibold mb-2">
              <Database className="w-4 h-4 text-emerald-400" />
              <span>Primary Data Source</span>
            </div>
            <p className="text-space-400 leading-relaxed">
              NASA FIRMS (Fire Information for Resource Management System).
            </p>
            <div className="mt-2 flex items-center space-x-3">
              <a
                href="https://firms.modaps.eosdis.nasa.gov/"
                target="_blank"
                rel="noreferrer"
                className="text-space-300 hover:text-white flex items-center gap-1 transition-colors underline"
              >
                <span>FIRMS Portal</span>
                <ExternalLink className="w-3 h-3" />
              </a>
              <a
                href="https://firms.modaps.eosdis.nasa.gov/api/"
                target="_blank"
                rel="noreferrer"
                className="text-space-300 hover:text-white flex items-center gap-1 transition-colors underline"
              >
                <span>API Docs</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between text-space-500">
          <div>
            FireLens v0.1.0 &bull; Phase 1 Foundation Active &bull; NASA Space Apps Challenge 2026
          </div>
          <div className="mt-2 sm:mt-0 font-mono text-[11px]">
            MODIS (1km) &bull; VIIRS (375m) Harmonization
          </div>
        </div>
      </div>
    </footer>
  );
}
