import pandas as pd
import numpy as np
from app.engines.business_health import BusinessHealthEngine
from app.engines.diagnostic import DiagnosticEngine
from app.engines.root_cause import RootCauseEngine
from app.engines.risk_opportunity import RiskOpportunityEngine
from app.engines.evidence_builder import EvidenceBuilder
from app.engines.recommendation import RecommendationEngine
from app.engines.simulation import SimulationEngine
from app.models.schemas import SimulationRequest


def get_mock_df():
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        "revenue": np.random.uniform(100, 500, n),
        "discount": np.random.uniform(0.05, 0.35, n),
        "region": np.random.choice(["East", "West", "Central"], n),
        "product_type": np.random.choice(["Hardware", "Software", "Services"], n),
        "delivery_days": np.random.exponential(3, n)
    })


def test_business_health_engine():
    df = get_mock_df()
    health = BusinessHealthEngine.assess_health(df, target_col="revenue")
    assert 0.0 <= health.overall_health_score <= 100.0
    assert health.overall_status in ["Strong", "Stable", "Vulnerable", "Distressed"]
    assert len(health.kpis) >= 1


def test_diagnostic_engine():
    df = get_mock_df()
    diag = DiagnosticEngine.diagnose_variance(df, target_col="revenue")
    assert diag.focal_metric == "revenue"
    assert len(diag.variance_breakdown) > 0
    assert any(b.direction in ["Drag", "Lift"] for b in diag.variance_breakdown)
    assert len(diag.diagnostic_narrative) > 20


def test_root_cause_engine():
    df = get_mock_df()
    rc = RootCauseEngine.analyze_root_cause(df, target_col="revenue")
    assert len(rc.factor_contributions) > 0
    assert len(rc.pareto_breakdown) > 0
    assert rc.statistical_confidence_level > 0.0
    top_factor = rc.factor_contributions[0]
    assert 0.0 <= top_factor.statistical_significance_p_value <= 1.0


def test_recommendation_and_evidence():
    df = get_mock_df()
    diag = DiagnosticEngine.diagnose_variance(df, target_col="revenue")
    rc = RootCauseEngine.analyze_root_cause(df, target_col="revenue")
    risk_opp = RiskOpportunityEngine.identify_risks_and_opportunities(df, "revenue", diag, rc)
    
    evidence = EvidenceBuilder.construct_evidence_chains("revenue", diag, rc, risk_opp)
    assert len(evidence) >= 1
    assert len(evidence[0].nodes) >= 3

    recs = RecommendationEngine.generate_prioritized_recommendations("revenue", diag, rc, risk_opp)
    assert len(recs) >= 3
    # Check that priority score is sorted descending
    scores = [r.priority_score for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_simulation_engine():
    df = get_mock_df()
    df["profit"] = df["revenue"] * 0.20
    req = SimulationRequest(
        analysis_id="dummy",
        price_change_pct=5.0,
        discount_adjustment_pct=10.0,
        churn_mitigation_pct=15.0,
        operational_efficiency_pct=5.0
    )
    res = SimulationEngine.run_simulation(df, "revenue", req)
    assert res.simulated_revenue > 0
    assert res.simulated_profit > 0
    assert "price_sensitivity_per_pct" in res.sensitivity_breakdown
