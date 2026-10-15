import React, { useState, useRef, useEffect } from 'react';
import {
  History,
  Home
} from 'lucide-react';

interface Props {
  dbDialect: string;
  onOpenUploadModal: () => void;
  onSeedSamples: () => void;
  isSeeding: boolean;
  onOpenStoredAnalyses?: () => void;
  onGoHome?: () => void;
  currentView?: string;
}

export const Header: React.FC<Props> = ({
  dbDialect,
  onOpenUploadModal,
  onSeedSamples,
  isSeeding,
  onOpenStoredAnalyses,
  onGoHome,
  currentView = 'home',
}) => {
  const [actionsOpen, setActionsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setActionsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Product Identity */}
          <div className="flex items-center gap-3">
            <button
              onClick={onGoHome}
              className="flex items-center gap-3 text-left hover:opacity-95 transition-opacity cursor-pointer group"
              title="Business Analytics Consultant — Return to Home"
            >

              <img
                src="/business-favicon.png"
                alt="Business Analytics Consultant"
                className="w-10 h-10 shrink-0 object-contain transition-transform group-hover:scale-105"
                draggable={false}
              />

              <div>
                <span className="font-bold text-slate-900 text-base sm:text-lg tracking-tight block leading-tight">
                  Business Analytics Consultant
                </span>
              </div>
            </button>
          </div>

          {/* Right Global Application Navigation Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Home Navigation Button */}
            {onGoHome && (
              <button
                onClick={onGoHome}
                className={`inline-flex items-center gap-1.5 rounded-md
    px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${currentView === 'home'
                    ? 'bg-blue-50 text-blue-600'
                    : 'bg-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                  }`}
                title="Go to Home Landing Page"
              >
                <Home
                  className={`h-4 w-4 ${currentView === 'home' ? 'text-blue-600' : 'text-slate-500'
                    }`}
                />
                <span>Home</span>
              </button>
            )}

            {/* Stored Analyses Navigation Button */}
            {onOpenStoredAnalyses && (
              <button
                onClick={onOpenStoredAnalyses}
                className={`inline-flex items-center gap-1.5 rounded-md
    px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${currentView === 'history'
                    ? 'bg-blue-50 text-blue-600'
                    : 'bg-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                  }`}
                title="View past analytical runs and decision history"
              >
                <History
                  className={`h-4 w-4 ${currentView === 'history' ? 'text-blue-600' : 'text-slate-500'
                    }`}
                />
                <span>Analyses</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
