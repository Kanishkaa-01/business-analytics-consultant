
import { ScenarioComparisonReport } from '../types';

/**
 * Builds deterministic Apache ECharts configuration for Scenario Comparison.
 * Compares Revenue, Net Profit, and Profit Margin % across Baseline and evaluated scenarios.
 * Properly defines Cartesian2D coordinates (xAxis + yAxis) and handles formatting.
 */
export function buildComparisonChartOption(
  comparisonReport: ScenarioComparisonReport | null
): Record<string, any> {
  if (
    !comparisonReport ||
    !Array.isArray(comparisonReport.scenarios) ||
    comparisonReport.scenarios.length === 0
  ) {
    return {};
  }

  const names = comparisonReport.scenarios.map((s) => s.name || 'Scenario');
  const revs = comparisonReport.scenarios.map((s) => Number(s.revenue) || 0);
  const profs = comparisonReport.scenarios.map((s) => Number(s.profit) || 0);
  const margins = comparisonReport.scenarios.map(
    (s) => Number(s.profit_margin_pct) || 0
  );

  const maxMargin = Math.max(
    100,
    ...margins.map((m) => Math.ceil(m / 10) * 10)
  );

  return {
    title: {
      text: 'Scenario Financial Comparison',
      subtext:
        'Revenue, Net Profit, and Profit Margin across evaluated scenarios',
      left: 'center',
      top: 8,
      itemGap: 6,
      textStyle: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#1e293b',
      },
      subtextStyle: {
        fontSize: 11,
        color: '#64748b',
        lineHeight: 16,
      },
    },

    // Light-mode tooltip
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: {
          color: 'rgba(148, 163, 184, 0.12)',
        },
      },
      backgroundColor: '#FFFFFF',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      padding: [10, 12],
      textStyle: {
        color: '#1E293B',
        fontSize: 12,
      },
      extraCssText:
        'box-shadow: 0 4px 16px rgba(15, 23, 42, 0.10); border-radius: 8px;',
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) {
          return '';
        }

        const title = params[0].axisValueLabel || params[0].name;

        let html = `<div style="font-weight:bold;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #E2E8F0;color:#1E293B;">${title}</div>`;

        params.forEach((p: any) => {
          const colorDot = `<span style="display:inline-block;margin-right:6px;border-radius:50%;width:8px;height:8px;background-color:${p.color};"></span>`;

          const valStr =
            p.seriesName === 'Profit Margin %'
              ? `${Number(p.value).toFixed(2)}%`
              : `$${Number(p.value).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`;

          html += `<div style="display:flex;justify-content:space-between;gap:16px;margin-top:3px;">
            <span style="color:#64748B;">${colorDot}${p.seriesName}:</span>
            <span style="font-family:monospace;font-weight:bold;color:#1E293B;">${valStr}</span>
          </div>`;
        });

        return html;
      },
    },

    legend: {
      data: ['Revenue', 'Net Profit', 'Profit Margin %'],
      top: 54,
      left: 'center',
      itemGap: 16,
      itemWidth: 12,
      itemHeight: 10,
      textStyle: {
        fontSize: 11,
        color: '#475569',
      },
    },

    grid: {
      left: '4%',
      right: '5%',
      bottom: '10%',
      top: 90,
      containLabel: true,
    },

    xAxis: {
      type: 'category',
      data: names,
      axisLine: {
        lineStyle: {
          color: '#cbd5e1',
        },
      },
      axisTick: {
        alignWithLabel: true,
      },
      axisLabel: {
        fontSize: 11,
        color: '#475569',
        interval: 0,
        formatter: (val: string) => {
          if (!val) return '';
          return val.length > 18 ? `${val.slice(0, 16)}…` : val;
        },
      },
    },

    yAxis: [
      {
        type: 'value',
        name: 'Amount ($)',
        nameTextStyle: {
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#f1f5f9',
          },
        },
        axisLabel: {
          formatter: (v: number) => {
            if (Math.abs(v) >= 1_000_000) {
              return `$${(v / 1_000_000).toFixed(1)}M`;
            }
            if (Math.abs(v) >= 1_000) {
              return `$${(v / 1_000).toFixed(0)}k`;
            }
            return `$${v}`;
          },
          fontSize: 10,
          color: '#64748b',
        },
      },
      {
        type: 'value',
        name: 'Margin (%)',
        nameTextStyle: {
          color: '#64748b',
          fontSize: 11,
        },
        min: 0,
        max: maxMargin,
        splitLine: {
          show: false,
        },
        axisLabel: {
          formatter: '{value}%',
          fontSize: 10,
          color: '#64748b',
        },
      },
    ],

    series: [
      {
        name: 'Revenue',
        type: 'bar',
        data: revs,
        barMaxWidth: 40,
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: 'Net Profit',
        type: 'bar',
        data: profs,
        barMaxWidth: 40,
        itemStyle: {
          color: '#10b981',
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: 'Profit Margin %',
        type: 'line',
        yAxisIndex: 1,
        data: margins,
        lineStyle: {
          color: '#f59e0b',
          width: 2.5,
        },
        itemStyle: {
          color: '#f59e0b',
        },
        symbol: 'circle',
        symbolSize: 6,
      },
    ],
  };
}
