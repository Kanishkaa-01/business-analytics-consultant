import React, { useEffect, useState } from 'react';
import { X, HelpCircle, CheckCircle, Info, ShieldAlert, BookOpen } from 'lucide-react';
import { api } from '../../services/api';
import { WhyThisResultResponse } from '../../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  analysisId: string;
  resultType: string;
  resultId: string;
}

export const WhyThisResultModal: React.FC<Props> = ({
  isOpen,
  onClose,
  analysisId,
  resultType,
  resultId,
}) => {
  const [data, setData] = useState<WhyThisResultResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !analysisId) return;
    setLoading(true);
    setError(null);
    api.getWhyThisResult(analysisId, resultType, resultId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Could not load explanation.'))
      .finally(() => setLoading(false));
  }, [isOpen, analysisId, resultType, resultId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Why This Result?</h3>
              <p className="text-xs text-slate-500">Transparent Methodology & Statistical Rationale</p>
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
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-7 h-7 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-500 font-medium">Retrieving deterministic decision trail...</p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Title & Plain English Summary */}
              <div className="bg-blue-50/70 border border-blue-100 rounded-xl p-4.5 space-y-1.5">
                <h4 className="font-bold text-blue-950 text-sm">{data.title}</h4>
                <p className="text-xs text-blue-900 leading-relaxed">{data.plain_english_summary}</p>
              </div>

              {/* Primary Driver */}
              <div className="border border-slate-200 rounded-xl p-4 space-y-1">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">PRIMARY CONTRIBUTING METRIC</span>
                <p className="text-sm font-semibold text-slate-900">{data.primary_driver}</p>
              </div>

              {/* Supporting Evidence */}
              {data.supporting_evidence && data.supporting_evidence.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    Empirical Evidence Points
                  </span>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
                    {data.supporting_evidence.map((ev, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-slate-700">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{ev}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Methodology & Formulas */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-indigo-600" />
                  Methodology & Mathematical Formulas
                </span>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2 text-xs text-slate-700">
                  <p><b>Methodology:</b> {data.methodology_applied}</p>
                  <p className="font-mono text-[11px] bg-white p-2 rounded border border-slate-200 text-slate-800">
                    {data.underlying_formulas_or_logic}
                  </p>
                </div>
              </div>

              {/* Data Inputs & Assumptions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="border border-slate-200 rounded-xl p-3 bg-white space-y-1.5">
                  <span className="font-bold text-slate-700 flex items-center gap-1">
                    <Info className="w-3.5 h-3.5 text-blue-500" /> Data Inputs
                  </span>
                  <ul className="list-disc list-inside text-slate-600 space-y-0.5 text-[11px]">
                    {data.data_inputs_used.map((inp, idx) => (
                      <li key={idx}>{inp}</li>
                    ))}
                  </ul>
                </div>
                <div className="border border-slate-200 rounded-xl p-3 bg-white space-y-1.5">
                  <span className="font-bold text-slate-700 flex items-center gap-1">
                    <Info className="w-3.5 h-3.5 text-amber-500" /> Assumptions & Limits
                  </span>
                  <ul className="list-disc list-inside text-slate-600 space-y-0.5 text-[11px]">
                    {data.limitations_and_assumptions.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Causation Disclaimer */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2.5 text-amber-900 text-xs leading-relaxed">
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{data.causation_disclaimer}</span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
