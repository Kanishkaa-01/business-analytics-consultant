import React, { useState } from 'react';
import {
  FileCheck2,
  AlertCircle,
  Database,
  Layers,
  Search,
  CheckCircle,
  HelpCircle,
  TrendingDown,
  Lightbulb,
  ExternalLink,
  ArrowRight
} from 'lucide-react';
import { EvidenceChain } from '../../types';

interface Props {
  chains: EvidenceChain[];
  onSelectRecommendation: (recId: string) => void;
  onNavigateNext: () => void;
}

export const Evidence: React.FC<Props> = ({
  chains,
  onSelectRecommendation,
  onNavigateNext,
}) => {
  const [selectedChainId, setSelectedChainId] = useState<string>(
    chains[0]?.id || ''
  );

  const activeChain = chains.find((c) => c.id === selectedChainId) || chains[0];

  const getStepIcon = (stage: string) => {
    switch (stage) {
      case 'Data Source':
        return <Database className="w-4 h-4 text-slate-700" />;
      case 'Data Extracted':
        return <Layers className="w-4 h-4 text-cyan-600" />;
      case 'Observed Pattern':
        return <Search className="w-4 h-4 text-blue-600" />;
      case 'Data Check':
        return <CheckCircle className="w-4 h-4 text-indigo-600" />;
      case 'Possible Reason':
        return <HelpCircle className="w-4 h-4 text-purple-600" />;
      case 'Estimated Impact':
        return <TrendingDown className="w-4 h-4 text-amber-600" />;
      case 'Recommended Action':
        return <Lightbulb className="w-4 h-4 text-emerald-600" />;
      default:
        return <CheckCircle className="w-4 h-4 text-slate-500" />;
    }
  };

  const getStepNumber = (stage: string, idx: number) => {
    const map: Record<string, number> = {
      'Data Source': 1,
      'Data Extracted': 2,
      'Observed Pattern': 3,
      'Data Check': 4,
      'Possible Reason': 5,
      'Estimated Impact': 6,
      'Recommended Action': 7
    };
    return map[stage] || idx + 1;
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Traceable Evidence Trail
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Every analytical conclusion is backed by an unbroken trail from raw source data to the final recommended action.
          </p>
        </div>

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 shrink-0">
          <span className="font-bold text-slate-900">{chains.length}</span> Traceable Evidence Trails
        </div>
      </div>

      {/* Prominent Disclaimer Banner */}
      <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-xl flex items-center gap-3 text-xs text-amber-900 shadow-2xs">
        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
        <span className="font-semibold">
          Note: An observed relationship does not necessarily prove causation. The steps below show the empirical trail connecting data observation to action.
        </span>
      </div>

      {/* Trail Selector Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {chains.map((chain) => {
          const isSelected = chain.id === activeChain?.id;
          return (
            <button
              key={chain.id}
              onClick={() => setSelectedChainId(chain.id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border ${
                isSelected
                  ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              {chain.title}
            </button>
          );
        })}
      </div>

      {/* Active Trail Stepper */}
      {activeChain && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
            <div>
              <div className="text-xs uppercase font-bold text-blue-600">
                Evidence Trail ID: {activeChain.id}
              </div>
              <h3 className="text-base font-bold text-slate-900">{activeChain.title}</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Target Metric: <span className="font-semibold text-slate-700">{activeChain.target_metric}</span> &bull;{' '}

              </p>
            </div>

            <button
              onClick={() => onSelectRecommendation(activeChain.associated_recommendation_id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors shrink-0"
            >
              <span>Go to Recommendation ({activeChain.associated_recommendation_id})</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 7 Clean Steps */}
          <div className="space-y-4 relative before:absolute before:inset-0 before:left-5 before:w-0.5 before:bg-slate-200 before:z-0">
            {activeChain.nodes.map((node, nIdx) => {
              const stepNumber = getStepNumber(node.stage, nIdx);
              return (
                <div key={nIdx} className="relative z-10 flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-white border-2 border-slate-200 flex items-center justify-center font-bold text-xs text-slate-700 shadow-2xs shrink-0 group-hover:border-blue-500">
                    {stepNumber}
                  </div>

                  <div className="flex-1 bg-slate-50/70 p-4 rounded-xl border border-slate-200 hover:border-blue-200 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        {getStepIcon(node.stage)}
                        <span className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                          Step {stepNumber}: {node.stage}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white text-slate-700 border border-slate-200 shrink-0">
                        {node.metric_or_statistic}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed font-medium">
                      {node.detail}
                    </p>

                    <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                      <span>Data Reference: <b className="text-slate-700">{node.data_support}</b></span>
                      <span className="text-emerald-700 font-semibold">&bull; Audit Verified</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Stage</div>
          <div className="text-sm font-semibold">Test Scenarios in What-If Interactive Simulator</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Run What-If Analysis</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export { Evidence as Stage6_EvidenceTrail, Evidence as EvidenceTrail };

