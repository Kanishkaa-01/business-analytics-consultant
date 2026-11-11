import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  Printer,
  Calendar,
  AlertCircle,
  FileSpreadsheet,
  Download,
  ChevronDown,
  FileCheck,
  ShieldCheck,
  Info
} from 'lucide-react';
import { AnalysisRunResponse, DecisionRecord, RecommendationItem } from '../../types';

interface Props {
  analysis: AnalysisRunResponse;
  decisions: DecisionRecord[];
  recommendations: RecommendationItem[];
  onOpenDecisionModal: (rec: RecommendationItem) => void;
}

export const DecisionNotes: React.FC<Props> = ({
  analysis,
  decisions,
  recommendations,
  onOpenDecisionModal,
}) => {
  const [downloadOpen, setDownloadOpen] = useState<boolean>(false);
  const downloadRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (downloadRef.current && !downloadRef.current.contains(event.target as Node)) {
        setDownloadOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const acceptedCount = decisions.filter((d) => d.decision_status === 'Accepted').length;
  const rejectedCount = decisions.filter((d) => d.decision_status === 'Rejected').length;
  const reviewCount = decisions.filter(
    (d) => d.decision_status === 'Under Review' || d.decision_status === 'Deferred'
  ).length;

  const totalAcceptedImpact = decisions
    .filter((d) => d.decision_status === 'Accepted')
    .reduce((acc, curr) => acc + (curr.expected_impact_dollars || 0), 0);

  const handleFullReport = () => {
    window.open(`/api/export/${analysis.id}/complete-decision-report?format=html`, '_blank');
  };

  const handleDownloadPdf = () => {
    setDownloadOpen(false);
    window.open(`/api/export/${analysis.id}/complete-decision-report?format=pdf`, '_blank');
  };

  const handleDownloadExcel = () => {
    setDownloadOpen(false);
    window.open(`/api/export/${analysis.id}/excel-report`, '_blank');
  };

  const handlePrintSummary = () => {
    window.open(`/api/export/${analysis.id}/print-report`, '_blank');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Accepted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Accepted
          </span>
        );
      case 'Rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
            <XCircle className="w-3.5 h-3.5" />
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <Clock className="w-3.5 h-3.5" />
            Needs Review
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Decision Notes & Action Logs
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Record, audit, and export all executive decisions made on analytical recommendations.
            Ensures human-in-the-loop oversight and clear accountability.
          </p>
        </div>

        {/* Reporting Actions (Only: Full Report, Download, Print Summary) */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {/* 1. Full Report */}
          <button
            onClick={handleFullReport}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-2xs transition-colors cursor-pointer"
            title="View Complete 17-Section Business Decision Report"
          >
            <FileCheck className="w-3.5 h-3.5" />
            <span>Full Report</span>
          </button>

          {/* 2. Download Dropdown */}
          <div className="relative" ref={downloadRef}>
            <button
              onClick={() => setDownloadOpen(!downloadOpen)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold border border-slate-300 shadow-2xs transition-colors cursor-pointer"
              aria-expanded={downloadOpen}
              aria-haspopup="true"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Download</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {downloadOpen && (
              <div className="absolute right-0 mt-1.5 w-44 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-50 text-xs animate-in fade-in slide-in-from-top-1 duration-150">
                <button
                  onClick={handleDownloadPdf}
                  className="w-full text-left px-3.5 py-2 hover:bg-rose-50 flex items-center gap-2 text-slate-700 hover:text-rose-900 transition-colors cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  <span>PDF Document</span>
                </button>
                <button
                  onClick={handleDownloadExcel}
                  className="w-full text-left px-3.5 py-2 hover:bg-emerald-50 flex items-center gap-2 text-slate-700 hover:text-emerald-900 transition-colors cursor-pointer"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>Excel Workbook</span>
                </button>
              </div>
            )}
          </div>

          {/* 3. Print Summary */}
          <button
            onClick={handlePrintSummary}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold shadow-2xs transition-colors cursor-pointer"
            title="Print concise executive decision summary"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Summary</span>
          </button>
        </div>
      </div>

      {/* Decision Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
            Total Decisions Logged
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            {decisions.length} / {recommendations.length}
          </div>
          <div className="text-xs text-slate-500 mt-1">Actions reviewed by management</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
            Accepted Actions
          </div>
          <div className="text-2xl font-extrabold text-emerald-600">
            {acceptedCount}
          </div>
          <div className="text-xs text-slate-500 mt-1">Approved for implementation</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
            Under Review / Deferred
          </div>
          <div className="text-2xl font-extrabold text-amber-600">
            {reviewCount}
          </div>
          <div className="text-xs text-slate-500 mt-1">Awaiting stakeholder feedback</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="text-xs font-semibold uppercase text-slate-500 mb-1">
            Committed Value Gain
          </div>
          <div className="text-2xl font-extrabold text-blue-600">
            +${totalAcceptedImpact.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-slate-500 mt-1">Total projected financial recovery</div>
        </div>
      </div>

      {/* Clarification Callout: Scenario vs Recommendation vs Decision */}
      <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-900">
        <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-bold">Human-in-the-Loop Governance:</span>
          <p className="text-blue-800 leading-relaxed">
            A scenario simulation is an estimate; a recommendation is an analytical suggestion.
            Only entries recorded in this Action Log represent approved, binding management decisions.
          </p>
        </div>
      </div>

      {/* Decision Notes List */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Decision Notes & Action Log
          </h3>
          <span className="text-xs text-slate-500">
            {decisions.length} recorded entry{decisions.length === 1 ? '' : 'ies'}
          </span>
        </div>

        {decisions.length === 0 ? (
          <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-500 space-y-2">
            <p>No decision notes recorded yet.</p>
            <p className="text-slate-400">
              Navigate to <b>6. Recommendations</b> and click <b>Record Decision</b> on any item to log your notes.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {decisions.map((dec) => {
              const matchedRec = recommendations.find((r) => r.id === dec.recommendation_id);
              return (
                <div
                  key={dec.id}
                  className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-all space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-200/80">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-500">{dec.recommendation_id}</span>
                        <h4 className="text-sm font-bold text-slate-900">{dec.action_title}</h4>
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-3">
                        <span>Stakeholder: <b className="text-slate-700">{dec.stakeholder || 'Management'}</b></span>
                        {dec.target_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-400" />
                            Target: <b className="text-slate-700">{dec.target_date}</b>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {getStatusBadge(dec.decision_status)}
                      {matchedRec && (
                        <button
                          onClick={() => onOpenDecisionModal(matchedRec)}
                          className="text-xs font-semibold text-blue-600 hover:text-blue-800 underline cursor-pointer"
                        >
                          Edit Note
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Decision Reason & Impact */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="md:col-span-2 space-y-0.5">
                      <span className="font-bold text-slate-700">Reason / Rationale:</span>
                      <p className="text-slate-600 bg-white p-2.5 rounded-lg border border-slate-200/80 leading-relaxed font-medium">
                        {dec.notes_rationale || 'No specific rationale entered.'}
                      </p>
                    </div>

                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-700">Estimated Impact:</span>
                      <div className="p-2.5 bg-white rounded-lg border border-slate-200/80">
                        <div className="text-base font-extrabold text-emerald-700">
                          +${Number(dec.expected_impact_dollars || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Expected value recovery</div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export { DecisionNotes as Stage8_DecisionNotes };

