import React from "react";
import { AlertCircle, Sigma, ArrowRight, ShieldCheck } from "lucide-react";
import { RootCauseReport, FactorContribution } from "../../types";
import { ParetoChart } from "../charts/ParetoChart";
import { TermTooltip } from "../common/TermTooltip";

export function getSupportingEvidence(fc: FactorContribution): string {
  const pVal =
    typeof fc.statistical_significance_p_value === "number"
      ? fc.statistical_significance_p_value
      : 0.05;
  const coef =
    typeof fc.correlation_or_coef === "number" ? fc.correlation_or_coef : 0;
  const absCoef = Math.abs(coef);
  const attrib =
    typeof fc.attribution_percentage === "number"
      ? fc.attribution_percentage
      : 0;
  const isNegative =
    coef < 0 ||
    Boolean(fc.direction && fc.direction.toLowerCase().includes("negative"));

  // If statistical significance indicates no reliable association
  if (pVal >= 0.1 || (pVal >= 0.05 && absCoef < 0.15 && attrib < 5)) {
    return "No clear association with the observed pattern.";
  }

  // Determine association strength based on correlation magnitude or attribution share
  let strength: "Strong" | "Moderate" | "Weak" = "Weak";
  if (absCoef >= 0.5 || attrib >= 20) {
    strength = "Strong";
  } else if (absCoef >= 0.25 || attrib >= 10) {
    strength = "Moderate";
  }

  if (isNegative) {
    if (strength === "Weak") {
      return "Negative association with the observed pattern.";
    }
    return `${strength} negative association with the observed pattern.`;
  }

  return `${strength} positive association with the observed pattern.`;
}

interface Props {
  rootCause: RootCauseReport;
  onNavigateNext: () => void;
}

export const PossibleReasons: React.FC<Props> = ({
  rootCause,
  onNavigateNext,
}) => {
  const disclaimer =
    rootCause.causation_disclaimer ||
    "Note: An observed relationship does not necessarily prove causation.";

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Contributing Factors & Associated Patterns
          </h2>

          <p className="text-sm font-semibold text-white leading-relaxed">
            {rootCause.primary_root_cause}
          </p>

          {rootCause.possible_reasons_summary && (
            <p className="text-xs text-slate-300 leading-relaxed">
              {rootCause.possible_reasons_summary}
            </p>
          )}
        </div>
      </div>

      {/* Prominent Causation Disclaimer Alert */}
      <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-xl flex items-center gap-3 text-xs text-amber-900 shadow-2xs">
        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
        <span className="font-semibold">
          {disclaimer} Factors shown below represent observed statistical
          associations and contributing patterns in the data.
        </span>
      </div>

      {/* Factors Associated with Observed Patterns */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Sigma className="w-4 h-4 text-purple-600" />
            Factors Associated with Observed Patterns
          </h3>
          <span className="text-xs text-slate-500">
            Statistical association and contribution share
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Contributing Factor</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">
                  <TermTooltip termKey="contribution" label="Contribution %" />
                </th>
                <th className="py-2.5 px-3">Supporting Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rootCause.factor_contributions.map((fc, idx) => (
                <tr key={idx} className="hover:bg-slate-50/70">
                  <td className="py-2.5 px-3 font-bold text-slate-900">
                    {fc.factor_name}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                      {fc.factor_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2">
                      <div className="w-14 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-purple-600 h-1.5 rounded-full"
                          style={{
                            width: `${Math.min(100, Math.max(0, fc.attribution_percentage))}%`,
                          }}
                        />
                      </div>
                      <span className="font-bold text-slate-900">
                        {fc.attribution_percentage}%
                      </span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 leading-relaxed">
                    {getSupportingEvidence(fc)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Disclaimer below the table */}
        <div className="flex items-center gap-2 pt-1 text-xs text-slate-500 italic">
          <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span>{disclaimer}</span>
        </div>
      </div>

      {/* Focus on Biggest Contributors (was Pareto) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="font-semibold uppercase text-slate-600">
            Focus on Biggest Contributors
          </span>
          <span>
            (Identifies which areas account for the majority of the difference)
          </span>
        </div>
        <ParetoChart items={rootCause.pareto_breakdown} />
      </div>

{/* Contributors Table */}
{rootCause.pareto_breakdown && rootCause.pareto_breakdown.length > 0 && (
  <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
      Biggest Contributors Breakdown
    </h3>
    <div className="overflow-x-auto border border-slate-200 rounded-lg">
      <table className="w-full min-w-[640px] table-fixed text-xs text-slate-700">
        <colgroup>
          <col className="w-[28%]" />
          <col className="w-[18%]" />
          <col className="w-[18%]" />
          <col className="w-[18%]" />
          <col className="w-[18%]" />
        </colgroup>
        <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
          <tr>
            <th className="py-3 px-5 text-left whitespace-nowrap">Entity / Segment</th>
            <th className="py-3 px-2 text-center whitespace-nowrap">Impact ($)</th>
            <th className="py-3 px-2 text-center whitespace-nowrap">Contribution %</th>
            <th className="py-3 px-2 text-center whitespace-nowrap">Cumulative Share %</th>
            <th className="py-3 px-2 text-center whitespace-nowrap">Focus Area</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rootCause.pareto_breakdown.map((item, idx) => (
            <tr key={idx} className="hover:bg-slate-50/70">
              <td className="py-3 px-5 text-left font-bold text-slate-900 truncate">
                {item.entity}
              </td>
              <td className="py-3 px-2 text-center font-semibold text-rose-600 tabular-nums">
                ${Math.abs(item.loss_or_impact).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </td>
              <td className="py-3 px-2 text-center font-semibold text-slate-800 tabular-nums">
                {item.contribution_percentage !== undefined
                  ? `${item.contribution_percentage.toFixed(1)}%`
                  : '-'}
              </td>
              <td className="py-3 px-2 text-center font-semibold text-slate-800 tabular-nums">
                {item.cumulative_percentage.toFixed(1)}%
              </td>
              <td className="py-3 px-2 text-center">
                {item.is_vital_few ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                    High Focus
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[10px] font-semibold bg-slate-50 text-slate-500 border border-slate-200">
                    Normal
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
)}
      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">
            Next Stage
          </div>
          <div className="text-sm font-semibold">
            Review Prioritized Recommended Actions
          </div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>View Recommendations</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export { PossibleReasons as Stage4_PossibleReasons };

