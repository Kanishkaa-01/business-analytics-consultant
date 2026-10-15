import React from 'react';
import {
  Split,
  ArrowDownRight,
  ArrowUpRight,
  AlertOctagon,
  ArrowRight,
  TrendingDown,
  Layers,
  Scale
} from 'lucide-react';
import { DiagnosticReport } from '../../types';
import { VarianceChart } from '../charts/VarianceChart';

interface Props {
  diagnostic: DiagnosticReport;
  onNavigateNext: () => void;
}

export const Stage3_Diagnostics: React.FC<Props> = ({ diagnostic, onNavigateNext }) => {
  const isNetNegative = diagnostic.total_variance < 0;

  return (
    <div className="space-y-6">
      {/* Research Question Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Split className="w-3.5 h-3.5" />
            Core Question 2: Why is it happening? (Diagnostic Decomposition)
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Multidimensional Variance Decomposition
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            {diagnostic.diagnostic_narrative}
          </p>
        </div>

        {/* Total Variance Pill */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">
            Total Net Variance ({diagnostic.focal_metric})
          </div>
          <div
            className={`text-2xl font-black mt-1 ${
              isNetNegative ? 'text-rose-600' : 'text-emerald-600'
            }`}
          >
            {diagnostic.total_variance > 0 ? '+' : ''}
            {diagnostic.total_variance.toLocaleString()}
            <span className="text-sm font-semibold ml-1">
              ({diagnostic.variance_pct > 0 ? '+' : ''}{diagnostic.variance_pct}%)
            </span>
          </div>
        </div>
      </div>

      {/* Supporting Evidence Chart */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span className="font-semibold uppercase text-slate-600">Supporting Evidence Chart</span>
          <span>(Positive and Negative Changes Quantification)</span>
        </div>
        <VarianceChart
          items={diagnostic.variance_breakdown}
          metricName={diagnostic.focal_metric}
        />
      </div>

      {/* Variance Breakdown Table */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            Segment Comparison Breakdown
          </h3>
          <span className="text-xs text-slate-500">
            Decomposed across {diagnostic.segment_diagnostics.length} analytical dimensions
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Dimension</th>
                <th className="py-2.5 px-3">Segment</th>
                <th className="py-2.5 px-3">Baseline</th>
                <th className="py-2.5 px-3">Actual</th>
                <th className="py-2.5 px-3">Variance</th>
                <th className="py-2.5 px-3">Shift %</th>
                <th className="py-2.5 px-3">Contribution Share</th>
                <th className="py-2.5 px-3">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {diagnostic.variance_breakdown.map((item, idx) => {
                const isDrag = item.direction === 'Drag';
                return (
                  <tr key={idx} className="hover:bg-slate-50/70">
                    <td className="py-2 px-3 font-semibold text-slate-800">{item.dimension}</td>
                    <td className="py-2 px-3 font-bold text-slate-900">{item.segment}</td>
                    <td className="py-2 px-3 text-slate-600">${item.baseline_value.toLocaleString()}</td>
                    <td className="py-2 px-3 text-slate-900">${item.actual_value.toLocaleString()}</td>
                    <td
                      className={`py-2 px-3 font-bold ${
                        isDrag ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {item.variance > 0 ? '+' : ''}${item.variance.toLocaleString()}
                    </td>
                    <td
                      className={`py-2 px-3 font-semibold ${
                        item.variance_pct < 0 ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {item.variance_pct > 0 ? '+' : ''}{item.variance_pct}%
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-700">
                      {item.contribution_share_pct}%
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          isDrag
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {isDrag ? (
                          <ArrowDownRight className="w-3 h-3 text-rose-600" />
                        ) : (
                          <ArrowUpRight className="w-3 h-3 text-emerald-600" />
                        )}
                        {item.direction}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Segment Dispersion & Anomaly Alerts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dispersion summary */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Scale className="w-4 h-4 text-indigo-600" />
            Dimension Dispersion Metrics (Inequality)
          </h3>
          <div className="space-y-2">
            {diagnostic.segment_diagnostics.map((seg, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs flex items-center justify-between"
              >
                <div>
                  <div className="font-bold text-slate-800">{seg.dimension}</div>
                  <div className="text-[11px] text-slate-500">
                    {seg.underperforming_segments.length} underperforming &bull;{' '}
                    {seg.overperforming_segments.length} overperforming
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-slate-900">
                    CV: {seg.dispersion_gini_or_cv}
                  </div>
                  <div className="text-[10px] text-slate-500">Coeff. of Variation</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Anomaly Alerts */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-600" />
            Isolated Outlier & Extreme Drawdown Events
          </h3>
          {diagnostic.anomalies_detected.length === 0 ? (
            <div className="p-3 bg-slate-50 text-slate-600 text-xs rounded-lg border border-slate-200">
              No extreme 2.5x IQR outliers detected. Variance is systemic rather than single-event driven.
            </div>
          ) : (
            <div className="space-y-2">
              {diagnostic.anomalies_detected.map((anom, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-rose-50/50 border border-rose-200 text-xs space-y-1"
                >
                  <div className="font-bold text-rose-900">{anom.type}</div>
                  <p className="text-rose-800">{anom.description}</p>
                  {anom.focal_record_info && (
                    <div className="text-[11px] font-mono text-rose-700 bg-white/80 p-1.5 rounded border border-rose-200">
                      Sample Context: {JSON.stringify(anom.focal_record_info)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">Proceed to Root Cause Statistical Factor Attribution</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Examine Statistical Proof</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
