import React, { useState, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  BarChart3,
  TrendingUp,
  PieChart as PieIcon,
  ScatterChart as ScatterIcon,
  Table as TableIcon,
  ChevronDown,
  Info,
  Check
} from 'lucide-react';
import {
  SupportedChartType,
  DataPoint,
  analyzeChartCompatibility,
  buildEChartsOption,
} from '../../utils/visualizationCompatibility';

interface Props {
  data: DataPoint[];
  title?: string;
  metricName?: string;
  hints?: {
    isTimeSeries?: boolean;
    isCategorical?: boolean;
    isBivariate?: boolean;
  };
  height?: number;
  showExplanation?: boolean;
  className?: string;
}

export const AdaptiveVisualization: React.FC<Props> = ({
  data,
  title,
  metricName = 'Value',
  hints,
  height = 280,
  showExplanation = true,
  className = '',
}) => {
  const analysis = useMemo(() => {
    return analyzeChartCompatibility(data, {
      ...hints,
      metricName,
    });
  }, [data, hints, metricName]);

  const [currentType, setCurrentType] = useState<SupportedChartType>(analysis.recommendedType);

  // If the dataset changes and currentType is no longer allowed, reset to recommended
  useMemo(() => {
    if (!analysis.allowedTypes.includes(currentType)) {
      setCurrentType(analysis.recommendedType);
    }
  }, [analysis, currentType]);

  const chartOption = useMemo(() => {
    if (currentType === 'table') return null;
    return buildEChartsOption(data, currentType, undefined, metricName);
  }, [data, currentType, metricName]);

  const getIconForType = (type: SupportedChartType) => {
    switch (type) {
      case 'line':
        return <TrendingUp className="w-3.5 h-3.5 text-blue-600" />;
      case 'horizontal_bar':
      case 'bar':
        return <BarChart3 className="w-3.5 h-3.5 text-indigo-600" />;
      case 'pie':
        return <PieIcon className="w-3.5 h-3.5 text-amber-600" />;
      case 'scatter':
        return <ScatterIcon className="w-3.5 h-3.5 text-purple-600" />;
      case 'table':
        return <TableIcon className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Top Controls: Recommendation Badge + View As Dropdown */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          {title && <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">{title}</span>}
          {showExplanation && (
            <span
              className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded"
              title={analysis.recommendationReason}
            >
              <Info className="w-3 h-3 text-slate-400" />
              <span>Recommended: {analysis.options.find((o) => o.isRecommended)?.label}</span>
            </span>
          )}
        </div>

        {/* View As Selector Dropdown */}
        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <span className="text-xs font-medium text-slate-500">View as:</span>
          <div className="relative inline-block text-left">
            <select
              value={currentType}
              onChange={(e) => setCurrentType(e.target.value as SupportedChartType)}
              className="appearance-none pl-3 pr-7 py-1 bg-white border border-slate-300 hover:border-slate-400 rounded-lg text-xs font-semibold text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
            >
              {analysis.options.map((opt) => (
                <option
                  key={opt.type}
                  value={opt.type}
                  disabled={opt.disabled}
                >
                  {opt.label} {opt.isRecommended ? '★ (Recommended)' : ''} {opt.disabled ? `(${opt.disabledReason})` : ''}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2 top-2 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Explanatory Note for current view vs recommendation */}
      {showExplanation && (
        <div className="text-[11px] text-slate-500 flex items-start gap-1.5 bg-slate-50/80 p-2 rounded-lg border border-slate-100">
          <Info className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
          <span>
            {currentType === analysis.recommendedType
              ? analysis.recommendationReason
              : `Alternative view selected (${analysis.options.find((o) => o.type === currentType)?.label}). Default recommendation was ${analysis.options.find((o) => o.isRecommended)?.label}.`}
          </span>
        </div>
      )}

      {/* Visualization Canvas */}
      {currentType === 'table' ? (
        <div className="overflow-x-auto rounded-xl border border-slate-200" style={{ maxHeight: height }}>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider sticky top-0 border-b border-slate-200">
              <tr>
                <th className="px-3 py-2">Item / Dimension</th>
                <th className="px-3 py-2 text-right">{metricName}</th>
                {data.some((d) => d.secondaryValue !== undefined) && (
                  <th className="px-3 py-2 text-right">Secondary Value</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data.map((d, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="px-3 py-2 font-medium text-slate-800">{d.label}</td>
                  <td className="px-3 py-2 font-bold text-slate-900 text-right">
                    {typeof d.value === 'number' ? d.value.toLocaleString() : d.value}
                  </td>
                  {data.some((row) => row.secondaryValue !== undefined) && (
                    <td className="px-3 py-2 text-slate-600 text-right">
                      {d.secondaryValue !== undefined ? d.secondaryValue.toLocaleString() : '-'}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        chartOption && <ReactECharts option={chartOption} style={{ height, width: '100%' }} />
      )}
    </div>
  );
};
