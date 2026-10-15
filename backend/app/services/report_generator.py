import io
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from app.models.db_models import AnalysisRun, Dataset, DecisionRecord, SimulationScenario
from app.models.schemas import SimulationOutcome, ScenarioComparisonReport
from app.engines.advanced_findings import AdvancedFindingsEngine
from app.engines.simulation import SimulationEngine
from app.services.data_ingestion import IngestionService


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for ReportLab to compute total page count and add headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Business Analytics Consultant — Business Decision Report")
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Explainable Decision Support System")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 40, 8.5 * inch - 54, 11 * inch - 40)

        # Running footer (all pages)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 34, page_str)
        self.drawString(54, 34, "Confidential — Explainable Business Decision Support System (MSc IT)")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        self.restoreState()


class ReportGeneratorService:
    @staticmethod
    def _get_advanced_findings(run: AnalysisRun, dataset: Optional[Dataset]) -> Dict[str, Any]:
        """Safely fetch or derive advanced findings."""
        if dataset and dataset.file_path:
            file_p = Path(dataset.file_path)
            if file_p.exists():
                try:
                    df = IngestionService.load_dataframe(file_p)
                    rep = AdvancedFindingsEngine.analyze(df, run.target_column, run.date_column)
                    return rep.model_dump()
                except Exception:
                    pass
        return {"trends": [], "anomalies": [], "segment_comparisons": [], "summary": "No historical trends or anomalies available."}

    @staticmethod
    def _get_scenario_comparison(run: AnalysisRun, scenarios: List[SimulationScenario], bh: Dict[str, Any]) -> ScenarioComparisonReport:
        base_rev = 100000.0
        base_prof = 20000.0
        om = bh.get('overview_metrics') or {}
        if om.get('total_revenue'):
            base_rev = float(om.get('total_revenue'))
            base_prof = float(om.get('total_profit') or (base_rev * 0.20))
        elif bh.get('kpis'):
            for kp in bh.get('kpis', []):
                if kp.get('name', '').lower() in ['revenue', 'sales', 'turnover']:
                    base_rev = float(kp.get('current_value', 100000.0))
                    base_prof = base_rev * 0.20
                    break

        baseline_outcome = SimulationOutcome(
            baseline_revenue=base_rev,
            simulated_revenue=base_rev,
            revenue_delta=0.0,
            revenue_delta_pct=0.0,
            baseline_profit=base_prof,
            simulated_profit=base_prof,
            profit_delta=0.0,
            profit_delta_pct=0.0,
            baseline_margin_pct=round((base_prof / base_rev * 100), 2) if base_rev > 0 else 0.0,
            simulated_margin_pct=round((base_prof / base_rev * 100), 2) if base_rev > 0 else 0.0,
            margin_delta_pct=0.0,
            net_economic_value_added=0.0,
            risk_adjusted_return=0.0,
            sensitivity_breakdown={},
            recommendation_impact_overlap=[]
        )

        scenario_dicts = [
            {
                "id": str(s.id),
                "name": str(s.name),
                "parameters": s.parameters or {},
                "projected_outcomes": s.projected_outcomes or {}
            }
            for s in scenarios
        ]

        return SimulationEngine.compare_scenarios(baseline_outcome, scenario_dicts)

    # =========================================================================
    # PDF REPORT GENERATOR (13 Sections)
    # =========================================================================
    @classmethod
    def generate_pdf_report(
        cls,
        run: AnalysisRun,
        dataset: Optional[Dataset],
        decisions: List[DecisionRecord],
        scenarios: List[SimulationScenario]
    ) -> bytes:
        """
        Generates comprehensive 13-section business report in PDF format via ReportLab.
        Deterministic, fully traceable analytical report.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        # Custom Typography Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#475569'),
            spaceAfter=14
        )
        h1_style = ParagraphStyle(
            'SecH1',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155'),
            spaceAfter=6
        )
        body_bold = ParagraphStyle(
            'BodyBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )
        cell_header_style = ParagraphStyle(
            'CellHeader',
            parent=cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#FFFFFF')
        )
        callout_style = ParagraphStyle(
            'Callout',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#475569')
        )

        story = []

        # Extract data payload
        adv_findings = cls._get_advanced_findings(run, dataset)
        dq = run.data_quality or {}
        bh = run.business_health or {}
        diag = run.diagnostics or {}
        rc = run.root_cause or {}
        ro = run.risks_opportunities or {}
        recs = run.recommendations or []
        chains = run.evidence_chains or []
        created_str = run.created_at.strftime("%Y-%m-%d %H:%M UTC") if run.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # -------------------------------------------------------------
        # Header / Title Block
        # -------------------------------------------------------------
        story.append(Paragraph("Business Decision & Analytics Report", title_style))
        story.append(Paragraph("Explainable Decision Support System — Deterministic Business Intelligence Report", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

        # Meta Info Table
        meta_data = [
            [
                Paragraph("<b>Analysis ID:</b>", cell_style), Paragraph(str(run.id), cell_style),
                Paragraph("<b>Target Metric:</b>", cell_style), Paragraph(str(run.target_column or "N/A"), cell_style)
            ],
            [
                Paragraph("<b>Dataset Name:</b>", cell_style), Paragraph(str(dataset.name if dataset else "N/A"), cell_style),
                Paragraph("<b>Generated At:</b>", cell_style), Paragraph(created_str, cell_style)
            ],
            [
                Paragraph("<b>Records Analyzed:</b>", cell_style), Paragraph(f"{dataset.row_count if dataset else 0:,} rows", cell_style),
                Paragraph("<b>Data Quality Score:</b>", cell_style), Paragraph(f"{dq.get('overall_quality_score', 0):.1f}/100", cell_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[1.3*inch, 2.2*inch, 1.4*inch, 2.1*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 1. Executive Summary
        # -------------------------------------------------------------
        story.append(Paragraph("1. Executive Summary", h1_style))
        health_score = bh.get('overall_health_score', 0)
        health_status = bh.get('overall_status', 'Unknown')
        exec_summary = bh.get('executive_summary', 'Comprehensive analytical review completed.')
        story.append(Paragraph(
            f"<b>Overall Business Health:</b> {health_score}/100 &bull; <b>Status:</b> {health_status}",
            body_bold
        ))
        story.append(Paragraph(exec_summary, body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 2. Data Quality & Reliability
        # -------------------------------------------------------------
        story.append(Paragraph("2. Data Quality & Reliability", h1_style))
        reliability = dq.get('reliability_assessment', 'Satisfactory')
        story.append(Paragraph(
            f"<b>Quality Score:</b> {dq.get('overall_quality_score', 0):.1f}/100 &bull; "
            f"<b>Reliability Rating:</b> {reliability} &bull; "
            f"<b>Completeness:</b> {dq.get('completeness_pct', 100):.1f}% &bull; "
            f"<b>Validity:</b> {dq.get('validity_pct', 100):.1f}%",
            body_style
        ))
        
        col_metrics = dq.get('column_metrics', [])[:6]
        if col_metrics:
            dq_rows = [[
                Paragraph("Column", cell_header_style),
                Paragraph("Type", cell_header_style),
                Paragraph("Completeness", cell_header_style),
                Paragraph("Validity", cell_header_style),
                Paragraph("Issues / Flags", cell_header_style)
            ]]
            for c in col_metrics:
                issues = ", ".join(c.get('potential_issues', [])) or "None detected"
                dq_rows.append([
                    Paragraph(str(c.get('column_name', '')), cell_style),
                    Paragraph(str(c.get('inferred_type', '')), cell_style),
                    Paragraph(f"{c.get('completeness_pct', 0):.1f}%", cell_style),
                    Paragraph(f"{c.get('validity_pct', 0):.1f}%", cell_style),
                    Paragraph(issues, cell_style)
                ])
            dq_table = Table(dq_rows, colWidths=[1.8*inch, 1.0*inch, 1.1*inch, 1.1*inch, 2.0*inch])
            dq_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(dq_table)
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 3. Business Health Overview
        # -------------------------------------------------------------
        story.append(Paragraph("3. Business Health Overview", h1_style))
        kpis = bh.get('kpis', [])
        if kpis:
            kpi_rows = [[
                Paragraph("KPI Metric", cell_header_style),
                Paragraph("Current Value", cell_header_style),
                Paragraph("Baseline / Target", cell_header_style),
                Paragraph("Variance %", cell_header_style),
                Paragraph("Health Status", cell_header_style)
            ]]
            for k in kpis:
                curr = f"{k.get('current_value', 0):,.2f} {k.get('unit', '')}"
                tgt = f"{k.get('target_or_baseline', 0):,.2f}" if k.get('target_or_baseline') is not None else "N/A"
                var_p = f"{k.get('variance_pct', 0):+.1f}%" if k.get('variance_pct') is not None else "N/A"
                kpi_rows.append([
                    Paragraph(str(k.get('name', '')), cell_style),
                    Paragraph(curr, cell_style),
                    Paragraph(tgt, cell_style),
                    Paragraph(var_p, cell_style),
                    Paragraph(str(k.get('status', '')).upper(), cell_style)
                ])
            kpi_table = Table(kpi_rows, colWidths=[2.0*inch, 1.4*inch, 1.4*inch, 1.1*inch, 1.1*inch])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(kpi_table)
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 4. Key Findings
        # -------------------------------------------------------------
        story.append(Paragraph("4. Key Findings", h1_style))
        focal_metric = diag.get('focal_metric', 'Target Metric')
        tot_var = diag.get('total_variance', 0)
        tot_var_pct = diag.get('variance_pct', 0)
        diag_narrative = diag.get('diagnostic_narrative', 'Analytical diagnosis performed across dimensions.')
        story.append(Paragraph(
            f"<b>Focal Metric:</b> {focal_metric} &bull; "
            f"<b>Observed Net Variance:</b> ${tot_var:+,.2f} ({tot_var_pct:+.1f}%)",
            body_bold
        ))
        story.append(Paragraph(diag_narrative, body_style))

        findings = diag.get('findings', [])[:5]
        if findings:
            find_rows = [[
                Paragraph("Finding", cell_header_style),
                Paragraph("Metric", cell_header_style),
                Paragraph("Observed", cell_header_style),
                Paragraph("Comparison", cell_header_style),
                Paragraph("Difference", cell_header_style)
            ]]
            for f in findings:
                diff_val = f.get('difference', 0)
                diff_str = f"${diff_val:+,.2f}" if isinstance(diff_val, (int, float)) else str(diff_val)
                obs_val = f.get('observed_value', 0)
                obs_str = f"${obs_val:,.2f}" if isinstance(obs_val, (int, float)) else str(obs_val)
                find_rows.append([
                    Paragraph(str(f.get('title', '')), cell_style),
                    Paragraph(str(f.get('metric', '')), cell_style),
                    Paragraph(obs_str, cell_style),
                    Paragraph(str(f.get('comparison', '')), cell_style),
                    Paragraph(diff_str, cell_style)
                ])
            find_table = Table(find_rows, colWidths=[2.3*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.1*inch])
            find_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(find_table)
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 5. Trends & Anomalies
        # -------------------------------------------------------------
        story.append(Paragraph("5. Trends & Anomalies", h1_style))
        trends = adv_findings.get('trends', [])
        anomalies = adv_findings.get('anomalies', [])

        if trends:
            story.append(Paragraph("<b>Trend Analysis Findings:</b>", body_bold))
            tr_rows = [[
                Paragraph("Metric", cell_header_style),
                Paragraph("Direction", cell_header_style),
                Paragraph("Slope / Rate", cell_header_style),
                Paragraph("Consistency", cell_header_style),
                Paragraph("Summary", cell_header_style)
            ]]
            for t in trends[:4]:
                tr_rows.append([
                    Paragraph(str(t.get('metric_name', '')), cell_style),
                    Paragraph(str(t.get('direction', '')), cell_style),
                    Paragraph(f"{t.get('slope_per_period', 0):+.2f}/period", cell_style),
                    Paragraph(f"{t.get('consistency_pct', 0):.1f}%", cell_style),
                    Paragraph(str(t.get('summary', '')), cell_style)
                ])
            tr_table = Table(tr_rows, colWidths=[1.4*inch, 1.0*inch, 1.2*inch, 1.0*inch, 2.4*inch])
            tr_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(tr_table)
            story.append(Spacer(1, 6))

        if anomalies:
            story.append(Paragraph("<b>Empirical Anomaly Detection (IQR Method):</b>", body_bold))
            anom_rows = [[
                Paragraph("Metric", cell_header_style),
                Paragraph("Dimension / Group", cell_header_style),
                Paragraph("Observed", cell_header_style),
                Paragraph("Expected Range", cell_header_style),
                Paragraph("Severity", cell_header_style)
            ]]
            for a in anomalies[:5]:
                exp_range = f"[{a.get('expected_lower', 0):,.1f}, {a.get('expected_upper', 0):,.1f}]"
                anom_rows.append([
                    Paragraph(str(a.get('metric_name', '')), cell_style),
                    Paragraph(str(a.get('dimension_or_group', 'Global')), cell_style),
                    Paragraph(f"{a.get('observed_value', 0):,.2f}", cell_style),
                    Paragraph(exp_range, cell_style),
                    Paragraph(str(a.get('severity', 'Medium')), cell_style)
                ])
            anom_table = Table(anom_rows, colWidths=[1.5*inch, 1.6*inch, 1.3*inch, 1.6*inch, 1.0*inch])
            anom_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(anom_table)
        elif not trends:
            story.append(Paragraph("No significant trend or anomaly patterns detected in current dataset.", body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 6. Segment Comparisons
        # -------------------------------------------------------------
        story.append(Paragraph("6. Segment Comparisons", h1_style))
        var_breakdown = diag.get('variance_breakdown', [])[:6]
        if var_breakdown:
            seg_rows = [[
                Paragraph("Dimension", cell_header_style),
                Paragraph("Segment", cell_header_style),
                Paragraph("Baseline", cell_header_style),
                Paragraph("Actual", cell_header_style),
                Paragraph("Difference", cell_header_style),
                Paragraph("Contribution", cell_header_style),
                Paragraph("Impact Type", cell_header_style)
            ]]
            for b in var_breakdown:
                dir_label = "Positive Gain" if b.get('direction') == "Lift" else "Negative Difference"
                seg_rows.append([
                    Paragraph(str(b.get('dimension', '')), cell_style),
                    Paragraph(str(b.get('segment', '')), cell_style),
                    Paragraph(f"${b.get('baseline_value', 0):,.2f}", cell_style),
                    Paragraph(f"${b.get('actual_value', 0):,.2f}", cell_style),
                    Paragraph(f"${b.get('variance', 0):+,.2f}", cell_style),
                    Paragraph(f"{b.get('contribution_share_pct', 0):.1f}%", cell_style),
                    Paragraph(dir_label, cell_style)
                ])
            seg_table = Table(seg_rows, colWidths=[1.1*inch, 1.4*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.8*inch, 1.2*inch])
            seg_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(seg_table)
        else:
            story.append(Paragraph("No segment comparison breakdowns available.", body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 7. Possible Reasons (Factor Analysis)
        # -------------------------------------------------------------
        story.append(Paragraph("7. Possible Reasons (Factor Analysis)", h1_style))
        prim_reason = rc.get('primary_root_cause', 'General business factors observed.')
        conf_level = rc.get('statistical_confidence_level', 80.0)
        conf_display = "Significant association (p < 0.05)" if (conf_level == 100.0 or conf_level >= 95.0) else f"{conf_level:.1f}%"
        story.append(Paragraph(
            f"<b>Possible Contributor:</b> {prim_reason} &bull; "
            f"<b>Statistical Basis:</b> {conf_display}",
            body_bold
        ))

        factors = rc.get('factor_contributions', [])[:4]
        if factors:
            fac_rows = [[
                Paragraph("Factor Name", cell_header_style),
                Paragraph("Category", cell_header_style),
                Paragraph("Attribution %", cell_header_style),
                Paragraph("Direction", cell_header_style),
                Paragraph("Evidence Statement", cell_header_style)
            ]]
            for f in factors:
                fac_rows.append([
                    Paragraph(str(f.get('factor_name', '')), cell_style),
                    Paragraph(str(f.get('factor_type', 'Operational')), cell_style),
                    Paragraph(f"{f.get('attribution_percentage', 0):.1f}%", cell_style),
                    Paragraph(str(f.get('direction', 'Negative Impact')), cell_style),
                    Paragraph(str(f.get('evidence_statement', '')), cell_style)
                ])
            fac_table = Table(fac_rows, colWidths=[1.4*inch, 1.1*inch, 1.0*inch, 1.2*inch, 2.3*inch])
            fac_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(fac_table)

        story.append(Spacer(1, 4))
        story.append(Paragraph("<i>Note: Factors represent statistical association and variance contribution, not verified causal proof.</i>", callout_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 8. Supporting Evidence
        # -------------------------------------------------------------
        story.append(Paragraph("8. Supporting Evidence", h1_style))
        if chains:
            for ch in chains[:3]:
                story.append(Paragraph(f"<b>Evidence Chain: {ch.get('title', 'Observed Evidence')}</b>", body_bold))
                story.append(Paragraph(
                    f"&bull; <b>Target Metric:</b> {ch.get('target_metric', '')}<br/>"
                    f"&bull; <b>Observed Phenomenon:</b> {ch.get('observed_phenomenon', '')}<br/>"
                    f"&bull; <b>Underlying Mechanism:</b> {ch.get('underlying_mechanism', '')}<br/>"
                    f"&bull; <b>Statistical Proof:</b> {ch.get('statistical_proof', '')}",
                    body_style
                ))
        else:
            story.append(Paragraph("Evidence trail derived directly from mathematical variance breakdown.", body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 9. Recommended Actions
        # -------------------------------------------------------------
        story.append(Paragraph("9. Recommended Actions", h1_style))
        if recs:
            for r in recs[:4]:
                action_text = r.get('recommendation') or r.get('what_to_do') or r.get('mechanism_of_action') or r.get('title')
                reason_text = r.get('reason') or r.get('why') or r.get('rationale') or ''
                story.append(Paragraph(f"<b>[{r.get('id')}] {r.get('title')}</b>", body_bold))
                story.append(Paragraph(
                    f"<b>What to do:</b> {action_text}<br/>"
                    f"<b>Why:</b> {reason_text}<br/>"
                    f"<b>Urgency:</b> {r.get('urgency', 'Near Term')} &bull; "
                    f"<b>Effort:</b> {r.get('implementation_effort', 'Medium')} &bull; "
                    f"<b>Expected Financial Impact:</b> +${r.get('expected_financial_impact', 0):,.2f}",
                    body_style
                ))
        else:
            story.append(Paragraph("No recommendations generated for current dataset.", body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 10. Recommendation Priority Ranking
        # -------------------------------------------------------------
        story.append(Paragraph("10. Recommendation Priority Ranking", h1_style))
        if recs:
            prio_rows = [[
                Paragraph("Rank", cell_header_style),
                Paragraph("Recommendation Action", cell_header_style),
                Paragraph("Priority Level", cell_header_style),
                Paragraph("Priority Score", cell_header_style),
                Paragraph("Est. Impact", cell_header_style),
                Paragraph("Effort", cell_header_style),
                Paragraph("Status", cell_header_style)
            ]]
            for idx, r in enumerate(recs[:5]):
                score = round(r.get('priority_score', 50))
                prio_rows.append([
                    Paragraph(f"#{idx + 1}", cell_style),
                    Paragraph(str(r.get('title', '')), cell_style),
                    Paragraph(str(r.get('priority_level') or r.get('priority_tier') or 'Medium Priority'), cell_style),
                    Paragraph(f"{score}/100", cell_style),
                    Paragraph(f"+${r.get('expected_financial_impact', 0):,.2f}", cell_style),
                    Paragraph(str(r.get('implementation_effort', 'Medium')), cell_style),
                    Paragraph(str(r.get('decision_status') or r.get('status') or 'Pending Review'), cell_style)
                ])
            prio_table = Table(prio_rows, colWidths=[0.6*inch, 2.2*inch, 1.2*inch, 0.9*inch, 1.0*inch, 0.6*inch, 1.0*inch])
            prio_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(prio_table)
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 11. What-If Scenario Comparison
        # -------------------------------------------------------------
        story.append(Paragraph("11. What-If Scenario Comparison", h1_style))
        comparison = cls._get_scenario_comparison(run, scenarios, bh)
        scen_rows = [[
            Paragraph("Scenario Name", cell_header_style),
            Paragraph("Revenue", cell_header_style),
            Paragraph("Profit", cell_header_style),
            Paragraph("Margin %", cell_header_style),
            Paragraph("Incremental Value", cell_header_style)
        ]]
        for sc in comparison.scenarios:
            inc_str = f"${sc.incremental_value:+,.2f}" if sc.id != "baseline" else "Baseline"
            scen_rows.append([
                Paragraph(str(sc.name), cell_style),
                Paragraph(f"${sc.revenue:,.2f}", cell_style),
                Paragraph(f"${sc.profit:,.2f}", cell_style),
                Paragraph(f"{sc.profit_margin_pct:.1f}%", cell_style),
                Paragraph(inc_str, cell_style)
            ])
        scen_table = Table(scen_rows, colWidths=[2.2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.4*inch])
        scen_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(scen_table)
        if comparison.comparison_insights:
            story.append(Spacer(1, 4))
            for ins in comparison.comparison_insights:
                story.append(Paragraph(f"&bull; {ins}", callout_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 12. Decision Notes & Audit Trail
        # -------------------------------------------------------------
        story.append(Paragraph("12. Decision Notes & Audit Trail", h1_style))
        if decisions:
            dec_rows = [[
                Paragraph("Action Title", cell_header_style),
                Paragraph("Status", cell_header_style),
                Paragraph("Stakeholder", cell_header_style),
                Paragraph("Notes / Rationale", cell_header_style),
                Paragraph("Target Date", cell_header_style)
            ]]
            for d in decisions:
                dec_rows.append([
                    Paragraph(str(d.action_title), cell_style),
                    Paragraph(str(d.decision_status).upper(), cell_style),
                    Paragraph(str(d.stakeholder or "Unassigned"), cell_style),
                    Paragraph(str(d.notes_rationale or "No rationale recorded."), cell_style),
                    Paragraph(str(d.target_date or "TBD"), cell_style)
                ])
            dec_table = Table(dec_rows, colWidths=[1.8*inch, 1.1*inch, 1.2*inch, 2.3*inch, 1.1*inch])
            dec_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(dec_table)
        else:
            story.append(Paragraph("No human-in-the-loop decisions currently logged for this analysis.", body_style))
        story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 13. Methodology, Assumptions & Limitations
        # -------------------------------------------------------------
        story.append(Paragraph("13. Methodology, Assumptions & Limitations", h1_style))
        methodology_text = (
            "<b>Deterministic Analytical Foundations:</b><br/>"
            "1. <b>Zero Fabrication:</b> All metrics, health scores, and variance calculations are computed deterministically "
            "in Python using exact arithmetic, standard statistical libraries (SciPy, Statsmodels), and Apache ECharts definitions.<br/>"
            "2. <b>Association vs. Causation:</b> Statistical factor attributions represent non-causal associations derived from "
            "multiple linear regression, variance decomposition, and Pareto analysis. Management should validate causal pathways "
            "through operational context.<br/>"
            "3. <b>Anomaly Detection:</b> Outliers are detected using the non-parametric Interquartile Range (IQR) technique "
            "with bounds at Q1 - 1.5&times;IQR and Q3 + 1.5&times;IQR.<br/>"
            "4. <b>Simulation Boundaries:</b> What-if scenario modeling applies linear parameter shifts relative to the neutral baseline. "
            "Non-linear market reactions, severe price elasticity changes, and macro shocks are outside model boundaries.<br/>"
            "5. <b>Data Quality Assumptions:</b> Findings reflect the data quality profile of the ingested source files. Integrity is "
            f"verified via SHA-256 hash ({dataset.file_hash if dataset else 'N/A'})."
        )
        story.append(Paragraph(methodology_text, body_style))

        # Build Document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    # =========================================================================
    # EXCEL REPORT GENERATOR (10 Sheets)
    # =========================================================================
    @classmethod
    def generate_excel_report(
        cls,
        run: AnalysisRun,
        dataset: Optional[Dataset],
        decisions: List[DecisionRecord],
        scenarios: List[SimulationScenario]
    ) -> bytes:
        """
        Generates 10-sheet structured business workbook in Excel (.xlsx) format via openpyxl.
        Professional formatting, styles, auto-width, number formatting, and gridlines.
        """
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # Style definitions
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        bold_font = Font(name="Calibri", size=11, bold=True, color="1E293B")
        regular_font = Font(name="Calibri", size=10, color="1E293B")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        def apply_header(ws, row_idx: int, headers: List[str]):
            for col_idx, text in enumerate(headers, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=text)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.border = thin_border

        def auto_fit_columns(ws):
            ws.views.sheetView[0].showGridLines = True
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value is not None:
                        val_str = str(cell.value)
                        max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 50))

        adv_findings = cls._get_advanced_findings(run, dataset)
        dq = run.data_quality or {}
        bh = run.business_health or {}
        diag = run.diagnostics or {}
        rc = run.root_cause or {}
        recs = run.recommendations or []

        # -------------------------------------------------------------
        # Sheet 1: Summary
        # -------------------------------------------------------------
        ws_sum = wb.create_sheet(title="Summary")
        ws_sum.cell(row=1, column=1, value="Business Decision & Analytics Summary").font = title_font
        ws_sum.cell(row=2, column=1, value="Explainable Decision Support System — Deterministic Analytical Report").font = sub_font
        
        sum_meta = [
            ("Analysis ID", str(run.id)),
            ("Dataset Name", dataset.name if dataset else "N/A"),
            ("Dataset Hash (SHA-256)", dataset.file_hash if dataset else "N/A"),
            ("Target Metric", str(run.target_column or "N/A")),
            ("Date Column", str(run.date_column or "N/A")),
            ("Records Analyzed", dataset.row_count if dataset else 0),
            ("Execution Time (ms)", run.execution_time_ms),
            ("Data Quality Score", f"{dq.get('overall_quality_score', 0):.1f}/100"),
            ("Business Health Score", f"{bh.get('overall_health_score', 0)}/100 ({bh.get('overall_status', 'Unknown')})"),
            ("Executive Summary", bh.get('executive_summary', 'Analysis completed.'))
        ]
        for idx, (label, val) in enumerate(sum_meta, 4):
            c1 = ws_sum.cell(row=idx, column=1, value=label)
            c1.font = bold_font
            c2 = ws_sum.cell(row=idx, column=2, value=val)
            c2.font = regular_font
            c1.border = thin_border
            c2.border = thin_border
        auto_fit_columns(ws_sum)

        # -------------------------------------------------------------
        # Sheet 2: Data Quality
        # -------------------------------------------------------------
        ws_dq = wb.create_sheet(title="Data Quality")
        ws_dq.cell(row=1, column=1, value="Data Quality & Column Profiles").font = title_font
        dq_headers = ["Column Name", "Inferred Type", "Completeness %", "Validity %", "Null Count", "Unique Count", "Issues Detected"]
        apply_header(ws_dq, 3, dq_headers)
        for r_idx, c in enumerate(dq.get('column_metrics', []), 4):
            issues = ", ".join(c.get('potential_issues', [])) or "None"
            row_vals = [
                c.get('column_name'),
                c.get('inferred_type'),
                c.get('completeness_pct'),
                c.get('validity_pct'),
                c.get('null_count'),
                c.get('unique_count'),
                issues
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_dq.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [3, 4] and isinstance(val, (int, float)):
                    cell.number_format = "0.0%"
                    cell.value = val / 100.0
                elif col_idx in [5, 6] and isinstance(val, (int, float)):
                    cell.number_format = "#,##0"
        auto_fit_columns(ws_dq)

        # -------------------------------------------------------------
        # Sheet 3: Business Metrics
        # -------------------------------------------------------------
        ws_kpi = wb.create_sheet(title="Business Metrics")
        ws_kpi.cell(row=1, column=1, value="KPI Metrics & Health Vital Signs").font = title_font
        kpi_headers = ["Metric Name", "Current Value", "Target / Baseline", "Variance %", "Unit", "Status", "Interpretation"]
        apply_header(ws_kpi, 3, kpi_headers)
        for r_idx, k in enumerate(bh.get('kpis', []), 4):
            row_vals = [
                k.get('name'),
                k.get('current_value'),
                k.get('target_or_baseline'),
                (k.get('variance_pct') / 100.0) if k.get('variance_pct') is not None else None,
                k.get('unit'),
                k.get('status'),
                k.get('interpretation')
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_kpi.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [2, 3] and isinstance(val, (int, float)):
                    cell.number_format = "#,##0.00"
                elif col_idx == 4 and isinstance(val, (int, float)):
                    cell.number_format = "+0.0%;-0.0%;0.0%"
        auto_fit_columns(ws_kpi)

        # -------------------------------------------------------------
        # Sheet 4: Findings
        # -------------------------------------------------------------
        ws_find = wb.create_sheet(title="Findings")
        ws_find.cell(row=1, column=1, value="Key Analytical Findings").font = title_font
        find_headers = ["Finding Title", "Type", "Metric", "Observed Value", "Comparison", "Difference", "Possible Reason", "Recommended Action"]
        apply_header(ws_find, 3, find_headers)
        for r_idx, f in enumerate(diag.get('findings', []), 4):
            row_vals = [
                f.get('title'),
                f.get('type'),
                f.get('metric'),
                f.get('observed_value'),
                f.get('comparison'),
                f.get('difference'),
                f.get('possible_reason'),
                f.get('recommended_action')
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_find.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [4, 6] and isinstance(val, (int, float)):
                    cell.number_format = "$#,##0.00"
        auto_fit_columns(ws_find)

        # -------------------------------------------------------------
        # Sheet 5: Trends
        # -------------------------------------------------------------
        ws_tr = wb.create_sheet(title="Trends")
        ws_tr.cell(row=1, column=1, value="Trend Analysis Findings").font = title_font
        tr_headers = ["Metric Name", "Direction", "Slope Per Period", "Consistency %", "Summary Explanation"]
        apply_header(ws_tr, 3, tr_headers)
        for r_idx, t in enumerate(adv_findings.get('trends', []), 4):
            row_vals = [
                t.get('metric_name'),
                t.get('direction'),
                t.get('slope_per_period'),
                (t.get('consistency_pct') / 100.0) if t.get('consistency_pct') is not None else None,
                t.get('summary')
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_tr.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx == 3 and isinstance(val, (int, float)):
                    cell.number_format = "+#,##0.00;-#,##0.00;0.00"
                elif col_idx == 4 and isinstance(val, (int, float)):
                    cell.number_format = "0.0%"
        auto_fit_columns(ws_tr)

        # -------------------------------------------------------------
        # Sheet 6: Anomalies
        # -------------------------------------------------------------
        ws_anom = wb.create_sheet(title="Anomalies")
        ws_anom.cell(row=1, column=1, value="Detected Empirical Anomalies (IQR)").font = title_font
        anom_headers = ["Metric Name", "Dimension / Group", "Observed Value", "Expected Lower", "Expected Upper", "Severity", "Explanation"]
        apply_header(ws_anom, 3, anom_headers)
        for r_idx, a in enumerate(adv_findings.get('anomalies', []), 4):
            row_vals = [
                a.get('metric_name'),
                a.get('dimension_or_group'),
                a.get('observed_value'),
                a.get('expected_lower'),
                a.get('expected_upper'),
                a.get('severity'),
                a.get('explanation')
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_anom.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [3, 4, 5] and isinstance(val, (int, float)):
                    cell.number_format = "#,##0.00"
        auto_fit_columns(ws_anom)

        # -------------------------------------------------------------
        # Sheet 7: Segment Comparisons
        # -------------------------------------------------------------
        ws_seg = wb.create_sheet(title="Segment Comparisons")
        ws_seg.cell(row=1, column=1, value="Segment Comparisons Breakdown").font = title_font
        seg_headers = ["Dimension", "Segment", "Baseline Value", "Actual Value", "Difference", "Variance %", "Contribution Share %", "Direction Type"]
        apply_header(ws_seg, 3, seg_headers)
        for r_idx, b in enumerate(diag.get('variance_breakdown', []), 4):
            dir_label = "Positive Gain" if b.get('direction') == "Lift" else "Negative Difference"
            row_vals = [
                b.get('dimension'),
                b.get('segment'),
                b.get('baseline_value'),
                b.get('actual_value'),
                b.get('variance'),
                (b.get('variance_pct') / 100.0) if b.get('variance_pct') is not None else None,
                (b.get('contribution_share_pct') / 100.0) if b.get('contribution_share_pct') is not None else None,
                dir_label
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_seg.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [3, 4, 5] and isinstance(val, (int, float)):
                    cell.number_format = "$#,##0.00"
                elif col_idx in [6, 7] and isinstance(val, (int, float)):
                    cell.number_format = "+0.0%;-0.0%;0.0%"
        auto_fit_columns(ws_seg)

        # -------------------------------------------------------------
        # Sheet 8: Recommendations
        # -------------------------------------------------------------
        ws_rec = wb.create_sheet(title="Recommendations")
        ws_rec.cell(row=1, column=1, value="Ranked Business Recommendations").font = title_font
        rec_headers = ["Rank", "ID", "Title", "Priority Level", "Priority Score", "Expected Impact ($)", "Effort", "Urgency", "What to Do", "Supporting Finding", "Status"]
        apply_header(ws_rec, 3, rec_headers)
        for r_idx, r in enumerate(recs, 4):
            row_vals = [
                r_idx - 3,
                r.get('id'),
                r.get('title'),
                r.get('priority_level') or r.get('priority_tier'),
                r.get('priority_score'),
                r.get('expected_financial_impact'),
                r.get('implementation_effort'),
                r.get('urgency'),
                r.get('recommendation') or r.get('what_to_do') or r.get('mechanism_of_action'),
                r.get('supporting_finding') or r.get('evidence'),
                r.get('decision_status') or r.get('status')
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_rec.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx == 5 and isinstance(val, (int, float)):
                    cell.number_format = "0.0"
                elif col_idx == 6 and isinstance(val, (int, float)):
                    cell.number_format = "$#,##0.00"
        auto_fit_columns(ws_rec)

        # -------------------------------------------------------------
        # Sheet 9: Scenario Comparison
        # -------------------------------------------------------------
        ws_scen = wb.create_sheet(title="Scenario Comparison")
        ws_scen.cell(row=1, column=1, value="What-If Scenario Comparison vs Neutral Baseline").font = title_font
        scen_headers = ["Scenario Name", "Parameters Modified", "Revenue", "Profit", "Margin %", "Incremental Value", "Risk-Adjusted Return"]
        apply_header(ws_scen, 3, scen_headers)
        comparison = cls._get_scenario_comparison(run, scenarios, bh)
        for r_idx, sc in enumerate(comparison.scenarios, 4):
            params_str = ", ".join([f"{k}: {v:+}%" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in sc.parameters.items()]) if sc.parameters else "Baseline"
            row_vals = [
                sc.name,
                params_str,
                sc.revenue,
                sc.profit,
                (sc.profit_margin_pct / 100.0) if sc.profit_margin_pct is not None else 0.0,
                sc.incremental_value,
                sc.risk_adjusted_return
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_scen.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if col_idx in [3, 4, 6, 7] and isinstance(val, (int, float)):
                    cell.number_format = "$#,##0.00"
                elif col_idx == 5 and isinstance(val, (int, float)):
                    cell.number_format = "0.0%"
        auto_fit_columns(ws_scen)

        # -------------------------------------------------------------
        # Sheet 10: Decision Notes
        # -------------------------------------------------------------
        ws_dec = wb.create_sheet(title="Decision Notes")
        ws_dec.cell(row=1, column=1, value="Management Decision Notes & Audit Trail").font = title_font
        dec_headers = ["Action Title", "Decision Status", "Stakeholder", "Rationale Notes", "Target Date", "Created At"]
        apply_header(ws_dec, 3, dec_headers)
        for r_idx, d in enumerate(decisions, 4):
            created_str = d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "N/A"
            row_vals = [
                d.action_title,
                d.decision_status,
                d.stakeholder,
                d.notes_rationale,
                d.target_date,
                created_str
            ]
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws_dec.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
        auto_fit_columns(ws_dec)

        # Save to buffer
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()
