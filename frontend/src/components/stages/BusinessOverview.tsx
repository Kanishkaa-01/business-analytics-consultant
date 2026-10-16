import React from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  DollarSign,
  Receipt,
  Users,
  Percent,
  PercentSquare,
  Gauge,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Clock,
  Sparkles,
  Layers,
  Search
} from 'lucide-react';
import { BusinessHealthOverview, FindingItem } from '../../types';
import { TimelineChart } from '../charts/TimelineChart';
import { TermTooltip } from '../common/TermTooltip';

interface Props {
  health: BusinessHealthOverview;
  onNavigateNext: () => void;
  analysisId?: string;
  datasetId?: string;
  findings?: FindingItem[];
  onOpenWhyResult?: (resultType: string, resultId: string) => void;
  onOpenDrillDown?: (dimension: string) => void;
}

export const BusinessOverview: React.FC<Props> = ({
  health,
  onNavigateNext,
  analysisId,
  datasetId,
  findings = [],
  onOpenWhyResult,
  onOpenDrillDown,
}) => {
  const metrics = health.overview_metrics || {};

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Strong':
        return 'text-emerald-700 bg-emerald-50 border-emerald-300';
      case 'Stable':
        return 'text-blue-700 bg-blue-50 border-blue-300';
      case 'Vulnerable':
        return 'text-amber-700 bg-amber-50 border-amber-300';
      default:
        return 'text-rose-700 bg-rose-50 border-rose-300';
    }
  };

  // Section 9: 4+4 Logical KPI Grouping (Financial Performance, Commercial Activity)
  const overviewCards = [
    // Row 1 — Financial Performance
    {
      id: 'rev',
      title: 'Total Revenue',
      category: 'Financial Performance',
      termKey: 'revenue',
      icon: DollarSign,
      value:
        metrics.total_revenue !== null && metrics.total_revenue !== undefined
          ? `$${metrics.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          : null,
      note: 'Total recognized sales volume'
    },
    {
      id: 'profit',
      title: 'Total Profit',
      category: 'Financial Performance',
      termKey: 'profit',
      icon: DollarSign,
      value:
        metrics.total_profit !== null && metrics.total_profit !== undefined
          ? `$${metrics.total_profit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          : null,
      note: 'Net commercial return after costs'
    },
    {
      id: 'margin',
      title: 'Profit Margin (%)',
      category: 'Financial Performance',
      termKey: 'profit_margin',
      icon: Percent,
      value:
        metrics.profit_margin_pct !== null && metrics.profit_margin_pct !== undefined
          ? `${metrics.profit_margin_pct.toFixed(2)}%`
          : null,
      note: 'Profit as percentage of revenue'
    },
    {
      id: 'growth',
      title: 'Growth Rate (%)',
      category: 'Financial Performance',
      termKey: 'growth_rate',
      icon: TrendingUp,
      value:
        metrics.growth_rate_pct !== null && metrics.growth_rate_pct !== undefined
          ? `${metrics.growth_rate_pct > 0 ? '+' : ''}${metrics.growth_rate_pct.toFixed(2)}%`
          : null,
      note: 'Period-over-period performance change'
    },

    // Row 2 — Commercial Activity
    {
      id: 'txns',
      title: 'Transactions / Records',
      category: 'Commercial Activity',
      termKey: 'revenue',
      icon: Receipt,
      value:
        metrics.transactions_count !== null && metrics.transactions_count !== undefined
          ? metrics.transactions_count.toLocaleString()
          : null,
      note: 'Total recorded commercial entries'
    },
    {
      id: 'aov',
      title: 'Average Order Value',
      category: 'Commercial Activity',
      termKey: 'revenue',
      icon: Receipt,
      value:
        metrics.average_order_value !== null && metrics.average_order_value !== undefined
          ? `$${metrics.average_order_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          : null,
      note: 'Mean value per transaction'
    },
    {
      id: 'cust',
      title: 'Customers / Accounts',
      category: 'Commercial Activity',
      termKey: 'revenue',
      icon: Users,
      value:
        metrics.unique_customers !== null && metrics.unique_customers !== undefined
          ? metrics.unique_customers.toLocaleString()
          : null,
      note:
        metrics.unique_customers !== null && metrics.unique_customers !== undefined
          ? 'Distinct customer accounts'
          : (health.vital_signs?.customer_segment_categories_present
              ? 'No customer-level identifier detected'
              : 'No customer-level data detected'),
      hasSegmentation: !!health.vital_signs?.customer_segment_categories_present
    },
    {
      id: 'discount',
      title: 'Average Discount (%)',
      category: 'Commercial Activity',
      termKey: 'profit',
      icon: PercentSquare,
      value:
        metrics.average_discount_pct !== null && metrics.average_discount_pct !== undefined
          ? `${metrics.average_discount_pct.toFixed(2)}%`
          : null,
      note: 'Mean concession rate applied'
    }
  ];

  return (
    <div className="space-y-8">

      {/* 1. Header Card & Business Health */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Business Overview & Operational Health
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            {health.executive_summary}
          </p>
        </div>

        {/* Executive Health Score Badge */}
        <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 shrink-0">
          <div className="text-right">
            <div className="text-xs uppercase font-bold text-slate-500">Health Index</div>
            <div className="text-3xl font-extrabold text-slate-900">
              {health.overall_health_score}
              <span className="text-lg font-normal text-slate-500">/100</span>
            </div>
          </div>
          <div
            className={`px-3 py-2 rounded-xl border text-sm font-bold shadow-inner ${getStatusColor(
              health.overall_status
            )}`}
          >
            {health.overall_status}
          </div>
          {onOpenWhyResult && (
            <button
              onClick={() => onOpenWhyResult('health_score', 'overall')}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors cursor-pointer"
              title="See transparent calculation methodology and contributing factors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Why this score?</span>
            </button>
          )}
        </div>
      </div>

      {/* Primary Observed Pressure Callout */}
      {health.primary_pressure && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3.5 text-xs shadow-2xs ${
            health.primary_pressure.impact === 'Primary Drag'
              ? 'bg-rose-50/90 border-rose-200 text-rose-900'
              : 'bg-emerald-50/90 border-emerald-200 text-emerald-900'
          }`}
        >
          {health.primary_pressure.impact === 'Primary Drag' ? (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <div className="space-y-1 flex-1">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="font-bold text-sm">
                Primary Observed Pressure: {health.primary_pressure.component}
              </span>
              <span
                className={`font-extrabold px-2.5 py-0.5 rounded text-[11px] self-start sm:self-auto border ${
                  health.primary_pressure.impact === 'Primary Drag'
                    ? 'bg-white border-rose-200 text-rose-700'
                    : 'bg-white border-emerald-200 text-emerald-700'
                }`}
              >
                Dimension Health: {health.primary_pressure.score}/100
              </span>
            </div>
            <p className="text-slate-700 leading-relaxed font-medium">
              {health.primary_pressure.description}
            </p>
          </div>
        </div>
      )}

      {/* 2. Key Business Metrics (4+4 Grid) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Key Business Metrics
          </h3>
          <span className="text-xs text-slate-500">
            Automatically detected from dataset schema
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {overviewCards.map((card) => {
            const Icon = card.icon;
            const hasVal = card.value !== null;
            return (
              <div
                key={card.id}
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between text-slate-500 mb-2">
                    <TermTooltip termKey={card.termKey} label={card.title} />
                    <Icon className="w-4 h-4 text-slate-400 shrink-0" />
                  </div>
                  {hasVal ? (
                    <div className="text-2xl font-extrabold text-slate-900">
                      {card.value}
                    </div>
                  ) : (
                    <div className="text-xl font-bold text-slate-400 py-1">
                      Not Available
                    </div>
                  )}
                  {/* Segmentation Badge if segmentation exists but no customer ID */}
                  {card.id === 'cust' && !hasVal && card.hasSegmentation && (
                    <div className="text-[10px] text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded font-medium mt-1 inline-block">
                      Customer Segmentation: Available
                    </div>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 border-t border-slate-100 pt-2">
                  {card.note}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Main Business Visualizations (Clean 2-Column Layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">   
        {/* Left: Trend Timeline Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3 flex flex-col">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              <span>Revenue & Volume Progression</span>
            </h4>
            <span className="text-[11px] text-slate-500">Observation Trend</span>
          </div>

          {health.timeline_series && health.timeline_series.length > 0 ? (
            <TimelineChart
              data={health.timeline_series}
              metricName="Total Revenue / Volume"
            />
          ) : (
            <div className="py-16 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              Temporal trend timeline not available for this dataset structure.
            </div>
          )}
        </div>

        {/* Right: Health Component Breakdown Table */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3 flex flex-col h-fit">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-indigo-600" />
              <span>Health Component Breakdown</span>
            </h4>
            <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
              Total: {health.overall_health_score}/100
            </span>
          </div>

          {health.health_breakdown && health.health_breakdown.length > 0 ? (
            <div className="overflow-x-auto border border-slate-200 rounded-lg w-full">
              <table className="w-full text-left text-[11px] text-slate-700">
                <thead className="bg-slate-50 text-[10px] font-bold text-slate-600 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2 px-3">Dimension</th>
                    <th className="py-2 px-3">Score</th>
                    <th className="py-2 px-3">Weight</th>
                    <th className="py-2 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[11px]">
                  {health.health_breakdown.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2 px-3 font-semibold text-slate-800">{item.component}</td>
                      <td className="py-2 px-3 font-bold text-slate-900">{item.normalized_score}/100</td>
                      <td className="py-2 px-3 text-slate-600">{item.weight_pct}%</td>
                      <td className="py-2 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                            item.status === 'Healthy'
                              ? 'bg-emerald-100 text-emerald-800'
                              : item.status === 'Stable'
                              ? 'bg-blue-100 text-blue-800'
                              : item.status === 'Vulnerable'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              Component breakdown not available.
            </div>
          )}
        </div>
      </div>

      {/* 4. Key Findings Preview Cards */}
      {findings && findings.length > 0 && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Search className="w-4 h-4 text-amber-600" />
                <span>Key Findings Preview</span>
              </h3>
              <p className="text-xs text-slate-500">
                Core statistical anomalies and variances identified for executive attention
              </p>
            </div>
            <button
              onClick={onNavigateNext}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
            >
              <span>View All Findings ({findings.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {findings.slice(0, 3).map((f, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-slate-50 transition-colors space-y-2 text-xs flex flex-col justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase text-slate-400">
                      {f.metric}
                    </span>
                    <span
                      className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                        f.type === 'Problem'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {f.type}
                    </span>
                  </div>
                  <h4 className="font-bold text-slate-900 line-clamp-1">{f.title}</h4>
                  <div className="text-slate-600 font-semibold">
                    Difference: <span className={f.type === 'Problem' ? 'text-rose-600' : 'text-emerald-600'}>{f.difference}</span>
                  </div>
                </div>

                <button
                  onClick={onNavigateNext}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800 pt-1 cursor-pointer"
                >
                  <span>View Finding</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Phase Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Stage</div>
          <div className="text-sm font-semibold">Examine Specific Findings & Performance Issues</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
        >
          <span>View Findings</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export { BusinessOverview as Stage2_BusinessOverview };

