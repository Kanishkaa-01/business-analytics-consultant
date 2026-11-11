import { describe, it, expect } from 'vitest';
import { buildComparisonChartOption } from '../utils/scenarioChartOptions';
import { ScenarioComparisonReport } from '../types';

/**
 * Scenario Comparison Client Logic & Deterministic Calculation Tests
 */

interface ScenarioInput {
  name: string;
  intervention_type: string;
  change_percentage: number | string;
  parameter_type?: 'percentage' | 'percentage_points';
  notes?: string;
}

interface DatasetSupportFlags {
  hasCost: boolean;
  hasDiscount: boolean;
}

function validateScenarioInput(input: ScenarioInput, flags: DatasetSupportFlags): string | null {
  if (!input.name || !input.name.trim()) {
    return 'Scenario name is required.';
  }
  const val = Number(input.change_percentage);
  if (isNaN(val) || input.change_percentage === '') {
    return 'Change parameter must be a valid number.';
  }

  if (input.intervention_type === 'Price Change') {
    if (val < -100) return 'Price change percentage cannot be less than -100% (prices cannot be negative).';
    if (val > 500) return 'Price change percentage cannot exceed +500%.';
  } else if (input.intervention_type === 'Sales Volume Change') {
    if (val < -100) return 'Sales volume change percentage cannot be less than -100% (sales volume cannot be negative).';
    if (val > 500) return 'Sales volume change percentage cannot exceed +500%.';
  } else if (input.intervention_type === 'Operating Cost Reduction') {
    if (!flags.hasCost) return 'Operating Cost Reduction is unsupported: dataset lacks required cost or profit metrics.';
    if (val < 0) return 'Operating cost reduction percentage cannot be negative (must be >= 0%).';
    if (val > 100) return 'Operating cost reduction percentage cannot exceed 100% (costs cannot be reduced below zero).';
  } else if (input.intervention_type === 'Discount Change') {
    if (!flags.hasDiscount) return 'Discount Change is unsupported: dataset lacks valid discount data.';
    if (input.parameter_type === 'percentage') {
      if (val < -100 || val > 100) return 'Discount percentage change must be between -100% and +100%.';
    } else {
      if (val < 0) return 'Percentage points discount reduction cannot be negative.';
      if (val > 100) return 'Percentage points discount reduction cannot exceed 100 pp.';
    }
  } else {
    return `Unsupported intervention type: ${input.intervention_type}`;
  }

  return null;
}

function simulateScenarioFinancials(
  baselineRev: number,
  baselineCost: number,
  interventionType: string,
  changeVal: number,
  paramType: 'percentage' | 'percentage_points' = 'percentage',
  baselineDiscountRate = 0.15
) {
  const baselineProfit = baselineRev - baselineCost;

  if (interventionType === 'Price Change') {
    // Price change: Revenue = base * (1 + p), Cost unchanged
    const pFrac = changeVal / 100;
    const simRev = baselineRev * (1 + pFrac);
    const simCost = baselineCost;
    const simProfit = simRev - simCost;
    return {
      revenue: simRev,
      profit: simProfit,
      revenueDelta: simRev - baselineRev,
      profitDelta: simProfit - baselineProfit,
      marginPct: (simProfit / simRev) * 100,
    };
  }

  if (interventionType === 'Sales Volume Change') {
    // Sales volume: Revenue = base * (1 + v), Cost = base * (1 + v), Margin % preserved
    const vFrac = changeVal / 100;
    const simRev = baselineRev * (1 + vFrac);
    const simCost = baselineCost * (1 + vFrac);
    const simProfit = simRev - simCost;
    return {
      revenue: simRev,
      profit: simProfit,
      revenueDelta: simRev - baselineRev,
      profitDelta: simProfit - baselineProfit,
      marginPct: (simProfit / simRev) * 100,
    };
  }

  if (interventionType === 'Operating Cost Reduction') {
    // Cost reduction: Revenue unchanged, Cost = base * (1 - ops), Profit = base + baseCost * ops
    const opsFrac = changeVal / 100;
    const simRev = baselineRev;
    const simCost = baselineCost * (1 - opsFrac);
    const simProfit = simRev - simCost;
    return {
      revenue: simRev,
      profit: simProfit,
      revenueDelta: simRev - baselineRev,
      profitDelta: simProfit - baselineProfit,
      marginPct: (simProfit / simRev) * 100,
    };
  }

  if (interventionType === 'Discount Change') {
    // Discount change: Margin recovery
    let gain = 0;
    if (paramType === 'percentage') {
      gain = baselineRev * baselineDiscountRate * (changeVal / 100);
    } else {
      gain = baselineRev * (changeVal / 100);
    }
    const simRev = baselineRev;
    const simProfit = baselineProfit + gain;
    return {
      revenue: simRev,
      profit: simProfit,
      revenueDelta: 0,
      profitDelta: gain,
      marginPct: (simProfit / simRev) * 100,
    };
  }

  throw new Error(`Unknown intervention type: ${interventionType}`);
}

function evaluateTieAndRankings(scenarios: Array<{ name: string; profit: number; revenue: number }>) {
  if (scenarios.length === 0) return { bestProfit: null, isTie: false, insight: '' };

  const maxProfit = Math.max(...scenarios.map((s) => s.profit));
  const topProfitScenarios = scenarios.filter((s) => Math.abs(s.profit - maxProfit) < 1e-4);

  if (topProfitScenarios.length > 1) {
    const tiedNames = topProfitScenarios.map((s) => s.name).join(' and ');
    return {
      bestProfit: null,
      isTie: true,
      insight: `Scenarios ${tiedNames} tied for highest net profit ($${maxProfit.toLocaleString()}).`,
    };
  }

  return {
    bestProfit: topProfitScenarios[0].name,
    isTie: false,
    insight: `Scenario ${topProfitScenarios[0].name} leads in net profit ($${maxProfit.toLocaleString()}).`,
  };
}

describe('Scenario Comparison - Validation and Interventions', () => {
  const fullSupport: DatasetSupportFlags = { hasCost: true, hasDiscount: true };
  const limitedSupport: DatasetSupportFlags = { hasCost: false, hasDiscount: false };

  it('rejects empty scenario name', () => {
    const err = validateScenarioInput(
      { name: '   ', intervention_type: 'Price Change', change_percentage: 5 },
      fullSupport
    );
    expect(err).toBe('Scenario name is required.');
  });

  it('rejects non-numeric change parameter', () => {
    const err = validateScenarioInput(
      { name: 'Test Plan', intervention_type: 'Price Change', change_percentage: 'abc' },
      fullSupport
    );
    expect(err).toBe('Change parameter must be a valid number.');
  });

  it('rejects price change below -100%', () => {
    const err = validateScenarioInput(
      { name: 'Extreme Cut', intervention_type: 'Price Change', change_percentage: -105 },
      fullSupport
    );
    expect(err).toContain('cannot be less than -100%');
  });

  it('rejects sales volume change below -100%', () => {
    const err = validateScenarioInput(
      { name: 'Catastrophic Drop', intervention_type: 'Sales Volume Change', change_percentage: -101 },
      fullSupport
    );
    expect(err).toContain('cannot be less than -100%');
  });

  it('rejects operating cost reduction below 0% or above 100%', () => {
    const errNegative = validateScenarioInput(
      { name: 'Cost Increase as Reduction', intervention_type: 'Operating Cost Reduction', change_percentage: -5 },
      fullSupport
    );
    expect(errNegative).toContain('cannot be negative');

    const errOver = validateScenarioInput(
      { name: 'Impossible Savings', intervention_type: 'Operating Cost Reduction', change_percentage: 105 },
      fullSupport
    );
    expect(errOver).toContain('cannot exceed 100%');
  });

  it('rejects unsupported interventions when dataset lacks required fields', () => {
    const errCost = validateScenarioInput(
      { name: 'Ops Cut', intervention_type: 'Operating Cost Reduction', change_percentage: 10 },
      limitedSupport
    );
    expect(errCost).toContain('dataset lacks required cost or profit metrics');

    const errDiscount = validateScenarioInput(
      { name: 'Disc Adjust', intervention_type: 'Discount Change', change_percentage: 5 },
      limitedSupport
    );
    expect(errDiscount).toContain('dataset lacks valid discount data');
  });

  it('correctly validates discount change in percentage vs percentage points', () => {
    // Valid percentage
    expect(
      validateScenarioInput(
        { name: 'Disc %', intervention_type: 'Discount Change', change_percentage: 25, parameter_type: 'percentage' },
        fullSupport
      )
    ).toBeNull();

    // Invalid percentage (> 100%)
    expect(
      validateScenarioInput(
        { name: 'Disc %', intervention_type: 'Discount Change', change_percentage: 120, parameter_type: 'percentage' },
        fullSupport
      )
    ).toContain('must be between -100% and +100%');

    // Valid pp
    expect(
      validateScenarioInput(
        { name: 'Disc pp', intervention_type: 'Discount Change', change_percentage: 3.5, parameter_type: 'percentage_points' },
        fullSupport
      )
    ).toBeNull();

    // Invalid pp (< 0)
    expect(
      validateScenarioInput(
        { name: 'Disc pp', intervention_type: 'Discount Change', change_percentage: -2, parameter_type: 'percentage_points' },
        fullSupport
      )
    ).toContain('cannot be negative');
  });
});

describe('Scenario Comparison - Deterministic Formulas & Baseline Equality', () => {
  const BASE_REV = 100000;
  const BASE_COST = 60000;
  const BASE_PROFIT = 40000;
  const BASE_MARGIN = 40.0;

  it('preserves baseline equality: all-zero changes yield exact baseline and zero incremental value', () => {
    const priceZero = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Price Change', 0);
    expect(priceZero.revenue).toBe(BASE_REV);
    expect(priceZero.profit).toBe(BASE_PROFIT);
    expect(priceZero.revenueDelta).toBe(0);
    expect(priceZero.profitDelta).toBe(0);
    expect(priceZero.marginPct).toBeCloseTo(BASE_MARGIN);

    const volumeZero = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Sales Volume Change', 0);
    expect(volumeZero.revenue).toBe(BASE_REV);
    expect(volumeZero.profit).toBe(BASE_PROFIT);
    expect(volumeZero.revenueDelta).toBe(0);
    expect(volumeZero.profitDelta).toBe(0);
    expect(volumeZero.marginPct).toBeCloseTo(BASE_MARGIN);

    const costZero = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Operating Cost Reduction', 0);
    expect(costZero.revenue).toBe(BASE_REV);
    expect(costZero.profit).toBe(BASE_PROFIT);
    expect(costZero.revenueDelta).toBe(0);
    expect(costZero.profitDelta).toBe(0);
    expect(costZero.marginPct).toBeCloseTo(BASE_MARGIN);
  });

  it('ensures operating cost reduction isolates costs and does NOT alter revenue', () => {
    const costCut = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Operating Cost Reduction', 10);
    // Revenue must remain exactly at baseline
    expect(costCut.revenue).toBe(BASE_REV);
    expect(costCut.revenueDelta).toBe(0);
    // Profit must increase by 10% of 60,000 = 6,000
    expect(costCut.profit).toBe(46000);
    expect(costCut.profitDelta).toBe(6000);
    // Margin increases from 40% to 46%
    expect(costCut.marginPct).toBe(46.0);
  });

  it('verifies sales volume change scales revenue and costs proportionally, preserving margin %', () => {
    const volGrowth = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Sales Volume Change', 15);
    // Revenue +15% -> 115,000
    expect(volGrowth.revenue).toBeCloseTo(115000);
    expect(volGrowth.revenueDelta).toBeCloseTo(15000);
    // Profit +15% -> 46,000
    expect(volGrowth.profit).toBeCloseTo(46000);
    expect(volGrowth.profitDelta).toBeCloseTo(6000);
    // Margin % remains constant at 40%
    expect(volGrowth.marginPct).toBeCloseTo(BASE_MARGIN);
  });

  it('verifies price change alters revenue with no cost change', () => {
    const priceHike = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Price Change', 5);
    // Revenue +5% -> 105,000
    expect(priceHike.revenue).toBe(105000);
    expect(priceHike.revenueDelta).toBe(5000);
    // Profit +5,000 -> 45,000
    expect(priceHike.profit).toBe(45000);
    expect(priceHike.profitDelta).toBe(5000);
  });

  it('distinguishes discount change % vs pp calculations', () => {
    // 10% reduction on 15% discount rate = 100,000 * 0.15 * 0.10 = $1,500
    const discPct = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Discount Change', 10, 'percentage', 0.15);
    expect(discPct.profitDelta).toBe(1500);

    // 2 pp reduction = 100,000 * 0.02 = $2,000
    const discPP = simulateScenarioFinancials(BASE_REV, BASE_COST, 'Discount Change', 2, 'percentage_points', 0.15);
    expect(discPP.profitDelta).toBe(2000);
  });
});

describe('Scenario Comparison - Tie Handling & Insight Consistency', () => {
  it('reports a tie when multiple scenarios achieve identical top profit', () => {
    const scenarios = [
      { name: 'Plan A: Price Hike', profit: 50000, revenue: 110000 },
      { name: 'Plan B: Cost Efficiency', profit: 50000, revenue: 100000 },
      { name: 'Plan C: Minor Expansion', profit: 45000, revenue: 105000 },
    ];

    const result = evaluateTieAndRankings(scenarios);
    expect(result.isTie).toBe(true);
    expect(result.bestProfit).toBeNull();
    expect(result.insight).toContain('Plan A: Price Hike and Plan B: Cost Efficiency tied');
  });

  it('reports a clear winner when no tie exists', () => {
    const scenarios = [
      { name: 'Plan A: Price Hike', profit: 52000, revenue: 110000 },
      { name: 'Plan B: Cost Efficiency', profit: 50000, revenue: 100000 },
    ];

    const result = evaluateTieAndRankings(scenarios);
    expect(result.isTie).toBe(false);
    expect(result.bestProfit).toBe('Plan A: Price Hike');
    expect(result.insight).toContain('Plan A: Price Hike leads in net profit');
  });
});

describe('Scenario Comparison - Chart Visualization Option Builder', () => {
  it('returns empty object when report is null or scenarios empty', () => {
    expect(buildComparisonChartOption(null)).toEqual({});
    expect(buildComparisonChartOption({ scenarios: [] } as any)).toEqual({});
  });

  it('builds valid Cartesian2D option with xAxis, yAxis, and 3 series', () => {
    const mockReport: ScenarioComparisonReport = {
      scenarios: [
        {
          id: 'baseline',
          name: 'Baseline',
          revenue: 4235224.34,
          profit: 1443103.44,
          profit_margin_pct: 34.07,
          incremental_value: 0,
          risk_adjusted_return: 0,
          revenue_delta: 0,
          profit_delta: 0,
          parameters: {},
          intervention_summary: 'Baseline (0% adjustments)',
        },
        {
          id: 'sc-1',
          name: 'Moderate Price Increase',
          revenue: 4319928.83,
          profit: 1527807.93,
          profit_margin_pct: 35.37,
          incremental_value: 84704.49,
          risk_adjusted_return: 71998.81,
          revenue_delta: 84704.49,
          profit_delta: 84704.49,
          parameters: { intervention_type: 'Price Change', change_percentage: 2.0 },
          intervention_summary: 'Price Increase: +2%',
        },
        {
          id: 'sc-2',
          name: 'Sales Growth',
          revenue: 4446985.56,
          profit: 1515258.61,
          profit_margin_pct: 34.07,
          incremental_value: 72155.17,
          risk_adjusted_return: 61331.9,
          revenue_delta: 211761.22,
          profit_delta: 72155.17,
          parameters: { intervention_type: 'Sales Volume Change', change_percentage: 5.0 },
          intervention_summary: 'Volume Growth: +5%',
        },
      ],
      comparison_insights: ['Sales Growth leads in projected revenue.'],
    };

    const option = buildComparisonChartOption(mockReport);

    // Verify Cartesian2D xAxis presence and category alignment
    expect(option.xAxis).toBeDefined();
    expect(option.xAxis.type).toBe('category');
    expect(option.xAxis.data).toEqual(['Baseline', 'Moderate Price Increase', 'Sales Growth']);

    // Verify dual y-axes (Currency Amount and Margin %)
    expect(option.yAxis).toHaveLength(2);
    expect(option.yAxis[0].name).toBe('Amount ($)');
    expect(option.yAxis[1].name).toBe('Margin (%)');

    // Verify 3 distinct series (Revenue, Net Profit, Profit Margin %)
    expect(option.series).toHaveLength(3);
    expect(option.series[0].name).toBe('Revenue');
    expect(option.series[0].type).toBe('bar');
    expect(option.series[0].data).toEqual([4235224.34, 4319928.83, 4446985.56]);

    expect(option.series[1].name).toBe('Net Profit');
    expect(option.series[1].type).toBe('bar');
    expect(option.series[1].data).toEqual([1443103.44, 1527807.93, 1515258.61]);

    expect(option.series[2].name).toBe('Profit Margin %');
    expect(option.series[2].type).toBe('line');
    expect(option.series[2].yAxisIndex).toBe(1);
    expect(option.series[2].data).toEqual([34.07, 35.37, 34.07]);

    // Verify legend and tooltip configuration
    expect(option.legend.data).toEqual(['Revenue', 'Net Profit', 'Profit Margin %']);
    expect(option.tooltip.trigger).toBe('axis');
  });
});

