from pathlib import Path
import pytest
import pandas as pd
from app.services.pdf_parser import PDFParser
from app.services.docx_parser import DOCXParser
from app.services.spreadsheet_parser import SpreadsheetParser
from app.engines.evidence_builder import EvidenceBuilder
from app.models.schemas import DiagnosticReport, RootCauseReport, RisksAndOpportunitiesReport, VarianceBreakdownItem, FactorContribution

SAMPLE_DIR = Path(__file__).parent.parent / "app" / "sample_data"


# 1. PDF text extraction
def test_pdf_text_extraction():
    pdf_path = SAMPLE_DIR / "retail_q3_executive_memo.pdf"
    assert pdf_path.exists(), "retail_q3_executive_memo.pdf must exist"
    doc = PDFParser.parse_pdf(pdf_path, dataset_id="test-pdf", filename="retail_q3_executive_memo.pdf")
    
    assert doc.format == "pdf"
    assert len(doc.paragraphs) > 0
    full_text = " ".join(p["text"] for p in doc.paragraphs)
    assert "gross sales revenue" in full_text.lower()
    assert "discounting" in full_text.lower()


# 2. PDF page preservation
def test_pdf_page_preservation():
    pdf_path = SAMPLE_DIR / "retail_q3_executive_memo.pdf"
    doc = PDFParser.parse_pdf(pdf_path, dataset_id="test-pdf", filename="retail_q3_executive_memo.pdf")
    
    assert doc.page_or_section_count >= 2
    # Verify that every paragraph and heading retains a valid page number
    for p in doc.paragraphs:
        assert "page" in p
        assert p["page"] in [1, 2]
    for h in doc.headings:
        assert "page" in h
        assert h["page"] in [1, 2]


# 3. PDF table extraction
def test_pdf_table_extraction():
    pdf_path = SAMPLE_DIR / "retail_q3_executive_memo.pdf"
    doc = PDFParser.parse_pdf(pdf_path, dataset_id="test-pdf", filename="retail_q3_executive_memo.pdf")
    
    assert len(doc.tables) >= 1
    table = doc.tables[0]
    assert table.location.page_number == 1
    assert "Sales Channel" in table.headers or "Direct Online" in [str(c) for c in table.headers] or len(table.rows) >= 2


# 4. DOCX paragraph extraction
def test_docx_paragraph_extraction():
    docx_path = SAMPLE_DIR / "q3_financial_audit_review.docx"
    assert docx_path.exists(), "q3_financial_audit_review.docx must exist"
    doc = DOCXParser.parse_docx(docx_path, dataset_id="test-docx", filename="q3_financial_audit_review.docx")
    
    assert doc.format == "docx"
    assert len(doc.paragraphs) > 0
    full_text = " ".join(p["text"] for p in doc.paragraphs)
    assert "49.8M" in full_text or "Internal Audit" in full_text
    assert len(doc.headings) >= 2


# 5. DOCX table extraction
def test_docx_table_extraction():
    docx_path = SAMPLE_DIR / "q3_financial_audit_review.docx"
    doc = DOCXParser.parse_docx(docx_path, dataset_id="test-docx", filename="q3_financial_audit_review.docx")
    
    assert len(doc.tables) >= 1
    table = doc.tables[0]
    assert table.row_count >= 3
    assert "Operating Region" in table.headers
    assert any("North America" in row for row in table.rows)


# 6. CSV compatibility
def test_csv_compatibility():
    csv_path = SAMPLE_DIR / "retail_ecommerce_q3.csv"
    assert csv_path.exists()
    doc = SpreadsheetParser.parse_spreadsheet(csv_path, dataset_id="test-csv", filename="retail_ecommerce_q3.csv")
    
    assert doc.format == "csv"
    assert len(doc.tables) >= 1
    assert len(doc.evidence_items) > 0
    # Every evidence item retains sheet and column
    for item in doc.evidence_items:
        assert item.location.sheet_name == "Main"
        assert item.location.column_name is not None


# 7. XLSX compatibility
def test_xlsx_compatibility(tmp_path):
    # Create test multi-sheet XLSX file
    xlsx_path = tmp_path / "test_business_data.xlsx"
    with pd.ExcelWriter(xlsx_path) as writer:
        pd.DataFrame({"revenue": [1000.0, 2000.0], "region": ["North", "South"]}).to_excel(writer, sheet_name="Q3_Sales", index=False)
        pd.DataFrame({"cost": [400.0, 800.0], "facility": ["Plant_A", "Plant_B"]}).to_excel(writer, sheet_name="Supply_Chain", index=False)

    doc = SpreadsheetParser.parse_spreadsheet(xlsx_path, dataset_id="test-xlsx", filename="test_business_data.xlsx")
    assert doc.format == "xlsx"
    assert doc.page_or_section_count == 2
    assert "Q3_Sales" in doc.metadata["sheets"]
    assert "Supply_Chain" in doc.metadata["sheets"]
    assert any(item.location.sheet_name == "Q3_Sales" for item in doc.evidence_items)
    assert any(item.location.sheet_name == "Supply_Chain" for item in doc.evidence_items)


# 8. Evidence source tracking (Extended 7-stage chain)
def test_evidence_source_tracking():
    mock_diag = DiagnosticReport(
        focal_metric="net_revenue",
        total_variance=-12000.0,
        variance_pct=-14.2,
        variance_breakdown=[VarianceBreakdownItem(
            dimension="category",
            segment="Electronics",
            baseline_value=45000.0,
            actual_value=33000.0,
            variance=-12000.0,
            variance_pct=-26.6,
            contribution_share_pct=62.5,
            direction="Drag"
        )],
        segment_diagnostics=[],
        anomalies_detected=[],
        diagnostic_narrative="Electronics was the dominant drag."
    )
    mock_rc = RootCauseReport(
        primary_root_cause="Runaway marketplace discounting in Electronics",
        secondary_root_causes=[],
        factor_contributions=[FactorContribution(
            factor_name="Discount Rate",
            factor_type="Commercial",
            attribution_percentage=58.5,
            statistical_significance_p_value=0.00012,
            correlation_or_coef=-0.62,
            direction="Negative Impact",
            evidence_statement="Pearson r=-0.62 (p=0.00012)"
        )],
        pareto_breakdown=[],
        causal_tree_structure={"root_issue": "Margin Erosion"},
        statistical_confidence_level=88.5,
        methodology_notes="ANOVA & Covariance"
    )
    mock_risk = RisksAndOpportunitiesReport(
        total_exposure_at_risk=48000.0,
        total_opportunity_upside=65000.0,
        risk_profile_rating="Moderate",
        risks=[],
        opportunities=[]
    )

    chains = EvidenceBuilder.construct_evidence_chains(
        target_col="net_revenue",
        diagnostic=mock_diag,
        root_cause=mock_rc,
        risk_opp=mock_risk,
        source_filename="retail_ecommerce_q3.csv",
        source_type="csv",
        source_location="Sheet 'Main', Column 'net_revenue'"
    )

    assert len(chains) >= 1
    chain = chains[0]
    stages = [n.stage for n in chain.nodes]
    # Verify 7-stage extension: Source -> Extracted Evidence -> Observation -> Diagnostic Test -> Root Cause Proof -> Risk Assessment -> Action Prescribed
    expected_stages = ["Data Source", "Data Extracted", "Observed Pattern", "Data Check", "Possible Reason", "Estimated Impact", "Recommended Action"]
    assert stages == expected_stages
    assert "retail_ecommerce_q3.csv" in chain.nodes[0].detail

