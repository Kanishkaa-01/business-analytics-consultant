import React, { useState, useEffect } from 'react';
import {
  Upload,
  Sparkles,
  ArrowRight,
  TrendingUp,
  MessageSquareText,
  Search,
  Target,
  Sliders,
  LineChart,
  Calendar,
  Clock,
  ShieldCheck,
  FileSpreadsheet,
  AlertTriangle,
  Activity,
  ClipboardCheck,
  CheckCircle2,
  ArrowUp,
  ChartNoAxesCombined,
} from 'lucide-react';
import { StoredAnalysisSummary } from '../types';
import { api } from '../services/api';

interface Props {
  onOpenUploadModal: () => void;
  onSeedSamples: () => void;
  isSeeding: boolean;
  onSelectAnalysis: (analysisId: string) => void;
  onOpenStoredAnalyses: () => void;
}

/* ---------- Small shared pieces ---------- */

const SectionHeader: React.FC<{ title: string; subtitle?: string; action?: React.ReactNode }> = ({
  title,
  subtitle,
  action,
}) => (
  <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold tracking-tight text-slate-900 text-balance">{title}</h2>
      {subtitle && <p className="mt-1.5 text-sm text-slate-600 leading-relaxed">{subtitle}</p>}
    </div>
    {action}
  </div>
);

const PremiumSectionHeader: React.FC<{
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}> = ({ title, subtitle, action }) => (
  <div className="rounded-2xl border border-slate-200/80 bg-white/80 px-5 py-4 sm:px-6 sm:py-5 shadow-sm shadow-slate-900/[0.03]">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="mt-0.5 h-7 w-1 shrink-0 rounded-full bg-blue-600"
          />

          <div className="min-w-0">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 text-balance">
              {title}
            </h2>

            {subtitle && (
              <p className="mt-1.5 text-sm sm:text-base leading-relaxed text-slate-500">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      </div>

      {action && (
        <div className="shrink-0 sm:pl-4">
          {action}
        </div>
      )}
    </div>
  </div>
);

// Color the health bar by score. Adjust thresholds to match how your engine scores health.
const healthTone = (score: number) => {
  if (score >= 70) return { bar: 'bg-emerald-500', text: 'text-emerald-700' };
  if (score >= 40) return { bar: 'bg-amber-500', text: 'text-amber-700' };
  return { bar: 'bg-rose-500', text: 'text-rose-700' };
};

/* Decorative product preview shown in the hero. Static, illustrative data only. */
const HeroPreview: React.FC = () => (
  <div aria-hidden="true" className="w-full max-w-md mx-auto lg:max-w-none">
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5 overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-200" />
          <span className="w-2.5 h-2.5 rounded-full bg-slate-200" />
          <span className="w-2.5 h-2.5 rounded-full bg-slate-200" />
        </div>
        <span className="text-[11px] font-medium text-slate-500">Business overview, sample preview</span>
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-3 gap-2.5">
          {[
            { label: 'Revenue', value: '1.24M', delta: '+8.2%', up: true },
            { label: 'Gross margin', value: '31.4%', delta: '-1.9 pts', up: false },
            { label: 'Health score', value: '82/100', delta: 'Good', up: true },
          ].map((k) => (
            <div key={k.label} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
              <div className="text-[11px] text-slate-500">{k.label}</div>
              <div className="text-base font-bold text-slate-900 mt-0.5">{k.value}</div>
              <div className={`text-[11px] font-semibold mt-0.5 ${k.up ? 'text-emerald-600' : 'text-rose-600'}`}>
                {k.delta}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-slate-200 px-3 pt-3 pb-2">
          <div className="text-[11px] font-medium text-slate-500 mb-1">Monthly revenue</div>
          <svg viewBox="0 0 300 90" className="w-full h-24" role="presentation">
            <defs>
              <linearGradient id="heroArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563eb" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0 70 L30 62 L60 66 L90 50 L120 54 L150 38 L180 42 L210 28 L240 32 L270 18 L300 22 L300 90 L0 90 Z"
              fill="url(#heroArea)"
            />
            <polyline
              points="0,70 30,62 60,66 90,50 120,54 150,38 180,42 210,28 240,32 270,18 300,22"
              fill="none"
              stroke="#2563eb"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <div>
            <div className="text-xs font-bold text-slate-900">Margin fell in one region after July</div>
            <div className="text-[11px] text-slate-600 mt-0.5">Supporting evidence is ready to review.</div>
          </div>
        </div>
      </div>
    </div>
    <p className="text-center text-[11px] text-slate-500 mt-3">Illustrative preview with sample numbers</p>
  </div>
);

/* ---------- Page ---------- */

export const HomePage: React.FC<Props> = ({
  onOpenUploadModal,
  onSeedSamples,
  isSeeding,
  onSelectAnalysis,
  onOpenStoredAnalyses,
}) => {
  const [recentAnalyses, setRecentAnalyses] = useState<StoredAnalysisSummary[]>([]);
  const [loadingRecent, setLoadingRecent] = useState<boolean>(true);

  useEffect(() => {
    loadRecent();
  }, []);

  const loadRecent = async () => {
    try {
      setLoadingRecent(true);
      const list = await api.listStoredAnalyses();
      // Keep up to 3 most recent
      setRecentAnalyses((list || []).slice(0, 3));
    } catch (e) {
      console.warn('Could not load recent analyses:', e);
      setRecentAnalyses([]);
    } finally {
      setLoadingRecent(false);
    }
  };

  const hasAnalyses = recentAnalyses.length > 0;

  const handleCapabilityClick = () => {
    if (hasAnalyses) {
      onSelectAnalysis(recentAnalyses[0].id);
    } else {
      onOpenUploadModal();
    }
  };

  const steps = [
    {
      step: 1,
      icon: Upload,
      title: 'Upload',
      desc: 'Add your sales, transaction, or operations data.',
      outputs: ['CSV and Excel files', 'Automatic column profiling'],
    },
    {
      step: 2,
      icon: Activity,
      title: 'Understand',
      desc: 'See how reliable the data is and how the business is performing.',
      outputs: ['Data quality check', 'Health score and KPIs'],
    },
    {
      step: 3,
      icon: Search,
      title: 'Investigate',
      desc: 'Find what changed, what may be driving it, and the evidence behind it.',
      outputs: ['Key findings', 'Likely drivers', 'Supporting evidence'],
    },
    {
      step: 4,
      icon: ClipboardCheck,
      title: 'Decide',
      desc: 'Test possible actions and keep a record of what you decide.',
      outputs: ['Recommendations', 'What-if scenarios', 'Decision log'],
    },
  ];

  const capabilityCards = [
    {
      id: 'overview',
      icon: TrendingUp,
      color: 'text-blue-600 bg-blue-50 border-blue-200',
      title: 'Business Overview',
      desc: 'Performance, key metrics, trends, and overall business health.',
      example: 'How is the business doing overall?',
    },
    {
      id: 'ask_data',
      icon: MessageSquareText,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
      title: 'Ask Your Data',
      desc: 'Ask questions about your dataset in plain language.',
      example: 'Which region’s margin dropped last quarter?',
    },
    {
      id: 'findings',
      icon: Search,
      color: 'text-amber-600 bg-amber-50 border-amber-200',
      title: 'Findings & Evidence',
      desc: 'Important observations, with the evidence that supports each one.',
      example: 'What changed, and what backs it up?',
    },
    {
      id: 'goals',
      icon: Target,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
      title: 'KPI Goals',
      desc: 'Track performance against the targets you define.',
      example: 'Are we on track for this quarter’s targets?',
    },
    {
      id: 'scenarios',
      icon: Sliders,
      color: 'text-purple-600 bg-purple-50 border-purple-200',
      title: 'Scenario Analysis',
      desc: 'Estimate the effect of changes with supported what-if scenarios.',
      example: 'What happens if we raise prices by 5%?',
    },
    {
      id: 'forecast',
      icon: LineChart,
      color: 'text-rose-600 bg-rose-50 border-rose-200',
      title: 'Forecast & Validation',
      desc: 'Trends and forecasts, with checks on how far to trust them.',
      example: 'Where is revenue heading, and how reliable is that?',
    },
  ];

  const trustPoints = [
    { icon: FileSpreadsheet, text: 'Easy data import' },
    { icon: ShieldCheck, text: 'Evidence-backed insights' },
    { icon: Sparkles, text: 'Try before you upload' },
  ];

  const focusRing =
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-20 animate-fade-in">
      {/* 1. Hero */}
      <section className="grid lg:grid-cols-2 gap-12 lg:gap-14 items-center">
        <div className="space-y-6 text-center lg:text-left">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-[1.1] text-balance">
            Turn business data into better decisions
          </h1>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl mx-auto lg:mx-0">
            Transform raw business data into clear insights, uncover what's changing, and explore potential outcomes before making your next move.
          </p>

          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-1">
            <button
              onClick={onOpenUploadModal}
              className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 motion-safe:transition-colors cursor-pointer ${focusRing}`}
            >
              <Upload className="w-4 h-4" />
              <span>Upload dataset</span>
            </button>
            <button
              onClick={onSeedSamples}
              disabled={isSeeding}
              className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 shadow-2xs motion-safe:transition-colors cursor-pointer disabled:opacity-50 ${focusRing}`}
            >
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>{isSeeding ? 'Loading sample data...' : 'Try with sample data'}</span>
            </button>
          </div>




          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-2 pt-3 w-full">
            {trustPoints.map(({ icon: Icon, text }) => (
              <div
                key={text}
                className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm shadow-slate-900/[0.03]"
              >
                <Icon
                  className="h-4 w-4 shrink-0 text-blue-600"
                  aria-hidden="true"
                />
                <span className="whitespace-nowrap text-xs font-medium text-slate-600">
                  {text}
                </span>
              </div>
            ))}
          </div>



        </div>

        <HeroPreview />
      </section>

      {/* 2. How it works */}
      <section className="rounded-3xl border border-slate-200 bg-white px-6 py-10 sm:px-12 sm:py-14 shadow-2xs space-y-8">
        <SectionHeader
          title="From raw data to a documented decision"
          subtitle="Four steps, each building on the one before it."
        />
        <div
          aria-hidden="true"
          className="h-px w-full bg-slate-200"
        />
        <ol>
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <li key={s.step} className="relative flex gap-5 sm:gap-8 pb-12 last:pb-0">
                {/* Vertical connector between steps */}
                {i < steps.length - 1 && (
                  <span aria-hidden="true" className="absolute left-6 top-16 bottom-3 w-px bg-slate-200" />
                )}

                <div className="relative z-10 w-12 h-12 shrink-0 rounded-2xl bg-blue-600 text-white shadow-md shadow-blue-500/20 flex items-center justify-center">
                  <Icon className="w-5 h-5" />
                </div>

                <div className="flex-1 min-w-0 grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] md:gap-12 items-start">
                  <div>
                    <p className="text-sm font-semibold text-blue-600">Step {s.step}</p>
                    <h3 className="mt-1 text-xl font-bold text-slate-900">{s.title}</h3>
                    <p className="mt-2 text-base text-slate-600 leading-relaxed max-w-md">{s.desc}</p>
                  </div>

                  <ul className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 space-y-3">
                    {s.outputs.map((o) => (
                      <li key={o} className="flex items-center gap-3 text-sm text-slate-700">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                        <span>{o}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      {/* 3. Tools */}
      <section className="space-y-6">
        <PremiumSectionHeader
          title="Tools for every stage of the decision"
          subtitle={
            hasAnalyses
              ? 'Explore your business performance, investigate findings, and evaluate your next move.'
              : 'Upload a dataset or load the sample data to unlock these tools.'
          }
        />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {capabilityCards.map((feat) => {
            const Icon = feat.icon;
            return (
              <button
                key={feat.id}
                type="button"
                onClick={handleCapabilityClick}
                className={`group text-left bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs hover:border-blue-300 hover:shadow-sm motion-safe:transition cursor-pointer flex flex-col gap-4 ${focusRing}`}
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${feat.color}`}>
                  <Icon className="w-5 h-5" />
                </div>

                <div className="space-y-1.5">
                  <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-700 motion-safe:transition-colors">
                    {feat.title}
                  </h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{feat.desc}</p>
                </div>

                <div className="mt-auto space-y-3">
                  <p className="text-sm text-slate-700 bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 italic">
                    “{feat.example}”
                  </p>
                  <span className="flex items-center gap-1 text-sm font-semibold text-blue-600">
                    {hasAnalyses ? 'Open in latest analysis' : 'Upload data to start'}
                    <ArrowRight className="w-4 h-4 motion-safe:transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* 4. Recent analyses */}
      <section className="space-y-6">
        <PremiumSectionHeader
          title="Recent analyses"
          subtitle="Continue where you left off or revisit previous business insights."
          action={
            <button
              type="button"
              onClick={onOpenStoredAnalyses}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 hover:text-blue-700 motion-safe:transition-colors self-start sm:self-auto cursor-pointer ${focusRing}`}
            >
              <span>View all analyses</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          }
        />

        {loadingRecent ? (
          <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center text-sm text-slate-600">
            Loading recent analyses...
          </div>
        ) : !hasAnalyses ? (
          <div className="p-10 bg-white rounded-2xl border border-dashed border-slate-300 text-center space-y-4">
            <Clock className="w-8 h-8 text-slate-400 mx-auto" />
            <div className="space-y-1">
              <p className="text-base font-semibold text-slate-800">No analyses yet</p>
              <p className="text-sm text-slate-600">Upload a dataset or load sample data to create your first one.</p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={onOpenUploadModal}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-2xs motion-safe:transition-colors cursor-pointer ${focusRing}`}
              >
                <Upload className="w-4 h-4" />
                <span>Upload dataset</span>
              </button>
              <button
                onClick={onSeedSamples}
                disabled={isSeeding}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 motion-safe:transition-colors cursor-pointer disabled:opacity-50 ${focusRing}`}
              >
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span>{isSeeding ? 'Loading sample data...' : 'Try with sample data'}</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recentAnalyses.map((an, idx) => {
              const rawScore = an.health_score;
              const score =
                rawScore !== null && rawScore !== undefined && Number.isFinite(Number(rawScore))
                  ? Number(rawScore)
                  : null;
              const tone = score !== null ? healthTone(score) : null;
              const showDataset = !!an.dataset_name && an.dataset_name !== an.analysis_name;

              return (
                <button
                  key={an.id}
                  type="button"
                  onClick={() => onSelectAnalysis(an.id)}
                  className={`group text-left bg-white rounded-2xl border border-slate-200 shadow-2xs hover:border-blue-300 hover:shadow-sm motion-safe:transition p-5 flex flex-col gap-4 cursor-pointer ${focusRing}`}
                >
                  {/* Title row */}
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 shrink-0 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3
                        className="text-base font-bold text-slate-900 leading-snug line-clamp-2"
                        title={an.analysis_name}
                      >
                        {an.analysis_name}
                      </h3>
                      {showDataset && (
                        <p className="text-sm text-slate-600 mt-0.5 line-clamp-1" title={an.dataset_name}>
                          {an.dataset_name}
                        </p>
                      )}
                    </div>
                    {idx === 0 && (
                      <span className="shrink-0 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-100 rounded-full px-2 py-0.5">
                        Latest
                      </span>
                    )}
                  </div>

                  {/* Health score */}
                  {score !== null && tone && (
                    <div>
                      <div className="flex items-baseline justify-between text-xs">
                        <span className="text-slate-600">Health score</span>
                        <span className={`font-bold ${tone.text}`}>{Math.round(score * 10) / 10}/100</span>
                      </div>
                      <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${tone.bar}`}
                          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Meta chips */}
                  {(an.target_column || an.dataset_version) && (
                    <div className="flex flex-wrap gap-2 text-xs text-slate-700">
                      {an.target_column && (
                        <span className="inline-flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-md px-2 py-1">
                          <Target className="w-3 h-3 text-slate-400" />
                          Metric: <b className="text-slate-900">{an.target_column}</b>
                        </span>
                      )}
                      {an.dataset_version && (
                        <span className="inline-flex items-center bg-slate-50 border border-slate-200 rounded-md px-2 py-1 font-mono">
                          v{an.dataset_version}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="mt-auto pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs text-slate-600">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      {new Date(an.created_at).toLocaleDateString(undefined, {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                    <span className="flex items-center gap-1 text-sm font-semibold text-blue-600">
                      Open analysis
                      <ArrowRight className="w-4 h-4 motion-safe:transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* 5. Closing call to action (shown once the user has analyses) */}
      {hasAnalyses && (
        <section className="rounded-3xl bg-slate-900 px-6 py-10 sm:px-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left max-w-xl">
            <h2 className="text-2xl font-bold tracking-tight text-white text-balance">
              Ready to analyze another dataset?
            </h2>
            <p className="mt-2 text-sm text-slate-300 leading-relaxed">
              Upload a new file to get its data quality check, key findings, and what-if scenarios.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={onOpenUploadModal}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-blue-600 hover:bg-blue-500 text-white motion-safe:transition-colors cursor-pointer ${focusRing}`}
            >
              <Upload className="w-4 h-4" />
              <span>Upload dataset</span>
            </button>
            <button
              onClick={onOpenStoredAnalyses}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white border border-slate-600 hover:bg-slate-800 motion-safe:transition-colors cursor-pointer ${focusRing}`}
            >
              <span>Browse stored analyses</span>
            </button>
          </div>
        </section>
      )}


      {/* 6. Footer — Premium Minimalist */}
      <footer className="mt-10 border-t border-slate-200 pt-5 pb-4">
        {/* Main footer row */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          {/* Brand message */}
          <div className="flex min-w-0 items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50">
              <ChartNoAxesCombined
                className="h-5 w-5 text-blue-600"
                aria-hidden="true"
              />
            </div>

            <div className="min-w-0">
              <h2 className="text-sm font-semibold leading-5 text-slate-800">
                Insights backed by evidence
              </h2>

              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                Turn your business data into actionable insights, with
                supporting evidence to help you understand every finding.
              </p>
            </div>
          </div>

          {/* Back to top */}
          <button
            type="button"
            onClick={() =>
              window.scrollTo({
                top: 0,
                behavior: window.matchMedia(
                  "(prefers-reduced-motion: reduce)"
                ).matches
                  ? "auto"
                  : "smooth",
              })
            }
            className={`inline-flex shrink-0 items-center gap-1.5 self-start
        rounded-md text-sm font-medium text-slate-500
        transition-colors hover:text-blue-600
        focus-visible:outline-none focus-visible:ring-2
        focus-visible:ring-blue-500 focus-visible:ring-offset-2
        sm:self-center ${focusRing}`}
          >
            <span>Back to top</span>
            <ArrowUp className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Bottom copyright row */}
        <div className="mt-5 flex flex-col gap-2 border-t border-slate-100 pt-4
    sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-slate-400">
            &copy; {new Date().getFullYear()} Business Analytics Consultant
          </p>

          <p className="text-xs leading-5 text-slate-400">
            From data to better decisions.
          </p>
        </div>
      </footer>

    </div>
  );
};