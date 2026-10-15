import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import docx
from app.models.evidence_model import (
    ExtractedDocument,
    ExtractedTable,
    NormalizedEvidenceItem,
    SourceLocation,
)


class DOCXParser:
    @staticmethod
    def parse_docx(
        file_path: Path,
        dataset_id: str,
        filename: str
    ) -> ExtractedDocument:
        """
        Extracts and normalizes textual, tabular, and numerical evidence from DOCX files.
        Preserves heading hierarchy, section associations, and table cell structures.
        """
        doc = docx.Document(str(file_path))
        core_props = doc.core_properties
        metadata = {
            "title": core_props.title or "",
            "author": core_props.author or "",
            "created": str(core_props.created) if core_props.created else "",
            "comments": core_props.comments or "",
            "category": core_props.category or "",
        }

        paragraphs: List[Dict[str, Any]] = []
        headings: List[Dict[str, Any]] = []
        evidence_items: List[NormalizedEvidenceItem] = []
        structured_metrics: Dict[str, Any] = {}

        current_heading = "Document Header"
        current_section = "General"

        # 1. Paragraph and Heading Extraction
        for p_idx, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name if p.style else ""

            # Check if heading
            if "Heading" in style_name or style_name in ["Title", "Subtitle"]:
                current_heading = text
                current_section = text
                level = 1
                if "2" in style_name:
                    level = 2
                elif "3" in style_name:
                    level = 3
                headings.append({
                    "text": text,
                    "level": level,
                    "index": p_idx
                })
            else:
                paragraphs.append({
                    "text": text,
                    "section": current_heading,
                    "style": style_name,
                    "index": p_idx
                })

            # Extract metrics and financial amounts from paragraph
            DOCXParser._extract_evidence_from_text(
                text=text,
                section=current_heading,
                dataset_id=dataset_id,
                filename=filename,
                p_idx=p_idx,
                evidence_items=evidence_items,
                structured_metrics=structured_metrics
            )

        # 2. Table Extraction
        tables: List[ExtractedTable] = []
        for t_idx, table in enumerate(doc.tables):
            if not table.rows:
                continue

            headers = [cell.text.strip() for cell in table.rows[0].cells]
            rows: List[List[Any]] = []
            for r_idx in range(1, len(table.rows)):
                row_vals = [cell.text.strip() for cell in table.rows[r_idx].cells]
                if any(v != "" for v in row_vals):
                    rows.append(row_vals)

            loc = SourceLocation(heading_or_section=current_heading, row_index=t_idx)
            tables.append(ExtractedTable(
                table_index=t_idx,
                location=loc,
                caption=f"Table {t_idx + 1} ({current_heading})",
                headers=headers,
                rows=rows,
                row_count=len(rows),
                col_count=len(headers)
            ))

            # Add table summary as evidence item
            table_summary = f"Table {t_idx + 1} in '{current_heading}': {', '.join(headers[:4])} ({len(rows)} rows)"
            evidence_items.append(NormalizedEvidenceItem(
                id=f"EVID-DOCX-TBL-{t_idx}",
                source_id=dataset_id,
                source_filename=filename,
                source_type="docx",
                evidence_type="structured_quantitative",
                content=table_summary,
                location=loc,
                confidence_score=0.95,
                reliability_metadata={"row_count": len(rows), "headers": headers}
            ))

        title = metadata.get("title") or Path(filename).stem.replace("_", " ").title()

        return ExtractedDocument(
            dataset_id=dataset_id,
            filename=filename,
            format="docx",
            title=title,
            author=metadata.get("author") or "Management Author",
            page_or_section_count=max(1, len(headings)),
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
        section: str,
        dataset_id: str,
        filename: str,
        p_idx: int,
        evidence_items: List[NormalizedEvidenceItem],
        structured_metrics: Dict[str, Any]
    ):
        """Extracts financial and operational metrics, currencies, and percentages from DOCX text."""
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

            start_pos = max(0, match.start() - 40)
            end_pos = min(len(text), match.end() + 40)
            context = text[start_pos:end_pos].strip()

            metric_name = "Financial Amount"
            for term in ["revenue", "sales", "arr", "profit", "margin", "ebitda", "loss", "cost", "turnover", "expenditure", "gmv"]:
                if term in context.lower():
                    metric_name = term.upper()
                    break

            loc = SourceLocation(heading_or_section=section, row_index=p_idx)
            evid_id = f"EVID-DOCX-{p_idx}-{len(evidence_items)}"
            evidence_items.append(NormalizedEvidenceItem(
                id=evid_id,
                source_id=dataset_id,
                source_filename=filename,
                source_type="docx",
                evidence_type="documentary_textual",
                content=context,
                metric_name=metric_name,
                metric_value=final_val,
                unit=symbol,
                location=loc,
                confidence_score=0.92,
                reliability_metadata={"extracted_text": match.group(0), "section": section}
            ))
            structured_metrics[metric_name] = final_val

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

            loc = SourceLocation(heading_or_section=section, row_index=p_idx)
            evid_id = f"EVID-DOCX-PCT-{p_idx}-{len(evidence_items)}"
            evidence_items.append(NormalizedEvidenceItem(
                id=evid_id,
                source_id=dataset_id,
                source_filename=filename,
                source_type="docx",
                evidence_type="documentary_textual",
                content=context,
                metric_name=metric_name,
                metric_value=pct_val,
                unit="%",
                location=loc,
                confidence_score=0.92,
                reliability_metadata={"extracted_percentage": match.group(0), "section": section}
            ))
