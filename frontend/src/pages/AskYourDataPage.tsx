import React from 'react';
import {
  ArrowLeft,
  MessageSquareText,
  HelpCircle,
  ShieldCheck,
  Lightbulb,
  Database,
  ChevronRight,
  Table2,
  Repeat,
} from 'lucide-react';
import { AskYourData } from '../components/analysis/AskYourData';

interface Props {
  datasetId?: string;
  datasetName?: string;
  onBackToWorkspace: () => void;
}

const QUESTION_TIPS: { pattern: string; example: string }[] = [
  { pattern: 'Metric + grouping', example: 'Total net_revenue by region' },
  { pattern: 'Rankings', example: 'Top 5 categories by profit' },
  { pattern: 'Change over time', example: 'Monthly trend of net_revenue' },
  { pattern: 'Averages', example: 'Average order value by channel' },
];

export const AskYourDataPage: React.FC<Props> = ({
  datasetId,
  datasetName,
  onBackToWorkspace,
}) => {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <header className="rounded-2xl border border-[#1b2f5c] bg-gradient-to-br from-[#0b1f44] via-[#102a58] to-[#1a3a7a] px-5 sm:px-6 py-5 space-y-5 shadow-sm">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs">
          <button
            onClick={onBackToWorkspace}
            className="inline-flex items-center gap-1.5 font-medium text-blue-200/80 hover:text-white transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 rounded"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Analysis workspace
          </button>
          <ChevronRight className="w-3 h-3 text-blue-300/40" />
          <span aria-current="page" className="font-semibold text-white">
            Ask your data
          </span>
        </nav>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Title block */}
          <div className="flex items-start gap-4 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500 text-white flex items-center justify-center shrink-0 shadow-sm ring-4 ring-white/10">
              <MessageSquareText className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-white leading-tight">
                Ask your data
              </h1>
              <p className="text-sm text-blue-100/75 mt-1 max-w-xl leading-relaxed">
                Ask a question in plain language and get an answer calculated
                directly from your dataset.
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      {datasetId ? (
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-6 items-start">
          {/* Query tool */}
          <section className="min-w-0">
            <AskYourData datasetId={datasetId} />
          </section>

          {/* Guidance rail */}
          <aside className="space-y-4 xl:sticky xl:top-0">
            {datasetName && (
              <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
                  <Database className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] text-slate-400 font-medium">
                    Querying
                  </div>
                  <div className="text-sm font-semibold text-slate-900 leading-snug break-words">
                    {datasetName}
                  </div>
                </div>
              </div>
            )}

            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                <h2 className="text-sm font-bold text-slate-900">
                  Questions that work well
                </h2>
              </div>
              <ul className="divide-y divide-slate-100">
                {QUESTION_TIPS.map((tip) => (
                  <li key={tip.pattern} className="py-2.5 first:pt-0 last:pb-0">
                    <div className="text-xs font-semibold text-slate-700">
                      {tip.pattern}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      “{tip.example}”
                    </div>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-100">
                Use column names as they appear in your dataset for the most
                precise results.
              </p>
            </div>

          </aside>
        </div>
      ) : (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
            <HelpCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800">
              Select a dataset to start asking questions
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Upload or choose a dataset in the analysis workflow, then come
              back here to query it.
            </p>
          </div>
          <button
            onClick={onBackToWorkspace}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Choose a dataset
          </button>
        </div>
      )}
    </div>
  );
};