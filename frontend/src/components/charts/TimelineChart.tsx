import React from 'react';
import ReactECharts from 'echarts-for-react';

interface Props {
  data: Array<{
    period: string;
    metric_sum: number;
    metric_mean: number;
    count: number;
  }>;
  metricName: string;
  aggregationType?: 'sum' | 'mean';
  unit?: string;
}

export const TimelineChart: React.FC<Props> = ({
  data,
  metricName,
  aggregationType = 'sum',
  unit = '',
}) => {
  if (!data || data.length === 0) return null;

  const periods = data.map((d) => d.period);
  const values = aggregationType === 'mean' ? data.map((d) => d.metric_mean) : data.map((d) => d.metric_sum);
  const displayName = aggregationType === 'mean' ? `${metricName} (Average)` : `${metricName} (Total)`;

  const option = {
    title: {
      text: `Historical Progression: ${metricName}`,
      subtext: `Supporting Evidence: Baseline vs Recent Period Trajectory (${aggregationType === 'mean' ? 'Average' : 'Aggregate Sum'})`,
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' },
      subtextStyle: { fontSize: 11, color: '#64748b' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const p = params[0];
        const val = Number(p.value);
        let formattedVal = val.toLocaleString();
        if (unit === '$') {
          formattedVal = `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        } else if (unit === '%') {
          formattedVal = `${val.toFixed(2)}%`;
        } else if (unit) {
          formattedVal = `${val.toLocaleString()} ${unit}`;
        }
        return `<div style="font-size:12px;font-weight:bold;margin-bottom:4px;">${p.name}</div><div>${displayName}: <b>${formattedVal}</b></div>`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '65px', containLabel: true },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: { fontSize: 11, color: '#475569' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: {
        fontSize: 10,
        color: '#475569',
        formatter: (val: number) => {
          if (unit === '$') {
            if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
            if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(0)}k`;
            return `$${val}`;
          }
          if (unit === '%') return `${val.toFixed(1)}%`;
          if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
          if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(0)}k`;
          return `${val}`;
        },
      },
    },
    series: [
      {
        name: displayName,
        type: 'line',
        smooth: true,
        data: values,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37, 99, 235, 0.25)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
            ],
          },
        },
        lineStyle: { color: '#2563eb', width: 2.5 },
        itemStyle: { color: '#2563eb' },
      },
    ],
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
      <ReactECharts option={option} style={{ height: 260, width: '100%' }} />
    </div>
  );
};
