import React from 'react';
import ReactECharts from 'echarts-for-react';
import { VarianceBreakdownItem } from '../../types';

interface Props {
  items: VarianceBreakdownItem[];
  metricName: string;
}

export const VarianceChart: React.FC<Props> = ({ items, metricName }) => {
  const topItems = items.slice(0, 10);
  const segments = topItems.map((i) => `${i.segment} (${i.dimension})`).reverse();
  const values = topItems.map((i) => i.variance).reverse();

  const option = {
    title: {
      text: `Variance Breakdown: Supporting Evidence for ${metricName}`,
      subtext: 'Segment Comparison of Positive and Negative Changes',
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' },
      subtextStyle: { fontSize: 11, color: '#64748b' },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0];
        const val = p.value;
        const color = val < 0 ? '#ef4444' : '#10b981';
        return `<b>${p.name}</b><br/>Variance: <span style="color:${color};font-weight:bold">${val >= 0 ? '+' : ''}${val.toLocaleString()}</span>`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '65px', containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    yAxis: {
      type: 'category',
      data: segments,
      axisLabel: { fontSize: 11, color: '#475569' },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
    },
    series: [
      {
        name: 'Variance',
        type: 'bar',
        data: values.map((val) => ({
          value: val,
          itemStyle: {
            color: val < 0 ? '#ef4444' : '#10b981',
            borderRadius: [0, 4, 4, 0],
          },
        })),
      },
    ],
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
      <ReactECharts option={option} style={{ height: 280, width: '100%' }} />
    </div>
  );
};
