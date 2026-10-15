import React from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  ArrowRight
} from 'lucide-react';
import { BusinessHealthOverview } from '../../types';
import { TimelineChart } from '../charts/TimelineChart';

interface Props {
  health: BusinessHealthOverview;
  onNavigateNext: () => void;
}

export const Stage2_BusinessHealth: React.FC<Props> = ({ health, onNavigateNext }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Strong':
        return 'text-emerald-700 bg-emerald-50 border-emerald-300';
      case 'Stable':
        return 'text-blue-700 bg-blue-50 border-blue-300';
      case 'Vulnerable':
        return 'text-amber-700 bg-amber-50 border-amber-300';
      default:
        return 'text-rose-700 bg-rose-50 border-rose-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Research Question Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Activity className="w-3.5 h-3.5" />
            Core Question 1: What is happening?
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Business Health & Operational Vital Signs
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            {health.executive_summary}
          </p>
        </div>

        {/* Executive Health Score Badge */}
        <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0">
          <div className="text-right">
            <div className="text-xs uppercase font-bold text-slate-500">Health Index</div>
            <div className="text-3xl font-extrabold text-slate-900">
              {health.overall_health_score}<span className="text-lg font-normal text-slate-500">/100</span>
            </div>
          </div>
          <div
            className={`px-3 py-2 rounded-xl border text-sm font-bold shadow-inner ${getStatusColor(
              health.overall_status
            )}`}
          >
            {health.overall_status}
          </div>
        </div>
      </div>

      {/* KPI Performance Scorecards */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          Key Performance Indicators & Baseline Trajectory
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {health.kpis.map((kpi, idx) => {
            const isNegative = kpi.trend === 'deteriorating';
            return (
              <div
                key={idx}
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-700 line-clamp-1">{kpi.name}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        kpi.status === 'healthy'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : kpi.status === 'warning'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {kpi.status}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-extrabold text-slate-900">
                      {kpi.unit === '$' && '$'}
                      {kpi.current_value.toLocaleString()}
                      {kpi.unit !== '$' && ` ${kpi.unit}`}
                    </span>
                    {kpi.variance_pct !== null && kpi.variance_pct !== undefined && (
                      <span
                        className={`inline-flex items-center gap-0.5 text-xs font-bold ${
                          isNegative ? 'text-rose-600' : 'text-emerald-600'
                        }`}
                      >
                        {isNegative ? (
                          <TrendingDown className="w-3.5 h-3.5" />
                        ) : (
                          <TrendingUp className="w-3.5 h-3.5" />
                        )}
                        {kpi.variance_pct > 0 ? `+${kpi.variance_pct}%` : `${kpi.variance_pct}%`}
                      </span>
                    )}
                  </div>
                  {kpi.target_or_baseline !== null && kpi.target_or_baseline !== undefined && (
                    <div className="text-[11px] text-slate-500 mt-1">
                      Baseline: {kpi.unit === '$' ? '$' : ''}{kpi.target_or_baseline.toLocaleString()}
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-100 text-xs text-slate-600 leading-snug">
                  {kpi.interpretation}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Supporting Evidence Chart (Timeline progression if available) */}
      {health.timeline_series && health.timeline_series.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-semibold uppercase text-slate-600">Supporting Evidence Chart</span>
            <span>(Charts serve as empirical proof, not the primary product)</span>
          </div>
          <TimelineChart
            data={health.timeline_series}
            metricName={health.vital_signs.primary_metric || 'Focal Metric'}
          />
        </div>
      )}

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Analytical Phase</div>
          <div className="text-sm font-semibold">Proceed to Diagnostic Variance Decomposition</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>Examine Segment Comparison</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
