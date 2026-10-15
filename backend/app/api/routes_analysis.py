from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Dataset, AnalysisRun, DecisionRecord, KpiGoal
from app.models.schemas import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    DecisionRecordSchema,
    ChartSpecification,
    AdvancedFindingsReport,
    ForecastReport,
    ForecastRequest,
    StoredAnalysisSummary,
    AnalysisRenameRequest,
    DrillDownRequest,
    DrillDownResponse,
    ForecastCompareResponse,
    DecisionImpactMatrixResponse,
    WhyThisResultResponse,
    AskDataRequest,
    AskDataResponse,
    KpiGoalCreate,
    KpiGoalUpdate,
    KpiGoalResponse,
)
from app.engines.pipeline import DecisionPipeline
from app.engines.visualization_engine import VisualizationEngine
from app.engines.advanced_findings import AdvancedFindingsEngine
from app.engines.forecasting_engine import ForecastingEngine
from app.engines.drill_down import DrillDownEngine
from app.engines.decision_impact import DecisionImpactEngine
from app.engines.explanation_engine import ExplanationEngine
from app.engines.ask_data_engine import AskDataEngine
from app.engines.goal_tracking import GoalTrackingEngine
from app.services.data_ingestion import IngestionService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=AnalysisRunResponse)
def execute_analysis(
    req: AnalysisRunRequest,
    db: Session = Depends(get_db)
):
    """
    Executes the deterministic 9-stage analytical decision pipeline on a dataset.
    Preserves original uploaded files without modification.
    """
    dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Source data file '{dataset.filename}' is missing on disk.")

    ext = file_path.suffix.lower()
    if ext in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="The 9-stage quantitative variance pipeline requires a structured tabular dataset (CSV or XLSX). Upload a CSV or Excel dataset to run variance analysis."
        )

    try:
        pipeline_output = DecisionPipeline.run_full_pipeline(
            file_path=file_path,
            target_column=req.target_column,
            date_column=req.date_column,
            dataset_id=dataset.id
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analytical pipeline execution error: {str(exc)}")

    now_utc = datetime.now(timezone.utc)
    display_name = req.analysis_name if (req.analysis_name and req.analysis_name.strip()) else f"{dataset.name} Analysis - {now_utc.strftime('%b %d, %Y %H:%M')}"
    dataset_ver = dataset.file_hash[:8] if dataset.file_hash else "v1.0"

    # Persist the deterministic analytical run
    analysis_run = AnalysisRun(
        dataset_id=dataset.id,
        target_column=pipeline_output["target_column"],
        date_column=pipeline_output["date_column"],
        status="completed",
        analysis_name=display_name,
        dataset_version=dataset_ver,
        completed_at=now_utc,
        execution_time_ms=pipeline_output["execution_time_ms"],
        data_quality=pipeline_output["data_quality"],
        business_health=pipeline_output["business_health"],
        diagnostics=pipeline_output["diagnostics"],
        root_cause=pipeline_output["root_cause"],
        risks_opportunities=pipeline_output["risks_opportunities"],
        evidence_chains=pipeline_output["evidence_chains"],
        recommendations=pipeline_output["recommendations"]
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)

    return AnalysisRunResponse(
        id=analysis_run.id,
        dataset_id=analysis_run.dataset_id,
        target_column=analysis_run.target_column,
        date_column=analysis_run.date_column,
        status=analysis_run.status,
        execution_time_ms=analysis_run.execution_time_ms,
        created_at=analysis_run.created_at,
        analysis_name=analysis_run.analysis_name,
        dataset_version=analysis_run.dataset_version,
        completed_at=analysis_run.completed_at,
        data_quality=analysis_run.data_quality,
        business_health=analysis_run.business_health,
        diagnostics=analysis_run.diagnostics,
        root_cause=analysis_run.root_cause,
        risks_opportunities=analysis_run.risks_opportunities,
        evidence_chains=analysis_run.evidence_chains,
        recommendations=analysis_run.recommendations,
        decisions=[]
    )


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
def get_analysis_run(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve full analytical findings and captured decisions for an analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    decisions = db.query(DecisionRecord).filter(DecisionRecord.analysis_id == analysis_id).all()
    dec_schemas = [DecisionRecordSchema.model_validate(d) for d in decisions]

    return AnalysisRunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        target_column=run.target_column,
        date_column=run.date_column,
        status=run.status,
        execution_time_ms=run.execution_time_ms,
        created_at=run.created_at,
        analysis_name=run.analysis_name or f"Analysis {run.id[:8]}",
        dataset_version=run.dataset_version,
        completed_at=run.completed_at or run.created_at,
        data_quality=run.data_quality,
        business_health=run.business_health,
        diagnostics=run.diagnostics,
        root_cause=run.root_cause,
        risks_opportunities=run.risks_opportunities,
        evidence_chains=run.evidence_chains,
        recommendations=run.recommendations,
        decisions=dec_schemas
    )


@router.get("/dataset/{dataset_id}")
def list_analyses_for_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """List historical analytical runs performed on a given dataset."""
    runs = db.query(AnalysisRun).filter(AnalysisRun.dataset_id == dataset_id).order_by(AnalysisRun.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "dataset_id": r.dataset_id,
            "target_column": r.target_column,
            "status": r.status,
            "execution_time_ms": r.execution_time_ms,
            "created_at": r.created_at,
            "health_score": r.business_health.get("overall_health_score"),
            "quality_score": r.data_quality.get("overall_quality_score")
        }
        for r in runs
    ]


@router.get("/{analysis_id}/visualization", response_model=ChartSpecification)
def get_analysis_visualization(
    analysis_id: str,
    dimension_col: str = None,
    second_numeric_col: str = None,
    is_part_to_whole: bool = False,
    is_single_kpi: bool = False,
    db: Session = Depends(get_db)
):
    """
    Phase 11: Returns an automatically selected Apache ECharts specification
    based on the analysis run dataset structure and selected dimensions.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    spec = VisualizationEngine.select_and_generate_chart(
        df=df,
        target_col=run.target_column,
        date_col=run.date_column,
        dimension_col=dimension_col,
        second_numeric_col=second_numeric_col,
        is_part_to_whole=is_part_to_whole,
        is_single_kpi=is_single_kpi
    )
    return spec


@router.get("/{analysis_id}/advanced-findings", response_model=AdvancedFindingsReport)
def get_advanced_findings(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    Phase 12: Returns deterministic Trend Analysis, Anomaly Detection,
    and Segment Comparisons for the analysis run.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    report = AdvancedFindingsEngine.analyze(
        df=df,
        target_col=run.target_column,
        date_col=run.date_column
    )
    return report


@router.post("/{analysis_id}/forecast", response_model=ForecastReport)
def generate_forecast_for_analysis(
    analysis_id: str,
    payload: ForecastRequest = None,
    db: Session = Depends(get_db)
):
    """
    Phase 16: Deterministically generates a multi-model forecast with holdout validation.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    req = payload or ForecastRequest()
    target_col = req.metric_col or run.target_column
    date_col = req.date_col or run.date_column
    horizon = req.horizon or 3

    report = ForecastingEngine.generate_forecast(
        df=df,
        target_col=target_col,
        date_col=date_col,
        horizon=horizon,
        selected_model_type=req.model_type
    )
    return report


# -------------------------------------------------------------
# Stored Analyses History & Management
# -------------------------------------------------------------
@router.get("/stored", response_model=List[StoredAnalysisSummary])
def list_stored_analyses(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieves all past analytical runs with search and metadata summaries."""
    query = (
        db.query(AnalysisRun, Dataset.name.label("dataset_name"))
        .join(Dataset, AnalysisRun.dataset_id == Dataset.id)
        .order_by(AnalysisRun.created_at.desc())
    )
    results = query.all()
    summaries = []
    for run, ds_name in results:
        display_name = run.analysis_name or f"{ds_name} Analysis"
        if search:
            s_low = search.lower()
            if s_low not in display_name.lower() and s_low not in ds_name.lower():
                continue

        health_score = None
        if run.business_health and isinstance(run.business_health, dict):
            health_score = run.business_health.get("overall_health_score")

        summaries.append(StoredAnalysisSummary(
            id=run.id,
            analysis_name=display_name,
            dataset_id=run.dataset_id,
            dataset_name=ds_name,
            dataset_version=run.dataset_version,
            target_column=run.target_column,
            date_column=run.date_column,
            status=run.status,
            execution_time_ms=int(run.execution_time_ms or 0),
            health_score=health_score,
            created_at=run.created_at,
            completed_at=run.completed_at
        ))
    return summaries


@router.patch("/{analysis_id}/rename", response_model=StoredAnalysisSummary)
def rename_stored_analysis(
    analysis_id: str,
    payload: AnalysisRenameRequest,
    db: Session = Depends(get_db)
):
    """Renames a stored analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    run.analysis_name = payload.analysis_name.strip()
    db.commit()
    db.refresh(run)

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    ds_name = dataset.name if dataset else "Unknown"
    health_score = run.business_health.get("overall_health_score") if run.business_health else None

    return StoredAnalysisSummary(
        id=run.id,
        analysis_name=run.analysis_name,
        dataset_id=run.dataset_id,
        dataset_name=ds_name,
        dataset_version=run.dataset_version,
        target_column=run.target_column,
        date_column=run.date_column,
        status=run.status,
        execution_time_ms=int(run.execution_time_ms or 0),
        health_score=health_score,
        created_at=run.created_at,
        completed_at=run.completed_at
    )


@router.delete("/{analysis_id}")
def delete_stored_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Deletes a stored analysis run and cascades child scenarios and records."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    db.delete(run)
    db.commit()
    return {"status": "success", "message": f"Analysis {analysis_id} deleted."}


# -------------------------------------------------------------
# Drill-Down Analysis
# -------------------------------------------------------------
@router.post("/{analysis_id}/drill-down", response_model=DrillDownResponse)
def execute_drill_down_analysis(
    analysis_id: str,
    payload: DrillDownRequest,
    db: Session = Depends(get_db)
):
    """Executes deterministic hierarchical multi-level drill down with parent filtering."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset or not dataset.file_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    try:
        res = DrillDownEngine.execute_drill_down(
            df=df,
            dimension=payload.dimension,
            metric=payload.metric or run.target_column,
            aggregation=payload.aggregation or "sum",
            parent_filters=payload.parent_filters,
            limit=payload.limit or 10
        )
        return DrillDownResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------
# Forecast vs Actual
# -------------------------------------------------------------
@router.post("/{analysis_id}/forecast-vs-actual", response_model=ForecastCompareResponse)
@router.get("/{analysis_id}/forecast-vs-actual", response_model=ForecastCompareResponse)
def compare_forecast_vs_actual_endpoint(
    analysis_id: str,
    payload: Optional[ForecastRequest] = None,
    db: Session = Depends(get_db)
):
    """Compares holdout statistical forecasts against empirical actuals."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset or not dataset.file_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    req = payload or ForecastRequest()
    target_col = req.metric_col or run.target_column
    date_col = req.date_col or run.date_column
    horizon = req.horizon or 3

    return ForecastingEngine.compare_forecast_vs_actual(
        df=df,
        target_col=target_col,
        date_col=date_col,
        horizon=horizon,
        model_type=req.model_type
    )


# -------------------------------------------------------------
# Decision Impact Matrix
# -------------------------------------------------------------
@router.get("/{analysis_id}/decision-impact", response_model=DecisionImpactMatrixResponse)
def get_decision_impact_matrix(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """Maps recommendations to Effort vs. Impact quadrants with Apache ECharts spec."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    return DecisionImpactEngine.generate_impact_matrix(run.recommendations or [])


# -------------------------------------------------------------
# Why This Result? Explanations
# -------------------------------------------------------------
@router.get("/{analysis_id}/explanations/{result_type}/{result_id}", response_model=WhyThisResultResponse)
def get_why_this_result_explanation(
    analysis_id: str,
    result_type: str,
    result_id: str,
    db: Session = Depends(get_db)
):
    """Provides plain-English rationale, mathematical formulas, inputs, and assumptions."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    return ExplanationEngine.explain_result(run, result_type, result_id)


# -------------------------------------------------------------
# Ask Data Convenience Endpoint on Analysis
# -------------------------------------------------------------
@router.post("/{analysis_id}/ask", response_model=AskDataResponse)
def ask_question_on_analysis(
    analysis_id: str,
    req: AskDataRequest,
    db: Session = Depends(get_db)
):
    """Answers natural language questions about the dataset tied to this analysis."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset or not dataset.file_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    res = AskDataEngine.answer_question(df, req.query, dataset.schema_metadata)
    return AskDataResponse(**res)


# -------------------------------------------------------------
# KPI Goal Tracking
# -------------------------------------------------------------
@router.get("/{analysis_id}/goals", response_model=List[KpiGoalResponse])
def list_goals_for_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Lists all KPI goals defined for this analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    goals = db.query(KpiGoal).filter(
        (KpiGoal.analysis_id == analysis_id) | (KpiGoal.dataset_id == run.dataset_id)
    ).all()
    return goals


@router.post("/{analysis_id}/goals", response_model=KpiGoalResponse)
def create_goal_for_analysis(
    analysis_id: str,
    req: KpiGoalCreate,
    db: Session = Depends(get_db)
):
    """Creates a new KPI goal, evaluates baseline and current progress deterministically."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    df = None
    if dataset and dataset.file_path and Path(dataset.file_path).exists():
        df = IngestionService.load_dataframe(Path(dataset.file_path))

    curr_val = GoalTrackingEngine.extract_metric_current_value(df, req.metric)
    eval_res = GoalTrackingEngine.evaluate_goal(
        metric=req.metric,
        target_value=req.target_value,
        target_type=req.target_type,
        current_val=curr_val
    )

    goal = KpiGoal(
        analysis_id=analysis_id,
        dataset_id=run.dataset_id,
        metric=req.metric,
        target_type=req.target_type,
        target_value=eval_res["target_value"],
        baseline_value=eval_res["baseline_value"],
        current_value=eval_res["current_value"],
        progress_pct=eval_res["progress_pct"],
        status=eval_res["status"],
        notes=req.notes
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.put("/{analysis_id}/goals/{goal_id}", response_model=KpiGoalResponse)
def update_goal_for_analysis(
    analysis_id: str,
    goal_id: str,
    req: KpiGoalUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing KPI target or note."""
    goal = db.query(KpiGoal).filter(KpiGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    if req.target_value is not None:
        goal.target_value = req.target_value
    if req.notes is not None:
        goal.notes = req.notes
    if req.target_type is not None:
        goal.target_type = req.target_type

    eval_res = GoalTrackingEngine.evaluate_goal(
        metric=goal.metric,
        target_value=goal.target_value,
        target_type=goal.target_type,
        current_val=goal.current_value or goal.baseline_value or 0.0,
        baseline_val=goal.baseline_value
    )
    goal.progress_pct = eval_res["progress_pct"]
    goal.status = eval_res["status"]

    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{analysis_id}/goals/{goal_id}")
def delete_goal(analysis_id: str, goal_id: str, db: Session = Depends(get_db)):
    """Deletes a KPI goal."""
    goal = db.query(KpiGoal).filter(KpiGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    db.delete(goal)
    db.commit()
    return {"status": "success", "message": f"Goal {goal_id} deleted."}

