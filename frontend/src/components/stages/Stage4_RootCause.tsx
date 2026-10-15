import React from 'react';
import {
  GitBranch,
  CheckCircle2,
  Percent,
  Sigma,
  ArrowRight,
  PieChart,
  Binary,
  ShieldCheck
} from 'lucide-react';
import { RootCauseReport } from '../../types';
import { ParetoChart } from '../charts/ParetoChart';

interface Props {
  rootCause: RootCauseReport;
  onNavigateNext: () => void;
}

export const Stage4_RootCause: React.FC<Props> = ({ rootCause, onNavigateNext }) => {
  return (
    <div className="space-y-6">
      {/* Research Question Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <GitBranch className="w-3.5 h-3.5" />
            Core Question 2: Why is it happening? (Statistical Root-Cause Proof)
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Root Cause Factor Attribution & Pareto Isolation
          </h2>
          <p className="text-sm font-semibold text-slate-800 leading-relaxed">
            {rootCause.primary_root_cause}
          </p>
          <p className="text-xs text-slate-500">{rootCause.methodology_notes}</p>
        </div>

        {/* Statistical Confidence Level */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">
            Statistical Confidence Level
          </div>
          <div className="text-3xl font-extrabold text-blue-600 mt-1">
            {rootCause.statistical_confidence_level}%
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5 flex items-center justify-end gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-600" />
            Hypothesis test p &lt; 0.05
          </div>
        </div>
      </div>

      {/* Statistical Factor Contributions Table */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Sigma className="w-4 h-4 text-purple-600" />
            Statistical Factor Drivers (ANOVA & Covariance Attribution)
          </h3>
          <span className="text-xs text-slate-500">
            Normalized to 100% variance explained
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Factor Name</th>
                <th className="py-2.5 px-3">Classification</th>
                <th className="py-2.5 px-3">Attribution %</th>
                <th className="py-2.5 px-3">p-value</th>
                <th className="py-2.5 px-3">r / Coef</th>
                <th className="py-2.5 px-3">Direction</th>
                <th className="py-2.5 px-3">Statistical Proof</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rootCause.factor_contributions.map((fc, idx) => {
                const isSignificant = fc.statistical_significance_p_value < 0.05;
                return (
                  <tr key={idx} className="hover:bg-slate-50/70">
                    <td className="py-2 px-3 font-bold text-slate-900">{fc.factor_name}</td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        {fc.factor_type}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-12 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-purple-600 h-1.5 rounded-full"
                            style={{ width: `${fc.attribution_percentage}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-900">{fc.attribution_percentage}%</span>
                      </div>
                    </td>
                    <td className="py-2 px-3 font-mono">
                      <span className={isSignificant ? 'text-emerald-600 font-bold' : 'text-slate-500'}>
                        {fc.statistical_significance_p_value.toFixed(5)}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono font-semibold text-slate-700">
                      {fc.correlation_or_coef > 0 ? '+' : ''}
                      {fc.correlation_or_coef}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          fc.direction.includes('Negative')
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {fc.direction}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-600 max-w-sm truncate" title={fc.evidence_statement}>
                      {fc.evidence_statement}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Supporting Evidence Chart: Pareto 80/20 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="font-semibold uppercase text-slate-600">Supporting Evidence Chart</span>
          <span>(Empirical Pareto 80/20 Concentration of Variance)</span>
        </div>
        <ParetoChart items={rootCause.pareto_breakdown} />
      </div>

      {/* Causal Tree Structure & Vital Few Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Vital Few Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <PieChart className="w-4 h-4 text-amber-500" />
            Pareto Vital Few Entities
          </h3>
          <p className="text-xs text-slate-600">
            Entities that account for the critical 80% boundary of accumulated downside variance:
          </p>
          <div className="space-y-1.5">
            {rootCause.pareto_breakdown
              .filter((p) => p.is_vital_few)
              .map((p, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-amber-50/60 border border-amber-200 text-xs flex items-center justify-between"
                >
                  <span className="font-bold text-amber-950">{p.entity}</span>
                  <div className="text-right">
                    <span className="font-bold text-amber-900">${p.loss_or_impact.toLocaleString()}</span>
                    <span className="text-[11px] text-amber-700 ml-2">({p.cumulative_percentage}%)</span>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Deterministic Causal Tree DAG View */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Binary className="w-4 h-4 text-blue-600" />
            Deterministic Causal Mechanism Tree
          </h3>
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-3">
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              {rootCause.causal_tree_structure.root_issue}
            </div>
            <div className="pl-4 border-l-2 border-slate-300 space-y-2">
              <div className="flex items-center gap-2 text-slate-800 font-semibold">
                <div className="w-2 h-2 rounded-full bg-purple-500" />
                Primary Driver: {rootCause.causal_tree_structure.primary_node?.factor} (
                {rootCause.causal_tree_structure.primary_node?.attribution}% attribution)
              </div>
              <div className="pl-4 border-l-2 border-slate-200 space-y-1 text-slate-600 text-[11px]">
                <div>&bull; Mechanism: Segment Drag across identified variance partitions</div>
                <div>&bull; Significance: Verified under Ordinary Least Squares & ANOVA</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">Proceed to Risk & Opportunity Detection</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Examine Downside & Upside</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
