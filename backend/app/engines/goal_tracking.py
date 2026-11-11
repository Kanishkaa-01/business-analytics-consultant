from typing import Dict, Any, List, Optional
import pandas as pd
from app.services.semantic_metrics import SemanticMetricDetector


class GoalTrackingEngine:
    """
    Deterministic KPI Goal and Target Tracking Engine.
    Monitors progress against quantitative organizational targets.
    """

    @classmethod
    def evaluate_goal(
        cls,
        metric: str,
        target_value: float,
        target_type: str,
        current_val: float,
        baseline_val: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates progress and operational status deterministically.
        """
        if baseline_val is None:
            baseline_val = current_val

        progress_pct = 0.0

        if target_type == "percentage_growth":
            # target_value is percentage (e.g. 10.0 for 10% growth)
            if baseline_val != 0:
                actual_growth_pct = ((current_val - baseline_val) / abs(baseline_val)) * 100.0
                if target_value != 0:
                    progress_pct = (actual_growth_pct / target_value) * 100.0
                else:
                    progress_pct = 100.0 if actual_growth_pct >= 0 else 0.0
            else:
                progress_pct = 100.0 if current_val > 0 else 0.0
        else:
            # Absolute target
            if baseline_val != target_value:
                progress_pct = ((current_val - baseline_val) / (target_value - baseline_val)) * 100.0
            elif target_value != 0:
                progress_pct = (current_val / target_value) * 100.0
            else:
                progress_pct = 100.0 if current_val == target_value else 0.0

        # Bound and determine status
        if progress_pct >= 100.0:
            status = "Target Achieved"
        elif progress_pct >= 75.0:
            status = "On Track"
        elif progress_pct >= 40.0:
            status = "Near Target"
        else:
            status = "Below Target"

        return {
            "metric": metric,
            "target_type": target_type,
            "target_value": round(float(target_value), 2),
            "baseline_value": round(float(baseline_val), 2),
            "current_value": round(float(current_val), 2),
            "progress_pct": round(float(progress_pct), 1),
            "status": status
        }

    @classmethod
    def extract_metric_current_value(cls, df: pd.DataFrame, metric_name: str) -> float:
        """
        Extracts current value of a metric from dataset.
        """
        if df is None or df.empty:
            return 0.0

        # Exact match
        for col in df.columns:
            if col.lower() == metric_name.lower():
                if pd.api.types.is_numeric_dtype(df[col]):
                    return float(df[col].dropna().sum())

        # Semantic match
        metrics_info = SemanticMetricDetector.detect_metrics(df)
        if metric_name.lower() in ["revenue", "sales", "total sales", "net revenue"]:
            rev_col = metrics_info.get("revenue_col")
            if rev_col and rev_col in df.columns:
                return float(df[rev_col].dropna().sum())
        elif metric_name.lower() in ["quantity", "volume", "units"]:
            qty_col = metrics_info.get("quantity_col")
            if qty_col and qty_col in df.columns:
                return float(df[qty_col].dropna().sum())

        # Fallback to first numeric sum
        num_cols = df.select_dtypes(include=["number"]).columns
        if len(num_cols) > 0:
            return float(df[num_cols[0]].dropna().sum())

        return float(len(df))
