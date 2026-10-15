import React, { useState, useEffect } from 'react';
import {
  Target,
  Plus,
  Trash2,
  X,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../../services/api';
import { KpiGoalResponse } from '../../types';

interface Props {
  analysisId: string;
  datasetId: string;
  availableMetrics?: string[];
}

/* ---------- helpers ---------- */

type Tone = 'good' | 'near' | 'off';

const toneOf = (status: string): Tone =>
  status === 'Target Achieved' || status === 'On Track'
    ? 'good'
    : status === 'Near Target'
    ? 'near'
    : 'off';

const TONE_STYLES: Record<Tone, { pill: string; dot: string }> = {
  good: { pill: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-500' },
  near: { pill: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-500' },
  off: { pill: 'bg-rose-50 text-rose-700 border-rose-200', dot: 'bg-rose-500' },
};

const fmt = (n?: number | null): string =>
  n === null || n === undefined ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: 2 });

// Remaining distance to the target amount. For growth targets the amount is
// baseline × (1 + growth%). Returns null when it can't be worked out.
const getGap = (goal: KpiGoalResponse): number | null => {
  if (goal.current_value === null || goal.current_value === undefined) return null;
  let targetAmount: number | null;
  if (goal.target_type === 'percentage_growth') {
    targetAmount =
      goal.baseline_value === null || goal.baseline_value === undefined
        ? null
        : goal.baseline_value * (1 + goal.target_value / 100);
  } else {
    targetAmount = goal.target_value;
  }
  return targetAmount === null ? null : targetAmount - goal.current_value;
};

const inputClass =
  'w-full px-3 py-2.5 text-sm rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent placeholder:text-slate-400';

/* ---------- component ---------- */

export const KpiGoals: React.FC<Props> = ({
  analysisId,
  datasetId,
  availableMetrics = ['Revenue', 'Profit', 'Quantity', 'Unit Price'],
}) => {
  const [goals, setGoals] = useState<KpiGoalResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMetric, setNewMetric] = useState(availableMetrics[0] || 'Revenue');
  const [newTargetType, setNewTargetType] = useState<'absolute' | 'percentage_growth'>('absolute');
  const [newTargetValue, setNewTargetValue] = useState<number>(100000);
  const [newNotes, setNewNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const loadGoals = async () => {
    if (!analysisId) return;
    setLoading(true);
    setLoadError(null);
    try {
      const res = await api.listGoals(analysisId);
      setGoals(res);
    } catch (err: any) {
      setLoadError(err?.message || 'Could not load your targets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGoals();
  }, [analysisId]);

  // Close the dialog with Escape
  useEffect(() => {
    if (!showAddModal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowAddModal(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showAddModal]);

  const openAddModal = () => {
    setError(null);
    setNewNotes('');
    setShowAddModal(true);
  };

  const handleCreateGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createGoal(analysisId, {
        dataset_id: datasetId,
        analysis_id: analysisId,
        metric: newMetric.trim(),
        target_type: newTargetType,
        target_value: Number(newTargetValue),
        notes: newNotes,
      });
      setShowAddModal(false);
      setNewNotes('');
      await loadGoals();
    } catch (err: any) {
      setError(err.message || 'Failed to save goal.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGoal = async (id: string) => {
    setActionError(null);
    try {
      await api.deleteGoal(analysisId, id);
      setGoals((prev) => prev.filter((g) => g.id !== id));
    } catch (err: any) {
      setActionError(err?.message || 'Could not delete the target.');
    } finally {
      setPendingDeleteId(null);
    }
  };

  const counts = {
    good: goals.filter((g) => toneOf(g.status) === 'good').length,
    near: goals.filter((g) => toneOf(g.status) === 'near').length,
    off: goals.filter((g) => toneOf(g.status) === 'off').length,
  };

  const summaryTiles = [
    { label: 'Total targets', value: goals.length, icon: Target, tint: 'text-slate-500 bg-slate-100' },
    { label: 'On track or achieved', value: counts.good, icon: CheckCircle2, tint: 'text-emerald-600 bg-emerald-50' },
    { label: 'Near target', value: counts.near, icon: AlertTriangle, tint: 'text-amber-600 bg-amber-50' },
    { label: 'Off track', value: counts.off, icon: AlertCircle, tint: 'text-rose-600 bg-rose-50' },
  ];

  return (
    <div className="space-y-6">
      {/* Summary tiles */}
      {!loading && goals.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryTiles.map(({ label, value, icon: Icon, tint }) => (
            <div
              key={label}
              className="bg-white rounded-xl border border-slate-200 shadow-xs px-4 py-3.5 flex items-center gap-3"
            >
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${tint}`}>
                <Icon className="w-4.5 h-4.5" />
              </div>
              <div className="min-w-0">
                <div className="text-2xl font-bold text-slate-900 leading-none tabular-nums">{value}</div>
                <div className="text-xs text-slate-500 mt-1 truncate">{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Targets */}
      <section className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Your targets</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Progress is measured from each metric’s baseline to its target.
            </p>
          </div>
          <button
            onClick={openAddModal}
            className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
          >
            <Plus className="w-4 h-4" />
            <span>Set target</span>
          </button>
        </div>

        <div className="p-6">
          {actionError && (
            <div
              role="alert"
              className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              {actionError}
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div aria-busy="true" className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
              {[0, 1].map((i) => (
                <div key={i} className="p-4 rounded-xl border border-slate-200 space-y-3">
                  <div className="h-4 w-1/3 bg-slate-200 rounded" />
                  <div className="h-14 bg-slate-100 rounded-lg" />
                  <div className="h-2 bg-slate-100 rounded-full" />
                </div>
              ))}
            </div>
          )}

          {/* Load error */}
          {!loading && loadError && (
            <div className="py-8 text-center space-y-3">
              <AlertCircle className="w-8 h-8 mx-auto text-red-400" />
              <p className="text-xs text-slate-600">{loadError}</p>
              <button
                onClick={loadGoals}
                className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 cursor-pointer"
              >
                Try again
              </button>
            </div>
          )}

          {/* Empty state */}
          {!loading && !loadError && goals.length === 0 && (
            <div className="py-10 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                <Target className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-800">No targets yet</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Pick a metric, such as revenue or profit, and set the number you want to reach.
                  Progress shows up here.
                </p>
              </div>
              <button
                onClick={openAddModal}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
              >
                Set your first target
              </button>
            </div>
          )}

          {/* Goal cards */}
          {!loading && !loadError && goals.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {goals.map((goal) => {
                const tone = TONE_STYLES[toneOf(goal.status)];
                const progress = goal.progress_pct ?? 0;
                const progressClamped = Math.min(100, Math.max(0, progress));
                const gap = getGap(goal);
                const isConfirming = pendingDeleteId === goal.id;

                return (
                  <article
                    key={goal.id}
                    className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors space-y-4"
                  >
                    {/* Title row */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-bold text-slate-900 text-sm truncate">{goal.metric}</h3>
                        <span className="text-xs text-slate-400">
                          {goal.target_type === 'percentage_growth' ? 'Growth target' : 'Absolute target'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${tone.pill}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${tone.dot}`} />
                          {goal.status}
                        </span>
                        <button
                          onClick={() => setPendingDeleteId(goal.id)}
                          className="p-1.5 rounded-md text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
                          title="Delete target"
                          aria-label={`Delete target for ${goal.metric}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Numbers */}
                    <div className="grid grid-cols-3 divide-x divide-slate-200 rounded-lg bg-slate-50 border border-slate-100 py-2.5">
                      <div className="px-3">
                        <div className="text-[11px] font-medium text-slate-400">Baseline</div>
                        <div className="text-sm font-bold text-slate-700 mt-0.5 tabular-nums truncate">
                          {fmt(goal.baseline_value)}
                        </div>
                      </div>
                      <div className="px-3">
                        <div className="text-[11px] font-medium text-slate-400">Current</div>
                        <div className="text-sm font-bold text-slate-900 mt-0.5 tabular-nums truncate">
                          {fmt(goal.current_value)}
                        </div>
                      </div>
                      <div className="px-3">
                        <div className="text-[11px] font-medium text-slate-400">Target</div>
                        <div className="text-sm font-bold text-emerald-700 mt-0.5 tabular-nums truncate">
                          {goal.target_type === 'percentage_growth'
                            ? `+${goal.target_value}%`
                            : fmt(goal.target_value)}
                        </div>
                      </div>
                    </div>

                    {/* Progress */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-baseline text-xs">
                        <span className="font-medium text-slate-500">
                          {gap === null ? 'Progress' : gap <= 0 ? 'Target reached' : `${fmt(gap)} to go`}
                        </span>
                        <span
                          className={`font-bold tabular-nums ${
                            progress >= 100 ? 'text-emerald-600' : 'text-slate-700'
                          }`}
                        >
                          {progress.toFixed(1)}%
                        </span>
                      </div>
                      <div
                        role="progressbar"
                        aria-valuenow={Math.round(progressClamped)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        className="w-full h-2 rounded-full bg-slate-100 overflow-hidden"
                      >
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            progress >= 100
                              ? 'bg-emerald-500'
                              : progress >= 75
                              ? 'bg-blue-600'
                              : progress >= 40
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                          style={{ width: `${progressClamped}%` }}
                        />
                      </div>
                    </div>

                    {goal.notes && (
                      <p className="text-xs text-slate-500 border-t border-slate-100 pt-3 leading-relaxed">
                        {goal.notes}
                      </p>
                    )}

                    {/* Inline delete confirmation */}
                    {isConfirming && (
                      <div className="flex items-center justify-between gap-3 rounded-lg bg-rose-50 border border-rose-200 px-3 py-2">
                        <span className="text-xs font-medium text-rose-800">Delete this target?</span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => setPendingDeleteId(null)}
                            className="px-2.5 py-1 rounded-md text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 cursor-pointer"
                          >
                            Keep
                          </button>
                          <button
                            onClick={() => handleDeleteGoal(goal.id)}
                            className="px-2.5 py-1 rounded-md text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 cursor-pointer"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Add target dialog */}
      {showAddModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setShowAddModal(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="kpi-dialog-title"
            className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full overflow-hidden"
          >
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-slate-200 bg-slate-50">
              <div>
                <h4 id="kpi-dialog-title" className="font-bold text-slate-900 text-sm">
                  Set a KPI target
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Choose a metric and the result you want to reach.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateGoal} className="p-5 space-y-4">
              {error && (
                <div
                  role="alert"
                  className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700"
                >
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="kpi-metric" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Metric
                </label>
                <input
                  id="kpi-metric"
                  type="text"
                  list="kpi-metric-options"
                  value={newMetric}
                  onChange={(e) => setNewMetric(e.target.value)}
                  placeholder="e.g. Net revenue, Profit, Units"
                  required
                  autoFocus
                  className={inputClass}
                />
                <datalist id="kpi-metric-options">
                  {availableMetrics.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="kpi-type" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Target type
                  </label>
                  <select
                    id="kpi-type"
                    value={newTargetType}
                    onChange={(e) => setNewTargetType(e.target.value as 'absolute' | 'percentage_growth')}
                    className={`${inputClass} cursor-pointer`}
                  >
                    <option value="absolute">Absolute value</option>
                    <option value="percentage_growth">% growth</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="kpi-value" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    {newTargetType === 'percentage_growth' ? 'Growth' : 'Target value'}
                  </label>
                  <div className="relative">
                    <input
                      id="kpi-value"
                      type="number"
                      step="any"
                      value={newTargetValue}
                      onChange={(e) => setNewTargetValue(Number(e.target.value))}
                      required
                      className={`${inputClass} ${newTargetType === 'percentage_growth' ? 'pr-8' : ''}`}
                    />
                    {newTargetType === 'percentage_growth' && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-400 pointer-events-none">
                        %
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-400 -mt-2">
                {newTargetType === 'percentage_growth'
                  ? 'Growth is measured against the metric’s baseline.'
                  : 'The exact value you want the metric to reach.'}
              </p>

              <div>
                <label htmlFor="kpi-notes" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Notes <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <textarea
                  id="kpi-notes"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="e.g. Approved in Q3 planning"
                  rows={2}
                  className={inputClass}
                />
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !newMetric.trim()}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold shadow-xs cursor-pointer"
                >
                  {saving ? 'Saving…' : 'Save target'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};