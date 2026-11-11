import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 for data immutability verification
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    schema_metadata = Column(JSON, default=dict)
    is_sample = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    analyses = relationship("AnalysisRun", back_populates="dataset", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    target_column = Column(String(255), nullable=True)
    date_column = Column(String(255), nullable=True)
    status = Column(String(50), default="completed")
    execution_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Analytical results stored deterministically
    data_quality = Column(JSON, default=dict)
    business_health = Column(JSON, default=dict)
    diagnostics = Column(JSON, default=dict)
    root_cause = Column(JSON, default=dict)
    risks_opportunities = Column(JSON, default=dict)
    evidence_chains = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    analysis_name = Column(String(255), nullable=True)
    dataset_version = Column(String(64), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    forecast_data = Column(JSON, default=dict)

    # Relationships
    dataset = relationship("Dataset", back_populates="analyses")
    decisions = relationship("DecisionRecord", back_populates="analysis", cascade="all, delete-orphan")
    simulations = relationship("SimulationScenario", back_populates="analysis", cascade="all, delete-orphan")
    goals = relationship("KpiGoal", back_populates="analysis", cascade="all, delete-orphan")
    forecasts = relationship("ForecastRecord", back_populates="analysis", cascade="all, delete-orphan")


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False)
    recommendation_id = Column(String(100), nullable=False)
    action_title = Column(String(255), nullable=False)
    decision_status = Column(String(50), default="Under Review")  # Accepted, Rejected, Deferred, Under Review
    stakeholder = Column(String(100), nullable=True)
    notes_rationale = Column(Text, nullable=True)
    target_date = Column(String(50), nullable=True)
    expected_impact_dollars = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRun", back_populates="decisions")


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    parameters = Column(JSON, default=dict)
    projected_outcomes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRun", back_populates="simulations")


class KpiGoal(Base):
    __tablename__ = "kpi_goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    metric = Column(String(100), nullable=False)
    target_type = Column(String(50), default="absolute")  # absolute, percentage_growth
    target_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    progress_pct = Column(Float, default=0.0)
    status = Column(String(50), default="Below Target")  # On Track, Near Target, Below Target, Target Achieved
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRun", back_populates="goals")
    dataset = relationship("Dataset")


class ForecastRecord(Base):
    __tablename__ = "forecast_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    metric = Column(String(100), nullable=False)
    date_column = Column(String(100), nullable=True)
    model_name = Column(String(100), nullable=False)
    horizon = Column(Integer, default=3)
    forecast_series = Column(JSON, default=list)
    actual_series = Column(JSON, default=list)
    comparison_summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRun", back_populates="forecasts")
    dataset = relationship("Dataset")
