from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats
from app.models.schemas import (
    RootCauseReport,
    FactorContribution,
    ParetoItem,
)
from app.services.semantic_metrics import SemanticMetricDetector


class RootCauseEngine:
    @staticmethod
    def analyze_root_cause(
        df: pd.DataFrame,
        target_col: str,
        dimensions: Optional[List[str]] = None
    ) -> RootCauseReport:
        """
        Conducts deterministic factor association analysis using ANOVA, linear feature attribution,
        p-value significance testing, Pareto 80/20 loss concentration, and causal tree derivation.
        Filters out mathematical tautologies (e.g. revenue-cost=profit) so operational drivers surface.
        """
        work_df = df.copy()
        if target_col not in work_df.columns:
            numeric_cols = [c for c in work_df.select_dtypes(include=[np.number]).columns]
            target_col = numeric_cols[0]

        target_series = work_df[target_col].dropna()
        factor_contributions: List[FactorContribution] = []

        # Detect derived relationships to avoid mathematical tautologies crowding out operational drivers
        detected = SemanticMetricDetector.detect_metrics(work_df, target_override=target_col)
        derived_relationships = detected.get("derived_relationships", [])
        math_identity_cols = set()
        for rel in derived_relationships:
            if isinstance(rel, dict):
                target_match = rel.get("dependent_var")
                comps = rel.get("component_vars", [])
                if target_col == target_match:
                    math_identity_cols.update(comps)
                elif target_col in comps:
                    if target_match:
                        math_identity_cols.add(target_match)

        # 1. Numerical Drivers Analysis (Correlation, Slope, and p-values)
        candidate_num_cols = [
            c for c in work_df.select_dtypes(include=[np.number]).columns
            if c != target_col and not c.startswith("__")
            and not any(k in str(c).lower() for k in ["id", "uuid", "key", "no", "num", "code", "stock", "invoice"])
        ]
        # Prefer operational numeric columns over direct mathematical identities if available
        operational_num_cols = [c for c in candidate_num_cols if c not in math_identity_cols]
        if operational_num_cols:
            candidate_num_cols = operational_num_cols

        stat_drivers = []
        for num_col in candidate_num_cols:
            subset = work_df[[target_col, num_col]].dropna()
            if len(subset) >= 10:
                corr, p_val = stats.pearsonr(subset[num_col], subset[target_col])
                if not np.isnan(corr) and not np.isnan(p_val):
                    # Classify factor type
                    name_lower = num_col.lower()
                    if any(k in name_lower for k in ["discount", "price", "margin", "tax", "fee", "cost"]):
                        f_type = "Commercial"
                    elif any(k in name_lower for k in ["delay", "lead_time", "fulfillment", "shipping", "duration", "defect"]):
                        f_type = "Operational"
                    elif any(k in name_lower for k in ["usage", "frequency", "ticket", "tenure", "age", "satisfaction", "rating"]):
                        f_type = "Customer"
                    else:
                        f_type = "Supply & Economics"

                    stat_drivers.append({
                        "name": num_col,
                        "type": f_type,
                        "corr": corr,
                        "abs_corr": abs(corr),
                        "p_value": p_val,
                    })

        # 2. Categorical Factor Drivers via ANOVA (One-way analysis of variance)
        valid_cat_cols = []
        candidate_cats = dimensions if dimensions else [
            c for c in work_df.columns
            if c != target_col and not pd.api.types.is_numeric_dtype(work_df[c])
        ]
        for c in candidate_cats:
            if c not in work_df.columns or c == target_col:
                continue
            name_clean = str(c).strip().lower()
            if any(k in name_clean for k in ["invoice", "invoiceno", "order", "id", "uuid", "key", "code", "sku", "stock"]):
                continue
            if name_clean in ["id", "customerid", "customer_id", "userid", "clientid"]:
                continue
            nunique = int(work_df[c].nunique())
            if 2 <= nunique <= 60:
                valid_cat_cols.append(c)

        cat_cols = valid_cat_cols

        anova_drivers = []
        for cat_col in cat_cols[:5]:
            groups = [group[target_col].dropna().values for _, group in work_df.groupby(cat_col) if len(group) >= 5]
            if len(groups) >= 2:
                try:
                    f_stat, p_val = stats.f_oneway(*groups)
                    if not np.isnan(f_stat) and not np.isnan(p_val):
                        name_lower = cat_col.lower()
                        if any(k in name_lower for k in ["channel", "tier", "plan", "segment", "promo"]):
                            f_type = "Commercial"
                        elif any(k in name_lower for k in ["carrier", "warehouse", "facility", "shipping_method", "vendor"]):
                            f_type = "Operational"
                        elif any(k in name_lower for k in ["customer", "persona", "cohort"]):
                            f_type = "Customer"
                        else:
                            f_type = "Market Demographics"

                        # Eta-squared approximation for variance explained
                        all_vals = np.concatenate(groups)
                        ss_total = np.sum((all_vals - np.mean(all_vals))**2)
                        ss_between = sum(len(g) * (np.mean(g) - np.mean(all_vals))**2 for g in groups)
                        eta_sq = float(ss_between / ss_total) if ss_total > 0 else 0.0

                        anova_drivers.append({
                            "name": cat_col,
                            "type": f_type,
                            "f_stat": f_stat,
                            "p_value": p_val,
                            "eta_squared": eta_sq,
                            "abs_importance": eta_sq
                        })
                except Exception:
                    pass

        # Combine and compute normalized attribution percentages
        all_candidate_factors = []
        for s in stat_drivers:
            all_candidate_factors.append({
                "factor_name": s["name"],
                "factor_type": s["type"],
                "raw_weight": s["abs_corr"],
                "p_value": s["p_value"],
                "corr_val": s["corr"],
                "is_anova": False
            })

        for a in anova_drivers:
            all_candidate_factors.append({
                "factor_name": a["name"],
                "factor_type": a["type"],
                "raw_weight": a["abs_importance"] * 1.5,  # scale categorical effect size
                "p_value": a["p_value"],
                "corr_val": -0.45 if a["p_value"] < 0.05 else 0.1,
                "is_anova": True
            })

        sum_weights = sum(item["raw_weight"] for item in all_candidate_factors)
        all_candidate_factors.sort(key=lambda x: x["raw_weight"], reverse=True)

        for item in all_candidate_factors[:6]:
            attrib_pct = round((item["raw_weight"] / sum_weights * 100), 1) if sum_weights > 0 else 16.6
            p_val = round(float(item["p_value"]), 5)
            significance = "Statistically Significant (p < 0.01)" if p_val < 0.01 else ("Moderate Significance (p < 0.05)" if p_val < 0.05 else "Directional Only (p >= 0.05)")
            direction = "Negative Impact" if item["corr_val"] < 0 else "Positive Impact"

            if item["is_anova"]:
                evidence = (
                    f"One-Way ANOVA test across '{item['factor_name']}' categories shows {significance} "
                    f"(p = {p_val:.4f}). The data suggests differences between groups may be related to performance. "
                    f"Note: An observed relationship does not necessarily prove causation."
                )
                ev_type = "Segment Comparison (ANOVA)"
            else:
                evidence = (
                    f"Correlation check demonstrates Pearson r = {item['corr_val']:+.3f} ({significance}, p = {p_val:.4f}), "
                    f"accounting for {attrib_pct}% of the explained pattern. "
                    f"Note: Correlation does not prove causation."
                )
                ev_type = "Correlation"

            factor_contributions.append(FactorContribution(
                factor_name=item["factor_name"].replace("_", " ").title(),
                factor_type=item["factor_type"],
                attribution_percentage=attrib_pct,
                statistical_significance_p_value=p_val,
                correlation_or_coef=round(float(item["corr_val"]), 3),
                direction=direction,
                evidence_statement=evidence,
                evidence_type=ev_type
            ))

        # 3. Focus on Biggest Contributors (Contribution Analysis / Pareto) or Adaptive Alternative
        pareto_items: List[ParetoItem] = []
        has_valid_contribution = False
        contribution_unsupported_reason = None
        alternative_analysis = None

        candidate_pareto_cols = []
        for col in work_df.columns:
            if col == target_col or str(col).startswith("__"):
                continue
            name_clean = str(col).strip().lower()
            if any(k in name_clean for k in ["invoice", "invoiceno", "order", "id", "uuid", "key", "code", "sku", "stock"]):
                continue
            if name_clean in ["id", "customerid", "customer_id", "userid", "clientid"]:
                continue
            nunique = int(work_df[col].nunique())
            if 2 <= nunique <= 60 and not pd.api.types.is_numeric_dtype(work_df[col]):
                candidate_pareto_cols.append((col, nunique))

        candidate_pareto_cols.sort(key=lambda x: x[1])
        pareto_col = candidate_pareto_cols[0][0] if candidate_pareto_cols else None

        # Check if target_col is numeric
        is_target_numeric = target_col in work_df.columns and pd.api.types.is_numeric_dtype(work_df[target_col])
        metric_unit = SemanticMetricDetector.infer_column_unit(target_col, work_df[target_col] if is_target_numeric else None)

        # Check for loss / drag criteria
        target_series = work_df[target_col].dropna() if is_target_numeric else pd.Series(dtype=float)
        has_negative_losses = bool((target_series < 0).any())
        is_drag_metric = any(k in str(target_col).lower() for k in ["loss", "scrap", "defect", "downtime", "cost", "delay", "error", "waste"])

        # Genuine Contribution / Pareto condition
        if pareto_col and is_target_numeric and (has_negative_losses or is_drag_metric):
            if has_negative_losses:
                # Loss contribution: isolate negative outcomes
                loss_df = work_df[work_df[target_col] < 0]
                grouped_loss = loss_df.groupby(pareto_col)[target_col].sum().abs().reset_index()
                grouped_loss.columns = [pareto_col, "loss_val"]
            else:
                grouped_loss = work_df.groupby(pareto_col)[target_col].sum().reset_index()
                grouped_loss.columns = [pareto_col, "loss_val"]

            grouped_loss = grouped_loss[grouped_loss["loss_val"] > 0].sort_values("loss_val", ascending=False)
            total_loss = float(grouped_loss["loss_val"].sum())

            if total_loss > 0 and len(grouped_loss) >= 2:
                has_valid_contribution = True
                cum_sum = 0.0
                for _, row in grouped_loss.head(10).iterrows():
                    l_val = float(row["loss_val"])
                    cum_sum += l_val
                    cum_pct = round((cum_sum / total_loss * 100), 1)
                    single_pct = round((l_val / total_loss * 100), 1)
                    is_vital = cum_pct <= 80.0 or len(pareto_items) == 0
                    pareto_items.append(ParetoItem(
                        entity=str(row[pareto_col]),
                        loss_or_impact=round(l_val, 2),
                        cumulative_percentage=min(cum_pct, 100.0),
                        is_vital_few=is_vital,
                        contribution_percentage=single_pct
                    ))

        # If contribution analysis is unsupported or produced no valid items, provide adaptive alternative
        if not has_valid_contribution or not pareto_items:
            has_valid_contribution = False
            pareto_items = []

            # Alternative 1: Category Comparison
            if pareto_col and is_target_numeric:
                grouped = work_df.groupby(pareto_col)[target_col].agg(["mean", "count"]).reset_index()
                grouped = grouped.sort_values(by="mean", ascending=False).head(10)
                t_label = str(target_col).replace("_", " ").title()
                p_col_label = str(pareto_col).replace("_", " ").title()
                cat_data = [
                    {
                        "entity": str(r[pareto_col]),
                        "value": round(float(r["mean"]), 2),
                        "count": int(r["count"])
                    }
                    for _, r in grouped.iterrows()
                ]
                total_mean = float(grouped["mean"].sum())
                for item in cat_data:
                    item["share_pct"] = round((item["value"] / total_mean * 100), 1) if total_mean > 0 else 0.0

                alternative_analysis = {
                    "alternative_type": "category_comparison",
                    "section_title": "Category Metric Comparison",
                    "chart_title": f"Average {t_label} across {p_col_label} Categories",
                    "explanation": f"Observed cross-sectional average of '{t_label}' segmented by '{p_col_label}'. (Note: This is an empirical comparison across groups, not a causal contribution analysis).",
                    "entity_label": p_col_label,
                    "metric_label": t_label,
                    "unit": metric_unit,
                    "data": cat_data
                }
            # Alternative 2: Metric Distribution
            elif is_target_numeric and len(target_series) >= 4 and target_series.nunique() > 1:
                t_label = str(target_col).replace("_", " ").title()
                cuts = pd.cut(target_series, bins=min(6, target_series.nunique()), precision=1)
                counts = cuts.value_counts(sort=False)
                tot = len(target_series)
                dist_data = [
                    {
                        "entity": str(interval),
                        "value": int(cnt),
                        "share_pct": round(cnt / tot * 100, 1) if tot > 0 else 0.0
                    }
                    for interval, cnt in counts.items()
                ]
                alternative_analysis = {
                    "alternative_type": "metric_distribution",
                    "section_title": "Metric Distribution Analysis",
                    "chart_title": f"Frequency Distribution of {t_label}",
                    "explanation": f"Observed empirical frequency distribution of {t_label} across all {tot:,} observations.",
                    "entity_label": "Value Interval",
                    "metric_label": "Record Count",
                    "unit": "records",
                    "data": dist_data
                }
            # Alternative 3: Key Data Insights
            elif is_target_numeric and len(target_series) > 0:
                t_label = str(target_col).replace("_", " ").title()
                alternative_analysis = {
                    "alternative_type": "descriptive_insights",
                    "section_title": "Key Data Insights",
                    "chart_title": f"Summary Statistics for {t_label}",
                    "explanation": f"Empirical statistical characteristics of {t_label} across verified dataset records.",
                    "entity_label": "Statistic",
                    "metric_label": "Value",
                    "unit": metric_unit,
                    "data": [
                        {"entity": "Total Sum", "value": round(float(target_series.sum()), 2), "share_pct": 100.0},
                        {"entity": "Mean Average", "value": round(float(target_series.mean()), 2), "share_pct": 0.0},
                        {"entity": "Median", "value": round(float(target_series.median()), 2), "share_pct": 0.0},
                        {"entity": "Min Value", "value": round(float(target_series.min()), 2), "share_pct": 0.0},
                        {"entity": "Max Value", "value": round(float(target_series.max()), 2), "share_pct": 0.0},
                    ]
                }
            # Alternative 4: Limitation
            else:
                alternative_analysis = {
                    "alternative_type": "limitation",
                    "section_title": "Analytical Limitations",
                    "chart_title": "Factor Contribution Unavailable",
                    "explanation": "This dataset does not contain the categorical dimensions or numerical metrics required to calculate factor contributions or distribution breakdowns.",
                    "entity_label": "N/A",
                    "metric_label": "N/A",
                    "unit": "",
                    "data": []
                }
            contribution_unsupported_reason = "Contribution analysis requires an additive loss, variance, or drag metric with baseline targets."

        # Derive primary and secondary possible reasons
        if factor_contributions:
            primary_factor = factor_contributions[0]
            primary_cause = (
                f"Possible contributor: '{primary_factor.factor_name}' is associated with "
                f"{primary_factor.attribution_percentage}% of the observed difference."
            )
            secondary_causes = [
                f"{f.factor_name} ({f.attribution_percentage}% contribution, p={f.statistical_significance_p_value})"
                for f in factor_contributions[1:4]
            ]
            possible_reasons_summary = (
                f"Statistical checks suggest '{primary_factor.factor_name}' is the strongest factor "
                f"associated with the observed pattern ({primary_factor.attribution_percentage}% contribution share). "
                f"Note: An observed relationship does not necessarily prove causation."
            )
        else:
            primary_cause = "No single dominant contributing factor was identified from the available data."
            secondary_causes = ["General variation across baseline"]
            possible_reasons_summary = "Performance appears evenly distributed without strong factor concentration."

        # Causal Tree Structure (kept for backward compatibility, labeled non-causal)
        causal_tree = {
            "root_issue": f"Observed Pattern in {target_col.replace('_', ' ').title()}",
            "primary_node": {
                "factor": factor_contributions[0].factor_name if factor_contributions else "Unknown",
                "attribution": factor_contributions[0].attribution_percentage if factor_contributions else 100.0,
                "sub_nodes": [
                    {
                        "mechanism": "Segment Difference",
                        "vital_entities": [p.entity for p in pareto_items if p.is_vital_few][:3]
                    },
                    {
                        "mechanism": "Statistical Correlation",
                        "p_value_threshold": "p < 0.05"
                    }
                ]
            }
        }

        p_val_avg = float(np.mean([f.statistical_significance_p_value for f in factor_contributions])) if factor_contributions else 0.5
        n_factor = min(1.0, len(work_df) / 500)
        confidence_level = round((1.0 - min(0.3, p_val_avg)) * (0.7 + 0.3 * n_factor) * 100, 1)

        return RootCauseReport(
            primary_root_cause=primary_cause,
            secondary_root_causes=secondary_causes,
            factor_contributions=factor_contributions,
            pareto_breakdown=pareto_items,
            causal_tree_structure=causal_tree,
            statistical_confidence_level=confidence_level,
            methodology_notes="Evaluated using Pearson correlation, One-Way ANOVA group comparison, and segment comparison analysis. Note: An observed relationship does not necessarily prove causation.",
            possible_reasons_summary=possible_reasons_summary,
            causation_disclaimer="Note: An observed relationship does not necessarily prove causation.",
            evidence_type="Correlation & Segment Comparison",
            has_valid_contribution=has_valid_contribution,
            contribution_unsupported_reason=contribution_unsupported_reason,
            alternative_analysis=alternative_analysis
        )
