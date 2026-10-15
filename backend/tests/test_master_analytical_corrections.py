import pytest
import pandas as pd
import numpy as np

from app.services.semantic_metrics import SemanticMetricDetector
from app.services.temporal_helper import TemporalHelper
from app.services.quality_profiler import QualityProfiler
from app.engines.business_health import BusinessHealthEngine
from app.engines.simulation import SimulationEngine
from app.engines.diagnostic import DiagnosticEngine
from app.engines.root_cause import RootCauseEngine
from app.models.schemas import SimulationRequest


class TestMasterAnalyticalCorrections:
    """
    Comprehensive verification suite for Master Prompt corrections across:
    AREA 1 - Core Analytics / Methodology
    AREA 2 - What-If Scenario Simulator
    AREA 3 - Business Health Index
    """

    # -------------------------------------------------------------
    # AREA 1: Core Analytics & Semantic Metric Detection
    # -------------------------------------------------------------
    def test_semantic_metric_subtypes_recognition(self):
        """Verify recognition of various revenue, profit, cost, and discount subtypes."""
        df = pd.DataFrame({
            "gross_sales": [1000.0, 2000.0, 3000.0],
            "operating_profit": [200.0, 400.0, 600.0],
            "cogs": [700.0, 1400.0, 2100.0],
            "discount_pct": [0.10, 0.15, 0.05],
            "qty": [10, 20, 30]
        })
        detected = SemanticMetricDetector.detect_metrics(df)

        assert detected["revenue"]["column"] == "gross_sales"
        assert detected["revenue"]["label"] == "Gross Sales"
        assert detected["profit"]["column"] == "operating_profit"
        assert detected["profit"]["label"] == "Operating Profit"
        assert detected["cost"]["column"] == "cogs"
        assert detected["cost"]["label"] == "COGS"
        assert detected["discount"]["column"] == "discount_pct"
        assert detected["quantity"]["column"] == "qty"

    def test_customer_identifier_vs_tier_separation(self):
        """CustomerID must be identified as an entity ID, customer_tier must NEVER be counted as customers."""
        df = pd.DataFrame({
            "customer_id": [101, 102, 103, 104, 105],
            "customer_tier": ["Gold", "Silver", "Gold", "Bronze", "Silver"],
            "net_revenue": [500.0, 300.0, 800.0, 200.0, 400.0]
        })
        detected = SemanticMetricDetector.detect_metrics(df)

        assert detected["customer_identifier"]["column"] == "customer_id"
        assert detected["customer_segment"]["column"] == "customer_tier"
        assert detected["customer_identifier"]["column"] != "customer_tier"

        # Verify BusinessHealthEngine counts distinct customer_id, not customer_tier
        health = BusinessHealthEngine.assess_health(df, target_col="net_revenue")
        assert health.overview_metrics["unique_customers"] == 5

    def test_customer_tier_only_dataset_does_not_invent_customer_count(self):
        """When dataset has customer_tier but no customer_id, unique_customers must be None."""
        df = pd.DataFrame({
            "customer_tier": ["Gold", "Silver", "Gold", "Bronze", "Silver"],
            "net_revenue": [500.0, 300.0, 800.0, 200.0, 400.0]
        })
        detected = SemanticMetricDetector.detect_metrics(df)
        assert detected["customer_identifier"]["column"] is None
        assert detected["customer_segment"]["column"] == "customer_tier"

        health = BusinessHealthEngine.assess_health(df, target_col="net_revenue")
        assert health.overview_metrics["unique_customers"] is None

    def test_binary_columns_not_flagged_as_iqr_outliers(self):
        """Binary 0/1 columns (e.g. returned, churned) must NOT have IQR outliers calculated."""
        # 100 rows, 10 returns (10% positive rate, continuous IQR would flag all 10 as outliers)
        df = pd.DataFrame({
            "net_revenue": np.random.uniform(100, 200, 100),
            "is_returned": [1] * 10 + [0] * 90
        })
        detected = SemanticMetricDetector.detect_metrics(df)
        assert "is_returned" in detected["binary_cols"]

        report = QualityProfiler.audit_dataset(df)
        ret_metric = next(m for m in report.column_metrics if m.column == "is_returned")
        assert ret_metric.outlier_count == 0
        assert ret_metric.outlier_percentage == 0.0

    def test_derived_variable_filtering_in_root_cause(self):
        """Mathematical identities (revenue - cost = profit) must not crowd out operational drivers."""
        np.random.seed(42)
        n = 100
        rev = np.random.uniform(500, 1000, n)
        cost = np.random.uniform(200, 400, n)
        profit = rev - cost
        channel = np.random.choice(["Online", "Retail", "Wholesale"], n)
        region = np.random.choice(["North", "South", "East"], n)

        df = pd.DataFrame({
            "revenue": rev,
            "cost": cost,
            "profit": profit,
            "channel": channel,
            "region": region
        })

        rc = RootCauseEngine.analyze_root_cause(df, target_col="profit")
        # Factors surfaced should include channel or region, not just revenue/cost tautologies
        factor_names = [f.factor_name.lower() for f in rc.factor_contributions]
        assert any("channel" in fn or "region" in fn for fn in factor_names)

    def test_temporal_helper_zero_and_negative_baseline(self):
        """Calculate variance cleanly handles zero baseline and negative baseline."""
        diff, var_pct = TemporalHelper.calculate_variance(100.0, 0.0)
        assert diff == 100.0
        assert var_pct == 0.0  # Safe fallback without ZeroDivisionError

        # Improving from loss (-100) to smaller loss (-50) is +50%
        diff_neg, var_pct_neg = TemporalHelper.calculate_variance(-50.0, -100.0)
        assert diff_neg == 50.0
        assert var_pct_neg == 50.0

    def test_temporal_chronological_vs_record_order_fallback(self):
        """Dates trigger chronological split; lack of dates triggers record-order fallback with explicit warning."""
        df_with_dates = pd.DataFrame({
            "order_date": pd.date_range("2023-01-01", periods=10, freq="D"),
            "sales": np.arange(10) * 100.0
        })
        res_dates = TemporalHelper.analyze_temporal_structure(df_with_dates, date_col="order_date")
        assert res_dates["has_dates"] is True
        assert res_dates["is_record_order"] is False
        assert "Earlier Period" in res_dates["baseline_label"]

        df_no_dates = pd.DataFrame({
            "category": ["A", "B", "C", "D"],
            "sales": [10.0, 20.0, 30.0, 40.0]
        })
        res_no_dates = TemporalHelper.analyze_temporal_structure(df_no_dates)
        assert res_no_dates["has_dates"] is False
        assert res_no_dates["is_record_order"] is True
        assert "fallback" in res_no_dates["methodological_note"].lower()

    # -------------------------------------------------------------
    # AREA 2: What-If Scenario Simulator
    # -------------------------------------------------------------
    def test_simulation_discount_updates_simulated_revenue_and_profit(self):
        """Adjusting Discount Change lever MUST update simulated revenue, profit, and margin."""
        df = pd.DataFrame({
            "revenue": [1000.0, 2000.0, 3000.0, 4000.0],
            "profit": [200.0, 400.0, 600.0, 800.0],
            "discount": [0.10, 0.15, 0.05, 0.10]
        })
        baseline_req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        base_res = SimulationEngine.run_simulation(df, "revenue", baseline_req)

        # Apply +5% discount reduction
        disc_req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=5.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        disc_res = SimulationEngine.run_simulation(df, "revenue", disc_req)

        assert disc_res.simulated_revenue > base_res.simulated_revenue
        assert disc_res.simulated_profit > base_res.simulated_profit
        assert disc_res.revenue_delta > 0.0
        assert disc_res.profit_delta > 0.0
        assert disc_res.simulated_margin_pct > base_res.simulated_margin_pct

    def test_simulation_cost_efficiency_updates_profit_only(self):
        """Adjusting Cost Efficiency lever MUST update simulated profit and margin without altering revenue."""
        df = pd.DataFrame({
            "revenue": [1000.0, 2000.0, 3000.0, 4000.0],
            "cost": [700.0, 1400.0, 2100.0, 2800.0],
            "profit": [300.0, 600.0, 900.0, 1200.0]
        })
        base_req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        base_res = SimulationEngine.run_simulation(df, "revenue", base_req)

        # Apply +10% cost reduction
        cost_req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=10.0
        )
        cost_res = SimulationEngine.run_simulation(df, "revenue", cost_req)

        # Revenue remains exactly at baseline
        assert cost_res.simulated_revenue == base_res.baseline_revenue
        assert cost_res.revenue_delta == 0.0

        # Profit increases by cost savings
        assert cost_res.simulated_profit > base_res.baseline_profit
        assert cost_res.profit_delta > 0.0
        assert cost_res.simulated_margin_pct > base_res.baseline_margin_pct

    def test_simulation_neutral_baseline_immutable_zero_deltas(self):
        """Zero inputs return exact baseline with zero deltas."""
        df = pd.DataFrame({
            "revenue": [5000.0, 10000.0],
            "profit": [1000.0, 2000.0]
        })
        req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        res = SimulationEngine.run_simulation(df, "revenue", req)
        assert res.simulated_revenue == 15000.0
        assert res.simulated_profit == 3000.0
        assert res.revenue_delta == 0.0
        assert res.profit_delta == 0.0
        assert res.margin_delta_pct == 0.0

    def test_simulation_dynamic_sensitivity_table(self):
        """Sensitivity table dynamically evaluates +1% marginal shift for active levers."""
        df = pd.DataFrame({
            "revenue": [100000.0],
            "cost": [60000.0],
            "profit": [40000.0],
            "discount": [0.10]
        })
        req = SimulationRequest(
            analysis_id="test",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        res = SimulationEngine.run_simulation(df, "revenue", req)
        assert res.sensitivity_table is not None
        assert len(res.sensitivity_table) >= 3

        # Price lever +1% on $100,000 = $1,000
        price_step = next(item for item in res.sensitivity_table if "Price" in item["lever"])
        assert price_step["revenue_impact"] == 1000.0

        # Cost lever +1% on $60,000 cost = $600 profit impact
        cost_step = next(item for item in res.sensitivity_table if "Cost" in item["lever"])
        assert cost_step["profit_impact"] == 600.0

    # -------------------------------------------------------------
    # AREA 3: Business Health Index
    # -------------------------------------------------------------
    def test_health_index_continuous_trend_normalization(self):
        """Trend normalization produces smooth values, avoiding discrete steps."""
        # Test varying trend percentage points
        score_15 = BusinessHealthEngine._normalize_trend(15.0)
        score_5 = BusinessHealthEngine._normalize_trend(5.0)
        score_neg5 = BusinessHealthEngine._normalize_trend(-5.0)
        score_neg15 = BusinessHealthEngine._normalize_trend(-15.0)

        # Higher growth yields higher score continuously
        assert 100.0 >= score_15 > score_5 > score_neg5 > score_neg15 >= 0.0

    def test_health_index_dynamic_weight_renormalization(self):
        """When Profit and Discount are absent, available components dynamically renormalize to 100%."""
        # Dataset with ONLY volume and records (no revenue, profit, cost, or discount)
        df = pd.DataFrame({
            "units_sold": [10, 20, 30, 40, 50, 60, 70, 80]
        })
        health = BusinessHealthEngine.assess_health(df, target_col="units_sold")

        assert health.health_breakdown is not None
        assert len(health.health_breakdown) > 0

        total_weight = sum(item["weight_pct"] for item in health.health_breakdown)
        assert round(total_weight, 0) == 100.0

        # Weighted score sum matches overall health score
        weighted_sum = sum(item["weighted_score"] for item in health.health_breakdown)
        assert round(weighted_sum, 1) == health.overall_health_score

    def test_health_index_component_breakdown_full_schema(self):
        """Full schema dataset populates all 5 components with appropriate base weights."""
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=10, freq="D"),
            "net_revenue": [1000.0 * (1 + i * 0.05) for i in range(10)],
            "net_profit": [200.0 * (1 + i * 0.05) for i in range(10)],
            "quantity": [10 + i for i in range(10)],
            "discount": [0.08] * 10
        })
        health = BusinessHealthEngine.assess_health(df, target_col="net_revenue", date_col="date")

        assert health.health_breakdown is not None
        components = [item["component"] for item in health.health_breakdown]
        assert "Primary Metric Trend" in components
        assert "Profit Trend" in components
        assert "Profit Margin" in components
        assert "Volume Trend" in components
        assert "Discount Pressure" in components

        # Primary observed pressure is populated
        assert health.primary_pressure is not None
        assert "component" in health.primary_pressure
        assert "description" in health.primary_pressure

    def test_health_index_centralized_thresholds(self):
        """Categorization strictly follows Strong (>=80), Stable (60-79.9), Vulnerable (40-59.9), Distressed (<40)."""
        # Distressed dataset (declining performance)
        df_distressed = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=20, freq="D"),
            "revenue": [1000.0] * 10 + [200.0] * 10,
            "profit": [200.0] * 10 + [-100.0] * 10,
            "discount": [0.45] * 20
        })
        health_dist = BusinessHealthEngine.assess_health(df_distressed, target_col="revenue", date_col="date")
        assert health_dist.overall_health_score < 60.0
        assert health_dist.overall_status in ["Vulnerable", "Distressed"]
