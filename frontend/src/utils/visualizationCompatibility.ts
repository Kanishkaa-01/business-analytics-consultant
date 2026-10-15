/**
 * Deterministic Visualization Recommendation & Compatibility Utility
 * Strictly client-side presentation mapping. Never mutates underlying analytics.
 */

export type SupportedChartType =
  | 'line'
  | 'bar'
  | 'horizontal_bar'
  | 'pie'
  | 'scatter'
  | 'table';

export interface ChartTypeOption {
  type: SupportedChartType;
  label: string;
  isRecommended: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

export interface CompatibilityAnalysis {
  recommendedType: SupportedChartType;
  recommendationReason: string;
  allowedTypes: SupportedChartType[];
  options: ChartTypeOption[];
}

export interface DataPoint {
  label: string;
  value: number;
  secondaryValue?: number;
  raw?: any;
}

/**
 * Determine supported chart types and recommended visualization based on data characteristics.
 */
export function analyzeChartCompatibility(
  data: DataPoint[],
  hints?: {
    isTimeSeries?: boolean;
    isCategorical?: boolean;
    isBivariate?: boolean;
    metricName?: string;
    dimensionName?: string;
  }
): CompatibilityAnalysis {
  const count = data.length;
  const hasNegative = data.some((d) => d.value < 0);
  const isTimeSeries =
    hints?.isTimeSeries ??
    (count > 0 &&
      data.every((d) =>
        /^\d{4}(-\d{2})?|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)|Q[1-4]|^\d{1,2}\/\d{1,2}/i.test(
          String(d.label).trim()
        )
      ));
  const isBivariate = hints?.isBivariate ?? data.some((d) => d.secondaryValue !== undefined);

  let recommendedType: SupportedChartType = 'bar';
  let recommendationReason = 'Bar chart provides clear discrete comparison across categories.';
  const allowed = new Set<SupportedChartType>(['table']);

  if (isTimeSeries) {
    recommendedType = 'line';
    recommendationReason =
      'Recommended: Line Chart because chronological sequential periods are best interpreted through continuous trend progression.';
    allowed.add('line');
    allowed.add('bar');
    // Pie is explicitly disallowed for time series to prevent distorting temporal continuity
  } else if (isBivariate) {
    recommendedType = 'scatter';
    recommendationReason =
      'Recommended: Scatter Plot because dual continuous numeric dimensions reveal correlation and dispersion.';
    allowed.add('scatter');
    allowed.add('bar');
  } else {
    // Categorical
    if (count > 7) {
      recommendedType = 'horizontal_bar';
      recommendationReason =
        'Recommended: Horizontal Bar Chart because numerous categories (>7) read more legibly with horizontal axis labels.';
      allowed.add('horizontal_bar');
      allowed.add('bar');
      // Pie disallowed for > 7 categories to prevent crowded slices
    } else {
      recommendedType = 'bar';
      recommendationReason =
        'Recommended: Bar Chart because discrete segments with distinct magnitudes are most clearly compared side-by-side.';
      allowed.add('bar');
      allowed.add('horizontal_bar');
      if (!hasNegative && count <= 7 && count >= 2) {
        allowed.add('pie');
      }
    }
  }

  const allTypes: { type: SupportedChartType; label: string }[] = [
    { type: 'line', label: 'Line Chart' },
    { type: 'bar', label: 'Bar Chart' },
    { type: 'horizontal_bar', label: 'Horizontal Bar' },
    { type: 'pie', label: 'Pie Chart' },
    { type: 'scatter', label: 'Scatter Plot' },
    { type: 'table', label: 'Data Table' },
  ];

  const options: ChartTypeOption[] = allTypes.map((t) => {
    const isAllowed = allowed.has(t.type);
    let disabledReason: string | undefined;
    if (!isAllowed) {
      if (t.type === 'pie') {
        disabledReason = isTimeSeries
          ? 'Pie charts distort chronological progression'
          : hasNegative
          ? 'Pie charts cannot represent negative values'
          : 'Too many categories for readable slices (>7)';
      } else if (t.type === 'scatter') {
        disabledReason = 'Scatter plots require dual continuous numeric variables';
      } else if (t.type === 'line') {
        disabledReason = 'Line charts imply continuity and are not recommended for unordered categories';
      } else {
        disabledReason = 'Incompatible with this data shape';
      }
    }

    return {
      type: t.type,
      label: t.label,
      isRecommended: t.type === recommendedType,
      disabled: !isAllowed,
      disabledReason,
    };
  });

  return {
    recommendedType,
    recommendationReason,
    allowedTypes: Array.from(allowed),
    options,
  };
}

/**
 * Generate Apache ECharts options deterministically for the selected chart type.
 */
export function buildEChartsOption(
  data: DataPoint[],
  chartType: SupportedChartType,
  title?: string,
  metricName = 'Value'
): any {
  const labels = data.map((d) => d.label);
  const values = data.map((d) => d.value);

  const baseOption: any = {
    title: title
      ? {
          text: title,
          textStyle: { fontSize: 13, fontWeight: 'bold', color: '#1e293b' },
        }
      : undefined,
    tooltip: { trigger: chartType === 'pie' ? 'item' : 'axis' },
    grid: { left: '4%', right: '4%', bottom: '10%', top: title ? '45px' : '20px', containLabel: true },
  };

  switch (chartType) {
    case 'line':
      return {
        ...baseOption,
        tooltip: {
          trigger: 'axis',
          formatter: (params: any) => {
            const p = Array.isArray(params) ? params[0] : params;
            return `<b>${p.name}</b><br/>${metricName}: <b>${Number(p.value).toLocaleString()}</b>`;
          },
        },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { rotate: labels.length > 6 ? 25 : 0, fontSize: 11, color: '#475569' },
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: {
            formatter: (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`),
            fontSize: 10,
          },
        },
        series: [
          {
            name: metricName,
            type: 'line',
            smooth: true,
            data: values,
            lineStyle: { color: '#2563eb', width: 2.5 },
            itemStyle: { color: '#2563eb' },
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
          },
        ],
      };

    case 'horizontal_bar':
      return {
        ...baseOption,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
        },
        xAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: {
            formatter: (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`),
            fontSize: 10,
          },
        },
        yAxis: {
          type: 'category',
          data: [...labels].reverse(),
          axisLabel: { fontSize: 11, color: '#334155' },
        },
        series: [
          {
            name: metricName,
            type: 'bar',
            data: [...values].reverse(),
            itemStyle: {
              color: '#3b82f6',
              borderRadius: [0, 4, 4, 0],
            },
          },
        ],
      };

    case 'pie':
      return {
        ...baseOption,
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} ({d}%)',
        },
        legend: {
          orient: 'vertical',
          right: '5%',
          top: 'middle',
          textStyle: { fontSize: 11, color: '#475569' },
        },
        series: [
          {
            name: metricName,
            type: 'pie',
            radius: ['42%', '70%'],
            center: ['40%', '52%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 5,
              borderColor: '#fff',
              borderWidth: 2,
            },
            data: data.map((d) => ({ name: d.label, value: d.value })),
          },
        ],
      };

    case 'scatter':
      return {
        ...baseOption,
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            const val = params.value;
            return `<b>${params.name || ''}</b><br/>X: ${val[0]}<br/>Y: ${val[1]}`;
          },
        },
        xAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [
          {
            type: 'scatter',
            symbolSize: 8,
            data: data.map((d) => [d.value, d.secondaryValue ?? 0]),
            itemStyle: { color: '#6366f1' },
          },
        ],
      };

    case 'bar':
    default:
      return {
        ...baseOption,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params: any) => {
            const p = Array.isArray(params) ? params[0] : params;
            return `<b>${p.name}</b><br/>${metricName}: <b>${Number(p.value).toLocaleString()}</b>`;
          },
        },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { interval: 0, rotate: labels.length > 5 ? 25 : 0, fontSize: 11, color: '#475569' },
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: {
            formatter: (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`),
            fontSize: 10,
          },
        },
        series: [
          {
            name: metricName,
            type: 'bar',
            data: values,
            itemStyle: {
              color: '#3b82f6',
              borderRadius: [4, 4, 0, 0],
            },
          },
        ],
      };
  }
}
