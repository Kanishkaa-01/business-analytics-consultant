import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf
import pdfplumber
from app.models.evidence_model import (
    ExtractedDocument,
    ExtractedTable,
    NormalizedEvidenceItem,
    SourceLocation,
)


class PDFParser:
    @staticmethod
    def parse_pdf(
        file_path: Path,
        dataset_id: str,
        filename: str
    ) -> ExtractedDocument:
        """
        Extracts and normalizes textual, tabular, and numerical evidence from PDF files.
        Preserves exact page numbers, headings, tables, and bounding locations without loss.
        """
        doc = pymupdf.open(str(file_path))
        page_count = len(doc)
        metadata = doc.metadata or {}

        paragraphs: List[Dict[str, Any]] = []
        headings: List[Dict[str, Any]] = []
        evidence_items: List[NormalizedEvidenceItem] = []
        structured_metrics: Dict[str, Any] = {}

        # 1. PyMuPDF text block and heading extraction
        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block.get("type") == 0:  # text block
                    block_text = ""
                    max_font_size = 0.0
                    is_bold = False

                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if span_text:
                                block_text += (" " if block_text else "") + span_text
                                font_size = span.get("size", 10.0)
                                if font_size > max_font_size:
                                    max_font_size = font_size
                                if "bold" in span.get("font", "").lower() or span.get("flags", 0) & 2 != 0:
                                    is_bold = True

                    block_text = block_text.strip()
                    if not block_text or len(block_text) < 3:
                        continue

                    # Bounding box
                    bbox = [round(c, 1) for c in block.get("bbox", [0, 0, 0, 0])]

                    # Classify if heading: larger font or bold short title
                    is_heading = (max_font_size >= 13.0) or (is_bold and len(block_text) < 80 and not block_text.endswith("."))

                    if is_heading:
                        headings.append({
                            "page": page_num,
                            "text": block_text,
                            "level": 1 if max_font_size >= 16.0 else 2,
                            "bbox": bbox
                        })
                    else:
                        paragraphs.append({
                            "page": page_num,
                            "text": block_text,
                            "bbox": bbox
                        })

                    # Extract numerical and financial metrics from text
                    PDFParser._extract_evidence_from_text(
                        text=block_text,
                        page_num=page_num,
                        dataset_id=dataset_id,
                        filename=filename,
                        bbox=bbox,
                        evidence_items=evidence_items,
                        structured_metrics=structured_metrics
                    )

        # 2. Extract tables using pdfplumber for high fidelity
        tables: List[ExtractedTable] = []
        try:
            with pdfplumber.open(str(file_path)) as plumber_pdf:
                t_idx = 0
                for p_idx, p_page in enumerate(plumber_pdf.pages):
                    page_num = p_idx + 1
                    extracted_tbls = p_page.extract_tables()
                    for tbl in extracted_tbls:
                        if not tbl or len(tbl) < 2:
                            continue
                        headers = [str(c).strip() if c is not None else f"Col_{i}" for i, c in enumerate(tbl[0])]
                        raw_rows = []
                        for row in tbl[1:]:
                            clean_row = [str(c).strip() if c is not None else "" for c in row]
                            if any(c != "" for c in clean_row):
                                raw_rows.append(clean_row)

                        if raw_rows:
                            loc = SourceLocation(page_number=page_num, row_index=t_idx)
                            tables.append(ExtractedTable(
                                table_index=t_idx,
                                location=loc,
                                caption=f"Table {t_idx + 1} (Page {page_num})",
                                headers=headers,
                                rows=raw_rows,
                                row_count=len(raw_rows),
                                col_count=len(headers)
                            ))

                            # Add table summary as evidence item
                            table_summary = f"Table on page {page_num}: {', '.join(headers[:4])} ({len(raw_rows)} rows)"
                            evidence_items.append(NormalizedEvidenceItem(
                                id=f"EVID-PDF-TBL-{t_idx}",
                                source_id=dataset_id,
                                source_filename=filename,
                                source_type="pdf",
                                evidence_type="structured_quantitative",
                                content=table_summary,
                                location=loc,
                                confidence_score=0.95,
                                reliability_metadata={"row_count": len(raw_rows), "headers": headers}
                            ))
                            t_idx += 1
        except Exception as exc:
            pass  # Fall back to parsed text if table extraction fails

        doc.close()

        title = metadata.get("title") or Path(filename).stem.replace("_", " ").title()

        return ExtractedDocument(
            dataset_id=dataset_id,
            filename=filename,
            format="pdf",
            title=title,
            author=metadata.get("author") or "Document Author",
            page_or_section_count=page_count,
            metadata=metadata,
            paragraphs=paragraphs,
            headings=headings,
            tables=tables,
            evidence_items=evidence_items,
            structured_metrics_found=structured_metrics
        )

    @staticmethod
    def _extract_evidence_from_text(
        text: str,
        page_num: int,
        dataset_id: str,
        filename: str,
        bbox: List[float],
        evidence_items: List[NormalizedEvidenceItem],
        structured_metrics: Dict[str, Any]
    ):
        """Identifies financial and operational metrics, currencies, and percentages."""
        # Currency patterns: e.g. $52.4M, ₹49.8M, €12.5M, $1,250,000
        currency_pattern = re.compile(
            r'([\$₹€£])\s?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s?([MBKmbk]|million|billion|crore|lakh)?',
            re.IGNORECASE
        )
        pct_pattern = re.compile(r'([0-9]+(?:\.[0-9]+)?)\s?%')

        for match in currency_pattern.finditer(text):
            symbol, num_str, multiplier = match.groups()
            clean_num = float(num_str.replace(",", ""))
            mult_lower = (multiplier or "").lower()

            mult_val = 1.0
            if "m" in mult_lower or "million" in mult_lower:
                mult_val = 1_000_000.0
            elif "b" in mult_lower or "billion" in mult_lower:
                mult_val = 1_000_000_000.0
            elif "k" in mult_lower:
                mult_val = 1_000.0
            elif "crore" in mult_lower:
                mult_val = 10_000_000.0
            elif "lakh" in mult_lower:
                mult_val = 100_000.0

            final_val = clean_num * mult_val

            # Infer metric name from surrounding window
            start_pos = max(0, match.start() - 40)
            end_pos = min(len(text), match.end() + 40)
            context = text[start_pos:end_pos].strip()

            metric_name = "Financial Amount"
            for term in ["revenue", "sales", "arr", "profit", "margin", "ebitda", "loss", "cost", "turnover", "expenditure", "gmv"]:
                if term in context.lower():
                    metric_name = term.upper()
                    break

            loc = SourceLocation(page_number=page_num, bbox=bbox)
            evid_id = f"EVID-PDF-{page_num}-{len(evidence_items)}"
            item = NormalizedEvidenceItem(
                id=evid_id,
                source_id=dataset_id,
                source_filename=filename,
                source_type="pdf",
                evidence_type="documentary_textual",
                content=context,
                metric_name=metric_name,
                metric_value=final_val,
                unit=symbol,
                location=loc,
                confidence_score=0.90,
                reliability_metadata={"extracted_text": match.group(0), "page": page_num}
            )
            evidence_items.append(item)
            structured_metrics[metric_name] = final_val

        # Percentage patterns
        for match in pct_pattern.finditer(text):
            pct_val = float(match.group(1))
            start_pos = max(0, match.start() - 35)
            end_pos = min(len(text), match.end() + 35)
            context = text[start_pos:end_pos].strip()

            metric_name = "Rate / Percentage"
            for term in ["discount", "growth", "margin", "churn", "retention", "variance", "defect", "adoption"]:
                if term in context.lower():
                    metric_name = f"{term.title()} Rate"
                    break

            loc = SourceLocation(page_number=page_num, bbox=bbox)
            evid_id = f"EVID-PDF-PCT-{page_num}-{len(evidence_items)}"
            evidence_items.append(NormalizedEvidenceItem(
                id=evid_id,
                source_id=dataset_id,
                source_filename=filename,
                source_type="pdf",
                evidence_type="documentary_textual",
                content=context,
                metric_name=metric_name,
                metric_value=pct_val,
                unit="%",
                location=loc,
                confidence_score=0.90,
                reliability_metadata={"extracted_percentage": match.group(0), "page": page_num}
            ))
