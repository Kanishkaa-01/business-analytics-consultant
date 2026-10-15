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
    def generate_prioritized_recommendations(
        target_col: str,
        diagnostic: DiagnosticReport,
        root_cause: RootCauseReport,
        risk_opp: RisksAndOpportunitiesReport
    ) -> List[RecommendationItem]:
        """
        Answers Question 3: 'What could we do?'
        Generates understandable, explainable recommended actions ranked by Priority Score
        (Impact × Evidence Strength × Ease, normalized to 0–100).
        """
        recommendations: List[RecommendationItem] = []

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

            what_to_do = f"Standardize operations, review sales terms, and improve workflows in {seg_display}."
            why = f"This segment contributes {primary_drag.contribution_share_pct}% of the total negative difference ({primary_drag.variance:+.2f})."
            evidence_text = f"Baseline: ${primary_drag.baseline_value:,.2f} -> Actual: ${primary_drag.actual_value:,.2f} (Difference: {primary_drag.variance:+.2f})"

            recommendations.append(RecommendationItem(
                id="REC-001",
                title=f"Improve Operations in {seg_display}",
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
                expected_impact_label=f"Estimated improvement: ~${expected_gain:,.2f} recovery",
                difficulty="Medium (Requires coordination across teams)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Temporary operational slowdown while processes adjust.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Segment comparison: negative difference of {primary_drag.variance:+.2f} ({primary_drag.contribution_share_pct}% share).",
                decision_status="Pending Review"
            ))

        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # Action 2: Discount Control OR Concentration Mitigation (Dataset-Aware)
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

            what_to_do = "Set clear discount limits and require manager authorization for commercial concessions."
            why = "High discounts reduce net margin capture without generating proportionate transaction volume."
            evidence_text = f"Identified estimated ${focal_risk.estimated_financial_exposure:,.2f} in potential margin leakage."

            recommendations.append(RecommendationItem(
                id="REC-002",
                title="Establish Clear Discount Controls",
                urgency="Immediate (0–30 days)",
                category="Discount Control",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Update discount guidelines and approval rules",
                    "Brief the sales team on standard discount limits",
                    "Weekly discount exception review"
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
                tradeoffs_and_risks="Sales reps may experience slight pushback from customers expecting large discounts.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=f"Estimated savings: ~${expected_savings:,.2f}",
                difficulty="Low (Policy update and guideline adjustment)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="May require negotiation training for sales team.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Identified estimated ${focal_risk.estimated_financial_exposure:,.2f} in potential margin leakage.",
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

            what_to_do = "Develop secondary distribution markets and regional customer accounts to mitigate concentration exposure."
            why = "High volume concentration exposes operations to significant vulnerability if primary market conditions fluctuate."
            evidence_text = f"Identified concentration risk with ~${focal_risk.estimated_financial_exposure:,.2f} in exposed volume."

            recommendations.append(RecommendationItem(
                id="REC-002",
                title="Diversify Distribution & Segment Mix",
                urgency="Near Term (30–90 days)",
                category="Risk Mitigation",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Analyze geographic and channel penetration in secondary regions",
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
                expected_impact_label=f"Estimated risk mitigation: ~${expected_impact:,.2f}",
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

            what_to_do = f"Allocate additional inventory, marketing, and attention to {seg_display}."
            why = f"This area showed strong positive performance (+{top_lift.variance:,.2f}) and represents a clear opportunity."
            evidence_text = f"Baseline: ${top_lift.baseline_value:,.2f} -> Actual: ${top_lift.actual_value:,.2f} (+{top_lift.variance:,.2f})"

            recommendations.append(RecommendationItem(
                id="REC-003",
                title=f"Support Growth in {seg_display}",
                urgency="Near Term (30–90 days)",
                category="Growth Opportunity",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Check inventory availability and supply capacity",
                    "Allocate marketing resources toward high-performing segment"
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
                expected_impact_label=f"Estimated growth potential: ~${projected_lift:,.2f}",
                difficulty="Medium (Requires supply planning)",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Demand might level off if market becomes saturated.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Segment comparison positive variance (+${top_lift.variance:,.2f}).",
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

            what_to_do = f"Focus reviews on the biggest individual contributors ({vital_names})."
            why = f"These top {len(vital_few[:3])} areas represent the largest share of the total difference."
            evidence_text = f"Top areas combined represent ${total_impact_val:,.2f} in observed variance."

            recommendations.append(RecommendationItem(
                id="REC-004",
                title=f"Focus on Top Contributors ({vital_names})",
                urgency="Near Term (30–90 days)",
                category="Focus on Biggest Contributors",
                mechanism_of_action=what_to_do,
                rationale=why,
                prerequisites=[
                    "Review specific accounts or SKUs",
                    "Discuss solutions directly with category managers"
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
                tradeoffs_and_risks="May require difficult contract conversations or product changes.",
                status="Pending Review",
                what_to_do=what_to_do,
                why=why,
                evidence=evidence_text,
                expected_impact_label=f"Estimated potential recovery: ~${expected_impact:,.2f}",
                difficulty="Medium",
                priority_label=f"Priority Score: {priority_score}/100",
                possible_risk="Customer relationship considerations during contract review.",
                recommendation=what_to_do,
                reason=why,
                supporting_finding=f"Top areas represent ${total_impact_val:,.2f} in observed variance.",
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

        recommendations.append(RecommendationItem(
            id="REC-005",
            title="Monitor Unusual Changes in Key Metrics",
            urgency="Long Term (90+ days)",
            category="Monitor Unusual Changes",
            mechanism_of_action="Set up monthly checks to flag when a metric changes significantly from expected averages.",
            rationale="Catches unexpected drops or margin declines early rather than waiting for quarterly reviews.",
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
            what_to_do="Set up monthly automated checks to flag significant metric variations.",
            why="Early detection prevents minor issues from compounding into large financial losses.",
            evidence_text=f"Total observed difference across data was ${abs(diagnostic.total_variance):,.2f}.",
            expected_impact_label=f"Estimated value from early detection: ~${expected_mon_impact:,.2f}",
            difficulty="Low (Simple tracking dashboard / checklist)",
            priority_label=f"Priority Score: {priority_score}/100",
            possible_risk="Notification fatigue if thresholds are set too sensitively.",
            recommendation="Set up monthly automated checks to flag significant metric variations.",
            reason="Early detection prevents minor issues from compounding into large financial losses.",
            supporting_finding=f"Total observed difference across data was ${abs(diagnostic.total_variance):,.2f}.",
            decision_status="Pending Review"
        ))

        # Sort by Priority Score descending
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        return recommendations
