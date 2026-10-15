import React, { useState } from 'react';
import {
  GitCommit,
  CheckCircle,
  ArrowRight,
  Database,
  FileSearch,
  Sigma,
  AlertTriangle,
  Lightbulb,
  ExternalLink,
  FileSpreadsheet,
  Layers,
  MapPin
} from 'lucide-react';
import { EvidenceChain } from '../../types';

interface Props {
  chains: EvidenceChain[];
  onSelectRecommendation: (recId: string) => void;
  onNavigateNext: () => void;
}

export const Stage6_EvidenceChains: React.FC<Props> = ({
  chains,
  onSelectRecommendation,
  onNavigateNext,
}) => {
  const [selectedChainId, setSelectedChainId] = useState<string>(
    chains[0]?.id || ''
  );

  const activeChain = chains.find((c) => c.id === selectedChainId) || chains[0];

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'Source':
        return <FileSpreadsheet className="w-4 h-4 text-slate-700" />;
      case 'Extracted Evidence':
        return <Layers className="w-4 h-4 text-cyan-600" />;
      case 'Observation':
        return <FileSearch className="w-4 h-4 text-blue-600" />;
      case 'Diagnostic Test':
        return <Database className="w-4 h-4 text-indigo-600" />;
      case 'Root Cause Proof':
        return <Sigma className="w-4 h-4 text-purple-600" />;
      case 'Risk Assessment':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'Action Prescribed':
        return <Lightbulb className="w-4 h-4 text-emerald-600" />;
      default:
        return <CheckCircle className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Research Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <GitCommit className="w-3.5 h-3.5" />
            Auditability Engine: 7-Stage Explainable Evidence Chains
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Traceable Analytic-to-Decision Audit Trails
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Eliminates the "black box" nature of traditional analytics by establishing an unbroken,
            verifiable chain: <span className="font-semibold text-slate-800">Source &rarr; Extracted Evidence &rarr; Observation &rarr; Diagnostic Test &rarr; Root Cause Proof &rarr; Risk Assessment &rarr; Action</span>.
          </p>
        </div>

        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 shrink-0">
          <span className="font-bold text-slate-900">{chains.length}</span> Verified Causal Chains
        </div>
      </div>

      {/* Chain Selector Pills */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {chains.map((chain) => {
          const isSelected = chain.id === (activeChain?.id);
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

      {/* Active Chain Trace Details */}
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
                Statistical Proof: <span className="font-mono text-purple-700 font-semibold">{activeChain.statistical_proof}</span>
              </p>
            </div>

            <button
              onClick={() => onSelectRecommendation(activeChain.associated_recommendation_id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors shrink-0"
            >
              <span>View Linked Recommendation ({activeChain.associated_recommendation_id})</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Stepper / Timeline Nodes */}
          <div className="space-y-4 relative before:absolute before:inset-0 before:left-5 before:w-0.5 before:bg-slate-200 before:z-0">
            {activeChain.nodes.map((node, nIdx) => {
              const isSource = node.stage === 'Source';
              const isExtracted = node.stage === 'Extracted Evidence';

              return (
                <div key={nIdx} className="relative z-10 flex items-start gap-4">
                  <div
                    className={`w-10 h-10 rounded-full bg-white border-2 flex items-center justify-center shadow-xs shrink-0 ${
                      isSource
                        ? 'border-slate-500 bg-slate-50'
                        : isExtracted
                        ? 'border-cyan-500 bg-cyan-50/40'
                        : 'border-slate-300'
                    }`}
                  >
                    {getStageIcon(node.stage)}
                  </div>

                  <div
                    className={`flex-1 p-4 rounded-xl border space-y-1.5 text-xs ${
                      isSource
                        ? 'bg-slate-50/90 border-slate-300'
                        : isExtracted
                        ? 'bg-cyan-50/20 border-cyan-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                          Step {nIdx + 1}: {node.stage}
                        </span>
                        {isSource && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                            Cryptographic Provenance
                          </span>
                        )}
                        {isExtracted && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-cyan-100 text-cyan-800">
                            Normalized Extraction
                          </span>
                        )}
                      </div>
                      <span className="font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 text-[11px]">
                        {node.metric_or_statistic}
                      </span>
                    </div>
                    <p className="text-slate-800 font-medium leading-relaxed">{node.detail}</p>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500 pt-1 border-t border-slate-200/60">
                      <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                      <span>
                        Source Evidence: <span className="italic text-slate-700 font-medium">{node.data_support}</span>
                      </span>
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
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">Proceed to Prioritized Management Recommendations</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Examine Prioritized Action Matrix</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
