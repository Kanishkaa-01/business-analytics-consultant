import React from 'react';
import ReactECharts from 'echarts-for-react';
import { ParetoItem } from '../../types';

interface Props {
  items: ParetoItem[];
}

export const ParetoChart: React.FC<Props> = ({ items }) => {
  const topItems = items.slice(0, 8);
  const entities = topItems.map((i) => i.entity);
  const losses = topItems.map((i) => i.loss_or_impact);
  const cumulativePct = topItems.map((i) => i.cumulative_percentage);

  const option = {
    title: {
      text: 'Biggest Contributors to Overall Difference',
      subtext: 'Shows which areas account for most of the total difference',
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' },
      subtextStyle: { fontSize: 11, color: '#64748b' },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: { left: '3%', right: '5%', bottom: '3%', top: '65px', containLabel: true },
    xAxis: {
      type: 'category',
      data: entities,
      axisLabel: { interval: 0, rotate: 20, fontSize: 10, color: '#475569' },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Impact ($)',
        splitLine: { lineStyle: { color: '#f1f5f9' } },
      },
      {
        type: 'value',
        name: 'Cumulative %',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Loss Impact',
        type: 'bar',
        data: losses.map((l, idx) => ({
          value: l,
          itemStyle: {
            color: topItems[idx]?.is_vital_few ? '#f97316' : '#94a3b8',
            borderRadius: [4, 4, 0, 0],
          },
        })),
      },
      {
        name: 'Cumulative %',
        type: 'line',
        yAxisIndex: 1,
        data: cumulativePct,
        lineStyle: { color: '#2563eb', width: 2.5 },
        itemStyle: { color: '#2563eb' },
        markLine: {
          data: [{ yAxis: 80, name: 'Majority Contribution' }],
          lineStyle: { color: '#dc2626', type: 'dashed' },
          label: { formatter: 'Majority Contribution', position: 'end' },
        },
      },
    ],
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
      <ReactECharts option={option} style={{ height: 280, width: '100%' }} />
    </div>
  );
};
