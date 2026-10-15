import React from 'react';
import {
  Target,
  ArrowLeft,
  ChevronRight,
  AlertCircle,
  Gauge,
  TrendingUp,
} from 'lucide-react';
import { KpiGoals } from '../components/analysis/KpiGoals';

interface Props {
  analysisId?: string;
  datasetId?: string;
  datasetName?: string;
  onBackToWorkspace: () => void;
}

export const KpiGoalsPage: React.FC<Props> = ({
  analysisId,
  datasetId,
  datasetName,
  onBackToWorkspace,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <header className="rounded-2xl border border-[#13594c]/60 bg-gradient-to-br from-[#0b3a33] via-[#0e4a40] to-[#13594c] px-5 sm:px-6 py-5 space-y-5 shadow-sm">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs">
          <button
            onClick={onBackToWorkspace}
            className="inline-flex items-center gap-1.5 font-medium text-emerald-100/75 hover:text-white transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 rounded"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Analysis workspace
          </button>
          <ChevronRight className="w-3 h-3 text-emerald-200/40" />
          <span aria-current="page" className="font-semibold text-white">
            KPI goals
          </span>
        </nav>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Title block */}
          <div className="flex items-start gap-4 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500 text-white flex items-center justify-center shrink-0 shadow-sm ring-4 ring-white/10">
              <Target className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-white leading-tight">KPI goals</h1>
              <p className="text-sm text-emerald-50/75 mt-1 max-w-xl leading-relaxed">
                Set targets for your key metrics, then track current performance against them and
                see how far each one has left to go.
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      {analysisId && datasetId ? (
        <KpiGoals analysisId={analysisId} datasetId={datasetId} />
      ) : (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800">Run an analysis to set KPI goals</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Goals are tracked against the baseline from an analysis. Run the pipeline on your
              dataset first, then come back here.
            </p>
          </div>
          <button
            onClick={onBackToWorkspace}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Go to analysis workflow
          </button>
        </div>
      )}
    </div>
  );
};