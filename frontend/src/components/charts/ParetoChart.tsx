import React from 'react';
import ReactECharts from 'echarts-for-react';
import { ParetoItem } from '../../types';

interface Props {
  items: ParetoItem[];
  unit?: string;
  title?: string;
  subtext?: string;
}

export const ParetoChart: React.FC<Props> = ({
  items,
  unit = '$',
  title = 'Biggest Contributors to Overall Difference',
  subtext = 'Shows which areas account for most of the total difference'
}) => {
  if (!items || items.length === 0) {
    return null;
  }

  const topItems = items.slice(0, 8);
  const entities = topItems.map((i) => i.entity);
  const losses = topItems.map((i) => i.loss_or_impact);
  const cumulativePct = topItems.map((i) => i.cumulative_percentage);
  const yName = unit === '$' ? 'Impact ($)' : (unit ? `Impact (${unit})` : 'Impact');

  const option = {
    title: {
      text: title,
      subtext: subtext,
      textStyle: { fontSize: 13, fontWeight: 'bold', color: '#334155' },
      subtextStyle: { fontSize: 11, color: '#64748b' },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return '';
        const barParam = params[0];
        const lineParam = params[1];
        let res = `<div style="font-size: 11px;"><strong>${barParam.name}</strong><br/>`;
        if (barParam) {
          const valStr = unit === '$' ? `$${Number(barParam.value).toLocaleString()}` : `${Number(barParam.value).toLocaleString()} ${unit}`;
          res += `${barParam.seriesName}: ${valStr}<br/>`;
        }
        if (lineParam) {
          res += `${lineParam.seriesName}: ${lineParam.value}%`;
        }
        res += '</div>';
        return res;
      }
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
        name: yName,
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
