from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SourceLocation(BaseModel):
    page_number: Optional[int] = None           # PDF page (1-indexed)
    heading_or_section: Optional[str] = None    # DOCX section/heading or PDF section
    sheet_name: Optional[str] = None            # XLSX sheet
    column_name: Optional[str] = None           # CSV / XLSX column
    row_index: Optional[int] = None             # Row index if tabular
    bbox: Optional[List[float]] = None          # [x0, y0, x1, y1] for PDF if available


class NormalizedEvidenceItem(BaseModel):
    id: str
    source_id: str
    source_filename: str
    source_type: str                            # 'csv', 'xlsx', 'pdf', 'docx'
    evidence_type: str                          # 'structured_quantitative' or 'documentary_textual'
    content: str                                # Extracted text or tabular summary
    metric_name: Optional[str] = None           # e.g. "Revenue", "Discount Rate", "Lead Time", "Churn"
    metric_value: Optional[float] = None
    unit: Optional[str] = None                  # "$", "₹", "%", "days", "units"
    temporal_period: Optional[str] = None       # e.g. "Q3 2025", "FY2025"
    entity_segment: Optional[str] = None        # e.g. "Electronics", "Marketplace", "Europe"
    location: SourceLocation
    confidence_score: float = 1.0               # 0.0 to 1.0
    reliability_metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedTable(BaseModel):
    table_index: int
    location: SourceLocation
    caption: Optional[str] = None
    headers: List[str]
    rows: List[List[Any]]
    row_count: int
    col_count: int


class ExtractedDocument(BaseModel):
    dataset_id: str
    filename: str
    format: str                                 # 'pdf', 'docx', 'csv', 'xlsx'
    title: Optional[str] = None
    author: Optional[str] = None
    page_or_section_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    paragraphs: List[Dict[str, Any]] = Field(default_factory=list)
    headings: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    evidence_items: List[NormalizedEvidenceItem] = Field(default_factory=list)
    structured_metrics_found: Dict[str, Any] = Field(default_factory=dict)

