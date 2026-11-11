import os
import pytest
import pandas as pd
import numpy as np
from app.engines.business_health import BusinessHealthEngine
from app.engines.diagnostic import DiagnosticEngine
from app.engines.root_cause import RootCauseEngine
from app.engines.risk_opportunity import RiskOpportunityEngine
from app.engines.recommendation import RecommendationEngine
from app.engines.evidence_builder import EvidenceBuilder


def test_superstore_distinct_orders_and_aov():
    """Verify Superstore calculates AOV using distinct orders, detects retail domain, and plots timeline."""
    path = os.path.join("backend", "data_storage", "uploads", "Sample - Superstore.csv")
    if not os.path.exists(path):
        pytest.skip("Sample - Superstore.csv not available")

    df = pd.read_csv(path, encoding="latin1")
    health = BusinessHealthEngine.assess_health(df)

    assert health.domain == "retail"
    assert health.domain_label == "Retail & E-Commerce"
    assert health.is_undated_snapshot is False
    assert health.has_health_score is True
    assert 0.0 <= health.overall_health_score <= 100.0
    assert health.overall_status in ["Strong", "Stable", "Vulnerable", "Distressed"]

    # Verify distinct orders vs line items
    overview = health.overview_metrics or {}
    num_txns = overview.get("transactions_count") or overview.get("num_transactions")
    distinct_orders = overview.get("distinct_orders") or overview.get("num_orders")
    assert num_txns == len(df)  # 9,994 line items
    assert distinct_orders == 5009  # 5,009 unique orders
    assert distinct_orders < num_txns

    # Verify AOV: ~$2,297,200.86 / 5,009 = ~$458.61 (NOT divided by 9,994!)
    aov = overview.get("average_order_value") or overview.get("avg_order_value")
    assert aov is not None
    assert 455.0 <= aov <= 465.0
    items_per_order = overview.get("items_per_order")
    assert items_per_order is not None
    assert 1.9 <= items_per_order <= 2.1

    # Verify Timeline
    assert health.timeline_series is not None
    assert len(health.timeline_series) > 0
    assert health.timeline_metadata is not None
    assert health.timeline_metadata.get("is_undated") is False
    assert health.timeline_metadata.get("unit") == "$"


def test_ibm_hr_workforce_adaptive():
    """Verify IBM HR data is classified as workforce, marked as undated snapshot, and has no fake trend score."""
    path = os.path.join("backend", "data_storage", "uploads", "WA_Fn-UseC_-HR-Employee-Attrition.csv")
    if not os.path.exists(path):
        pytest.skip("WA_Fn-UseC_-HR-Employee-Attrition.csv not available")

    df = pd.read_csv(path)
    health = BusinessHealthEngine.assess_health(df)

    assert health.domain == "workforce"
    assert health.domain_label == "Workforce & HR"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False
    assert health.overall_health_score == 0.0
    assert health.overall_status in ["Unavailable", "N/A"]
    assert health.health_score_explanation is not None
    assert "chronological" in health.health_score_explanation.lower()

    # Verify Timeline is empty for undated snapshot
    assert len(health.timeline_series or []) == 0
    assert health.timeline_metadata is not None
    assert health.timeline_metadata.get("is_undated") is True

    # Verify Adaptive KPIs
    kpi_map = {k["id"]: k for k in (health.adaptive_kpis or [])}
    assert "headcount" in kpi_map
    assert kpi_map["headcount"]["value"] == 1470
    assert "attrition_rate" in kpi_map
    assert 15.5 <= kpi_map["attrition_rate"]["value"] <= 16.5
    assert kpi_map["attrition_rate"]["unit"] == "%"
    assert "$" not in kpi_map["attrition_rate"]["formatted_value"]
    assert "avg_income" in kpi_map
    assert kpi_map["avg_income"]["unit"] == "$"
    assert "overtime_rate" in kpi_map
    assert kpi_map["overtime_rate"]["unit"] == "%"


def test_manufacturing_adaptive():
    """Verify manufacturing dataset is classified under manufacturing domain with operational KPIs."""
    path = os.path.join("backend", "app", "sample_data", "manufacturing_supply.csv")
    if not os.path.exists(path):
        pytest.skip("manufacturing_supply.csv not available")

    df = pd.read_csv(path)
    health = BusinessHealthEngine.assess_health(df)

    assert health.domain == "manufacturing"
    assert health.domain_label == "Manufacturing & Operations"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False
    assert health.overall_status in ["Unavailable", "N/A"]

    kpi_map = {k["id"]: k for k in (health.adaptive_kpis or [])}
    assert "batch_count" in kpi_map
    assert "defect_rate" in kpi_map
    assert kpi_map["defect_rate"]["unit"] == "%"
    assert "scrap_cost" in kpi_map
    assert kpi_map["scrap_cost"]["unit"] == "$"
    assert "cycle_time" in kpi_map
    assert kpi_map["cycle_time"]["unit"] == "hours"
    assert "downtime" in kpi_map
    assert kpi_map["downtime"]["unit"] == "minutes"


def test_saas_adaptive():
    """Verify SaaS dataset is classified under saas domain with subscription KPIs."""
    path = os.path.join("backend", "app", "sample_data", "b2b_saas_churn.csv")
    if not os.path.exists(path):
        pytest.skip("b2b_saas_churn.csv not available")

    df = pd.read_csv(path)
    health = BusinessHealthEngine.assess_health(df)

    assert health.domain == "saas"
    assert health.domain_label == "Subscription & SaaS"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False

    kpi_map = {k["id"]: k for k in (health.adaptive_kpis or [])}
    assert "arr" in kpi_map
    assert kpi_map["arr"]["unit"] == "$"
    assert "churn_rate" in kpi_map
    assert kpi_map["churn_rate"]["unit"] == "%"
    assert "account_count" in kpi_map
    assert "active_users" in kpi_map
    assert "nps" in kpi_map
    assert "feature_adoption" in kpi_map


def test_generic_undated_dataset():
    """Verify generic undated datasets display non-financial descriptive statistics without fake trends."""
    df = pd.DataFrame({
        "student_id": [f"STU_{i}" for i in range(80)],
        "course": ["Math", "Physics", "Chemistry", "Biology"] * 20,
        "grade_score": [65.0 + (i % 30) for i in range(80)],
        "study_hours": [5.0 + (i % 25) for i in range(80)]
    })

    health = BusinessHealthEngine.assess_health(df)
    assert health.domain == "general"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False
    assert health.overall_status in ["Unavailable", "N/A"]
    assert len(health.timeline_series or []) == 0

    kpi_map = {k["id"]: k for k in (health.adaptive_kpis or [])}
    assert "total_records" in kpi_map
    assert kpi_map["total_records"]["value"] == 80
    assert "data_completeness" in kpi_map


def test_empty_dataset_handling():
    """Verify empty DataFrame raises ValueError as specified."""
    df_empty = pd.DataFrame()
    with pytest.raises(ValueError, match="Cannot assess business health on an empty dataset"):
        BusinessHealthEngine.assess_health(df_empty)


def test_unsupported_columns_dataset():
    """Verify dataset with non-numeric or ID-only columns handles gracefully without crashing."""
    df_text = pd.DataFrame({
        "row_key": ["K1", "K2", "K3", "K4"],
        "entity_name": ["Alpha", "Beta", "Gamma", "Delta"]
    })
    health = BusinessHealthEngine.assess_health(df_text)
    assert health.domain == "general"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False
    assert len(health.adaptive_kpis or []) >= 1


def test_rate_aggregation_timeline():
    """Verify rate/percentage metric uses mean aggregation on timeline."""
    dates = pd.date_range("2023-01-01", periods=12, freq="ME")
    df = pd.DataFrame({
        "record_date": dates,
        "defect_rate_pct": [1.5 + (i * 0.1) for i in range(12)],
        "category": ["A", "B", "A", "B"] * 3
    })

    health = BusinessHealthEngine.assess_health(df, target_col="defect_rate_pct", date_col="record_date")
    assert health.has_dates is True if hasattr(health, "has_dates") else health.is_undated_snapshot is False
    assert health.timeline_metadata is not None
    assert health.timeline_metadata.get("aggregation_type") == "mean"
    assert health.timeline_metadata.get("unit") == "%"


def test_recommendation_units_and_no_hardcoded_dollars():
    """Verify recommendations and evidence trails respect metric units and do not hardcode $ for non-monetary metrics."""
    df = pd.DataFrame({
        "attrition_rate": [12.0, 18.0, 24.0, 15.0, 22.0, 19.0],
        "department": ["Sales", "Sales", "R&D", "R&D", "HR", "HR"],
        "workload_score": [8.0, 9.0, 7.5, 6.0, 8.5, 7.0]
    })

    diag = DiagnosticEngine.diagnose_variance(df, target_col="attrition_rate", dimensions=["department"])
    rc = RootCauseEngine.analyze_root_cause(df, target_col="attrition_rate", dimensions=["department"])
    risk_opp = RiskOpportunityEngine.identify_risks_and_opportunities(df, "attrition_rate", diag, rc)

    recs = RecommendationEngine.generate_prioritized_recommendations("attrition_rate", diag, rc, risk_opp)
    assert len(recs) >= 1

    # Check evidence text on first recommendation
    rec0 = recs[0]
    assert rec0.evidence is not None
    # Must not contain "$12" or "$18" for percentage rate
    assert "$" not in rec0.evidence
    assert "%" in rec0.evidence

    # Check evidence chains
    chains = EvidenceBuilder.construct_evidence_chains("attrition_rate", diag, rc, risk_opp)
    assert len(chains) >= 1
    extracted_node = [n for n in chains[0].nodes if n.stage == "Data Extracted"][0]
    assert "$" not in extracted_node.metric_or_statistic
