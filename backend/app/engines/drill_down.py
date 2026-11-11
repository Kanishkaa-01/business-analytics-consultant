from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.services.semantic_metrics import SemanticMetricDetector


class DrillDownEngine:
    """
    Deterministic hierarchical multi-level drill-down engine.
    Applies parent filtering, computes segment shares, variances,
    and isolates entity identifiers from categorical breakdown.
    """

    @classmethod
    def execute_drill_down(
        cls,
        df: pd.DataFrame,
        dimension: str,
        metric: Optional[str] = None,
        aggregation: str = "sum",
        parent_filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Executes a deterministic drill-down query on a DataFrame with parent filtering.
        """
        if df is None or df.empty:
            raise ValueError("Dataset is empty or unavailable.")

        if dimension not in df.columns:
            raise ValueError(f"Selected dimension '{dimension}' does not exist in dataset.")

        # Strict Identifier Isolation
        if SemanticMetricDetector.is_identifier_column(dimension, df[dimension]):
            raise ValueError(
                f"Column '{dimension}' is an entity identifier with high cardinality and cannot be used for grouping or drill-down."
            )

        # Apply parent filters
        filtered_df = df.copy()
        applied_filters = parent_filters or {}
        for f_col, f_val in applied_filters.items():
            if f_col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[f_col].astype(str) == str(f_val)]

        if filtered_df.empty:
            return {
                "dimension": dimension,
                "metric": metric or "count",
                "total_value": 0.0,
                "parent_filters": applied_filters,
                "segments": [],
                "next_suggested_dimensions": [],
                "echarts_spec": {}
            }

        # Resolve metric
        num_cols = [c for c in filtered_df.columns if pd.api.types.is_numeric_dtype(filtered_df[c])]
        if not metric or metric not in filtered_df.columns:
            metrics_info = SemanticMetricDetector.detect_metrics(filtered_df)
            metric = metrics_info.get("primary_metric") or (num_cols[0] if num_cols else None)

        if not metric or metric not in filtered_df.columns:
            # Fallback to row counts
            filtered_df["_count"] = 1
            metric = "_count"
            aggregation = "sum"

        # Group by dimension
        valid_agg = "mean" if aggregation == "mean" else "sum"
        grouped = filtered_df.groupby(dimension, observed=True).agg(
            metric_val=(metric, valid_agg),
            record_count=(dimension, "count")
        ).reset_index()

        grouped = grouped.sort_values(by="metric_val", ascending=False)
        total_val = float(filtered_df[metric].sum()) if valid_agg == "sum" else float(filtered_df[metric].mean())

        seg_mean = float(grouped["metric_val"].mean()) if not grouped.empty else 0.0

        segments = []
        chart_labels = []
        chart_values = []

        top_slice = grouped.head(limit)
        for _, row in top_slice.iterrows():
            d_val = str(row[dimension])
            m_val = float(row["metric_val"])
            rec_cnt = int(row["record_count"])
            share = (m_val / total_val * 100.0) if total_val != 0 and valid_agg == "sum" else 0.0
            variance_pct = ((m_val - seg_mean) / seg_mean * 100.0) if seg_mean != 0 else 0.0

            segments.append({
                "dimension_value": d_val,
                "metric_value": round(m_val, 2),
                "share_pct": round(share, 1),
                "record_count": rec_cnt,
                "variance_from_mean_pct": round(variance_pct, 1)
            })
            chart_labels.append(d_val)
            chart_values.append(round(m_val, 2))

        # Next suggested dimensions
        excluded_dims = set(list(applied_filters.keys()) + [dimension])
        next_dims = []
        for col in df.columns:
            if col not in excluded_dims and not pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_datetime64_any_dtype(df[col]):
                if not SemanticMetricDetector.is_identifier_column(col, df[col]):
                    u_cnt = df[col].nunique()
                    if 2 <= u_cnt <= 60:
                        next_dims.append(col)

        # Build ECharts spec
        echarts_spec = {
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "formatter": "{b}: {c}"
            },
            "grid": {"left": "3%", "right": "4%", "bottom": "15%", "top": "10%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": chart_labels,
                "axisLabel": {"interval": 0, "rotate": 25 if len(chart_labels) > 4 else 0}
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": metric,
                "type": "bar",
                "data": chart_values,
                "itemStyle": {
                    "color": "#4F46E5",
                    "borderRadius": [4, 4, 0, 0]
                }
            }]
        }

        return {
            "dimension": dimension,
            "metric": metric,
            "total_value": round(total_val, 2),
            "parent_filters": applied_filters,
            "segments": segments,
            "next_suggested_dimensions": next_dims[:5],
            "echarts_spec": echarts_spec
        }
