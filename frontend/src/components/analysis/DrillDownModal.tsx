import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { Layers, X, ChevronRight, Filter, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';
import { DrillDownResponse } from '../../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
  initialDimension?: string;
  targetMetric?: string;
  availableDimensions?: string[];
}

export const DrillDownModal: React.FC<Props> = ({
  isOpen,
  onClose,
  analysisId,
  initialDimension,
  targetMetric,
  availableDimensions = [],
}) => {
  const [selectedDimension, setSelectedDimension] = useState<string>(initialDimension || availableDimensions[0] || 'region');
  const [parentFilters, setParentFilters] = useState<Record<string, any>>({});
  const [data, setData] = useState<DrillDownResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDrillDown = async (dim: string, filters: Record<string, any>) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.drillDown(analysisId, {
        dimension: dim,
        metric: targetMetric,
        aggregation: 'sum',
        parent_filters: filters,
        limit: 10,
      });
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Drill-down failed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen || !analysisId) return;
    const initialDim = initialDimension || availableDimensions[0] || 'region';
    setSelectedDimension(initialDim);
    setParentFilters({});
    fetchDrillDown(initialDim, {});
  }, [isOpen, analysisId, initialDimension]);

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
    const baseDim = availableDimensions[0] || 'region';
    setSelectedDimension(baseDim);
    fetchDrillDown(baseDim, {});
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden my-6">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Explore Details: Dimensional Breakdown</h3>
              <p className="text-xs text-slate-500">Deconstruct metrics across organizational and customer segments</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[78vh] overflow-y-auto">
          {/* Breadcrumb Navigation & Dimension Select */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
            {/* Filter Breadcrumbs */}
            <div className="flex items-center gap-1.5 text-xs text-slate-600 flex-wrap">
              <button
                onClick={handleResetFilters}
                className="font-bold text-indigo-600 hover:underline"
              >
                All Data
              </button>
              {Object.entries(parentFilters).map(([k, v]) => (
                <span key={k} className="flex items-center gap-1.5">
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                  <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
                    {k}: {String(v)}
                  </span>
                </span>
              ))}
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-bold text-slate-900">{selectedDimension}</span>
            </div>

            {/* Dimension Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Breakdown:</span>
              <select
                value={selectedDimension}
                onChange={(e) => {
                  setSelectedDimension(e.target.value);
                  fetchDrillDown(e.target.value, parentFilters);
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500"
              >
                {[selectedDimension, ...(data?.next_suggested_dimensions || []), ...availableDimensions]
                  .filter((v, i, a) => a.indexOf(v) === i)
                  .map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {error && (
            <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-2">
              <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-400 font-medium">Aggregating dimensional slices...</p>
            </div>
          )}

          {data && !loading && (
            <>
              {/* ECharts Chart */}
              {data.echarts_spec && Object.keys(data.echarts_spec).length > 0 && (
                <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-200">
                  <ReactECharts
                    option={data.echarts_spec}
                    style={{ height: 260 }}
                    onEvents={{
                      click: (params: any) => {
                        if (params?.name) handleSegmentClick(params.name);
                      },
                    }}
                  />
                  <p className="text-[11px] text-slate-400 text-center mt-1">
                    Click a bar to explore sub-dimensions
                  </p>
                </div>
              )}

              {/* Segments Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-600 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-2.5 border-b border-slate-200">{data.dimension} Segment</th>
                      <th className="px-4 py-2.5 border-b border-slate-200">{data.metric}</th>
                      <th className="px-4 py-2.5 border-b border-slate-200">Share %</th>
                      <th className="px-4 py-2.5 border-b border-slate-200">Records</th>
                      <th className="px-4 py-2.5 border-b border-slate-200">Variance from Avg</th>
                      <th className="px-4 py-2.5 border-b border-slate-200">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {data.segments.map((seg, sIdx) => (
                      <tr key={sIdx} className="hover:bg-indigo-50/40">
                        <td className="px-4 py-2.5 font-bold text-slate-900">{seg.dimension_value}</td>
                        <td className="px-4 py-2.5 font-semibold text-slate-800">{seg.metric_value.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-slate-600">{seg.share_pct.toFixed(1)}%</td>
                        <td className="px-4 py-2.5 text-slate-500">{seg.record_count.toLocaleString()}</td>
                        <td className="px-4 py-2.5 font-semibold">
                          <span className={seg.variance_from_mean_pct && seg.variance_from_mean_pct > 0 ? 'text-emerald-600' : 'text-rose-600'}>
                            {seg.variance_from_mean_pct ? `${seg.variance_from_mean_pct > 0 ? '+' : ''}${seg.variance_from_mean_pct.toFixed(1)}%` : '0%'}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          {data.next_suggested_dimensions.length > 0 && (
                            <button
                              onClick={() => handleSegmentClick(seg.dimension_value)}
                              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                            >
                              <span>Explore {data.next_suggested_dimensions[0]}</span>
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex justify-between items-center">
          <span className="text-xs text-slate-500">
            {data ? `Total Value: ${data.total_value.toLocaleString()} across ${data.segments.length} segments` : ''}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors shadow-xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
