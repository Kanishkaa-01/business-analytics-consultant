from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import DecisionRecord, AnalysisRun
from app.models.schemas import DecisionRecordSchema, DecisionCreate

router = APIRouter(prefix="/decisions", tags=["Decision Support"])


class DecisionStatusUpdate(BaseModel):
    decision_status: str  # Accepted, Rejected, Deferred, Under Review
    stakeholder: Optional[str] = None
    notes_rationale: Optional[str] = None
    target_date: Optional[str] = None
    expected_impact_dollars: Optional[float] = None


@router.post("/{analysis_id}", response_model=DecisionRecordSchema)
def record_decision(
    analysis_id: str,
    payload: DecisionCreate,
    db: Session = Depends(get_db)
):
    """
    Human-in-the-loop: Records executive decision against an analytical recommendation.
    Logs stakeholder, decision status, target date, and justification rationale.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    # Check if a decision already exists for this recommendation in this run
    existing = db.query(DecisionRecord).filter(
        DecisionRecord.analysis_id == analysis_id,
        DecisionRecord.recommendation_id == payload.recommendation_id
    ).first()

    if existing:
        existing.decision_status = payload.decision_status
        existing.stakeholder = payload.stakeholder or existing.stakeholder
        existing.notes_rationale = payload.notes_rationale or existing.notes_rationale
        existing.target_date = payload.target_date or existing.target_date
        if payload.expected_impact_dollars is not None:
            existing.expected_impact_dollars = payload.expected_impact_dollars
        db.commit()
        db.refresh(existing)
        return DecisionRecordSchema.model_validate(existing)

    decision = DecisionRecord(
        analysis_id=analysis_id,
        recommendation_id=payload.recommendation_id,
        action_title=payload.action_title,
        decision_status=payload.decision_status,
        stakeholder=payload.stakeholder or "Decision Maker",
        notes_rationale=payload.notes_rationale or "",
        target_date=payload.target_date or "",
        expected_impact_dollars=payload.expected_impact_dollars or 0.0
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    return DecisionRecordSchema.model_validate(decision)


@router.get("/analysis/{analysis_id}", response_model=List[DecisionRecordSchema])
def list_decisions_for_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve all human decisions logged for a specific analysis run."""
    decisions = db.query(DecisionRecord).filter(
        DecisionRecord.analysis_id == analysis_id
    ).order_by(DecisionRecord.created_at.desc()).all()
    return [DecisionRecordSchema.model_validate(d) for d in decisions]


@router.patch("/{decision_id}", response_model=DecisionRecordSchema)
def update_decision(
    decision_id: str,
    payload: DecisionStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update decision state, stakeholder sign-off or target milestone."""
    decision = db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision record not found.")

    decision.decision_status = payload.decision_status
    if payload.stakeholder is not None:
        decision.stakeholder = payload.stakeholder
    if payload.notes_rationale is not None:
        decision.notes_rationale = payload.notes_rationale
    if payload.target_date is not None:
        decision.target_date = payload.target_date
    if payload.expected_impact_dollars is not None:
        decision.expected_impact_dollars = payload.expected_impact_dollars

    db.commit()
    db.refresh(decision)
    return DecisionRecordSchema.model_validate(decision)
