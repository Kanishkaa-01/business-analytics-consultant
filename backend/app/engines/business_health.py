from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.schemas import BusinessHealthOverview, KpiMetric
from app.services.semantic_metrics import SemanticMetricDetector
from app.services.temporal_helper import TemporalHelper


class BusinessHealthEngine:
    """
    Deterministic, dataset-aware Business Health Index and Overview Engine.
    Implements continuous piecewise trend normalization, dynamic weight renormalization,
    and schema-aware KPI evaluation.
    """

    @staticmethod
    def _normalize_trend(var_pct: float, is_inverted: bool = False) -> float:
        """
        Continuous piecewise linear trend normalization [0.0 to 100.0].
        Avoids discrete arbitrary scores.
        """
        effective_pct = -var_pct if is_inverted else var_pct

        if effective_pct >= 20.0:
            return 100.0
        elif effective_pct >= 10.0:
            return round(85.0 + ((effective_pct - 10.0) / 10.0) * 15.0, 1)
        elif effective_pct >= 0.0:
            return round(70.0 + ((effective_pct - 0.0) / 10.0) * 15.0, 1)
        elif effective_pct >= -10.0:
            return round(50.0 + ((effective_pct - (-10.0)) / 10.0) * 20.0, 1)
        elif effective_pct >= -20.0:
            return round(30.0 + ((effective_pct - (-20.0)) / 10.0) * 20.0, 1)
        else:
            return round(max(0.0, 30.0 + (effective_pct - (-20.0)) * 0.75), 1)

    @staticmethod
    def _normalize_margin(margin_pct: float) -> float:
        """
        Continuous piecewise normalization for profit margin percentage [0.0 to 100.0].
        """
        if margin_pct >= 30.0:
            return 100.0
        elif margin_pct >= 20.0:
            return round(85.0 + ((margin_pct - 20.0) / 10.0) * 15.0, 1)
        elif margin_pct >= 10.0:
            return round(70.0 + ((margin_pct - 10.0) / 10.0) * 15.0, 1)
        elif margin_pct >= 0.0:
            return round(50.0 + ((margin_pct - 0.0) / 10.0) * 20.0, 1)
        else:
            return round(max(0.0, 50.0 + margin_pct * 1.5), 1)

    @staticmethod
    def _normalize_discount(discount_pct: float) -> float:
        """
        Continuous piecewise normalization for discount pressure (lower is healthier).
        """
        if discount_pct <= 5.0:
            return 100.0
        elif discount_pct <= 15.0:
            return round(85.0 + ((15.0 - discount_pct) / 10.0) * 15.0, 1)
        elif discount_pct <= 25.0:
            return round(70.0 + ((25.0 - discount_pct) / 10.0) * 15.0, 1)
        elif discount_pct <= 40.0:
            return round(50.0 + ((40.0 - discount_pct) / 15.0) * 20.0, 1)
        else:
            return round(max(0.0, 50.0 - (discount_pct - 40.0)), 1)

    @staticmethod
    def assess_health(
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None
    ) -> BusinessHealthOverview:
        """
        Answers Question 1: 'What is happening?'
        Calculates understandable business overview metrics and the multi-component
        Business Health Index with dynamic weight renormalization.
        """
        if df is None or df.empty:
            raise ValueError("Cannot assess business health on an empty dataset.")

        # 1. Semantic Metric Detection
        detected = SemanticMetricDetector.detect_metrics(df, target_override=target_col, date_override=date_col)
        rev_info = detected["revenue"]
        profit_info = detected["profit"]
        cost_info = detected["cost"]
        price_info = detected["price"]
        discount_info = detected["discount"]
        qty_info = detected["quantity"]
        cust_id_info = detected["customer_identifier"]
        cust_seg_info = detected["customer_segment"]
        prim_info = detected["primary_metric"]

        rev_col = rev_info["column"]
        profit_col = profit_info["column"]
        cost_col = cost_info["column"]
        price_col = price_info["column"]
        disc_col = discount_info["column"]
        qty_col = qty_info["column"]
        cust_id_col = cust_id_info["column"]
        cust_seg_col = cust_seg_info["column"]
        if isinstance(detected.get("primary_metric"), dict):
            primary_metric = detected["primary_metric"]["column"]
            primary_label = detected["primary_metric"]["label"]
        else:
            primary_metric = detected.get("primary_metric")
            primary_label = detected.get("primary_metric_label") or (str(primary_metric).replace("_", " ").title() if primary_metric else "Primary Metric")

        # 2. Temporal Structure Analysis (Chronological vs Record-Order Sequence)
        temporal = TemporalHelper.analyze_temporal_structure(df, date_col=detected["date"]["column"])
        baseline_slice = temporal["baseline_df"]
        current_slice = temporal["current_df"]
        has_dates = temporal["has_dates"]
        work_df = temporal.get("work_df", df)

        # 3. Overview Financial & Operational Metrics
        total_revenue = float(df[rev_col].sum()) if rev_col else None

        # Estimated Transaction Value if Quantity and Price exist
        estimated_txn_val = None
        if qty_col and price_col and qty_col in df.columns and price_col in df.columns:
            try:
                estimated_txn_val = float((df[qty_col] * df[price_col]).sum())
            except Exception:
                estimated_txn_val = None

        effective_revenue = total_revenue if total_revenue is not None else estimated_txn_val

        # Total Profit
        total_profit = None
        if profit_col:
            total_profit = float(df[profit_col].sum())
        elif rev_col and cost_col:
            total_profit = float(df[rev_col].sum() - df[cost_col].sum())

        # Profit Margin
        profit_margin = None
        if total_profit is not None and effective_revenue and effective_revenue > 0:
            profit_margin = round((total_profit / effective_revenue) * 100, 1)

        # Transactions
        num_transactions = len(df)

        # Average Order Value
        avg_order_value = None
        if effective_revenue is not None and num_transactions > 0:
            avg_order_value = round(effective_revenue / num_transactions, 2)

        # Distinct Customer Count (Strictly entity identifiers, NEVER categorical tiers)
        num_customers = None
        if cust_id_col:
            num_customers = int(df[cust_id_col].dropna().nunique())

        # Average Discount
        avg_discount = None
        if disc_col:
            mean_d = float(df[disc_col].mean())
            avg_discount = round(mean_d * 100, 1) if mean_d <= 1.0 else round(mean_d, 1)

        # Growth Rate (recent vs earlier observation window)
        growth_rate = None
        if effective_revenue is not None and len(baseline_slice) > 0 and len(current_slice) > 0:
            if rev_col:
                b_rev = float(baseline_slice[rev_col].sum())
                c_rev = float(current_slice[rev_col].sum())
            elif qty_col and price_col:
                b_rev = float((baseline_slice[qty_col] * baseline_slice[price_col]).sum())
                c_rev = float((current_slice[qty_col] * current_slice[price_col]).sum())
            else:
                b_rev, c_rev = 0.0, 0.0
            _, growth_rate = TemporalHelper.calculate_variance(c_rev, b_rev)

        # 4. Multi-Component Health Index with Dynamic Weight Renormalization
        # Component 1: Primary Metric Trend (Base Weight: 40%)
        # Component 2: Profit Trend (Base Weight: 25%)
        # Component 3: Profit Margin (Base Weight: 20%)
        # Component 4: Volume Trend (Base Weight: 10%)
        # Component 5: Discount/Cost Pressure (Base Weight: 5%)
        components_pool = []

        # 4a. Primary Metric Trend
        is_neg_primary = any(k in str(primary_metric).lower() for k in ["churn", "cost", "loss", "delay", "defect", "return", "error"])
        if primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric]):
            curr_p = float(current_slice[primary_metric].sum()) if len(current_slice) > 0 else 0.0
            base_p = float(baseline_slice[primary_metric].sum()) if len(baseline_slice) > 0 else 0.0
        else:
            curr_p = float(len(current_slice))
            base_p = float(len(baseline_slice))
        _, prim_var_pct = TemporalHelper.calculate_variance(curr_p, base_p)
        prim_score = BusinessHealthEngine._normalize_trend(prim_var_pct, is_inverted=is_neg_primary)

        components_pool.append({
            "component": "Primary Metric Trend",
            "metric_name": primary_label or str(primary_metric).replace("_", " ").title(),
            "raw_value": round(prim_var_pct, 1),
            "unit": "% change",
            "trend_direction": "improving" if (prim_var_pct >= 0 if not is_neg_primary else prim_var_pct <= 0) else "deteriorating",
            "normalized_score": prim_score,
            "base_weight": 0.40,
        })

        # 4b. Profit Trend (Base Weight: 25%)
        if total_profit is not None:
            if profit_col:
                curr_prof = float(current_slice[profit_col].sum()) if len(current_slice) > 0 else 0.0
                base_prof = float(baseline_slice[profit_col].sum()) if len(baseline_slice) > 0 else 0.0
            elif rev_col and cost_col:
                curr_prof = float(current_slice[rev_col].sum() - current_slice[cost_col].sum()) if len(current_slice) > 0 else 0.0
                base_prof = float(baseline_slice[rev_col].sum() - baseline_slice[cost_col].sum()) if len(baseline_slice) > 0 else 0.0
            else:
                curr_prof, base_prof = 0.0, 0.0
            _, prof_var_pct = TemporalHelper.calculate_variance(curr_prof, base_prof)
            prof_trend_score = BusinessHealthEngine._normalize_trend(prof_var_pct, is_inverted=False)

            components_pool.append({
                "component": "Profit Trend",
                "metric_name": profit_info["label"] or "Net Profit",
                "raw_value": round(prof_var_pct, 1),
                "unit": "% change",
                "trend_direction": "improving" if prof_var_pct >= 0 else "deteriorating",
                "normalized_score": prof_trend_score,
                "base_weight": 0.25,
            })

        # 4c. Profit Margin (Base Weight: 20%)
        if profit_margin is not None:
            margin_score = BusinessHealthEngine._normalize_margin(profit_margin)
            components_pool.append({
                "component": "Profit Margin",
                "metric_name": "Profit Margin",
                "raw_value": round(profit_margin, 1),
                "unit": "%",
                "trend_direction": "healthy" if profit_margin >= 15.0 else ("stable" if profit_margin >= 5.0 else "under pressure"),
                "normalized_score": margin_score,
                "base_weight": 0.20,
            })

        # 4d. Volume Trend (Base Weight: 10%)
        if qty_col and qty_col in df.columns:
            curr_vol = float(current_slice[qty_col].sum()) if len(current_slice) > 0 else 0.0
            base_vol = float(baseline_slice[qty_col].sum()) if len(baseline_slice) > 0 else 0.0
            vol_metric_name = "Transaction Volume"
        else:
            curr_vol = float(len(current_slice))
            base_vol = float(len(baseline_slice))
            vol_metric_name = "Record Activity Count"
        _, vol_var_pct = TemporalHelper.calculate_variance(curr_vol, base_vol)
        vol_score = BusinessHealthEngine._normalize_trend(vol_var_pct, is_inverted=False)

        components_pool.append({
            "component": "Volume Trend",
            "metric_name": vol_metric_name,
            "raw_value": round(vol_var_pct, 1),
            "unit": "% change",
            "trend_direction": "improving" if vol_var_pct >= 0 else "deteriorating",
            "normalized_score": vol_score,
            "base_weight": 0.10,
        })

        # 4e. Discount / Cost Pressure (Base Weight: 5%)
        if avg_discount is not None:
            disc_score = BusinessHealthEngine._normalize_discount(avg_discount)
            components_pool.append({
                "component": "Discount Pressure",
                "metric_name": "Average Discount",
                "raw_value": round(avg_discount, 1),
                "unit": "%",
                "trend_direction": "controlled" if avg_discount <= 15.0 else "elevated",
                "normalized_score": disc_score,
                "base_weight": 0.05,
            })
        elif cost_col and effective_revenue and effective_revenue > 0:
            cost_ratio = round(float(df[cost_col].sum()) / effective_revenue * 100, 1)
            cost_score = round(max(0.0, min(100.0, 100.0 - (cost_ratio - 50.0) * 1.5)), 1)
            components_pool.append({
                "component": "Cost Ratio Pressure",
                "metric_name": "Cost-to-Revenue Ratio",
                "raw_value": cost_ratio,
                "unit": "%",
                "trend_direction": "controlled" if cost_ratio <= 70.0 else "elevated",
                "normalized_score": cost_score,
                "base_weight": 0.05,
            })

        # Dynamic Weight Renormalization
        total_base_weight = sum(c["base_weight"] for c in components_pool)
        health_breakdown = []
        overall_health_score_accum = 0.0

        for comp in components_pool:
            renorm_weight = comp["base_weight"] / total_base_weight
            weight_pct = round(renorm_weight * 100, 1)
            norm_score = comp["normalized_score"]
            weighted_val = norm_score * renorm_weight
            overall_health_score_accum += weighted_val

            if norm_score >= 80.0:
                c_status = "Healthy"
            elif norm_score >= 60.0:
                c_status = "Stable"
            elif norm_score >= 40.0:
                c_status = "Vulnerable"
            else:
                c_status = "Critical"

            health_breakdown.append({
                "component": comp["component"],
                "metric_name": comp["metric_name"],
                "raw_value": comp["raw_value"],
                "unit": comp["unit"],
                "trend_direction": comp["trend_direction"],
                "normalized_score": norm_score,
                "weight_pct": weight_pct,
                "weighted_score": round(weighted_val, 2),
                "status": c_status
            })

        overall_health_score = round(max(0.0, min(100.0, overall_health_score_accum)), 1)

        # Centralized Thresholds
        if overall_health_score >= 80.0:
            overall_status = "Strong"
        elif overall_health_score >= 60.0:
            overall_status = "Stable"
        elif overall_health_score >= 40.0:
            overall_status = "Vulnerable"
        else:
            overall_status = "Distressed"

        # Identify Primary Observed Pressure (lowest scoring component)
        sorted_by_score = sorted(health_breakdown, key=lambda x: x["normalized_score"])
        lowest_comp = sorted_by_score[0] if sorted_by_score else None

        if lowest_comp and lowest_comp["normalized_score"] < 70.0:
            primary_pressure = {
                "component": lowest_comp["component"],
                "metric_name": lowest_comp["metric_name"],
                "score": lowest_comp["normalized_score"],
                "raw_value": lowest_comp["raw_value"],
                "unit": lowest_comp["unit"],
                "impact": "Primary Drag",
                "description": (
                    f"{lowest_comp['component']} ({lowest_comp['metric_name']}) has the lowest score "
                    f"at {lowest_comp['normalized_score']}/100 ({lowest_comp['status']}), "
                    f"exerting the most significant negative pressure on overall business performance."
                )
            }
        else:
            primary_pressure = {
                "component": "None",
                "metric_name": "Balanced Performance",
                "score": 85.0,
                "raw_value": 0.0,
                "unit": "",
                "impact": "Balanced",
                "description": "All monitored analytical dimensions are operating within acceptable or strong parameters."
            }

        # 5. Build KPIs for UI Compatibility
        kpis: List[KpiMetric] = []

        # Primary Metric KPI
        prim_kpi_status = "healthy" if prim_score >= 80 else ("warning" if prim_score >= 60 else "critical")
        prim_kpi_trend = "improving" if (prim_var_pct >= 0 if not is_neg_primary else prim_var_pct <= 0) else "deteriorating"
        kpis.append(KpiMetric(
            name=f"Primary Metric: {primary_label or str(primary_metric).replace('_', ' ').title()}",
            current_value=round(curr_p, 2),
            target_or_baseline=round(base_p, 2),
            variance_pct=round(prim_var_pct, 2),
            unit="$" if any(k in str(primary_metric).lower() for k in ["revenue", "sales", "price", "profit", "amount", "cost"]) else "units",
            trend=prim_kpi_trend,
            status=prim_kpi_status,
            interpretation=f"Shift of {prim_var_pct:+.1f}% compared with earlier observation period. Normalized health contribution: {prim_score}/100."
        ))

        # Revenue KPI (if detected and not primary)
        if rev_col and rev_col != primary_metric:
            curr_r = float(current_slice[rev_col].sum()) if len(current_slice) > 0 else 0.0
            base_r = float(baseline_slice[rev_col].sum()) if len(baseline_slice) > 0 else 0.0
            _, r_var = TemporalHelper.calculate_variance(curr_r, base_r)
            r_status = "healthy" if r_var >= 0 else ("critical" if r_var < -5.0 else "warning")
            kpis.append(KpiMetric(
                name=rev_info["label"] or "Total Revenue",
                current_value=round(curr_r, 2),
                target_or_baseline=round(base_r, 2),
                variance_pct=r_var,
                unit="$",
                trend="improving" if r_var >= 0 else "deteriorating",
                status=r_status,
                interpretation=f"Revenue shifted by {r_var:+.1f}% compared with earlier period."
            ))

        # Profit KPI (if detected)
        if total_profit is not None:
            if profit_col:
                curr_p_val = float(current_slice[profit_col].sum()) if len(current_slice) > 0 else 0.0
                base_p_val = float(baseline_slice[profit_col].sum()) if len(baseline_slice) > 0 else 0.0
            elif rev_col and cost_col:
                curr_p_val = float(current_slice[rev_col].sum() - current_slice[cost_col].sum()) if len(current_slice) > 0 else 0.0
                base_p_val = float(baseline_slice[rev_col].sum() - baseline_slice[cost_col].sum()) if len(baseline_slice) > 0 else 0.0
            else:
                curr_p_val, base_p_val = 0.0, 0.0
            _, p_var = TemporalHelper.calculate_variance(curr_p_val, base_p_val)
            p_status = "healthy" if p_var >= 0 else ("critical" if p_var < -10.0 else "warning")
            kpis.append(KpiMetric(
                name=profit_info["label"] or "Net Profit",
                current_value=round(curr_p_val, 2),
                target_or_baseline=round(base_p_val, 2),
                variance_pct=p_var,
                unit="$",
                trend="improving" if p_var >= 0 else "deteriorating",
                status=p_status,
                interpretation=f"Profit shifted by {p_var:+.1f}% compared with earlier period."
            ))

        # Discount KPI (if detected)
        if avg_discount is not None and disc_col:
            curr_d = float(current_slice[disc_col].mean()) if len(current_slice) > 0 else 0.0
            base_d = float(baseline_slice[disc_col].mean()) if len(baseline_slice) > 0 else 0.0
            curr_d_pct = curr_d * 100 if curr_d <= 1.0 else curr_d
            base_d_pct = base_d * 100 if base_d <= 1.0 else base_d
            d_var = round(curr_d_pct - base_d_pct, 1)
            kpis.append(KpiMetric(
                name="Average Discount",
                current_value=round(curr_d_pct, 1),
                target_or_baseline=round(base_d_pct, 1),
                variance_pct=d_var,
                unit="%",
                trend="deteriorating" if d_var > 1.0 else "stable",
                status="critical" if d_var > 3.0 else ("warning" if d_var > 0.5 else "healthy"),
                interpretation=f"Discounts changed by {d_var:+.1f} percentage points compared with earlier period."
            ))

        # 6. Build Timeline Series (if dates exist)
        timeline_series: List[Dict[str, Any]] = []
        if has_dates and "__parsed_temporal_date" in work_df.columns:
            try:
                metric_for_timeline = primary_metric if (primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric])) else (rev_col or qty_col)
                if metric_for_timeline and metric_for_timeline in work_df.columns:
                    work_df["__period_str"] = work_df["__parsed_temporal_date"].dt.to_period("M").astype(str)
                    grouped = work_df.groupby("__period_str")[metric_for_timeline].agg(["sum", "mean", "count"]).reset_index()
                    for _, row in grouped.tail(12).iterrows():
                        timeline_series.append({
                            "period": str(row["__period_str"]),
                            "metric_sum": round(float(row["sum"]), 2),
                            "metric_mean": round(float(row["mean"]), 2),
                            "count": int(row["count"])
                        })
            except Exception:
                timeline_series = []

        # 7. Synthesize Executive Summary and Vital Signs
        summary_text = (
            f"Overall Business Health is rated at {overall_health_score}/100 ({overall_status}). "
            f"Focal metric '{primary_label or primary_metric}' exhibited a {prim_var_pct:+.1f}% variance "
            f"between earlier and recent periods ({temporal['baseline_label']} vs {temporal['current_label']}). "
            f"{primary_pressure['description']}"
        )

        vital_signs = {
            "total_records_analyzed": len(df),
            "primary_metric": primary_metric,
            "period_variance_pct": round(prim_var_pct, 2),
            "healthy_kpi_count": sum(1 for k in kpis if k.status == "healthy"),
            "warning_kpi_count": sum(1 for k in kpis if k.status == "warning"),
            "critical_kpi_count": sum(1 for k in kpis if k.status == "critical"),
            "data_span_has_temporal_index": has_dates,
            "is_record_order_fallback": temporal["is_record_order"],
            "temporal_methodology_note": temporal["methodological_note"],
            "distinct_customer_identifier_present": cust_id_col is not None,
            "customer_segment_categories_present": cust_seg_col is not None,
            "business_overview_metrics": {
                "total_revenue": total_revenue,
                "total_profit": total_profit,
                "profit_margin_pct": profit_margin,
                "num_transactions": num_transactions,
                "avg_order_value": avg_order_value,
                "num_customers": num_customers,
                "customer_identifier_column": cust_id_col,
                "customer_segment_column": cust_seg_col,
                "growth_rate_pct": growth_rate,
                "avg_discount_pct": avg_discount,
                "estimated_transaction_value": round(estimated_txn_val, 2) if estimated_txn_val is not None else None,
                "detected_columns": {
                    "revenue": rev_col,
                    "cost": cost_col,
                    "profit": profit_col,
                    "customer_id": cust_id_col,
                    "customer_segment": cust_seg_col,
                    "discount": disc_col,
                    "price": price_col,
                    "quantity": qty_col,
                    "date": detected["date"]["column"]
                }
            }
        }

        overview_metrics_dict = {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "profit_margin": profit_margin,
            "profit_margin_pct": profit_margin,
            "transactions_count": num_transactions,
            "num_transactions": num_transactions,
            "average_order_value": avg_order_value,
            "avg_order_value": avg_order_value,
            "unique_customers": num_customers,
            "num_customers": num_customers,
            "customer_identifier_column": cust_id_col,
            "customer_segment_column": cust_seg_col,
            "growth_rate": growth_rate,
            "growth_rate_pct": growth_rate,
            "average_discount_pct": avg_discount,
            "avg_discount": avg_discount,
            "estimated_transaction_value": round(estimated_txn_val, 2) if estimated_txn_val is not None else None,
        }

        methodology_text = (
            "Multi-component Health Index utilizes continuous piecewise trend normalization across "
            "Primary Metric Trend (40%), Profit Trend (25%), Profit Margin (20%), Volume Trend (10%), "
            "and Discount/Cost Pressure (5%). Weights are dynamically renormalized if schema metrics are absent."
        )

        return BusinessHealthOverview(
            overall_health_score=overall_health_score,
            overall_status=overall_status,
            executive_summary=summary_text,
            kpis=kpis,
            vital_signs=vital_signs,
            overview_metrics=overview_metrics_dict,
            timeline_series=timeline_series,
            health_breakdown=health_breakdown,
            primary_pressure=primary_pressure,
            health_methodology=methodology_text
        )
