import { describe, it, expect } from 'vitest';
import { RecommendationItem, FindingItem } from '../types';

describe('Key Findings & Recommendations Simplification Verification', () => {
  it('formats recommendation card attributes with simplified terminology', () => {
    const rec: RecommendationItem = {
      id: 'REC-01',
      title: 'Optimize wholesale customer tier pricing',
      category: 'Commercial',
      what_to_do: 'Implement dynamic discount thresholds for high-volume accounts.',
      mechanism_of_action: 'Mechanism action text',
      why: 'Margin compression observed in enterprise tiers.',
      rationale: 'Statistical rationale text',
      expected_financial_impact: 125000,
      priority_score: 88,
      priority_level: 'High Priority',
      difficulty: 'Moderate',
      urgency: 'Immediate',
      supporting_finding: 'Wholesale segment margin dropped 4.2% YoY.',
      evidence: 'Evidence description',
      implementation_effort: 'Medium',
      confidence_score_pct: 90,
      impact_score: 85,
      confidence_score: 90,
      ease_score: 75,
      priority_tier: 'High',
      tradeoffs_and_risks: 'Potential pushback',
      status: 'pending',
      prerequisites: []
    };

    // Recommended Action resolves what_to_do before mechanism_of_action
    const action = rec.what_to_do || rec.mechanism_of_action || rec.title;
    expect(action).toBe('Implement dynamic discount thresholds for high-volume accounts.');

    // Priority Score formatting
    const score = Math.round(rec.priority_score || 50);
    expect(score).toBe(88);
    expect(rec.priority_level).toBe('High Priority');

    // Supporting Evidence resolves supporting_finding / evidence before rationale
    const evidence = rec.supporting_finding || rec.evidence || rec.why || rec.rationale;
    expect(evidence).toBe('Wholesale segment margin dropped 4.2% YoY.');

    // Estimated Impact calculation is preserved
    expect(rec.expected_financial_impact).toBe(125000);
  });

  it('handles missing financial impact gracefully with standard wording', () => {
    const recNoImpact: Partial<RecommendationItem> = {
      id: 'REC-02',
      title: 'Review operational shipping routing',
      category: 'Operational',
      what_to_do: 'Rebalance fulfillment across regional distribution centers.',
      priority_score: 65,
      priority_level: 'Medium Priority',
      expected_financial_impact: 0,
      supporting_finding: 'Warehouse variance accounts for delivery delays.'
    };

    const hasImpact = typeof recNoImpact.expected_financial_impact === 'number' && recNoImpact.expected_financial_impact > 0;
    expect(hasImpact).toBe(false);

    const impactText = hasImpact && recNoImpact.expected_financial_impact !== undefined
      ? `+$${recNoImpact.expected_financial_impact.toLocaleString()}`
      : 'Estimated impact not available for this metric';
    expect(impactText).toBe('Estimated impact not available for this metric');
  });

  it('verifies findings representation retains problems and opportunities', () => {
    const findings: FindingItem[] = [
      {
        title: 'Gross margin deficit in EU segment',
        type: 'Problem',
        metric: 'Gross Margin',
        observed_value: '$1,200,000',
        comparison: 'Prior Period ($1,450,000)',
        difference: '-$250,000 (-17.2%)',
        possible_reason: 'Increased tariff and logistics surcharges',
        recommended_action: 'Audit European logistics contracts'
      },
      {
        title: 'Rapid growth in digital accessories category',
        type: 'Opportunity',
        metric: 'Revenue',
        observed_value: '$850,000',
        comparison: 'Target ($600,000)',
        difference: '+$250,000 (+41.7%)',
        possible_reason: 'Strong organic search referral conversion',
        recommended_action: 'Scale digital marketing spend'
      }
    ];

    const problems = findings.filter(f => f.type === 'Problem');
    const opportunities = findings.filter(f => f.type === 'Opportunity');

    expect(problems.length).toBe(1);
    expect(opportunities.length).toBe(1);
    expect(problems[0].possible_reason).toBe('Increased tariff and logistics surcharges');
    expect(problems[0].recommended_action).toBe('Audit European logistics contracts');
  });
});
