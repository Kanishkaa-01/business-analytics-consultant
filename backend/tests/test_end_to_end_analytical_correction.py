import pytest
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path

from app.services.data_ingestion import IngestionService
from app.services.quality_profiler import QualityProfiler
from app.engines.business_health import BusinessHealthEngine
from app.engines.diagnostic import DiagnosticEngine
from app.engines.advanced_findings import AdvancedFindingsEngine
from app.engines.root_cause import RootCauseEngine
from app.engines.risk_opportunity import RiskOpportunityEngine
from app.engines.recommendation import RecommendationEngine
from app.engines.simulation import SimulationEngine
from app.engines.forecasting_engine import ForecastingEngine
from app.engines.evidence_builder import EvidenceBuilder
from app.models.schemas import SimulationRequest


@pytest.fixture
def sample_retail_df():
    """
    Creates a realistic mini-retail dataset modeled after UCI Online Retail:
    500 rows, 8 columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country
    Includes cancellations ('C' prefix, negative quantity), guest checkouts (missing CustomerID),
    and UK concentration.
    """
    np.random.seed(42)
    n = 300

    dates = pd.date_range("2011-01-01", periods=10, freq="W")
    countries = ["United Kingdom"] * 270 + ["Germany"] * 15 + ["France"] * 15
    invoices = [f"{536365 + i % 50}" for i in range(n)]
    # Add a few cancellations with 'C'
    for i in range(0, 30, 5):
        invoices[i] = f"C{536365 + i}"

    quantities = [np.random.randint(1, 20) if not invoices[i].startswith("C") else -np.random.randint(1, 5) for i in range(n)]
    unit_prices = [round(float(np.random.uniform(1.5, 25.0)), 2) for _ in range(n)]
    # Add one negative price adjustment
    unit_prices[10] = -5.0

    customer_ids = [float(12345 + (i % 25)) if i % 4 != 0 else np.nan for i in range(n)]
    descriptions = [f"Product Item {i % 30}" for i in range(n)]
    stock_codes = [f"SKU{1000 + (i % 30)}" for i in range(n)]

    df = pd.DataFrame({
        "InvoiceNo": invoices,
        "StockCode": stock_codes,
        "Description": descriptions,
        "Quantity": quantities,
        "InvoiceDate": [dates[i % len(dates)] for i in range(n)],
        "UnitPrice": unit_prices,
        "CustomerID": customer_ids,
        "Country": countries
    })
    return df


class TestEndToEndAnalyticalCorrection:

    def test_identifier_column_detection(self, sample_retail_df):
        """InvoiceNo and CustomerID must be classified as identifiers, not categoricals or numeric drivers."""
        assert IngestionService.is_identifier_column("InvoiceNo", sample_retail_df["InvoiceNo"]) is True
        assert IngestionService.is_identifier_column("CustomerID", sample_retail_df["CustomerID"]) is True
        assert IngestionService.is_identifier_column("Quantity", sample_retail_df["Quantity"]) is False
        assert IngestionService.is_identifier_column("UnitPrice", sample_retail_df["UnitPrice"]) is False
        assert IngestionService.is_identifier_column("Country", sample_retail_df["Country"]) is False

        schema = IngestionService.extract_schema_metadata(sample_retail_df)
        identifiers = schema["identifier_candidates"]
        assert "InvoiceNo" in identifiers
        assert "CustomerID" in identifiers

        # Ensure identifiers NEVER enter categorical or numeric candidate lists
        assert "InvoiceNo" not in schema["categorical_candidates"]
        assert "CustomerID" not in schema["categorical_candidates"]
        assert "CustomerID" not in schema["numeric_candidates"]

        # Only Country should be the primary categorical candidate (StockCode/Description have high cardinality)
        assert "Country" in schema["categorical_candidates"]

    def test_dataset_capabilities_detection(self, sample_retail_df):
        """Capabilities should accurately reflect presence of quantity and unit price, absence of profit and discount."""
        caps = IngestionService.detect_dataset_capabilities(sample_retail_df)
        assert caps["has_quantity"] is True
        assert caps["has_unit_price"] is True
        assert caps["estimated_transaction_value_available"] is True
        assert caps["has_discount"] is False
        assert caps["has_profit"] is False
        assert caps["has_cost"] is False

    def test_dataframe_cache_performance(self, sample_retail_df):
        """Verify LRU/mtime caching avoids repeated file reads."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            sample_retail_df.to_csv(tmp_path, index=False)
            df1 = IngestionService.load_dataframe(tmp_path)
            df2 = IngestionService.load_dataframe(tmp_path)
            assert str(tmp_path.resolve()) in IngestionService._DF_CACHE
            assert df1.equals(df2)
            assert len(df1) == len(sample_retail_df)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_data_quality_contextualization(self, sample_retail_df):
        """Data quality profiler must contextualize negative quantities as returns and missing CustomerID as guest checkouts."""
        report = QualityProfiler.audit_dataset(sample_retail_df)

        qty_issues = [i for i in report.issues if i.column == "Quantity"]
        assert any("return" in i.description.lower() or "cancellation" in i.description.lower() for i in qty_issues)

        cust_issues = [i for i in report.issues if i.column == "CustomerID"]
        assert any("guest" in i.description.lower() or "unregistered" in i.description.lower() for i in cust_issues)

        price_issues = [i for i in report.issues if i.column == "UnitPrice"]
        assert any("accounting" in i.description.lower() or "debt" in i.description.lower() for i in price_issues)

    def test_business_health_schema_awareness(self, sample_retail_df):
        """Business health engine must compute estimated_transaction_value and not invent profit or discount."""
        health = BusinessHealthEngine.assess_health(sample_retail_df, target_col="Quantity")
        om = health.overview_metrics or {}

        assert om.get("estimated_transaction_value") is not None
        assert om.get("total_profit") is None
        assert om.get("profit_margin") is None
        assert om.get("avg_discount") is None
        # KPIs must never include CustomerID or InvoiceNo
        kpi_names = [k.name.lower() for k in health.kpis]
        assert not any("customerid" in k or "invoiceno" in k for k in kpi_names)

    def test_diagnostic_and_advanced_findings_dimensions(self, sample_retail_df):
        """Diagnostics and advanced findings must only evaluate true dimensions, not InvoiceNo or CustomerID."""
        diag = DiagnosticEngine.diagnose_variance(sample_retail_df, target_col="UnitPrice")
        for b in diag.variance_breakdown:
            assert b.dimension != "InvoiceNo"
            assert b.dimension != "CustomerID"
            assert b.segment != "InvoiceNo"

        adv = AdvancedFindingsEngine.analyze(sample_retail_df, target_col="UnitPrice", date_col="InvoiceDate")
        for sc in adv.segment_comparisons:
            assert sc.dimension != "InvoiceNo"
            assert sc.dimension != "CustomerID"

    def test_root_cause_and_risk_no_fake_causes(self, sample_retail_df):
        """Root cause engine must not identify CustomerID or InvoiceNo as ANOVA drivers or Pareto vital few."""
        diag = DiagnosticEngine.diagnose_variance(sample_retail_df, target_col="UnitPrice")
        rc = RootCauseEngine.analyze_root_cause(sample_retail_df, target_col="UnitPrice")

        for fc in rc.factor_contributions:
            assert fc.factor_name != "CustomerID"
            assert fc.factor_name != "InvoiceNo"

        for p in rc.pareto_breakdown:
            assert not p.entity.startswith("C5")  # Must not be an invoice code

        ro = RiskOpportunityEngine.identify_risks_and_opportunities(sample_retail_df, "UnitPrice", diag, rc)
        # Should detect concentration in Country (UK is ~90%)
        concentration_risks = [r for r in ro.risks if r.category == "Concentration"]
        assert len(concentration_risks) >= 1

    def test_recommendation_and_evidence_no_discount_rule_without_discount_data(self, sample_retail_df):
        """When discount data is absent, recommendation engine must NOT emit discount control recommendations."""
        diag = DiagnosticEngine.diagnose_variance(sample_retail_df, target_col="UnitPrice")
        rc = RootCauseEngine.analyze_root_cause(sample_retail_df, target_col="UnitPrice")
        ro = RiskOpportunityEngine.identify_risks_and_opportunities(sample_retail_df, "UnitPrice", diag, rc)

        recs = RecommendationEngine.generate_prioritized_recommendations("UnitPrice", diag, rc, ro)
        rec_ids = [r.id for r in recs]
        rec_titles = [r.title for r in recs]

        # Discount control recommendation must NOT be present when discount data is absent
        assert "Establish Clear Discount Controls" not in rec_titles
        for t in rec_titles:
            assert "discount control" not in t.lower()
            assert "15%" not in t.lower()

        # Diversification recommendation MUST be present due to concentration
        assert "Diversify Distribution & Segment Mix" in rec_titles

        # Evidence builder must reflect concentration, not discount control
        chains = EvidenceBuilder.construct_evidence_chains(
            target_col="UnitPrice",
            diagnostic=diag,
            root_cause=rc,
            risk_opp=ro
        )
        for chain in chains:
            assert "15% discount" not in chain.statistical_proof.lower()

    def test_simulation_dataset_awareness_and_neutral_baseline(self, sample_retail_df):
        """What-If Simulation must return 0 delta on neutral baseline, no invented profit, and dynamic sensitivity."""
        req = SimulationRequest(
            analysis_id="test-sim",
            price_change_pct=0.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        outcome = SimulationEngine.run_simulation(
            sample_retail_df,
            "UnitPrice",
            req
        )

        # Neutral baseline must have zero deltas
        assert outcome.revenue_delta == 0.0
        assert outcome.revenue_delta_pct == 0.0
        assert outcome.profit_delta == 0.0
        assert outcome.simulated_profit == 0.0
        assert outcome.baseline_profit == 0.0

        # Sensitivity breakdown must ONLY include supported levers
        assert "price_sensitivity_per_pct" in outcome.sensitivity_breakdown
        assert "discount_recapture_per_pct" not in outcome.sensitivity_breakdown
        assert "operational_efficiency_per_pct" not in outcome.sensitivity_breakdown

        # Price test with price_change_pct = 10%
        req_price = SimulationRequest(
            analysis_id="test-sim",
            price_change_pct=10.0,
            discount_adjustment_pct=0.0,
            churn_mitigation_pct=0.0,
            operational_efficiency_pct=0.0
        )
        outcome_price = SimulationEngine.run_simulation(sample_retail_df, "UnitPrice", req_price)
        assert outcome_price.revenue_delta > 0.0
        assert round(outcome_price.revenue_delta_pct, 1) == 10.0  # Linear price change without assumed elasticity

    def test_forecasting_engine_resilience(self, sample_retail_df):
        """Forecasting engine should detect date and metric, produce valid holdout validation."""
        report = ForecastingEngine.generate_forecast(
            df=sample_retail_df,
            target_col=None,  # Should auto-detect estimated_transaction_value or Quantity
            date_col="InvoiceDate",
            horizon=3
        )
        assert report.is_available is True
        assert report.metric_name != "Customerid"
        assert len(report.models) == 3
        assert report.recommended_model in ["linear", "moving_average", "exponential_smoothing"]
