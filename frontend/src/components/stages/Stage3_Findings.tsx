import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Sparkles,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Layers,
  AlertCircle,
  BarChart2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import {
  DiagnosticReport,
  FindingItem,
  AdvancedFindingsReport,
  ChartSpecification
} from '../../types';
import { api } from '../../services/api';
import { AutoVisualization } from '../charts/AutoVisualization';

interface Props {
  diagnostic: DiagnosticReport;
  analysisId?: string;
  onNavigateNext: () => void;
  onOpenDrillDown?: (dimension?: string, metric?: string) => void;
}

export const Stage3_Findings: React.FC<Props> = ({
  diagnostic,
  analysisId,
  onNavigateNext,
  onOpenDrillDown,
}) => {
  const [filterType, setFilterType] = useState<'All' | 'Problem' | 'Opportunity'>('All');
  const [advFindings, setAdvFindings] = useState<AdvancedFindingsReport | null>(null);
  const [autoVizSpec, setAutoVizSpec] = useState<ChartSpecification | null>(null);
  const [isLoadingAdv, setIsLoadingAdv] = useState<boolean>(false);
  const [showAnomalyDetails, setShowAnomalyDetails] = useState<boolean>(false);

  useEffect(() => {
    if (analysisId) {
      loadAdvancedData(analysisId);
    }
  }, [analysisId]);

  const loadAdvancedData = async (id: string) => {
    setIsLoadingAdv(true);
    try {
      const [adv, viz] = await Promise.all([
        api.getAdvancedFindings(id).catch(() => null),
        api.getVisualization(id).catch(() => null),
      ]);
      setAdvFindings(adv);
      setAutoVizSpec(viz);
    } catch (e) {
      console.warn('Could not load advanced findings:', e);
    } finally {
      setIsLoadingAdv(false);
    }
  };

  const findings: FindingItem[] = diagnostic.findings || [];
  const filteredFindings =
    filterType === 'All'
      ? findings
      : findings.filter((f) => f.type === filterType);

  const problemCount = findings.filter((f) => f.type === 'Problem').length;
  const oppCount = findings.filter((f) => f.type === 'Opportunity').length;

  return (
    <div className="space-y-6">

      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Key Findings
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            {diagnostic.diagnostic_narrative}
          </p>
        </div>

        {/* Total Variance Pill */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0 text-right">
          <div className="text-xs uppercase font-bold text-slate-500">
            Observed Difference ({diagnostic.focal_metric})
          </div>
          <div
            className={`text-2xl font-black mt-1 ${
              diagnostic.total_variance < 0 ? 'text-rose-600' : 'text-emerald-600'
            }`}
          >
            {diagnostic.total_variance > 0 ? '+' : ''}
            ${Math.abs(diagnostic.total_variance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            <span className="text-sm font-semibold ml-1">
              ({diagnostic.variance_pct > 0 ? '+' : ''}{diagnostic.variance_pct}%)
            </span>
          </div>
        </div>
      </div>

      {/* 1. Findings Section (Primary) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Findings
            </h3>
            <span className="text-xs text-slate-500">
              ({filteredFindings.length} {filteredFindings.length === 1 ? 'item' : 'items'} identified)
            </span>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterType('All')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                filterType === 'All'
                  ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              All Findings ({findings.length})
            </button>
            <button
              onClick={() => setFilterType('Problem')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                filterType === 'Problem'
                  ? 'bg-rose-600 text-white border-rose-600 shadow-xs'
                  : 'bg-white text-rose-700 border-rose-200 hover:bg-rose-50'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Problems ({problemCount})
            </button>
            <button
              onClick={() => setFilterType('Opportunity')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                filterType === 'Opportunity'
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                  : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Opportunities ({oppCount})
            </button>
          </div>
        </div>

        {/* Findings Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredFindings.map((finding, idx) => {
            const isProblem = finding.type === 'Problem';
            return (
              <div
                key={idx}
                className={`p-5 rounded-xl border bg-white shadow-xs space-y-3 transition-all ${
                  isProblem
                    ? 'border-rose-100 hover:border-rose-300'
                    : 'border-emerald-100 hover:border-emerald-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`p-1.5 rounded-lg ${
                        isProblem ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'
                      }`}
                    >
                      {isProblem ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                    </span>
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        {finding.metric} &bull; {finding.type}
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">{finding.title}</h4>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
                      isProblem
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {finding.type}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-xs">
                  <div>
                    <div className="text-[10px] text-slate-400">Observed Value</div>
                    <div className="font-bold text-slate-900">{finding.observed_value}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Comparison</div>
                    <div className="font-medium text-slate-600">{finding.comparison}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400">Difference</div>
                    <div className={`font-bold ${isProblem ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {finding.difference}
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 pt-1 text-[11px]">
                  {finding.possible_reason && (
                    <div className="p-2 rounded-lg bg-slate-50 border border-slate-100 text-slate-600">
                      <span className="font-semibold text-slate-800">Possible Contributor: </span>
                      {finding.possible_reason}
                    </div>
                  )}
                  {finding.recommended_action && (
                    <div className="p-2 rounded-lg bg-blue-50/60 border border-blue-100 text-blue-800">
                      <span className="font-semibold text-blue-900">Recommended Action: </span>
                      {finding.recommended_action}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Main Visualization Section */}
      {autoVizSpec && autoVizSpec.available && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold uppercase tracking-wider text-slate-700">
              Visualization
            </span>
            <span>Supports primary finding</span>
          </div>
          <AutoVisualization spec={autoVizSpec} loading={isLoadingAdv} />
        </div>
      )}

      {/* 3. Unusual Data Points */}
      {advFindings && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                <span>Unusual Data Points</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Unusual values identified using the IQR method.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                {advFindings.anomalies.length} {advFindings.anomalies.length === 1 ? 'unusual value' : 'unusual values'} detected.
              </span>
              {advFindings.anomalies.length > 0 && (
                <button
                  onClick={() => setShowAnomalyDetails((prev) => !prev)}
                  className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:bg-blue-100 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 transition-colors cursor-pointer"
                >
                  <span>{showAnomalyDetails ? 'Hide Details' : 'View Details'}</span>
                  {showAnomalyDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>
          </div>

          {advFindings.anomalies.length === 0 ? (
            <div className="text-xs text-slate-500 p-3 bg-slate-50 rounded-lg text-center">
              No unusual values detected outside typical ranges.
            </div>
          ) : (
            <>
              {/* Compact Summary when collapsed */}
              {!showAnomalyDetails && (
                <div className="p-3 bg-amber-50/40 border border-amber-200/80 rounded-lg flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="text-slate-700">
                    Identified {advFindings.anomalies.filter((a) => a.severity === 'High').length} high-severity and {advFindings.anomalies.filter((a) => a.severity !== 'High').length} standard outliers across periods.
                  </span>
                </div>
              )}

              {/* Detailed Cards when expanded */}
              {showAnomalyDetails && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                  {advFindings.anomalies.map((a, idx) => (
                    <div key={idx} className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{a.period_or_record}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            a.severity === 'High' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {a.severity} Severity
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-700 leading-relaxed">
                        {a.statement}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 4. Segment Comparisons */}
      {advFindings?.segment_comparisons && advFindings.segment_comparisons.length > 0 && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 uppercase tracking-wider">
                <BarChart2 className="w-4 h-4 text-purple-600" />
                <span>Segment Comparisons</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Which segments are performing differently across categories?
              </p>
            </div>
            <span className="text-[11px] text-slate-500">
              {advFindings.segment_comparisons.length} dimensions evaluated
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {advFindings.segment_comparisons.map((sc, idx) => (
              <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{sc.dimension}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                      {sc.spread_pct.toFixed(1)}% Spread
                    </span>
                    {onOpenDrillDown && (
                      <button
                        onClick={() => onOpenDrillDown(sc.dimension, diagnostic.focal_metric)}
                        className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-2 py-0.5 rounded transition-colors cursor-pointer"
                        title={`Explore details for ${sc.dimension}`}
                      >
                        <Layers className="w-3 h-3 text-indigo-600" />
                        <span>Explore Details</span>
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-[11px] text-slate-700 leading-relaxed">
                  {sc.statement}
                </p>
                {sc.associated_pattern && (
                  <p className="text-[10px] text-slate-500 italic pt-0.5">
                    Associated Pattern: {sc.associated_pattern}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Stage</div>
          <div className="text-sm font-semibold">Explore Possible Reasons & Associated Factors</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
        >
          <span>Examine Possible Reasons</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
