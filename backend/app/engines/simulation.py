from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.models.schemas import (
    SimulationRequest,
    SimulationOutcome,
    ScenarioComparisonItem,
    ScenarioComparisonReport,
)
from app.services.semantic_metrics import SemanticMetricDetector


class SimulationEngine:
    @staticmethod
    def run_simulation(
        df: pd.DataFrame,
        target_col: str,
        params: SimulationRequest
    ) -> SimulationOutcome:
        """
        Runs deterministic what-if scenario simulations with price change,
        discount recovery, customer retention, and operational cost efficiency levers.
        All levers dynamically affect simulated revenue, profit, margin, and sensitivity.
        """
        total_records = len(df)
        if total_records == 0:
            raise ValueError("Cannot simulate on an empty dataset.")

        # Unified semantic detection
        detected = SemanticMetricDetector.detect_metrics(df, target_override=target_col)
        rev_info = detected["revenue"]
        profit_info = detected["profit"]
        cost_info = detected["cost"]
        disc_info = detected["discount"]
        churn_info = detected["churn"]
        qty_info = detected["quantity"]
        price_info = detected["price"]

        rev_col = rev_info["column"]
        profit_col = profit_info["column"]
        cost_col = cost_info["column"]
        disc_col = disc_info["column"]
        churn_col = churn_info["column"]
        qty_col = qty_info["column"]
        price_col = price_info["column"]

        has_profit = bool(profit_col or (rev_col and cost_col))
        has_discount = bool(disc_col)
        has_cost = bool(cost_col)
        has_churn = bool(churn_col)

        # Baseline Revenue Anchor
        if rev_col and rev_col in df.columns:
            baseline_revenue = float(df[rev_col].sum())
        elif qty_col and price_col and qty_col in df.columns and price_col in df.columns:
            baseline_revenue = float((df[qty_col] * df[price_col]).sum())
        elif target_col in df.columns and pd.api.types.is_numeric_dtype(df[target_col]):
            baseline_revenue = float(df[target_col].sum())
        else:
            baseline_revenue = 100000.0

        # Baseline Profit Anchor
        if profit_col:
            baseline_profit = float(df[profit_col].sum())
        elif rev_col and cost_col:
            baseline_profit = float(df[rev_col].sum() - df[cost_col].sum())
        else:
            baseline_profit = 0.0

        # Baseline Cost Anchor
        if cost_col:
            baseline_costs = float(df[cost_col].sum())
        elif has_profit and baseline_revenue > baseline_profit:
            baseline_costs = float(baseline_revenue - baseline_profit)
        else:
            baseline_costs = 0.0

        # Levers as fractional multipliers
        # Input validation
        if np.isnan(params.price_change_pct) or np.isinf(params.price_change_pct):
            raise ValueError("Price change percentage must be a valid finite number.")
        if params.price_change_pct < -100.0:
            raise ValueError("Price change percentage cannot be less than -100% (prices cannot be negative).")

        volume_pct = getattr(params, "volume_change_pct", 0.0)
        if np.isnan(volume_pct) or np.isinf(volume_pct):
            raise ValueError("Sales volume change percentage must be a valid finite number.")
        if volume_pct < -100.0:
            raise ValueError("Sales volume change percentage cannot be less than -100% (sales volume cannot be negative).")

        if np.isnan(params.operational_efficiency_pct) or np.isinf(params.operational_efficiency_pct):
            raise ValueError("Operating cost reduction percentage must be a valid finite number.")
        if params.operational_efficiency_pct < 0.0 or params.operational_efficiency_pct > 100.0:
            raise ValueError("Operating cost reduction percentage must be between 0% and 100%.")

        if np.isnan(params.discount_adjustment_pct) or np.isinf(params.discount_adjustment_pct):
            raise ValueError("Discount change percentage must be a valid finite number.")
        if params.discount_adjustment_pct < -100.0 or params.discount_adjustment_pct > 100.0:
            raise ValueError("Discount change percentage must be between -100% and 100%.")

        p_change = params.price_change_pct / 100.0
        v_change = volume_pct / 100.0
        d_adjust = params.discount_adjustment_pct / 100.0
        churn_mit = params.churn_mitigation_pct / 100.0
        ops_eff = params.operational_efficiency_pct / 100.0

        is_all_zero = (
            params.price_change_pct == 0.0
            and volume_pct == 0.0
            and params.discount_adjustment_pct == 0.0
            and params.churn_mitigation_pct == 0.0
            and params.operational_efficiency_pct == 0.0
        )

        simulation_insights: List[str] = []

        # Effective baseline discount rate for discount recapture calculation
        effective_disc_rate = 0.10
        if has_discount and disc_col:
            raw_mean_disc = float(df[disc_col].mean())
            if 0.01 <= raw_mean_disc <= 0.80:
                effective_disc_rate = raw_mean_disc
            elif raw_mean_disc > 1.0:
                effective_disc_rate = min(0.50, raw_mean_disc / 100.0)

        # Supported interventions list for this dataset
        supported_interventions = ["Price Change", "Sales Volume Change"]
        if has_cost and baseline_costs > 0:
            supported_interventions.append("Operating Cost Reduction")
        if has_discount and disc_col and effective_disc_rate > 0:
            supported_interventions.append("Discount Change")

        if is_all_zero:
            simulation_insights.append("Baseline scenario active. No lever adjustments applied.")
            simulated_revenue = baseline_revenue
            simulated_profit = baseline_profit
            rev_delta = 0.0
            rev_delta_pct = 0.0
            profit_delta = 0.0
            profit_delta_pct = 0.0
            net_economic_value = 0.0
            risk_adjusted_return = 0.0
        else:
            # Deterministic simulation accumulation
            # 1. Price Lever (Transparent assumption: quantity remains fixed)
            if params.price_change_pct != 0:
                p_dir = "increase" if params.price_change_pct > 0 else "reduction"
                p_rev_impact = baseline_revenue * p_change
                simulation_insights.append(
                    f"A {abs(params.price_change_pct):.1f}% price {p_dir} shifts revenue by "
                    f"${p_rev_impact:+,.2f} (deterministic model holding sales volume constant)."
                )

            # 2. Sales Volume Lever (Transparent assumption: unit price remains constant, variable costs scale)
            if volume_pct != 0:
                v_dir = "increase" if volume_pct > 0 else "reduction"
                v_rev_impact = baseline_revenue * v_change
                simulation_insights.append(
                    f"A {abs(volume_pct):.1f}% sales volume {v_dir} shifts revenue by "
                    f"${v_rev_impact:+,.2f} (deterministic model holding unit price constant and scaling variable costs proportionally)."
                )

            # Combined price and volume revenue impact
            pv_rev_delta = baseline_revenue * ((1.0 + p_change) * (1.0 + v_change) - 1.0)
            current_rev = baseline_revenue + pv_rev_delta

            # 3. Discount Lever
            discount_gain = 0.0
            if has_discount and params.discount_adjustment_pct != 0:
                parameter_type = getattr(params, "parameter_type", "percentage")
                if parameter_type == "percentage_points":
                    discount_gain = baseline_revenue * (params.discount_adjustment_pct / 100.0)
                else:
                    discount_gain = baseline_revenue * effective_disc_rate * d_adjust
                current_rev += discount_gain
                d_dir = "reduction" if params.discount_adjustment_pct > 0 else "expansion"
                simulation_insights.append(
                    f"A {abs(params.discount_adjustment_pct):.1f}% discount {d_dir} recovers "
                    f"${discount_gain:+,.2f} in net revenue and flow-through profit."
                )
            elif not has_discount and params.discount_adjustment_pct != 0:
                simulation_insights.append("Discount Change lever is unavailable: Dataset lacks a discount column.")

            # 4. Customer Retention / Churn Lever
            churn_saved = 0.0
            if has_churn and params.churn_mitigation_pct > 0:
                churn_saved = baseline_revenue * 0.05 * churn_mit
                current_rev += churn_saved
                simulation_insights.append(
                    f"Improving customer retention by {params.churn_mitigation_pct:.1f}% protects an estimated ${churn_saved:+,.2f} in revenue."
                )
            elif not has_churn and params.churn_mitigation_pct > 0:
                simulation_insights.append("Customer Retention lever is unavailable: Requires churn/retention data.")

            # 5. Cost Efficiency Lever (Never increases revenue; applies to operating costs)
            if has_cost and params.operational_efficiency_pct > 0:
                effective_cost_base = baseline_costs * (1.0 + v_change)
                cost_savings = effective_cost_base * ops_eff
                simulation_insights.append(
                    f"Operating cost reduction of {params.operational_efficiency_pct:.1f}% delivers ${cost_savings:+,.2f} in cost savings to profit (revenue remains unchanged)."
                )
            elif not has_cost and params.operational_efficiency_pct > 0:
                simulation_insights.append("Cost Efficiency lever is unavailable: Dataset lacks cost or profit metrics.")

            # Simulated Revenue (Cost reduction never modifies revenue)
            simulated_revenue = current_rev

            # Simulated Profit
            if has_profit:
                # Profit under volume, price, efficiency, discount, and churn
                # Volume scales baseline profit; price increase adds margin directly; efficiency reduces cost; discount recaptures revenue
                base_scaled_profit = baseline_profit * (1.0 + v_change)
                price_profit_addition = baseline_revenue * (1.0 + v_change) * p_change
                cost_savings_addition = baseline_costs * (1.0 + v_change) * ops_eff
                churn_profit_addition = churn_saved * 0.80 if churn_saved > 0 else 0.0

                simulated_profit = (
                    base_scaled_profit
                    + price_profit_addition
                    + cost_savings_addition
                    + discount_gain
                    + churn_profit_addition
                )
            else:
                simulated_profit = 0.0

            rev_delta = simulated_revenue - baseline_revenue
            rev_delta_pct = (rev_delta / abs(baseline_revenue) * 100) if baseline_revenue != 0 else 0.0

            if has_profit:
                profit_delta = simulated_profit - baseline_profit
                profit_delta_pct = (profit_delta / abs(baseline_profit) * 100) if baseline_profit != 0 else 0.0
                net_economic_value = round(profit_delta, 2)
                risk_adjusted_return = round(profit_delta * 0.85, 2)
            else:
                profit_delta = 0.0
                profit_delta_pct = 0.0
                net_economic_value = round(rev_delta, 2)
                risk_adjusted_return = round(rev_delta * 0.85, 2)

        baseline_margin_pct = round((baseline_profit / baseline_revenue * 100) if (has_profit and baseline_revenue > 0) else 0.0, 2)
        simulated_margin_pct = round((simulated_profit / simulated_revenue * 100) if (has_profit and simulated_revenue > 0) else 0.0, 2)
        margin_delta_pct = round(simulated_margin_pct - baseline_margin_pct, 2) if has_profit else 0.0

        # Sensitivity breakdown (dynamically calculated for supported levers)
        sensitivity: Dict[str, float] = {
            "price_sensitivity_per_pct": round(baseline_revenue * 0.01, 2),
            "volume_sensitivity_per_pct": round(baseline_revenue * 0.01, 2),
        }
        if has_discount:
            sensitivity["discount_recapture_per_pct"] = round(baseline_revenue * effective_disc_rate * 0.01, 2)
        if has_churn:
            sensitivity["churn_mitigation_per_pct"] = round(baseline_revenue * 0.05 * 0.01, 2)
        if has_cost and cost_col and baseline_costs > 0:
            sensitivity["operational_efficiency_per_pct"] = round(baseline_costs * 0.01, 2)

        # Dynamic Sensitivity Table (+1% marginal impact)
        sensitivity_table = [
            {
                "lever": "Price Adjustment",
                "step": "+1.0%",
                "revenue_impact": round(baseline_revenue * 0.01, 2),
                "profit_impact": round(baseline_revenue * 0.01, 2) if has_profit else 0.0,
                "is_supported": True,
            },
            {
                "lever": "Sales Volume Growth",
                "step": "+1.0%",
                "revenue_impact": round(baseline_revenue * 0.01, 2),
                "profit_impact": round(baseline_profit * 0.01, 2) if has_profit else 0.0,
                "is_supported": True,
            }
        ]
        if has_discount:
            disc_step_rev = round(baseline_revenue * effective_disc_rate * 0.01, 2)
            sensitivity_table.append({
                "lever": "Discount Reduction",
                "step": "+1.0%",
                "revenue_impact": disc_step_rev,
                "profit_impact": disc_step_rev if has_profit else 0.0,
                "is_supported": True,
            })
        if has_churn:
            churn_step_rev = round(baseline_revenue * 0.05 * 0.01, 2)
            sensitivity_table.append({
                "lever": "Customer Retention",
                "step": "+1.0%",
                "revenue_impact": churn_step_rev,
                "profit_impact": round(churn_step_rev * 0.80, 2) if has_profit else 0.0,
                "is_supported": True,
            })
        if has_cost and baseline_costs > 0:
            cost_step = round(baseline_costs * 0.01, 2)
            sensitivity_table.append({
                "lever": "Cost Efficiency",
                "step": "+1.0%",
                "revenue_impact": 0.0,
                "profit_impact": cost_step if has_profit else 0.0,
                "is_supported": True,
            })

        # Recommendations validated by this simulation configuration
        reinforced_recommendations = []
        if abs(params.price_change_pct) > 0:
            reinforced_recommendations.append("REC-003: Support Growth in Leading Segments")
        if abs(volume_pct) > 0:
            reinforced_recommendations.append("REC-003: Support Growth in Leading Segments")
        if has_discount and abs(params.discount_adjustment_pct) > 0:
            reinforced_recommendations.append("REC-002: Discount Control")
        if has_churn and params.churn_mitigation_pct > 0:
            reinforced_recommendations.append("REC-001: Operational Turnaround for Lagging Segments")
        if has_cost and params.operational_efficiency_pct > 0:
            reinforced_recommendations.append("REC-005: Set Up Automatic Alerts for Metric Outliers")

        assumptions_note = (
            "Transparent Assumptions: Price changes assume zero elasticity (constant volume). "
            "Sales volume changes assume constant unit price and proportional variable cost scaling. "
            "Operating cost reductions apply strictly to operating expenditure without altering revenue. "
            "Discount changes assume direct dollar recapture into net revenue and operating income."
        )

        return SimulationOutcome(
            baseline_revenue=round(baseline_revenue, 2),
            simulated_revenue=round(simulated_revenue, 2),
            revenue_delta=round(rev_delta, 2),
            revenue_delta_pct=round(rev_delta_pct, 2),
            baseline_profit=round(baseline_profit, 2),
            simulated_profit=round(simulated_profit, 2),
            profit_delta=round(profit_delta, 2),
            profit_delta_pct=round(profit_delta_pct, 2),
            baseline_margin_pct=baseline_margin_pct,
            simulated_margin_pct=simulated_margin_pct,
            margin_delta_pct=margin_delta_pct,
            simulation_insights=simulation_insights,
            net_economic_value_added=net_economic_value,
            risk_adjusted_return=risk_adjusted_return,
            sensitivity_breakdown=sensitivity,
            recommendation_impact_overlap=reinforced_recommendations,
            sensitivity_table=sensitivity_table,
            assumptions_statement=assumptions_note,
            supported_interventions=supported_interventions
        )

    @classmethod
    def validate_scenario_input(
        cls,
        df: pd.DataFrame,
        target_col: str,
        intervention_type: str,
        change_value: float,
        parameter_type: str = "percentage"
    ) -> Dict[str, Any]:
        """
        Validates scenario input against model and dataset constraints.
        Distinguishes percentage changes from percentage points,
        verifies dataset support, and rejects invalid values.
        """
        if df is None or df.empty:
            raise ValueError("Dataset is empty or missing.")

        if change_value is None or np.isnan(change_value) or np.isinf(change_value):
            raise ValueError("Parameter value must be a valid finite number.")

        detected = SemanticMetricDetector.detect_metrics(df, target_override=target_col)
        rev_info = detected["revenue"]
        profit_info = detected["profit"]
        cost_info = detected["cost"]
        disc_info = detected["discount"]

        cost_col = cost_info["column"]
        disc_col = disc_info["column"]
        has_cost = bool(cost_col or (rev_info["column"] and profit_info["column"]))
        has_discount = bool(disc_col and disc_col in df.columns and df[disc_col].dropna().count() > 0)

        norm_type = intervention_type.strip().lower().replace("_", " ")

        if norm_type in ["price change", "price", "price adjustment"]:
            if parameter_type == "percentage_points":
                raise ValueError("Price change must be specified as a percentage change (%), not percentage points.")
            if change_value < -100.0:
                raise ValueError("Price change percentage cannot be less than -100% (prices cannot be negative).")
            if change_value > 500.0:
                raise ValueError("Price change percentage exceeds the maximum supported threshold (+500%).")
            return {
                "intervention_type": "Price Change",
                "price_change_pct": float(change_value),
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "parameter_type": "percentage",
            }

        elif norm_type in ["sales volume change", "sales volume", "volume change", "volume"]:
            if parameter_type == "percentage_points":
                raise ValueError("Sales volume change must be specified as a percentage change (%), not percentage points.")
            if change_value < -100.0:
                raise ValueError("Sales volume change percentage cannot be less than -100% (sales volume cannot be negative).")
            if change_value > 500.0:
                raise ValueError("Sales volume change exceeds the maximum supported threshold (+500%).")
            return {
                "intervention_type": "Sales Volume Change",
                "price_change_pct": 0.0,
                "volume_change_pct": float(change_value),
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "parameter_type": "percentage",
            }

        elif norm_type in ["operating cost reduction", "cost reduction", "cost efficiency", "operational efficiency"]:
            if parameter_type == "percentage_points":
                raise ValueError("Operating cost reduction must be specified as a percentage change (%), not percentage points.")
            if not has_cost:
                raise ValueError("Operating Cost Reduction is unsupported: dataset lacks required cost or profit metrics.")
            if change_value < 0.0:
                raise ValueError("Operating cost reduction percentage cannot be negative (cost reduction must be >= 0%).")
            if change_value > 100.0:
                raise ValueError("Operating cost reduction percentage cannot exceed 100% (costs cannot be reduced below zero).")
            return {
                "intervention_type": "Operating Cost Reduction",
                "price_change_pct": 0.0,
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": float(change_value),
                "discount_adjustment_pct": 0.0,
                "parameter_type": "percentage",
            }

        elif norm_type in ["discount change", "discount reduction", "discount control", "discount adjustment"]:
            if not has_discount:
                raise ValueError("Discount Change is unsupported: dataset lacks valid discount data.")
            if parameter_type == "percentage_points":
                raw_mean_disc = float(df[disc_col].mean())
                baseline_disc_rate = raw_mean_disc if raw_mean_disc <= 1.0 else (raw_mean_disc / 100.0)
                baseline_pp = baseline_disc_rate * 100.0
                if change_value > baseline_pp:
                    raise ValueError(f"Discount reduction cannot exceed the baseline discount rate of {baseline_pp:.1f} percentage points.")
            else:
                if change_value < -100.0 or change_value > 100.0:
                    raise ValueError("Discount percentage change must be between -100% and +100%.")
            return {
                "intervention_type": "Discount Change",
                "price_change_pct": 0.0,
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": float(change_value),
                "parameter_type": parameter_type,
            }

        else:
            raise ValueError(f"Unsupported intervention type '{intervention_type}'. Supported types: Price Change, Sales Volume Change, Operating Cost Reduction, Discount Change.")

    @staticmethod
    def compare_scenarios(
        baseline_outcome: SimulationOutcome,
        scenarios: List[Dict[str, Any]]
    ) -> ScenarioComparisonReport:
        """
        Deterministically compares multiple simulation scenarios against baseline.
        Produces standardized financial metrics, profit margins, and comparative insights,
        with explicit tie reporting to avoid unsupported single winners.
        """
        items: List[ScenarioComparisonItem] = []

        # Neutral baseline
        base_rev = float(baseline_outcome.baseline_revenue)
        base_prof = float(baseline_outcome.baseline_profit)
        base_margin = round((base_prof / base_rev * 100) if base_rev > 0 else 0.0, 2)

        items.append(ScenarioComparisonItem(
            id="baseline",
            name="Baseline",
            revenue=round(base_rev, 2),
            profit=round(base_prof, 2),
            profit_margin_pct=base_margin,
            incremental_value=0.0,
            risk_adjusted_return=0.0,
            revenue_delta=0.0,
            profit_delta=0.0,
            parameters={
                "price_change_pct": 0.0,
                "volume_change_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": 0.0,
                "operational_efficiency_pct": 0.0
            },
            intervention_summary="Baseline (0% adjustments)",
            notes="Default neutral baseline"
        ))

        for sc in scenarios:
            outcomes = sc.get("projected_outcomes") or {}
            params = sc.get("parameters") or {}
            sim_rev = float(outcomes.get("simulated_revenue", base_rev))
            sim_prof = float(outcomes.get("simulated_profit", base_prof))
            prof_margin = round((sim_prof / sim_rev * 100) if sim_rev > 0 else 0.0, 2)
            inc_val = float(outcomes.get("profit_delta") or outcomes.get("net_economic_value_added") or 0.0)
            risk_adj = float(outcomes.get("risk_adjusted_return") or 0.0)
            rev_delta = float(outcomes.get("revenue_delta") or (sim_rev - base_rev))
            prof_delta = float(outcomes.get("profit_delta") or (sim_prof - base_prof))

            # Build human-readable intervention summary
            intervention_summary = None
            if params.get("intervention_type"):
                c_val = params.get("change_percentage", params.get("change_pct", 0.0))
                p_unit = "%" if params.get("parameter_type", "percentage") == "percentage" else "pp"
                itype = params.get("intervention_type")
                if itype == "Price Change":
                    direction = "Increase" if c_val > 0 else ("Reduction" if c_val < 0 else "Change")
                    intervention_summary = f"Price {direction}: {c_val:+g}{p_unit}"
                elif itype == "Sales Volume Change":
                    direction = "Growth" if c_val > 0 else ("Decline" if c_val < 0 else "Change")
                    intervention_summary = f"Volume {direction}: {c_val:+g}{p_unit}"
                elif itype in ["Operating Cost Reduction", "Cost Reduction"]:
                    intervention_summary = f"Cost Reduction: {abs(c_val):g}{p_unit}"
                else:
                    intervention_summary = f"{itype}: {c_val:+g}{p_unit}"
            elif params.get("price_change_pct") is not None and params.get("price_change_pct") != 0:
                c_val = params.get("price_change_pct")
                direction = "Increase" if c_val > 0 else "Reduction"
                intervention_summary = f"Price {direction}: {c_val:+g}%"
            elif params.get("volume_change_pct") is not None and params.get("volume_change_pct") != 0:
                c_val = params.get("volume_change_pct")
                direction = "Growth" if c_val > 0 else "Decline"
                intervention_summary = f"Volume {direction}: {c_val:+g}%"
            elif params.get("operational_efficiency_pct") is not None and params.get("operational_efficiency_pct") != 0:
                c_val = params.get("operational_efficiency_pct")
                intervention_summary = f"Cost Reduction: {abs(c_val):g}%"
            elif params.get("discount_adjustment_pct") is not None and params.get("discount_adjustment_pct") != 0:
                intervention_summary = f"Discount Change: {params.get('discount_adjustment_pct'):+g}%"

            notes = sc.get("notes") or params.get("notes") or outcomes.get("notes")

            items.append(ScenarioComparisonItem(
                id=str(sc.get("id") or sc.get("name")),
                name=sc.get("name", "Scenario"),
                revenue=round(sim_rev, 2),
                profit=round(sim_prof, 2),
                profit_margin_pct=prof_margin,
                incremental_value=round(inc_val, 2),
                risk_adjusted_return=round(risk_adj, 2),
                revenue_delta=round(rev_delta, 2),
                profit_delta=round(prof_delta, 2),
                parameters=params,
                intervention_summary=intervention_summary,
                notes=notes
            ))

        insights: List[str] = []
        if len(items) <= 1:
            insights.append("Only the neutral baseline is active. Create and save scenarios to compare tradeoffs.")
            return ScenarioComparisonReport(scenarios=items, comparison_insights=insights)

        non_baseline = [it for it in items if it.id != "baseline"]

        # Check if all scenarios have zero incremental value
        all_zero_deltas = all(
            abs(it.profit_delta) < 1e-4 and abs(it.revenue_delta) < 1e-4
            for it in non_baseline
        )

        # 1. Profit Evaluation & Tie Detection
        max_profit = max(it.profit for it in non_baseline)
        top_profit = [it for it in non_baseline if abs(it.profit - max_profit) < 1e-4]
        if len(top_profit) > 1:
            best_profit_name = f"Tie ({', '.join(s.name for s in top_profit)})"
            profit_names = ", ".join(f"'{s.name}'" for s in top_profit)
            if top_profit[0].profit_delta > 0:
                insights.append(
                    f"Tie for highest simulated profit: {profit_names} "
                    f"each produce an identical profit improvement of +${top_profit[0].profit_delta:,.2f}."
                )
            else:
                insights.append(
                    f"Tie for best relative profit: {profit_names} "
                    f"share the top simulated profit of ${max_profit:,.2f}."
                )
        else:
            best_profit = top_profit[0]
            best_profit_name = best_profit.name
            if best_profit.profit_delta > 0:
                insights.append(f"'{best_profit.name}' produces the highest simulated profit improvement (+${best_profit.profit_delta:,.2f}).")
            else:
                insights.append(f"'{best_profit.name}' produces the best relative profit performance among evaluated scenarios.")

        # 2. Revenue Evaluation & Tie Detection
        max_rev = max(it.revenue for it in non_baseline)
        top_rev = [it for it in non_baseline if abs(it.revenue - max_rev) < 1e-4]
        if len(top_rev) > 1:
            best_rev_name = f"Tie ({', '.join(s.name for s in top_rev)})"
            rev_names = ", ".join(f"'{s.name}'" for s in top_rev)
            if set(s.name for s in top_rev) != set(s.name for s in top_profit):
                insights.append(
                    f"Tie for highest simulated revenue: {rev_names} "
                    f"each achieve ${max_rev:,.2f} in projected revenue."
                )
        else:
            best_rev = top_rev[0]
            best_rev_name = best_rev.name
            if best_rev.name != best_profit_name and not (len(top_profit) > 1 and best_rev.name in [s.name for s in top_profit]):
                insights.append(f"'{best_rev.name}' achieves the highest simulated revenue (+${best_rev.revenue_delta:,.2f}) but yields lower profit gains than '{best_profit_name}'.")

        # 3. Margin Evaluation & Tie Detection
        max_margin = max(it.profit_margin_pct for it in non_baseline)
        top_margin = [it for it in non_baseline if abs(it.profit_margin_pct - max_margin) < 1e-4]
        if len(top_margin) > 1:
            best_margin_name = f"Tie ({', '.join(s.name for s in top_margin)})"
            margin_names = ", ".join(f"'{s.name}'" for s in top_margin)
            if len(non_baseline) > len(top_margin) and set(s.name for s in top_margin) != set(s.name for s in top_profit):
                insights.append(
                    f"Tie for highest profit margin: {margin_names} "
                    f"each deliver a {max_margin:.2f}% margin."
                )
        else:
            best_margin = top_margin[0]
            best_margin_name = best_margin.name
            if best_margin.name != best_profit_name and best_margin.name != best_rev_name:
                insights.append(f"'{best_margin.name}' delivers the highest simulated profit margin ({best_margin.profit_margin_pct:.2f}%).")

        if all_zero_deltas:
            insights.append("All evaluated scenarios match the neutral baseline with zero incremental value.")

        return ScenarioComparisonReport(
            scenarios=items,
            comparison_insights=insights,
            best_profit_scenario=best_profit_name,
            best_revenue_scenario=best_rev_name,
            best_margin_scenario=best_margin_name
        )
