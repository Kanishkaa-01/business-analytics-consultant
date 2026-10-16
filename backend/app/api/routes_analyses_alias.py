from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import (
    StoredAnalysisSummary,
    PaginatedStoredAnalysesResponse,
    AnalysisRenameRequest,
    AnalysisRunResponse,
    DrillDownRequest,
    DrillDownResponse,
    ForecastRequest,
    ForecastCompareResponse,
    DecisionImpactMatrixResponse,
    WhyThisResultResponse,
    AskDataRequest,
    AskDataResponse,
    KpiGoalCreate,
    KpiGoalUpdate,
    KpiGoalResponse,
)
from app.api.routes_analysis import (
    list_stored_analyses,
    get_analysis_run,
    rename_stored_analysis,
    delete_stored_analysis,
    execute_drill_down_analysis,
    compare_forecast_vs_actual_endpoint,
    get_decision_impact_matrix,
    get_why_this_result_explanation,
    ask_question_on_analysis,
    list_goals_for_analysis,
    create_goal_for_analysis,
    update_goal_for_analysis,
    delete_goal,
)

router = APIRouter(prefix="/analyses", tags=["Analyses History & Workflows"])


@router.get("", response_model=Union[PaginatedStoredAnalysesResponse, List[StoredAnalysisSummary]])
@router.get("/", response_model=Union[PaginatedStoredAnalysesResponse, List[StoredAnalysisSummary]])
def get_all_analyses(
    search: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    sort_by: Optional[str] = Query("newest"),
    db: Session = Depends(get_db)
):
    return list_stored_analyses(search=search, page=page, page_size=page_size, sort_by=sort_by, db=db)


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
def get_single_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return get_analysis_run(analysis_id=analysis_id, db=db)


@router.patch("/{analysis_id}", response_model=StoredAnalysisSummary)
@router.patch("/{analysis_id}/rename", response_model=StoredAnalysisSummary)
def patch_analysis_name(analysis_id: str, payload: AnalysisRenameRequest, db: Session = Depends(get_db)):
    return rename_stored_analysis(analysis_id=analysis_id, payload=payload, db=db)


@router.delete("/{analysis_id}")
def remove_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return delete_stored_analysis(analysis_id=analysis_id, db=db)


@router.post("/{analysis_id}/drill-down", response_model=DrillDownResponse)
def drill_down_alias(analysis_id: str, payload: DrillDownRequest, db: Session = Depends(get_db)):
    return execute_drill_down_analysis(analysis_id=analysis_id, payload=payload, db=db)


@router.post("/{analysis_id}/forecast-vs-actual", response_model=ForecastCompareResponse)
@router.get("/{analysis_id}/forecast-vs-actual", response_model=ForecastCompareResponse)
def forecast_vs_actual_alias(analysis_id: str, payload: Optional[ForecastRequest] = None, db: Session = Depends(get_db)):
    return compare_forecast_vs_actual_endpoint(analysis_id=analysis_id, payload=payload, db=db)


@router.get("/{analysis_id}/decision-impact", response_model=DecisionImpactMatrixResponse)
def decision_impact_alias(analysis_id: str, db: Session = Depends(get_db)):
    return get_decision_impact_matrix(analysis_id=analysis_id, db=db)


@router.get("/{analysis_id}/explanations/{result_type}/{result_id}", response_model=WhyThisResultResponse)
def why_result_alias(analysis_id: str, result_type: str, result_id: str, db: Session = Depends(get_db)):
    return get_why_this_result_explanation(analysis_id=analysis_id, result_type=result_type, result_id=result_id, db=db)


@router.post("/{analysis_id}/ask", response_model=AskDataResponse)
def ask_alias(analysis_id: str, req: AskDataRequest, db: Session = Depends(get_db)):
    return ask_question_on_analysis(analysis_id=analysis_id, req=req, db=db)


@router.get("/{analysis_id}/goals", response_model=List[KpiGoalResponse])
def goals_list_alias(analysis_id: str, db: Session = Depends(get_db)):
    return list_goals_for_analysis(analysis_id=analysis_id, db=db)


@router.post("/{analysis_id}/goals", response_model=KpiGoalResponse)
def goals_create_alias(analysis_id: str, req: KpiGoalCreate, db: Session = Depends(get_db)):
    return create_goal_for_analysis(analysis_id=analysis_id, req=req, db=db)


@router.put("/{analysis_id}/goals/{goal_id}", response_model=KpiGoalResponse)
def goals_update_alias(analysis_id: str, goal_id: str, req: KpiGoalUpdate, db: Session = Depends(get_db)):
    return update_goal_for_analysis(analysis_id=analysis_id, goal_id=goal_id, req=req, db=db)


@router.delete("/{analysis_id}/goals/{goal_id}")
def goals_delete_alias(analysis_id: str, goal_id: str, db: Session = Depends(get_db)):
    return delete_goal(analysis_id=analysis_id, goal_id=goal_id, db=db)
