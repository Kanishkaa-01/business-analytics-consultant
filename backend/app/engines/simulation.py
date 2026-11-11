from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.schemas import (
    SimulationRequest,
    SimulationOutcome,
    ScenarioComparisonItem,
    ScenarioComparisonReport,
)
from app.services.semantic_metrics import SemanticMetricDetector
from app.services.capability_assessor import DatasetCapabilityAssessor


class SimulationEngine:
    @staticmethod
    def run_simulation(
        df: pd.DataFrame,
        target_col: str,
        params: SimulationRequest
    ) -> SimulationOutcome:
        """
        Runs deterministic what-if scenario simulations adapting to dataset domain:
        - Retail: Price change, discount recovery, sales volume, operating cost reduction
        - Workforce / HR: Attrition reduction, job satisfaction improvement, HR cost efficiency
        - Manufacturing: Defect rate reduction, downtime reduction, throughput optimization
        - SaaS: Churn mitigation, account expansion, cost efficiency
        - Financial: Asset volume growth, yield optimization, operational cost reduction
        - General: Primary metric adjustment or clean limitation statement
        """
        total_records = len(df)
        if total_records == 0:
            raise ValueError("Cannot simulate on an empty dataset.")

        caps = DatasetCapabilityAssessor.assess_capabilities(df, target_col=target_col)

        # Check if scenario simulation is supported for this dataset
        if not caps.can_simulate_scenarios:
            reason = (
                caps.scenario_unsupported_reason
                or "What-If scenario simulation is unavailable for this dataset because required decision levers and controllable outcome variables were not detected."
            )
            return SimulationOutcome(
                baseline_revenue=0.0,
                simulated_revenue=0.0,
                revenue_delta=0.0,
                revenue_delta_pct=0.0,
                baseline_profit=0.0,
                simulated_profit=0.0,
                profit_delta=0.0,
                profit_delta_pct=0.0,
                baseline_margin_pct=0.0,
                simulated_margin_pct=0.0,
                margin_delta_pct=0.0,
                simulation_insights=[reason],
                net_economic_value_added=0.0,
                risk_adjusted_return=0.0,
                sensitivity_breakdown={},
                recommendation_impact_overlap=[],
                sensitivity_table=[],
                assumptions_statement=reason,
                supported_interventions=[],
                scenario_domain=caps.domain,
                scenario_domain_label=caps.domain_label,
                is_scenario_supported=False,
                unsupported_reason=reason,
                outcome_cards=[],
                active_levers=[],
                chart_config=None,
            )

        # Input validation on common numeric lever params
        if np.isnan(params.price_change_pct) or np.isinf(params.price_change_pct):
            raise ValueError("Parameter percentage must be a valid finite number.")
        if params.price_change_pct < -100.0:
            raise ValueError("Adjustment percentage cannot be less than -100%.")

        volume_pct = getattr(params, "volume_change_pct", 0.0)
        if np.isnan(volume_pct) or np.isinf(volume_pct):
            raise ValueError("Volume change percentage must be a valid finite number.")
        if volume_pct < -100.0:
            raise ValueError("Volume change percentage cannot be less than -100%.")

        if np.isnan(params.operational_efficiency_pct) or np.isinf(params.operational_efficiency_pct):
            raise ValueError("Operating cost reduction percentage must be a valid finite number.")
        if params.operational_efficiency_pct < 0.0 or params.operational_efficiency_pct > 100.0:
            raise ValueError("Operating cost reduction percentage must be between 0% and 100%.")

        if np.isnan(params.discount_adjustment_pct) or np.isinf(params.discount_adjustment_pct):
            raise ValueError("Discount change percentage must be a valid finite number.")
        if params.discount_adjustment_pct < -100.0 or params.discount_adjustment_pct > 100.0:
            raise ValueError("Discount change percentage must be between -100% and 100%.")

        # -------------------------------------------------------------
        # DOMAIN 1: WORKFORCE / HR
        # -------------------------------------------------------------
        if caps.domain == "workforce":
            total_hc = len(df)
            attr_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["attrition", "turnover", "left", "resigned"])), None)
            comp_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["monthlyincome", "salary", "wage", "compensation", "earnings"])), None)
            sat_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["jobsatisfaction", "satisfaction", "engagement", "rating"])), None)

            if attr_col:
                is_attr = df[attr_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "attrited", "left"])
                base_attr_count = int(is_attr.sum())
            else:
                base_attr_count = max(1, int(round(total_hc * 0.16)))

            base_attr_rate = round((base_attr_count / total_hc * 100), 2) if total_hc > 0 else 0.0

            if comp_col and pd.api.types.is_numeric_dtype(df[comp_col]):
                avg_monthly_comp = float(df[comp_col].dropna().mean())
            else:
                avg_monthly_comp = 6500.0
            cost_per_turnover = round(avg_monthly_comp * 6.0, 2)  # Benchmark: 6 months replacement & onboarding cost

            # Levers:
            attr_red_pct = min(100.0, max(0.0, params.churn_mitigation_pct))
            sat_imp_pct = min(100.0, max(0.0, params.price_change_pct))
            hr_eff_pct = min(100.0, max(0.0, params.operational_efficiency_pct))

            is_all_zero = (attr_red_pct == 0.0 and sat_imp_pct == 0.0 and hr_eff_pct == 0.0)

            sim_attr_count = int(round(base_attr_count * (1.0 - attr_red_pct / 100.0)))
            retained_employees = base_attr_count - sim_attr_count
            sim_attr_rate = round((sim_attr_count / total_hc * 100), 2) if total_hc > 0 else 0.0
            turnover_cost_savings = round(retained_employees * cost_per_turnover, 2)

            annual_comp_expenditure = round(total_hc * avg_monthly_comp * 12.0, 2)
            hr_eff_savings = round(annual_comp_expenditure * 0.05 * (hr_eff_pct / 100.0), 2)
            net_value = round(turnover_cost_savings + hr_eff_savings, 2)
            risk_adj = round(net_value * 0.85, 2)

            insights: List[str] = []
            if is_all_zero:
                insights.append("Baseline workforce structure active. No retention or efficiency levers applied.")
            if attr_red_pct > 0:
                insights.append(
                    f"A {attr_red_pct:.1f}% reduction in attrition retains {retained_employees} employees, "
                    f"preventing ${turnover_cost_savings:+,.2f} in turnover, replacement, and lost-productivity costs."
                )
            if sat_imp_pct > 0:
                insights.append(
                    f"A {sat_imp_pct:.1f}% improvement in employee satisfaction strengthens retention stability and cultural alignment."
                )
            if hr_eff_pct > 0:
                insights.append(
                    f"Optimizing HR operational expenditure by {hr_eff_pct:.1f}% delivers ${hr_eff_savings:+,.2f} in process savings."
                )

            outcome_cards = [
                {
                    "title": "Retained Employees",
                    "baseline": float(total_hc - base_attr_count),
                    "simulated": float(total_hc - sim_attr_count),
                    "delta": float(retained_employees),
                    "delta_pct": round(float(retained_employees / max(1, base_attr_count) * 100), 1),
                    "unit": "employees",
                },
                {
                    "title": "Simulated Attrition Rate",
                    "baseline": base_attr_rate,
                    "simulated": sim_attr_rate,
                    "delta": round(sim_attr_rate - base_attr_rate, 2),
                    "delta_pct": round(((sim_attr_rate - base_attr_rate) / max(0.1, base_attr_rate) * 100), 1),
                    "unit": "%",
                },
                {
                    "title": "Estimated Turnover Cost Avoidance",
                    "baseline": 0.0,
                    "simulated": net_value,
                    "delta": net_value,
                    "delta_pct": 100.0 if net_value > 0 else 0.0,
                    "unit": "$",
                },
            ]

            active_levers = [
                {
                    "id": "churn_mitigation_pct",
                    "name": "Attrition Reduction",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Reduces employee turnover rate through retention and engagement initiatives.",
                },
                {
                    "id": "price_change_pct",
                    "name": "Job Satisfaction Improvement",
                    "min": 0,
                    "max": 25,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Simulates workplace culture and employee engagement enhancement.",
                },
                {
                    "id": "operational_efficiency_pct",
                    "name": "HR Program Cost Efficiency",
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Streamlines recruitment, onboarding, and internal talent development costs.",
                },
            ]

            sensitivity = {
                "attrition_reduction_per_pct": round(cost_per_turnover * base_attr_count * 0.01, 2),
                "hr_efficiency_per_pct": round(annual_comp_expenditure * 0.05 * 0.01, 2),
            }

            sensitivity_table = [
                {
                    "lever": "Attrition Reduction",
                    "step": "+1.0%",
                    "revenue_impact": 0.0,
                    "profit_impact": round(cost_per_turnover * base_attr_count * 0.01, 2),
                    "is_supported": True,
                },
                {
                    "lever": "HR Program Cost Efficiency",
                    "step": "+1.0%",
                    "revenue_impact": 0.0,
                    "profit_impact": round(annual_comp_expenditure * 0.05 * 0.01, 2),
                    "is_supported": True,
                },
            ]

            chart_config = {
                "domain": "workforce",
                "charts": [
                    {
                        "title": card["title"],
                        "unit": card["unit"],
                        "baseline": card["baseline"],
                        "simulated": card["simulated"],
                        "delta": card["delta"],
                    }
                    for card in outcome_cards
                ],
            }

            return SimulationOutcome(
                baseline_revenue=round(annual_comp_expenditure, 2),
                simulated_revenue=round(annual_comp_expenditure, 2),
                revenue_delta=0.0,
                revenue_delta_pct=0.0,
                baseline_profit=0.0,
                simulated_profit=round(net_value, 2),
                profit_delta=round(net_value, 2),
                profit_delta_pct=100.0 if net_value > 0 else 0.0,
                baseline_margin_pct=base_attr_rate,
                simulated_margin_pct=sim_attr_rate,
                margin_delta_pct=round(sim_attr_rate - base_attr_rate, 2),
                simulation_insights=insights,
                net_economic_value_added=net_value,
                risk_adjusted_return=risk_adj,
                sensitivity_breakdown=sensitivity,
                recommendation_impact_overlap=["REC-001: Workforce Retention & Attrition Control"],
                sensitivity_table=sensitivity_table,
                assumptions_statement=(
                    "Workforce Simulation Assumptions: Voluntary turnover replacement costs are estimated at "
                    f"6 months of baseline compensation (${cost_per_turnover:,.2f} per departure) based on standard SHRM benchmarks. "
                    "HR operational efficiency applies strictly to talent acquisition and training expenditure."
                ),
                supported_interventions=["Attrition Reduction", "Satisfaction Improvement", "HR Program Cost Efficiency"],
                scenario_domain="workforce",
                scenario_domain_label="Workforce & Human Resources",
                is_scenario_supported=True,
                outcome_cards=outcome_cards,
                active_levers=active_levers,
                chart_config=chart_config,
            )

        # -------------------------------------------------------------
        # DOMAIN 2: MANUFACTURING / OPERATIONS
        # -------------------------------------------------------------
        if caps.domain == "manufacturing":
            qty_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["quantity", "units", "output", "produced", "volume"])), None)
            defect_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["defect", "scrap", "reject", "fault", "error"])), None)
            downtime_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["downtime", "idle", "delay", "repair"])), None)

            total_units = float(df[qty_col].sum()) if (qty_col and pd.api.types.is_numeric_dtype(df[qty_col])) else float(len(df) * 100.0)

            if defect_col and pd.api.types.is_numeric_dtype(df[defect_col]):
                raw_def = float(df[defect_col].sum())
                base_defect_rate = round((raw_def / total_units * 100), 2) if raw_def <= total_units else round(float(df[defect_col].mean()), 2)
            else:
                base_defect_rate = 5.0

            if downtime_col and pd.api.types.is_numeric_dtype(df[downtime_col]):
                base_downtime = round(float(df[downtime_col].sum()), 1)
            else:
                base_downtime = 120.0

            defect_red_pct = min(100.0, max(0.0, params.churn_mitigation_pct))
            downtime_red_pct = min(100.0, max(0.0, params.operational_efficiency_pct))
            throughput_pct = min(100.0, max(-100.0, volume_pct))

            is_all_zero = (defect_red_pct == 0.0 and downtime_red_pct == 0.0 and throughput_pct == 0.0)

            sim_defect_rate = round(base_defect_rate * (1.0 - defect_red_pct / 100.0), 2)
            cost_per_defect = 50.0  # $50 benchmark cost per scrapped unit
            avoided_scrap_cost = round((base_defect_rate - sim_defect_rate) / 100.0 * total_units * cost_per_defect, 2)

            sim_downtime = round(base_downtime * (1.0 - downtime_red_pct / 100.0), 1)
            recovered_downtime = round(base_downtime - sim_downtime, 1)
            downtime_value = round(recovered_downtime * 200.0, 2)  # $200/hr downtime avoidance benchmark

            net_value = round(avoided_scrap_cost + downtime_value, 2)
            risk_adj = round(net_value * 0.85, 2)

            insights = []
            if is_all_zero:
                insights.append("Baseline manufacturing operations active. No operational adjustments applied.")
            if defect_red_pct > 0:
                insights.append(
                    f"A {defect_red_pct:.1f}% defect reduction lowers defect rate from {base_defect_rate:.2f}% to {sim_defect_rate:.2f}%, "
                    f"avoiding ${avoided_scrap_cost:+,.2f} in scrap and rework costs."
                )
            if downtime_red_pct > 0:
                insights.append(
                    f"Reducing downtime by {downtime_red_pct:.1f}% recovers {recovered_downtime:,.1f} operational hours (${downtime_value:+,.2f} value)."
                )

            outcome_cards = [
                {
                    "title": "Simulated Defect Rate",
                    "baseline": base_defect_rate,
                    "simulated": sim_defect_rate,
                    "delta": round(sim_defect_rate - base_defect_rate, 2),
                    "delta_pct": round(((sim_defect_rate - base_defect_rate) / max(0.1, base_defect_rate) * 100), 1),
                    "unit": "%",
                },
                {
                    "title": "Avoided Scrap Cost",
                    "baseline": 0.0,
                    "simulated": avoided_scrap_cost,
                    "delta": avoided_scrap_cost,
                    "delta_pct": 100.0 if avoided_scrap_cost > 0 else 0.0,
                    "unit": "$",
                },
                {
                    "title": "Recovered Operational Uptime",
                    "baseline": 0.0,
                    "simulated": recovered_downtime,
                    "delta": recovered_downtime,
                    "delta_pct": 100.0 if recovered_downtime > 0 else 0.0,
                    "unit": "hours",
                },
            ]

            active_levers = [
                {
                    "id": "churn_mitigation_pct",
                    "name": "Defect Rate Reduction",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Reduces manufacturing defect rate via automated quality assurance.",
                },
                {
                    "id": "operational_efficiency_pct",
                    "name": "Downtime Reduction",
                    "min": 0,
                    "max": 40,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Recovers equipment uptime through predictive maintenance scheduling.",
                },
                {
                    "id": "volume_change_pct",
                    "name": "Throughput Optimization",
                    "min": -20,
                    "max": 30,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Optimizes production line capacity and cycle times.",
                },
            ]

            sensitivity = {
                "defect_reduction_per_pct": round(total_units * 0.01 * cost_per_defect, 2),
                "downtime_reduction_per_pct": round(base_downtime * 0.01 * 200.0, 2),
            }

            sensitivity_table = [
                {
                    "lever": "Defect Rate Reduction",
                    "step": "+1.0%",
                    "revenue_impact": 0.0,
                    "profit_impact": round(total_units * 0.01 * cost_per_defect, 2),
                    "is_supported": True,
                },
                {
                    "lever": "Downtime Reduction",
                    "step": "+1.0%",
                    "revenue_impact": 0.0,
                    "profit_impact": round(base_downtime * 0.01 * 200.0, 2),
                    "is_supported": True,
                },
            ]

            chart_config = {
                "domain": "manufacturing",
                "charts": [
                    {
                        "title": card["title"],
                        "unit": card["unit"],
                        "baseline": card["baseline"],
                        "simulated": card["simulated"],
                        "delta": card["delta"],
                    }
                    for card in outcome_cards
                ],
            }

            return SimulationOutcome(
                baseline_revenue=round(total_units * 100.0, 2),
                simulated_revenue=round(total_units * 100.0, 2),
                revenue_delta=0.0,
                revenue_delta_pct=0.0,
                baseline_profit=0.0,
                simulated_profit=round(net_value, 2),
                profit_delta=round(net_value, 2),
                profit_delta_pct=100.0 if net_value > 0 else 0.0,
                baseline_margin_pct=base_defect_rate,
                simulated_margin_pct=sim_defect_rate,
                margin_delta_pct=round(sim_defect_rate - base_defect_rate, 2),
                simulation_insights=insights,
                net_economic_value_added=net_value,
                risk_adjusted_return=risk_adj,
                sensitivity_breakdown=sensitivity,
                recommendation_impact_overlap=["REC-001: Quality Assurance & Defect Reduction"],
                sensitivity_table=sensitivity_table,
                assumptions_statement=(
                    "Manufacturing Simulation Assumptions: Scrap and rework costs are benchmarked at $50 per defect unit. "
                    "Operational downtime avoidance is valued at $200 per operating hour."
                ),
                supported_interventions=["Defect Rate Reduction", "Downtime Reduction", "Throughput Optimization"],
                scenario_domain="manufacturing",
                scenario_domain_label="Manufacturing & Operations",
                is_scenario_supported=True,
                outcome_cards=outcome_cards,
                active_levers=active_levers,
                chart_config=chart_config,
            )

        # -------------------------------------------------------------
        # DOMAIN 3: SAAS / SUBSCRIPTION
        # -------------------------------------------------------------
        if caps.domain == "saas":
            rev_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["arr", "mrr", "revenue", "amount"])), None)
            churn_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["churn", "cancelled", "left", "status"])), None)
            total_acc = len(df)

            base_arr = float(df[rev_col].sum()) if (rev_col and pd.api.types.is_numeric_dtype(df[rev_col])) else float(total_acc * 1200.0)

            if churn_col:
                is_churned = df[churn_col].astype(str).str.strip().str.lower().isin(["yes", "1", "true", "churned", "cancelled"])
                base_churn_count = int(is_churned.sum())
            else:
                base_churn_count = max(1, int(round(total_acc * 0.08)))
            base_churn_rate = round((base_churn_count / total_acc * 100), 2) if total_acc > 0 else 0.0

            churn_red_pct = min(100.0, max(0.0, params.churn_mitigation_pct))
            expansion_pct = min(100.0, max(-100.0, params.price_change_pct))
            cost_eff_pct = min(100.0, max(0.0, params.operational_efficiency_pct))

            is_all_zero = (churn_red_pct == 0.0 and expansion_pct == 0.0 and cost_eff_pct == 0.0)

            sim_churn_count = int(round(base_churn_count * (1.0 - churn_red_pct / 100.0)))
            retained_accounts = base_churn_count - sim_churn_count
            sim_churn_rate = round((sim_churn_count / total_acc * 100), 2) if total_acc > 0 else 0.0
            protected_arr = round(base_arr * (base_churn_rate / 100.0) * (churn_red_pct / 100.0), 2)
            expansion_arr = round(base_arr * (expansion_pct / 100.0), 2)
            sim_arr = round(base_arr + protected_arr + expansion_arr, 2)
            net_value = round(protected_arr + expansion_arr, 2)
            risk_adj = round(net_value * 0.85, 2)

            insights = []
            if is_all_zero:
                insights.append("Baseline subscription structure active. No retention or expansion adjustments applied.")
            if churn_red_pct > 0:
                insights.append(
                    f"A {churn_red_pct:.1f}% churn reduction retains {retained_accounts} subscription accounts, protecting ${protected_arr:+,.2f} in ARR."
                )
            if expansion_pct != 0:
                insights.append(
                    f"A {expansion_pct:+.1f}% expansion in net revenue retention shifts ARR by ${expansion_arr:+,.2f}."
                )

            outcome_cards = [
                {
                    "title": "Protected ARR",
                    "baseline": 0.0,
                    "simulated": protected_arr,
                    "delta": protected_arr,
                    "delta_pct": 100.0 if protected_arr > 0 else 0.0,
                    "unit": "$",
                },
                {
                    "title": "Simulated Churn Rate",
                    "baseline": base_churn_rate,
                    "simulated": sim_churn_rate,
                    "delta": round(sim_churn_rate - base_churn_rate, 2),
                    "delta_pct": round(((sim_churn_rate - base_churn_rate) / max(0.1, base_churn_rate) * 100), 1),
                    "unit": "%",
                },
                {
                    "title": "Retained Subscriptions",
                    "baseline": float(total_acc - base_churn_count),
                    "simulated": float(total_acc - sim_churn_count),
                    "delta": float(retained_accounts),
                    "delta_pct": round(float(retained_accounts / max(1, base_churn_count) * 100), 1),
                    "unit": "accounts",
                },
            ]

            active_levers = [
                {
                    "id": "churn_mitigation_pct",
                    "name": "Churn Rate Reduction",
                    "min": 0,
                    "max": 50,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Protects annual recurring revenue by decreasing customer churn.",
                },
                {
                    "id": "price_change_pct",
                    "name": "Account Expansion / ARPU Uplift",
                    "min": -20,
                    "max": 30,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Models expansion revenue, upsell, and average contract value changes.",
                },
                {
                    "id": "operational_efficiency_pct",
                    "name": "Operating Cost Efficiency",
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Optimizes customer acquisition and infrastructure expenditures.",
                },
            ]

            sensitivity = {
                "churn_reduction_per_pct": round(base_arr * (base_churn_rate / 100.0) * 0.01, 2),
                "expansion_per_pct": round(base_arr * 0.01, 2),
            }

            sensitivity_table = [
                {
                    "lever": "Churn Rate Reduction",
                    "step": "+1.0%",
                    "revenue_impact": round(base_arr * (base_churn_rate / 100.0) * 0.01, 2),
                    "profit_impact": round(base_arr * (base_churn_rate / 100.0) * 0.01 * 0.8, 2),
                    "is_supported": True,
                },
                {
                    "lever": "Account Expansion",
                    "step": "+1.0%",
                    "revenue_impact": round(base_arr * 0.01, 2),
                    "profit_impact": round(base_arr * 0.01 * 0.8, 2),
                    "is_supported": True,
                },
            ]

            chart_config = {
                "domain": "saas",
                "charts": [
                    {
                        "title": card["title"],
                        "unit": card["unit"],
                        "baseline": card["baseline"],
                        "simulated": card["simulated"],
                        "delta": card["delta"],
                    }
                    for card in outcome_cards
                ],
            }

            return SimulationOutcome(
                baseline_revenue=round(base_arr, 2),
                simulated_revenue=round(sim_arr, 2),
                revenue_delta=round(sim_arr - base_arr, 2),
                revenue_delta_pct=round(((sim_arr - base_arr) / base_arr * 100), 2) if base_arr > 0 else 0.0,
                baseline_profit=round(base_arr * 0.20, 2),
                simulated_profit=round(base_arr * 0.20 + net_value * 0.80, 2),
                profit_delta=round(net_value * 0.80, 2),
                profit_delta_pct=round((net_value * 0.80 / max(1.0, base_arr * 0.20) * 100), 2),
                baseline_margin_pct=base_churn_rate,
                simulated_margin_pct=sim_churn_rate,
                margin_delta_pct=round(sim_churn_rate - base_churn_rate, 2),
                simulation_insights=insights,
                net_economic_value_added=net_value,
                risk_adjusted_return=risk_adj,
                sensitivity_breakdown=sensitivity,
                recommendation_impact_overlap=["REC-001: Customer Success & Churn Mitigation"],
                sensitivity_table=sensitivity_table,
                assumptions_statement=(
                    "SaaS Simulation Assumptions: Protected ARR is calculated from baseline recurring revenue "
                    "multiplied by the churn rate reduction. Account expansion assumes constant customer volume."
                ),
                supported_interventions=["Churn Rate Reduction", "Account Expansion", "Operating Cost Efficiency"],
                scenario_domain="saas",
                scenario_domain_label="SaaS & Subscription",
                is_scenario_supported=True,
                outcome_cards=outcome_cards,
                active_levers=active_levers,
                chart_config=chart_config,
            )

        # -------------------------------------------------------------
        # DOMAIN 4: FINANCIAL / BANKING
        # -------------------------------------------------------------
        if caps.domain == "financial":
            bal_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["balance", "loan", "deposit", "asset", "amount"])), None)
            base_bal = float(df[bal_col].sum()) if (bal_col and pd.api.types.is_numeric_dtype(df[bal_col])) else 1000000.0

            vol_growth_pct = min(100.0, max(-100.0, volume_pct))
            yield_opt_pct = min(100.0, max(-100.0, params.price_change_pct))
            cost_eff_pct = min(100.0, max(0.0, params.operational_efficiency_pct))

            is_all_zero = (vol_growth_pct == 0.0 and yield_opt_pct == 0.0 and cost_eff_pct == 0.0)

            sim_bal = round(base_bal * (1.0 + vol_growth_pct / 100.0), 2)
            bal_delta = round(sim_bal - base_bal, 2)
            bal_delta_pct = round((bal_delta / base_bal * 100), 2) if base_bal > 0 else 0.0

            base_yield = 0.035  # Benchmark 3.5% net interest margin
            sim_yield = base_yield * (1.0 + yield_opt_pct / 100.0)
            base_nim = round(base_bal * base_yield, 2)
            sim_nim = round(sim_bal * sim_yield, 2)
            nim_delta = round(sim_nim - base_nim, 2)

            net_value = nim_delta
            risk_adj = round(net_value * 0.85, 2)

            insights = []
            if is_all_zero:
                insights.append("Baseline financial portfolio active. No asset volume or yield adjustments applied.")
            if vol_growth_pct != 0:
                insights.append(
                    f"A {vol_growth_pct:+.1f}% shift in asset volume adjusts balance by ${bal_delta:+,.2f}."
                )
            if yield_opt_pct != 0:
                insights.append(
                    f"A {yield_opt_pct:+.1f}% yield optimization alters projected annual spread revenue by ${nim_delta:+,.2f}."
                )

            outcome_cards = [
                {
                    "title": "Simulated Asset Volume",
                    "baseline": base_bal,
                    "simulated": sim_bal,
                    "delta": bal_delta,
                    "delta_pct": bal_delta_pct,
                    "unit": "$",
                },
                {
                    "title": "Net Spread / Yield Revenue",
                    "baseline": base_nim,
                    "simulated": sim_nim,
                    "delta": nim_delta,
                    "delta_pct": round((nim_delta / max(1.0, base_nim) * 100), 2),
                    "unit": "$",
                },
                {
                    "title": "Net Yield Margin",
                    "baseline": round(base_yield * 100, 2),
                    "simulated": round(sim_yield * 100, 2),
                    "delta": round((sim_yield - base_yield) * 100, 2),
                    "delta_pct": round(((sim_yield - base_yield) / base_yield * 100), 1),
                    "unit": "%",
                },
            ]

            active_levers = [
                {
                    "id": "volume_change_pct",
                    "name": "Asset Volume Growth",
                    "min": -20,
                    "max": 30,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Models expansion in loan, deposit, or asset portfolios.",
                },
                {
                    "id": "price_change_pct",
                    "name": "Yield / Spread Optimization",
                    "min": -10,
                    "max": 20,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Adjusts interest rate spreads and financial fee structures.",
                },
                {
                    "id": "operational_efficiency_pct",
                    "name": "Operating Cost Efficiency",
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "default": 0,
                    "unit": "%",
                    "description": "Streamlines branch and transaction processing expenditure.",
                },
            ]

            chart_config = {
                "domain": "financial",
                "charts": [
                    {
                        "title": card["title"],
                        "unit": card["unit"],
                        "baseline": card["baseline"],
                        "simulated": card["simulated"],
                        "delta": card["delta"],
                    }
                    for card in outcome_cards
                ],
            }

            return SimulationOutcome(
                baseline_revenue=round(base_bal, 2),
                simulated_revenue=round(sim_bal, 2),
                revenue_delta=bal_delta,
                revenue_delta_pct=bal_delta_pct,
                baseline_profit=base_nim,
                simulated_profit=sim_nim,
                profit_delta=nim_delta,
                profit_delta_pct=round((nim_delta / max(1.0, base_nim) * 100), 2),
                baseline_margin_pct=round(base_yield * 100, 2),
                simulated_margin_pct=round(sim_yield * 100, 2),
                margin_delta_pct=round((sim_yield - base_yield) * 100, 2),
                simulation_insights=insights,
                net_economic_value_added=net_value,
                risk_adjusted_return=risk_adj,
                sensitivity_breakdown={"asset_growth_per_pct": round(base_bal * 0.01, 2)},
                recommendation_impact_overlap=["REC-001: Margin & Spread Management"],
                sensitivity_table=[{"lever": "Asset Growth", "step": "+1.0%", "revenue_impact": round(base_bal * 0.01, 2), "profit_impact": round(base_nim * 0.01, 2), "is_supported": True}],
                assumptions_statement="Financial Simulation Assumptions: Yield calculations use a 3.5% baseline net interest margin.",
                supported_interventions=["Asset Volume Growth", "Yield / Spread Optimization", "Operating Cost Efficiency"],
                scenario_domain="financial",
                scenario_domain_label="Banking & Financial Services",
                is_scenario_supported=True,
                outcome_cards=outcome_cards,
                active_levers=active_levers,
                chart_config=chart_config,
            )

        # -------------------------------------------------------------
        # DOMAIN 5: GENERAL / UNFAMILIAR
        # -------------------------------------------------------------
        if caps.domain == "general":
            if caps.primary_metric and caps.primary_metric in df.columns and pd.api.types.is_numeric_dtype(df[caps.primary_metric]):
                m_col = caps.primary_metric
                m_label = m_col.replace("_", " ").title()
                m_unit = caps.metric_units.get(m_col, "")
                base_val = float(df[m_col].sum())
                adj_pct = params.price_change_pct
                sim_val = base_val * (1.0 + adj_pct / 100.0)
                delta = sim_val - base_val
                delta_pct = (delta / abs(base_val) * 100) if base_val != 0 else 0.0

                outcome_cards = [
                    {
                        "title": f"Simulated {m_label}",
                        "baseline": round(base_val, 2),
                        "simulated": round(sim_val, 2),
                        "delta": round(delta, 2),
                        "delta_pct": round(delta_pct, 1),
                        "unit": m_unit,
                    }
                ]
                active_levers = [
                    {
                        "id": "price_change_pct",
                        "name": f"{m_label} Adjustment",
                        "min": -30,
                        "max": 30,
                        "step": 1,
                        "default": 0,
                        "unit": "%",
                        "description": f"Adjusts {m_label} holding other parameters constant.",
                    }
                ]
                chart_config = {
                    "domain": "general",
                    "charts": [
                        {
                            "title": card["title"],
                            "unit": card["unit"],
                            "baseline": card["baseline"],
                            "simulated": card["simulated"],
                            "delta": card["delta"],
                        }
                        for card in outcome_cards
                    ],
                }
                insights = [f"Adjusting {m_label} by {adj_pct:+.1f}% shifts projected metric value by {delta:+,.2f} {m_unit}."]

                return SimulationOutcome(
                    baseline_revenue=round(base_val, 2),
                    simulated_revenue=round(sim_val, 2),
                    revenue_delta=round(delta, 2),
                    revenue_delta_pct=round(delta_pct, 2),
                    baseline_profit=0.0,
                    simulated_profit=0.0,
                    profit_delta=0.0,
                    profit_delta_pct=0.0,
                    baseline_margin_pct=0.0,
                    simulated_margin_pct=0.0,
                    margin_delta_pct=0.0,
                    simulation_insights=insights,
                    net_economic_value_added=round(delta, 2),
                    risk_adjusted_return=round(delta * 0.85, 2),
                    sensitivity_breakdown={f"{m_col}_sensitivity_per_pct": round(base_val * 0.01, 2)},
                    recommendation_impact_overlap=[],
                    sensitivity_table=[{"lever": f"{m_label} Adjustment", "step": "+1.0%", "revenue_impact": round(base_val * 0.01, 2), "profit_impact": 0.0, "is_supported": True}],
                    assumptions_statement=f"General simulation adjusts {m_label} proportionally without assuming financial or retail structures.",
                    supported_interventions=[f"{m_label} Adjustment"],
                    scenario_domain="general",
                    scenario_domain_label="General Analytics",
                    is_scenario_supported=True,
                    outcome_cards=outcome_cards,
                    active_levers=active_levers,
                    chart_config=chart_config,
                )
            else:
                reason = "What-If scenario simulation is unavailable for this dataset because required decision levers and controllable outcome variables were not detected."
                return SimulationOutcome(
                    baseline_revenue=0.0,
                    simulated_revenue=0.0,
                    revenue_delta=0.0,
                    revenue_delta_pct=0.0,
                    baseline_profit=0.0,
                    simulated_profit=0.0,
                    profit_delta=0.0,
                    profit_delta_pct=0.0,
                    baseline_margin_pct=0.0,
                    simulated_margin_pct=0.0,
                    margin_delta_pct=0.0,
                    simulation_insights=[reason],
                    net_economic_value_added=0.0,
                    risk_adjusted_return=0.0,
                    sensitivity_breakdown={},
                    recommendation_impact_overlap=[],
                    sensitivity_table=[],
                    assumptions_statement=reason,
                    supported_interventions=[],
                    scenario_domain=caps.domain,
                    scenario_domain_label=caps.domain_label,
                    is_scenario_supported=False,
                    unsupported_reason=reason,
                    outcome_cards=[],
                    active_levers=[],
                    chart_config=None,
                )

        # -------------------------------------------------------------
        # DOMAIN 6: RETAIL & E-COMMERCE (DEFAULT)
        # -------------------------------------------------------------
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

        outcome_cards = [
            {
                "title": "Gross Revenue",
                "baseline": round(baseline_revenue, 2),
                "simulated": round(simulated_revenue, 2),
                "delta": round(rev_delta, 2),
                "delta_pct": round(rev_delta_pct, 1),
                "unit": "$",
            },
            {
                "title": "Net Profit",
                "baseline": round(baseline_profit, 2),
                "simulated": round(simulated_profit, 2),
                "delta": round(profit_delta, 2),
                "delta_pct": round(profit_delta_pct, 1),
                "unit": "$",
            },
            {
                "title": "Profit Margin",
                "baseline": baseline_margin_pct,
                "simulated": simulated_margin_pct,
                "delta": margin_delta_pct,
                "delta_pct": 0.0,
                "unit": "%",
            },
        ]

        active_levers = [
            {
                "id": "price_change_pct",
                "name": "Price Change",
                "min": -30,
                "max": 30,
                "step": 1,
                "default": 0,
                "unit": "%",
                "description": "Adjust product pricing holding volume constant.",
            },
            {
                "id": "volume_change_pct",
                "name": "Sales Volume Change",
                "min": -30,
                "max": 30,
                "step": 1,
                "default": 0,
                "unit": "%",
                "description": "Adjust sales volume scaling variable costs proportionally.",
            },
        ]
        if has_discount:
            active_levers.append({
                "id": "discount_adjustment_pct",
                "name": "Discount Change",
                "min": -20,
                "max": 20,
                "step": 1,
                "default": 0,
                "unit": "%",
                "description": "Adjust promotional discount rate to recapture gross profit.",
            })
        if has_cost and baseline_costs > 0:
            active_levers.append({
                "id": "operational_efficiency_pct",
                "name": "Cost Efficiency",
                "min": 0,
                "max": 20,
                "step": 1,
                "default": 0,
                "unit": "%",
                "description": "Reduce baseline operating costs directly.",
            })

        chart_config = {
            "domain": "retail",
            "charts": [
                {
                    "title": card["title"],
                    "unit": card["unit"],
                    "baseline": card["baseline"],
                    "simulated": card["simulated"],
                    "delta": card["delta"],
                }
                for card in outcome_cards
            ],
        }

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
            supported_interventions=supported_interventions,
            scenario_domain="retail",
            scenario_domain_label="Retail & E-Commerce",
            is_scenario_supported=True,
            outcome_cards=outcome_cards,
            active_levers=active_levers,
            chart_config=chart_config,
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
        Supports retail, workforce, manufacturing, saas, financial, and general domains.
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

        # 1. Price Change
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
                "churn_mitigation_pct": 0.0,
                "parameter_type": "percentage",
            }

        # 2. Sales Volume Change / Throughput / Asset Volume Growth
        elif norm_type in ["sales volume change", "sales volume", "volume change", "volume", "throughput optimization", "asset volume growth", "asset growth"]:
            if parameter_type == "percentage_points":
                raise ValueError("Sales volume change must be specified as a percentage change (%), not percentage points.")
            if change_value < -100.0:
                raise ValueError("Sales volume change percentage cannot be less than -100% (sales volume cannot be negative).")
            if change_value > 500.0:
                raise ValueError("Sales volume change exceeds the maximum supported threshold (+500%).")
            return {
                "intervention_type": intervention_type.strip().title(),
                "price_change_pct": 0.0,
                "volume_change_pct": float(change_value),
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": 0.0,
                "parameter_type": "percentage",
            }

        # 3. Operating Cost Reduction / Downtime Reduction / HR Efficiency
        elif norm_type in ["operating cost reduction", "cost reduction", "cost efficiency", "operational efficiency", "downtime reduction", "hr program cost efficiency", "hr efficiency"]:
            if not has_cost:
                raise ValueError("Operating Cost Reduction is unsupported: dataset lacks valid cost or profit data.")
            if parameter_type == "percentage_points":
                raise ValueError("Cost reduction must be specified as a percentage change (%), not percentage points.")
            if change_value < 0.0:
                raise ValueError("Operating cost reduction percentage cannot be negative (must be >= 0%).")
            if change_value > 100.0:
                raise ValueError("Operating cost reduction percentage cannot exceed 100%.")
            return {
                "intervention_type": intervention_type.strip().title(),
                "price_change_pct": 0.0,
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": float(change_value),
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": 0.0,
                "parameter_type": "percentage",
            }

        # 4. Discount Change
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
                "churn_mitigation_pct": 0.0,
                "parameter_type": parameter_type,
            }

        # 5. Attrition Reduction / Churn Rate Reduction / Defect Rate Reduction
        elif norm_type in ["attrition reduction", "workforce retention", "churn rate reduction", "churn reduction", "customer retention", "defect rate reduction", "defect reduction"]:
            if change_value < 0.0:
                raise ValueError("Reduction percentage cannot be negative (must be >= 0%).")
            if change_value > 100.0:
                raise ValueError("Reduction percentage cannot exceed 100%.")
            return {
                "intervention_type": intervention_type.strip().title(),
                "price_change_pct": 0.0,
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": float(change_value),
                "parameter_type": "percentage",
            }

        # 6. Job Satisfaction Improvement / Account Expansion / Yield Optimization
        elif norm_type in ["job satisfaction improvement", "satisfaction improvement", "account expansion", "account expansion / arpu uplift", "arpu uplift", "yield optimization", "yield / spread optimization", "spread optimization"]:
            if change_value < -50.0:
                raise ValueError("Adjustment cannot be less than -50%.")
            if change_value > 100.0:
                raise ValueError("Adjustment cannot exceed +100%.")
            return {
                "intervention_type": intervention_type.strip().title(),
                "price_change_pct": float(change_value),
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": 0.0,
                "parameter_type": "percentage",
            }

        # 7. General Metric Adjustment
        elif "adjustment" in norm_type or (target_col and norm_type in target_col.lower()):
            if change_value < -100.0:
                raise ValueError("Adjustment percentage cannot be less than -100%.")
            if change_value > 500.0:
                raise ValueError("Adjustment percentage exceeds the maximum threshold (+500%).")
            return {
                "intervention_type": intervention_type.strip().title(),
                "price_change_pct": float(change_value),
                "volume_change_pct": 0.0,
                "operational_efficiency_pct": 0.0,
                "discount_adjustment_pct": 0.0,
                "churn_mitigation_pct": 0.0,
                "parameter_type": "percentage",
            }

        else:
            raise ValueError(
                f"Unsupported intervention type '{intervention_type}'. "
                "Supported types: Price Change, Sales Volume Change, Operating Cost Reduction, Discount Change, "
                "Attrition Reduction, Job Satisfaction Improvement, Defect Rate Reduction, Downtime Reduction, Churn Rate Reduction."
            )

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
            elif params.get("churn_mitigation_pct") is not None and params.get("churn_mitigation_pct") != 0:
                intervention_summary = f"Attrition/Churn Reduction: +{params.get('churn_mitigation_pct'):g}%"

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
