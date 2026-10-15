import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.engines.ask_data_engine import AskDataEngine
from app.engines.goal_tracking import GoalTrackingEngine
from app.engines.drill_down import DrillDownEngine
from app.engines.forecasting_engine import ForecastingEngine
from app.engines.decision_impact import DecisionImpactEngine
from app.engines.explanation_engine import ExplanationEngine


client = TestClient(app)


@pytest.fixture
def sample_retail_df():
    data = {
        "InvoiceNo": [f"INV{i}" for i in range(100)],
        "CustomerID": [f"CUST{i % 20}" for i in range(100)],
        "Country": ["United Kingdom" if i < 60 else "Germany" if i < 85 else "France" for i in range(100)],
        "Category": ["Electronics" if i % 2 == 0 else "Apparel" for i in range(100)],
        "Quantity": [10 + (i % 5) for i in range(100)],
        "UnitPrice": [5.0 + (i % 3) * 2.5 for i in range(100)],
        "InvoiceDate": pd.date_range(start="2024-01-01", periods=100, freq="D")
    }
    df = pd.DataFrame(data)
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    return df


class TestAskDataEngine:
    def test_row_count_and_columns(self, sample_retail_df):
        res = AskDataEngine.answer_question(sample_retail_df, "How many rows are in this dataset?")
        assert res["understood"] is True
        assert res["metric_value"] == 100.0
        assert "100 rows" in res["answer_text"]

    def test_missing_metric_rejection(self, sample_retail_df):
        res = AskDataEngine.answer_question(sample_retail_df, "What is the net profit?")
        assert res["understood"] is False
        assert "Profit cannot be calculated" in res["answer_text"]

    def test_ranking_by_category(self, sample_retail_df):
        res = AskDataEngine.answer_question(sample_retail_df, "Top 5 Country by total Revenue")
        assert res["understood"] is True
        assert len(res["table_data"]) > 0
        assert res["echarts_spec"] is not None

    def test_identifier_isolation(self, sample_retail_df):
        res = AskDataEngine.answer_question(sample_retail_df, "Show breakdown by InvoiceNo")
        # Should not group by high cardinality identifier
        assert "identifier" in res["answer_text"].lower() or "unique" in res["answer_text"].lower()


class TestGoalTrackingEngine:
    def test_absolute_goal_evaluation(self):
        # Target: 1000, current: 800, baseline: 500
        res = GoalTrackingEngine.evaluate_goal(
            metric="Revenue",
            target_value=1000.0,
            target_type="absolute",
            current_val=800.0,
            baseline_val=500.0
        )
        assert res["progress_pct"] == 60.0
        assert res["status"] == "Near Target"

        # Target reached
        res2 = GoalTrackingEngine.evaluate_goal(
            metric="Revenue",
            target_value=1000.0,
            target_type="absolute",
            current_val=1050.0,
            baseline_val=500.0
        )
        assert res2["progress_pct"] >= 100.0
        assert res2["status"] == "Target Achieved"

    def test_growth_goal_evaluation(self):
        # Target: 20% growth, current: 110, baseline: 100 -> actual growth: 10% -> 50% progress
        res = GoalTrackingEngine.evaluate_goal(
            metric="Sales",
            target_value=20.0,
            target_type="percentage_growth",
            current_val=110.0,
            baseline_val=100.0
        )
        assert res["progress_pct"] == 50.0
        assert res["status"] == "Near Target"


class TestDrillDownEngine:
    def test_drill_down_success(self, sample_retail_df):
        res = DrillDownEngine.execute_drill_down(
            df=sample_retail_df,
            dimension="Country",
            metric="Revenue",
            aggregation="sum"
        )
        assert res["dimension"] == "Country"
        assert len(res["segments"]) == 3
        assert res["total_value"] > 0
        assert res["echarts_spec"] is not None

    def test_drill_down_with_parent_filter(self, sample_retail_df):
        res = DrillDownEngine.execute_drill_down(
            df=sample_retail_df,
            dimension="Category",
            metric="Revenue",
            parent_filters={"Country": "France"}
        )
        assert res["parent_filters"] == {"Country": "France"}
        assert len(res["segments"]) > 0

    def test_drill_down_identifier_rejection(self, sample_retail_df):
        with pytest.raises(ValueError, match="entity identifier"):
            DrillDownEngine.execute_drill_down(
                df=sample_retail_df,
                dimension="InvoiceNo",
                metric="Revenue"
            )


class TestDecisionImpactEngine:
    def test_quadrant_mapping(self):
        recs = [
            {
                "id": "R1",
                "title": "Quick Pricing Fix",
                "expected_financial_impact": 15000.0,
                "impact_score": 8.0,
                "implementation_effort": "Low"
            },
            {
                "id": "R2",
                "title": "ERP Transformation",
                "expected_financial_impact": 45000.0,
                "impact_score": 9.0,
                "implementation_effort": "High"
            },
            {
                "id": "R3",
                "title": "Update Documentation",
                "expected_financial_impact": 1000.0,
                "impact_score": 3.0,
                "implementation_effort": "Low"
            }
        ]
        res = DecisionImpactEngine.generate_impact_matrix(recs)
        assert len(res.items) == 3
        assert res.quadrant_counts["Quick Wins"] == 1
        assert res.quadrant_counts["Strategic Bets"] == 1
        assert res.quadrant_counts["Fill-ins"] == 1
        assert res.echarts_spec is not None


class TestForecastVsActual:
    def test_holdout_comparison(self, sample_retail_df):
        res = ForecastingEngine.compare_forecast_vs_actual(
            df=sample_retail_df,
            target_col="Revenue",
            date_col="InvoiceDate",
            horizon=3
        )
        assert res.horizon >= 2
        assert len(res.comparison) >= 2
        assert "mae" in res.accuracy_summary
        assert res.echarts_spec is not None


class TestNewFeatureEndpoints:
    @pytest.fixture(autouse=True)
    def setup_analysis(self):
        client.post("/api/datasets/seed-samples")
        datasets = client.get("/api/datasets").json()
        self.retail_ds = next(d for d in datasets if d["filename"] == "retail_ecommerce_q3.csv")
        run_res = client.post("/api/analysis/run", json={
            "dataset_id": self.retail_ds["id"],
            "target_column": "net_revenue",
            "date_column": "transaction_date"
        })
        self.analysis = run_res.json()
        self.analysis_id = self.analysis["id"]

    def test_stored_analyses_listing_and_rename(self):
        list_res = client.get("/api/analyses")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) > 0
        found = any(item["id"] == self.analysis_id for item in items)
        assert found

        # Rename
        rename_res = client.patch(f"/api/analyses/{self.analysis_id}", json={
            "analysis_name": "Executive Retail Q3 Audit"
        })
        assert rename_res.status_code == 200
        assert rename_res.json()["analysis_name"] == "Executive Retail Q3 Audit"

    def test_ask_data_api(self):
        ask_res = client.post(f"/api/datasets/{self.retail_ds['id']}/ask", json={
            "query": "What is the total net revenue?"
        })
        assert ask_res.status_code == 200
        data = ask_res.json()
        assert data["understood"] is True
        assert data["metric_value"] is not None

        # Suggested questions
        sug_res = client.get(f"/api/datasets/{self.retail_ds['id']}/suggested-questions")
        assert sug_res.status_code == 200
        assert len(sug_res.json()) > 0

    def test_drill_down_api(self):
        drill_res = client.post(f"/api/analyses/{self.analysis_id}/drill-down", json={
            "dimension": "region",
            "metric": "net_revenue",
            "aggregation": "sum"
        })
        assert drill_res.status_code == 200
        data = drill_res.json()
        assert data["dimension"] == "region"
        assert len(data["segments"]) > 0

    def test_decision_impact_api(self):
        impact_res = client.get(f"/api/analyses/{self.analysis_id}/decision-impact")
        assert impact_res.status_code == 200
        data = impact_res.json()
        assert len(data["items"]) > 0
        assert "Quick Wins" in data["quadrant_counts"]

    def test_explanation_api(self):
        why_res = client.get(f"/api/analyses/{self.analysis_id}/explanations/health_score/overall")
        assert why_res.status_code == 200
        data = why_res.json()
        assert data["result_type"] == "health_score"
        assert len(data["supporting_evidence"]) > 0

    def test_kpi_goals_api(self):
        create_res = client.post(f"/api/analyses/{self.analysis_id}/goals", json={
            "dataset_id": self.retail_ds["id"],
            "analysis_id": self.analysis_id,
            "metric": "net_revenue",
            "target_type": "absolute",
            "target_value": 500000.0,
            "notes": "Target for Q4"
        })
        assert create_res.status_code == 200
        goal = create_res.json()
        assert goal["metric"] == "net_revenue"
        assert goal["target_value"] == 500000.0

        list_goals = client.get(f"/api/analyses/{self.analysis_id}/goals")
        assert list_goals.status_code == 200
        assert len(list_goals.json()) > 0

        # Delete goal
        del_res = client.delete(f"/api/analyses/{self.analysis_id}/goals/{goal['id']}")
        assert del_res.status_code == 200

    def test_complete_decision_report_api(self):
        rep_res = client.get(f"/api/export/{self.analysis_id}/complete-decision-report?format=html")
        assert rep_res.status_code == 200
        html = rep_res.text
        assert "Section 1: Executive Summary" in html
        assert "Section 9: Decision Impact Matrix" in html
        assert "Section 17: Non-Causation Disclaimer" in html

