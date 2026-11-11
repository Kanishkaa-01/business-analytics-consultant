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

    ORDER_ID_KEYWORDS = [
        "order_id", "order id", "orderid", "order_no", "orderno", "order no",
        "invoice_no", "invoiceno", "invoice no", "invoice", "trans_id",
        "transaction_id", "transaction id", "txn_id", "txnid"
    ]

    EMPLOYEE_ID_KEYWORDS = [
        "employee_number", "employeenumber", "employee_id", "employeeid",
        "staff_id", "staffid", "worker_id", "workerid"
    ]

    BATCH_ID_KEYWORDS = [
        "batch_id", "batchid", "lot_id", "lotid", "run_id", "runid"
    ]

    ACCOUNT_ID_KEYWORDS = [
        "account_id", "accountid", "subscriber_id", "subscriberid", "tenant_id", "tenantid"
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

        if pd.api.types.is_float_dtype(series):
            return False

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

        if total_rows > 50 and unique_count == total_rows and (pd.api.types.is_string_dtype(series) or series.dtype == "object"):
            return True

        return False

    @classmethod
    def detect_metrics(cls, df: pd.DataFrame, target_override: Optional[str] = None, date_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for semantic metric detection.
        Returns a structured dictionary of detected metrics, subtypes, domain classification, and variables.
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

        # 3. Entity Identifiers (Customer, Order, Employee, Batch, Account)
        customer_id_col = cls._detect_customer_identifier(df)
        customer_segment_col = cls._detect_customer_segment(df)
        order_id_col = cls._detect_order_identifier(df)
        employee_id_col = cls._detect_employee_identifier(df)
        batch_id_col = cls._detect_batch_identifier(df)
        account_id_col = cls._detect_account_identifier(df)

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

        # 8. Domain Classification
        domain_info = cls.detect_domain(df)

        # 9. Domain-Specific Columns Extraction
        cols_lower = {str(c).strip().lower(): c for c in df.columns}

        # Workforce / HR columns
        workforce_cols = {
            "attrition": cls._detect_first_match(df, cols, ["attrition", "turnover", "left_company", "resigned", "is_attrited"]),
            "income": cls._detect_first_match(df, num_cols, ["monthlyincome", "monthly_income", "salary", "hourlyrate", "dailyrate", "wage", "base_salary"]),
            "overtime": cls._detect_first_match(df, cols, ["overtime", "over_time"]),
            "tenure": cls._detect_first_match(df, num_cols, ["yearsatcompany", "years_at_company", "tenure", "totalworkingyears", "total_working_years"]),
            "satisfaction": cls._detect_first_match(df, num_cols, ["jobsatisfaction", "job_satisfaction", "environmentsatisfaction", "relationship_satisfaction"]),
            "department": cls._detect_first_match(df, cols, ["department", "dept", "business_unit"]),
            "job_role": cls._detect_first_match(df, cols, ["jobrole", "job_role", "role", "title", "position"]),
            "salary_hike": cls._detect_first_match(df, num_cols, ["percentsalaryhike", "salary_hike", "raise_pct"]),
        }

        # Manufacturing / Operations columns
        mfg_cols = {
            "defect_rate": cls._detect_first_match(df, num_cols, ["defect_rate_pct", "defect_rate", "defective_pct", "error_rate"]),
            "defective_units": cls._detect_first_match(df, num_cols, ["defective_units", "defects_count", "scrap_units", "rejected_units"]),
            "downtime": cls._detect_first_match(df, num_cols, ["downtime_minutes", "downtime_hours", "downtime", "idle_time"]),
            "cycle_time": cls._detect_first_match(df, num_cols, ["cycle_time_hours", "cycle_time", "lead_time", "process_time"]),
            "production_cost": cls._detect_first_match(df, num_cols, ["total_production_cost", "production_cost", "manufacturing_cost"]),
            "scrap_cost": cls._detect_first_match(df, num_cols, ["scrap_cost_dollars", "scrap_cost", "waste_cost"]),
            "on_time_delivery": cls._detect_first_match(df, cols, ["on_time_delivery_flag", "on_time_delivery", "delivered_on_time"]),
            "batch_size": cls._detect_first_match(df, num_cols, ["batch_size_units", "batch_size", "lot_size"]),
            "facility": cls._detect_first_match(df, cols, ["facility", "plant", "site", "factory", "location"]),
        }

        # SaaS / Subscription columns
        saas_cols = {
            "arr": cls._detect_first_match(df, num_cols, ["arr_dollars", "arr", "annual_recurring_revenue", "mrr", "mrr_dollars"]),
            "churn": churn_col or cls._detect_first_match(df, cols, ["churn_flag", "is_churn", "churned"]),
            "active_users": cls._detect_first_match(df, num_cols, ["daily_active_users", "dau", "mau", "active_users"]),
            "nps": cls._detect_first_match(df, num_cols, ["nps_satisfaction", "nps", "satisfaction_score"]),
            "support_tickets": cls._detect_first_match(df, num_cols, ["support_tickets_raised", "support_tickets", "tickets"]),
            "feature_adoption": cls._detect_first_match(df, num_cols, ["feature_adoption_pct", "feature_adoption", "adoption_rate"]),
            "plan": cls._detect_first_match(df, cols, ["subscription_plan", "plan", "pricing_tier", "tier"]),
        }

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
            "order_id_col": order_id_col,
            "employee_id_col": employee_id_col,
            "batch_id_col": batch_id_col,
            "account_id_col": account_id_col,
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
            "domain": domain_info["domain"],
            "domain_label": domain_info["domain_label"],
            "entity_label": domain_info["entity_label"],
            "domain_metrics": {
                "workforce": workforce_cols,
                "manufacturing": mfg_cols,
                "saas": saas_cols,
            },
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
                "has_order_entity": order_id_col is not None,
                "has_employee_entity": employee_id_col is not None,
                "has_batch_entity": batch_id_col is not None,
                "has_account_entity": account_id_col is not None,
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

        exclude_terms = ["duration", "cycle_time", "downtime", "lead_time", "delivery_time", "wait_time", "response_time", "time_spent", "training", "overtime", "part_time", "full_time"]
        cols_lower = {str(c).strip().lower(): c for c in df.columns}
        for kw in cls.DATE_KEYWORDS:
            for clean_name, original in cols_lower.items():
                if any(x in clean_name for x in exclude_terms):
                    continue
                if pd.api.types.is_numeric_dtype(df[original]):
                    col_max = df[original].dropna().max() if not df[original].dropna().empty else 0
                    if col_max < 100_000_000:
                        continue
                if kw == clean_name or kw in clean_name:
                    try:
                        sample = df[original].dropna().head(10)
                        if not sample.empty:
                            parsed = pd.to_datetime(sample, errors="coerce")
                            if parsed.notnull().sum() >= len(sample) * 0.7:
                                valid_years = parsed.dropna().dt.year
                                if len(valid_years) > 0 and 1980 <= valid_years.min() and valid_years.max() <= 2060:
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
    def _detect_order_identifier(cls, df: pd.DataFrame) -> Optional[str]:
        """Detects order / transaction ID column distinct from line item indices."""
        for col in df.columns:
            name_clean = str(col).strip().lower()
            for kw in cls.ORDER_ID_KEYWORDS:
                if name_clean == kw or name_clean.endswith(f"_{kw}") or name_clean.startswith(f"{kw}_"):
                    return col
            if re.match(r'^(order|invoice|txn|trans|transaction)[-_ ]?(id|no|num|number|key|code)$', name_clean):
                return col
        return None

    @classmethod
    def _detect_employee_identifier(cls, df: pd.DataFrame) -> Optional[str]:
        """Detects employee / workforce identification columns."""
        for col in df.columns:
            name_clean = str(col).strip().lower()
            for kw in cls.EMPLOYEE_ID_KEYWORDS:
                if name_clean == kw or kw in name_clean:
                    return col
            if re.match(r'^(emp|employee|staff|worker)[-_ ]?(id|no|num|number|key|code)$', name_clean):
                return col
        return None

    @classmethod
    def _detect_batch_identifier(cls, df: pd.DataFrame) -> Optional[str]:
        """Detects manufacturing batch / lot / run identifier."""
        for col in df.columns:
            name_clean = str(col).strip().lower()
            for kw in cls.BATCH_ID_KEYWORDS:
                if name_clean == kw or kw in name_clean:
                    return col
            if re.match(r'^(batch|lot|run|production)[-_ ]?(id|no|num|number|code)$', name_clean):
                return col
        return None

    @classmethod
    def _detect_account_identifier(cls, df: pd.DataFrame) -> Optional[str]:
        """Detects SaaS / subscription account identifier."""
        for col in df.columns:
            name_clean = str(col).strip().lower()
            for kw in cls.ACCOUNT_ID_KEYWORDS:
                if name_clean == kw or kw in name_clean:
                    return col
            if re.match(r'^(acct|account|subscriber|tenant)[-_ ]?(id|no|num|number|key)$', name_clean):
                return col
        return None

    @classmethod
    def infer_column_unit(cls, col_name: str, series: Optional[pd.Series] = None) -> str:
        """Infers metric unit from column naming semantics and optional series values."""
        name_clean = str(col_name).strip().lower()
        if any(k in name_clean for k in ["revenue", "sales", "price", "profit", "amount", "cost", "income", "salary", "arr", "mrr", "dollars", "spend", "expenditure", "wage", "usd", "balance", "deposit", "loan", "asset", "capital", "fee"]):
            return "$"
        if any(k in name_clean for k in ["pct", "percent", "rate", "margin", "discount", "ratio", "share"]):
            return "%"
        if any(k in name_clean for k in ["hours", "cycle_time"]):
            return "hrs"
        if any(k in name_clean for k in ["minutes", "downtime"]):
            return "mins"
        if any(k in name_clean for k in ["days"]):
            return "days"
        if any(k in name_clean for k in ["quantity", "volume", "units", "items", "batches", "tickets"]):
            return "units"
        if any(k in name_clean for k in ["employees", "headcount", "workers"]):
            return "employees"
        if any(k in name_clean for k in ["accounts", "subscribers"]):
            return "accounts"
        return ""

    @classmethod
    def detect_domain(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Determines domain (retail, workforce, manufacturing, saas, general) based on
        columns, data types, and semantic keywords.
        """
        cols_lower = [str(c).strip().lower() for c in df.columns]

        scores = {
            "retail": 0,
            "workforce": 0,
            "manufacturing": 0,
            "saas": 0,
            "financial": 0
        }

        for col in cols_lower:
            # Retail signals
            if any(k in col for k in ["order_id", "invoiceno", "invoice_no", "sales", "profit", "discount", "cogs", "sku", "product"]):
                scores["retail"] += 2
            elif any(k in col for k in ["revenue", "price", "quantity", "customer"]):
                scores["retail"] += 1

            # Workforce / HR signals
            if any(k in col for k in ["attrition", "employeenumber", "employee_id", "employee_number", "jobrole", "job_role", "monthlyincome", "monthly_income", "overtime", "yearsatcompany", "totalworkingyears"]):
                scores["workforce"] += 3
            elif any(k in col for k in ["department", "salary", "wage", "satisfaction", "tenure", "educationfield", "performancerating"]):
                scores["workforce"] += 1

            # Manufacturing / Operations signals
            if any(k in col for k in ["batch_id", "batchid", "defect_rate", "defective_units", "downtime", "cycle_time", "scrap_cost", "production_cost"]):
                scores["manufacturing"] += 3
            elif any(k in col for k in ["facility", "plant", "raw_material", "yield", "supplier", "on_time_delivery"]):
                scores["manufacturing"] += 1

            # SaaS signals
            if any(k in col for k in ["arr_dollars", "arr", "mrr", "churn_flag", "daily_active_users", "dau", "nps_satisfaction", "subscription_plan", "expansion_arr"]):
                scores["saas"] += 3
            elif any(k in col for k in ["churn", "active_users", "nps", "support_tickets", "feature_adoption"]):
                scores["saas"] += 1

            # Financial / Banking signals
            if any(k in col for k in ["balance", "loan", "deposit", "credit", "asset", "liability", "principal", "interest_rate", "euribor", "cons.price.idx", "cons.conf.idx", "nr.employed"]):
                scores["financial"] += 2
            elif any(k in col for k in ["transaction", "portfolio", "dividend", "yield", "capital"]):
                scores["financial"] += 1

        top_domain = max(scores, key=scores.get)
        top_score = scores[top_domain]

        if top_score < 2:
            return {
                "domain": "general",
                "domain_label": "General Analytics",
                "entity_label": "Records"
            }

        labels = {
            "retail": ("Retail & E-Commerce", "Orders"),
            "workforce": ("Workforce & HR", "Employees"),
            "manufacturing": ("Manufacturing & Operations", "Batches"),
            "saas": ("Subscription & SaaS", "Accounts"),
            "financial": ("Banking & Financial Services", "Transactions / Accounts")
        }

        dl, el = labels.get(top_domain, ("General Analytics", "Records"))
        return {
            "domain": top_domain,
            "domain_label": dl,
            "entity_label": el
        }

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
            "order_id_col": None,
            "employee_id_col": None,
            "batch_id_col": None,
            "account_id_col": None,
            "churn_col": None,
            "date_col": None,
            "binary_cols": [],
            "derived_relationships": [],
            "domain": "general",
            "domain_label": "General Analytics",
            "entity_label": "Records",
            "domain_metrics": {
                "workforce": {},
                "manufacturing": {},
                "saas": {},
            },
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
                "has_order_entity": False,
                "has_employee_entity": False,
                "has_batch_entity": False,
                "has_account_entity": False,
                "has_churn": False,
                "estimated_txn_value_available": False
            }
        }

