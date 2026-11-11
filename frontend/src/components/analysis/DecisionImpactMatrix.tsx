import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { Compass, Zap, Flame, CheckSquare, RefreshCw, HelpCircle } from 'lucide-react';
import { api } from '../../services/api';
import { DecisionImpactMatrixResponse } from '../../types';

interface Props {
  analysisId: string;
  onOpenExplanation?: (recId: string) => void;
}

export const DecisionImpactMatrix: React.FC<Props> = ({ analysisId, onOpenExplanation }) => {
  const [data, setData] = useState<DecisionImpactMatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    setLoading(true);
    api.getDecisionImpactMatrix(analysisId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Failed to load impact matrix.'))
      .finally(() => setLoading(false));
  }, [analysisId]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm md:text-base">Decision Impact Matrix</h3>
            <p className="text-xs text-slate-500">Portfolio prioritization: Implementation Effort vs Expected Business Impact</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {loading && (
          <div className="py-12 flex justify-center text-xs text-slate-400 font-medium">
            Mapping recommendations to quadrant coordinates...
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {/* Executive Synthesis */}
            <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-100 text-emerald-900 text-xs leading-relaxed font-medium">
              {data.executive_summary}
            </div>

            {/* Quadrant Count Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/40 text-emerald-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  <Zap className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Quick Wins</span>
                </div>
                <div className="text-2xl font-black">{data.quadrant_counts['Quick Wins'] || 0}</div>
                <div className="text-[10px] text-emerald-700">Low Effort, High Impact</div>
              </div>

              <div className="p-3.5 rounded-xl border border-blue-200 bg-blue-50/40 text-blue-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  <Flame className="w-3.5 h-3.5 text-blue-600" />
                  <span>Strategic Bets</span>
                </div>
                <div className="text-2xl font-black">{data.quadrant_counts['Strategic Bets'] || 0}</div>
                <div className="text-[10px] text-blue-700">High Effort, High Impact</div>
              </div>

              <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/40 text-amber-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  <CheckSquare className="w-3.5 h-3.5 text-amber-600" />
                  <span>Fill-ins</span>
                </div>
                <div className="text-2xl font-black">{data.quadrant_counts['Fill-ins'] || 0}</div>
                <div className="text-[10px] text-amber-700">Low Effort, Low Impact</div>
              </div>

              <div className="p-3.5 rounded-xl border border-rose-200 bg-rose-50/40 text-rose-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-xs">
                  <RefreshCw className="w-3.5 h-3.5 text-rose-600" />
                  <span>Re-evaluate</span>
                </div>
                <div className="text-2xl font-black">{data.quadrant_counts['Re-evaluate'] || 0}</div>
                <div className="text-[10px] text-rose-700">High Effort, Low Impact</div>
              </div>
            </div>

            {/* Apache ECharts 2D Scatter Matrix */}
            {data.echarts_spec && Object.keys(data.echarts_spec).length > 0 && (
              <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-200">
                <ReactECharts option={data.echarts_spec} style={{ height: 320 }} />
              </div>
            )}

            {/* Table of Items */}
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-2.5 border-b border-slate-200">Action Title</th>
                    <th className="px-4 py-2.5 border-b border-slate-200">Quadrant</th>
                    <th className="px-4 py-2.5 border-b border-slate-200">Effort (1-10)</th>
                    <th className="px-4 py-2.5 border-b border-slate-200">Impact Score (1-10)</th>
                    <th className="px-4 py-2.5 border-b border-slate-200">Expected Upside</th>
                    <th className="px-4 py-2.5 border-b border-slate-200">Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {data.items.map((item, idx) => {
                    const qBadge =
                      item.quadrant === 'Quick Wins'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : item.quadrant === 'Strategic Bets'
                        ? 'bg-blue-50 text-blue-700 border-blue-200'
                        : item.quadrant === 'Fill-ins'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-rose-50 text-rose-700 border-rose-200';

                    return (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-bold text-slate-900">{item.action_title}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${qBadge}`}>
                            {item.quadrant}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-slate-600">
                          {item.implementation_effort} ({item.effort_score})
                        </td>
                        <td className="px-4 py-2.5 font-bold text-slate-800">{item.impact_score} / 10</td>
                        <td className="px-4 py-2.5 font-semibold text-emerald-700">
                          ${item.expected_impact_dollars.toLocaleString()}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 max-w-xs truncate">
                          {item.supporting_finding}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
