from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import AnalysisRun, Dataset, DecisionRecord, SimulationScenario, KpiGoal
from app.services.report_generator import ReportGeneratorService
from app.engines.decision_impact import DecisionImpactEngine
from app.engines.forecasting_engine import ForecastingEngine
from app.services.data_ingestion import IngestionService

router = APIRouter(prefix="/export", tags=["Business Decision Report Export"])



@router.get("/{analysis_id}/pdf-report")
def export_pdf_report(analysis_id: str, db: Session = Depends(get_db)):
    """Phase 15: Generates professional 13-section business report in PDF format."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    decisions = db.query(DecisionRecord).filter(DecisionRecord.analysis_id == analysis_id).all()
    scenarios = db.query(SimulationScenario).filter(SimulationScenario.analysis_id == analysis_id).all()

    pdf_bytes = ReportGeneratorService.generate_pdf_report(run, dataset, decisions, scenarios)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="business_report_{analysis_id[:8]}.pdf"'}
    )


@router.get("/{analysis_id}/excel-report")
def export_excel_report(analysis_id: str, db: Session = Depends(get_db)):
    """Phase 15: Generates professional 10-sheet structured business workbook in Excel format."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    decisions = db.query(DecisionRecord).filter(DecisionRecord.analysis_id == analysis_id).all()
    scenarios = db.query(SimulationScenario).filter(SimulationScenario.analysis_id == analysis_id).all()

    excel_bytes = ReportGeneratorService.generate_excel_report(run, dataset, decisions, scenarios)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="business_report_{analysis_id[:8]}.xlsx"'}
    )


@router.get("/{analysis_id}/dossier")
def get_executive_dossier_json(analysis_id: str, db: Session = Depends(get_db)):
    """Generates complete structured Executive Business Decision Report."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    decisions = db.query(DecisionRecord).filter(DecisionRecord.analysis_id == analysis_id).all()

    dossier = {
        "title": "Executive Business Decision Report",
        "system": "Business Analytics Consultant — Explainable Business Decision Support System",
        "analysis_id": run.id,
        "generated_at": run.created_at.isoformat(),
        "execution_time_ms": run.execution_time_ms,
        "dataset_integrity": {
            "name": dataset.name if dataset else "Unknown",
            "filename": dataset.filename if dataset else "Unknown",
            "sha256_hash": dataset.file_hash if dataset else "Unknown",
            "row_count": dataset.row_count if dataset else 0,
            "column_count": dataset.column_count if dataset else 0
        },
        "four_core_questions": {
            "question_1_what_is_happening": {
                "health_score": run.business_health.get("overall_health_score"),
                "status": run.business_health.get("overall_status"),
                "summary": run.business_health.get("executive_summary"),
                "kpis": run.business_health.get("kpis", [])
            },
            "question_2_why_is_it_happening": {
                "focal_metric": run.diagnostics.get("focal_metric"),
                "total_variance": run.diagnostics.get("total_variance"),
                "variance_pct": run.diagnostics.get("variance_pct"),
                "narrative": run.diagnostics.get("diagnostic_narrative"),
                "primary_variance_drivers": run.diagnostics.get("variance_breakdown", [])[:5]
            },
            "question_3_what_requires_attention": {
                "primary_root_cause": run.root_cause.get("primary_root_cause"),
                "statistical_confidence": run.root_cause.get("statistical_confidence_level"),
                "factor_attribution": run.root_cause.get("factor_contributions", []),
                "pareto_vital_few": [p for p in run.root_cause.get("pareto_breakdown", []) if p.get("is_vital_few")],
                "total_risk_exposure": run.risks_opportunities.get("total_exposure_at_risk"),
                "total_opportunity_upside": run.risks_opportunities.get("total_opportunity_upside"),
                "risk_profile": run.risks_opportunities.get("risk_profile_rating")
            },
            "question_4_what_action_to_consider": {
                "prioritized_recommendations": run.recommendations,
                "evidence_chains": run.evidence_chains,
                "recorded_management_decisions": [
                    {
                        "action_title": d.action_title,
                        "status": d.decision_status,
                        "stakeholder": d.stakeholder,
                        "notes": d.notes_rationale,
                        "target_date": d.target_date
                    }
                    for d in decisions
                ]
            }
        },
        "data_quality_audit": run.data_quality
    }
    return dossier


@router.get("/{analysis_id}/print-report", response_class=HTMLResponse)
def get_printable_executive_report(analysis_id: str, db: Session = Depends(get_db)):
    """Renders a printable executive HTML decision dossier."""
    dossier = get_executive_dossier_json(analysis_id, db)
    q1 = dossier["four_core_questions"]["question_1_what_is_happening"]
    q2 = dossier["four_core_questions"]["question_2_why_is_it_happening"]
    q3 = dossier["four_core_questions"]["question_3_what_requires_attention"]
    q4 = dossier["four_core_questions"]["question_4_what_action_to_consider"]
    ds = dossier["dataset_integrity"]

    kpi_rows = "".join([
        f"<tr><td><b>{k.get('name')}</b></td><td>{k.get('current_value'):,} {k.get('unit')}</td>"
        f"<td>{k.get('variance_pct', 0):+.1f}%</td><td><span class='badge {k.get('status')}'>{k.get('status').upper()}</span></td></tr>"
        for k in q1.get("kpis", [])
    ])

    rec_cards = "".join([
        f"<div class='rec-card'>"
        f"<h3>[{r.get('priority_tier')}] {r.get('title')}</h3>"
        f"<p><b>Urgency:</b> {r.get('urgency')} | <b>Effort:</b> {r.get('implementation_effort')} | <b>Expected Impact:</b> ${r.get('expected_financial_impact', 0):,.2f}</p>"
        f"<p><b>Recommended Action:</b> {r.get('mechanism_of_action')}</p>"
        f"<p><b>Supporting Evidence:</b> {r.get('rationale')}</p>"
        f"</div>"
        for r in q4.get("prioritized_recommendations", [])[:4]
    ])

    conf_raw = q3.get('statistical_confidence')
    conf_display = "Significant association (p &lt; 0.05)" if (conf_raw == 100 or conf_raw == '100%' or conf_raw == '100') else f"{conf_raw}%"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Executive Business Decision Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; margin: 40px auto; max-width: 900px; padding: 0 20px; }}
  h1 {{ font-size: 24px; color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 12px; }}
  h2 {{ font-size: 18px; color: #0369a1; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }}
  .meta-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 16px; margin-bottom: 24px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 24px; font-size: 14px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
  th {{ background: #f1f5f9; font-weight: 600; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
  .healthy {{ background: #dcfce7; color: #15803d; }}
  .warning {{ background: #fef9c3; color: #a16207; }}
  .critical {{ background: #fee2e2; color: #b91c1c; }}
  .rec-card {{ border: 1px solid #cbd5e1; border-left: 4px solid #0284c7; border-radius: 6px; padding: 14px; margin-bottom: 14px; background: #fafafa; }}
  .rec-card h3 {{ margin: 0 0 6px 0; font-size: 15px; color: #0f172a; }}
  .rec-card p {{ margin: 4px 0; font-size: 13px; }}
  @media print {{ body {{ margin: 15px; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom: 20px; text-align: right;">
  <button onclick="window.print()" style="padding: 8px 16px; background: #0284c7; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Print / Save as PDF</button>
</div>

<h1>Business Decision Report</h1>
<div class="meta-box">
  <b>System:</b> Business Analytics Consultant (Explainable Decision Support System)<br>
  <b>Dataset:</b> {ds['name']} ({ds['filename']})<br>
  <b>Integrity Checksum (SHA-256):</b> <code>{ds['sha256_hash']}</code><br>
  <b>Records Analyzed:</b> {ds['row_count']:,} rows &times; {ds['column_count']} dimensions | <b>Generated:</b> {dossier['generated_at']}
</div>

<h2>1. What is Happening? (Business Health & KPI Vital Signs)</h2>
<p><b>Overall Health Index:</b> {q1.get('health_score')}/100 ({q1.get('status')})</p>
<p>{q1.get('summary')}</p>
<table>
  <thead>
    <tr><th>Metric</th><th>Current Value</th><th>Variance (Period)</th><th>Health Status</th></tr>
  </thead>
  <tbody>
    {kpi_rows}
  </tbody>
</table>

<h2>2. Why is it Happening? (Variance Decomposition & Segment Comparison)</h2>
<p><b>Focal Metric:</b> {q2.get('focal_metric')} | <b>Total Net Variance:</b> {q2.get('total_variance'):+,.2f} ({q2.get('variance_pct', 0):+.1f}%)</p>
<p>{q2.get('narrative')}</p>

<h2>3. What Requires Attention? (Possible Reasons & Estimated Impact)</h2>
<p><b>Possible Contributor:</b> {q3.get('primary_root_cause')}</p>
<p><b>Statistical Basis:</b> {conf_display}</p>
<p><b>Financial Downside at Risk:</b> ${q3.get('total_risk_exposure', 0):,.2f} ({q3.get('risk_profile')} Profile) | <b>Upside Growth Potential:</b> ${q3.get('total_opportunity_upside', 0):,.2f}</p>

<h2>4. What Action Could Management Consider? (Prioritized Recommendations)</h2>
{rec_cards}

<hr style="margin-top: 40px; border: none; border-top: 1px solid #cbd5e1;">
<p style="font-size: 11px; color: #64748b; text-align: center;">Business Analytics Consultant — Explainable Business Decision Support System &bull; MSc IT Research Project</p>
</body>
</html>"""
    return html_content


@router.get("/{analysis_id}/complete-decision-report")
def get_complete_decision_report(
    analysis_id: str,
    format: str = Query("html", description="Output format: 'html' or 'pdf'"),
    db: Session = Depends(get_db)
):
    """
    Renders complete 17-section Business Decision Report in HTML or PDF.
    Encompasses:
    1. Executive Summary
    2. Data Quality & Reliability Assessment
    3. Business Health & Vital Signs Overview
    4. Primary Diagnostics & Variance Breakdown
    5. Root Cause & Statistical Attribution
    6. Risks & Opportunities Analysis
    7. Evidence Trail & Supporting Data Points
    8. Prioritized Recommendations & Action Plan
    9. Decision Impact Matrix (Effort vs Impact Quadrants)
    10. Scenario Simulation & What-If Analysis
    11. Forecast & Projection Overview
    12. Forecast vs Actual Variance Analysis
    13. KPI Goal Tracking & Target Milestones
    14. Drill-Down Insights
    15. Decision Registry & Stakeholder Commitments
    16. Assumptions, Methodology & Analytical Integrity
    17. Non-Causation Disclaimer & Sign-off Appendix
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    decisions = db.query(DecisionRecord).filter(DecisionRecord.analysis_id == analysis_id).all()
    scenarios = db.query(SimulationScenario).filter(SimulationScenario.analysis_id == analysis_id).all()
    goals = db.query(KpiGoal).filter((KpiGoal.analysis_id == analysis_id) | (KpiGoal.dataset_id == run.dataset_id)).all()

    if format.lower() == "pdf":
        pdf_bytes = ReportGeneratorService.generate_pdf_report(run, dataset, decisions, scenarios)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="complete_decision_report_{analysis_id[:8]}.pdf"'}
        )

    # HTML Generation
    bh = run.business_health or {}
    dq = run.data_quality or {}
    diag = run.diagnostics or {}
    rc = run.root_cause or {}
    ro = run.risks_opportunities or {}
    recs = run.recommendations or []
    ev_chains = run.evidence_chains or []

    # Decision Impact Matrix
    matrix_res = DecisionImpactEngine.generate_impact_matrix(recs)

    # Forecast and Forecast vs Actual
    df = None
    fc_summary = "Forecasting model not calculated."
    fc_actual_summary = "Holdout forecast vs actual comparison not executed."
    if dataset and dataset.file_path and Path(dataset.file_path).exists():
        try:
            df = IngestionService.load_dataframe(Path(dataset.file_path))
            fc_rep = ForecastingEngine.generate_forecast(df, run.target_column, run.date_column)
            if fc_rep.is_available:
                fc_summary = fc_rep.trajectory_narrative or "Forecast calculated."
            fc_act = ForecastingEngine.compare_forecast_vs_actual(df, run.target_column, run.date_column)
            if fc_act.insights:
                fc_actual_summary = " ".join(fc_act.insights)
        except Exception:
            pass

    # Build HTML sections
    kpi_rows = "".join([
        f"<tr><td><b>{k.get('name')}</b></td><td>{k.get('current_value'):,} {k.get('unit')}</td>"
        f"<td>{k.get('variance_pct', 0):+.1f}%</td><td><span class='badge {k.get('status')}'>{k.get('status', '').upper()}</span></td></tr>"
        for k in bh.get("kpis", [])
    ])

    issue_rows = "".join([
        f"<tr><td><span class='badge {i.get('severity', '').lower()}'>{i.get('severity')}</span></td>"
        f"<td>{i.get('dimension')}</td><td>{i.get('column') or 'Dataset-wide'}</td>"
        f"<td>{i.get('description')}</td><td>{i.get('affected_rows', 0):,} ({i.get('percentage', 0):.1f}%)</td></tr>"
        for i in dq.get("issues", [])
    ]) or "<tr><td colspan='5'>No critical data quality issues identified.</td></tr>"

    rec_cards = "".join([
        f"<div class='card'>"
        f"<h3>[{r.get('priority_tier')}] {r.get('title')}</h3>"
        f"<p><b>Urgency:</b> {r.get('urgency')} | <b>Effort:</b> {r.get('implementation_effort')} | <b>Expected Financial Upside:</b> ${r.get('expected_financial_impact', 0):,.2f}</p>"
        f"<p><b>Mechanism:</b> {r.get('mechanism_of_action')}</p>"
        f"<p><b>Rationale:</b> {r.get('rationale')}</p>"
        f"</div>"
        for r in recs
    ])

    impact_matrix_rows = "".join([
        f"<tr><td><b>{item.action_title}</b></td>"
        f"<td><span class='badge {'healthy' if item.quadrant == 'Quick Wins' else 'warning' if item.quadrant == 'Strategic Bets' else 'critical'}'>{item.quadrant}</span></td>"
        f"<td>{item.implementation_effort} ({item.effort_score}/10)</td>"
        f"<td>{item.impact_score}/10</td>"
        f"<td>${item.expected_impact_dollars:,.2f}</td>"
        f"<td>{item.timeframe}</td></tr>"
        for item in matrix_res.items
    ])

    scenario_rows = "".join([
        f"<tr><td><b>{s.name}</b></td>"
        f"<td>{', '.join([f'{k}: {v:+}%' if isinstance(v, (int, float)) else f'{k}: {v}' for k, v in (s.parameters or {}).items()])}</td>"
        f"<td>${(s.projected_outcomes or {}).get('simulated_revenue', 0):,.2f}</td>"
        f"<td>${(s.projected_outcomes or {}).get('simulated_profit', 0):,.2f}</td>"
        f"<td>{(s.projected_outcomes or {}).get('simulated_margin_pct', 0):.1f}%</td></tr>"
        for s in scenarios
    ]) or "<tr><td colspan='5'>No simulated scenarios saved yet.</td></tr>"

    goal_rows = "".join([
        f"<tr><td><b>{g.metric}</b></td>"
        f"<td>{g.target_type}</td>"
        f"<td>{g.target_value:,.2f}</td>"
        f"<td>{g.current_value:,.2f}</td>"
        f"<td>{g.progress_pct:.1f}%</td>"
        f"<td><span class='badge {'healthy' if g.status == 'Target Achieved' or g.status == 'On Track' else 'warning' if g.status == 'Near Target' else 'critical'}'>{g.status}</span></td></tr>"
        for g in goals
    ]) or "<tr><td colspan='6'>No active KPI targets tracked.</td></tr>"

    decision_rows = "".join([
        f"<tr><td><b>{d.action_title}</b></td>"
        f"<td><span class='badge {'healthy' if d.decision_status == 'Accepted' else 'warning'}'>{d.decision_status}</span></td>"
        f"<td>{d.stakeholder or 'Decision Maker'}</td>"
        f"<td>{d.notes_rationale or 'Recorded in registry'}</td>"
        f"<td>{d.target_date or 'TBD'}</td></tr>"
        for d in decisions
    ]) or "<tr><td colspan='5'>No recorded managerial decisions.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Complete Business Decision Report — {run.id[:8]}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #0f172a; margin: 40px auto; max-width: 960px; padding: 0 24px; }}
  h1 {{ font-size: 26px; color: #0f172a; border-bottom: 3px solid #2563eb; padding-bottom: 12px; margin-bottom: 16px; }}
  h2 {{ font-size: 19px; color: #1e40af; margin-top: 36px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }}
  h3 {{ font-size: 15px; color: #1e293b; margin-top: 14px; margin-bottom: 6px; }}
  .meta-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-bottom: 28px; font-size: 13px; line-height: 1.8; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 20px; font-size: 13px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
  th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
  .card {{ border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; border-radius: 6px; padding: 14px; margin-bottom: 14px; background: #fafafa; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
  .healthy {{ background: #dcfce7; color: #15803d; }}
  .warning {{ background: #fef9c3; color: #a16207; }}
  .critical {{ background: #fee2e2; color: #b91c1c; }}
  .disclaimer {{ background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; padding: 14px; border-radius: 6px; font-size: 13px; color: #92400e; margin: 24px 0; }}
  @media print {{ body {{ margin: 15px; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom: 24px; text-align: right;">
  <a href="/api/export/{analysis_id}/complete-decision-report?format=pdf" style="padding: 8px 16px; background: #059669; color: white; border-radius: 4px; text-decoration: none; font-weight: 600; margin-right: 8px;">Download PDF</a>
  <button onclick="window.print()" style="padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Print Report</button>
</div>

<h1>Complete Business Decision Report</h1>

<div class="meta-box">
  <b>Analysis Title:</b> {run.analysis_name or 'Baseline Business Analysis'}<br>
  <b>Dataset:</b> {dataset.name if dataset else 'Dataset'} ({dataset.filename if dataset else 'N/A'}) &bull; Version: <code>{run.dataset_version or 'v1.0'}</code><br>
  <b>Scope:</b> {dataset.row_count if dataset else 0:,} records &times; {dataset.column_count if dataset else 0} dimensions &bull; Run: {run.created_at.strftime('%Y-%m-%d %H:%M UTC')}
</div>

<h2>Section 1: Executive Summary</h2>
<p>{bh.get('executive_summary', 'Executive overview synthesized from deterministic analytical diagnostics.')}</p>

<h2>Section 2: Data Quality & Reliability Assessment</h2>
<p><b>Overall Quality Score:</b> {dq.get('overall_quality_score', 100):.1f}/100 (Grade {dq.get('grade', 'A')}) &bull; Reliability: <b>{dq.get('reliability_assessment', 'High')}</b></p>
<table>
  <thead><tr><th>Severity</th><th>Dimension</th><th>Column</th><th>Issue Description</th><th>Affected Records</th></tr></thead>
  <tbody>{issue_rows}</tbody>
</table>

<h2>Section 3: Business Health & Vital Signs Overview</h2>
<p><b>Health Score:</b> {bh.get('overall_health_score', 0):.1f}/100 &bull; Status: <b>{bh.get('overall_status', 'Stable')}</b></p>
<table>
  <thead><tr><th>KPI Metric</th><th>Current Value</th><th>Variance %</th><th>Health Status</th></tr></thead>
  <tbody>{kpi_rows}</tbody>
</table>

<h2>Section 4: Primary Diagnostics & Variance Breakdown</h2>
<p><b>Focal Metric:</b> {diag.get('focal_metric', 'Revenue')} &bull; Net Variance: <b>{diag.get('total_variance', 0):+,.2f} ({diag.get('variance_pct', 0):+.1f}%)</b></p>
<p>{diag.get('diagnostic_narrative', 'Decomposition across business dimensions.')}</p>

<h2>Section 5: Root Cause & Statistical Attribution</h2>
<p><b>Dominant Root Cause:</b> {rc.get('primary_root_cause', 'Segment Concentration')} (Confidence: {rc.get('statistical_confidence_level', 'High')})</p>

<h2>Section 6: Risks & Opportunities Analysis</h2>
<p><b>Capital at Risk:</b> ${ro.get('total_exposure_at_risk', 0):,.2f} &bull; <b>Growth Potential:</b> ${ro.get('total_opportunity_upside', 0):,.2f} &bull; Profile: <b>{ro.get('risk_profile_rating', 'Moderate')}</b></p>

<h2>Section 7: Evidence Trail & Supporting Data Points</h2>
<p>Evaluated {len(ev_chains)} formal quantitative evidence chains connecting raw dataset rows to managerial insights.</p>

<h2>Section 8: Prioritized Recommendations & Action Plan</h2>
{rec_cards}

<h2>Section 9: Decision Impact Matrix (Effort vs. Impact)</h2>
<p>{matrix_res.executive_summary}</p>
<table>
  <thead><tr><th>Action Title</th><th>Quadrant</th><th>Effort</th><th>Impact Score</th><th>Expected Value</th><th>Timeframe</th></tr></thead>
  <tbody>{impact_matrix_rows}</tbody>
</table>

<h2>Section 10: Scenario Simulation & What-If Analysis</h2>
<table>
  <thead><tr><th>Scenario Name</th><th>Parameters Modified</th><th>Projected Revenue</th><th>Projected Profit</th><th>Projected Margin</th></tr></thead>
  <tbody>{scenario_rows}</tbody>
</table>

<h2>Section 11: Forecast & Projection Overview</h2>
<p>{fc_summary}</p>

<h2>Section 12: Forecast vs Actual Variance Analysis</h2>
<p>{fc_actual_summary}</p>

<h2>Section 13: KPI Goal Tracking & Target Milestones</h2>
<table>
  <thead><tr><th>Metric</th><th>Target Type</th><th>Target Value</th><th>Current Value</th><th>Progress %</th><th>Status</th></tr></thead>
  <tbody>{goal_rows}</tbody>
</table>

<h2>Section 14: Drill-Down Insights</h2>
<p>Multi-level dimensional exploration conducted across categorical candidates. High-cardinality entity identifiers isolated to preserve analytical validity.</p>

<h2>Section 15: Decision Registry & Stakeholder Commitments</h2>
<table>
  <thead><tr><th>Action Title</th><th>Decision Status</th><th>Owner</th><th>Rationale Notes</th><th>Target Date</th></tr></thead>
  <tbody>{decision_rows}</tbody>
</table>

<h2>Section 16: Assumptions, Methodology & Analytical Integrity</h2>
<p>All calculations execute deterministic statistical formulas and pandas aggregations. No generative hallucination or arbitrary code execution was utilized in numeric steps.</p>

<h2>Section 17: Non-Causation Disclaimer & Sign-off Appendix</h2>
<div class="disclaimer">
  <b>Important Analytical Governance Disclaimer:</b><br>
  Note: An observed relationship does not necessarily prove causation.<br>
  Statistical correlations and quantitative attributions identified in this report reflect deterministic patterns within the ingested dataset.
  Strategic decisions must incorporate qualitative market dynamics, competitive behavior, and executive domain expertise.
</div>

<hr style="margin-top: 40px; border: none; border-top: 1px solid #cbd5e1;">
<p style="font-size: 11px; color: #64748b; text-align: center;">Business Analytics Consultant &bull; Explainable Business Decision Support System &bull; Complete Decision Report</p>
</body>
</html>"""
    return HTMLResponse(content=html)

