from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from app.models.schemas import (
    TrendFinding,
    AnomalyFinding,
    SegmentComparisonFinding,
    AdvancedFindingsReport,
)


class AdvancedFindingsEngine:
    """
    Phase 12: Advanced Findings Engine
    Generates deterministic Trend Analysis, Anomaly Detection, and Segment Comparisons.
    Adheres strictly to explainability principles: no causal claims, deterministic math.
    """

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        target_col: str,
        date_col: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
    ) -> AdvancedFindingsReport:
        # Edge cases: Empty dataframe or invalid target
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return AdvancedFindingsReport(
                trends=[],
                anomalies=[],
                segment_comparisons=[],
                summary="No records available to perform advanced findings analysis.",
                empty_reason="The dataset contains no records."
            )

        if not target_col or target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if not num_cols:
                return AdvancedFindingsReport(
                    trends=[],
                    anomalies=[],
                    segment_comparisons=[],
                    summary="No numerical metrics available for advanced findings.",
                    empty_reason="Not available in this dataset."
                )
            target_col = num_cols[0]

        metric_label = target_col.replace('_', ' ').title()
        clean_target = df[target_col].dropna()

        if len(clean_target) < 2:
            return AdvancedFindingsReport(
                trends=[],
                anomalies=[],
                segment_comparisons=[],
                summary="Insufficient data points to perform statistical trend or anomaly analysis.",
                empty_reason="Not enough historical data points."
            )

        # -------------------------------------------------------------
        # 12A. Trend Analysis
        # -------------------------------------------------------------
        trends: List[TrendFinding] = []
        has_date = False

        if date_col and date_col in df.columns:
            try:
                temp_df = df[[date_col, target_col]].dropna().copy()
                temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=[date_col])

                if len(temp_df) >= 2:
                    has_date = True
                    temp_df = temp_df.sort_values(by=date_col)
                    # Group by period string
                    date_series = temp_df[date_col]
                    time_span_days = (date_series.max() - date_series.min()).days
                    fmt = "%Y-%m-%d" if time_span_days < 60 else "%Y-%m"

                    grouped = temp_df.groupby(temp_df[date_col].dt.strftime(fmt))[target_col].sum().reset_index()

                    if len(grouped) >= 2:
                        first_val = float(grouped[target_col].iloc[0])
                        last_val = float(grouped[target_col].iloc[-1])
                        growth_pct = round(((last_val - first_val) / max(1.0, abs(first_val))) * 100, 1) if first_val != 0 else 0.0

                        if growth_pct > 3.0:
                            direction = "increasing"
                        elif growth_pct < -3.0:
                            direction = "decreasing"
                        else:
                            direction = "stable"

                        max_idx = grouped[target_col].idxmax()
                        min_idx = grouped[target_col].idxmin()

                        highest_period = str(grouped.iloc[max_idx][date_col])
                        highest_val = round(float(grouped.iloc[max_idx][target_col]), 2)
                        lowest_period = str(grouped.iloc[min_idx][date_col])
                        lowest_val = round(float(grouped.iloc[min_idx][target_col]), 2)

                        stmt = (
                            f"{metric_label} showed an {direction} pattern ({growth_pct:+,.1f}% shift across "
                            f"{len(grouped)} periods). Highest observed period was {highest_period} (${highest_val:,.2f}), "
                            f"and lowest observed period was {lowest_period} (${lowest_val:,.2f})."
                        )

                        trends.append(TrendFinding(
                            metric=metric_label,
                            direction=direction,
                            growth_pct=growth_pct,
                            highest_period=highest_period,
                            highest_value=highest_val,
                            lowest_period=lowest_period,
                            lowest_value=lowest_val,
                            summary_statement=stmt,
                            periods_analyzed=len(grouped)
                        ))
            except Exception:
                pass

        # -------------------------------------------------------------
        # 12B. Deterministic Anomaly Detection (IQR + Z-Score)
        # -------------------------------------------------------------
        anomalies: List[AnomalyFinding] = []
        q1 = float(clean_target.quantile(0.25))
        q3 = float(clean_target.quantile(0.75))
        iqr = q3 - q1
        median_val = float(clean_target.median())
        mean_val = float(clean_target.mean())
        std_val = float(clean_target.std()) if len(clean_target) > 1 else 0.0

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outlier_rows = df[(df[target_col] < lower_bound) | (df[target_col] > upper_bound)]

        for idx, row in outlier_rows.head(6).iterrows():
            obs_val = round(float(row[target_col]), 2)
            dev = round(obs_val - median_val, 2)
            dev_pct = round((abs(dev) / max(1.0, abs(median_val))) * 100, 1)

            period_or_rec = f"Record #{idx + 1}"
            if date_col and date_col in row and pd.notna(row[date_col]):
                period_or_rec = str(row[date_col])[:10]

            severity = "High" if dev_pct > 60 else "Medium"
            dir_str = "unusually high" if dev > 0 else "unusually low"

            stmt = (
                f"{metric_label} in {period_or_rec} was {dir_str} compared with the observed distribution "
                f"(observed: ${obs_val:,.2f}, expected baseline: ${median_val:,.2f}, deviation: {dev:+,.2f} / {dev_pct:.1f}%)."
            )

            anomalies.append(AnomalyFinding(
                metric=metric_label,
                period_or_record=period_or_rec,
                observed_value=obs_val,
                expected_value=round(median_val, 2),
                expected_lower=round(lower_bound, 2),
                expected_upper=round(upper_bound, 2),
                deviation=dev,
                deviation_pct=dev_pct,
                method="IQR (1.5x)",
                severity=severity,
                statement=stmt
            ))

        # -------------------------------------------------------------
        # 12C. Segment Comparison
        # -------------------------------------------------------------
        segment_comparisons: List[SegmentComparisonFinding] = []
        valid_dims = []
        candidate_list = dimensions if dimensions else [c for c in df.columns if c != target_col and c != date_col]
        for c in candidate_list:
            if c not in df.columns or c == target_col or c == date_col:
                continue
            name_clean = str(c).strip().lower()
            if any(k in name_clean for k in ["invoice", "invoiceno", "order_id", "transaction_id", "row_id", "uuid"]):
                continue
            if name_clean in ["id", "customerid", "customer_id", "userid", "clientid"]:
                continue
            nunique = int(df[c].nunique())
            if 2 <= nunique <= 60 and not pd.api.types.is_numeric_dtype(df[c]):
                valid_dims.append(c)
            elif 2 <= nunique <= 15 and pd.api.types.is_numeric_dtype(df[c]) and not any(k in name_clean for k in ["id", "no", "num", "code"]):
                valid_dims.append(c)
        dimensions = valid_dims

        # Secondary metric to detect associated patterns (e.g. discount, margin, unit_cost)
        other_num_cols = [
            c for c in df.columns
            if c != target_col and pd.api.types.is_numeric_dtype(df[c])
        ]
        sec_col = other_num_cols[0] if other_num_cols else None

        for dim in dimensions[:4]:
            if dim in df.columns:
                clean_dim_df = df[[dim, target_col]].dropna()
                if clean_dim_df[dim].nunique() >= 2:
                    agg = clean_dim_df.groupby(dim)[target_col].agg(["sum", "mean"]).reset_index()
                    agg = agg.sort_values(by="sum", ascending=False)

                    top_row = agg.iloc[0]
                    bottom_row = agg.iloc[-1]

                    top_seg = str(top_row[dim])
                    top_val = round(float(top_row["sum"]), 2)
                    bottom_seg = str(bottom_row[dim])
                    bottom_val = round(float(bottom_row["sum"]), 2)

                    spread = round(((top_val - bottom_val) / max(1.0, abs(bottom_val))) * 100, 1)

                    assoc_pattern = None
                    if sec_col and sec_col in df.columns:
                        try:
                            sec_agg = df.groupby(dim)[sec_col].mean()
                            sec_top = float(sec_agg.get(top_row[dim], 0.0))
                            sec_bot = float(sec_agg.get(bottom_row[dim], 0.0))
                            assoc_pattern = (
                                f"'{bottom_seg}' is also associated with an average {sec_col.replace('_', ' ')} of {sec_bot:,.2f} "
                                f"compared with {sec_top:,.2f} in '{top_seg}'."
                            )
                        except Exception:
                            pass

                    dim_label = dim.replace('_', ' ').title()
                    stmt = (
                        f"Within {dim_label}, '{top_seg}' had the highest observed {metric_label} (${top_val:,.2f}) "
                        f"while '{bottom_seg}' had the lowest (${bottom_val:,.2f}). "
                        f"This pattern represents a {spread:.1f}% spread between the top and bottom segments."
                    )

                    segment_comparisons.append(SegmentComparisonFinding(
                        dimension=dim_label,
                        top_segment=top_seg,
                        top_segment_value=top_val,
                        bottom_segment=bottom_seg,
                        bottom_segment_value=bottom_val,
                        metric=metric_label,
                        spread_pct=spread,
                        associated_pattern=assoc_pattern,
                        statement=stmt
                    ))

        # Summary statement
        parts = []
        if trends:
            parts.append(f"Trend: {trends[0].summary_statement}")
        if anomalies:
            parts.append(f"Anomalies: {len(anomalies)} notable outlier records identified.")
        else:
            parts.append("Anomalies: No acute anomalies detected beyond standard IQR thresholds.")
        if segment_comparisons:
            parts.append(f"Segment comparisons: {len(segment_comparisons)} categorical dimensions evaluated.")

        summary_text = " ".join(parts)

        return AdvancedFindingsReport(
            trends=trends,
            anomalies=anomalies,
            segment_comparisons=segment_comparisons,
            summary=summary_text,
            has_date_dimension=has_date,
            empty_reason=None
        )
