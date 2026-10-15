import re
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from app.services.semantic_metrics import SemanticMetricDetector
from app.services.temporal_helper import TemporalHelper


class AskDataEngine:
    """
    Deterministic, explainable Natural Language Query Engine for structured datasets.
    Parses user queries into structured aggregation intents and executes strictly
    validated pandas operations. Never evaluates arbitrary code.
    """

    @classmethod
    def generate_suggested_questions(cls, df: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Dynamically generates meaningful business questions tailored to the dataset's schema.
        """
        if df is None or df.empty:
            return ["What is the total number of records in this dataset?"]

        questions = [
            f"What is the total number of records and columns in this dataset?",
        ]

        metrics = SemanticMetricDetector.detect_metrics(df)
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]
        
        # Filter out high-cardinality/identifier columns from categories
        valid_cats = []
        for c in cat_cols:
            if not SemanticMetricDetector.is_identifier_column(c, df[c]):
                unique_c = df[c].nunique()
                if 2 <= unique_c <= 100:
                    valid_cats.append(c)

        target = metrics.get("primary_metric") or (num_cols[0] if num_cols else None)
        date_col = metrics.get("date_col")

        if target and valid_cats:
            first_cat = valid_cats[0]
            questions.append(f"What are the top 5 {first_cat} by total {target}?")
            questions.append(f"What is the distribution of {target} across {first_cat}?")
            if len(valid_cats) > 1:
                questions.append(f"Which {valid_cats[1]} has the highest average {target}?")

        if target:
            questions.append(f"What is the total and average {target} overall?")

        if date_col and target:
            questions.append(f"What is the monthly trend of {target} over time?")

        questions.append("Are there any missing values or data quality issues in this dataset?")

        return questions[:6]

    @classmethod
    def answer_question(cls, df: pd.DataFrame, query: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Interprets natural language query, validates against schema, runs deterministic
        pandas aggregation, and returns structured result with answer text, table, and ECharts.
        """
        if df is None or df.empty:
            return {
                "query": query,
                "understood": False,
                "answer_text": "Dataset is empty or unavailable.",
                "metric_value": None,
                "table_data": [],
                "echarts_spec": None,
                "explanation": "No data available to query.",
                "suggested_followups": []
            }

        cleaned_query = query.strip().lower()
        metrics_info = SemanticMetricDetector.detect_metrics(df)
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        
        # Identify non-identifier categoricals
        cat_cols = []
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c]):
                if not SemanticMetricDetector.is_identifier_column(c, df[c]):
                    cat_cols.append(c)

        date_col = metrics_info.get("date_col")

        # 1. Check for Data Quality / Row Count queries
        if any(term in cleaned_query for term in ["how many rows", "record count", "total records", "number of rows", "total rows"]):
            count = len(df)
            cols_count = len(df.columns)
            return {
                "query": query,
                "understood": True,
                "answer_text": f"The dataset contains **{count:,} rows** and **{cols_count} columns**.",
                "metric_value": float(count),
                "table_data": [{"Metric": "Total Rows", "Value": count}, {"Metric": "Total Columns", "Value": cols_count}],
                "echarts_spec": None,
                "explanation": f"Exact row count derived deterministically from dataset shape ({count} x {cols_count}).",
                "suggested_followups": cls.generate_suggested_questions(df, metadata)[:3]
            }

        if any(term in cleaned_query for term in ["data quality", "missing values", "null values", "null count", "missing count"]):
            null_summary = []
            for c in df.columns:
                n_null = int(df[c].isnull().sum())
                if n_null > 0:
                    pct = round((n_null / len(df)) * 100, 2)
                    null_summary.append({"Column": str(c), "Missing Count": n_null, "Missing Pct": f"{pct}%"})
            
            if not null_summary:
                ans = f"Great news! Across all {len(df):,} records, there are zero missing or null values in any column."
            else:
                ans = f"Found missing values in {len(null_summary)} columns. Column `{null_summary[0]['Column']}` has {null_summary[0]['Missing Count']:,} missing values ({null_summary[0]['Missing Pct']})."

            return {
                "query": query,
                "understood": True,
                "answer_text": ans,
                "metric_value": float(len(null_summary)),
                "table_data": null_summary if null_summary else [{"Status": "Clean", "Missing Values": 0}],
                "echarts_spec": None,
                "explanation": "Calculated via deterministic null-value scan across all columns.",
                "suggested_followups": cls.generate_suggested_questions(df, metadata)[:3]
            }

        # 2. Check for missing business metric requested (e.g. profit, margin when not present)
        for term, label in [("profit", "Profit"), ("margin", "Profit Margin"), ("cogs", "Cost of Goods Sold"), ("churn", "Customer Churn")]:
            if term in cleaned_query:
                # check if dataset actually has this metric
                has_metric = any(term in c.lower() for c in df.columns)
                if not has_metric:
                    available_num = ", ".join([f"`{c}`" for c in num_cols[:5]])
                    return {
                        "query": query,
                        "understood": False,
                        "answer_text": f"**{label} cannot be calculated** from this dataset because no {label.lower()}-related column exists in the uploaded schema. Available numeric metrics are: {available_num}.",
                        "metric_value": None,
                        "table_data": [],
                        "echarts_spec": None,
                        "explanation": f"Schema audit confirmed that neither `{term}` nor direct accounting cost drivers are present in the dataset.",
                        "suggested_followups": [
                            f"What is the total {num_cols[0]}?" if num_cols else "What is the row count?",
                            f"Top 5 categories by {num_cols[0]}?" if num_cols and cat_cols else "Show data quality summary"
                        ]
                    }

        # 3. Detect target metric
        target_metric = None
        for c in num_cols:
            if c.lower() in cleaned_query:
                target_metric = c
                break

        if not target_metric:
            # Semantic keyword search
            if any(w in cleaned_query for w in ["revenue", "sales", "turnover", "income"]):
                target_metric = metrics_info.get("revenue_col") or metrics_info.get("primary_metric")
            elif any(w in cleaned_query for w in ["quantity", "volume", "units", "items", "qty"]):
                target_metric = metrics_info.get("quantity_col")
            elif any(w in cleaned_query for w in ["price", "cost", "rate", "unit price"]):
                target_metric = metrics_info.get("price_col")

        if not target_metric and num_cols:
            target_metric = metrics_info.get("primary_metric") or num_cols[0]

        # 4. Detect dimension (category)
        target_dim = None
        for c in cat_cols:
            if c.lower() in cleaned_query:
                target_dim = c
                break

        # Check preposition "by <col>" or "per <col>" or "across <col>"
        match = re.search(r"(?:by|per|across|in|for)\s+([a-zA-Z0-9_\s]+)", cleaned_query)
        if match and not target_dim:
            candidate = match.group(1).strip()
            for c in cat_cols:
                if candidate in c.lower() or c.lower() in candidate:
                    target_dim = c
                    break

        # Check if user asked for an identifier column
        all_cols_lower = {c.lower(): c for c in df.columns}
        for term in ["customer", "customerid", "customer_id", "invoiceno", "invoice", "transaction_id", "order_id"]:
            if term in cleaned_query:
                matching_col = all_cols_lower.get(term)
                if matching_col and SemanticMetricDetector.is_identifier_column(matching_col, df[matching_col]):
                    # It's an identifier! We don't group by high-cardinality ID, but we can report unique count or top entities
                    n_unique = df[matching_col].nunique()
                    return {
                        "query": query,
                        "understood": True,
                        "answer_text": f"The identifier `{matching_col}` contains **{n_unique:,} unique entities** across {len(df):,} records. To maintain analytical reliability and avoid extreme fragmentation, break downs are performed across business dimensions like {', '.join([f'`{c}`' for c in cat_cols[:3]])}.",
                        "metric_value": float(n_unique),
                        "table_data": [{"Metric": f"Unique {matching_col}", "Count": n_unique}, {"Metric": "Total Records", "Count": len(df)}],
                        "echarts_spec": None,
                        "explanation": f"`{matching_col}` was classified as an entity identifier with high cardinality ({n_unique:,} distinct values).",
                        "suggested_followups": [f"What are the top 5 {cat_cols[0]} by {target_metric}?" if cat_cols and target_metric else "What is the total revenue?"]
                    }

        # 5. Check for Temporal / Trend Query
        is_trend_query = any(w in cleaned_query for w in ["trend", "over time", "monthly", "by month", "timeline", "history", "by year", "daily"])
        if is_trend_query and date_col and target_metric:
            return cls._handle_trend_query(df, query, target_metric, date_col, metrics_info)

        # 6. Check for Ranking / Top N or Breakdown Query
        is_ranking_or_breakdown = target_dim is not None or any(w in cleaned_query for w in ["top", "highest", "lowest", "best", "worst", "breakdown", "distribution", "share"])
        if is_ranking_or_breakdown and target_metric:
            chosen_dim = target_dim or (cat_cols[0] if cat_cols else None)
            if chosen_dim:
                return cls._handle_ranking_query(df, query, target_metric, chosen_dim, cleaned_query)

        # 7. Overall Aggregation Query (Total, Average, Max, Min)
        if target_metric:
            return cls._handle_aggregate_query(df, query, target_metric, cleaned_query)

        # 8. Fallback
        return {
            "query": query,
            "understood": False,
            "answer_text": f"I couldn't identify a specific metric or dimension from your question. Try asking about numeric metrics like {', '.join([f'`{c}`' for c in num_cols[:3]])} or breakdowns by {', '.join([f'`{c}`' for c in cat_cols[:3]])}.",
            "metric_value": None,
            "table_data": [],
            "echarts_spec": None,
            "explanation": "Query terms did not match recognized aggregation patterns or dataset column names.",
            "suggested_followups": cls.generate_suggested_questions(df, metadata)[:4]
        }

    @classmethod
    def _handle_aggregate_query(cls, df: pd.DataFrame, query: str, metric: str, q_lower: str) -> Dict[str, Any]:
        """Calculates single metric aggregations deterministically."""
        s = df[metric].dropna()
        if s.empty:
            return {
                "query": query,
                "understood": True,
                "answer_text": f"No valid numeric data found in column `{metric}`.",
                "metric_value": 0.0,
                "table_data": [],
                "echarts_spec": None,
                "explanation": f"Column `{metric}` contains only null values.",
                "suggested_followups": []
            }

        total_val = float(s.sum())
        mean_val = float(s.mean())
        median_val = float(s.median())
        min_val = float(s.min())
        max_val = float(s.max())

        agg_type = "sum"
        if any(w in q_lower for w in ["average", "mean", "avg"]):
            agg_type = "mean"
            val = mean_val
            ans = f"The **average {metric}** is **{val:,.2f}** (median: {median_val:,.2f}, min: {min_val:,.2f}, max: {max_val:,.2f})."
        elif any(w in q_lower for w in ["maximum", "max", "highest"]):
            agg_type = "max"
            val = max_val
            ans = f"The **maximum {metric}** is **{val:,.2f}**."
        elif any(w in q_lower for w in ["minimum", "min", "lowest"]):
            agg_type = "min"
            val = min_val
            ans = f"The **minimum {metric}** is **{val:,.2f}**."
        elif any(w in q_lower for w in ["median"]):
            agg_type = "median"
            val = median_val
            ans = f"The **median {metric}** is **{val:,.2f}**."
        else:
            val = total_val
            ans = f"The **total {metric}** is **{val:,.2f}** across {len(s):,} valid records (average: {mean_val:,.2f})."

        table = [
            {"Aggregation": "Total (Sum)", "Value": f"{total_val:,.2f}"},
            {"Aggregation": "Average (Mean)", "Value": f"{mean_val:,.2f}"},
            {"Aggregation": "Median", "Value": f"{median_val:,.2f}"},
            {"Aggregation": "Minimum", "Value": f"{min_val:,.2f}"},
            {"Aggregation": "Maximum", "Value": f"{max_val:,.2f}"},
            {"Aggregation": "Record Count", "Value": f"{len(s):,}"}
        ]

        return {
            "query": query,
            "understood": True,
            "answer_text": ans,
            "metric_value": round(val, 2),
            "table_data": table,
            "echarts_spec": None,
            "explanation": f"Aggregated {len(s):,} non-null records from column `{metric}` using standard statistical operations.",
            "suggested_followups": [
                f"What are the top 5 segments by {metric}?",
                f"What is the monthly trend of {metric}?"
            ]
        }

    @classmethod
    def _handle_ranking_query(cls, df: pd.DataFrame, query: str, metric: str, dimension: str, q_lower: str) -> Dict[str, Any]:
        """Calculates dimension breakdowns and top/bottom rankings."""
        # Detect limit
        limit = 5
        match_n = re.search(r"(?:top|bottom)\s+(\d+)", q_lower)
        if match_n:
            limit = int(match_n.group(1))
            limit = max(1, min(limit, 25))

        is_bottom = any(w in q_lower for w in ["bottom", "lowest", "worst", "least"])
        is_avg = any(w in q_lower for w in ["average", "avg", "mean"])

        agg_func = "mean" if is_avg else "sum"
        grouped = df.groupby(dimension)[metric].agg(agg_func).reset_index()
        total_metric = float(df[metric].sum()) if not is_avg else float(df[metric].mean())

        grouped = grouped.sort_values(by=metric, ascending=is_bottom)
        top_slice = grouped.head(limit)

        table_data = []
        chart_labels = []
        chart_values = []

        for _, row in top_slice.iterrows():
            d_val = str(row[dimension])
            m_val = float(row[metric])
            share = (m_val / total_metric * 100) if total_metric != 0 and not is_avg else 0.0
            table_data.append({
                dimension: d_val,
                f"{'Average' if is_avg else 'Total'} {metric}": round(m_val, 2),
                "Share %": f"{share:.1f}%" if not is_avg else "N/A"
            })
            chart_labels.append(d_val)
            chart_values.append(round(m_val, 2))

        lead_entity = chart_labels[0] if chart_labels else "N/A"
        lead_val = chart_values[0] if chart_values else 0.0
        order_str = "lowest" if is_bottom else "highest"
        ans = (
            f"The top {len(chart_labels)} {dimension} by {'average' if is_avg else 'total'} {metric} are shown below. "
            f"**{lead_entity}** ranks {order_str} with **{lead_val:,.2f}** "
            f"({f'{(lead_val / total_metric * 100):.1f}% of total' if not is_avg and total_metric != 0 else ''})."
        )

        echarts_spec = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"left": "3%", "right": "4%", "bottom": "10%", "top": "10%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": chart_labels,
                "axisLabel": {"interval": 0, "rotate": 30 if len(chart_labels) > 4 else 0}
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": f"{'Avg' if is_avg else 'Total'} {metric}",
                "type": "bar",
                "data": chart_values,
                "itemStyle": {"color": "#3B82F6", "borderRadius": [4, 4, 0, 0]}
            }]
        }

        return {
            "query": query,
            "understood": True,
            "answer_text": ans,
            "metric_value": lead_val,
            "table_data": table_data,
            "echarts_spec": echarts_spec,
            "explanation": f"Ranked {len(grouped):,} unique values of `{dimension}` based on deterministic pandas groupby of `{metric}`.",
            "suggested_followups": [
                f"What is the overall average {metric}?",
                f"How does {lead_entity} compare to the overall total?"
            ]
        }

    @classmethod
    def _handle_trend_query(cls, df: pd.DataFrame, query: str, metric: str, date_col: str, metrics_info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates temporal trends over time."""
        try:
            ts_df, freq = TemporalHelper.prepare_time_series(df, date_col, metric, agg_func="sum")
            if ts_df.empty or len(ts_df) < 2:
                return cls._handle_aggregate_query(df, query, metric, query.lower())

            table_data = []
            periods = []
            vals = []
            for _, r in ts_df.iterrows():
                p_str = str(r["period"])
                v_num = float(r["value"])
                periods.append(p_str)
                vals.append(round(v_num, 2))
                table_data.append({"Period": p_str, f"Total {metric}": round(v_num, 2)})

            start_val = vals[0]
            end_val = vals[-1]
            diff = end_val - start_val
            pct_change = (diff / start_val * 100) if start_val != 0 else 0.0
            direction = "increased" if diff > 0 else "decreased" if diff < 0 else "remained flat"

            ans = (
                f"Across **{len(periods)} periods** ({periods[0]} to {periods[-1]}), "
                f"**{metric}** has {direction} from **{start_val:,.2f}** to **{end_val:,.2f}** "
                f"({pct_change:+.1f}% overall change)."
            )

            echarts_spec = {
                "tooltip": {"trigger": "axis"},
                "grid": {"left": "3%", "right": "4%", "bottom": "10%", "top": "10%", "containLabel": True},
                "xAxis": {"type": "category", "data": periods, "axisLabel": {"rotate": 30 if len(periods) > 6 else 0}},
                "yAxis": {"type": "value"},
                "series": [{
                    "name": metric,
                    "type": "line",
                    "data": vals,
                    "smooth": True,
                    "lineStyle": {"color": "#10B981", "width": 3},
                    "itemStyle": {"color": "#10B981"},
                    "areaStyle": {"color": "rgba(16, 185, 129, 0.15)"}
                }]
            }

            return {
                "query": query,
                "understood": True,
                "answer_text": ans,
                "metric_value": end_val,
                "table_data": table_data,
                "echarts_spec": echarts_spec,
                "explanation": f"Aggregated monthly chronological periods along `{date_col}` using deterministic temporal aggregation.",
                "suggested_followups": [
                    f"What is the average {metric} per month?",
                    f"What are the top categories driving this {metric} trend?"
                ]
            }
        except Exception as exc:
            return cls._handle_aggregate_query(df, query, metric, query.lower())
