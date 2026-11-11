import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Scale,
  Percent,
  Layers,
  ArrowRight
} from 'lucide-react';
import { DataQualityReport } from '../../types';

interface Props {
  report: DataQualityReport;
  onNavigateNext?: () => void;
}

export const DataQuality: React.FC<Props> = ({ report, onNavigateNext }) => {
  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A':
        return 'text-emerald-600 bg-emerald-50 border-emerald-300';
      case 'B':
        return 'text-blue-600 bg-blue-50 border-blue-300';
      case 'C':
        return 'text-amber-600 bg-amber-50 border-amber-300';
      case 'D':
        return 'text-orange-600 bg-orange-50 border-orange-300';
      default:
        return 'text-rose-600 bg-rose-50 border-rose-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-sm border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Data Quality & Reliability Check
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            {report.reliability_assessment}
          </p>
        </div>


        {/* Score & Grade Dial */}
        <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0">
          <div className="text-right">
            <div className="text-xs uppercase font-bold text-slate-500">Quality Score</div>
            <div className="text-3xl font-extrabold text-slate-900">
              {report.overall_quality_score}<span className="text-lg font-normal text-slate-500">/100</span>
            </div>
          </div>
          <div
            className={`w-14 h-14 rounded-xl border flex items-center justify-center text-2xl font-black shadow-inner ${getGradeColor(
              report.grade
            )}`}
          >
            {report.grade}
          </div>
        </div>
      </div>

      {/* 4 Pillars Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-slate-500">Completeness</span>
            <Percent className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {(report.completeness_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Non-null values across matrix</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-slate-500">Validity</span>
            <CheckCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {(report.validity_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Bounds & domain compliance</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-slate-500">Uniqueness</span>
            <Layers className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {report.duplicate_rows === 0 ? '100%' : `${report.duplicate_rows} dups`}
          </div>
          <div className="text-xs text-slate-500 mt-1">Record-level deduplication</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase text-slate-500">Consistency</span>
            <Scale className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {(report.consistency_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Distribution stability</div>
        </div>
      </div>

      {/* Identified Issues Log */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Identified Quality & Integrity Anomalies ({report.issues.length})
        </h3>

        {report.issues.length === 0 ? (
          <div className="p-4 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-medium border border-emerald-200 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            No critical data hygiene issues detected. The dataset satisfies statistical prerequisites for attribution modeling.
          </div>
        ) : (
          <div className="space-y-2">
            {report.issues.map((issue, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 flex items-start gap-3 text-xs"
              >
                {issue.severity === 'Critical' ? (
                  <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                ) : issue.severity === 'Warning' ? (
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                ) : (
                  <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                        issue.severity === 'Critical'
                          ? 'bg-rose-100 text-rose-800'
                          : issue.severity === 'Warning'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {issue.severity}
                    </span>
                    <span className="font-semibold text-slate-900">
                      {issue.dimension} &bull; {issue.column || 'Dataset Wide'}
                    </span>
                    <span className="text-slate-500">
                      ({issue.affected_rows} rows / {issue.percentage}%)
                    </span>
                  </div>
                  <p className="text-slate-700">{issue.description}</p>
                  <p className="text-slate-500 italic">Recommendation: {issue.recommendation}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Column Quality Matrix */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
          Column-by-Column Integrity Profile
        </h3>
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full min-w-[640px] table-fixed text-left text-xs text-slate-700">
            {/* Fixed column widths keep every column in the same place on every row */}
            <colgroup>
              <col className="w-[26%]" />
              <col className="w-[22%]" />
              <col className="w-[16%]" />
              <col className="w-[20%]" />
              <col className="w-[16%]" />
            </colgroup>
            <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
              <tr>
                <th className="py-3 px-4">Column Name</th>
                <th className="py-3 px-4">Completeness</th>
                <th className="py-3 px-4 text-center">Validity</th>
                <th className="py-3 px-4 text-center">Outliers</th>
                <th
                  className="py-3 px-4 text-center"
                  title="Skewness: how lopsided the values are. Near 0 is symmetric; above 1 means a long tail of high values."
                >
                  Skewness
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.column_metrics.map((col) => (
                <tr key={col.column} className="hover:bg-slate-50/70">
                  <td className="py-2.5 px-4 font-semibold text-slate-900 truncate" title={col.column}>
                    {col.column}
                  </td>

                  <td className="py-2.5 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-24 shrink-0 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-emerald-500 h-1.5 rounded-full"
                          style={{ width: `${col.completeness_score * 100}%` }}
                        />
                      </div>
                      <span className="tabular-nums">
                        {(col.completeness_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>

                  <td className="py-2.5 px-4 text-center tabular-nums">
                    {(col.validity_score * 100).toFixed(1)}%
                  </td>

                  <td className="py-2.5 px-4">
                    {/* Count and percentage sit in fixed slots so they line up on every row */}
                    <div className="flex items-baseline justify-center gap-2 tabular-nums">
                      {col.outlier_count > 0 ? (
                        <>
                          <span className="w-10 text-right font-semibold text-amber-600">
                            {col.outlier_count.toLocaleString()}
                          </span>
                          <span className="w-16 text-left text-amber-500">
                            ({Number(col.outlier_percentage).toFixed(2)}%)
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="w-10 text-right text-slate-400">0</span>
                          <span className="w-16" aria-hidden="true" />
                        </>
                      )}
                    </div>
                  </td>

                  <td className="py-2.5 px-4 text-center tabular-nums text-slate-600">
                    {col.skewness !== null && col.skewness !== undefined ? (
                      Number(col.skewness).toFixed(2)
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {/* Next Phase Navigation Banner */}
<div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between gap-4">
  <div className="min-w-0">
    <div className="text-xs text-blue-300 font-bold uppercase">
      Next Stage
    </div>
    <div className="text-sm font-semibold">
      Review Business Performance & Key Metrics
    </div>
  </div>

  <button
    onClick={onNavigateNext}
    className="inline-flex shrink-0 items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
  >
    <span>Continue to Business Overview</span>
    <ArrowRight className="w-4 h-4" />
  </button>
</div>
    </div>
  );
};

export { DataQuality as Stage1_DataQuality };