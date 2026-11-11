import pytest
import pandas as pd
import numpy as np
from app.engines.simulation import SimulationEngine
from app.models.schemas import SimulationRequest, SimulationOutcome


@pytest.fixture
def mock_df():
    return pd.DataFrame({
        "revenue": [1000.0, 2000.0, 3000.0, 4000.0],
        "profit": [200.0, 400.0, 600.0, 800.0]
    })


def test_neutral_baseline(mock_df):
    req = SimulationRequest(
        analysis_id="test",
        price_change_pct=0.0,
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    outcome = SimulationEngine.run_simulation(mock_df, "revenue", req)
    assert outcome.revenue_delta == 0.0
    assert outcome.profit_delta == 0.0
    assert outcome.net_economic_value_added == 0.0
    assert outcome.risk_adjusted_return == 0.0
    # Profit margin = Net profit / gross revenue * 100
    expected_margin = round(outcome.baseline_profit / outcome.baseline_revenue * 100, 2)
    assert outcome.baseline_margin_pct == expected_margin


def test_positive_and_negative_changes(mock_df):
    req_pos = SimulationRequest(
        analysis_id="test",
        price_change_pct=5.0,
        discount_adjustment_pct=10.0,
        churn_mitigation_pct=10.0,
        operational_efficiency_pct=5.0
    )
    res_pos = SimulationEngine.run_simulation(mock_df, "revenue", req_pos)
    assert res_pos.profit_delta > 0
    assert res_pos.simulated_profit > res_pos.baseline_profit

    req_neg = SimulationRequest(
        analysis_id="test",
        price_change_pct=-5.0,
        discount_adjustment_pct=-10.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    res_neg = SimulationEngine.run_simulation(mock_df, "revenue", req_neg)
    assert res_neg.profit_delta < 0


def test_scenario_comparison_report(mock_df):
    baseline_req = SimulationRequest(
        analysis_id="test",
        price_change_pct=0.0,
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    base_outcome = SimulationEngine.run_simulation(mock_df, "revenue", baseline_req)

    sc_a_req = SimulationRequest(
        analysis_id="test",
        price_change_pct=5.0,
        discount_adjustment_pct=5.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    out_a = SimulationEngine.run_simulation(mock_df, "revenue", sc_a_req)

    sc_b_req = SimulationRequest(
        analysis_id="test",
        price_change_pct=2.0,
        discount_adjustment_pct=10.0,
        churn_mitigation_pct=10.0,
        operational_efficiency_pct=5.0
    )
    out_b = SimulationEngine.run_simulation(mock_df, "revenue", sc_b_req)

    scenarios = [
        {"id": "sc-1", "name": "Scenario A", "parameters": sc_a_req.model_dump(), "projected_outcomes": out_a.model_dump()},
        {"id": "sc-2", "name": "Scenario B", "parameters": sc_b_req.model_dump(), "projected_outcomes": out_b.model_dump()},
    ]

    report = SimulationEngine.compare_scenarios(base_outcome, scenarios)
    assert len(report.scenarios) == 3  # Baseline + 2 scenarios
    assert report.scenarios[0].name == "Baseline"
    assert report.scenarios[0].incremental_value == 0.0

    # Best profit scenario identified
    assert report.best_profit_scenario in ["Scenario A", "Scenario B"]
    assert len(report.comparison_insights) >= 1
    assert any("profit improvement" in ins or "relative profit" in ins for ins in report.comparison_insights)


def test_profit_margin_calculation(mock_df):
    req = SimulationRequest(
        analysis_id="test",
        price_change_pct=3.0,
        discount_adjustment_pct=4.0,
        churn_mitigation_pct=5.0,
        operational_efficiency_pct=2.0
    )
    outcome = SimulationEngine.run_simulation(mock_df, "revenue", req)
    calc_margin = round(outcome.simulated_profit / outcome.simulated_revenue * 100, 2)
    assert outcome.simulated_margin_pct == calc_margin


def test_empty_dataframe_raises(mock_df):
    empty_df = pd.DataFrame()
    req = SimulationRequest(
        analysis_id="test",
        price_change_pct=1.0,
        discount_adjustment_pct=1.0,
        churn_mitigation_pct=1.0,
        operational_efficiency_pct=1.0
    )
    with pytest.raises(ValueError):
        SimulationEngine.run_simulation(empty_df, "revenue", req)


def test_baseline_equality_all_zero_inputs(mock_df):
    """All-zero changes must reproduce baseline values and yield zero incremental value."""
    req = SimulationRequest(
        analysis_id="test",
        price_change_pct=0.0,
        volume_change_pct=0.0,
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    outcome = SimulationEngine.run_simulation(mock_df, "revenue", req)
    assert outcome.simulated_revenue == outcome.baseline_revenue
    assert outcome.simulated_profit == outcome.baseline_profit
    assert outcome.revenue_delta == 0.0
    assert outcome.profit_delta == 0.0
    assert outcome.net_economic_value_added == 0.0
    assert outcome.risk_adjusted_return == 0.0
    assert outcome.margin_delta_pct == 0.0


def test_sales_volume_change_scales_revenue_and_profit_proportionally(mock_df):
    """Sales volume change scales revenue and profit while preserving margin % (constant unit economics)."""
    base_req = SimulationRequest(analysis_id="test")
    base_out = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    # +10% sales volume change
    vol_req = SimulationRequest(analysis_id="test", volume_change_pct=10.0)
    vol_out = SimulationEngine.run_simulation(mock_df, "revenue", vol_req)

    assert vol_out.simulated_revenue == pytest.approx(base_out.baseline_revenue * 1.10, rel=1e-3)
    assert vol_out.simulated_profit == pytest.approx(base_out.baseline_profit * 1.10, rel=1e-3)
    assert vol_out.revenue_delta == pytest.approx(base_out.baseline_revenue * 0.10, rel=1e-3)
    assert vol_out.profit_delta == pytest.approx(base_out.baseline_profit * 0.10, rel=1e-3)
    assert vol_out.simulated_margin_pct == pytest.approx(base_out.baseline_margin_pct, rel=1e-2)
    assert vol_out.margin_delta_pct == 0.0
    assert vol_out.net_economic_value_added > 0.0


def test_cost_reduction_does_not_increase_revenue(mock_df):
    """Ensure operating cost reduction increases profit without increasing revenue when price and volume are unchanged."""
    base_req = SimulationRequest(analysis_id="test")
    base_out = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    cost_req = SimulationRequest(analysis_id="test", operational_efficiency_pct=10.0)
    cost_out = SimulationEngine.run_simulation(mock_df, "revenue", cost_req)

    # Revenue MUST NOT change
    assert cost_out.simulated_revenue == base_out.baseline_revenue
    assert cost_out.revenue_delta == 0.0

    # Profit increases from cost savings
    assert cost_out.simulated_profit > base_out.baseline_profit
    assert cost_out.profit_delta > 0.0
    assert cost_out.simulated_margin_pct > base_out.baseline_margin_pct


def test_validation_rejects_invalid_values(mock_df):
    """Validate inputs: reject invalid values (< -100% price/volume, < 0% cost reduction, > 100% cost reduction)."""
    # Price change < -100%
    with pytest.raises(ValueError, match="Price change percentage cannot be less than -100%"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Price Change", -105.0)

    # Volume change < -100%
    with pytest.raises(ValueError, match="Sales volume change percentage cannot be less than -100%"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Sales Volume Change", -110.0)

    # Cost reduction < 0%
    with pytest.raises(ValueError, match="Operating cost reduction percentage cannot be negative"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Operating Cost Reduction", -5.0)

    # Cost reduction > 100%
    with pytest.raises(ValueError, match="Operating cost reduction percentage cannot exceed 100%"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Operating Cost Reduction", 110.0)


def test_unsupported_interventions_rejected_when_fields_missing():
    """Disable/reject unsupported interventions when required dataset fields are missing."""
    # Dataframe with revenue only (no cost, no profit, no discount)
    rev_only_df = pd.DataFrame({"revenue": [1000.0, 2000.0, 3000.0]})

    # Cost reduction should be rejected because no cost/profit data exists
    with pytest.raises(ValueError, match="Operating Cost Reduction is unsupported"):
        SimulationEngine.validate_scenario_input(rev_only_df, "revenue", "Operating Cost Reduction", 10.0)

    # Discount change should be rejected because no discount column exists
    with pytest.raises(ValueError, match="Discount Change is unsupported"):
        SimulationEngine.validate_scenario_input(rev_only_df, "revenue", "Discount Change", 5.0)


def test_distinguish_percentage_changes_from_percentage_points(mock_df):
    """Distinguish percentage changes from percentage-point changes and reject invalid types."""
    # Price change specified as percentage points should be rejected
    with pytest.raises(ValueError, match="Price change must be specified as a percentage change"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Price Change", 5.0, parameter_type="percentage_points")

    # Sales volume specified as percentage points should be rejected
    with pytest.raises(ValueError, match="Sales volume change must be specified as a percentage change"):
        SimulationEngine.validate_scenario_input(mock_df, "revenue", "Sales Volume Change", 5.0, parameter_type="percentage_points")

    # Dataset with discount column
    df_disc = pd.DataFrame({
        "revenue": [10000.0],
        "profit": [2000.0],
        "discount": [0.15]  # 15% discount
    })
    # Valid percentage points on discount: 5 pp reduction
    res_pp = SimulationEngine.validate_scenario_input(df_disc, "revenue", "Discount Change", 5.0, parameter_type="percentage_points")
    assert res_pp["parameter_type"] == "percentage_points"
    assert res_pp["discount_adjustment_pct"] == 5.0

    # Discount reduction exceeding baseline discount rate should be rejected
    with pytest.raises(ValueError, match="Discount reduction cannot exceed the baseline discount rate"):
        SimulationEngine.validate_scenario_input(df_disc, "revenue", "Discount Change", 25.0, parameter_type="percentage_points")


def test_scenario_comparison_reports_ties_accurately(mock_df):
    """If scenarios tie in profit or revenue, report a tie rather than selecting an unsupported winner."""
    base_req = SimulationRequest(analysis_id="test")
    base_outcome = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    # Two distinct scenarios that result in the EXACT same profit
    # Scenario 1: Price +5% ($500 gain on $10,000 revenue)
    # Scenario 2: Another Price +5% plan
    sc1_out = SimulationEngine.run_simulation(mock_df, "revenue", SimulationRequest(analysis_id="test", price_change_pct=5.0))
    sc2_out = SimulationEngine.run_simulation(mock_df, "revenue", SimulationRequest(analysis_id="test", price_change_pct=5.0))

    scenarios = [
        {"id": "sc-1", "name": "Plan Alpha", "parameters": {"price_change_pct": 5.0}, "projected_outcomes": sc1_out.model_dump()},
        {"id": "sc-2", "name": "Plan Beta", "parameters": {"price_change_pct": 5.0}, "projected_outcomes": sc2_out.model_dump()},
    ]

    report = SimulationEngine.compare_scenarios(base_outcome, scenarios)

    # Tie must be reported
    assert "Tie" in str(report.best_profit_scenario)
    assert any("Tie for highest simulated profit" in ins for ins in report.comparison_insights)
    assert any("Plan Alpha" in ins and "Plan Beta" in ins for ins in report.comparison_insights)


def test_scenario_comparison_all_zero_scenarios_reports_baseline_match(mock_df):
    """When all evaluated scenarios have zero changes, comparison insights report baseline match."""
    base_req = SimulationRequest(analysis_id="test")
    base_outcome = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    zero_out = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    scenarios = [
        {"id": "sc-zero", "name": "Zero Plan", "parameters": {}, "projected_outcomes": zero_out.model_dump()}
    ]

    report = SimulationEngine.compare_scenarios(base_outcome, scenarios)
    assert any("match the neutral baseline with zero incremental value" in ins for ins in report.comparison_insights)


def test_intervention_summary_direction_clarity(mock_df):
    """Ensure Price Change and Sales Volume Change generate clear direction-explicit summaries."""
    base_req = SimulationRequest(analysis_id="test")
    base_outcome = SimulationEngine.run_simulation(mock_df, "revenue", base_req)

    scenarios = [
        {
            "id": "sc-pos-price",
            "name": "Price Increase Plan",
            "parameters": {"intervention_type": "Price Change", "change_percentage": 5.0, "parameter_type": "percentage"},
            "projected_outcomes": {}
        },
        {
            "id": "sc-neg-price",
            "name": "Price Reduction Plan",
            "parameters": {"intervention_type": "Price Change", "change_percentage": -5.0, "parameter_type": "percentage"},
            "projected_outcomes": {}
        },
        {
            "id": "sc-pos-vol",
            "name": "Volume Growth Plan",
            "parameters": {"intervention_type": "Sales Volume Change", "change_percentage": 10.0, "parameter_type": "percentage"},
            "projected_outcomes": {}
        },
        {
            "id": "sc-neg-vol",
            "name": "Volume Decline Plan",
            "parameters": {"intervention_type": "Sales Volume Change", "change_percentage": -10.0, "parameter_type": "percentage"},
            "projected_outcomes": {}
        },
        {
            "id": "sc-cost",
            "name": "Cost Reduction Plan",
            "parameters": {"intervention_type": "Operating Cost Reduction", "change_percentage": 8.0, "parameter_type": "percentage"},
            "projected_outcomes": {}
        },
    ]

    report = SimulationEngine.compare_scenarios(base_outcome, scenarios)
    by_name = {sc.name: sc for sc in report.scenarios}

    assert by_name["Price Increase Plan"].intervention_summary == "Price Increase: +5%"
    assert by_name["Price Reduction Plan"].intervention_summary == "Price Reduction: -5%"
    assert by_name["Volume Growth Plan"].intervention_summary == "Volume Growth: +10%"
    assert by_name["Volume Decline Plan"].intervention_summary == "Volume Decline: -10%"
    assert by_name["Cost Reduction Plan"].intervention_summary == "Cost Reduction: 8%"

