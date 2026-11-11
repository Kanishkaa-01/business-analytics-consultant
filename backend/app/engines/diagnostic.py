from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.schemas import (
    DiagnosticReport,
    VarianceBreakdownItem,
    SegmentDiagnostic,
)
from app.services.temporal_helper import TemporalHelper


class DiagnosticEngine:
    @staticmethod
    def diagnose_variance(
        df: pd.DataFrame,
        target_col: str,
        date_col: Optional[str] = None,
        dimensions: Optional[List[str]] = None
    ) -> DiagnosticReport:
        """
        Answers Question 2: 'Why is it happening?'
        Performs mathematical variance decomposition, dimension-level drag vs lift analysis,
        segment dispersion profiling, and anomalous cluster isolation.
        """
        if target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns]
            if not numeric_cols:
                raise ValueError("No numeric metric available for diagnostic analysis.")
            target_col = numeric_cols[0]

        # Sanitize and discover valid business dimensions (strictly excluding identifiers)
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

        # Baseline vs current split using TemporalHelper
        temporal = TemporalHelper.analyze_temporal_structure(df, date_col=date_col)
        base_df = temporal["baseline_df"]
        curr_df = temporal["current_df"]

        total_base = float(base_df[target_col].sum()) if len(base_df) > 0 else 0.0
        total_curr = float(curr_df[target_col].sum()) if len(curr_df) > 0 else 0.0
        total_var, total_var_pct = TemporalHelper.calculate_variance(total_curr, total_base)

        variance_breakdowns: List[VarianceBreakdownItem] = []
        segment_diagnostics: List[SegmentDiagnostic] = []
        anomalies_detected: List[Dict[str, Any]] = []

        is_negative_metric = any(term in target_col.lower() for term in ["churn", "loss", "cost", "delay", "defect", "return", "error"])

        # Decompose variance across dimensions
        for dim in dimensions[:4]:  # Top 4 analytical dimensions
            base_grp = base_df.groupby(dim)[target_col].sum()
            curr_grp = curr_df.groupby(dim)[target_col].sum()
            all_segments = set(base_grp.index).union(set(curr_grp.index))

            dim_variances = []
            for seg in all_segments:
                b_val = float(base_grp.get(seg, 0.0))
                c_val = float(curr_grp.get(seg, 0.0))
                diff = c_val - b_val
                diff_pct = round((diff / b_val * 100), 2) if b_val != 0 else 0.0
                dim_variances.append({
                    "segment": str(seg),
                    "baseline": b_val,
                    "actual": c_val,
                    "diff": diff,
                    "diff_pct": diff_pct,
                    "abs_diff": abs(diff)
                })

            sum_abs_diff = sum(item["abs_diff"] for item in dim_variances)

            underperforming = []
            overperforming = []

            for item in dim_variances:
                share_pct = round((item["abs_diff"] / sum_abs_diff * 100), 2) if sum_abs_diff > 0 else 0.0

                # Determine direction: Drag or Lift
                if is_negative_metric:
                    direction = "Drag" if item["diff"] > 0 else "Lift"
                else:
                    direction = "Drag" if item["diff"] < 0 else "Lift"

                variance_breakdowns.append(VarianceBreakdownItem(
                    dimension=dim,
                    segment=item["segment"],
                    baseline_value=round(item["baseline"], 2),
                    actual_value=round(item["actual"], 2),
                    variance=round(item["diff"], 2),
                    variance_pct=item["diff_pct"],
                    contribution_share_pct=share_pct,
                    direction=direction
                ))

                if direction == "Drag" and share_pct >= 10.0:
                    underperforming.append({
                        "segment": item["segment"],
                        "variance": round(item["diff"], 2),
                        "variance_pct": item["diff_pct"],
                        "share_pct": share_pct
                    })
                elif direction == "Lift" and share_pct >= 10.0:
                    overperforming.append({
                        "segment": item["segment"],
                        "variance": round(item["diff"], 2),
                        "variance_pct": item["diff_pct"],
                        "share_pct": share_pct
                    })

            # Dispersion calculation (Coefficient of Variation of actual segment values)
            vals = [item["actual"] for item in dim_variances]
            mean_v = np.mean(vals) if vals else 0.0
            std_v = np.std(vals) if vals else 0.0
            cv = round(float(std_v / mean_v), 3) if mean_v != 0 else 0.0

            segment_diagnostics.append(SegmentDiagnostic(
                dimension=dim,
                underperforming_segments=sorted(underperforming, key=lambda x: abs(x["variance"]), reverse=True),
                overperforming_segments=sorted(overperforming, key=lambda x: abs(x["variance"]), reverse=True),
                dispersion_gini_or_cv=cv
            ))

        # Detect transaction-level or cluster-level anomalies
        clean_target = df[target_col].dropna()
        q25 = float(clean_target.quantile(0.25))
        q75 = float(clean_target.quantile(0.75))
        iqr = q75 - q25
        high_outliers = df[df[target_col] > (q75 + 2.5 * iqr)]
        low_outliers = df[df[target_col] < (q25 - 2.5 * iqr)]

        if len(high_outliers) > 0:
            top_outlier = high_outliers.sort_values(target_col, ascending=False).iloc[0]
            anomalies_detected.append({
                "type": "Extreme Value Spikes",
                "count": len(high_outliers),
                "sample_impact": float(top_outlier[target_col]),
                "description": f"Detected {len(high_outliers)} severe positive spike(s) exceeding 2.5x IQR threshold.",
                "focal_record_info": {col: str(top_outlier[col]) for col in dimensions[:3]}
            })

        if len(low_outliers) > 0:
            bottom_outlier = low_outliers.sort_values(target_col, ascending=True).iloc[0]
            anomalies_detected.append({
                "type": "Severe Drawdown / Margin Deficits",
                "count": len(low_outliers),
                "sample_impact": float(bottom_outlier[target_col]),
                "description": f"Detected {len(low_outliers)} severe downside drop(s) below lower extreme boundary.",
                "focal_record_info": {col: str(bottom_outlier[col]) for col in dimensions[:3]}
            })

        # Synthesize explainable narrative
        drag_items = [b for b in variance_breakdowns if b.direction == "Drag"]
        drag_items = sorted(drag_items, key=lambda x: x.contribution_share_pct, reverse=True)

        lift_items = [b for b in variance_breakdowns if b.direction == "Lift"]
        lift_items = sorted(lift_items, key=lambda x: x.contribution_share_pct, reverse=True)

        if drag_items:
            top_drag = drag_items[0]
            narrative = (
                f"Analysis of '{target_col}' shows a total difference of {total_var:+.2f} ({total_var_pct:+.1f}%). "
                f"The largest difference occurs in '{top_drag.dimension}', specifically segment '{top_drag.segment}', "
                f"which accounts for {top_drag.contribution_share_pct}% of the negative difference ({top_drag.variance:+.2f})."
            )
        else:
            narrative = (
                f"Performance of '{target_col}' remained stable across evaluated segments, "
                f"with a total difference of {total_var:+.2f} ({total_var_pct:+.1f}%)."
            )

        # -------------------------------------------------------------
        # Synthesize Structured Findings (Problems & Opportunities)
        # -------------------------------------------------------------
        is_money = any(k in target_col.lower() for k in ["revenue", "sales", "price", "profit", "amount", "cost"])
        findings: List[Dict[str, Any]] = []

        # Overall metric finding
        if total_var_pct < -2.0:
            findings.append({
                "title": f"Declining {target_col.replace('_', ' ').title()}",
                "type": "Problem",
                "metric": target_col,
                "observed_value": f"${total_curr:,.2f}" if is_money else f"{total_curr:,.1f}",
                "comparison": f"${total_base:,.2f} baseline" if is_money else f"{total_base:,.1f} baseline",
                "difference": f"{total_var:+,.2f} ({total_var_pct:+.1f}%)",
                "possible_reason": "Multiple segments experienced lower performance across recent observations.",
                "recommended_action": "Examine contributing factors in Possible Reasons and Recommended Actions."
            })
        elif total_var_pct > 2.0:
            findings.append({
                "title": f"Growing {target_col.replace('_', ' ').title()}",
                "type": "Opportunity",
                "metric": target_col,
                "observed_value": f"${total_curr:,.2f}" if is_money else f"{total_curr:,.1f}",
                "comparison": f"${total_base:,.2f} baseline" if is_money else f"{total_base:,.1f} baseline",
                "difference": f"{total_var:+,.2f} ({total_var_pct:+.1f}%)",
                "possible_reason": "Positive demand growth observed across core categories.",
                "recommended_action": "Support growth momentum with adequate inventory and resources."
            })

        # Segment Drag Findings (Problems)
        for item in drag_items[:4]:
            findings.append({
                "title": f"Underperforming Area: {item.segment}",
                "type": "Problem",
                "metric": target_col,
                "observed_value": f"${item.actual_value:,.2f}" if is_money else f"{item.actual_value:,.1f}",
                "comparison": f"${item.baseline_value:,.2f} baseline" if is_money else f"{item.baseline_value:,.1f} baseline",
                "difference": f"{item.variance:+,.2f} ({item.variance_pct:+.1f}%)",
                "possible_reason": f"This segment contributes {item.contribution_share_pct}% of the negative difference.",
                "recommended_action": f"Review operations, costs, and pricing in '{item.segment}'."
            })

        # Segment Lift Findings (Opportunities)
        for item in lift_items[:3]:
            findings.append({
                "title": f"Strong Area: {item.segment}",
                "type": "Opportunity",
                "metric": target_col,
                "observed_value": f"${item.actual_value:,.2f}" if is_money else f"{item.actual_value:,.1f}",
                "comparison": f"${item.baseline_value:,.2f} baseline" if is_money else f"{item.baseline_value:,.1f} baseline",
                "difference": f"{item.variance:+,.2f} ({item.variance_pct:+.1f}%)",
                "possible_reason": f"Positive trajectory delivering {item.contribution_share_pct}% of positive difference.",
                "recommended_action": f"Consider expanding marketing or stock in '{item.segment}'."
            })

        return DiagnosticReport(
            focal_metric=target_col,
            total_variance=round(total_var, 2),
            variance_pct=total_var_pct,
            variance_breakdown=variance_breakdowns[:15],
            segment_diagnostics=segment_diagnostics,
            anomalies_detected=anomalies_detected,
            diagnostic_narrative=narrative,
            findings=findings
        )
