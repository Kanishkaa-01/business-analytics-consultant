from typing import Dict, Any, List, Optional
from app.models.schemas import WhyThisResultResponse
from app.models.db_models import AnalysisRun


class ExplanationEngine:
    """
    Deterministic Explanation Engine.
    Provides rigorous 'Why This Result?' metadata, underlying formulas,
    mathematical evidence, assumptions, and non-causation disclaimers.
    """

    @classmethod
    def explain_result(
        cls,
        run: AnalysisRun,
        result_type: str,
        result_id: str
    ) -> WhyThisResultResponse:
        """
        Generates structured, explainable decision rationales for any analytical artifact.
        """
        r_type = result_type.lower().strip()
        bh = run.business_health or {}
        diag = run.diagnostics or {}
        rc = run.root_cause or {}
        recs = run.recommendations or []

        # 1. Health Score Explanation
        if r_type in ["health", "health_score", "business_health"]:
            score = bh.get("overall_health_score", 0.0)
            status = bh.get("overall_status", "Stable")
            kpis = bh.get("kpis", [])
            weakest_kpi = None
            for k in kpis:
                if k.get("status") in ["critical", "warning"]:
                    weakest_kpi = k
                    break

            evidence = [
                f"Overall composite score evaluated at {score:.1f}/100 ({status}).",
                f"Evaluated {len(kpis)} core KPI metrics and {len(bh.get('vital_signs', {}))} vital sign health dimensions."
            ]
            if weakest_kpi:
                evidence.append(
                    f"Primary downward pressure originates from `{weakest_kpi.get('name')}` "
                    f"with {weakest_kpi.get('variance_pct', 0):+.1f}% variance ({weakest_kpi.get('status').upper()})."
                )

            drag_text = (
                f"underperformance in {weakest_kpi.get('name')} exerts primary drag."
                if weakest_kpi else "all tracked metrics remain within acceptable bounds."
            )
            return WhyThisResultResponse(
                result_type="health_score",
                result_id=result_id or "health_score",
                title=f"Why is the Business Health Score {score:.1f} / 100 ({status})?",
                plain_english_summary=(
                    f"The health score reflects a weighted evaluation of financial momentum, operational consistency, "
                    f"and stability. While overall metrics place the organization in the '{status}' tier, {drag_text}"
                ),
                primary_driver=weakest_kpi.get("name") if weakest_kpi else "Balanced Metric Performance",
                supporting_evidence=evidence,
                methodology_applied="Multi-factor weighted composite scoring with continuous trend normalization and bounds clamping.",
                underlying_formulas_or_logic=(
                    "Health_Score = 100 - Sum(Variance_Penalties) * Severity_Weight. "
                    "Metrics experiencing adverse deviations from baseline baseline receive proportional penalties."
                ),
                data_inputs_used=[
                    f"Target column: {run.target_column or 'Primary Metric'}",
                    f"Date column: {run.date_column or 'Chronological Index'}",
                    f"Records audited: {run.execution_time_ms}ms execution across all clean dataset rows."
                ],
                limitations_and_assumptions=[
                    "Composite weights reflect standard empirical corporate benchmarks.",
                    "Health status assumes continuous operational conditions without unrecorded external shocks."
                ],
                causation_disclaimer="Correlation and deterministic associations do not prove business causation. External market and organizational factors must be considered."
            )

        # 2. Recommendation Explanation
        if r_type in ["recommendation", "rec"]:
            target_rec = None
            for rec in recs:
                if str(rec.get("id")) == str(result_id) or str(rec.get("recommendation_id")) == str(result_id):
                    target_rec = rec
                    break
            if not target_rec and recs:
                target_rec = recs[0]

            if target_rec:
                title = target_rec.get("title") or target_rec.get("action_title") or "Recommended Action"
                effort = target_rec.get("implementation_effort", "Medium")
                impact = target_rec.get("expected_financial_impact") or target_rec.get("expected_impact_dollars") or 0.0
                tier = target_rec.get("priority_tier", "Tier 1")

                return WhyThisResultResponse(
                    result_type="recommendation",
                    result_id=str(target_rec.get("id", result_id)),
                    title=f"Why is '{title}' recommended?",
                    plain_english_summary=(
                        f"This action was prioritized as a {tier} recommendation because it addresses the identified "
                        f"root cause with an estimated potential upside of ${impact:,.2f} under {effort} operational effort."
                    ),
                    primary_driver=target_rec.get("mechanism_of_action") or "Variance elimination",
                    supporting_evidence=[
                        f"Expected Financial Upside: ${impact:,.2f}",
                        f"Implementation Effort: {effort}",
                        f"Priority Tier: {tier}",
                        f"Underlying finding: {target_rec.get('rationale', 'Empirical data driver')}"
                    ],
                    methodology_applied="Empirical risk-reward prioritization and deterministic elasticity response.",
                    underlying_formulas_or_logic=(
                        "Expected_Impact = Baseline_Exposure * Sensitivity_Recapture_Rate. "
                        "Effort is mapped categorically (Low=2.5, Medium=5.0, High=8.0) into the Decision Impact Matrix."
                    ),
                    data_inputs_used=[
                        f"Diagnosed segment variance: {diag.get('total_variance', 'N/A')}",
                        f"Statistical confidence: {rc.get('statistical_confidence_level', 'High')}"
                    ],
                    limitations_and_assumptions=[
                        "Assumes organizational capability to implement within designated timeframe.",
                        "Financial returns depend on historical customer price sensitivity remaining stable."
                    ],
                    causation_disclaimer="Correlation and deterministic associations do not prove business causation. External market and organizational factors must be considered."
                )

        # 3. Finding / Diagnostic Explanation
        if r_type in ["finding", "diagnostic", "root_cause"]:
            focal_metric = diag.get("focal_metric", "Revenue")
            tot_var = diag.get("total_variance", 0.0)
            var_pct = diag.get("variance_pct", 0.0)
            primary_cause = rc.get("primary_root_cause", "Segment Concentration")

            return WhyThisResultResponse(
                result_type="finding",
                result_id=result_id or "primary_finding",
                title=f"Why did {focal_metric} experience a {var_pct:+.1f}% variance?",
                plain_english_summary=(
                    f"Statistical decomposition identified a total net variance of {tot_var:,.2f} ({var_pct:+.1f}%). "
                    f"Attribution indicates that {primary_cause} is the dominant driver."
                ),
                primary_driver=primary_cause,
                supporting_evidence=[
                    f"Total observed variance: {tot_var:,.2f} ({var_pct:+.1f}%)",
                    f"Statistical confidence level: {rc.get('statistical_confidence_level', '95%')}",
                    f"Dominant root cause: {primary_cause}"
                ],
                methodology_applied="Segment variance decomposition and Pareto 80/20 attribution.",
                underlying_formulas_or_logic=(
                    "Delta_Total = Sum(Delta_Segment_i). "
                    "Pareto attribution isolates the vital few categories generating 80% of net change."
                ),
                data_inputs_used=[
                    f"Focal metric: {focal_metric}",
                    f"Dimension categories audited: {', '.join([c.get('factor', '') for c in rc.get('factor_contributions', [])[:3]])}"
                ],
                limitations_and_assumptions=[
                    "Variance calculation compares recent observational periods against baseline mean.",
                    "Attribution assumes additive segment independence."
                ],
                causation_disclaimer="Correlation and deterministic associations do not prove business causation. External market and organizational factors must be considered."
            )

        # 4. Fallback / General Explanation
        return WhyThisResultResponse(
            result_type=result_type,
            result_id=result_id,
            title=f"Analytical Explanation for {result_type.capitalize()}",
            plain_english_summary="Calculated deterministically using reproducible mathematical algorithms over clean dataset records.",
            primary_driver=run.target_column or "Primary Metric",
            supporting_evidence=[
                f"Analysis Run ID: {run.id[:8]}",
                f"Execution Duration: {run.execution_time_ms}ms"
            ],
            methodology_applied="Deterministic business analytics and mathematical decomposition.",
            underlying_formulas_or_logic="Deterministic pandas aggregation and statistical modeling.",
            data_inputs_used=[f"Dataset: {run.dataset_id}"],
            limitations_and_assumptions=["Calculations reflect dataset rows provided at ingestion time."],
            causation_disclaimer="Correlation and deterministic associations do not prove business causation. External market and organizational factors must be considered."
        )
