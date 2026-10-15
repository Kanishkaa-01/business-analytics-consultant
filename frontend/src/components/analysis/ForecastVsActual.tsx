import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { TrendingUp, CheckCircle, AlertTriangle, Info, Calendar } from 'lucide-react';
import { api } from '../../services/api';
import { ForecastCompareResponse } from '../../types';

interface Props {
  analysisId: string;
}

export const ForecastVsActual: React.FC<Props> = ({ analysisId }) => {
  const [data, setData] = useState<ForecastCompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    setLoading(true);
    api.getForecastVsActual(analysisId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Failed to calculate forecast vs actual.'))
      .finally(() => setLoading(false));
  }, [analysisId]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500 text-white flex items-center justify-center shadow-xs">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm md:text-base">Forecast vs Actual Variance Analysis</h3>
          </div>
        </div>
        {data && (
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-200/80 text-slate-700">
            Model: {data.model_name}
          </span>
        )}
      </div>

      <div className="p-6 space-y-6">
        {loading && (
          <div className="py-12 flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-400 font-medium">Computing holdout forecast accuracy...</p>
          </div>
        )}

        {error && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {/* Accuracy Summary Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">FORECAST ERROR</span>
                <span className="text-xl font-black text-slate-900">
                  {data.accuracy_summary.mape ? `${data.accuracy_summary.mape}%` : 'N/A'}
                </span>
                <span className="text-[11px] text-slate-500 block mt-0.5">Average Forecast Error</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">WITHIN FORECAST RANGE</span>
                <span className="text-xl font-black text-emerald-600">
                  {data.accuracy_summary.within_ci_percentage !== undefined ? `${data.accuracy_summary.within_ci_percentage}%` : 'N/A'}
                </span>
                <span className="text-[11px] text-slate-500 block mt-0.5">Actual values within forecast range</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">FORECAST PERIOD</span>
                <span className="text-xl font-black text-slate-900">{data.horizon} Periods</span>
                <span className="text-[11px] text-slate-500 block mt-0.5">Periods Tested</span>
              </div>
            </div>

            {/* Chart */}
            {data.echarts_spec && Object.keys(data.echarts_spec).length > 0 && (
              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-200">
                <ReactECharts option={data.echarts_spec} style={{ height: 280 }} />
              </div>
            )}

{/* Comparison Table */}
{data.comparison && data.comparison.length > 0 && (
  <div className="overflow-x-auto rounded-xl border border-slate-200">
    <table className="w-full min-w-[760px] table-fixed text-xs">
      <colgroup>
        <col className="w-[14%]" />
        <col className="w-[18%]" />
        <col className="w-[18%]" />
        <col className="w-[16%]" />
        <col className="w-[14%]" />
        <col className="w-[20%]" />
      </colgroup>
      <thead className="bg-slate-100 text-slate-600 font-semibold uppercase tracking-wider">
        <tr>
          <th className="px-5 py-3 text-left whitespace-nowrap border-b border-slate-200">Period</th>
          <th className="px-3 py-3 text-center whitespace-nowrap border-b border-slate-200">Actual Realization</th>
          <th className="px-3 py-3 text-center whitespace-nowrap border-b border-slate-200">Forecasted Value</th>
          <th className="px-3 py-3 text-center whitespace-nowrap border-b border-slate-200">Variance ($)</th>
          <th className="px-3 py-3 text-center whitespace-nowrap border-b border-slate-200">Variance (%)</th>
          <th className="px-3 py-3 text-center whitespace-nowrap border-b border-slate-200">Inside Uncertainty Band</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 bg-white">
        {data.comparison.map((item, idx) => {
          const fmt = (n: number) =>
            Math.abs(n).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            });
          const sign = (n: number) => (n >= 0 ? '+' : '-');

          return (
            <tr key={idx} className="hover:bg-slate-50">
              <td className="px-5 py-3 text-left font-bold text-slate-900">{item.period}</td>
              <td className="px-3 py-3 text-center font-semibold text-slate-800 tabular-nums">
                ${fmt(item.actual)}
              </td>
              <td className="px-3 py-3 text-center text-slate-600 tabular-nums">
                ${fmt(item.forecast)}
              </td>
              <td className="px-3 py-3 text-center font-semibold tabular-nums">
                <span className={item.variance >= 0 ? 'text-emerald-600' : 'text-rose-600'}>
                  {sign(item.variance)}${fmt(item.variance)}
                </span>
              </td>
              <td className="px-3 py-3 text-center font-semibold tabular-nums">
                <span className={item.variance_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}>
                  {sign(item.variance_pct)}{Math.abs(item.variance_pct).toFixed(1)}%
                </span>
              </td>
              <td className="px-3 py-3 text-center">
                {item.in_confidence_interval ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle className="w-3 h-3" /> Yes
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200">
                    <AlertTriangle className="w-3 h-3" /> Outside
                  </span>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
)}

            {/* Insights */}
            {data.insights && data.insights.length > 0 && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-blue-500" />
                  Forecasting Validation Insights
                </span>
                <ul className="text-xs text-slate-600 space-y-1">
                  {data.insights.map((ins, iIdx) => (
                    <li key={iIdx} className="flex items-start gap-2">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>{ins}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
