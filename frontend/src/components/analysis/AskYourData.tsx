import React, { useState, useEffect, useMemo, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  Send,
  Search,
  AlertCircle,
  CornerDownRight,
  ChevronDown,
  Trash2,
  MessageSquareText,
} from 'lucide-react';
import { api } from '../../services/api';
import { AskDataResponse } from '../../types';
import { AdaptiveVisualization } from '../charts/AdaptiveVisualization';

interface Props {
  datasetId: string;
}

interface HistoryItem {
  id: number;
  question: string;
  response: AskDataResponse;
}

/* ---------- helpers ---------- */

// Renders **bold** and `code` as React nodes (no dangerouslySetInnerHTML).
const renderInline = (text: string): React.ReactNode[] => {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={i} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={i} className="bg-slate-200/70 px-1 py-0.5 rounded text-xs font-mono">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
};

const formatValue = (val: any): string =>
  typeof val === 'number'
    ? val.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : String(val ?? '');

const prettifyKey = (key: string): string => {
  const spaced = key.replace(/_/g, ' ').trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
};

const getVisualPoints = (response: AskDataResponse) => {
  if (!response.table_data || response.table_data.length < 2) return null;
  const firstRow = response.table_data[0];
  const keys = Object.keys(firstRow);
  const numKey = keys.find((k) => typeof firstRow[k] === 'number');
  const labelKey = keys.find((k) => k !== numKey) || keys[0];
  if (!numKey) return null;
  return {
    points: response.table_data.map((r) => ({
      label: String(r[labelKey] ?? ''),
      value: Number(r[numKey] ?? 0),
    })),
    metricName: numKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  };
};

const GROUP_ORDER = ['Overview', 'Breakdowns', 'Rankings', 'Trends'] as const;

const groupQuestions = (questions: string[]) => {
  const groups: Record<string, string[]> = {
    Overview: [],
    Breakdowns: [],
    Rankings: [],
    Trends: [],
  };
  questions.forEach((q) => {
    if (/trend|over time|monthly|weekly|daily|growth/i.test(q)) groups.Trends.push(q);
    else if (/\btop\b|bottom|highest|lowest|best|worst|rank/i.test(q)) groups.Rankings.push(q);
    else if (/distribution|breakdown|\bby\b|across/i.test(q)) groups.Breakdowns.push(q);
    else groups.Overview.push(q);
  });
  return GROUP_ORDER.map((name) => ({ name, items: groups[name] })).filter(
    (g) => g.items.length > 0
  );
};

/* ---------- result card ---------- */

const ResultCard: React.FC<{
  item: HistoryItem;
  isLatest: boolean;
  loading: boolean;
  onAsk: (q: string) => void;
}> = ({ item, isLatest, loading, onAsk }) => {
  const { response } = item;
  const [showCalc, setShowCalc] = useState(false);

  const rows = response.table_data || [];
  const isSingleRow = rows.length === 1;
  const visualPoints = useMemo(() => getVisualPoints(response), [response]);
  const hasChart = !isSingleRow && (!!visualPoints?.points.length || !!response.echarts_spec);
  const [showTable, setShowTable] = useState(!hasChart);

  return (
    <article className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden animate-fade-in">
      {/* Question */}
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-start gap-2.5">
        <MessageSquareText className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
        <h3 className="text-sm font-semibold text-slate-800 leading-snug">
          {response.query || item.question}
        </h3>
      </div>

      <div className="p-5 space-y-5">
        {/* Answer */}
        <p className="text-[15px] leading-relaxed text-slate-800 max-w-3xl">
          {renderInline(response.answer_text)}
        </p>

        {/* Single-row results: show values as stat tiles */}
        {isSingleRow && (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3">
            {Object.entries(rows[0])
              .slice(0, 4)
              .map(([key, val]) => (
                <div key={key} className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3">
                  <div className="text-xs text-slate-500 font-medium">{prettifyKey(key)}</div>
                  <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums break-words">
                    {formatValue(val)}
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Chart */}
        {hasChart && (
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
            {visualPoints && visualPoints.points.length > 0 ? (
              <AdaptiveVisualization
                data={visualPoints.points}
                metricName={visualPoints.metricName}
                height={260}
              />
            ) : (
              <ReactECharts option={response.echarts_spec} style={{ height: 260 }} />
            )}
          </div>
        )}

        {/* Data table */}
        {rows.length > 1 && (
          <div>
            <button
              onClick={() => setShowTable((v) => !v)}
              aria-expanded={showTable}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
            >
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform ${showTable ? 'rotate-180' : ''}`}
              />
              {showTable ? 'Hide data' : `View data (${rows.length} rows)`}
            </button>

            {showTable && (
              <div className="mt-2 overflow-auto max-h-80 rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-600 font-semibold sticky top-0">
                    <tr>
                      {Object.keys(rows[0]).map((colKey) => (
                        <th
                          key={colKey}
                          className={`px-4 py-2.5 border-b border-slate-200 whitespace-nowrap ${
                            typeof rows[0][colKey] === 'number' ? 'text-right' : ''
                          }`}
                        >
                          {prettifyKey(colKey)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-50/80">
                        {Object.values(row).map((val: any, cIdx) => (
                          <td
                            key={cIdx}
                            className={`px-4 py-2 text-slate-700 ${
                              typeof val === 'number' ? 'text-right tabular-nums font-medium' : ''
                            }`}
                          >
                            {formatValue(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* How it was calculated */}
        {response.explanation && (
          <div className="border-t border-slate-100 pt-3">
            <button
              onClick={() => setShowCalc((v) => !v)}
              aria-expanded={showCalc}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
            >
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform ${showCalc ? 'rotate-180' : ''}`}
              />
              How this was calculated
            </button>
            {showCalc && (
              <p className="mt-2 text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 max-w-3xl">
                {response.explanation}
              </p>
            )}
          </div>
        )}

        {/* Follow-ups (latest answer only) */}
        {isLatest && response.suggested_followups && response.suggested_followups.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500">
              <CornerDownRight className="w-3 h-3 text-slate-400" />
              Ask next
            </div>
            <div className="flex flex-wrap gap-2">
              {response.suggested_followups.map((fQ, fIdx) => (
                <button
                  key={fIdx}
                  onClick={() => onAsk(fQ)}
                  disabled={loading}
                  className="px-3 py-1.5 rounded-full bg-blue-50 hover:bg-blue-100 disabled:opacity-50 text-blue-700 text-xs font-medium border border-blue-200/60 transition-colors cursor-pointer"
                >
                  {fQ}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
};

/* ---------- main component ---------- */

export const AskYourData: React.FC<Props> = ({ datasetId }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load suggestions and reset state when the dataset changes
  useEffect(() => {
    if (!datasetId) return;
    let cancelled = false;
    setHistory([]);
    setError(null);
    setSuggestedQuestions([]);
    api
      .getSuggestedQuestions(datasetId)
      .then((qs) => {
        if (!cancelled) setSuggestedQuestions(qs);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  const handleAsk = async (questionText: string) => {
    const q = questionText.trim();
    if (!q || loading) return;
    setLoading(true);
    setPending(q);
    setError(null);
    setQuery('');
    try {
      const res = await api.askData(datasetId, q);
      setHistory((prev) => [{ id: ++idRef.current, question: q, response: res }, ...prev]);
    } catch (err: any) {
      setError(err.message || 'Failed to process question.');
      setQuery(q); // give the question back so it can be edited and retried
    } finally {
      setLoading(false);
      setPending(null);
      inputRef.current?.focus();
    }
  };

  const groupedSuggestions = useMemo(() => groupQuestions(suggestedQuestions), [suggestedQuestions]);
  const showGroupLabels = groupedSuggestions.length > 1;

  return (
    <div className="space-y-5">
      {/* Ask box */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-4 sm:p-5 space-y-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(query);
          }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question, e.g. “What are the top 5 countries by revenue?”"
              disabled={loading}
              aria-label="Ask a question about your dataset"
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm placeholder:text-slate-400 disabled:bg-slate-50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold flex items-center gap-2 transition-colors shadow-xs cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Ask</span>
          </button>
        </form>

        {error && (
          <div
            role="alert"
            className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-700"
          >
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Suggested questions (shown until the first answer) */}
        {history.length === 0 && !pending && groupedSuggestions.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-800">Try asking</h2>
            <div className="space-y-2.5">
              {groupedSuggestions.map((group) => (
                <div key={group.name} className="flex flex-col sm:flex-row sm:items-start gap-1.5 sm:gap-3">
                  {showGroupLabels && (
                    <div className="sm:w-24 shrink-0 text-xs font-medium text-slate-500 sm:pt-1.5">
                      {group.name}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {group.items.map((sq, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleAsk(sq)}
                        disabled={loading}
                        className="px-3 py-1.5 rounded-full bg-slate-50 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700 text-xs font-medium border border-slate-200 transition-colors text-left cursor-pointer disabled:opacity-50"
                      >
                        {sq}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {(history.length > 0 || pending) && (
        <div className="space-y-4">
          {history.length > 0 && (
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">
                {history.length} {history.length === 1 ? 'answer' : 'answers'}
              </h2>
              <button
                onClick={() => setHistory([])}
                className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-red-600 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear all
              </button>
            </div>
          )}

          {/* Loading placeholder for the question in flight */}
          {pending && (
            <article
              aria-busy="true"
              className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden"
            >
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-start gap-2.5">
                <MessageSquareText className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
                <h3 className="text-sm font-semibold text-slate-800 leading-snug">{pending}</h3>
              </div>
              <div className="p-5 space-y-3 animate-pulse">
                <div className="h-3.5 bg-slate-200 rounded w-3/4" />
                <div className="h-3.5 bg-slate-200 rounded w-1/2" />
                <div className="h-40 bg-slate-100 rounded-xl mt-4" />
              </div>
            </article>
          )}

          {history.map((item, idx) => (
            <ResultCard
              key={item.id}
              item={item}
              isLatest={idx === 0}
              loading={loading}
              onAsk={handleAsk}
            />
          ))}
        </div>
      )}
    </div>
  );
};