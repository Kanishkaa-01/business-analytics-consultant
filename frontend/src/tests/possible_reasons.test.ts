import { describe, it, expect } from 'vitest';
import { getSupportingEvidence } from '../components/stages/Stage4_PossibleReasons';
import { FactorContribution } from '../types';

describe('Stage 4 - Possible Reasons Evidence Simplification & Causation Safety', () => {
  it('generates strong positive association for high attribution / correlation', () => {
    const fc: FactorContribution = {
      factor_name: 'Gross Sales',
      factor_type: 'Supply & Economics',
      attribution_percentage: 21.1,
      statistical_significance_p_value: 0.0001,
      correlation_or_coef: 0.58,
      direction: 'Positive Impact',
      evidence_statement: 'Correlation check demonstrates Pearson r = +0.58...'
    };

    const evidence = getSupportingEvidence(fc);
    expect(evidence).toBe('Strong positive association with the observed pattern.');
  });

  it('generates moderate positive association for moderate attribution / correlation', () => {
    const fc: FactorContribution = {
      factor_name: 'Unit Price',
      factor_type: 'Commercial',
      attribution_percentage: 12.6,
      statistical_significance_p_value: 0.005,
      correlation_or_coef: 0.32,
      direction: 'Positive Impact',
      evidence_statement: 'Correlation check demonstrates Pearson r = +0.32...'
    };

    const evidence = getSupportingEvidence(fc);
    expect(evidence).toBe('Moderate positive association with the observed pattern.');
  });

  it('generates weak positive association for low attribution & correlation', () => {
    const fc: FactorContribution = {
      factor_name: 'Shipping Method',
      factor_type: 'Operational',
      attribution_percentage: 4.5,
      statistical_significance_p_value: 0.04,
      correlation_or_coef: 0.18,
      direction: 'Positive Impact',
      evidence_statement: 'Correlation check demonstrates Pearson r = +0.18...'
    };

    const evidence = getSupportingEvidence(fc);
    expect(evidence).toBe('Weak positive association with the observed pattern.');
  });

  it('generates negative association for negative correlation', () => {
    const fcStrongNeg: FactorContribution = {
      factor_name: 'Discount Rate',
      factor_type: 'Commercial',
      attribution_percentage: 22.0,
      statistical_significance_p_value: 0.001,
      correlation_or_coef: -0.62,
      direction: 'Negative Impact',
      evidence_statement: 'Correlation check demonstrates Pearson r = -0.62...'
    };
    expect(getSupportingEvidence(fcStrongNeg)).toBe('Strong negative association with the observed pattern.');

    const fcWeakNeg: FactorContribution = {
      factor_name: 'Return Frequency',
      factor_type: 'Customer',
      attribution_percentage: 6.2,
      statistical_significance_p_value: 0.03,
      correlation_or_coef: -0.16,
      direction: 'Negative Impact',
      evidence_statement: 'Correlation check demonstrates Pearson r = -0.16...'
    };
    expect(getSupportingEvidence(fcWeakNeg)).toBe('Negative association with the observed pattern.');
  });

  it('generates no clear association when p-value is statistically insignificant', () => {
    const fcInsignificant: FactorContribution = {
      factor_name: 'Day of Week',
      factor_type: 'Market Demographics',
      attribution_percentage: 1.5,
      statistical_significance_p_value: 0.42,
      correlation_or_coef: 0.03,
      direction: 'Positive Impact',
      evidence_statement: 'Pearson r = +0.03 (Directional Only, p = 0.42)'
    };
    expect(getSupportingEvidence(fcInsignificant)).toBe('No clear association with the observed pattern.');
  });

  it('strictly adheres to causation safety guidelines and excludes technical jargon', () => {
    const sampleFactors: FactorContribution[] = [
      {
        factor_name: 'Gross Sales',
        factor_type: 'Supply & Economics',
        attribution_percentage: 21.1,
        statistical_significance_p_value: 0.0001,
        correlation_or_coef: 0.58,
        direction: 'Positive Impact',
        evidence_statement: ''
      },
      {
        factor_name: 'Cost of Goods',
        factor_type: 'Commercial',
        attribution_percentage: 21.0,
        statistical_significance_p_value: 0.0001,
        correlation_or_coef: 0.52,
        direction: 'Positive Impact',
        evidence_statement: ''
      },
      {
        factor_name: 'Unit Price',
        factor_type: 'Commercial',
        attribution_percentage: 12.6,
        statistical_significance_p_value: 0.005,
        correlation_or_coef: 0.32,
        direction: 'Positive Impact',
        evidence_statement: ''
      },
      {
        factor_name: 'Discount Rate',
        factor_type: 'Commercial',
        attribution_percentage: 15.0,
        statistical_significance_p_value: 0.001,
        correlation_or_coef: -0.45,
        direction: 'Negative Impact',
        evidence_statement: ''
      },
      {
        factor_name: 'Irrelevant Column',
        factor_type: 'Operational',
        attribution_percentage: 0.5,
        statistical_significance_p_value: 0.65,
        correlation_or_coef: 0.01,
        direction: 'Positive Impact',
        evidence_statement: ''
      }
    ];

    const forbiddenWords = ['causes', 'caused by', 'impact', 'drives', 'leads to', 'responsible for', 'p =', 'r =', 'p-value', 'pearson'];

    for (const factor of sampleFactors) {
      const text = getSupportingEvidence(factor).toLowerCase();
      for (const forbidden of forbiddenWords) {
        expect(text).not.toContain(forbidden);
      }
      expect(text).toContain('association');
    }
  });
});
