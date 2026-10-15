import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  History,
  Search,
  Trash2,
  Pencil,
  Play,
  Calendar,
  Database,
  ShieldCheck,
  Clock,
  X,
  AlertTriangle,
  AlertCircle,
  ArrowLeft,
  ChevronRight,
  Gauge,
} from 'lucide-react';
import { api } from '../services/api';
import { StoredAnalysisSummary } from '../types';

interface Props {
  onSelectAnalysis: (analysisId: string) => void;
  onBackToWorkspace: () => void;
}

type SortKey = 'newest' | 'oldest' | 'health' | 'name';


/* ---------- helpers ---------- */

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
};

const formatRelative = (iso: string): string => {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  const mins = Math.round((d.getTime() - Date.now()) / 60000);
  if (Math.abs(mins) < 60) return rtf.format(mins, 'minute');
  const hours = Math.round(mins / 60);
  if (Math.abs(hours) < 24) return rtf.format(hours, 'hour');
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 30) return rtf.format(days, 'day');
  return formatDate(iso);
};

const formatDuration = (ms?: number | null): string => {
  if (ms === null || ms === undefined) return '—';
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
};

const healthTone = (score: number) =>
  score >= 80
    ? { bar: 'bg-emerald-500', text: 'text-emerald-700' }
    : score >= 60
      ? { bar: 'bg-blue-500', text: 'text-blue-700' }
      : score >= 40
        ? { bar: 'bg-amber-500', text: 'text-amber-700' }
        : { bar: 'bg-rose-500', text: 'text-rose-700' };

/* ---------- dialog shell ---------- */

const Dialog: React.FC<{
  titleId: string;
  onClose: () => void;
  children: React.ReactNode;
}> = ({ titleId, onClose, children }) => {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-sm w-full overflow-hidden"
      >
        {children}
      </div>
    </div>
  );
};

/* ---------- page ---------- */

export const StoredAnalysesPage: React.FC<Props> = ({ onSelectAnalysis, onBackToWorkspace }) => {
  const [analyses, setAnalyses] = useState<StoredAnalysisSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('newest');
  const [renameTarget, setRenameTarget] = useState<StoredAnalysisSummary | null>(null);
  const [newName, setNewName] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<StoredAnalysisSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const requestId = useRef(0);

  // Debounce the search box so we don't hit the API on every keystroke
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchAnalyses = async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listStoredAnalyses(search);
      if (id === requestId.current) setAnalyses(data);
    } catch (err: any) {
      if (id === requestId.current) setError(err.message || 'Failed to fetch saved analyses.');
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [search]);

  const openRename = (item: StoredAnalysisSummary) => {
    setDialogError(null);
    setRenameTarget(item);
    setNewName(item.analysis_name);
  };

  const handleRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameTarget || !newName.trim()) return;
    setBusy(true);
    setDialogError(null);
    try {
      await api.renameAnalysis(renameTarget.id, newName.trim());
      setRenameTarget(null);
      await fetchAnalyses();
    } catch (err: any) {
      setDialogError(err.message || 'Failed to rename.');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setBusy(true);
    setDialogError(null);
    try {
      await api.deleteAnalysis(deleteTarget.id);
      setDeleteTarget(null);
      await fetchAnalyses();
    } catch (err: any) {
      setDialogError(err.message || 'Failed to delete.');
    } finally {
      setBusy(false);
    }
  };

  const sorted = useMemo(() => {
    const arr = [...analyses];
    switch (sortKey) {
      case 'oldest':
        return arr.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      case 'health':
        return arr.sort((a, b) => (b.health_score ?? -1) - (a.health_score ?? -1));
      case 'name':
        return arr.sort((a, b) => a.analysis_name.localeCompare(b.analysis_name));
      default:
        return arr.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
  }, [analyses, sortKey]);

  const stats = useMemo(() => {
    const scored = analyses.filter((a) => a.health_score !== null && a.health_score !== undefined);
    const avgHealth = scored.length
      ? scored.reduce((sum, a) => sum + (a.health_score as number), 0) / scored.length
      : null;
    const latest = analyses.length
      ? analyses.reduce((a, b) => (new Date(b.created_at) > new Date(a.created_at) ? b : a))
      : null;
    return {
      total: analyses.length,
      datasets: new Set(analyses.map((a) => a.dataset_name)).size,
      avgHealth,
      latest: latest ? formatRelative(latest.created_at) : '—',
    };
  }, [analyses]);

  const isInitialLoad = loading && analyses.length === 0;

  const summaryTiles = [
    { label: 'Saved analyses', value: String(stats.total), icon: History, tint: 'text-blue-600 bg-blue-50' },
    { label: 'Datasets analyzed', value: String(stats.datasets), icon: Database, tint: 'text-slate-600 bg-slate-100' },
    {
      label: 'Average health score',
      value: stats.avgHealth === null ? '—' : stats.avgHealth.toFixed(1),
      icon: Gauge,
      tint: 'text-emerald-600 bg-emerald-50',
    },
    { label: 'Last run', value: stats.latest, icon: Clock, tint: 'text-amber-600 bg-amber-50' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <header className="rounded-2xl border border-[#1b2f5c] bg-gradient-to-br from-[#0b1f44] via-[#102a58] to-[#1a3a7a] px-5 sm:px-6 py-5 space-y-5 shadow-sm">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs">
          <button
            onClick={onBackToWorkspace}
            className="inline-flex items-center gap-1.5 font-medium text-blue-200/80 hover:text-white transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 rounded"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to workspace
          </button>
          <ChevronRight className="w-3 h-3 text-blue-300/40" />
          <span aria-current="page" className="font-semibold text-white">
            Stored analyses
          </span>
        </nav>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="flex items-start gap-4 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-blue-500 text-white flex items-center justify-center shrink-0 shadow-sm ring-4 ring-white/10">
              <History className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-white leading-tight">Stored analyses</h1>

              <p className="text-sm text-blue-100/75 mt-1 max-w-xl leading-relaxed">
                Access past analyses, revisit insights, and continue where you left off.
              </p>

            </div>
          </div>
        </div>
      </header>

      {/* Summary tiles */}
      {!isInitialLoad && analyses.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {summaryTiles.map(({ label, value, icon: Icon, tint }) => (
            <div
              key={label}
              className="bg-white rounded-xl border border-slate-200 shadow-xs px-4 py-3.5 flex items-center gap-3"
            >
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${tint}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <div className="text-xl font-bold text-slate-900 leading-none tabular-nums truncate">
                  {value}
                </div>
                <div className="text-xs text-slate-500 mt-1 truncate">{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Toolbar: search and sort */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by analysis or dataset name"
            aria-label="Search stored analyses"
            className="w-full pl-10 pr-9 py-2.5 text-sm rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder:text-slate-400"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput('')}
              aria-label="Clear search"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-4">
          <span className="text-xs text-slate-500">
            {analyses.length} {analyses.length === 1 ? 'run' : 'runs'}
            {search && ' found'}
          </span>
          <div className="flex items-center gap-2">
            <label htmlFor="sort-analyses" className="text-xs font-medium text-slate-500">
              Sort by
            </label>
            <select
              id="sort-analyses"
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="health">Health score</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center justify-between gap-3"
        >
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
            {error}
          </span>
          <button
            onClick={fetchAnalyses}
            className="font-semibold text-red-700 hover:text-red-900 cursor-pointer"
          >
            Try again
          </button>
        </div>
      )}

      {/* List */}
      {isInitialLoad ? (
        <div aria-busy="true" className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 animate-pulse">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <div className="h-4 w-2/3 bg-slate-200 rounded" />
              <div className="h-3 w-1/2 bg-slate-100 rounded" />
              <div className="h-2 bg-slate-100 rounded-full" />
              <div className="h-8 bg-slate-100 rounded-lg" />
            </div>
          ))}
        </div>
      ) : sorted.length === 0 && !error ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
            <History className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-800">
              {search ? `No results for “${search}”` : 'No analyses yet'}
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {search
                ? 'Try a different analysis or dataset name.'
                : 'Upload a dataset and run the analysis pipeline. Each run is saved here with its full audit trail.'}
            </p>
          </div>
          {search ? (
            <button
              onClick={() => setSearchInput('')}
              className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold cursor-pointer"
            >
              Clear search
            </button>
          ) : (
            <button
              onClick={onBackToWorkspace}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Start an analysis
            </button>
          )}
        </div>
      ) : (
        <div
          className={`grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 transition-opacity ${loading ? 'opacity-60' : ''
            }`}
        >
          {sorted.map((item) => {
            const hasHealth = item.health_score !== null && item.health_score !== undefined;
            const tone = hasHealth ? healthTone(item.health_score as number) : null;
            const healthPct = hasHealth ? Math.min(100, Math.max(0, item.health_score as number)) : 0;

            return (
              <article
                key={item.id}
                className="bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-sm p-5 shadow-xs transition-all flex flex-col gap-4"
              >
                {/* Title */}
                <div className="space-y-2 min-w-0">
                  <h3 className="font-bold text-slate-900 text-sm leading-snug">
                    <button
                      onClick={() => onSelectAnalysis(item.id)}
                      className="text-left hover:text-blue-600 transition-colors cursor-pointer focus:outline-none focus-visible:underline"
                    >
                      {item.analysis_name}
                    </button>
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 min-w-0">
                    <Database className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate" title={item.dataset_name}>
                      {item.dataset_name}
                    </span>
                  </div>
                </div>

                {/* Health */}
                {hasHealth && tone && (
                  <div className="space-y-1.5">
                    <div className="flex items-baseline justify-between text-xs">
                      <span className="font-medium text-slate-500">Health score</span>
                      <span className={`font-bold tabular-nums ${tone.text}`}>
                        {(item.health_score as number).toFixed(1)}
                        <span className="text-slate-400 font-medium"> / 100</span>
                      </span>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuenow={Math.round(healthPct)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label="Health score"
                      className="h-1.5 rounded-full bg-slate-100 overflow-hidden"
                    >
                      <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${healthPct}%` }} />
                    </div>
                  </div>
                )}

                {/* Meta */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span
                    className="flex items-center gap-1.5"
                    title={new Date(item.created_at).toLocaleString()}
                  >
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    {formatRelative(item.created_at)}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    Ran in {formatDuration(item.execution_time_ms)}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-3 mt-auto border-t border-slate-100">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openRename(item)}
                      className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                      title="Rename"
                      aria-label={`Rename ${item.analysis_name}`}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        setDialogError(null);
                        setDeleteTarget(item);
                      }}
                      className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
                      title="Delete"
                      aria-label={`Delete ${item.analysis_name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <button
                    onClick={() => onSelectAnalysis(item.id)}
                    className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>Open analysis</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Rename dialog */}
      {renameTarget && (
        <Dialog titleId="rename-title" onClose={() => setRenameTarget(null)}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-slate-50">
            <h4 id="rename-title" className="font-bold text-slate-900 text-sm">
              Rename analysis
            </h4>
            <button
              onClick={() => setRenameTarget(null)}
              aria-label="Close"
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <form onSubmit={handleRename} className="p-5 space-y-4">
            {dialogError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {dialogError}
              </div>
            )}
            <div>
              <label htmlFor="rename-input" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Analysis name
              </label>
              <input
                id="rename-input"
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onFocus={(e) => e.currentTarget.select()}
                required
                autoFocus
                className="w-full px-3 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRenameTarget(null)}
                className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={busy || !newName.trim() || newName.trim() === renameTarget.analysis_name}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold cursor-pointer"
              >
                {busy ? 'Saving…' : 'Save'}
              </button>
            </div>
          </form>
        </Dialog>
      )}

      {/* Delete dialog */}
      {deleteTarget && (
        <Dialog titleId="delete-title" onClose={() => setDeleteTarget(null)}>
          <div className="p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1.5">
                <h4 id="delete-title" className="font-bold text-slate-900 text-sm">
                  Delete this analysis?
                </h4>
                <p className="text-xs text-slate-500 leading-relaxed">
                  <span className="font-semibold text-slate-700">{deleteTarget.analysis_name}</span> will
                  be permanently deleted, along with its scenarios, decisions and goals. This can’t be
                  undone.
                </p>
              </div>
            </div>
            {dialogError && (
              <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {dialogError}
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                autoFocus
                className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={busy}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-semibold shadow-xs cursor-pointer"
              >
                {busy ? 'Deleting…' : 'Delete analysis'}
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};