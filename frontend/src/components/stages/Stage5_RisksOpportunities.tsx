import React from 'react';
import {
  AlertTriangle,
  TrendingUp,
  Clock,
  ShieldAlert,
  ArrowRight,
  DollarSign,
  Target,
  Sparkles
} from 'lucide-react';
import { RisksAndOpportunitiesReport } from '../../types';

interface Props {
  report: RisksAndOpportunitiesReport;
  onNavigateNext: () => void;
}

export const Stage5_RisksOpportunities: React.FC<Props> = ({ report, onNavigateNext }) => {
  return (
    <div className="space-y-6">
      {/* Research Question Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Core Question 3: What requires attention?
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Risk Exposure Quantification & Strategic Opportunity Levers
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Deterministic identification of operational vulnerabilities, margin leakage, and growth
            vectors. Every risk is backed by early warning thresholds and quantified financial exposure.
          </p>
        </div>

        {/* Risk Profile Rating */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">
            Organizational Risk Profile
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {report.risk_profile_rating}
          </div>
          <div className="text-[11px] text-slate-500">
            {report.risks.length} active risk vector(s) identified
          </div>
        </div>
      </div>

      {/* Aggregate Financial Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Downside Risk Exposure */}
        <div className="bg-rose-50/60 p-5 rounded-xl border border-rose-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-rose-700 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4" />
              Total Financial Downside Exposure at Risk
            </div>
            <div className="text-3xl font-black text-rose-900 mt-1">
              ${report.total_exposure_at_risk.toLocaleString()}
            </div>
            <div className="text-xs text-rose-700 mt-1">
              Potential 30–90 day loss without managerial mitigation
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-100 flex items-center justify-center text-rose-700 font-extrabold text-lg">
            !
          </div>
        </div>

        {/* Upside Opportunity Value */}
        <div className="bg-emerald-50/60 p-5 rounded-xl border border-emerald-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              Total Identified Opportunity Upside
            </div>
            <div className="text-3xl font-black text-emerald-900 mt-1">
              +${report.total_opportunity_upside.toLocaleString()}
            </div>
            <div className="text-xs text-emerald-700 mt-1">
              Estimated value unlock via pricing discipline & segment scaling
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 font-extrabold text-lg">
            &uarr;
          </div>
        </div>
      </div>

      {/* Side-by-side Risk Radar & Opportunity Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risks Column */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              Prioritized Downside Risks ({report.risks.length})
            </h3>
            <span className="text-xs text-slate-500">Ranked by Financial Exposure</span>
          </div>

          <div className="space-y-3">
            {report.risks.map((risk) => (
              <div
                key={risk.id}
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2 hover:border-slate-300 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-bold text-slate-900 text-sm">{risk.title}</div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0 ${
                      risk.severity === 'High'
                        ? 'bg-rose-100 text-rose-800'
                        : risk.severity === 'Medium'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {risk.severity} Severity
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-slate-500">Exposure: </span>
                    <span className="font-bold text-rose-600">
                      ${risk.estimated_financial_exposure.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Probability: </span>
                    <span className="font-bold text-slate-800">{risk.probability_pct}%</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1 text-[11px] text-slate-500">
                    <Clock className="w-3 h-3 text-slate-400" />
                    Mitigation Window: {risk.mitigation_window_days} days
                  </div>
                </div>

                <div className="text-xs text-slate-600 space-y-0.5">
                  <div className="font-semibold text-slate-700">Early Warning Signals:</div>
                  {risk.early_warning_signals.map((sig, sIdx) => (
                    <div key={sIdx} className="text-slate-600 pl-2 border-l border-slate-200 text-[11px]">
                      &bull; {sig}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Opportunities Column */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              Strategic Growth Opportunities ({report.opportunities.length})
            </h3>
            <span className="text-xs text-slate-500">Ranked by Economic Upside</span>
          </div>

          <div className="space-y-3">
            {report.opportunities.map((opp) => (
              <div
                key={opp.id}
                className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2 hover:border-slate-300 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-bold text-slate-900 text-sm">{opp.title}</div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 shrink-0">
                    {opp.feasibility} Feasibility
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-slate-500">Potential Gain: </span>
                    <span className="font-bold text-emerald-600">
                      +${opp.potential_value_gain.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Confidence: </span>
                    <span className="font-bold text-slate-800">{opp.confidence_level_pct}%</span>
                  </div>
                  <div className="col-span-2 text-[11px] text-slate-500">
                    Target: <span className="font-semibold text-slate-700">{opp.target_segment}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-snug">
                  {opp.strategic_rationale}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">Proceed to Traceable Evidence Chains</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Examine Evidence Audit Trails</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
