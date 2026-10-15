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
}

export const TimelineChart: React.FC<Props> = ({ data, metricName }) => {
  if (!data || data.length === 0) return null;

  const periods = data.map((d) => d.period);
  const sums = data.map((d) => d.metric_sum);

  const option = {
    title: {
      text: `Historical Progression: ${metricName}`,
      subtext: 'Supporting Evidence: Baseline vs Recent Period Trajectory',
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' },
      subtextStyle: { fontSize: 11, color: '#64748b' },
    },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '65px', containLabel: true },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: { fontSize: 11, color: '#475569' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    series: [
      {
        name: metricName,
        type: 'line',
        smooth: true,
        data: sums,
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
