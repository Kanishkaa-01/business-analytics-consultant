import { describe, it, expect } from 'vitest';
import {
  analyzeChartCompatibility,
  buildEChartsOption,
  DataPoint
} from '../utils/visualizationCompatibility';

describe('Deterministic Visualization Recommendation & Compatibility', () => {
  it('recommends Line Chart for sequential time series data and disallows Pie Chart', () => {
    const timeData: DataPoint[] = [
      { label: '2024-01', value: 12000 },
      { label: '2024-02', value: 14500 },
      { label: '2024-03', value: 13200 },
      { label: '2024-04', value: 16800 },
    ];

    const result = analyzeChartCompatibility(timeData, { isTimeSeries: true });
    expect(result.recommendedType).toBe('line');
    expect(result.allowedTypes).toContain('line');
    expect(result.allowedTypes).toContain('bar');
    expect(result.allowedTypes).toContain('table');
    // Pie must be disallowed for time series
    expect(result.allowedTypes).not.toContain('pie');

    const pieOption = result.options.find((o) => o.type === 'pie');
    expect(pieOption?.disabled).toBe(true);
    expect(pieOption?.disabledReason).toMatch(/chronological progression/i);
  });

  it('recommends Bar Chart for discrete categories (<= 7) and permits Pie Chart when positive', () => {
    const categoricalData: DataPoint[] = [
      { label: 'North America', value: 50000 },
      { label: 'Europe', value: 42000 },
      { label: 'Asia Pacific', value: 31000 },
    ];

    const result = analyzeChartCompatibility(categoricalData, { isCategorical: true });
    expect(result.recommendedType).toBe('bar');
    expect(result.allowedTypes).toContain('bar');
    expect(result.allowedTypes).toContain('horizontal_bar');
    expect(result.allowedTypes).toContain('pie');
    expect(result.allowedTypes).toContain('table');
  });

  it('recommends Horizontal Bar for numerous categories (> 7) and disallows Pie Chart', () => {
    const manyCategories: DataPoint[] = Array.from({ length: 10 }, (_, i) => ({
      label: `Category ${i + 1}`,
      value: 1000 * (i + 1),
    }));

    const result = analyzeChartCompatibility(manyCategories, { isCategorical: true });
    expect(result.recommendedType).toBe('horizontal_bar');
    expect(result.allowedTypes).toContain('horizontal_bar');
    expect(result.allowedTypes).toContain('bar');
    expect(result.allowedTypes).toContain('table');
    // Pie must be disallowed for >7 categories
    expect(result.allowedTypes).not.toContain('pie');

    const pieOption = result.options.find((o) => o.type === 'pie');
    expect(pieOption?.disabled).toBe(true);
    expect(pieOption?.disabledReason).toMatch(/Too many categories/i);
  });

  it('disallows Pie Chart when negative values exist in categorical data', () => {
    const negativeData: DataPoint[] = [
      { label: 'Product A', value: 2500 },
      { label: 'Product B', value: -1200 },
      { label: 'Product C', value: 3100 },
    ];

    const result = analyzeChartCompatibility(negativeData);
    expect(result.allowedTypes).not.toContain('pie');
    const pieOption = result.options.find((o) => o.type === 'pie');
    expect(pieOption?.disabled).toBe(true);
    expect(pieOption?.disabledReason).toMatch(/negative values/i);
  });

  it('recommends Scatter Plot when bivariate continuous data is supplied', () => {
    const bivariateData: DataPoint[] = [
      { label: 'Item 1', value: 10.5, secondaryValue: 85.0 },
      { label: 'Item 2', value: 15.0, secondaryValue: 72.0 },
      { label: 'Item 3', value: 20.0, secondaryValue: 64.0 },
    ];

    const result = analyzeChartCompatibility(bivariateData, { isBivariate: true });
    expect(result.recommendedType).toBe('scatter');
    expect(result.allowedTypes).toContain('scatter');
    expect(result.allowedTypes).toContain('table');
  });

  it('always includes Data Table as an allowed compatible format for auditable inspection', () => {
    const sampleData: DataPoint[] = [{ label: 'Entry 1', value: 100 }];
    const result = analyzeChartCompatibility(sampleData);
    expect(result.allowedTypes).toContain('table');
    const tableOption = result.options.find((o) => o.type === 'table');
    expect(tableOption?.disabled).toBeFalsy();
  });

  it('builds valid ECharts configuration options deterministically', () => {
    const points: DataPoint[] = [
      { label: 'Q1', value: 100 },
      { label: 'Q2', value: 150 },
    ];

    const lineOpt = buildEChartsOption(points, 'line', 'Quarterly Trend', 'Sales');
    expect(lineOpt.series[0].type).toBe('line');
    expect(lineOpt.xAxis.data).toEqual(['Q1', 'Q2']);

    const barOpt = buildEChartsOption(points, 'bar', 'Quarterly Bar', 'Sales');
    expect(barOpt.series[0].type).toBe('bar');

    const hBarOpt = buildEChartsOption(points, 'horizontal_bar', 'Horizontal', 'Sales');
    expect(hBarOpt.series[0].type).toBe('bar');
    expect(hBarOpt.yAxis.type).toBe('category');

    const pieOpt = buildEChartsOption(points, 'pie', 'Pie Distribution', 'Sales');
    expect(pieOpt.series[0].type).toBe('pie');
  });
});
