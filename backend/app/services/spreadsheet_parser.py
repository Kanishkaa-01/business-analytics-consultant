from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.evidence_model import (
    ExtractedDocument,
    ExtractedTable,
    NormalizedEvidenceItem,
    SourceLocation,
)


class SpreadsheetParser:
    @staticmethod
    def parse_spreadsheet(
        file_path: Path,
        dataset_id: str,
        filename: str
    ) -> ExtractedDocument:
        """
        Parses CSV and XLSX spreadsheets into normalized evidence representation.
        Preserves sheet names, column headers, and structured quantitative metrics.
        """
        ext = file_path.suffix.lower()
        evidence_items: List[NormalizedEvidenceItem] = []
        tables: List[ExtractedTable] = []
        structured_metrics: Dict[str, Any] = {}
        sheet_names = ["Main"]

        if ext in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            dataframes = {s: excel_file.parse(s) for s in sheet_names}
        else:
            df = pd.read_csv(file_path)
            dataframes = {"Main": df}

        for s_idx, (sheet, df) in enumerate(dataframes.items()):
            row_count, col_count = df.shape
            clean_headers = [str(c) for c in df.columns]

            # Store preview rows as ExtractedTable
            sample_rows = df.head(10).replace({float("nan"): None}).values.tolist()
            loc = SourceLocation(sheet_name=sheet, row_index=s_idx)
            tables.append(ExtractedTable(
                table_index=s_idx,
                location=loc,
                caption=f"Sheet: {sheet} ({row_count} rows, {col_count} cols)",
                headers=clean_headers,
                rows=sample_rows,
                row_count=row_count,
                col_count=col_count
            ))

            # Numeric column aggregations as normalized evidence
            for col in df.select_dtypes(include=[np.number]).columns:
                series = df[col].dropna()
                if len(series) > 0:
                    total_val = float(series.sum())
                    mean_val = float(series.mean())
                    unit = "$" if any(k in col.lower() for k in ["revenue", "sales", "price", "profit", "amount", "cost"]) else ""
                    metric_name = col.replace("_", " ").title()

                    col_loc = SourceLocation(sheet_name=sheet, column_name=col)
                    evid_item = NormalizedEvidenceItem(
                        id=f"EVID-SHEET-{sheet}-{col}",
                        source_id=dataset_id,
                        source_filename=filename,
                        source_type="xlsx" if ext in [".xlsx", ".xls"] else "csv",
                        evidence_type="structured_quantitative",
                        content=f"Structured metric '{col}' in sheet '{sheet}': Total={total_val:,.2f}, Mean={mean_val:,.2f} ({len(series)} observations)",
                        metric_name=metric_name,
                        metric_value=round(total_val, 2),
                        unit=unit,
                        location=col_loc,
                        confidence_score=1.0,
                        reliability_metadata={"row_count": len(series), "mean": round(mean_val, 2)}
                    )
                    evidence_items.append(evid_item)
                    structured_metrics[metric_name] = total_val

        return ExtractedDocument(
            dataset_id=dataset_id,
            filename=filename,
            format="xlsx" if ext in [".xlsx", ".xls"] else "csv",
            title=Path(filename).stem.replace("_", " ").title(),
            author="System Ingestion",
            page_or_section_count=len(sheet_names),
            metadata={"sheets": sheet_names, "total_tables": len(tables)},
            paragraphs=[],
            headings=[{"text": s, "level": 1} for s in sheet_names],
            tables=tables,
            evidence_items=evidence_items,
            structured_metrics_found=structured_metrics
        )
