import time
from typing import Optional, Dict, Any
from pathlib import Path
import pandas as pd
from app.services.data_ingestion import IngestionService
from app.services.quality_profiler import QualityProfiler
from app.engines.business_health import BusinessHealthEngine
from app.engines.diagnostic import DiagnosticEngine
from app.engines.root_cause import RootCauseEngine
from app.engines.risk_opportunity import RiskOpportunityEngine
from app.engines.evidence_builder import EvidenceBuilder
from app.engines.recommendation import RecommendationEngine
from app.models.schemas import AnalysisRunResponse, DecisionRecordSchema


class DecisionPipeline:
    @staticmethod
    def run_full_pipeline(
        file_path: Path,
        target_column: Optional[str] = None,
        date_column: Optional[str] = None,
        analysis_id: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the deterministic 9-stage analytical decision pipeline:
        DATA -> QUALITY -> HEALTH -> DIAGNOSIS -> ROOT CAUSE -> RISKS/OPP -> EVIDENCE -> RECS -> DECISIONS
        """
        t0 = time.time()

        # Step 1: Load dataset immutably
        df = IngestionService.load_dataframe(file_path)

        # Infer target and date columns if not specified
        meta = IngestionService.extract_schema_metadata(df)
        if not target_column:
            target_column = meta.get("suggested_target")
        if not date_column:
            date_column = meta.get("suggested_date")

        # Step 2: Data Quality Profiling
        quality_report = QualityProfiler.audit_dataset(df)

        # Step 3: Business Health ("What is happening?")
        health_overview = BusinessHealthEngine.assess_health(
            df, target_col=target_column, date_col=date_column
        )

        # Step 4: Diagnostics ("Why is it happening?")
        diagnostic_report = DiagnosticEngine.diagnose_variance(
            df, target_col=target_column, date_col=date_column,
            dimensions=meta.get("categorical_candidates")
        )

        # Step 5: Root Cause Analysis (Statistical attribution & Pareto)
        root_cause_report = RootCauseEngine.analyze_root_cause(
            df, target_col=target_column, dimensions=meta.get("categorical_candidates")
        )

        # Step 6: Risks & Opportunities ("What requires attention?")
        risks_opp_report = RiskOpportunityEngine.identify_risks_and_opportunities(
            df, target_col=target_column, diagnostic=diagnostic_report, root_cause=root_cause_report
        )

        # Step 7: Traceable Evidence Chains (Extended to 7 stages)
        evidence_chains = EvidenceBuilder.construct_evidence_chains(
            target_col=target_column,
            diagnostic=diagnostic_report,
            root_cause=root_cause_report,
            risk_opp=risks_opp_report,
            source_filename=file_path.name,
            source_type=file_path.suffix.lstrip(".").lower(),
            source_location=f"Sheet 'Main', Column '{target_column}'"
        )

        # Step 8: Prioritized Recommendations ("What action to consider?")
        recommendations = RecommendationEngine.generate_prioritized_recommendations(
            target_col=target_column,
            diagnostic=diagnostic_report,
            root_cause=root_cause_report,
            risk_opp=risks_opp_report
        )

        execution_ms = round((time.time() - t0) * 1000, 2)

        return {
            "target_column": target_column,
            "date_column": date_column,
            "execution_time_ms": execution_ms,
            "data_quality": quality_report.model_dump(),
            "business_health": health_overview.model_dump(),
            "diagnostics": diagnostic_report.model_dump(),
            "root_cause": root_cause_report.model_dump(),
            "risks_opportunities": risks_opp_report.model_dump(),
            "evidence_chains": [chain.model_dump() for chain in evidence_chains],
            "recommendations": [rec.model_dump() for rec in recommendations]
        }
