import hashlib
import os
import shutil
import math
import datetime
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from app.core.config import settings
from app.services.pdf_parser import PDFParser
from app.services.docx_parser import DOCXParser
from app.services.spreadsheet_parser import SpreadsheetParser


def normalize_metadata_for_json(val: Any) -> Any:
    """
    Recursively normalizes metadata dictionaries, lists, and primitives into JSON-safe Python values.
    Preserves numeric, boolean, string, and ISO-8601 date semantics without destroying types.
    Converts:
    - pandas.Timestamp -> ISO 8601 string
    - datetime.datetime / datetime.date -> ISO 8601 string
    - numpy integer -> Python int
    - numpy floating type -> Python float (or None if NaN/Inf)
    - Python float NaN/Inf -> None
    - numpy.bool_ -> Python bool
    - pandas.NA / NaN / NaT -> None
    - numpy.ndarray -> Python list (recursively normalized)
    - dict -> recursively normalized dict (keys stringified)
    - list / tuple / set -> recursively normalized list
    - str / int / bool / None -> unchanged
    """
    if val is None or val is pd.NA or val is pd.NaT:
        return None

    # Booleans must precede integer check because in Python isinstance(True, int) is True
    if isinstance(val, (bool, np.bool_)):
        return bool(val)

    # Date and timestamp types
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        if pd.isna(val):
            return None
        return val.isoformat()

    # Integers (both numpy and standard)
    if isinstance(val, (np.integer, int)):
        return int(val)

    # Floating point numbers (both numpy and standard)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)

    # Numpy arrays
    if isinstance(val, np.ndarray):
        return [normalize_metadata_for_json(x) for x in val.tolist()]

    # Pandas Series and Index
    if isinstance(val, (pd.Series, pd.Index)):
        return [normalize_metadata_for_json(x) for x in val.tolist()]

    # Dictionaries
    if isinstance(val, dict):
        return {str(k): normalize_metadata_for_json(v) for k, v in val.items()}

    # Lists, tuples, sets
    if isinstance(val, (list, tuple, set)):
        return [normalize_metadata_for_json(x) for x in val]

    # Strings
    if isinstance(val, str):
        return val

    # Scalar fallback checks
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass

    if hasattr(val, "isoformat") and callable(val.isoformat):
        try:
            return val.isoformat()
        except Exception:
            pass

    if hasattr(val, "item") and callable(val.item):
        try:
            return normalize_metadata_for_json(val.item())
        except Exception:
            pass

    if hasattr(val, "tolist") and callable(val.tolist):
        try:
            return [normalize_metadata_for_json(x) for x in val.tolist()]
        except Exception:
            pass

    return val


class IngestionService:
    SUPPORTED_FORMATS = [".csv", ".txt", ".xlsx", ".xls", ".pdf", ".docx"]

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Compute deterministic SHA-256 hash to guarantee data immutability."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def save_and_profile_file(
        source_stream,
        filename: str,
        target_dir: Path = settings.UPLOAD_DIR
    ) -> Tuple[Path, str, int, int, int, Dict[str, Any]]:
        """
        Saves uploaded file without alteration and generates immutable metadata profile.
        Supports CSV, XLSX, PDF, and DOCX.
        Returns (destination_path, file_hash, file_size, row_count, col_count, schema_meta).
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(filename).name
        dest_path = target_dir / safe_filename

        # If a file with same name exists, append timestamp suffix to never overwrite
        if dest_path.exists():
            import time
            dest_path = target_dir / f"{int(time.time())}_{safe_filename}"

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(source_stream, buffer)

        file_size = os.path.getsize(dest_path)
        file_hash = IngestionService.calculate_file_hash(dest_path)
        ext = dest_path.suffix.lower()

        # Branch based on file type
        if ext == ".pdf":
            extracted = PDFParser.parse_pdf(dest_path, dataset_id=file_hash[:8], filename=filename)
            row_count = len(extracted.paragraphs)
            col_count = extracted.page_or_section_count
            schema_meta = {
                "file_type": "document",
                "format": "pdf",
                "title": extracted.title,
                "author": extracted.author,
                "page_count": extracted.page_or_section_count,
                "paragraph_count": len(extracted.paragraphs),
                "heading_count": len(extracted.headings),
                "table_count": len(extracted.tables),
                "evidence_count": len(extracted.evidence_items),
                "structured_metrics": extracted.structured_metrics_found,
                "columns": [],
                "numeric_candidates": list(extracted.structured_metrics_found.keys()),
                "datetime_candidates": [],
                "categorical_candidates": [],
                "suggested_target": list(extracted.structured_metrics_found.keys())[0] if extracted.structured_metrics_found else None,
                "suggested_date": None
            }
        elif ext == ".docx":
            extracted = DOCXParser.parse_docx(dest_path, dataset_id=file_hash[:8], filename=filename)
            row_count = len(extracted.paragraphs)
            col_count = len(extracted.headings)
            schema_meta = {
                "file_type": "document",
                "format": "docx",
                "title": extracted.title,
                "author": extracted.author,
                "section_count": extracted.page_or_section_count,
                "paragraph_count": len(extracted.paragraphs),
                "heading_count": len(extracted.headings),
                "table_count": len(extracted.tables),
                "evidence_count": len(extracted.evidence_items),
                "structured_metrics": extracted.structured_metrics_found,
                "columns": [],
                "numeric_candidates": list(extracted.structured_metrics_found.keys()),
                "datetime_candidates": [],
                "categorical_candidates": [],
                "suggested_target": list(extracted.structured_metrics_found.keys())[0] if extracted.structured_metrics_found else None,
                "suggested_date": None
            }
        elif ext in [".csv", ".txt", ".xlsx", ".xls"]:
            df = IngestionService.load_dataframe(dest_path)
            row_count, col_count = df.shape
            schema_meta = IngestionService.extract_schema_metadata(df)
            schema_meta["file_type"] = "structured_dataset"
            schema_meta["format"] = "xlsx" if ext in [".xlsx", ".xls"] else "csv"
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {', '.join(IngestionService.SUPPORTED_FORMATS)}")

        return dest_path, file_hash, file_size, row_count, col_count, IngestionService.normalize_for_json(schema_meta)

    @staticmethod
    def normalize_for_json(data: Any) -> Any:
        """Centralized normalization ensuring all metadata and structures are JSON-serializable."""
        return normalize_metadata_for_json(data)

    _DF_CACHE: Dict[str, Tuple[float, pd.DataFrame]] = {}

    @classmethod
    def load_dataframe(cls, file_path: Path) -> pd.DataFrame:
        """Loads dataset in read-only mode with in-memory caching to optimize large dataset pipelines."""
        resolved_path = str(file_path.resolve())
        mtime = file_path.stat().st_mtime if file_path.exists() else 0.0

        if resolved_path in cls._DF_CACHE:
            cached_mtime, cached_df = cls._DF_CACHE[resolved_path]
            if cached_mtime == mtime:
                return cached_df.copy()

        ext = file_path.suffix.lower()
        if ext in [".csv", ".txt"]:
            df = pd.read_csv(file_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        elif ext in [".pdf", ".docx"]:
            # If tabular data was extracted, return table as DataFrame; otherwise return paragraph frame
            raise ValueError(f"File '{file_path.name}' is a business document ({ext}), not a raw tabular dataset.")
        else:
            raise ValueError(f"Unsupported format: {ext}")

        # Evict oldest entry if cache exceeds limit
        if len(cls._DF_CACHE) >= 6:
            oldest = next(iter(cls._DF_CACHE))
            del cls._DF_CACHE[oldest]

        cls._DF_CACHE[resolved_path] = (mtime, df)
        return df.copy()

    @staticmethod
    def is_identifier_column(col_name: str, series: pd.Series, unique_count: Optional[int] = None, total_rows: Optional[int] = None) -> bool:
        """
        Determines whether a column is an identifier (e.g. InvoiceNo, CustomerID, OrderID, UUID)
        rather than an analytical business factor or numeric target.
        """
        if total_rows is None:
            total_rows = len(series)
        if unique_count is None:
            unique_count = int(series.nunique())

        name_clean = str(col_name).strip().lower()

        # Product codes/SKUs represent products, not pure transaction/user IDs
        if any(k in name_clean for k in ["stockcode", "stock_code", "sku", "product_code"]):
            return False

        id_patterns = [
            "id", "uuid", "guid", "key", "invoice", "invoiceno", "invoice_no",
            "order_id", "order_no", "orderno", "trans_id", "transaction_id", "txn_id",
            "row_id", "rowid", "account_id", "account_no", "customer_id", "customerid",
            "cust_id", "client_id", "user_id", "userid"
        ]

        matches_pattern = any(
            name_clean == p or name_clean.endswith(f"_{p}") or name_clean.endswith(p) or p in name_clean
            for p in id_patterns
        )

        if matches_pattern:
            if unique_count > 30 or unique_count == total_rows or (total_rows > 0 and (unique_count / total_rows) > 0.005):
                return True
            if unique_count > 10 and total_rows > 100:
                return True

        if total_rows > 50 and unique_count == total_rows:
            return True

        # High cardinality alphanumeric codes (e.g. C547502, 536365)
        if (pd.api.types.is_string_dtype(series) or series.dtype == "object") and total_rows > 500 and unique_count > 200:
            business_dims = ["country", "state", "city", "region", "category", "type", "status", "segment", "department"]
            if not any(k in name_clean for k in business_dims):
                sample_vals = [str(x) for x in series.dropna().head(10).tolist()]
                if sample_vals and all(re.match(r'^[A-Za-z0-9_-]{3,25}$', s) for s in sample_vals):
                    return True

        return False

    @staticmethod
    def detect_dataset_capabilities(df: pd.DataFrame) -> Dict[str, Any]:
        """Identifies analytical capabilities deterministically supported by the dataset schema."""
        has_date = any(
            pd.api.types.is_datetime64_any_dtype(df[c]) or
            any(k in str(c).lower() for k in ["date", "time", "timestamp", "period", "day", "month", "year"])
            for c in df.columns
        )
        has_quantity = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["quantity", "qty", "volume", "units", "items_count"])
            for c in df.columns
        )
        has_unit_price = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["unitprice", "unit_price", "price", "rate", "tariff"])
            for c in df.columns
        )
        has_revenue = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["revenue", "sales", "net_revenue", "gross_sales", "turnover", "total_sales", "gmv"])
            for c in df.columns
        )
        has_profit = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["profit", "net_profit", "net_income", "earnings"])
            for c in df.columns
        )
        has_cost = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["cost", "expenses", "operating_cost", "cogs", "total_cost", "overhead"])
            for c in df.columns
        )
        has_discount = any(
            pd.api.types.is_numeric_dtype(df[c]) and any(k in str(c).lower() for k in ["discount", "discount_rate", "discount_pct", "markdown", "rebate"])
            for c in df.columns
        )
        has_customer_id = any(
            any(k in str(c).lower() for k in ["customer", "customer_id", "customerid", "client", "account", "user_id"])
            for c in df.columns
        )
        has_product_id = any(
            any(k in str(c).lower() for k in ["stockcode", "stock_code", "product_id", "productid", "item_id", "sku", "product"])
            for c in df.columns
        )
        has_region = any(
            any(k in str(c).lower() for k in ["country", "region", "state", "territory", "market", "area", "geo", "city"])
            for c in df.columns
        )
        has_category = any(
            any(k in str(c).lower() for k in ["category", "segment", "department", "genre", "product_type", "type"])
            for c in df.columns
        )

        return {
            "has_date": has_date,
            "has_quantity": has_quantity,
            "has_unit_price": has_unit_price,
            "has_revenue": has_revenue,
            "has_profit": has_profit,
            "has_cost": has_cost,
            "has_discount": has_discount,
            "has_customer_id": has_customer_id,
            "has_product_id": has_product_id,
            "has_region": has_region,
            "has_category": has_category,
            "estimated_transaction_value_available": bool(has_quantity and has_unit_price)
        }

    @staticmethod
    def extract_schema_metadata(df: pd.DataFrame) -> Dict[str, Any]:
        """Profiles dataset columns, types, missingness, and identifying candidates."""
        columns_meta = []
        numeric_candidates = []
        datetime_candidates = []
        categorical_candidates = []
        identifier_candidates = []

        total_rows = len(df)

        for col in df.columns:
            series = df[col]
            null_count = int(series.isnull().sum())
            null_pct = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0
            unique_count = int(series.nunique(dropna=True))

            sample_vals = [
                normalize_metadata_for_json(val)
                for val in series.dropna().head(5).tolist()
            ]

            inferred_type = "categorical"
            min_val, max_val, mean_val, median_val, std_val = None, None, None, None, None

            # 1. Datetime detection
            if pd.api.types.is_datetime64_any_dtype(series):
                inferred_type = "datetime"
                datetime_candidates.append(str(col))
                clean_dt = series.dropna()
                if len(clean_dt) > 0:
                    min_val = clean_dt.min().isoformat() if hasattr(clean_dt.min(), "isoformat") else str(clean_dt.min())
                    max_val = clean_dt.max().isoformat() if hasattr(clean_dt.max(), "isoformat") else str(clean_dt.max())
            elif series.dtype == "object":
                sample_str = str(series.dropna().iloc[0]) if len(series.dropna()) > 0 else ""
                if any(delim in sample_str for delim in ["-", "/", ":"]) and len(sample_str) >= 8:
                    try:
                        parsed = pd.to_datetime(series.dropna().head(20), format="mixed", errors="coerce")
                        if parsed.notnull().mean() > 0.8:
                            inferred_type = "datetime"
                            datetime_candidates.append(str(col))
                            clean_parsed = pd.to_datetime(series.dropna(), format="mixed", errors="coerce").dropna()
                            if len(clean_parsed) > 0:
                                min_val = clean_parsed.min().isoformat() if hasattr(clean_parsed.min(), "isoformat") else str(clean_parsed.min())
                                max_val = clean_parsed.max().isoformat() if hasattr(clean_parsed.max(), "isoformat") else str(clean_parsed.max())
                    except Exception:
                        pass

            # 2. Non-datetime: Check for Identifier vs Numeric vs Categorical
            if inferred_type != "datetime":
                is_id = IngestionService.is_identifier_column(str(col), series, unique_count, total_rows)

                if is_id:
                    inferred_type = "identifier"
                    identifier_candidates.append(str(col))
                elif pd.api.types.is_numeric_dtype(series):
                    inferred_type = "numeric"
                    numeric_candidates.append(str(col))
                    clean_s = series.dropna()
                    if len(clean_s) > 0:
                        min_val = float(clean_s.min())
                        max_val = float(clean_s.max())
                        m_val = clean_s.mean()
                        mean_val = round(float(m_val), 4) if not math.isnan(m_val) else None
                        med_val = clean_s.median()
                        median_val = round(float(med_val), 4) if not math.isnan(med_val) else None
                        s_val = clean_s.std() if len(clean_s) > 1 else np.nan
                        std_val = round(float(s_val), 4) if not math.isnan(s_val) else None
                else:
                    inferred_type = "categorical"
                    # Only add to business categorical candidates if cardinality is bounded (2 to 60)
                    if 2 <= unique_count <= 60:
                        categorical_candidates.append(str(col))

            columns_meta.append({
                "name": str(col),
                "dtype": str(series.dtype),
                "inferred_type": inferred_type,
                "null_count": null_count,
                "null_percentage": null_pct,
                "unique_count": unique_count,
                "sample_values": sample_vals,
                "min_val": min_val,
                "max_val": max_val,
                "mean_val": mean_val,
                "median_val": median_val,
                "std_val": std_val,
            })

        suggested_target = None
        priority_names = ["revenue", "sales", "profit", "margin", "gmv", "amount", "quantity", "volume", "turnover", "unitprice", "price"]
        for p in priority_names:
            matches = [c for c in numeric_candidates if p in c.lower()]
            if matches:
                suggested_target = matches[0]
                break
        if not suggested_target and numeric_candidates:
            suggested_target = numeric_candidates[0]

        suggested_date = datetime_candidates[0] if datetime_candidates else None
        capabilities = IngestionService.detect_dataset_capabilities(df)

        return IngestionService.normalize_for_json({
            "columns": columns_meta,
            "numeric_candidates": numeric_candidates,
            "datetime_candidates": datetime_candidates,
            "categorical_candidates": categorical_candidates,
            "identifier_candidates": identifier_candidates,
            "suggested_target": suggested_target,
            "suggested_date": suggested_date,
            "capabilities": capabilities,
        })
