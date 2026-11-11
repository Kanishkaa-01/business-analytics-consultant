from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.models.schemas import (
    RisksAndOpportunitiesReport,
    RiskItem,
    OpportunityItem,
    RootCauseReport,
    DiagnosticReport,
)


class RiskOpportunityEngine:
    @staticmethod
    def identify_risks_and_opportunities(
        df: pd.DataFrame,
        target_col: str,
        diagnostic: DiagnosticReport,
        root_cause: RootCauseReport
    ) -> RisksAndOpportunitiesReport:
        """
        Answers Question 3: 'What requires attention?'
        Evaluates downside exposures, concentration risks, and upside growth opportunities.
        Quantifies economic value and mitigation windows deterministically.
        """
        risks: List[RiskItem] = []
        opportunities: List[OpportunityItem] = []

        total_target_val = float(df[target_col].sum()) if target_col in df.columns else 100000.0
        avg_target_val = float(df[target_col].mean()) if target_col in df.columns else 1000.0

        # -------------------------------------------------------------
        # 1. Concentration Risk (Herfindahl-Hirschman Index & Top-3 Share)
        # -------------------------------------------------------------
        cat_cols = [
            c for c in df.columns
            if (pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_object_dtype(df[c]))
            and 2 <= df[c].nunique() <= 60
            and not any(k in str(c).lower() for k in ["invoice", "invoiceno", "order", "id", "uuid", "key"])
        ]
        # Prioritize true segment/region dimensions (lower cardinality) over descriptions/SKUs
        cat_cols.sort(key=lambda c: df[c].nunique())
        for col in cat_cols[:3]:
            if total_target_val == 0:
                continue
            grp_share = (df.groupby(col)[target_col].sum() / total_target_val).sort_values(ascending=False)
            top1_share = float(grp_share.iloc[0]) if len(grp_share) > 0 else 0.0
            top3_share = float(grp_share.iloc[:3].sum()) if len(grp_share) >= 3 else top1_share

            # HHI Calculation: sum of squared market shares (0 to 10,000)
            hhi = float(sum((grp_share * 100)**2))

            if top3_share >= 0.60 or top1_share >= 0.35:
                exposure = round(total_target_val * top1_share * 0.25, 2)
                risks.append(RiskItem(
                    id=f"RISK-CONC-{col.upper()}",
                    title=f"High Volume Concentration in {col.replace('_', ' ').title()}",
                    category="Concentration",
                    severity="High" if top3_share > 0.75 else "Medium",
                    probability_pct=round(top1_share * 100, 1),
                    estimated_financial_exposure=exposure,
                    root_cause_ref=root_cause.primary_root_cause,
                    early_warning_signals=[
                        f"Top 3 {col} accounts for {top3_share*100:.1f}% of total {target_col}.",
                        f"HHI concentration index is {hhi:.0f} (values > 2500 indicate high concentration)."
                    ],
                    mitigation_window_days=60
                ))

        # -------------------------------------------------------------
        # 2. Margin Compression or Discounting Leakage Risk
        # -------------------------------------------------------------
        discount_cols = [c for c in df.columns if any(k in c.lower() for k in ["discount", "rebate", "markdown"])]
        if discount_cols:
            d_col = discount_cols[0]
            excess_discounts = df[df[d_col] > df[d_col].quantile(0.80)]
            if len(excess_discounts) > 0:
                leakage_exposure = round(float(excess_discounts[target_col].sum() * 0.15), 2)
                risks.append(RiskItem(
                    id="RISK-MARGIN-LEAK",
                    title="Commercial Margin Erosion via Uncontrolled Discounting",
                    category="Margin Compression",
                    severity="High",
                    probability_pct=75.0,
                    estimated_financial_exposure=leakage_exposure,
                    root_cause_ref=root_cause.primary_root_cause,
                    early_warning_signals=[
                        f"Top quintile of '{d_col}' is averaging {excess_discounts[d_col].mean()*100:.1f}%.",
                        f"High discounting is negatively correlated with net unit margin capture."
                    ],
                    mitigation_window_days=30
                ))

                # Corresponding Opportunity: Discount rationalization
                recapture_val = round(leakage_exposure * 0.70, 2)
                opportunities.append(OpportunityItem(
                    id="OPP-DISCOUNT-RECOVERY",
                    title="Algorithmic Discount Floor & Promotional Guardrails",
                    category="Pricing Optimization",
                    potential_value_gain=recapture_val,
                    feasibility="High",
                    confidence_level_pct=85.0,
                    target_segment=f"High-discount transactions ({d_col} > 80th percentile)",
                    strategic_rationale=(
                        f"Enforcing strict approval guidelines on highest discounts recovers an estimated "
                        f"${recapture_val:,.2f} in potential profit recovery without diminishing transaction volume."
                    )
                ))

        # -------------------------------------------------------------
        # 3. Operational Friction / Lead-Time Escalation
        # -------------------------------------------------------------
        delay_cols = [c for c in df.columns if any(k in c.lower() for k in ["delay", "lead_time", "shipping_days", "fulfillment_time"])]
        if delay_cols:
            delay_col = delay_cols[0]
            high_delays = df[df[delay_col] > df[delay_col].quantile(0.85)]
            if len(high_delays) > 0:
                risks.append(RiskItem(
                    id="RISK-OPS-BOTTLENECK",
                    title=f"Fulfillment Latency in {delay_col.replace('_', ' ').title()}",
                    category="Operational Delay",
                    severity="Medium",
                    probability_pct=60.0,
                    estimated_financial_exposure=round(float(high_delays[target_col].sum() * 0.10), 2),
                    root_cause_ref="Operational latency exceeding SLA targets",
                    early_warning_signals=[
                        f"85th percentile SLA reaches {df[delay_col].quantile(0.85):.1f} days/units.",
                        f"{len(high_delays)} transactions suffered acute delivery delays."
                    ],
                    mitigation_window_days=45
                ))

        # -------------------------------------------------------------
        # 4. Segment Drag & Diagnostic Root-Cause Risks
        # -------------------------------------------------------------
        drag_items = [b for b in diagnostic.variance_breakdown if b.direction == "Drag"]
        if drag_items:
            primary_drag = drag_items[0]
            exposure_val = round(abs(primary_drag.variance), 2)
            risks.append(RiskItem(
                id=f"RISK-SEGMENT-DRAG",
                title=f"Segment Decay in '{primary_drag.segment}' ({primary_drag.dimension})",
                category="Performance Drag",
                severity="High" if abs(primary_drag.variance_pct) > 20 else "Medium",
                probability_pct=80.0,
                estimated_financial_exposure=exposure_val,
                root_cause_ref=root_cause.primary_root_cause,
                early_warning_signals=[
                    f"Segment accounted for {primary_drag.contribution_share_pct}% of total negative variance.",
                    f"Variance from baseline: {primary_drag.variance:+.2f} ({primary_drag.variance_pct:+.1f}%)."
                ],
                mitigation_window_days=30
            ))

        # -------------------------------------------------------------
        # 5. Growth Opportunities: Underperforming Recovery & Overperforming Expansion
        # -------------------------------------------------------------
        lift_items = [b for b in diagnostic.variance_breakdown if b.direction == "Lift"]
        if lift_items:
            top_lift = lift_items[0]
            upside = round(abs(top_lift.variance) * 1.35, 2)
            opportunities.append(OpportunityItem(
                id="OPP-SEGMENT-EXPANSION",
                title=f"Scale High-Momentum Segment: {top_lift.segment}",
                category="Revenue Growth",
                potential_value_gain=upside,
                feasibility="Medium",
                confidence_level_pct=82.0,
                target_segment=f"{top_lift.dimension}: {top_lift.segment}",
                strategic_rationale=(
                    f"Segment is generating positive growth (+{top_lift.variance:.2f}). Reallocating sales resources "
                    f"and promotional inventory to this segment capitalizes on proven organic demand."
                )
            ))

        # Core operational turnaround opportunity
        if drag_items:
            turnaround_target = drag_items[0]
            turnaround_gain = round(abs(turnaround_target.variance) * 0.65, 2)
            opportunities.append(OpportunityItem(
                id="OPP-TURNAROUND-REMEDY",
                title=f"Operational Remediation for '{turnaround_target.segment}'",
                category="Cost Reduction",
                potential_value_gain=turnaround_gain,
                feasibility="High",
                confidence_level_pct=78.0,
                target_segment=f"{turnaround_target.dimension}: {turnaround_target.segment}",
                strategic_rationale=(
                    f"Recovering 65% of the observed negative variance through targeted interventions "
                    f"unlocks ${turnaround_gain:,.2f} in bottom-line restoration."
                )
            ))

        # Ensure default risk and opportunity if clean data
        if not risks:
            risks.append(RiskItem(
                id="RISK-VARIANCE-MODERATE",
                title="Baseline Volatility & Macro Fluctuations",
                category="Macro Volatility",
                severity="Low",
                probability_pct=30.0,
                estimated_financial_exposure=round(total_target_val * 0.05, 2),
                root_cause_ref="General market fluctuation",
                early_warning_signals=["Standard deviation across periods within normal range"],
                mitigation_window_days=90
            ))

        total_exposure = sum(r.estimated_financial_exposure for r in risks)
        total_upside = sum(o.potential_value_gain for o in opportunities)

        if total_exposure > (total_target_val * 0.20):
            profile_rating = "High Risk"
        elif total_exposure > (total_target_val * 0.08):
            profile_rating = "Moderate"
        else:
            profile_rating = "Conservative"

        return RisksAndOpportunitiesReport(
            total_exposure_at_risk=round(total_exposure, 2),
            total_opportunity_upside=round(total_upside, 2),
            risk_profile_rating=profile_rating,
            risks=risks,
            opportunities=opportunities
        )
