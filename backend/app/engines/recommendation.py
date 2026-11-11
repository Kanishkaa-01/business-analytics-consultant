import re
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from app.models.schemas import (
    RecommendationItem,
    DiagnosticReport,
    RootCauseReport,
    RisksAndOpportunitiesReport,
)


class RecommendationEngine:
    @staticmethod
    def _is_date_str(val: str) -> bool:
        if not val or not isinstance(val, str):
            return False
        # Matches YYYY-MM, YYYY-MM-DD, etc.
        return bool(re.match(r'^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$', val.strip()))

    @staticmethod
    def calculate_priority_score(
        impact_score: float,
        confidence_score: float,
        ease_score: float,
        severity_score: Optional[float] = None
    ) -> float:
        """
        Phase 14: Deterministic Priority Score Formula.
        Transparent scoring based on 4 measurable dimensions:
        - Impact (40%)
        - Evidence / Confidence (25%)
        - Ease / Feasibility (20%)
        - Severity (15%)
        Normalized to 0–100 scale:
        Priority Score = (impact * 10)*0.40 + (confidence * 10)*0.25 + (ease * 10)*0.20 + (severity * 10)*0.15
        """
        # Guardrails for None or out-of-bound inputs
        imp = max(1.0, min(10.0, float(impact_score if impact_score is not None else 5.0)))
        conf = max(1.0, min(10.0, float(confidence_score if confidence_score is not None else 5.0)))
        ease = max(1.0, min(10.0, float(ease_score if ease_score is not None else 5.0)))
        sev = max(1.0, min(10.0, float(severity_score if severity_score is not None else 7.0)))

        score = (imp * 10.0) * 0.40 + (conf * 10.0) * 0.25 + (ease * 10.0) * 0.20 + (sev * 10.0) * 0.15
        return round(min(100.0, max(0.0, score)), 1)

    @staticmethod
    def get_priority_level(score: float) -> str:
        """
        Phase 14 Priority Levels:
        80–100: High Priority
        60–79: Medium Priority
        0–59: Lower Priority
        """
        if score >= 80.0:
            return "High Priority"
        elif score >= 60.0:
            return "Medium Priority"
        else:
            return "Lower Priority"

    @staticmethod
    def format_metric_value(val: Optional[float], target_col: str, include_sign: bool = False) -> str:
        if val is None:
            return "N/A"
        clean_target = str(target_col).lower()
        is_money = any(k in clean_target for k in ["revenue", "sales", "price", "profit", "amount", "cost", "income", "salary", "arr", "mrr", "wage", "cogs", "spend", "scrap_cost"])
        is_pct = any(k in clean_target for k in ["pct", "percent", "percentage", "rate", "margin", "ratio", "attrition", "churn", "defect"])
        is_time = any(k in clean_target for k in ["hour", "minute", "day", "cycle_time", "downtime", "duration"])

        if is_money:
            if include_sign:
                return f"{'+$' if val >= 0 else '-$'}{abs(val):,.2f}"
            return f"${val:,.2f}"
        elif is_pct:
            sign = ("+" if val > 0 else "") if include_sign else ""
            return f"{sign}{val:.1f}%"
        elif is_time:
            unit = "hrs" if "hour" in clean_target else ("mins" if "min" in clean_target else "days")
            sign = ("+" if val > 0 else "") if include_sign else ""
            return f"{sign}{val:,.1f} {unit}"
        else:
            sign = ("+" if val > 0 else "") if include_sign else ""
            return f"{sign}{val:,.2f}"

    @staticmethod
    def format_impact_label(gain_val: float, target_col: str, label_type: str = "improvement") -> str:
        clean_target = str(target_col).lower()
        is_money = any(k in clean_target for k in ["revenue", "sales", "price", "profit", "amount", "cost", "income", "salary", "arr", "mrr", "wage", "cogs", "spend", "scrap_cost"])
        is_pct = any(k in clean_target for k in ["pct", "percent", "percentage", "rate", "margin", "ratio", "attrition", "churn", "defect"])
        is_time = any(k in clean_target for k in ["hour", "minute", "day", "cycle_time", "downtime", "duration"])

        if is_money:
            return f"Estimated {label_type}: ~${gain_val:,.2f}"
        elif is_pct:
            return f"Estimated {label_type}: ~{gain_val:.1f}% variance reduction"
        elif is_time:
            unit = "hrs" if "hour" in clean_target else ("mins" if "min" in clean_target else "days")
            return f"Estimated {label_type}: ~{gain_val:,.1f} {unit} reduction"
        else:
            return f"Estimated {label_type}: ~{gain_val:,.1f} units optimization"

    @staticmethod
    def generate_prioritized_recommendations(
        target_col: str,
        diagnostic: DiagnosticReport,
        root_cause: RootCauseReport,
        risk_opp: RisksAndOpportunitiesReport
    ) -> List[RecommendationItem]:
        """
        Answers Question 3: 'What could we do?'
        Generates understandable, domain-appropriate recommended actions ranked by Priority Score
        (Impact × Evidence Strength × Ease, normalized to 0–100).
        """
        recommendations: List[RecommendationItem] = []
        clean_t = str(target_col).lower()
        is_workforce = any(k in clean_t for k in ["attrition", "turnover", "employee", "headcount", "resigned", "satisfaction"])
        is_mfg = any(k in clean_t for k in ["defect", "scrap", "downtime", "cycle_time", "yield", "batch"])
        is_saas = any(k in clean_t for k in ["churn", "arr", "mrr", "subscription", "ticket", "dau", "mau"])

        # -------------------------------------------------------------
        # Action 1: Improve Underperforming Areas
        # -------------------------------------------------------------
        drag_items = [b for b in diagnostic.variance_breakdown if b.direction == "Drag"]
        primary_drag = drag_items[0] if drag_items else None
        primary_factor = root_cause.factor_contributions[0] if root_cause.factor_contributions else None

        if primary_drag:
            seg_label = primary_drag.segment
            if RecommendationEngine._is_date_str(seg_label):
                seg_display = f"Recent Period (Historical observation: {seg_label})"
            else:
                seg_display = f"'{seg_label}'"

            expected_gain = round(abs(primary_drag.variance) * 0.60, 2)
            impact_score = min(9.5, max(5.0, round((expected_gain / max(1.0, abs(diagnostic.total_variance))) * 10, 1)))
            confidence_score = round(root_cause.statistical_confidence_level / 10.0, 1)
            ease_score = 6.5
            priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=8.5)
            priority_level = RecommendationEngine.get_priority_level(priority_score)

            diff_str = RecommendationEngine.format_metric_value(primary_drag.variance, target_col, include_sign=True)
            base_str = RecommendationEngine.format_metric_value(primary_drag.baseline_value, target_col)
            act_str = RecommendationEngine.format_metric_value(primary_drag.actual_value, target_col)
            evidence_text = f"Baseline: {base_str} -> Actual: {act_str} (Difference: {diff_str})"

            if is_workforce:
                action_title = f"Mitigate Workforce Turnover in {seg_display}"
                what_to_do = f"Conduct retention interviews, review workload distribution, and address career development in {seg_display}."
                why = f"This segment accounts for {primary_drag.contribution_share_pct:.1f}% of the negative variation ({diff_str})."
                impact_label = RecommendationEngine.format_impact_label(expected_gain, target_col, "retention improvement")
            elif is_mfg:
                action_title = f"Reduce Defect Rate & Losses in {seg_display}"
                what_to_do = f"Standardize machine calibration, inspect raw materials, and review operator workflows in {seg_display}."
                why = f"This segment contributes {primary_drag.contribution_share_pct:.1f}% of the total negative difference ({diff_str})."
                impact_label = RecommendationEngine.format_impact_label(expected_gain, target_col, "quality recovery")
            elif is_saas:
                action_title = f"Improve Account Retention in {seg_display}"
                what_to_do = f"Deploy proactive customer success interventions and onboarding check-ins for accounts in {seg_display}."
                why = f"This segment contributes {primary_drag.contribution_share_pct:.1f}% of total negative churn variation ({diff_str})."
                impact_label = RecommendationEngine.format_impact_label(expected_gain, target_col, "retention recovery")
            else:
                action_title = f"Improve Operations in {seg_display}"
                what_to_do = f"Standardize operations, review commercial terms, and improve workflows in {seg_display}."
                why = f"This segment contributes {primary_drag.contribution_share_pct:.1f}% of the total negative difference ({diff_str})."
                impact_label = RecommendationEngine.format_impact_label(expected_gain, target_col, "recovery")

            recommendations.append(RecommendationItem(
                id="REC-001",
                title=action_title,
                urgency="Immediate (0–30 days)",
                category="Improve Underperforming Areas",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    f"Operational review with team leads for {primary_drag.dimension}",
                    "Set clear minimum performance targets",
                    "Weekly progress check-in"
                ],
                expected_financial_impact=expected_gain,
                implementation_effort="Medium",
                confidence_score_pct=round(root_cause.statistical_confidence_level, 1),
                impact_score=impact_score,
                confidence_score=confidence_score,
                ease_score=ease_score,
                priority_score=priority_score,
                priority_tier=priority_level,
                priority_level=priority_level,
                tradeoffs_and_risks="Requires management time and team effort during initial changes.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=impact_label,
                difficulty="Medium (Requires coordination across teams)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Temporary operational slowdown while processes adjust.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Segment comparison: negative difference of {diff_str} ({primary_drag.contribution_share_pct:.1f}% share).",
                decision_status="Pending Review"
            ))

        # -------------------------------------------------------------
        # Action 2: Domain-Aware Risk Mitigation
        # -------------------------------------------------------------
        margin_risks = [r for r in risk_opp.risks if r.category == "Margin Compression"]
        concentration_risks = [r for r in risk_opp.risks if r.category == "Concentration"]

        if margin_risks:
            focal_risk = margin_risks[0]
            expected_savings = round(focal_risk.estimated_financial_exposure * 0.70, 2)
            impact_score = min(9.0, max(5.5, round((expected_savings / max(1.0, abs(diagnostic.total_variance))) * 10, 1)))
            confidence_score = 8.5
            ease_score = 8.0
            priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=8.0)
            priority_level = RecommendationEngine.get_priority_level(priority_score)

            exp_str = RecommendationEngine.format_metric_value(focal_risk.estimated_financial_exposure, target_col)

            if is_workforce:
                rec_title = "Implement Targeted Retention & Engagement Programs"
                what_to_do = "Conduct employee stay interviews, review compensation equity, and address burnout drivers in high-risk departments."
                why = "Observed elevated turnover exposure in critical workforce segments."
                evidence_text = f"Identified estimated {exp_str} in potential replacement and turnover exposure."
                impact_label = RecommendationEngine.format_impact_label(expected_savings, target_col, "savings from retention")
            elif is_mfg:
                rec_title = "Establish Preventive Maintenance & Material Controls"
                what_to_do = "Schedule regular machine servicing and enforce strict tolerance standards for incoming raw materials."
                why = "Elevated defect and downtime rates generate excessive scrap waste and production delays."
                evidence_text = f"Identified estimated {exp_str} in potential scrap and downtime loss."
                impact_label = RecommendationEngine.format_impact_label(expected_savings, target_col, "scrap cost reduction")
            elif is_saas:
                rec_title = "Deploy Proactive Customer Health Monitoring"
                what_to_do = "Monitor account usage trends and establish early-warning alerts for declining active users or ticket spikes."
                why = "Account churn risk leads to recurring revenue contraction."
                evidence_text = f"Identified estimated {exp_str} in contract value at risk."
                impact_label = RecommendationEngine.format_impact_label(expected_savings, target_col, "churn mitigation")
            else:
                rec_title = "Establish Clear Pricing & Discount Controls"
                what_to_do = "Set clear discount limits and require manager authorization for commercial concessions."
                why = "High discounts reduce net margin capture without generating proportionate transaction volume."
                evidence_text = f"Identified estimated {exp_str} in potential margin leakage."
                impact_label = RecommendationEngine.format_impact_label(expected_savings, target_col, "margin protection")

            recommendations.append(RecommendationItem(
                id="REC-002",
                title=rec_title,
                urgency="Immediate (0–30 days)",
                category="Risk Mitigation",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Update guidelines and standard operating rules",
                    "Brief relevant team leads on exception thresholds",
                    "Weekly review meeting"
                ],
                expected_financial_impact=expected_savings,
                implementation_effort="Low",
                confidence_score_pct=85.0,
                impact_score=impact_score,
                confidence_score=confidence_score,
                ease_score=ease_score,
                priority_score=priority_score,
                priority_tier=priority_level,
                priority_level=priority_level,
                tradeoffs_and_risks="Requires management discipline and consistent enforcement.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=impact_label,
                difficulty="Low (Policy update and guideline adjustment)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="May require adjustment period across teams.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=evidence_text,
                decision_status="Pending Review"
            ))
        elif concentration_risks:
            focal_risk = concentration_risks[0]
            expected_impact = round(focal_risk.estimated_financial_exposure * 0.50, 2)
            impact_score = min(9.0, max(5.0, round((expected_impact / max(1.0, abs(diagnostic.total_variance))) * 10, 1)))
            confidence_score = 8.0
            ease_score = 6.5
            priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=7.5)
            priority_level = RecommendationEngine.get_priority_level(priority_score)

            exp_str = RecommendationEngine.format_metric_value(focal_risk.estimated_financial_exposure, target_col)
            what_to_do = "Develop secondary distribution segments and regional accounts to mitigate concentration exposure."
            why = "High volume concentration exposes operations to significant vulnerability if primary conditions fluctuate."
            evidence_text = f"Identified concentration risk with ~{exp_str} in exposed volume."
            impact_label = RecommendationEngine.format_impact_label(expected_impact, target_col, "risk mitigation")

            recommendations.append(RecommendationItem(
                id="REC-002",
                title="Diversify Distribution & Segment Mix",
                urgency="Near Term (30–90 days)",
                category="Risk Mitigation",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Analyze geographic and channel penetration in secondary segments",
                    "Establish regional growth incentives"
                ],
                expected_financial_impact=expected_impact,
                implementation_effort="Medium",
                confidence_score_pct=80.0,
                impact_score=impact_score,
                confidence_score=confidence_score,
                ease_score=ease_score,
                priority_score=priority_score,
                priority_tier=priority_level,
                priority_level=priority_level,
                tradeoffs_and_risks="Requires strategic channel development and dedicated resource allocation.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=impact_label,
                difficulty="Medium (Requires coordination across commercial teams)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Takes time to establish traction in new markets.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"High concentration identified across primary segment ({focal_risk.title}).",
                decision_status="Pending Review"
            ))

        # -------------------------------------------------------------
        # Action 3: Growth Opportunity
        # -------------------------------------------------------------
        lift_items = [b for b in diagnostic.variance_breakdown if b.direction == "Lift"]
        if lift_items:
            top_lift = lift_items[0]
            seg_label = top_lift.segment
            if RecommendationEngine._is_date_str(seg_label):
                seg_display = f"Peak Growth Period (Historical observation: {seg_label})"
            else:
                seg_display = f"'{seg_label}'"

            projected_lift = round(abs(top_lift.variance) * 1.25, 2)
            impact_score = 7.5
            confidence_score = 8.0
            ease_score = 7.0
            priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=6.0)
            priority_level = RecommendationEngine.get_priority_level(priority_score)

            diff_str = RecommendationEngine.format_metric_value(top_lift.variance, target_col, include_sign=True)
            base_str = RecommendationEngine.format_metric_value(top_lift.baseline_value, target_col)
            act_str = RecommendationEngine.format_metric_value(top_lift.actual_value, target_col)
            evidence_text = f"Baseline: {base_str} -> Actual: {act_str} ({diff_str})"
            impact_label = RecommendationEngine.format_impact_label(projected_lift, target_col, "growth potential")

            what_to_do = f"Allocate additional inventory, marketing, and attention to {seg_display}."
            why = f"This area showed strong positive performance ({diff_str}) and represents a clear opportunity."

            recommendations.append(RecommendationItem(
                id="REC-003",
                title=f"Support Growth in {seg_display}",
                urgency="Near Term (30–90 days)",
                category="Growth Opportunity",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Check capacity and resource availability",
                    "Allocate focus toward high-performing segment"
                ],
                expected_financial_impact=projected_lift,
                implementation_effort="Medium",
                confidence_score_pct=80.0,
                impact_score=impact_score,
                confidence_score=confidence_score,
                ease_score=ease_score,
                priority_score=priority_score,
                priority_tier=priority_level,
                priority_level=priority_level,
                tradeoffs_and_risks="Ensure supply capacity can keep up with additional demand.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=impact_label,
                difficulty="Medium (Requires operational planning)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Demand might level off if segment becomes saturated.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Segment comparison positive variance ({diff_str}).",
                decision_status="Pending Review"
            ))

        # -------------------------------------------------------------
        # Action 4: Focus on Biggest Contributors
        # -------------------------------------------------------------
        vital_few = [p for p in root_cause.pareto_breakdown if p.is_vital_few]
        if vital_few:
            vital_names = ", ".join([v.entity for v in vital_few[:3]])
            impact_score = 7.0
            confidence_score = 7.5
            ease_score = 6.0
            total_impact_val = sum(v.loss_or_impact for v in vital_few[:3])
            expected_impact = round(total_impact_val * 0.40, 2)
            priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=7.0)
            priority_level = RecommendationEngine.get_priority_level(priority_score)

            tot_str = RecommendationEngine.format_metric_value(total_impact_val, target_col)
            impact_label = RecommendationEngine.format_impact_label(expected_impact, target_col, "potential recovery")

            what_to_do = f"Focus reviews on the biggest individual contributors ({vital_names})."
            why = f"These top {len(vital_few[:3])} areas represent the largest share of the total difference."
            evidence_text = f"Top areas combined represent {tot_str} in observed variance."

            recommendations.append(RecommendationItem(
                id="REC-004",
                title=f"Focus on Top Contributors ({vital_names})",
                urgency="Near Term (30–90 days)",
                category="Focus on Biggest Contributors",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Review specific accounts, categories, or items",
                    "Discuss solutions directly with area owners"
                ],
                expected_financial_impact=expected_impact,
                implementation_effort="Medium",
                confidence_score_pct=75.0,
                impact_score=impact_score,
                confidence_score=confidence_score,
                ease_score=ease_score,
                priority_score=priority_score,
                priority_tier=priority_level,
                priority_level=priority_level,
                tradeoffs_and_risks="May require difficult conversations or operational adjustments.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=impact_label,
                difficulty="Medium",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Stakeholder relationship considerations during operational review.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Top areas represent {tot_str} in observed variance.",
                decision_status="Pending Review"
            ))

        # -------------------------------------------------------------
        # Action 5: Monitor Unusual Changes
        # -------------------------------------------------------------
        expected_mon_impact = round(abs(diagnostic.total_variance) * 0.20, 2)
        impact_score = 6.0
        confidence_score = 9.0
        ease_score = 9.0
        priority_score = RecommendationEngine.calculate_priority_score(impact_score, confidence_score, ease_score, severity_score=5.0)
        priority_level = RecommendationEngine.get_priority_level(priority_score)

        tot_diff_str = RecommendationEngine.format_metric_value(abs(diagnostic.total_variance), target_col)
        early_det_label = RecommendationEngine.format_impact_label(expected_mon_impact, target_col, "early detection value")

        recommendations.append(RecommendationItem(
            id="REC-005",
            title="Monitor Unusual Changes in Key Metrics",
            urgency="Long Term (90+ days)",
            category="Monitor Unusual Changes",
            mechanism_of_action="Set up periodic checks to flag when a metric changes significantly from expected averages.",
            rationale="Catches unexpected deviations early rather than waiting for quarterly reviews.",
            prerequisites=[
                "Define metric review schedule",
                "Assign owners for metric check-ins"
            ],
            expected_financial_impact=expected_mon_impact,
            implementation_effort="Low",
            confidence_score_pct=90.0,
            impact_score=impact_score,
            confidence_score=confidence_score,
            ease_score=ease_score,
            priority_score=priority_score,
            priority_tier=priority_level,
            priority_level=priority_level,
            tradeoffs_and_risks="Ensure alert thresholds are balanced so managers are not overwhelmed with notifications.",
            status="Pending Review",
            what_to_do="Set up periodic automated checks to flag significant metric variations.",
            why="Early detection prevents minor anomalies from compounding into large operational or commercial problems.",
            evidence_text=f"Total observed difference across data was {tot_diff_str}.",
            expected_impact_label=early_det_label,
            difficulty="Low (Simple tracking dashboard / checklist)",
            priority_label=f"Priority Score: {priority_score}/100",
            possible_risk="Notification fatigue if thresholds are set too sensitively.",
            recommendation="Set up periodic automated checks to flag significant metric variations.",
            reason="Early detection prevents minor anomalies from compounding into large operational or commercial problems.",
            supporting_finding=f"Total observed difference across data was {tot_diff_str}.",
            decision_status="Pending Review"
        ))

        # Sort by Priority Score descending
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        return recommendations
