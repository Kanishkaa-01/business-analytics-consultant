import React from 'react';
import ReactECharts from 'echarts-for-react';
import { SimulationOutcome } from '../../types';

interface Props {
  outcome: SimulationOutcome;
}

export const SimulationChart: React.FC<Props> = ({ outcome }) => {
  const isNoChange =
    outcome.revenue_delta === 0 &&
    outcome.profit_delta === 0 &&
    (outcome.margin_delta_pct === 0 ||
      outcome.margin_delta_pct === undefined);

  // Baseline and simulated margins
  const baseMargin =
    outcome.baseline_margin_pct ??
    (outcome.baseline_revenue > 0
      ? (outcome.baseline_profit / outcome.baseline_revenue) * 100
      : 0);

  const simMargin =
    outcome.simulated_margin_pct ??
    (outcome.simulated_revenue > 0
      ? (outcome.simulated_profit / outcome.simulated_revenue) * 100
      : 0);

  // Common chart helper
  const getBarOption = (
    title: string,
    unit: '$' | '%',
    baselineVal: number,
    simulatedVal: number,
    deltaVal: number
  ) => {
    const isGain = deltaVal >= 0;

    return {
      title: {
        text: title,

        subtext: `Shift: ${
          isGain ? '+' : ''
        }${unit === '$' ? '$' : ''}${deltaVal.toLocaleString(
          undefined,
          {
            maximumFractionDigits: 1,
          }
        )}${unit === '%' ? '%' : ''}`,

        // Center title and subtitle
        left: 'center',
        top: 0,

        textStyle: {
          fontSize: 13,
          fontWeight: 'bold',
          color: '#1e293b',
        },

        subtextStyle: {
          fontSize: 11,
          fontWeight: 'bold',
          color: isNoChange
            ? '#64748b'
            : isGain
              ? '#10b981'
              : '#ef4444',
        },
      },

      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },

        formatter: (params: any) => {
          let s = `<b>${params[0].name}</b><br/>`;

          params.forEach((p: any) => {
            s += `${p.marker} ${p.seriesName}: <b>${
              unit === '$' ? '$' : ''
            }${Number(p.value).toLocaleString(undefined, {
              maximumFractionDigits: 1,
            })}${unit === '%' ? '%' : ''}</b><br/>`;
          });

          return s;
        },
      },

      // Centered legend placed BELOW the Shift subtitle
      legend: {
        data: ['Baseline', 'Simulated'],
        top: 43,
        left: 'center',

        itemWidth: 22,
        itemHeight: 10,
        itemGap: 10,

        textStyle: {
          fontSize: 10,
          color: '#64748b',
        },
      },

      // Creates enough space for:
      // Title → Shift → Legend → Chart
      grid: {
        left: '8%',
        right: '5%',
        bottom: '12%',
        top: '78px',
        containLabel: true,
      },

      xAxis: {
        type: 'category',

        data: ['Current vs Simulated'],

        axisLabel: {
          color: '#64748b',
          fontSize: 10,
        },

        axisTick: {
          show: false,
        },
      },

      yAxis: {
        type: 'value',

        axisLabel: {
          fontSize: 10,

          formatter: (v: number) =>
            `${unit === '$' ? '$' : ''}${
              v >= 1000
                ? `${(v / 1000).toFixed(0)}k`
                : v
            }${unit === '%' ? '%' : ''}`,
        },

        splitLine: {
          lineStyle: {
            color: '#f1f5f9',
          },
        },
      },

      series: [
        {
          name: 'Baseline',
          type: 'bar',

          barMaxWidth: 40,

          data: [
            Number(baselineVal.toFixed(1)),
          ],

          itemStyle: {
            color: '#94a3b8',
            borderRadius: [4, 4, 0, 0],
          },
        },

        {
          name: 'Simulated',
          type: 'bar',

          barMaxWidth: 40,

          data: [
            Number(simulatedVal.toFixed(1)),
          ],

          itemStyle: {
            color: isNoChange
              ? '#64748b'
              : isGain
                ? '#10b981'
                : '#ef4444',

            borderRadius: [4, 4, 0, 0],
          },
        },
      ],
    };
  };

  // Revenue chart
  const revenueOption = getBarOption(
    '1. Gross Revenue ($)',
    '$',
    outcome.baseline_revenue,
    outcome.simulated_revenue,
    outcome.revenue_delta
  );

  // Profit chart
  const profitOption = getBarOption(
    '2. Net Profit ($)',
    '$',
    outcome.baseline_profit,
    outcome.simulated_profit,
    outcome.profit_delta
  );

  // Profit margin chart
  const marginOption = getBarOption(
    '3. Profit Margin (%)',
    '%',
    baseMargin,
    simMargin,
    outcome.margin_delta_pct ??
      (simMargin - baseMargin)
  );

  return (
    <div className="space-y-4">

      {/* Neutral baseline message */}
      {isNoChange && (
        <div className="p-3 bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-600 text-center font-semibold">
          No changes have been applied. Simulation matches the baseline.
        </div>
      )}

      {/* Three comparison charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* Chart 1: Revenue */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <ReactECharts
            option={revenueOption}
            style={{
              height: 260,
              width: '100%',
            }}
          />
        </div>

        {/* Chart 2: Net Profit */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <ReactECharts
            option={profitOption}
            style={{
              height: 260,
              width: '100%',
            }}
          />
        </div>

        {/* Chart 3: Profit Margin */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <ReactECharts
            option={marginOption}
            style={{
              height: 260,
              width: '100%',
            }}
          />
        </div>

      </div>
    </div>
  );
};