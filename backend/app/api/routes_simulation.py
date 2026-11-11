from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import AnalysisRun, Dataset, SimulationScenario
from app.models.schemas import (
    SimulationRequest,
    SimulationOutcome,
    ScenarioComparisonReport,
    ScenarioUpdateRequest,
)
from app.engines.simulation import SimulationEngine
from app.services.data_ingestion import IngestionService

router = APIRouter(prefix="/simulation", tags=["Simulation & What-If"])


class SaveScenarioRequest(BaseModel):
    analysis_id: str
    name: str
    parameters: Dict[str, Any]
    projected_outcomes: Optional[Dict[str, Any]] = None


@router.post("/simulate", response_model=SimulationOutcome)
def simulate_scenario(
    req: SimulationRequest,
    db: Session = Depends(get_db)
):
    """
    Simulates business outcomes under managerial lever adjustments.
    Applies deterministic price elasticity, discount profit recovery, and retention math.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == req.analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Associated dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    target_col = run.target_column or df.select_dtypes(include=["number"]).columns[0]

    try:
        outcome = SimulationEngine.run_simulation(df, target_col, req)
        return outcome
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(exc)}")


@router.post("/save-scenario")
def save_scenario(
    req: SaveScenarioRequest,
    db: Session = Depends(get_db)
):
    """Saves a simulation scenario into the database for comparative review."""
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Scenario name cannot be empty.")

    run = db.query(AnalysisRun).filter(AnalysisRun.id == req.analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Associated dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    target_col = run.target_column or df.select_dtypes(include=["number"]).columns[0]

    params = dict(req.parameters or {})
    # Centralized validation & parameter normalization
    if params.get("intervention_type"):
        change_val = params.get("change_percentage", params.get("change_pct", 0.0))
        param_type = params.get("parameter_type", "percentage")
        try:
            norm_params = SimulationEngine.validate_scenario_input(
                df=df,
                target_col=target_col,
                intervention_type=str(params["intervention_type"]),
                change_value=float(change_val),
                parameter_type=str(param_type)
            )
            params.update(norm_params)
            params["change_percentage"] = float(change_val)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        try:
            p_pct = float(params.get("price_change_pct", 0.0))
            v_pct = float(params.get("volume_change_pct", 0.0))
            ops_pct = float(params.get("operational_efficiency_pct", 0.0))
            disc_pct = float(params.get("discount_adjustment_pct", 0.0))
            if p_pct < -100.0:
                raise ValueError("Price change percentage cannot be less than -100%.")
            if v_pct < -100.0:
                raise ValueError("Sales volume change percentage cannot be less than -100%.")
            if ops_pct < 0.0 or ops_pct > 100.0:
                raise ValueError("Operating cost reduction percentage must be between 0% and 100%.")
            if disc_pct < -100.0 or disc_pct > 100.0:
                raise ValueError("Discount change percentage must be between -100% and 100%.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # Recalculate outcomes deterministically using baseline & documented simulation formulas
    sim_req = SimulationRequest(
        analysis_id=req.analysis_id,
        price_change_pct=float(params.get("price_change_pct", 0.0)),
        volume_change_pct=float(params.get("volume_change_pct", 0.0)),
        discount_adjustment_pct=float(params.get("discount_adjustment_pct", 0.0)),
        churn_mitigation_pct=float(params.get("churn_mitigation_pct", 0.0)),
        operational_efficiency_pct=float(params.get("operational_efficiency_pct", 0.0)),
        parameter_type=params.get("parameter_type", "percentage")
    )
    recalculated = SimulationEngine.run_simulation(df, target_col, sim_req)
    projected_outcomes = recalculated.model_dump()

    scenario = SimulationScenario(
        analysis_id=req.analysis_id,
        name=req.name.strip(),
        parameters=params,
        projected_outcomes=projected_outcomes
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "status": "success",
        "scenario_id": scenario.id,
        "name": scenario.name,
        "parameters": scenario.parameters,
        "projected_outcomes": scenario.projected_outcomes
    }


@router.get("/{analysis_id}/scenarios")
def list_saved_scenarios(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve all saved simulation scenarios for an analysis run."""
    scenarios = db.query(SimulationScenario).filter(
        SimulationScenario.analysis_id == analysis_id
    ).order_by(SimulationScenario.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "parameters": s.parameters,
            "projected_outcomes": s.projected_outcomes,
            "created_at": s.created_at
        }
        for s in scenarios
    ]


@router.put("/scenario/{scenario_id}")
def update_scenario(
    scenario_id: str,
    payload: ScenarioUpdateRequest,
    db: Session = Depends(get_db)
):
    """Updates a saved scenario's name, parameters, or outcomes."""
    scenario = db.query(SimulationScenario).filter(SimulationScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    run = db.query(AnalysisRun).filter(AnalysisRun.id == scenario.analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Associated dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    target_col = run.target_column or df.select_dtypes(include=["number"]).columns[0]

    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status_code=400, detail="Scenario name cannot be empty.")
        scenario.name = payload.name.strip()

    if payload.parameters is not None:
        params = dict(payload.parameters)
        if params.get("intervention_type"):
            change_val = params.get("change_percentage", params.get("change_pct", 0.0))
            param_type = params.get("parameter_type", "percentage")
            try:
                norm_params = SimulationEngine.validate_scenario_input(
                    df=df,
                    target_col=target_col,
                    intervention_type=str(params["intervention_type"]),
                    change_value=float(change_val),
                    parameter_type=str(param_type)
                )
                params.update(norm_params)
                params["change_percentage"] = float(change_val)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        else:
            try:
                p_pct = float(params.get("price_change_pct", 0.0))
                v_pct = float(params.get("volume_change_pct", 0.0))
                ops_pct = float(params.get("operational_efficiency_pct", 0.0))
                disc_pct = float(params.get("discount_adjustment_pct", 0.0))
                if p_pct < -100.0:
                    raise ValueError("Price change percentage cannot be less than -100%.")
                if v_pct < -100.0:
                    raise ValueError("Sales volume change percentage cannot be less than -100%.")
                if ops_pct < 0.0 or ops_pct > 100.0:
                    raise ValueError("Operating cost reduction percentage must be between 0% and 100%.")
                if disc_pct < -100.0 or disc_pct > 100.0:
                    raise ValueError("Discount change percentage must be between -100% and 100%.")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        scenario.parameters = params

        # Recalculate outcomes
        sim_req = SimulationRequest(
            analysis_id=scenario.analysis_id,
            price_change_pct=float(params.get("price_change_pct", 0.0)),
            volume_change_pct=float(params.get("volume_change_pct", 0.0)),
            discount_adjustment_pct=float(params.get("discount_adjustment_pct", 0.0)),
            churn_mitigation_pct=float(params.get("churn_mitigation_pct", 0.0)),
            operational_efficiency_pct=float(params.get("operational_efficiency_pct", 0.0)),
            parameter_type=params.get("parameter_type", "percentage")
        )
        recalculated = SimulationEngine.run_simulation(df, target_col, sim_req)
        scenario.projected_outcomes = recalculated.model_dump()
    elif payload.projected_outcomes is not None:
        scenario.projected_outcomes = payload.projected_outcomes

    db.commit()
    db.refresh(scenario)
    return {
        "status": "success",
        "id": scenario.id,
        "name": scenario.name,
        "parameters": scenario.parameters,
        "projected_outcomes": scenario.projected_outcomes
    }


@router.delete("/scenario/{scenario_id}")
def delete_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """Deletes a saved scenario from the database."""
    scenario = db.query(SimulationScenario).filter(SimulationScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    db.delete(scenario)
    db.commit()
    return {"status": "success", "deleted_id": scenario_id}


@router.get("/{analysis_id}/compare", response_model=ScenarioComparisonReport)
def compare_scenarios_for_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """
    Deterministically compares all saved scenarios against the baseline
    for a given analysis run, recalculating outcomes from persisted parameters.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Associated dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df = IngestionService.load_dataframe(file_path)
    target_col = run.target_column or df.select_dtypes(include=["number"]).columns[0]

    # Baseline simulation (0% on all levers)
    baseline_req = SimulationRequest(
        analysis_id=analysis_id,
        price_change_pct=0.0,
        volume_change_pct=0.0,
        discount_adjustment_pct=0.0,
        churn_mitigation_pct=0.0,
        operational_efficiency_pct=0.0
    )
    baseline_outcome = SimulationEngine.run_simulation(df, target_col, baseline_req)

    # Fetch saved scenarios
    scenarios = db.query(SimulationScenario).filter(
        SimulationScenario.analysis_id == analysis_id
    ).order_by(SimulationScenario.created_at.asc()).all()

    scenario_dicts = []
    for s in scenarios:
        params = s.parameters or {}
        p_pct = float(params.get("price_change_pct", 0.0))
        v_pct = float(params.get("volume_change_pct", 0.0))
        ops_pct = float(params.get("operational_efficiency_pct", 0.0))
        disc_pct = float(params.get("discount_adjustment_pct", 0.0))
        churn_pct = float(params.get("churn_mitigation_pct", 0.0))
        param_type = params.get("parameter_type", "percentage")

        sim_req = SimulationRequest(
            analysis_id=analysis_id,
            price_change_pct=p_pct,
            volume_change_pct=v_pct,
            discount_adjustment_pct=disc_pct,
            churn_mitigation_pct=churn_pct,
            operational_efficiency_pct=ops_pct,
            parameter_type=param_type
        )
        # Recalculate scenario output using existing baseline and documented simulation formulas
        recalculated_outcome = SimulationEngine.run_simulation(df, target_col, sim_req)
        scenario_dicts.append({
            "id": s.id,
            "name": s.name,
            "parameters": params,
            "projected_outcomes": recalculated_outcome.model_dump(),
            "notes": params.get("notes") or (s.projected_outcomes or {}).get("notes")
        })

    report = SimulationEngine.compare_scenarios(baseline_outcome, scenario_dicts)
    return report

