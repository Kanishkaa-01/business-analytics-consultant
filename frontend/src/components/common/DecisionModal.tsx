import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, AlertCircle } from 'lucide-react';
import { RecommendationItem, DecisionRecord } from '../../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  recommendation: RecommendationItem | null;
  existingDecision?: DecisionRecord | null;
  onSaveDecision: (payload: {
    recommendation_id: string;
    action_title: string;
    decision_status: 'Accepted' | 'Rejected' | 'Deferred' | 'Under Review';
    stakeholder: string;
    notes_rationale: string;
    target_date: string;
    expected_impact_dollars: number;
  }) => Promise<void>;
}

export const DecisionModal: React.FC<Props> = ({
  isOpen,
  onClose,
  recommendation,
  existingDecision,
  onSaveDecision,
}) => {
  if (!isOpen || !recommendation) return null;

  const [status, setStatus] = useState<'Accepted' | 'Rejected' | 'Deferred' | 'Under Review'>(
    existingDecision?.decision_status || 'Accepted'
  );
  const [stakeholder, setStakeholder] = useState<string>(
    existingDecision?.stakeholder || 'Executive Steering Committee'
  );
  const [targetDate, setTargetDate] = useState<string>(
    existingDecision?.target_date || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [expectedImpact, setExpectedImpact] = useState<number>(
    existingDecision?.expected_impact_dollars || recommendation.expected_financial_impact
  );
  const [notes, setNotes] = useState<string>(
    existingDecision?.notes_rationale || ''
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (existingDecision) {
      setStatus(existingDecision.decision_status);
      setStakeholder(existingDecision.stakeholder || 'Executive Steering Committee');
      setTargetDate(existingDecision.target_date || '');
      setExpectedImpact(existingDecision.expected_impact_dollars);
      setNotes(existingDecision.notes_rationale || '');
    } else {
      setStatus('Accepted');
      setStakeholder('Executive Steering Committee');
      setTargetDate(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
      setExpectedImpact(recommendation.expected_financial_impact);
      setNotes('');
    }
  }, [existingDecision, recommendation]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSaveDecision({
        recommendation_id: recommendation.id,
        action_title: recommendation.title,
        decision_status: status,
        stakeholder,
        notes_rationale: notes,
        target_date: targetDate,
        expected_impact_dollars: expectedImpact,
      });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs uppercase font-bold text-blue-600">
              Human-in-the-Loop Decision Recording
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-0.5">
              {recommendation.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Decision Status */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Decision Status
            </label>
            <div className="grid grid-cols-4 gap-2">
              {(['Accepted', 'Under Review', 'Deferred', 'Rejected'] as const).map((s) => (
                <button
                  type="button"
                  key={s}
                  onClick={() => setStatus(s)}
                  className={`py-2 px-2 rounded-lg font-bold border text-center transition-all ${
                    status === s
                      ? s === 'Accepted'
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                        : s === 'Rejected'
                        ? 'bg-rose-600 text-white border-rose-600 shadow-xs'
                        : s === 'Deferred'
                        ? 'bg-amber-500 text-white border-amber-500 shadow-xs'
                        : 'bg-blue-600 text-white border-blue-600 shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Stakeholder Owner */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Accountable Stakeholder / Owner
            </label>
            <input
              type="text"
              value={stakeholder}
              onChange={(e) => setStakeholder(e.target.value)}
              required
              className="w-full border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g., Chief Commercial Officer, Head of Operations"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Target Execution Date */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Target Milestone Date
              </label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Expected Impact */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Projected Impact ($)
              </label>
              <input
                type="number"
                value={expectedImpact}
                onChange={(e) => setExpectedImpact(Number(e.target.value))}
                className="w-full border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Justification Rationale Notes */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Executive Justification & Execution Notes
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Detail reasons for acceptance, implementation constraints, or deferral timeline..."
              className="w-full border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-lg font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? 'Recording...' : 'Commit Decision'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
