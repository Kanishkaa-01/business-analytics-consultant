import React from 'react';
import { ChartSpecification } from '../../types';
import { AlertCircle, Activity } from 'lucide-react';
import { AdaptiveVisualization } from './AdaptiveVisualization';
import { DataPoint } from '../../utils/visualizationCompatibility';

interface Props {
  spec?: ChartSpecification | null;
  loading?: boolean;
}

export const AutoVisualization: React.FC<Props> = ({ spec, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs flex items-center justify-center min-h-[260px]">
        <div className="flex items-center gap-2.5 text-xs text-slate-500 font-medium">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span>Generating automatic visualization...</span>
        </div>
      </div>
    );
  }

  if (!spec || !spec.available || spec.chart_type === 'none') {
    return (
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs flex flex-col items-center justify-center min-h-[220px] text-center space-y-2">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="text-sm font-semibold text-slate-700">
          Visualization not available for this analysis.
        </div>
        <div className="text-xs text-slate-500 max-w-md">
          {spec?.empty_reason || 'The dataset structure or selected parameters could not be automatically mapped to a chart.'}
        </div>
      </div>
    );
  }

  // Single KPI Display
  if (spec.chart_type === 'kpi') {
    return (
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          <Activity className="w-4 h-4 text-blue-600" />
          <span>{spec.title}</span>
        </div>
        <div className="text-3xl font-black text-slate-900">
          ${(spec.kpi_value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div className="text-xs text-slate-500 mt-1">
          {spec.description}
        </div>
      </div>
    );
  }

  // Convert spec data to DataPoints
  const points: DataPoint[] = (spec.data || []).map((d: any) => ({
    label: String(
      d.category ||
      d.period ||
      d.name ||
      (spec.x_axis_field ? d[spec.x_axis_field] : '') ||
      d.x ||
      ''
    ),
    value: Number(
      d.value ??
      (spec.y_axis_field ? d[spec.y_axis_field] : null) ??
      d.y ??
      0
    ),
    secondaryValue: d.y !== undefined && d.x !== undefined ? Number(d.y) : undefined,
    raw: d,
  }));

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
      <AdaptiveVisualization
        data={points}
        title={spec.title}
        metricName={spec.series_name || 'Amount'}
        hints={{
          isTimeSeries: spec.chart_type === 'line',
          isBivariate: spec.chart_type === 'scatter',
        }}
        height={280}
      />
    </div>
  );
};
