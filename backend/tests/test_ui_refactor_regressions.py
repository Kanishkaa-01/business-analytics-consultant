import io
import pytest
import pandas as pd
import pymupdf
from fastapi.testclient import TestClient
from app.main import app
from app.services.semantic_metrics import SemanticMetricDetector
from app.engines.business_health import BusinessHealthEngine
from app.services.pdf_parser import PDFParser

client = TestClient(app)


class TestCustomerAccountKpiIsolation:
    """Requirement 8 & 21A: Tests for Customer / Account identification and isolation."""

    def test_dataset_with_customer_id_detects_count(self):
        """Valid customer identifier yields accurate distinct count."""
        df = pd.DataFrame({
            "CustomerID": [101, 102, 103, 101, 104],
            "Revenue": [100.0, 200.0, 150.0, 80.0, 300.0],
            "Date": pd.date_range("2025-01-01", periods=5, freq="D")
        })

        det = SemanticMetricDetector.detect_metrics(df)
        assert det["customer_identifier"]["column"] == "CustomerID"

        health = BusinessHealthEngine.assess_health(df)
        assert health.vital_signs["distinct_customer_identifier_present"] is True
        assert health.overview_metrics["unique_customers"] == 4

    def test_dataset_with_customer_segment_does_not_count_as_customers(self):
        """Segmentation categories must NEVER be counted as customer accounts."""
        df = pd.DataFrame({
            "Customer_Segment": ["Enterprise", "SMB", "Consumer", "SMB", "Enterprise"],
            "Revenue": [1000.0, 200.0, 50.0, 180.0, 950.0],
            "Date": pd.date_range("2025-01-01", periods=5, freq="D")
        })

        det = SemanticMetricDetector.detect_metrics(df)
        # Must NOT detect Customer_Segment as customer_identifier
        assert det["customer_identifier"]["column"] is None
        assert det["customer_segment"]["column"] == "Customer_Segment"

        health = BusinessHealthEngine.assess_health(df)
        assert health.vital_signs["distinct_customer_identifier_present"] is False
        assert health.vital_signs["customer_segment_categories_present"] is True
        assert health.overview_metrics["unique_customers"] is None

    def test_order_id_and_invoice_no_are_not_customers(self):
        """Transaction/Invoice IDs must NEVER be counted as customer accounts."""
        df = pd.DataFrame({
            "InvoiceNo": ["INV-001", "INV-002", "INV-003", "INV-004", "INV-005"],
            "OrderID": [1001, 1002, 1003, 1004, 1005],
            "Revenue": [50.0, 60.0, 70.0, 80.0, 90.0],
            "Date": pd.date_range("2025-01-01", periods=5, freq="D")
        })

        det = SemanticMetricDetector.detect_metrics(df)
        assert det["customer_identifier"]["column"] is None

        health = BusinessHealthEngine.assess_health(df)
        assert health.vital_signs["distinct_customer_identifier_present"] is False
        assert health.overview_metrics["unique_customers"] is None

    def test_country_region_category_are_not_customers(self):
        """Geographical and categorical dimensions must NEVER be treated as customer accounts."""
        df = pd.DataFrame({
            "Region": ["EMEA", "APAC", "AMER", "EMEA", "APAC"],
            "Country": ["UK", "Japan", "USA", "Germany", "Australia"],
            "Category": ["Hardware", "Software", "Cloud", "Hardware", "Cloud"],
            "Revenue": [100.0, 200.0, 300.0, 400.0, 500.0],
            "Date": pd.date_range("2025-01-01", periods=5, freq="D")
        })

        det = SemanticMetricDetector.detect_metrics(df)
        assert det["customer_identifier"]["column"] is None

        health = BusinessHealthEngine.assess_health(df)
        assert health.vital_signs["distinct_customer_identifier_present"] is False
        assert health.overview_metrics["unique_customers"] is None


class TestPyMuPDFParser:
    """Requirement 7 & 21C: Tests for modern PyMuPDF package usage."""

    def test_pymupdf_import_and_in_memory_doc(self):
        """PyMuPDF open, text rendering, and extraction work seamlessly."""
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Business Analytics Executive Report", fontsize=16)
        pdf_bytes = doc.tobytes()
        doc.close()

        assert len(pdf_bytes) > 0
        read_doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        assert len(read_doc) == 1
        text = read_doc[0].get_text()
        assert "Business Analytics Executive Report" in text
        read_doc.close()


class TestReportGenerationAndConsistency:
    """Requirement 6 & 21B: Tests for deterministic reporting across HTML, PDF, Excel, and Print."""

    @pytest.fixture
    def active_analysis_id(self):
        # Seed or upload a dataset to run an analysis
        seed_res = client.post("/api/datasets/seed-samples")
        datasets = seed_res.json()
        assert len(datasets) > 0
        ds_id = datasets[0]["id"]

        run_res = client.post("/api/analysis/run", json={"dataset_id": ds_id})
        assert run_res.status_code == 200
        return run_res.json()["id"]

    def test_complete_decision_report_html(self, active_analysis_id):
        """Full 17-section report HTML generates successfully and contains deterministic values."""
        res = client.get(f"/api/export/{active_analysis_id}/complete-decision-report?format=html")
        assert res.status_code == 200
        html = res.text
        assert "Executive Business Decision Report" in html or "Business Decision Report" in html
        assert "Executive Summary" in html or "Business Health" in html
        assert "Note: An observed relationship does not necessarily prove causation." in html

    def test_complete_decision_report_pdf(self, active_analysis_id):
        """PDF report returns application/pdf bytes with valid PDF magic header."""
        res = client.get(f"/api/export/{active_analysis_id}/complete-decision-report?format=pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content[:4] == b"%PDF"

    def test_excel_report_workbook(self, active_analysis_id):
        """Excel workbook returns valid openxml spreadsheet bytes."""
        res = client.get(f"/api/export/{active_analysis_id}/excel-report")
        assert res.status_code == 200
        assert "spreadsheetml" in res.headers["content-type"]
        assert res.content[:4] == b"PK\x03\x04"

    def test_printable_summary_report(self, active_analysis_id):
        """Printable decision report HTML generates cleanly."""
        res = client.get(f"/api/export/{active_analysis_id}/print-report")
        assert res.status_code == 200
        assert "Business Decision Report" in res.text
        assert "Print / Save as PDF" in res.text


class TestPhase10AnalyticalRefinements:
    """Verifications for non-causal language, PyMuPDF, forecasting uncertainty band, and binary variable handling."""

    def test_zero_import_fitz_in_backend(self):
        """Strictly 0 legacy `import fitz` statements exist in backend codebase."""
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent / "app"
        for py_file in backend_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "import fitz" not in content, f"Legacy `import fitz` found in {py_file}"
            assert "from fitz" not in content, f"Legacy `from fitz` found in {py_file}"

    def test_forecasting_holdout_uses_uncertainty_band(self):
        """Forecast vs actual insights use 'forecast uncertainty band' instead of unproven 95% CI."""
        from app.engines.forecasting_engine import ForecastingEngine

        df = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=16, freq="ME"),
            "Revenue": [100.0 + i * 5.0 for i in range(16)]
        })
        res = ForecastingEngine.compare_forecast_vs_actual(df, target_col="Revenue", date_col="Date", horizon=3)

        assert res.accuracy_summary.get("within_ci_percentage") is not None
        assert any("forecast uncertainty band" in ins for ins in res.insights)
        assert not any("95% confidence interval" in ins for ins in res.insights)

    def test_binary_variables_exempt_from_iqr_outliers(self):
        """Binary flags are profiled with event rates and exempt from IQR outlier inflation."""
        from app.services.quality_profiler import QualityProfiler
        df = pd.DataFrame({
            "is_returned": [0] * 95 + [1] * 5,  # 5% return rate
            "revenue": [100.0] * 100
        })
        report = QualityProfiler.audit_dataset(df)
        returned_metric = next((m for m in report.column_metrics if m.column == "is_returned"), None)
        assert returned_metric is not None
        assert returned_metric.outlier_count == 0
        assert returned_metric.outlier_percentage == 0.0

    def test_root_cause_non_causal_disclaimer_present(self):
        """Explanation and Root Cause engines always include clear non-causal language."""
        seed_res = client.post("/api/datasets/seed-samples")
        datasets = seed_res.json()
        assert len(datasets) > 0
        ds_id = datasets[0]["id"]
        run_res = client.post("/api/analysis/run", json={"dataset_id": ds_id})
        assert run_res.status_code == 200
        analysis_id = run_res.json()["id"]

        res = client.get(f"/api/analysis/{analysis_id}/explanations/finding/test_id")
        assert res.status_code == 200
        data = res.json()
        assert "causation" in data["causation_disclaimer"].lower()
        assert "do not prove" in data["causation_disclaimer"].lower()

