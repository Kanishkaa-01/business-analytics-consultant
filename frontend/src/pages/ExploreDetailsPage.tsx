import React, { useState, useEffect } from 'react';
import {
  Layers,
  ArrowLeft,
  ChevronRight,
  Filter,
  AlertCircle,
  RotateCcw,
  MousePointerClick,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { api } from '../services/api';
import { DrillDownResponse } from '../types';
import { AdaptiveVisualization } from '../components/charts/AdaptiveVisualization';
import { DataPoint } from '../utils/visualizationCompatibility';

interface Props {
  analysisId?: string;
  datasetName?: string;
  targetMetric?: string;
  availableDimensions?: string[];
  initialDimension?: string;
  onBackToWorkspace: () => void;
}

const prettify = (key: string): string => {
  const spaced = (key || '').replace(/_/g, ' ').trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
};

export const ExploreDetailsPage: React.FC<Props> = ({
  analysisId,
  datasetName,
  targetMetric = 'Target Metric',
  availableDimensions = [],
  initialDimension,
  onBackToWorkspace,
}) => {
  const [selectedDimension, setSelectedDimension] = useState<string>(
    initialDimension || availableDimensions[0] || 'dimension'
  );
  const [parentFilters, setParentFilters] = useState<Record<string, any>>({});
  const [data, setData] = useState<DrillDownResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDrillDown = async (dim: string, filters: Record<string, any>) => {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.drillDown(analysisId, {
        dimension: dim,
        metric: targetMetric,
        aggregation: 'sum',
        parent_filters: filters,
        limit: 12,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to aggregate detailed breakdown.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!analysisId) return;
    const defaultDim = initialDimension || availableDimensions[0] || 'dimension';
    setSelectedDimension(defaultDim);
    setParentFilters({});
    fetchDrillDown(defaultDim, {});
  }, [analysisId, initialDimension]);

  const handleSegmentClick = (segmentVal: string) => {
    if (!data?.next_suggested_dimensions || data.next_suggested_dimensions.length === 0) return;
    const nextDim = data.next_suggested_dimensions[0];
    const newFilters = { ...parentFilters, [selectedDimension]: segmentVal };
    setParentFilters(newFilters);
    setSelectedDimension(nextDim);
    fetchDrillDown(nextDim, newFilters);
  };

  const handleResetFilters = () => {
    setParentFilters({});
    const baseDim = availableDimensions[0] || 'dimension';
    setSelectedDimension(baseDim);
    fetchDrillDown(baseDim, {});
  };

  const chartPoints: DataPoint[] = (data?.segments || []).map((seg) => ({
    label: seg.dimension_value,
    value: seg.metric_value,
    secondaryValue: seg.record_count,
  }));

  const allDimensionOptions = [
    selectedDimension,
    ...(data?.next_suggested_dimensions || []),
    ...availableDimensions,
  ].filter((v, i, a) => a.indexOf(v) === i && v);

  const hasFilters = Object.keys(parentFilters).length > 0;

  // Summary tiles
  const topSegment =
    data && data.segments.length > 0
      ? data.segments.reduce((a, b) => (b.metric_value > a.metric_value ? b : a), data.segments[0])
      : null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <header className="rounded-2xl border border-[#4a2d8a]/60 bg-gradient-to-br from-[#2a1857] via-[#36206b] to-[#47298a] px-5 sm:px-6 py-5 space-y-5 shadow-sm">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs">
          <button
            onClick={onBackToWorkspace}
            className="inline-flex items-center gap-1.5 font-medium text-violet-200/80 hover:text-white transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-300 rounded"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Analysis workspace
          </button>
          <ChevronRight className="w-3 h-3 text-violet-300/40" />
          <span aria-current="page" className="font-semibold text-white">
            Explore details
          </span>
        </nav>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          {/* Title block */}
          <div className="flex items-start gap-4 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-purple-500 text-white flex items-center justify-center shrink-0 shadow-sm ring-4 ring-white/10">
              <Layers className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-white leading-tight">Explore details</h1>
              <p className="text-sm text-violet-100/75 mt-1 max-w-xl leading-relaxed">
                Break down{' '}
                <span className="font-semibold text-white">{targetMetric}</span> by category, then
                drill into any segment to see what drives it.
              </p>
            </div>
          </div>
        </div>
      </header>

      {!analysisId ? (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800">Run an analysis to explore details</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Segment breakdowns are built from an analysis. Run the pipeline first, then come back
              here.
            </p>
          </div>
          <button
            onClick={onBackToWorkspace}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Go to analysis workflow
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Controls: filter trail & dimension select */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <nav aria-label="Active filters" className="flex items-center gap-2 text-xs text-slate-600 flex-wrap">
              <button
                onClick={handleResetFilters}
                className="font-semibold text-purple-700 hover:text-purple-900 flex items-center gap-1.5 cursor-pointer bg-purple-50 hover:bg-purple-100 px-2.5 py-1 rounded-lg border border-purple-200 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500"
                title={hasFilters ? 'Clear filters and start over' : 'Reset to the first breakdown'}
              >
                <RotateCcw className="w-3 h-3" />
                <span>All segments</span>
              </button>
              {Object.entries(parentFilters).map(([k, v]) => (
                <span key={k} className="flex items-center gap-1.5">
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 font-medium border border-slate-200">
                    {prettify(k)}: <span className="font-semibold text-purple-700">{String(v)}</span>
                  </span>
                </span>
              ))}
              <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
              <span className="font-semibold text-slate-900 bg-white px-2.5 py-1 rounded-lg border border-slate-300">
                {prettify(selectedDimension)}
              </span>
            </nav>

            <div className="flex items-center gap-2">
              <label htmlFor="breakdown-dimension" className="text-xs font-medium text-slate-500">
                Break down by
              </label>
              <select
                id="breakdown-dimension"
                value={selectedDimension}
                onChange={(e) => {
                  setSelectedDimension(e.target.value);
                  fetchDrillDown(e.target.value, parentFilters);
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500 cursor-pointer shadow-xs"
              >
                {allDimensionOptions.map((d) => (
                  <option key={d} value={d}>
                    {prettify(d)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-xs text-red-700"
            >
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div
              aria-busy="true"
              className="bg-white p-12 rounded-2xl border border-slate-200 flex flex-col items-center justify-center space-y-2"
            >
              <div className="w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-400 font-medium">Calculating segment breakdown…</p>
            </div>
          )}

          {data && !loading && (
            <>
              {/* Summary tiles */}
              {topSegment && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-white rounded-xl border border-slate-200 shadow-xs px-5 py-4">
                    <div className="text-xs font-medium text-slate-500">
                      Total {prettify(data.metric).toLowerCase()}
                    </div>
                    <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
                      ${data.total_value.toLocaleString()}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {hasFilters ? 'Within the selected filters' : 'Across all segments'}
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 shadow-xs px-5 py-4">
                    <div className="text-xs font-medium text-slate-500">
                      Segments in {prettify(data.dimension).toLowerCase()}
                    </div>
                    <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">
                      {data.segments.length}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">Shown, ranked by value</div>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 shadow-xs px-5 py-4">
                    <div className="text-xs font-medium text-slate-500">Largest segment</div>
                    <div className="text-2xl font-bold text-slate-900 mt-1 truncate" title={topSegment.dimension_value}>
                      {topSegment.dimension_value}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {topSegment.share_pct.toFixed(1)}% of total
                    </div>
                  </div>
                </div>
              )}

              {/* Adaptive visualization */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <AdaptiveVisualization
                  data={chartPoints}
                  title={`${prettify(data.dimension)} distribution`}
                  metricName={data.metric}
                  height={300}
                />
              </div>

              {/* Segment breakdown table */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
                <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-purple-600" />
                    <h3 className="text-sm font-bold text-slate-900">
                      Segment breakdown{' '}
                      <span className="font-medium text-slate-500">
                        ({data.segments.length} {data.segments.length === 1 ? 'segment' : 'segments'})
                      </span>
                    </h3>
                  </div>
                  <span className="text-xs font-medium text-slate-500">
                    Total value:{' '}
                    <span className="font-bold text-slate-900 tabular-nums">
                      ${data.total_value.toLocaleString()}
                    </span>
                  </span>
                </div>

                {data.segments.length === 0 ? (
                  <div className="px-6 py-10 text-center text-xs text-slate-500">
                    No segments found for the current filters. Use “All segments” to start over.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-100/70 text-slate-600 font-semibold">
                        <tr>
                          <th className="px-5 py-3 border-b border-slate-200">{prettify(data.dimension)}</th>
                          <th className="px-5 py-3 border-b border-slate-200 text-right">
                            {prettify(data.metric)}
                          </th>
                          <th className="px-5 py-3 border-b border-slate-200 text-right">Share</th>
                          <th className="px-5 py-3 border-b border-slate-200 text-right">Records</th>
                          <th className="px-5 py-3 border-b border-slate-200 text-right">
                            Variance from mean
                          </th>
                          <th className="px-5 py-3 border-b border-slate-200 text-center">Drill down</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {data.segments.map((seg, sIdx) => {
                          const variance = seg.variance_from_mean_pct ?? 0;
                          const tone =
                            variance > 0
                              ? 'text-emerald-600'
                              : variance < 0
                              ? 'text-rose-600'
                              : 'text-slate-400';
                          const sharePct = Math.min(100, Math.max(0, seg.share_pct));
                          return (
                            <tr key={sIdx} className="hover:bg-purple-50/40 transition-colors">
                              <td className="px-5 py-3 font-bold text-slate-900">{seg.dimension_value}</td>
                              <td className="px-5 py-3 font-semibold text-slate-800 text-right tabular-nums">
                                ${seg.metric_value.toLocaleString()}
                              </td>
                              <td className="px-5 py-3 text-slate-600">
                                <div className="flex items-center justify-end gap-2.5">
                                  <div className="hidden sm:block w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                                    <div
                                      className="h-full rounded-full bg-purple-500"
                                      style={{ width: `${sharePct}%` }}
                                    />
                                  </div>
                                  <span className="tabular-nums w-12 text-right">
                                    {seg.share_pct.toFixed(1)}%
                                  </span>
                                </div>
                              </td>
                              <td className="px-5 py-3 text-slate-500 text-right tabular-nums">
                                {seg.record_count.toLocaleString()}
                              </td>
                              <td className={`px-5 py-3 font-semibold text-right tabular-nums ${tone}`}>
                                <span className="inline-flex items-center justify-end gap-0.5">
                                  {variance > 0 && <ArrowUpRight className="w-3.5 h-3.5" />}
                                  {variance < 0 && <ArrowDownRight className="w-3.5 h-3.5" />}
                                  {`${variance > 0 ? '+' : ''}${variance.toFixed(1)}%`}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-center">
                                {data.next_suggested_dimensions.length > 0 ? (
                                  <button
                                    onClick={() => handleSegmentClick(seg.dimension_value)}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-purple-700 hover:text-purple-900 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500"
                                  >
                                    <span>By {prettify(data.next_suggested_dimensions[0]).toLowerCase()}</span>
                                    <ChevronRight className="w-3 h-3" />
                                  </button>
                                ) : (
                                  <span className="text-[11px] text-slate-400">No further breakdown</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};