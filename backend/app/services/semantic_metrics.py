from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import re


class SemanticMetricDetector:
    """
    Centralized, deterministic semantic metric and schema detection layer.
    Dataset-agnostic: Automatically detects financial, operational, customer,
    and temporal fields based on schema, data types, and semantic patterns.
    """

    # Semantic keyword profiles
    REVENUE_PROFILES = [
        ("net_revenue", ["net_revenue", "net revenue", "net_sales", "net sales"], "Net Revenue"),
        ("gross_sales", ["gross_sales", "gross sales", "gross_revenue", "gross revenue"], "Gross Sales"),
        ("turnover", ["turnover", "total_turnover"], "Turnover"),
        ("sales", ["total_sales", "sales", "sales_amount", "sales_value", "total sales"], "Total Sales"),
        ("revenue", ["revenue", "total_revenue", "total revenue", "gmv"], "Total Revenue"),
    ]

    PROFIT_PROFILES = [
        ("net_profit", ["net_profit", "net profit", "net_income", "net income"], "Net Profit"),
        ("operating_profit", ["operating_profit", "operating profit", "ebit", "operating_income"], "Operating Profit"),
        ("gross_profit", ["gross_profit", "gross profit"], "Gross Profit"),
        ("ebitda", ["ebitda"], "EBITDA"),
        ("profit", ["profit", "earnings", "total_profit"], "Profit"),
    ]

    COST_PROFILES = [
        ("cogs", ["cogs", "cost_of_goods", "cost_of_sales", "cost of goods sold"], "COGS"),
        ("operating_cost", ["operating_cost", "operating cost", "opex"], "Operating Cost"),
        ("expenses", ["expenses", "expense", "total_expense"], "Expenses"),
        ("cost", ["cost", "costs", "total_cost", "total cost", "expenditure", "overhead"], "Total Cost"),
    ]

    PRICE_KEYWORDS = ["unitprice", "unit_price", "unit price", "selling_price", "price", "rate", "tariff"]
    DISCOUNT_KEYWORDS = ["discount_rate", "discount_pct", "discount_percentage", "discount", "markdown", "rebate", "concession"]
    QUANTITY_KEYWORDS = ["quantity", "qty", "volume", "units", "items_count", "item_count", "number_of_items"]

    # Genuine entity identifier keywords (never categorical tiers)
    CUSTOMER_ID_KEYWORDS = [
        "customer_id", "customerid", "client_id", "clientid",
        "account_id", "accountid", "buyer_id", "buyerid",
        "user_id", "userid", "subscriber_id", "subscriberid",
        "member_id", "memberid"
    ]

    # Explicit segmentation fields that must NEVER be counted as customers
    CUSTOMER_SEGMENT_KEYWORDS = [
        "customer_tier", "customer tier", "customertier",
        "customer_segment", "customer segment", "customersegment",
        "account_type", "account type", "membership_type", "membership type",
        "tier", "client_tier", "user_tier", "segment"
    ]

    CHURN_KEYWORDS = ["churn", "churned", "is_churn", "retention", "attrition", "cancelled", "canceled", "lapsed"]
    DATE_KEYWORDS = ["date", "time", "timestamp", "datetime", "created_at", "order_date", "invoice_date", "transaction_date", "period"]

    @classmethod
    def is_identifier_column(cls, col_name: str, series: pd.Series, unique_count: Optional[int] = None, total_rows: Optional[int] = None) -> bool:
        """Determines whether a column is an entity identifier."""
        if total_rows is None:
            total_rows = len(series)
        if unique_count is None:
            unique_count = int(series.nunique())

        name_clean = str(col_name).strip().lower()
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

        return False

    @classmethod
    def detect_metrics(cls, df: pd.DataFrame, target_override: Optional[str] = None, date_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for semantic metric detection.
        Returns a structured dictionary of detected metrics, subtypes, and variables.
        """
        if df is None or df.empty:
            return cls._empty_detection()

        cols = list(df.columns)
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

        # 1. Date Detection
        date_col = cls._detect_date_column(df, date_override)

        # 2. Financial Metrics Detection
        rev_col, rev_label = cls._detect_revenue(df, num_cols)
        profit_col, profit_label = cls._detect_profit(df, num_cols)
        cost_col, cost_label = cls._detect_cost(df, num_cols)
        price_col = cls._detect_first_match(df, num_cols, cls.PRICE_KEYWORDS)
        discount_col = cls._detect_first_match(df, num_cols, cls.DISCOUNT_KEYWORDS)
        qty_col = cls._detect_first_match(df, num_cols, cls.QUANTITY_KEYWORDS)

        # 3. Customer Identifier vs. Segmentation Category Detection
        customer_id_col = cls._detect_customer_identifier(df)
        customer_segment_col = cls._detect_customer_segment(df)

        # 4. Retention / Churn Detection
        churn_col = cls._detect_churn(df)

        # 5. Binary Flag Detection
        binary_cols = cls._detect_binary_columns(df)

        # 6. Mathematical Dependency Detection (Derived Variables)
        derived_relationships = cls._detect_derived_relationships(df, rev_col, profit_col, cost_col, discount_col, price_col, qty_col)

        # 7. Primary Metric Selection
        primary_metric, primary_label = cls._select_primary_metric(
            df, target_override, rev_col, rev_label, qty_col, price_col, num_cols
        )

        return {
            "primary_metric": primary_metric,
            "primary_metric_label": primary_label,
            "primary": {"column": primary_metric, "label": primary_label},
            "revenue": {"column": rev_col, "label": rev_label},
            "profit": {"column": profit_col, "label": profit_label},
            "cost": {"column": cost_col, "label": cost_label},
            "price": {"column": price_col, "label": "Price"},
            "discount": {"column": discount_col, "label": "Discount"},
            "quantity": {"column": qty_col, "label": "Quantity"},
            "customer_identifier": {"column": customer_id_col, "label": "Customer ID"},
            "customer_segment": {"column": customer_segment_col, "label": "Customer Segment"},
            "churn": {"column": churn_col, "label": "Churn"},
            "date": {"column": date_col, "label": "Date"},
            "revenue_col": rev_col,
            "revenue_label": rev_label,
            "profit_col": profit_col,
            "profit_label": profit_label,
            "cost_col": cost_col,
            "cost_label": cost_label,
            "price_col": price_col,
            "discount_col": discount_col,
            "quantity_col": qty_col,
            "customer_id_col": customer_id_col,
            "customer_segment_col": customer_segment_col,
            "churn_col": churn_col,
            "date_col": date_col,
            "binary_cols": binary_cols,
            "derived_relationships": derived_relationships,
            "capabilities": {
                "has_date": date_col is not None,
                "has_revenue": rev_col is not None,
                "has_profit": profit_col is not None or (rev_col is not None and cost_col is not None),
                "has_cost": cost_col is not None,
                "has_price": price_col is not None,
                "has_discount": discount_col is not None,
                "has_quantity": qty_col is not None,
                "has_customer_entity": customer_id_col is not None,
                "has_customer_segment": customer_segment_col is not None,
                "has_churn": churn_col is not None,
                "estimated_txn_value_available": (qty_col is not None and price_col is not None)
            }
        }

    @classmethod
    def _detect_date_column(cls, df: pd.DataFrame, explicit_col: Optional[str] = None) -> Optional[str]:
        if explicit_col and explicit_col in df.columns:
            return explicit_col

        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col

        cols_lower = {str(c).strip().lower(): c for c in df.columns}
        for kw in cls.DATE_KEYWORDS:
            for clean_name, original in cols_lower.items():
                if kw == clean_name or kw in clean_name:
                    try:
                        sample = df[original].dropna().head(10)
                        if not sample.empty:
                            parsed = pd.to_datetime(sample, errors="coerce")
                            if parsed.notnull().sum() >= len(sample) * 0.7:
                                return original
                    except Exception:
                        pass
        return None

    @classmethod
    def _detect_revenue(cls, df: pd.DataFrame, num_cols: List[str]) -> Tuple[Optional[str], Optional[str]]:
        cols_lower = {str(c).strip().lower(): c for c in num_cols}
        for _, keywords, label in cls.REVENUE_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if clean_name == kw or clean_name.startswith(kw) or clean_name.endswith(kw):
                        return orig, label
        # Substring fallback
        for _, keywords, label in cls.REVENUE_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if kw in clean_name:
                        return orig, label
        return None, None

    @classmethod
    def _detect_profit(cls, df: pd.DataFrame, num_cols: List[str]) -> Tuple[Optional[str], Optional[str]]:
        cols_lower = {str(c).strip().lower(): c for c in num_cols}
        for _, keywords, label in cls.PROFIT_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if clean_name == kw or clean_name.startswith(kw) or clean_name.endswith(kw):
                        return orig, label
        for _, keywords, label in cls.PROFIT_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if kw in clean_name:
                        return orig, label
        return None, None

    @classmethod
    def _detect_cost(cls, df: pd.DataFrame, num_cols: List[str]) -> Tuple[Optional[str], Optional[str]]:
        cols_lower = {str(c).strip().lower(): c for c in num_cols}
        for _, keywords, label in cls.COST_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if clean_name == kw or clean_name.startswith(kw) or clean_name.endswith(kw):
                        return orig, label
        for _, keywords, label in cls.COST_PROFILES:
            for kw in keywords:
                for clean_name, orig in cols_lower.items():
                    if kw in clean_name:
                        return orig, label
        return None, None

    @classmethod
    def _detect_first_match(cls, df: pd.DataFrame, candidates: List[str], keywords: List[str]) -> Optional[str]:
        cols_lower = {str(c).strip().lower(): c for c in candidates}
        for kw in keywords:
            for clean_name, orig in cols_lower.items():
                if clean_name == kw or clean_name.startswith(kw) or clean_name.endswith(kw):
                    return orig
        for kw in keywords:
            for clean_name, orig in cols_lower.items():
                if kw in clean_name:
                    return orig
        return None

    @classmethod
    def _detect_customer_identifier(cls, df: pd.DataFrame) -> Optional[str]:
        """
        Detects genuine entity identifiers (customer_id, account_id, CustomerID, Customer Id, etc.).
        Strictly rejects segmentation/tier fields, region/country, and transaction/invoice identifiers.
        """
        for col in df.columns:
            name_clean = str(col).strip().lower()

            # Reject tier/segment categories and geographical/categorical dimensions immediately
            if any(k in name_clean for k in cls.CUSTOMER_SEGMENT_KEYWORDS):
                continue
            if any(k in name_clean for k in ["region", "country", "category", "channel", "type", "market", "invoice", "order"]):
                continue

            # Check for genuine ID patterns
            for kw in cls.CUSTOMER_ID_KEYWORDS:
                if name_clean == kw or name_clean.endswith(f"_{kw}") or name_clean.startswith(f"{kw}_"):
                    return col

            # Regex check for id suffixes with space, hyphen, underscore
            if re.match(r'^(cust|customer|client|account|user|buyer)[-_ ]?(id|no|num|number|key)$', name_clean):
                return col

        return None

    @classmethod
    def _detect_customer_segment(cls, df: pd.DataFrame) -> Optional[str]:
        """Detects segmentation/tier categories like customer_tier, account_type."""
        for col in df.columns:
            name_clean = str(col).strip().lower()
            if any(k in name_clean for k in cls.CUSTOMER_SEGMENT_KEYWORDS):
                # Ensure it's not a unique identifier
                if df[col].nunique() < len(df) or len(df) <= 5:
                    return col
        return None

    @classmethod
    def _detect_churn(cls, df: pd.DataFrame) -> Optional[str]:
        for col in df.columns:
            name_clean = str(col).strip().lower()
            if any(k in name_clean for k in cls.CHURN_KEYWORDS):
                return col
        return None

    @classmethod
    def _detect_binary_columns(cls, df: pd.DataFrame) -> List[str]:
        """
        Identifies binary boolean or 0/1 indicator columns (e.g. returned, churned, approved).
        These columns must NOT be treated as IQR outliers.
        """
        binary_cols = []
        for col in df.columns:
            series = df[col].dropna()
            if series.empty:
                continue
            if pd.api.types.is_bool_dtype(df[col]):
                binary_cols.append(col)
                continue

            unique_vals = set(series.unique())
            if unique_vals.issubset({0, 1}) or unique_vals.issubset({0.0, 1.0}) or unique_vals.issubset({"0", "1", "true", "false", "yes", "no", "y", "n"}):
                binary_cols.append(col)
            elif len(unique_vals) == 2 and any(k in str(col).lower() for k in ["flag", "is_", "has_", "status", "returned", "churned", "cancelled"]):
                binary_cols.append(col)
        return binary_cols

    @classmethod
    def _detect_derived_relationships(
        cls,
        df: pd.DataFrame,
        rev_col: Optional[str],
        profit_col: Optional[str],
        cost_col: Optional[str],
        disc_col: Optional[str],
        price_col: Optional[str],
        qty_col: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Identifies mathematical dependencies between columns to prevent derived
        measures from being ranked as independent explanatory factors (Phase 6).
        """
        relationships = []

        # Profit = Revenue - Cost
        if rev_col and profit_col and cost_col:
            try:
                calc_profit = df[rev_col] - df[cost_col]
                corr = df[profit_col].corr(calc_profit)
                if corr > 0.95:
                    relationships.append({
                        "dependent_var": profit_col,
                        "component_vars": [rev_col, cost_col],
                        "formula": f"{profit_col} = {rev_col} - {cost_col}",
                        "relationship_type": "algebraic_profit"
                    })
            except Exception:
                pass

        # Transaction Value = Quantity * Price
        if qty_col and price_col:
            relationships.append({
                "dependent_var": "estimated_transaction_value",
                "component_vars": [qty_col, price_col],
                "formula": f"estimated_transaction_value = {qty_col} * {price_col}",
                "relationship_type": "price_volume_product"
            })

        # Net Revenue = Gross Sales - Discount
        if rev_col and disc_col:
            relationships.append({
                "dependent_var": rev_col,
                "component_vars": [disc_col],
                "formula": f"{rev_col} influenced by {disc_col}",
                "relationship_type": "discount_deduction"
            })

        return relationships

    @classmethod
    def _select_primary_metric(
        cls,
        df: pd.DataFrame,
        target_override: Optional[str],
        rev_col: Optional[str],
        rev_label: Optional[str],
        qty_col: Optional[str],
        price_col: Optional[str],
        num_cols: List[str]
    ) -> Tuple[str, str]:
        # User override takes precedence
        if target_override and target_override in df.columns and pd.api.types.is_numeric_dtype(df[target_override]):
            return target_override, target_override.replace("_", " ").title()

        # Revenue has priority
        if rev_col:
            return rev_col, rev_label or rev_col.replace("_", " ").title()

        # Quantity * UnitPrice derived transaction value
        if qty_col and price_col and qty_col in df.columns and price_col in df.columns:
            return "estimated_transaction_value", "Estimated Transaction Value"

        # Quantity
        if qty_col:
            return qty_col, "Transaction Volume (Quantity)"

        # Filter out identifier-like numeric columns
        clean_numerics = [
            c for c in num_cols
            if not any(k in str(c).lower() for k in ["id", "uuid", "key", "no", "code", "index", "row"])
        ]
        if clean_numerics:
            chosen = clean_numerics[0]
            return chosen, chosen.replace("_", " ").title()

        if num_cols:
            return num_cols[0], num_cols[0].replace("_", " ").title()

        return "records", "Record Count"

    @classmethod
    def _empty_detection(cls) -> Dict[str, Any]:
        return {
            "primary_metric": "records",
            "primary_metric_label": "Record Count",
            "revenue_col": None,
            "revenue_label": None,
            "profit_col": None,
            "profit_label": None,
            "cost_col": None,
            "cost_label": None,
            "price_col": None,
            "discount_col": None,
            "quantity_col": None,
            "customer_id_col": None,
            "customer_segment_col": None,
            "churn_col": None,
            "date_col": None,
            "binary_cols": [],
            "derived_relationships": [],
            "capabilities": {
                "has_date": False,
                "has_revenue": False,
                "has_profit": False,
                "has_cost": False,
                "has_price": False,
                "has_discount": False,
                "has_quantity": False,
                "has_customer_entity": False,
                "has_customer_segment": False,
                "has_churn": False,
                "estimated_txn_value_available": False
            }
        }
