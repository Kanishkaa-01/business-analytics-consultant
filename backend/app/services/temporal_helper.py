from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class TemporalHelper:
    """
    Centralized, deterministic chronological and period analysis helper.
    Ensures genuine calendar-time comparisons when timestamps are present,
    and explicit record-order sequence fallback with clear warnings when absent.
    """

    @classmethod
    def analyze_temporal_structure(
        cls,
        df: pd.DataFrame,
        date_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inspects dataframe for valid date columns and determines chronological splits.
        """
        if df is None or df.empty:
            return {
                "has_dates": False,
                "is_record_order": True,
                "date_col": None,
                "baseline_df": pd.DataFrame(),
                "current_df": pd.DataFrame(),
                "baseline_label": "First Half (Record Order)",
                "current_label": "Second Half (Record Order)",
                "methodological_note": "Dataset is empty.",
            }

        work_df = df.copy()
        target_date_col = None

        # Check candidate date column
        if date_col and date_col in work_df.columns:
            target_date_col = date_col
        else:
            # Look for date-like columns
            for col in work_df.columns:
                col_lower = str(col).lower()
                if any(k in col_lower for k in ["date", "time", "timestamp", "datetime", "created_at", "invoicedate", "order_date"]):
                    target_date_col = col
                    break

        # Attempt to parse target date column if found
        has_dates = False
        parsed_series = None
        if target_date_col:
            try:
                parsed = pd.to_datetime(work_df[target_date_col], errors="coerce")
                valid_count = int(parsed.notnull().sum())
                if valid_count > len(work_df) * 0.4 and valid_count >= 2:
                    work_df["__parsed_temporal_date"] = parsed
                    has_dates = True
                    parsed_series = parsed
            except Exception:
                has_dates = False

        if has_dates and parsed_series is not None:
            # Drop rows with NaT for temporal slicing or sort them to the start
            work_df = work_df.sort_values("__parsed_temporal_date", na_position="first").reset_index(drop=True)
            valid_dates = work_df["__parsed_temporal_date"].dropna()
            min_date = valid_dates.min()
            max_date = valid_dates.max()
            date_range_days = (max_date - min_date).days

            # Temporal midpoint
            mid_date = min_date + (max_date - min_date) / 2

            baseline_mask = work_df["__parsed_temporal_date"] <= mid_date
            current_mask = work_df["__parsed_temporal_date"] > mid_date

            # If either slice is empty due to clustering, fallback to 50/50 chronological split
            if baseline_mask.sum() == 0 or current_mask.sum() == 0:
                mid_idx = max(1, len(work_df) // 2)
                base_df = work_df.iloc[:mid_idx]
                curr_df = work_df.iloc[mid_idx:]
            else:
                base_df = work_df[baseline_mask]
                curr_df = work_df[current_mask]

            min_str = min_date.strftime("%Y-%m-%d")
            mid_str = mid_date.strftime("%Y-%m-%d")
            max_str = max_date.strftime("%Y-%m-%d")

            return {
                "has_dates": True,
                "is_record_order": False,
                "date_col": target_date_col,
                "baseline_df": base_df,
                "current_df": curr_df,
                "min_date": min_str,
                "max_date": max_str,
                "date_range_days": date_range_days,
                "baseline_label": f"Earlier Period ({min_str} to {mid_str})",
                "current_label": f"Recent Period ({mid_str} to {max_str})",
                "methodological_note": f"Chronological comparison partitioned across temporal range ({min_str} to {max_str}).",
                "work_df": work_df
            }
        else:
            # Fallback to record-order sequence
            n = len(work_df)
            midpoint = max(1, n // 2)
            base_df = work_df.iloc[:midpoint]
            curr_df = work_df.iloc[midpoint:]

            return {
                "has_dates": False,
                "is_record_order": True,
                "date_col": None,
                "baseline_df": base_df,
                "current_df": curr_df,
                "min_date": None,
                "max_date": None,
                "date_range_days": None,
                "baseline_label": f"Baseline Records (1 to {midpoint})",
                "current_label": f"Recent Records ({midpoint + 1} to {n})",
                "methodological_note": (
                    "Temporal analysis fallback: Dataset lacks an identifiable timestamp column. "
                    "Comparison partitions the first half of records against the second half in row order. "
                    "Findings reflect record sequence rather than true calendar progression."
                ),
                "work_df": work_df
            }

    @staticmethod
    def calculate_variance(current_val: float, baseline_val: float) -> Tuple[float, float]:
        """
        Calculates absolute difference and percentage variance.
        Properly handles zero and negative baselines:
        - When baseline is 0: variance pct is 0.0 (avoiding ZeroDivisionError).
        - When baseline is negative: uses abs(baseline) so improving from -100 to -50 is positive (+50%).
        """
        diff = float(current_val - baseline_val)
        if baseline_val == 0.0:
            var_pct = 0.0
        else:
            var_pct = round((diff / abs(baseline_val)) * 100, 2)
        return round(diff, 2), var_pct
