import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  TrendingUp,
  AlertCircle,
  HelpCircle,
  Layers,
  CheckCircle,
  Activity,
  Sliders,
  ShieldAlert,
  Loader2
} from 'lucide-react';
import { ForecastReport, ForecastModelResult } from '../../types';
import { api } from '../../services/api';

interface Props {
  analysisId?: string;
}

export const ForecastingSection: React.FC<Props> = ({ analysisId }) => {
  const [report, setReport] = useState<ForecastReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState<number>(3);
  const [selectedModelType, setSelectedModelType] = useState<string>('linear');

  const fetchForecast = async (horizon: number) => {
    if (!analysisId) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await api.getForecast(analysisId, { horizon });
      setReport(data);
      if (data.recommended_model) {
        setSelectedModelType(data.recommended_model);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to compute forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (analysisId) {
      fetchForecast(selectedHorizon);
    }
  }, [analysisId, selectedHorizon]);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 flex items-center justify-center gap-3 text-slate-500 text-sm">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span>Evaluating time series and computing deterministic forecast models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-xs text-rose-800 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
        <div>
          <div className="font-bold">Forecasting calculation error</div>
          <div className="mt-1">{error}</div>
        </div>
      </div>
    );
  }

  // Graceful Fallback if dataset is unsuitable for forecasting
  if (!report || !report.is_available) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-3">
        <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
          <HelpCircle className="w-4 h-4 text-slate-500" />
          <span>Forecasting Not Available for this Dataset</span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {report?.reason ||
            'Forecasting requires a parseable date/time column and at least 6 historical observations to construct reliable models.'}
        </p>
        <div className="text-[11px] text-slate-500 italic bg-white p-3 rounded-xl border border-slate-200">
          Tip: Upload a dataset containing periodic time observations (e.g. monthly sales, quarterly revenue) to enable automated trend extrapolation.
        </div>
      </div>
    );
  }

  const activeModel =
    report.models.find((m) => m.model_type === selectedModelType) ||
    report.models.find((m) => m.is_recommended) ||
    report.models[0];

  // Prepare Apache ECharts Options
  const histPeriods = report.historical_series.map((h) => h.period);
  const histValues = report.historical_series.map((h) => h.value);

  const forecastPeriods = activeModel ? activeModel.forecast_points.map((f) => f.period) : [];
  const forecastValues = activeModel ? activeModel.forecast_points.map((f) => f.value) : [];
  const lowerBounds = activeModel ? activeModel.forecast_points.map((f) => f.lower_bound) : [];
  const upperBounds = activeModel ? activeModel.forecast_points.map((f) => f.upper_bound) : [];

  const allCategories = [...histPeriods, ...forecastPeriods];

  // Series alignment: historical series has nulls during forecast periods
  const historicalDataAligned = [...histValues, ...forecastPeriods.map(() => null)];

  // Forecast line connects to the last historical point
  const lastHistVal = histValues.length > 0 ? histValues[histValues.length - 1] : null;
  const forecastDataAligned = [
    ...histPeriods.slice(0, -1).map(() => null),
    lastHistVal,
    ...forecastValues,
  ];

  // Confidence band lower base & spread
  const bandLowerAligned = [
    ...histPeriods.slice(0, -1).map(() => null),
    lastHistVal,
    ...lowerBounds,
  ];
  const bandSpreadAligned = [
    ...histPeriods.slice(0, -1).map(() => null),
    0,
    ...upperBounds.map((u, i) => Math.max(0, u - lowerBounds[i])),
  ];

  const chartOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0F172A',
      borderColor: '#334155',
      textStyle: { color: '#F8FAFC', fontSize: 12 },
      formatter: (params: any) => {
        let content = `<div style="font-weight:bold; margin-bottom:4px;">Period: ${params[0]?.axisValue}</div>`;
        params.forEach((item: any) => {
          if (item.value !== null && item.value !== undefined && item.seriesName !== 'Band Base') {
            const valStr = typeof item.value === 'number' ? `$${item.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : item.value;
            content += `<div style="display:flex; justify-content:space-between; gap:12px;"><span>${item.marker} ${item.seriesName}:</span> <b>${valStr}</b></div>`;
          }
        });
        return content;
      },
    },
    legend: {
      data: ['Historical Observation', 'Model Forecast', 'Confidence Interval (95%)'],
      top: 0,
      textStyle: { color: '#475569', fontSize: 11 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: allCategories,
      axisLine: { lineStyle: { color: '#CBD5E1' } },
      axisLabel: { color: '#64748B', fontSize: 11, rotate: allCategories.length > 12 ? 30 : 0 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#CBD5E1' } },
      splitLine: { lineStyle: { color: '#F1F5F9' } },
      axisLabel: {
        color: '#64748B',
        fontSize: 11,
        formatter: (val: number) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`,
      },
    },
    series: [
      {
        name: 'Historical Observation',
        type: 'line',
        data: historicalDataAligned,
        itemStyle: { color: '#2563EB' },
        lineStyle: { width: 2.5 },
        symbol: 'circle',
        symbolSize: 6,
      },
      {
        name: 'Model Forecast',
        type: 'line',
        data: forecastDataAligned,
        itemStyle: { color: '#7C3AED' },
        lineStyle: { width: 2.5, type: 'dashed' },
        symbol: 'diamond',
        symbolSize: 7,
      },
      // Lower base of confidence band (transparent)
      {
        name: 'Band Base',
        type: 'line',
        data: bandLowerAligned,
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none',
      },
      // Shaded spread of confidence band
      {
        name: 'Confidence Interval (95%)',
        type: 'line',
        data: bandSpreadAligned,
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(124, 58, 237, 0.15)' },
        stack: 'confidence-band',
        symbol: 'none',
      },
    ],
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div className="space-y-1">
          <h3 className="text-lg font-bold text-slate-900">
            Time-Series Projection & Model Comparison
          </h3>
          <p className="text-xs text-slate-600">
            Evaluating historical {report.frequency} patterns for <b>{report.metric_name}</b> using deterministic mathematical formulations.
          </p>
        </div>

        {/* Horizon selector buttons */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Forecast Horizon:</span>
          {[3, 6, 12].map((hz) => (
            <button
              key={hz}
              onClick={() => setSelectedHorizon(hz)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                selectedHorizon === hz
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              +{hz} Periods
            </button>
          ))}
        </div>
      </div>

      {/* Model Selection Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {report.models.map((m) => {
          const isSelected = m.model_type === (activeModel?.model_type || '');
          return (
            <button
              key={m.model_type}
              onClick={() => setSelectedModelType(m.model_type)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border ${
                isSelected
                  ? 'bg-indigo-50 text-indigo-900 border-indigo-300 ring-2 ring-indigo-500/20 shadow-xs'
                  : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
              }`}
            >
              <span>{m.model_name}</span>
              {m.is_recommended && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Best Fit
                </span>
              )}
              <span className="text-[11px] text-slate-500 font-normal">
                (MAPE: {m.validation_metrics.mape.toFixed(1)}%)
              </span>
            </button>
          );
        })}
      </div>

      {/* Main ECharts Visualization */}
      <div className="bg-slate-50/60 rounded-xl p-4 border border-slate-100">
        <ReactECharts option={chartOption} style={{ height: 340, width: '100%' }} />
      </div>

      {/* Validation Metrics & Parameters Cards */}
      {activeModel && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Holdout MAPE</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">
              {activeModel.validation_metrics.mape.toFixed(2)}%
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Mean Absolute % Error</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Holdout MAE</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">
              ${activeModel.validation_metrics.mae.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Mean Absolute Error ($)</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Holdout RMSE</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">
              ${activeModel.validation_metrics.rmse.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Root Mean Squared Error</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Model Parameters</div>
            <div className="text-xs font-semibold text-slate-800 mt-1 line-clamp-2">
              {Object.entries(activeModel.parameters)
                .map(([k, v]) => `${k.replace('_', ' ')}: ${v}`)
                .join(', ')}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Deterministic weights</div>
          </div>
        </div>
      )}

      {/* Trajectory Narrative */}
      {report.trajectory_narrative && (
        <div className="p-4 bg-indigo-50/70 rounded-xl border border-indigo-200 text-xs text-indigo-950 flex items-start gap-3">
          <Activity className="w-4 h-4 text-indigo-700 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-indigo-900">Projected Trajectory:</div>
            <p className="leading-relaxed">{report.trajectory_narrative}</p>
          </div>
        </div>
      )}

      {/* Methodological Transparency & Non-causal Disclaimer */}
      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-600 text-[11px] flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <b>Methodological Disclaimer:</b> {report.disclaimer} All projections extrapolate past empirical observations and assume stability in underlying business drivers.
        </p>
      </div>
    </div>
  );
};
