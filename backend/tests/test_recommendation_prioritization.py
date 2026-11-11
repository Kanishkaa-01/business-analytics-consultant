import pytest
from app.engines.recommendation import RecommendationEngine
from app.models.schemas import (
    DiagnosticReport,
    RootCauseReport,
    RisksAndOpportunitiesReport,
    VarianceBreakdownItem,
    FactorContribution,
    ParetoItem,
    RiskItem,
    OpportunityItem
)


def test_calculate_priority_score_formula():
    """Verify formula: (impact*10)*0.40 + (confidence*10)*0.25 + (ease*10)*0.20 + (severity*10)*0.15"""
    # impact=10, conf=10, ease=10, sev=10 -> 40 + 25 + 20 + 15 = 100
    score_max = RecommendationEngine.calculate_priority_score(10.0, 10.0, 10.0, 10.0)
    assert score_max == 100.0

    # impact=8, conf=8, ease=8, sev=8 -> 32 + 20 + 16 + 12 = 80.0
    score_80 = RecommendationEngine.calculate_priority_score(8.0, 8.0, 8.0, 8.0)
    assert score_80 == 80.0

    # impact=6, conf=6, ease=6, sev=6 -> 24 + 15 + 12 + 9 = 60.0
    score_60 = RecommendationEngine.calculate_priority_score(6.0, 6.0, 6.0, 6.0)
    assert score_60 == 60.0


def test_priority_levels():
    """Verify priority level thresholds: 80+ High, 60-79 Medium, <60 Lower"""
    assert RecommendationEngine.get_priority_level(85.0) == "High Priority"
    assert RecommendationEngine.get_priority_level(80.0) == "High Priority"
    assert RecommendationEngine.get_priority_level(79.9) == "Medium Priority"
    assert RecommendationEngine.get_priority_level(60.0) == "Medium Priority"
    assert RecommendationEngine.get_priority_level(59.9) == "Lower Priority"
    assert RecommendationEngine.get_priority_level(30.0) == "Lower Priority"


def test_clamping_and_fallback_values():
    """Verify graceful clamping when values exceed bounds or are missing"""
    score_clamped_high = RecommendationEngine.calculate_priority_score(25.0, 15.0, 12.0, 20.0)
    assert score_clamped_high == 100.0

    score_clamped_low = RecommendationEngine.calculate_priority_score(-5.0, 0.0, -10.0, -1.0)
    # clamped to 1.0 each: 4 + 2.5 + 2 + 1.5 = 10.0
    assert score_clamped_low == 10.0

    # None falls back safely
    score_none = RecommendationEngine.calculate_priority_score(None, None, None, None)
    assert 0.0 <= score_none <= 100.0


def test_generate_prioritized_recommendations_sorted():
    """Verify recommendations are sorted descending by Priority Score and contain Phase 14 standardized fields"""
    diag = DiagnosticReport(
        focal_metric="revenue",
        total_variance=-50000.0,
        variance_pct=-12.5,
        variance_breakdown=[
            VarianceBreakdownItem(
                dimension="Region",
                segment="West",
                baseline_value=200000.0,
                actual_value=150000.0,
                variance=-50000.0,
                variance_pct=-25.0,
                contribution_share_pct=70.0,
                direction="Drag"
            ),
            VarianceBreakdownItem(
                dimension="Region",
                segment="East",
                baseline_value=100000.0,
                actual_value=120000.0,
                variance=20000.0,
                variance_pct=20.0,
                contribution_share_pct=30.0,
                direction="Lift"
            )
        ],
        segment_diagnostics=[],
        anomalies_detected=[],
        diagnostic_narrative="Regional variance observed."
    )

    root_cause = RootCauseReport(
        primary_root_cause="Regional underperformance in West",
        secondary_root_causes=[],
        factor_contributions=[
            FactorContribution(
                factor_name="Discounting",
                factor_type="Commercial",
                attribution_percentage=65.0,
                statistical_significance_p_value=0.01,
                correlation_or_coef=-0.72,
                direction="Negative Impact",
                evidence_statement="Excessive discounts"
            )
        ],
        pareto_breakdown=[
            ParetoItem(entity="SKU-A", loss_or_impact=30000.0, cumulative_percentage=60.0, is_vital_few=True),
            ParetoItem(entity="SKU-B", loss_or_impact=15000.0, cumulative_percentage=90.0, is_vital_few=True)
        ],
        causal_tree_structure={},
        statistical_confidence_level=85.0,
        methodology_notes="Regression"
    )

    risk_opp = RisksAndOpportunitiesReport(
        total_exposure_at_risk=40000.0,
        total_opportunity_upside=25000.0,
        risk_profile_rating="Moderate",
        risks=[
            RiskItem(
                id="RSK-01",
                title="Margin Compression Risk",
                category="Margin Compression",
                severity="High",
                probability_pct=75.0,
                estimated_financial_exposure=30000.0,
                root_cause_ref="Discounting",
                early_warning_signals=["Discount > 20%"],
                mitigation_window_days=30
            )
        ],
        opportunities=[
            OpportunityItem(
                id="OPP-01",
                title="East Expansion",
                category="Market Expansion",
                potential_value_gain=25000.0,
                feasibility="High",
                confidence_level_pct=80.0,
                target_segment="East",
                strategic_rationale="High organic growth"
            )
        ]
    )

    recs = RecommendationEngine.generate_prioritized_recommendations("revenue", diag, root_cause, risk_opp)
    assert len(recs) >= 3

    # Check sorting descending
    for i in range(len(recs) - 1):
        assert recs[i].priority_score >= recs[i + 1].priority_score

    # Check standardized fields on every item
    for r in recs:
        assert r.priority_score is not None
        assert 0.0 <= r.priority_score <= 100.0
        assert r.priority_level in ["High Priority", "Medium Priority", "Lower Priority"]
        assert r.recommendation is not None
        assert r.reason is not None
        assert r.supporting_finding is not None
        assert r.decision_status == "Pending Review"
