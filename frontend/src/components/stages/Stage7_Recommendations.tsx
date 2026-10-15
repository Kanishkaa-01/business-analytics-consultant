import React from 'react';
import {
  CheckSquare,
  Zap,
  Clock,
  DollarSign,
  ShieldCheck,
  ArrowRight,
  Sliders,
  CheckCircle2,
  XCircle,
  FileText,
  AlertCircle
} from 'lucide-react';
import { RecommendationItem, DecisionRecord } from '../../types';

interface Props {
  recommendations: RecommendationItem[];
  decisions: DecisionRecord[];
  onOpenDecisionModal: (rec: RecommendationItem) => void;
  onNavigateNext: () => void;
}

export const Stage7_Recommendations: React.FC<Props> = ({
  recommendations,
  decisions,
  onOpenDecisionModal,
  onNavigateNext,
}) => {
  const getDecisionForRec = (recId: string) => {
    return decisions.find((d) => d.recommendation_id === recId);
  };

  const getTierColor = (tier: string) => {
    if (tier.includes('P1')) return 'bg-rose-50 text-rose-700 border-rose-200';
    if (tier.includes('P2')) return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-blue-50 text-blue-700 border-blue-200';
  };

  return (
    <div className="space-y-6">
      {/* Research Question Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckSquare className="w-3.5 h-3.5" />
            Core Question 4: What action could management consider?
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Prioritized Management Recommendations & Action Matrix
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Prescriptions are generated deterministically from diagnostic variances, statistical factor
            attributions, and quantified risks. Ranked using Multi-Criteria Decision Analysis (ICE Score).
          </p>
        </div>

        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">Decisions Recorded</div>
          <div className="text-2xl font-black text-slate-900 mt-0.5">
            {decisions.length} / {recommendations.length}
          </div>
          <div className="text-[11px] text-slate-500">Human-in-the-loop Decision Tracking</div>
        </div>
      </div>

      {/* Prioritization Guide Banner */}
      <div className="bg-blue-50/70 border border-blue-200 rounded-xl p-4 text-xs text-blue-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-blue-600 shrink-0" />
          <span>
            <b>MCDA / ICE Scoring Framework:</b> Priority = (Impact &times; Confidence &times; Ease) / 10.
            P1 actions deliver highest financial recovery with rapid feasibility.
          </span>
        </div>
      </div>

      {/* Recommendations Cards List */}
      <div className="space-y-4">
        {recommendations.map((rec) => {
          const recordedDecision = getDecisionForRec(rec.id);
          return (
            <div
              key={rec.id}
              className={`bg-white rounded-2xl border transition-all shadow-xs p-6 space-y-4 ${
                recordedDecision ? 'border-slate-300 ring-1 ring-blue-500/10' : 'border-slate-200'
              }`}
            >
              {/* Header: Title, Urgency, Priority Tier, Action Button */}
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase border ${getTierColor(
                        rec.priority_tier
                      )}`}
                    >
                      {rec.priority_tier}
                    </span>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {rec.id} &bull; {rec.category}
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {rec.urgency}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{rec.title}</h3>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {recordedDecision ? (
                    <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                      <span className="text-xs text-slate-500">Decision:</span>
                      <span
                        className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${
                          recordedDecision.decision_status === 'Accepted'
                            ? 'bg-emerald-100 text-emerald-800'
                            : recordedDecision.decision_status === 'Rejected'
                            ? 'bg-rose-100 text-rose-800'
                            : recordedDecision.decision_status === 'Deferred'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {recordedDecision.decision_status}
                      </span>
                      <button
                        onClick={() => onOpenDecisionModal(rec)}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 ml-1 underline"
                      >
                        Edit
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => onOpenDecisionModal(rec)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition-colors"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Record Decision</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Rationale & Mechanism of Action */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-1">
                  <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px] text-blue-700">
                    Mechanism of Action (Intervention Strategy)
                  </div>
                  <p className="text-slate-700 leading-relaxed">{rec.mechanism_of_action}</p>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-1">
                  <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px] text-purple-700">
                    Statistical & Diagnostic Rationale
                  </div>
                  <p className="text-slate-700 leading-relaxed">{rec.rationale}</p>
                </div>
              </div>

              {/* Prerequisites & Tradeoffs */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="space-y-1.5">
                  <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                    Prerequisites for Execution:
                  </span>
                  <ul className="space-y-1 text-slate-600 pl-3 border-l-2 border-slate-200">
                    {rec.prerequisites.map((req, rIdx) => (
                      <li key={rIdx}>&bull; {req}</li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-1.5">
                  <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px] text-amber-700">
                    Tradeoffs & Implementation Risks:
                  </span>
                  <p className="text-slate-600 italic bg-amber-50/50 p-2.5 rounded-lg border border-amber-200/60">
                    {rec.tradeoffs_and_risks}
                  </p>
                </div>
              </div>

              {/* Scorecard Bar: Financial Gain, Effort, Confidence, ICE Breakdown */}
              <div className="bg-slate-900 text-white p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-4 text-xs">
                <div className="flex items-center gap-4">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">
                      Expected Return
                    </span>
                    <span className="text-emerald-400 font-extrabold text-sm">
                      +${rec.expected_financial_impact.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-6 w-px bg-slate-800" />
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Effort</span>
                    <span className="font-bold text-white text-sm">{rec.implementation_effort}</span>
                  </div>
                  <div className="h-6 w-px bg-slate-800" />
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">
                      Confidence
                    </span>
                    <span className="font-bold text-blue-300 text-sm">{rec.confidence_score_pct}%</span>
                  </div>
                </div>

                {/* ICE Breakdown */}
                <div className="flex items-center gap-3 bg-slate-800/80 px-3 py-1.5 rounded-lg font-mono text-[11px]">
                  <span>Impact: {rec.impact_score}/10</span>
                  <span>&bull;</span>
                  <span>Confidence: {rec.confidence_score}/10</span>
                  <span>&bull;</span>
                  <span>Ease: {rec.ease_score}/10</span>
                  <span className="text-amber-400 font-bold ml-1">
                    [ICE Score: {rec.priority_score}]
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">
            Proceed to Decision Support & Interactive What-If Simulator
          </div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Open Interactive Simulator</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
