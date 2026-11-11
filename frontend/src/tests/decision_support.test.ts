import { describe, it, expect } from 'vitest';

describe('Explainable Business Decision Support Calculations', () => {
  it('calculates ICE / Multi-Criteria Decision Prioritization Score correctly', () => {
    const impact = 8.5;
    const confidence = 8.0;
    const ease = 7.0;
    const priorityScore = Math.round(((impact * confidence * ease) / 10) * 10) / 10;
    expect(priorityScore).toBe(47.6);
  });

  it('verifies deterministic price elasticity calculation', () => {
    const baselineRevenue = 1000000;
    const priceChangePct = 0.05; // +5%
    const priceElasticity = -1.25;
    const volumeMultiplier = 1.0 + (priceElasticity * priceChangePct); // 1 - 0.0625 = 0.9375
    const simulatedRevenue = baselineRevenue * (1.0 + priceChangePct) * volumeMultiplier;
    
    // Revenue = 1,000,000 * 1.05 * 0.9375 = 984,375
    expect(Math.round(simulatedRevenue)).toBe(984375);
  });

  it('calculates gross margin recovery from algorithmic discount floor', () => {
    const baselineRevenue = 1000000;
    const discountReductionRate = 0.10; // 10%
    const marginRecaptureFactor = 0.12;
    const grossMarginRecovered = baselineRevenue * marginRecaptureFactor * discountReductionRate;
    expect(grossMarginRecovered).toBe(12000);
  });

  it('validates priority tier classification boundaries', () => {
    const getTier = (score: number) => {
      if (score >= 50) return 'P1 - Critical';
      if (score >= 35) return 'P2 - High';
      if (score >= 20) return 'P3 - Medium';
      return 'P4 - Opportunistic';
    };

    expect(getTier(55.2)).toBe('P1 - Critical');
    expect(getTier(42.0)).toBe('P2 - High');
    expect(getTier(28.5)).toBe('P3 - Medium');
    expect(getTier(14.0)).toBe('P4 - Opportunistic');
  });
});
