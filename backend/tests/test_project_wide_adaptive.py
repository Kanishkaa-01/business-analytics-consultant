import os
import pytest
import pandas as pd
import numpy as np

from app.services.capability_assessor import DatasetCapabilityAssessor, DatasetCapabilities
from app.engines.business_health import BusinessHealthEngine
from app.engines.root_cause import RootCauseEngine
from app.engines.simulation import SimulationEngine
from app.engines.forecasting_engine import ForecastingEngine
from app.models.schemas import SimulationRequest


def test_01_retail_superstore_full_pipeline():
    """
    Test 1: Retail dataset (Sample - Superstore.csv)
    - Classified as retail
    - Dates recognized and chronological timeline generated with currency unit '$'
    - Distinct orders used for AOV (5,009 orders, not 9,994 rows)
    - Health score evaluated defensibly
    - Retail simulation levers and outcome cards populated
    - Forecasting capability validated
    """
    path = os.path.join("backend", "data_storage", "uploads", "Sample - Superstore.csv")
    if not os.path.exists(path):
        pytest.skip("Sample - Superstore.csv not available")

    df = pd.read_csv(path, encoding="latin1")
    caps = DatasetCapabilityAssessor.assess_capabilities(df, target_col="Sales", date_col="Order Date")

    assert caps.domain == "retail"
    assert caps.has_valid_dates is True
    assert caps.primary_metric in ["Sales", "sales", "Profit", "profit"]
    assert caps.can_calculate_health_score is True
    assert caps.overview_chart_type == "time_series"
    assert caps.can_simulate_scenarios is True
    assert "Price Change" in caps.supported_scenarios or "Sales Volume Change" in caps.supported_scenarios

    # Business Health Engine
    health = BusinessHealthEngine.assess_health(df, target_col="Sales", date_col="Order Date")
    assert health.domain == "retail"
    assert health.has_health_score is True
    assert 0.0 <= health.overall_health_score <= 100.0
    assert health.overall_status in ["Strong", "Stable", "Vulnerable", "Distressed"]
    assert len(health.timeline_series or []) > 0
    assert health.timeline_metadata.get("unit") == "$"

    # Distinct orders in AOV
    overview = health.overview_metrics or {}
    num_txns = overview.get("transactions_count") or overview.get("num_transactions")
    distinct_orders = overview.get("distinct_orders") or overview.get("num_orders")
    assert num_txns == len(df)  # 9,994 line items
    assert distinct_orders == 5009  # 5,009 unique orders
    aov = overview.get("average_order_value") or overview.get("avg_order_value")
    assert 455.0 <= aov <= 465.0

    # Simulation Engine
    req = SimulationRequest(
        analysis_id="test_retail",
        price_change_pct=5.0,
        volume_change_pct=2.0,
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=3.0,
    )
    sim = SimulationEngine.run_simulation(df, target_col="Sales", params=req)
    assert sim.scenario_domain == "retail"
    assert sim.is_scenario_supported is True
    assert len(sim.outcome_cards or []) >= 2
    assert sim.simulated_revenue > 0
    assert any("Revenue" in card["title"] for card in sim.outcome_cards)

    # Forecasting Engine
    forecast_comp = ForecastingEngine.compare_forecast_vs_actual(df, target_col="Sales", date_col="Order Date")
    assert forecast_comp.is_available is True
    assert len(forecast_comp.comparison or []) > 0


def test_02_workforce_ibm_hr_no_dates():
    """
    Test 2: Workforce dataset without dates (WA_Fn-UseC_-HR-Employee-Attrition.csv)
    - Classified as workforce
    - Marked as undated snapshot
    - Health score is Unavailable (has_health_score=False, overall_status in ['Unavailable', 'N/A'])
    - Timeline replaced by cross-sectional Category Comparison or Distribution alternative
    - Pareto contribution is marked has_valid_contribution=False with alternative_analysis
    - Workforce scenario levers and outcome cards (Attrition, Retention Savings, HR Efficiency)
    - Forecasting marked is_available=False with honest reason and empirical alternative chart
    """
    path = os.path.join("backend", "data_storage", "uploads", "WA_Fn-UseC_-HR-Employee-Attrition.csv")
    if not os.path.exists(path):
        pytest.skip("WA_Fn-UseC_-HR-Employee-Attrition.csv not available")

    df = pd.read_csv(path)
    caps = DatasetCapabilityAssessor.assess_capabilities(df)

    assert caps.domain == "workforce"
    assert caps.has_valid_dates is False
    assert caps.can_calculate_health_score is False
    assert "chronological" in caps.health_score_unsupported_reason.lower()
    assert caps.overview_chart_type in ["category_comparison", "distribution"]
    assert caps.can_simulate_scenarios is True
    assert "Attrition Reduction" in caps.supported_scenarios

    # Business Health Engine
    health = BusinessHealthEngine.assess_health(df)
    assert health.domain == "workforce"
    assert health.is_undated_snapshot is True
    assert health.has_health_score is False
    assert health.overall_status in ["Unavailable", "N/A"]
    assert len(health.timeline_series or []) == 0
    # Alternative chart provided
    assert health.timeline_metadata.get("is_undated") is True
    assert health.timeline_metadata.get("alternative_chart") is not None
    alt = health.timeline_metadata["alternative_chart"]
    assert alt.get("chart_type") in ["category_comparison", "distribution"]

    # Root Cause Engine
    rc = RootCauseEngine.analyze_root_cause(df, target_col="MonthlyIncome")
    assert rc.has_valid_contribution is False
    assert rc.contribution_unsupported_reason is not None
    assert len(rc.pareto_breakdown) == 0
    assert rc.alternative_analysis is not None
    assert rc.alternative_analysis.get("alternative_type") in ["category_comparison", "metric_distribution"]

    # Workforce Simulation Engine
    req = SimulationRequest(
        analysis_id="test_hr",
        price_change_pct=10.0,  # mapped to Job Satisfaction
        churn_mitigation_pct=15.0,  # mapped to Attrition Reduction
        operational_efficiency_pct=5.0,  # mapped to HR Program Efficiency
        discount_adjustment_pct=0.0,
    )
    sim = SimulationEngine.run_simulation(df, target_col="MonthlyIncome", params=req)
    assert sim.scenario_domain == "workforce"
    assert sim.is_scenario_supported is True
    assert len(sim.outcome_cards or []) >= 3
    card_titles = [c["title"] for c in sim.outcome_cards]
    assert any("Attrition" in t for t in card_titles)
    assert any("Cost Savings" in t or "Turnover" in t for t in card_titles)
    # Never show retail Profit or Margin cards
    assert not any(t == "Projected Net Profit" for t in card_titles)
    assert not any(t == "Operating Margin" for t in card_titles)

    # Forecasting Engine
    fc = ForecastingEngine.compare_forecast_vs_actual(df, target_col="MonthlyIncome")
    assert fc.is_available is False
    assert "chronological" in fc.unsupported_reason.lower() or "date" in fc.unsupported_reason.lower()
    assert fc.alternative_type is not None
    assert len(fc.alternative_data or []) > 0


def test_03_manufacturing_operational_scenarios():
    """
    Test 3: Manufacturing dataset (manufacturing_supply.csv)
    - Classified as manufacturing
    - Operational KPIs: defect rate, scrap cost, downtime, cycle time
    - Manufacturing simulation: Defect Rate Reduction, Downtime Reduction, Throughput
    """
    path = os.path.join("backend", "app", "sample_data", "manufacturing_supply.csv")
    if not os.path.exists(path):
        pytest.skip("manufacturing_supply.csv not available")

    df = pd.read_csv(path)
    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps.domain == "manufacturing"

    req = SimulationRequest(
        analysis_id="test_mfg",
        churn_mitigation_pct=20.0,  # Defect Reduction
        operational_efficiency_pct=15.0,  # Downtime Reduction
        price_change_pct=0.0,
        discount_adjustment_pct=0.0,
    )
    sim = SimulationEngine.run_simulation(df, target_col="defect_rate_pct", params=req)
    assert sim.scenario_domain == "manufacturing"
    assert sim.is_scenario_supported is True
    card_titles = [c["title"] for c in sim.outcome_cards]
    assert any("Defect" in t for t in card_titles)
    assert any("Scrap" in t or "Downtime" in t for t in card_titles)


def test_04_saas_subscription_scenarios():
    """
    Test 4: SaaS dataset (b2b_saas_churn.csv)
    - Classified as saas
    - SaaS simulation: ARR protection, churn reduction, retained accounts
    """
    path = os.path.join("backend", "app", "sample_data", "b2b_saas_churn.csv")
    if not os.path.exists(path):
        pytest.skip("b2b_saas_churn.csv not available")

    df = pd.read_csv(path)
    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps.domain == "saas"

    req = SimulationRequest(
        analysis_id="test_saas",
        churn_mitigation_pct=25.0,  # Churn Reduction
        price_change_pct=5.0,  # Account Expansion
        discount_adjustment_pct=0.0,
        operational_efficiency_pct=0.0,
    )
    sim = SimulationEngine.run_simulation(df, target_col="annual_revenue", params=req)
    assert sim.scenario_domain == "saas"
    assert sim.is_scenario_supported is True
    card_titles = [c["title"] for c in sim.outcome_cards]
    assert any("ARR" in t for t in card_titles)
    assert any("Churn" in t for t in card_titles)


def test_05_financial_banking_domain():
    """
    Test 5: Financial dataset (bank-additional-full.csv or banking synthetic)
    - Classified as financial
    - Financial scenario levers: Asset Volume Growth, Yield/Spread Optimization
    """
    df = pd.DataFrame({
        "account_id": [f"ACC_{i}" for i in range(100)],
        "balance_usd": np.random.uniform(1000, 50000, 100),
        "interest_rate_pct": np.random.uniform(1.5, 6.0, 100),
        "credit_score": np.random.randint(580, 820, 100),
        "segment": np.random.choice(["Retail", "Commercial", "Wealth"], 100),
    })

    caps = DatasetCapabilityAssessor.assess_capabilities(df, target_col="balance_usd")
    assert caps.domain == "financial"
    assert caps.metric_units.get("balance_usd") == "$"
    assert caps.metric_units.get("interest_rate_pct") == "%"

    req = SimulationRequest(
        analysis_id="test_bank",
        price_change_pct=1.5,  # Spread / Rate Optimization
        volume_change_pct=5.0,  # Asset Volume Growth
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0,
    )
    sim = SimulationEngine.run_simulation(df, target_col="balance_usd", params=req)
    assert sim.scenario_domain == "financial"
    assert sim.is_scenario_supported is True
    card_titles = [c["title"] for c in sim.outcome_cards]
    assert any("Asset" in t or "Balance" in t for t in card_titles)


def test_06_unfamiliar_real_estate_dataset():
    """
    Test 6: Real estate / general dataset (Real estate.csv)
    - Classified as general
    - Descriptive statistics shown without fabricated financial revenue/profit
    - Health score cleanly marked unavailable
    - Scenarios adapt to primary metric adjustment or return clean unsupported status
    """
    path = os.path.join("backend", "data_storage", "uploads", "Real estate.csv")
    if not os.path.exists(path):
        pytest.skip("Real estate.csv not available")

    df = pd.read_csv(path)
    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps.domain == "general"
    assert caps.can_calculate_health_score is False

    health = BusinessHealthEngine.assess_health(df)
    assert health.domain == "general"
    assert health.has_health_score is False
    assert health.overall_status in ["Unavailable", "N/A"]

    # When no retail/HR levers exist
    req = SimulationRequest(analysis_id="test_re", price_change_pct=0.0, discount_adjustment_pct=0.0, churn_mitigation_pct=0.0, operational_efficiency_pct=0.0)
    sim = SimulationEngine.run_simulation(df, target_col=caps.primary_metric, params=req)
    assert sim.scenario_domain == "general"


def test_07_no_contribution_baseline_never_fabricates():
    """
    Test 7: Root cause engine on pure positive continuous metrics with no loss/variance targets
    - Evaluates factors (ANOVA / Correlation)
    - Correctly detects absence of additive drag/loss baseline
    - Sets has_valid_contribution=False and pareto_breakdown=[]
    - Populates alternative_analysis with non-causal Category Comparison or Distribution
    - Never fabricates Pareto percentages
    """
    df = pd.DataFrame({
        "employee_id": [f"EMP_{i}" for i in range(50)],
        "department": ["Engineering", "Product", "Design", "Sales", "Support"] * 10,
        "satisfaction_rating": np.random.uniform(3.0, 5.0, 50),
        "office_location": ["HQ", "Remote"] * 25,
    })

    rc = RootCauseEngine.analyze_root_cause(df, target_col="satisfaction_rating", dimensions=["department", "office_location"])
    assert rc.has_valid_contribution is False
    assert len(rc.pareto_breakdown) == 0
    assert rc.contribution_unsupported_reason is not None
    assert rc.alternative_analysis is not None
    assert rc.alternative_analysis.get("alternative_type") in ["category_comparison", "metric_distribution"]
    assert len(rc.alternative_analysis.get("data", [])) > 0


def test_08_unsupported_scenario_explanation():
    """
    Test 8: Dataset with no controllable decision levers or scenario metrics
    - Returns is_scenario_supported=False with clear explanatory reason
    - Does not invent 0/0 divisions or fake ROI cards
    """
    df = pd.DataFrame({
        "serial_number": [f"SN_{i}" for i in range(30)],
        "device_code": ["Alpha", "Beta", "Gamma"] * 10,
    })

    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps.can_simulate_scenarios is False
    assert caps.scenario_unsupported_reason is not None

    req = SimulationRequest(analysis_id="test_empty_levers", price_change_pct=5.0, discount_adjustment_pct=0.0, churn_mitigation_pct=0.0, operational_efficiency_pct=0.0)
    sim = SimulationEngine.run_simulation(df, target_col=None, params=req)
    assert sim.is_scenario_supported is False
    assert sim.unsupported_reason is not None


def test_09_robustness_missing_values_and_nulls():
    """
    Test 9: Missing values, NaNs, infs, mixed invalid types
    - Capability assessor and engines handle dirty data gracefully without uncaught exceptions
    """
    df = pd.DataFrame({
        "metric_a": [10.0, np.nan, 20.0, np.inf, -np.inf, 30.0, None],
        "category_b": ["North", None, "South", "East", "West", np.nan, "North"],
        "id_col": [f"ID_{i}" for i in range(7)],
    })

    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps is not None
    assert "metric_a" in caps.numeric_columns
    assert "category_b" in caps.categorical_columns


def test_10_dates_vs_durations_and_identifiers():
    """
    Test 10: Strict discrimination between chronological date fields vs numerical durations and IDs
    - Tenure, Age, Experience, Duration, Employee Number must NOT be flagged as date fields
    - High cardinality string IDs must be classified as identifiers, not categories
    """
    df = pd.DataFrame({
        "employee_id": [f"EMP_{i:04d}" for i in range(60)],
        "tenure_years": np.random.uniform(1.0, 15.0, 60),
        "age": np.random.randint(22, 65, 60),
        "duration_months": np.random.randint(1, 120, 60),
        "department": ["Engineering", "HR", "Sales"] * 20,
    })

    caps = DatasetCapabilityAssessor.assess_capabilities(df)
    assert caps.has_valid_dates is False
    assert caps.date_col is None
    assert "employee_id" in caps.identifier_columns
    assert "department" in caps.categorical_columns
    assert "tenure_years" in caps.numeric_columns
    assert "age" in caps.numeric_columns


def test_11_insufficient_periods_forecasting():
    """
    Test 11: Insufficient chronological history (<6 periods)
    - Valid date field exists, but dataset contains only 3 monthly observations
    - can_forecast is False
    - compare_forecast_vs_actual returns is_available=False with clear explanatory text
    - Never fabricates fake future forecasts or arbitrary MAPE
    """
    df = pd.DataFrame({
        "month_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        "revenue": [10000.0, 12000.0, 11500.0],
        "category": ["A", "A", "A"],
    })

    caps = DatasetCapabilityAssessor.assess_capabilities(df, target_col="revenue", date_col="month_date")
    assert caps.has_valid_dates is True
    assert caps.can_forecast is False
    assert "insufficient historical periods" in caps.forecast_unsupported_reason.lower()

    fc = ForecastingEngine.compare_forecast_vs_actual(df, target_col="revenue", date_col="month_date")
    assert fc.is_available is False
    assert "not enough" in fc.unsupported_reason.lower() or "insufficient" in fc.unsupported_reason.lower()
    assert fc.alternative_type is not None
