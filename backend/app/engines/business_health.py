from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.schemas import BusinessHealthOverview, KpiMetric
from app.services.semantic_metrics import SemanticMetricDetector
from app.services.data_ingestion import IngestionService
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

    @classmethod
    def _build_adaptive_kpis(
        cls,
        df: pd.DataFrame,
        detected: Dict[str, Any],
        effective_revenue: Optional[float],
        total_profit: Optional[float],
        profit_margin: Optional[float],
        num_orders: int,
        avg_order_value: Optional[float],
        num_customers: Optional[int],
        avg_items_per_order: Optional[float],
        avg_discount: Optional[float],
        growth_rate: Optional[float],
        primary_metric: Any,
        primary_label: Optional[str],
        has_dates: bool
    ) -> List[Dict[str, Any]]:
        domain = detected.get("domain", "general")
        cards: List[Dict[str, Any]] = []

        if domain == "retail":
            cards.append({
                "id": "total_revenue",
                "label": "Total Revenue",
                "value": effective_revenue,
                "formatted_value": f"${effective_revenue:,.2f}" if effective_revenue is not None else "N/A",
                "unit": "$",
                "note": "Total recognized sales volume"
            })
            cards.append({
                "id": "total_profit",
                "label": "Total Profit",
                "value": total_profit,
                "formatted_value": f"${total_profit:,.2f}" if total_profit is not None else "N/A",
                "unit": "$",
                "subtext": f"{profit_margin:.1f}% net margin" if profit_margin is not None else None,
                "note": "Net commercial return after costs"
            })
            cards.append({
                "id": "distinct_orders",
                "label": "Distinct Orders",
                "value": num_orders,
                "formatted_value": f"{num_orders:,}",
                "unit": "orders",
                "subtext": f"Across {len(df):,} line items" if detected.get("order_id_col") else None,
                "note": "Total unique order transactions"
            })
            cards.append({
                "id": "avg_order_value",
                "label": "Average Order Value",
                "value": avg_order_value,
                "formatted_value": f"${avg_order_value:,.2f}" if avg_order_value is not None else "N/A",
                "unit": "$",
                "note": "Mean revenue per distinct order"
            })
            cards.append({
                "id": "unique_customers",
                "label": "Unique Customers",
                "value": num_customers,
                "formatted_value": f"{num_customers:,}" if num_customers is not None else "N/A",
                "unit": "customers",
                "note": "Distinct customer accounts" if num_customers is not None else "No customer-level identifier detected"
            })
            cards.append({
                "id": "items_per_order",
                "label": "Items per Order",
                "value": avg_items_per_order,
                "formatted_value": f"{avg_items_per_order:.1f}" if avg_items_per_order is not None else "N/A",
                "unit": "items",
                "note": "Average line items per order"
            })
            cards.append({
                "id": "avg_discount",
                "label": "Average Discount (%)",
                "value": avg_discount,
                "formatted_value": f"{avg_discount:.1f}%" if avg_discount is not None else "0.0%",
                "unit": "%",
                "note": "Mean concession rate applied"
            })
            cards.append({
                "id": "growth_rate",
                "label": "Growth Rate (%)",
                "value": growth_rate,
                "formatted_value": f"{growth_rate:+.1f}%" if (growth_rate is not None and has_dates) else "Snapshot",
                "unit": "%" if (growth_rate is not None and has_dates) else "",
                "note": "Period-over-period performance change" if (growth_rate is not None and has_dates) else "Undated observation snapshot"
            })

        elif domain == "workforce":
            wf_cols = detected.get("domain_metrics", {}).get("workforce", {})
            emp_id_col = detected.get("employee_id_col")
            attrition_col = wf_cols.get("attrition")
            income_col = wf_cols.get("income")
            overtime_col = wf_cols.get("overtime")
            tenure_col = wf_cols.get("tenure")
            satisfaction_col = wf_cols.get("satisfaction")
            dept_col = wf_cols.get("department")
            salary_hike_col = wf_cols.get("salary_hike")

            total_emp = int(df[emp_id_col].dropna().nunique()) if (emp_id_col and emp_id_col in df.columns) else len(df)
            cards.append({
                "id": "headcount",
                "label": "Total Workforce",
                "value": total_emp,
                "formatted_value": f"{total_emp:,}",
                "unit": "employees",
                "note": "Total active workforce headcount"
            })

            if attrition_col and attrition_col in df.columns:
                attrited = df[attrition_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "y"])
                attrition_count = int(attrited.sum())
                attrition_rate = round((attrition_count / len(df)) * 100, 1)
                cards.append({
                    "id": "attrition_rate",
                    "label": "Attrition Rate",
                    "value": attrition_rate,
                    "formatted_value": f"{attrition_rate:.1f}%",
                    "unit": "%",
                    "status": "critical" if attrition_rate > 20 else ("warning" if attrition_rate > 12 else "healthy"),
                    "subtext": f"{attrition_count:,} departures of {len(df):,}",
                    "note": "Voluntary workforce separation rate"
                })

            if income_col and income_col in df.columns:
                avg_income = round(float(df[income_col].dropna().mean()), 2)
                cards.append({
                    "id": "avg_income",
                    "label": "Average Monthly Income",
                    "value": avg_income,
                    "formatted_value": f"${avg_income:,.2f}",
                    "unit": "$",
                    "note": "Mean employee monthly compensation"
                })

            if overtime_col and overtime_col in df.columns:
                ot_bool = df[overtime_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "y"])
                ot_rate = round((ot_bool.sum() / len(df)) * 100, 1)
                cards.append({
                    "id": "overtime_rate",
                    "label": "Overtime Participation",
                    "value": ot_rate,
                    "formatted_value": f"{ot_rate:.1f}%",
                    "unit": "%",
                    "status": "warning" if ot_rate > 30 else "healthy",
                    "note": "Employees working overtime hours"
                })

            if tenure_col and tenure_col in df.columns:
                avg_tenure = round(float(df[tenure_col].dropna().mean()), 1)
                cards.append({
                    "id": "avg_tenure",
                    "label": "Average Tenure",
                    "value": avg_tenure,
                    "formatted_value": f"{avg_tenure:.1f} yrs",
                    "unit": "years",
                    "note": "Mean years of service at company"
                })

            if satisfaction_col and satisfaction_col in df.columns:
                avg_sat = round(float(df[satisfaction_col].dropna().mean()), 2)
                max_sat = round(float(df[satisfaction_col].dropna().max()), 0)
                cards.append({
                    "id": "job_satisfaction",
                    "label": "Job Satisfaction",
                    "value": avg_sat,
                    "formatted_value": f"{avg_sat:.2f} / {int(max_sat)}",
                    "unit": "rating",
                    "note": "Mean recorded satisfaction index"
                })

            if dept_col and dept_col in df.columns:
                dept_count = int(df[dept_col].dropna().nunique())
                cards.append({
                    "id": "department_count",
                    "label": "Active Departments",
                    "value": dept_count,
                    "formatted_value": f"{dept_count}",
                    "unit": "departments",
                    "note": "Distinct operational business units"
                })

            if salary_hike_col and salary_hike_col in df.columns:
                avg_hike = round(float(df[salary_hike_col].dropna().mean()), 1)
                cards.append({
                    "id": "salary_hike",
                    "label": "Average Salary Hike",
                    "value": avg_hike,
                    "formatted_value": f"{avg_hike:.1f}%",
                    "unit": "%",
                    "note": "Mean compensation increment percentage"
                })

        elif domain == "manufacturing":
            mfg_cols = detected.get("domain_metrics", {}).get("manufacturing", {})
            batch_id_col = detected.get("batch_id_col")
            batch_size_col = mfg_cols.get("batch_size")
            defect_rate_col = mfg_cols.get("defect_rate")
            scrap_cost_col = mfg_cols.get("scrap_cost")
            cycle_time_col = mfg_cols.get("cycle_time")
            downtime_col = mfg_cols.get("downtime")
            prod_cost_col = mfg_cols.get("production_cost")
            otd_col = mfg_cols.get("on_time_delivery")
            facility_col = mfg_cols.get("facility")

            batch_count = int(df[batch_id_col].dropna().nunique()) if (batch_id_col and batch_id_col in df.columns) else len(df)
            total_produced = int(df[batch_size_col].dropna().sum()) if (batch_size_col and batch_size_col in df.columns) else None
            cards.append({
                "id": "batch_count",
                "label": "Production Batches",
                "value": batch_count,
                "formatted_value": f"{batch_count:,}",
                "unit": "batches",
                "subtext": f"{total_produced:,} units produced" if total_produced else None,
                "note": "Total operational runs tracked"
            })

            if defect_rate_col and defect_rate_col in df.columns:
                avg_defect = round(float(df[defect_rate_col].dropna().mean()), 2)
                cards.append({
                    "id": "defect_rate",
                    "label": "Defect Rate",
                    "value": avg_defect,
                    "formatted_value": f"{avg_defect:.2f}%",
                    "unit": "%",
                    "status": "critical" if avg_defect > 5 else ("warning" if avg_defect > 2.5 else "healthy"),
                    "note": "Mean batch defect percentage"
                })

            if scrap_cost_col and scrap_cost_col in df.columns:
                total_scrap = round(float(df[scrap_cost_col].dropna().sum()), 2)
                cards.append({
                    "id": "scrap_cost",
                    "label": "Scrap & Waste Cost",
                    "value": total_scrap,
                    "formatted_value": f"${total_scrap:,.2f}",
                    "unit": "$",
                    "note": "Financial loss from rejected output"
                })

            if cycle_time_col and cycle_time_col in df.columns:
                avg_cycle = round(float(df[cycle_time_col].dropna().mean()), 1)
                cards.append({
                    "id": "cycle_time",
                    "label": "Mean Cycle Time",
                    "value": avg_cycle,
                    "formatted_value": f"{avg_cycle:.1f} hrs",
                    "unit": "hours",
                    "note": "Average processing duration per run"
                })

            if downtime_col and downtime_col in df.columns:
                total_dt = round(float(df[downtime_col].dropna().sum()), 1)
                cards.append({
                    "id": "downtime",
                    "label": "Total Downtime",
                    "value": total_dt,
                    "formatted_value": f"{total_dt:,.1f} mins",
                    "unit": "minutes",
                    "note": "Aggregate equipment downtime"
                })

            if prod_cost_col and prod_cost_col in df.columns:
                total_pc = round(float(df[prod_cost_col].dropna().sum()), 2)
                cards.append({
                    "id": "production_cost",
                    "label": "Total Production Cost",
                    "value": total_pc,
                    "formatted_value": f"${total_pc:,.2f}",
                    "unit": "$",
                    "note": "Direct manufacturing expenditure"
                })

            if otd_col and otd_col in df.columns:
                otd_bool = df[otd_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "y"])
                otd_rate = round((otd_bool.sum() / len(df)) * 100, 1)
                cards.append({
                    "id": "on_time_delivery",
                    "label": "On-Time Delivery Rate",
                    "value": otd_rate,
                    "formatted_value": f"{otd_rate:.1f}%",
                    "unit": "%",
                    "note": "Percentage of batches delivered on schedule"
                })

            if facility_col and facility_col in df.columns:
                fac_count = int(df[facility_col].dropna().nunique())
                cards.append({
                    "id": "facility_count",
                    "label": "Production Facilities",
                    "value": fac_count,
                    "formatted_value": f"{fac_count}",
                    "unit": "plants",
                    "note": "Active manufacturing sites"
                })

        elif domain == "saas":
            saas_cols = detected.get("domain_metrics", {}).get("saas", {})
            acct_id_col = detected.get("account_id_col")
            arr_col = saas_cols.get("arr")
            churn_col = saas_cols.get("churn")
            active_users_col = saas_cols.get("active_users")
            nps_col = saas_cols.get("nps")
            tickets_col = saas_cols.get("support_tickets")
            adoption_col = saas_cols.get("feature_adoption")
            plan_col = saas_cols.get("plan")

            if arr_col and arr_col in df.columns:
                total_arr = round(float(df[arr_col].dropna().sum()), 2)
                cards.append({
                    "id": "arr",
                    "label": "Annual Recurring Revenue",
                    "value": total_arr,
                    "formatted_value": f"${total_arr:,.2f}",
                    "unit": "$",
                    "note": "Total contracted recurring revenue"
                })

            if churn_col and churn_col in df.columns:
                churn_bool = df[churn_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "y"])
                churn_rate = round((churn_bool.sum() / len(df)) * 100, 1)
                cards.append({
                    "id": "churn_rate",
                    "label": "Account Churn Rate",
                    "value": churn_rate,
                    "formatted_value": f"{churn_rate:.1f}%",
                    "unit": "%",
                    "status": "critical" if churn_rate > 15 else ("warning" if churn_rate > 8 else "healthy"),
                    "note": "Proportion of accounts churned"
                })

            total_accts = int(df[acct_id_col].dropna().nunique()) if (acct_id_col and acct_id_col in df.columns) else len(df)
            cards.append({
                "id": "account_count",
                "label": "Tracked Accounts",
                "value": total_accts,
                "formatted_value": f"{total_accts:,}",
                "unit": "accounts",
                "note": "Total business customer accounts"
            })

            if active_users_col and active_users_col in df.columns:
                total_dau = int(df[active_users_col].dropna().sum())
                avg_dau = round(float(df[active_users_col].dropna().mean()), 1)
                cards.append({
                    "id": "active_users",
                    "label": "Active Users (DAU)",
                    "value": total_dau,
                    "formatted_value": f"{total_dau:,}",
                    "unit": "users",
                    "subtext": f"Avg {avg_dau:.1f} users per account",
                    "note": "Total daily active platform users"
                })

            if nps_col and nps_col in df.columns:
                avg_nps = round(float(df[nps_col].dropna().mean()), 1)
                cards.append({
                    "id": "nps",
                    "label": "Net Promoter Score",
                    "value": avg_nps,
                    "formatted_value": f"{avg_nps:.1f}",
                    "unit": "score",
                    "status": "healthy" if avg_nps > 50 else ("warning" if avg_nps > 20 else "critical"),
                    "note": "Customer loyalty & advocacy index"
                })

            if tickets_col and tickets_col in df.columns:
                total_tickets = int(df[tickets_col].dropna().sum())
                cards.append({
                    "id": "support_tickets",
                    "label": "Support Tickets",
                    "value": total_tickets,
                    "formatted_value": f"{total_tickets:,}",
                    "unit": "tickets",
                    "note": "Customer support requests logged"
                })

            if adoption_col and adoption_col in df.columns:
                avg_adopt = round(float(df[adoption_col].dropna().mean()), 1)
                cards.append({
                    "id": "feature_adoption",
                    "label": "Feature Adoption Rate",
                    "value": avg_adopt,
                    "formatted_value": f"{avg_adopt:.1f}%",
                    "unit": "%",
                    "note": "Mean product capabilities utilization"
                })

            if plan_col and plan_col in df.columns and not df[plan_col].dropna().empty:
                top_plan = str(df[plan_col].value_counts().index[0])
                plan_pct = round((df[plan_col].value_counts().iloc[0] / len(df)) * 100, 0)
                cards.append({
                    "id": "subscription_plan",
                    "label": "Leading Plan",
                    "value": top_plan,
                    "formatted_value": f"{top_plan} ({int(plan_pct)}%)",
                    "unit": "tier",
                    "note": "Dominant customer plan category"
                })

        # General domain or fill gaps to ensure 6-8 cards
        if len(cards) < 6:
            cols = list(df.columns)
            num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
            cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
            total_cells = len(df) * len(cols)
            completeness = round((1.0 - (df.isnull().sum().sum() / total_cells)) * 100, 1) if total_cells > 0 else 100.0

            if not any(c["id"] == "total_records" for c in cards):
                cards.append({
                    "id": "total_records",
                    "label": "Total Records",
                    "value": len(df),
                    "formatted_value": f"{len(df):,}",
                    "unit": "records",
                    "note": "Total observations in dataset"
                })

            if primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric]):
                p_sum = float(df[primary_metric].dropna().sum())
                p_mean = float(df[primary_metric].dropna().mean())
                p_unit = SemanticMetricDetector.infer_column_unit(primary_metric, df[primary_metric])
                p_fmt = f"${p_sum:,.2f}" if p_unit == "$" else (f"{p_sum:.1f}%" if p_unit == "%" else f"{p_sum:,.1f}")
                p_mean_fmt = f"${p_mean:,.2f}" if p_unit == "$" else (f"{p_mean:.1f}%" if p_unit == "%" else f"{p_mean:,.2f}")
                
                cards.append({
                    "id": "primary_metric_total",
                    "label": f"Total {primary_label or primary_metric}",
                    "value": round(p_sum, 2),
                    "formatted_value": p_fmt,
                    "unit": p_unit,
                    "note": "Aggregate volume across observations"
                })
                cards.append({
                    "id": "primary_metric_avg",
                    "label": f"Average {primary_label or primary_metric}",
                    "value": round(p_mean, 2),
                    "formatted_value": p_mean_fmt,
                    "unit": p_unit,
                    "note": "Mean value per observation"
                })

            cards.append({
                "id": "numeric_features",
                "label": "Numeric Features",
                "value": len(num_cols),
                "formatted_value": f"{len(num_cols)}",
                "unit": "columns",
                "note": "Quantitative attributes analyzed"
            })
            cards.append({
                "id": "categorical_features",
                "label": "Categorical Dimensions",
                "value": len(cat_cols),
                "formatted_value": f"{len(cat_cols)}",
                "unit": "columns",
                "note": "Segmentation dimensions analyzed"
            })
            cards.append({
                "id": "data_completeness",
                "label": "Data Completeness",
                "value": completeness,
                "formatted_value": f"{completeness:.1f}%",
                "unit": "%",
                "status": "healthy" if completeness > 95 else "warning",
                "note": "Non-null values ratio across dataset"
            })
            cards.append({
                "id": "observation_timeframe",
                "label": "Observation Timeframe",
                "value": "Dated Series" if has_dates else "Static Snapshot",
                "formatted_value": "Dated Series" if has_dates else "Static Snapshot",
                "unit": "",
                "note": "Temporal analysis readiness"
            })

        return cards[:8]

    @staticmethod
    def assess_health(
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None
    ) -> BusinessHealthOverview:
        """
        Answers Question 1: 'What is happening?'
        Calculates understandable business overview metrics, domain-adaptive KPIs,
        and the multi-component Business Health Index with dynamic weight renormalization.
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

        # Transactions and Distinct Orders
        num_transactions = len(df)
        order_id_col = detected.get("order_id_col")
        if order_id_col and order_id_col in df.columns:
            distinct_orders = int(df[order_id_col].dropna().nunique())
        else:
            distinct_orders = None

        if distinct_orders and distinct_orders > 0:
            num_orders = distinct_orders
            avg_order_value = round(effective_revenue / distinct_orders, 2) if effective_revenue is not None else None
            avg_items_per_order = round(len(df) / distinct_orders, 1)
        else:
            num_orders = num_transactions
            avg_order_value = round(effective_revenue / num_transactions, 2) if (effective_revenue is not None and num_transactions > 0) else None
            avg_items_per_order = None

        # Distinct Customer Count (Strictly entity identifiers, NEVER categorical tiers)
        num_customers = None
        if cust_id_col:
            num_customers = int(df[cust_id_col].dropna().nunique())

        # Average Discount
        avg_discount = None
        if disc_col:
            mean_d = float(df[disc_col].mean())
            avg_discount = round(mean_d * 100, 1) if mean_d <= 1.0 else round(mean_d, 1)

        # Growth Rate (strictly for dated temporal series)
        growth_rate = None
        if has_dates and effective_revenue is not None and len(baseline_slice) > 0 and len(current_slice) > 0:
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
        health_breakdown: List[Dict[str, Any]] = []
        is_neg_primary = any(k in str(primary_metric).lower() for k in ["churn", "cost", "loss", "delay", "defect", "return", "error"])

        if has_dates:
            components_pool = []

            # 4a. Primary Metric Trend (Base Weight: 40%)
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
            if overall_health_score >= 80.0:
                overall_status = "Strong"
            elif overall_health_score >= 60.0:
                overall_status = "Stable"
            elif overall_health_score >= 40.0:
                overall_status = "Vulnerable"
            else:
                overall_status = "Distressed"

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

            summary_text = (
                f"Overall Business Health is rated at {overall_health_score}/100 ({overall_status}). "
                f"Focal metric '{primary_label or primary_metric}' exhibited a {prim_var_pct:+.1f}% variance "
                f"between earlier and recent periods ({temporal['baseline_label']} vs {temporal['current_label']}). "
                f"{primary_pressure['description']}"
            )
            has_health_score = True
            health_score_explanation = None
            methodology_text = (
                "Multi-component Health Index utilizes continuous piecewise trend normalization across "
                "Primary Metric Trend (40%), Profit Trend (25%), Profit Margin (20%), Volume Trend (10%), "
                "and Discount/Cost Pressure (5%). Weights are dynamically renormalized if schema metrics are absent."
            )
        else:
            # Undated Cross-Sectional Data
            curr_p = float(df[primary_metric].sum()) if (primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric])) else float(len(df))
            base_p = curr_p
            prim_var_pct = 0.0
            prim_score = 0.0
            overall_health_score = 0.0
            overall_status = "Unavailable"
            has_health_score = False
            health_score_explanation = (
                "Health score unavailable for this dataset: requires chronological time series "
                "and target performance baselines to compute a composite index."
            )
            health_breakdown = []
            primary_pressure = {
                "component": "Cross-Sectional Baseline",
                "metric_name": "Operational Metrics",
                "score": 85.0,
                "raw_value": 0.0,
                "unit": "",
                "impact": "Balanced",
                "description": (
                    "Cross-sectional operational metrics are operating within balanced parameters across the observed records."
                )
            }
            summary_text = (
                f"Business Overview for {detected['domain_label']} dataset containing {len(df):,} {detected['entity_label'].lower()}. "
                f"Cross-sectional operational performance metrics and empirical indicators summarized below."
            )
            methodology_text = (
                "Health scoring requires chronological time series to evaluate dynamic performance trajectories. "
                "Cross-sectional datasets are evaluated via domain KPIs and distribution analysis."
            )

        # 5. Build KPIs for UI Compatibility
        kpis: List[KpiMetric] = []
        prim_unit = SemanticMetricDetector.infer_column_unit(primary_metric, df[primary_metric] if primary_metric in df.columns else None)

        if has_dates:
            prim_kpi_status = "healthy" if prim_score >= 80 else ("warning" if prim_score >= 60 else "critical")
            prim_kpi_trend = "improving" if (prim_var_pct >= 0 if not is_neg_primary else prim_var_pct <= 0) else "deteriorating"
            kpis.append(KpiMetric(
                name=f"Primary Metric: {primary_label or str(primary_metric).replace('_', ' ').title()}",
                current_value=round(curr_p, 2),
                target_or_baseline=round(base_p, 2),
                variance_pct=round(prim_var_pct, 2),
                unit=prim_unit,
                trend=prim_kpi_trend,
                status=prim_kpi_status,
                interpretation=f"Shift of {prim_var_pct:+.1f}% compared with earlier observation period. Normalized health contribution: {prim_score}/100."
            ))

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
        else:
            kpis.append(KpiMetric(
                name=f"Primary Metric: {primary_label or str(primary_metric).replace('_', ' ').title()}",
                current_value=round(curr_p, 2),
                target_or_baseline=None,
                variance_pct=None,
                unit=prim_unit,
                trend="stable",
                status="healthy",
                interpretation=f"Snapshot aggregate across {len(df):,} {detected['entity_label'].lower()}."
            ))
            if effective_revenue is not None:
                kpis.append(KpiMetric(
                    name=rev_info["label"] or "Total Revenue",
                    current_value=round(effective_revenue, 2),
                    target_or_baseline=None,
                    variance_pct=None,
                    unit="$",
                    trend="stable",
                    status="healthy",
                    interpretation=f"Total recognized revenue of ${effective_revenue:,.2f}."
                ))

        # 6. Adaptive KPI Cards (Domain-Specific)
        adaptive_kpis = BusinessHealthEngine._build_adaptive_kpis(
            df=df,
            detected=detected,
            effective_revenue=effective_revenue,
            total_profit=total_profit,
            profit_margin=profit_margin,
            num_orders=num_orders,
            avg_order_value=avg_order_value,
            num_customers=num_customers,
            avg_items_per_order=avg_items_per_order,
            avg_discount=avg_discount,
            growth_rate=growth_rate,
            primary_metric=primary_metric,
            primary_label=primary_label,
            has_dates=has_dates
        )

        if not has_dates and adaptive_kpis:
            warning_kpis = [k for k in adaptive_kpis if k.get("status") in ["critical", "warning"]]
            if warning_kpis:
                wk = warning_kpis[0]
                primary_pressure = {
                    "component": wk["label"],
                    "metric_name": wk["label"],
                    "score": 40.0 if wk["status"] == "critical" else 65.0,
                    "raw_value": wk["value"],
                    "unit": wk.get("unit", ""),
                    "impact": "Primary Drag",
                    "description": f"{wk['label']} ({wk.get('formatted_value', '')}) represents the primary observed operational area requiring managerial focus."
                }

        # 7. Build Timeline Series & Metadata
        timeline_series: List[Dict[str, Any]] = []
        if has_dates and "__parsed_temporal_date" in work_df.columns:
            try:
                metric_for_timeline = primary_metric if (primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric])) else (rev_col or qty_col)
                if metric_for_timeline and metric_for_timeline in work_df.columns:
                    metric_unit = SemanticMetricDetector.infer_column_unit(metric_for_timeline, df[metric_for_timeline])
                    is_rate_or_mean = (
                        metric_unit == "%" or
                        any(k in str(metric_for_timeline).lower() for k in ["rate", "pct", "percent", "margin", "ratio", "score", "satisfaction", "avg", "average", "index", "cycle_time", "lead_time"])
                    )
                    aggregation_type = "mean" if is_rate_or_mean else "sum"
                    timeline_metadata = {
                        "is_undated": False,
                        "aggregation_type": aggregation_type,
                        "metric_name": primary_label or str(metric_for_timeline).replace("_", " ").title(),
                        "unit": metric_unit
                    }

                    work_df["__period_str"] = work_df["__parsed_temporal_date"].dt.to_period("M").astype(str)
                    grouped = work_df.groupby("__period_str")[metric_for_timeline].agg(["sum", "mean", "count"]).reset_index()
                    for _, row in grouped.tail(12).iterrows():
                        timeline_series.append({
                            "period": str(row["__period_str"]),
                            "metric_sum": round(float(row["sum"]), 2),
                            "metric_mean": round(float(row["mean"]), 2),
                            "count": int(row["count"])
                        })
                else:
                    timeline_metadata = {"is_undated": True, "message": "Timeline unavailable."}
            except Exception:
                timeline_series = []
                timeline_metadata = {"is_undated": True, "message": "Timeline calculation error."}
        else:
            alternative_chart = None
            cand_cats = [
                c for c in df.columns
                if not pd.api.types.is_numeric_dtype(df[c]) and 2 <= df[c].nunique() <= 30
                and not IngestionService.is_identifier_column(c, df[c])
            ]
            if cand_cats and primary_metric and primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric]):
                cat_col = cand_cats[0]
                grouped = df.groupby(cat_col)[primary_metric].agg(["mean", "count"]).reset_index()
                grouped = grouped.sort_values(by="mean", ascending=False).head(10)
                unit_str = SemanticMetricDetector.infer_column_unit(primary_metric, df[primary_metric])
                p_label = primary_label or str(primary_metric).replace("_", " ").title()
                c_label = str(cat_col).replace("_", " ").title()
                alternative_chart = {
                    "chart_type": "category_comparison",
                    "title": f"Average {p_label} by {c_label}",
                    "description": f"Cross-sectional comparison of average {p_label} across {c_label} categories.",
                    "category_field": c_label,
                    "metric_name": p_label,
                    "unit": unit_str,
                    "data": [
                        {"category": str(r[cat_col]), "value": round(float(r["mean"]), 2), "count": int(r["count"])}
                        for _, r in grouped.iterrows()
                    ]
                }
            elif primary_metric and primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[primary_metric]):
                clean_s = df[primary_metric].dropna()
                if len(clean_s) >= 4 and clean_s.nunique() > 1:
                    cuts = pd.cut(clean_s, bins=min(6, clean_s.nunique()), precision=1)
                    counts = cuts.value_counts(sort=False)
                    p_label = primary_label or str(primary_metric).replace("_", " ").title()
                    alternative_chart = {
                        "chart_type": "distribution",
                        "title": f"{p_label} Numerical Distribution",
                        "description": f"Frequency distribution of {p_label} across dataset observations.",
                        "category_field": "Interval",
                        "metric_name": "Records",
                        "unit": "records",
                        "data": [
                            {"category": str(interval), "value": int(cnt)}
                            for interval, cnt in counts.items()
                        ]
                    }

            timeline_metadata = {
                "is_undated": True,
                "has_dates": False,
                "aggregation_type": "sum",
                "metric_name": primary_label or "Metric",
                "unit": prim_unit,
                "message": "Chronological timeline unavailable: this dataset does not contain temporal dates.",
                "alternative_chart": alternative_chart
            }

        # 8. Vital Signs and Overview Metrics Dictionaries
        vital_signs = {
            "total_records_analyzed": len(df),
            "primary_metric": primary_metric,
            "period_variance_pct": round(prim_var_pct, 2) if has_dates else None,
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
                "distinct_orders": distinct_orders,
                "num_orders": num_orders,
                "avg_order_value": avg_order_value,
                "avg_items_per_order": avg_items_per_order,
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
                    "order_id": order_id_col,
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
            "distinct_orders": distinct_orders,
            "num_orders": num_orders,
            "average_order_value": avg_order_value,
            "avg_order_value": avg_order_value,
            "items_per_order": avg_items_per_order,
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

        return BusinessHealthOverview(
            overall_health_score=overall_health_score,
            overall_status=overall_status,
            executive_summary=summary_text,
            kpis=kpis,
            vital_signs=vital_signs,
            overview_metrics=overview_metrics_dict,
            timeline_series=timeline_series,
            timeline_metadata=timeline_metadata,
            health_breakdown=health_breakdown,
            primary_pressure=primary_pressure,
            health_methodology=methodology_text,
            domain=detected.get("domain", "general"),
            domain_label=detected.get("domain_label", "General Analytics"),
            entity_label=detected.get("entity_label", "Records"),
            is_undated_snapshot=not has_dates,
            has_health_score=has_health_score,
            health_score_explanation=health_score_explanation,
            adaptive_kpis=adaptive_kpis
        )
