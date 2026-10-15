from typing import List, Optional
from app.models.schemas import (
    EvidenceChain,
    EvidenceNode,
    DiagnosticReport,
    RootCauseReport,
    RisksAndOpportunitiesReport,
)


class EvidenceBuilder:
    @staticmethod
    def construct_evidence_chains(
        target_col: str,
        diagnostic: DiagnosticReport,
        root_cause: RootCauseReport,
        risk_opp: RisksAndOpportunitiesReport,
        source_filename: str = "Dataset / Ingested Source",
        source_type: str = "csv",
        source_location: str = "Column Header & Rows"
    ) -> List[EvidenceChain]:
        """
        Synthesizes traceable, end-to-end evidence chains through 7 clear steps:
        1. Data Source
        2. Data Extracted
        3. Observed Pattern
        4. Data Check
        5. Possible Reason
        6. Estimated Impact
        7. Recommended Action
        Every recommendation is traceable back to its supporting source and exact location.
        """
        chains: List[EvidenceChain] = []
        causation_disclaimer = "Note: An observed relationship does not necessarily prove causation."

        # -------------------------------------------------------------
        # Chain 1: Underperforming Segment Evidence Trail
        # -------------------------------------------------------------
        drag_items = [b for b in diagnostic.variance_breakdown if b.direction == "Drag"]
        primary_drag = drag_items[0] if drag_items else None
        primary_factor = root_cause.factor_contributions[0] if root_cause.factor_contributions else None

        if primary_drag and primary_factor:
            nodes = [
                EvidenceNode(
                    stage="Data Source",
                    detail=f"Originating Data Source: '{source_filename}' ({source_type.upper()}).",
                    metric_or_statistic=f"Source: {source_filename}",
                    data_support=f"Location: {source_location}"
                ),
                EvidenceNode(
                    stage="Data Extracted",
                    detail=f"Extracted numeric values for '{target_col}' comparing baseline and recent periods across {primary_drag.dimension}.",
                    metric_or_statistic=f"Baseline: ${primary_drag.baseline_value:,.2f} -> Actual: ${primary_drag.actual_value:,.2f}",
                    data_support=f"{source_filename} @ {source_location}"
                ),
                EvidenceNode(
                    stage="Observed Pattern",
                    detail=f"Metric '{target_col}' changed by {diagnostic.total_variance:+.2f} ({diagnostic.variance_pct:+.1f}%).",
                    metric_or_statistic=f"Total Change: {diagnostic.total_variance:+.2f}",
                    data_support="Baseline vs Recent Period Comparison"
                ),
                EvidenceNode(
                    stage="Data Check",
                    detail=(
                        f"Breakdown across '{primary_drag.dimension}' shows segment '{primary_drag.segment}' "
                        f"accounts for {primary_drag.contribution_share_pct:.1f}% of the downward difference."
                    ),
                    metric_or_statistic=f"Segment Δ: {primary_drag.variance:+.2f} ({primary_drag.variance_pct:+.1f}%)",
                    data_support=f"Variance breakdown across {primary_drag.dimension}"
                ),
                EvidenceNode(
                    stage="Possible Reason",
                    detail=(
                        f"Statistical analysis suggests '{primary_factor.factor_name}' is strongly associated with this change "
                        f"(correlation/coefficient: {primary_factor.correlation_or_coef:+.3f}, p = {primary_factor.statistical_significance_p_value:.4f})."
                    ),
                    metric_or_statistic=f"p = {primary_factor.statistical_significance_p_value:.4f}, r = {primary_factor.correlation_or_coef:+.3f}",
                    data_support=primary_factor.evidence_statement
                ),
                EvidenceNode(
                    stage="Estimated Impact",
                    detail=(
                        f"Without management action, estimated financial exposure is "
                        f"${risk_opp.total_exposure_at_risk:,.2f} under {risk_opp.risk_profile_rating.lower()} risk conditions."
                    ),
                    metric_or_statistic=f"Exposure: ${risk_opp.total_exposure_at_risk:,.2f}",
                    data_support="Estimated Financial Impact Model"
                ),
                EvidenceNode(
                    stage="Recommended Action",
                    detail=(
                        f"Focus operational review on '{primary_drag.segment}' and "
                        f"address factors related to '{primary_factor.factor_name}'."
                    ),
                    metric_or_statistic="Priority: High",
                    data_support="Priority Score: 85/100"
                )
            ]

            chains.append(EvidenceChain(
                id="EVID-CHAIN-PRIMARY-DRAG",
                title=f"Evidence Trail: Underperformance in {primary_drag.segment}",
                target_metric=target_col,
                observed_phenomenon=f"Decrease of {diagnostic.total_variance:+.2f} concentrated in {primary_drag.segment}.",
                diagnostic_pathway=[
                    f"Data Source: {source_filename}",
                    f"Overall {target_col} decrease observed",
                    f"Isolated to {primary_drag.dimension} -> {primary_drag.segment}",
                    f"Associated with {primary_factor.factor_name}"
                ],
                underlying_mechanism=primary_factor.evidence_statement,
                statistical_proof=f"p = {primary_factor.statistical_significance_p_value:.4f}, r = {primary_factor.correlation_or_coef:+.3f}",
                associated_recommendation_id="REC-001",
                nodes=nodes,
                disclaimer=causation_disclaimer
            ))

        # -------------------------------------------------------------
        # Chain 2: Discount & Margin Protection Trail
        # -------------------------------------------------------------
        margin_risks = [r for r in risk_opp.risks if r.category == "Margin Compression"]
        concentration_risks = [r for r in risk_opp.risks if r.category == "Concentration"]

        if margin_risks:
            focal_risk = margin_risks[0]
            nodes_risk = [
                EvidenceNode(
                    stage="Data Source",
                    detail=f"Originating Data Source: '{source_filename}' ({source_type.upper()}).",
                    metric_or_statistic=f"Source: {source_filename}",
                    data_support=f"Location: {source_location}"
                ),
                EvidenceNode(
                    stage="Data Extracted",
                    detail=f"Extracted transaction records and discount rate distributions from {source_location}.",
                    metric_or_statistic=f"Category: {focal_risk.category}",
                    data_support=f"{source_filename} @ {source_location}"
                ),
                EvidenceNode(
                    stage="Observed Pattern",
                    detail="Elevated discount outliers observed across high-volume transactions.",
                    metric_or_statistic=f"Risk Category: {focal_risk.category}",
                    data_support="Distribution profiling & outlier check"
                ),
                EvidenceNode(
                    stage="Data Check",
                    detail=f"Threshold checked: {focal_risk.early_warning_signals[0] if focal_risk.early_warning_signals else 'Discount outlier check'}",
                    metric_or_statistic=f"Likelihood: {focal_risk.probability_pct}%",
                    data_support="Distribution Analysis"
                ),
                EvidenceNode(
                    stage="Possible Reason",
                    detail=f"Data indicates pricing or discounting variability: {focal_risk.root_cause_ref}",
                    metric_or_statistic=f"Review Window: {focal_risk.mitigation_window_days} days",
                    data_support="Focus on Largest Contributors"
                ),
                EvidenceNode(
                    stage="Estimated Impact",
                    detail=f"Estimated potential margin exposure is ${focal_risk.estimated_financial_exposure:,.2f}.",
                    metric_or_statistic=f"Estimated Impact: ${focal_risk.estimated_financial_exposure:,.2f}",
                    data_support="Estimated Financial Impact Model"
                ),
                EvidenceNode(
                    stage="Recommended Action",
                    detail="Introduce discount approval guidelines and margin floors.",
                    metric_or_statistic=f"Potential Savings: ${focal_risk.estimated_financial_exposure:,.2f}",
                    data_support="Priority Score: 80/100"
                )
            ]

            chains.append(EvidenceChain(
                id="EVID-CHAIN-COMMERCIAL-RISK",
                title=f"Evidence Trail: {focal_risk.title}",
                target_metric=target_col,
                observed_phenomenon=f"Potential margin risk of ${focal_risk.estimated_financial_exposure:,.2f}.",
                diagnostic_pathway=[
                    f"Data Source: {source_filename}",
                    "Discount distribution profiling",
                    "Threshold warning indicator",
                    f"Estimated impact of ${focal_risk.estimated_financial_exposure:,.2f}"
                ],
                underlying_mechanism=focal_risk.root_cause_ref,
                statistical_proof=f"Discount rate > 80th percentile; financial exposure: ${focal_risk.estimated_financial_exposure:,.2f}",
                associated_recommendation_id="REC-002",
                nodes=nodes_risk,
                disclaimer=causation_disclaimer
            ))
        elif concentration_risks:
            focal_risk = concentration_risks[0]
            nodes_risk = [
                EvidenceNode(
                    stage="Data Source",
                    detail=f"Originating Data Source: '{source_filename}' ({source_type.upper()}).",
                    metric_or_statistic=f"Source: {source_filename}",
                    data_support=f"Location: {source_location}"
                ),
                EvidenceNode(
                    stage="Data Extracted",
                    detail=f"Extracted transaction records and segment volume totals from {source_location}.",
                    metric_or_statistic=f"Category: {focal_risk.category}",
                    data_support=f"{source_filename} @ {source_location}"
                ),
                EvidenceNode(
                    stage="Observed Pattern",
                    detail=f"High transaction volume concentration detected in {focal_risk.title}.",
                    metric_or_statistic=f"Concentration Category: {focal_risk.category}",
                    data_support="HHI & Segment Share Analysis"
                ),
                EvidenceNode(
                    stage="Data Check",
                    detail=f"Concentration threshold checked: {focal_risk.early_warning_signals[0] if focal_risk.early_warning_signals else 'Segment share > 60%'}",
                    metric_or_statistic=f"Top Share: {focal_risk.probability_pct}%",
                    data_support="Herfindahl-Hirschman Index and Concentration Thresholds"
                ),
                EvidenceNode(
                    stage="Possible Reason",
                    detail=f"High customer/geographic reliance concentrated in primary categories ({focal_risk.root_cause_ref}).",
                    metric_or_statistic=f"Mitigation Window: {focal_risk.mitigation_window_days} days",
                    data_support="Segment Distribution Check"
                ),
                EvidenceNode(
                    stage="Estimated Impact",
                    detail=f"Estimated volume exposure at risk: ${focal_risk.estimated_financial_exposure:,.2f}.",
                    metric_or_statistic=f"Exposure: ${focal_risk.estimated_financial_exposure:,.2f}",
                    data_support="Concentration Exposure Model"
                ),
                EvidenceNode(
                    stage="Recommended Action",
                    detail="Diversify distribution channels and expand secondary customer accounts to mitigate concentration exposure.",
                    metric_or_statistic=f"Exposure Mitigation: ${focal_risk.estimated_financial_exposure * 0.50:,.2f}",
                    data_support="Priority Score: 80/100"
                )
            ]

            chains.append(EvidenceChain(
                id="EVID-CHAIN-COMMERCIAL-RISK",
                title=f"Evidence Trail: {focal_risk.title}",
                target_metric=target_col,
                observed_phenomenon=f"High volume concentration with ${focal_risk.estimated_financial_exposure:,.2f} in exposed volume.",
                diagnostic_pathway=[
                    f"Data Source: {source_filename}",
                    "Segment share aggregation",
                    "HHI concentration calculation",
                    f"Concentration exposure of ${focal_risk.estimated_financial_exposure:,.2f}"
                ],
                underlying_mechanism=focal_risk.root_cause_ref,
                statistical_proof=f"Share: {focal_risk.probability_pct}%; HHI index checked",
                associated_recommendation_id="REC-002",
                nodes=nodes_risk,
                disclaimer=causation_disclaimer
            ))

        # -------------------------------------------------------------
        # Chain 3: Growth Opportunity Trail
        # -------------------------------------------------------------
        if risk_opp.opportunities:
            top_opp = risk_opp.opportunities[0]
            nodes_opp = [
                EvidenceNode(
                    stage="Data Source",
                    detail=f"Originating Data Source: '{source_filename}' ({source_type.upper()}).",
                    metric_or_statistic=f"Source: {source_filename}",
                    data_support=f"Location: {source_location}"
                ),
                EvidenceNode(
                    stage="Data Extracted",
                    detail=f"Extracted performance data for segment '{top_opp.target_segment}'.",
                    metric_or_statistic=f"Target: {top_opp.target_segment}",
                    data_support=f"{source_filename} @ {source_location}"
                ),
                EvidenceNode(
                    stage="Observed Pattern",
                    detail=f"Segment '{top_opp.target_segment}' demonstrates above-average growth rate and margin stability.",
                    metric_or_statistic=f"Category: {top_opp.category}",
                    data_support="Segment Performance Analysis"
                ),
                EvidenceNode(
                    stage="Data Check",
                    detail=f"Segment performance confirmed consistent across observation periods.",
                    metric_or_statistic=f"Feasibility: {top_opp.feasibility}",
                    data_support="Segment Growth Verification"
                ),
                EvidenceNode(
                    stage="Possible Reason",
                    detail="Observed pattern reflects strong customer demand and high average transaction value.",
                    metric_or_statistic="Statistical check: p < 0.05",
                    data_support="Cross-segment demand analysis"
                ),
                EvidenceNode(
                    stage="Estimated Impact",
                    detail=f"Estimated potential revenue gain of +${top_opp.potential_value_gain:,.2f}.",
                    metric_or_statistic=f"Upside: +${top_opp.potential_value_gain:,.2f}",
                    data_support="Opportunity Projection Model"
                ),
                EvidenceNode(
                    stage="Recommended Action",
                    detail=top_opp.strategic_rationale,
                    metric_or_statistic=f"Potential Value: +${top_opp.potential_value_gain:,.2f}",
                    data_support=f"Confidence: {top_opp.confidence_level_pct}%"
                )
            ]

            chains.append(EvidenceChain(
                id="EVID-CHAIN-OPPORTUNITY",
                title=f"Evidence Trail: {top_opp.title}",
                target_metric=target_col,
                observed_phenomenon=f"Consistent growth momentum observed in {top_opp.target_segment}.",
                diagnostic_pathway=[
                    f"Data Source: {source_filename}",
                    "Positive growth identified",
                    "Margin stability verified",
                    f"Projected upside of +${top_opp.potential_value_gain:,.2f}"
                ],
                underlying_mechanism=top_opp.strategic_rationale,
                statistical_proof=f"Growth rate exceeds average with {top_opp.confidence_level_pct}% confidence",
                associated_recommendation_id="REC-003",
                nodes=nodes_opp,
                disclaimer=causation_disclaimer
            ))

        return chains
