import React from 'react';
import {
  Clock,
  ArrowRight,
  CheckCircle2,
  Lightbulb,
  HelpCircle
} from 'lucide-react';
import { RecommendationItem, DecisionRecord } from '../../types';

interface Props {
  recommendations: RecommendationItem[];
  decisions: DecisionRecord[];
  onOpenDecisionModal: (rec: RecommendationItem) => void;
  onNavigateNext: () => void;
  analysisId?: string;
  onOpenWhyResult?: (resultType: string, resultId: string) => void;
}

export const Stage5_Recommendations: React.FC<Props> = ({
  recommendations,
  decisions,
  onOpenDecisionModal,
  onNavigateNext,
  onOpenWhyResult,
}) => {
  const getDecisionForRec = (recId: string) => {
    return decisions.find((d) => d.recommendation_id === recId);
  };

  const getTierBadge = (level?: string, score?: number) => {
    const s = score ?? 0;
    if (s >= 80 || level === 'High Priority') {
      return 'bg-emerald-50 text-emerald-800 border-emerald-300';
    }
    if (s >= 60 || level === 'Medium Priority') {
      return 'bg-amber-50 text-amber-800 border-amber-300';
    }
    return 'bg-slate-100 text-slate-700 border-slate-300';
  };

  return (
    <div className="space-y-6">

      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Recommendations
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Prioritized business actions ordered by estimated impact, feasibility, and supporting evidence.
          </p>
        </div>

        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">Decisions Recorded</div>
          <div className="text-2xl font-black text-slate-900 mt-0.5">
            {decisions.length} / {recommendations.length}
          </div>
          <div className="text-[11px] text-slate-500">Decision Notes</div>
        </div>
      </div>

      {/* Recommendations Cards List */}
      <div className="space-y-4">
        {recommendations.map((rec, index) => {
          const recordedDecision = getDecisionForRec(rec.id);
          const priorityScore = Math.round(rec.priority_score || 50);
          const priorityLevel =
            rec.priority_level ||
            (priorityScore >= 80
              ? 'High Priority'
              : priorityScore >= 60
              ? 'Medium Priority'
              : 'Lower Priority');

          const hasImpact =
            typeof rec.expected_financial_impact === 'number' &&
            rec.expected_financial_impact > 0;

          return (
            <div
              key={rec.id}
              className={`bg-white rounded-2xl border transition-all shadow-xs p-6 space-y-4 ${
                recordedDecision
                  ? 'border-slate-300 ring-1 ring-blue-500/10'
                  : 'border-slate-200'
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full text-xs font-black bg-slate-900 text-white">
                      Rank #{index + 1}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getTierBadge(
                        priorityLevel,
                        priorityScore
                      )}`}
                    >
                      {priorityLevel} &bull; {priorityScore}/100
                    </span>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {rec.id} &bull; {rec.category}
                    </span>
                    {rec.urgency && (
                      <span className="inline-flex items-center gap-1 text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {rec.urgency}
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{rec.title}</h3>
                </div>

                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  {onOpenWhyResult && (
                    <button
                      type="button"
                      onClick={() => onOpenWhyResult('recommendation', rec.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors cursor-pointer"
                      title="Why this action? View deterministic rationale"
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                      <span>Why this action?</span>
                    </button>
                  )}
                  {recordedDecision ? (
                    <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                      <span className="text-xs text-slate-500">Status:</span>
                      <span
                        className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${
                          recordedDecision.decision_status === 'Accepted'
                            ? 'bg-emerald-100 text-emerald-800'
                            : recordedDecision.decision_status === 'Rejected'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {recordedDecision.decision_status}
                      </span>
                      <button
                        onClick={() => onOpenDecisionModal(rec)}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 ml-1 underline cursor-pointer"
                      >
                        Edit
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
                        Status: {rec.decision_status || 'Pending Review'}
                      </span>
                      <button
                        onClick={() => onOpenDecisionModal(rec)}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition-colors cursor-pointer"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Record Decision</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Main Content: Recommended Action */}
              <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-100 space-y-1">
                <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wide">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
                  <span>Recommended Action</span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {rec.what_to_do || rec.mechanism_of_action || rec.title}
                </p>
              </div>

              {/* Core Attributes Grid: Priority Score, Estimated Impact, Supporting Evidence */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                {/* Priority Score */}
                <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    Priority Score
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-xl font-black text-slate-900">{priorityScore}</span>
                    <span className="text-xs font-semibold text-slate-400">/ 100</span>
                    <span className={`ml-2 text-[10px] font-bold px-2 py-0.5 rounded border ${getTierBadge(priorityLevel, priorityScore)}`}>
                      {priorityLevel}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Ranked #{index + 1} across {recommendations.length} candidate actions
                  </p>
                </div>

                {/* Estimated Impact */}
                <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    Estimated Impact
                  </div>
                  {hasImpact ? (
                    <div className="text-lg font-black text-emerald-700">
                      +${rec.expected_financial_impact.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  ) : (
                    <div className="text-xs font-semibold text-slate-500 italic mt-1">
                      Estimated impact not available for this metric
                    </div>
                  )}
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {hasImpact ? 'Projected financial improvement' : 'Requires financial baseline metadata'}
                  </p>
                </div>

                {/* Supporting Evidence */}
                <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-1">
                  <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    Supporting Evidence
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed font-normal">
                    {rec.supporting_finding || rec.evidence || rec.why || rec.rationale || 'Supported by observed variance and statistical patterns.'}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Stage</div>
          <div className="text-sm font-semibold">Inspect Complete Evidence Trail</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
        >
          <span>Examine Evidence</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
