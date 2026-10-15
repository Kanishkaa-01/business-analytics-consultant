from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# -------------------------------------------------------------
# Dataset Schemas
# -------------------------------------------------------------
class ColumnMetadata(BaseModel):
    name: str
    dtype: str
    inferred_type: str  # numeric, categorical, datetime, text, identifier
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any]
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    mean_val: Optional[float] = None
    median_val: Optional[float] = None
    std_val: Optional[float] = None


class DatasetSummary(BaseModel):
    id: str
    name: str
    filename: str
    row_count: int
    column_count: int
    file_size_bytes: int
    is_sample: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetDetail(DatasetSummary):
    file_hash: str
    schema_metadata: Dict[str, Any]
    preview_rows: List[Dict[str, Any]] = []


# -------------------------------------------------------------
# Data Quality Schemas
# -------------------------------------------------------------
class QualityIssue(BaseModel):
    severity: str  # Critical, Warning, Info
    dimension: str  # Completeness, Validity, Uniqueness, Consistency, Distribution
    column: Optional[str] = None
    description: str
    affected_rows: int
    percentage: float
    recommendation: str


class ColumnQualityMetric(BaseModel):
    column: str
    completeness_score: float
    validity_score: float
    outlier_count: int
    outlier_percentage: float
    skewness: Optional[float] = None


class DataQualityReport(BaseModel):
    overall_quality_score: float  # 0 to 100
    grade: str  # A, B, C, D, F
    total_records: int
    duplicate_rows: int
    completeness_ratio: float
    validity_ratio: float
    consistency_ratio: float
    issues: List[QualityIssue]
    column_metrics: List[ColumnQualityMetric]
    reliability_assessment: str


# -------------------------------------------------------------
# Business Health Schemas ("What is happening?")
# -------------------------------------------------------------
class KpiMetric(BaseModel):
    name: str
    current_value: float
    target_or_baseline: Optional[float] = None
    variance_pct: Optional[float] = None
    unit: str
    trend: str  # "improving", "deteriorating", "stable"
    status: str  # "healthy", "warning", "critical"
    interpretation: str


class BusinessHealthOverview(BaseModel):
    overall_health_score: float  # 0 - 100
    overall_status: str  # Strong, Stable, Vulnerable, Distressed
    executive_summary: str
    kpis: List[KpiMetric]
    vital_signs: Dict[str, Any]
    overview_metrics: Optional[Dict[str, Any]] = None
    timeline_series: Optional[List[Dict[str, Any]]] = None
    health_breakdown: Optional[List[Dict[str, Any]]] = None
    primary_pressure: Optional[Dict[str, Any]] = None
    health_methodology: Optional[str] = None


# -------------------------------------------------------------
# Diagnostics Schemas ("Why is it happening?")
# -------------------------------------------------------------
class VarianceBreakdownItem(BaseModel):
    dimension: str
    segment: str
    baseline_value: float
    actual_value: float
    variance: float
    variance_pct: float
    contribution_share_pct: float
    direction: str  # Drag, Lift


class SegmentDiagnostic(BaseModel):
    dimension: str
    underperforming_segments: List[Dict[str, Any]]
    overperforming_segments: List[Dict[str, Any]]
    dispersion_gini_or_cv: float


class DiagnosticReport(BaseModel):
    focal_metric: str
    total_variance: float
    variance_pct: float
    variance_breakdown: List[VarianceBreakdownItem]
    segment_diagnostics: List[SegmentDiagnostic]
    anomalies_detected: List[Dict[str, Any]]
    diagnostic_narrative: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)


# -------------------------------------------------------------
# Possible Reasons Analysis Schemas (Non-causal factor association)
# -------------------------------------------------------------
class FactorContribution(BaseModel):
    factor_name: str
    factor_type: str  # Operational, Commercial, Customer, Supply
    attribution_percentage: float
    statistical_significance_p_value: float
    correlation_or_coef: float
    direction: str  # "Negative Impact", "Positive Impact"
    evidence_statement: str
    evidence_type: str = "Correlation & Segment Comparison"


class ParetoItem(BaseModel):
    entity: str
    loss_or_impact: float
    cumulative_percentage: float
    is_vital_few: bool
    contribution_percentage: float = 0.0


class RootCauseReport(BaseModel):
    primary_root_cause: str
    secondary_root_causes: List[str]
    factor_contributions: List[FactorContribution]
    pareto_breakdown: List[ParetoItem]
    causal_tree_structure: Dict[str, Any]
    statistical_confidence_level: float
    methodology_notes: str
    possible_reasons_summary: Optional[str] = None
    causation_disclaimer: str = "Note: An observed relationship does not necessarily prove causation."
    evidence_type: str = "Statistical Association & Segment Comparison"


# -------------------------------------------------------------
# Risks & Opportunities Schemas ("What requires attention?")
# -------------------------------------------------------------
class RiskItem(BaseModel):
    id: str
    title: str
    category: str  # Churn, Margin Compression, Concentration, Operational Delay
    severity: str  # High, Medium, Low
    probability_pct: float
    estimated_financial_exposure: float
    root_cause_ref: str
    early_warning_signals: List[str]
    mitigation_window_days: int


class OpportunityItem(BaseModel):
    id: str
    title: str
    category: str  # Revenue Uplift, Cost Reduction, Pricing Optimization, Retention
    potential_value_gain: float
    feasibility: str  # High, Medium, Complex
    confidence_level_pct: float
    target_segment: str
    strategic_rationale: str


class RisksAndOpportunitiesReport(BaseModel):
    total_exposure_at_risk: float
    total_opportunity_upside: float
    risk_profile_rating: str  # Conservative, Moderate, High Risk
    risks: List[RiskItem]
    opportunities: List[OpportunityItem]


# -------------------------------------------------------------
# Traceable Evidence Trails
# -------------------------------------------------------------
class EvidenceNode(BaseModel):
    stage: str  # "Data Source", "Data Extracted", "Observed Pattern", "Data Check", "Possible Reason", "Estimated Impact", "Recommended Action"
    detail: str
    metric_or_statistic: str
    data_support: str


class EvidenceChain(BaseModel):
    id: str
    title: str
    target_metric: str
    observed_phenomenon: str
    diagnostic_pathway: List[str]
    underlying_mechanism: str
    statistical_proof: str
    associated_recommendation_id: str
    nodes: List[EvidenceNode]
    disclaimer: str = "Note: An observed relationship does not necessarily prove causation."


# -------------------------------------------------------------
# Recommended Actions Schemas ("What could we do?")
# -------------------------------------------------------------
class RecommendationItem(BaseModel):
    id: str
    title: str
    urgency: str  # Immediate (0-30 days), Near-term (30-90 days), Strategic (90+ days)
    category: str
    mechanism_of_action: str
    rationale: str
    prerequisites: List[str]
    expected_financial_impact: float
    implementation_effort: str  # Low, Medium, High
    confidence_score_pct: float
    # Priority Scoring
    impact_score: float  # 1-10
    confidence_score: float  # 1-10
    ease_score: float  # 1-10
    priority_score: float  # Priority Score 0-100
    priority_tier: str  # P1 - Critical, P2 - High, P3 - Medium, P4 - Opportunistic
    tradeoffs_and_risks: str
    status: str = "Pending Review"
    # Simple explicit explanation fields
    what_to_do: Optional[str] = None
    why: Optional[str] = None
    evidence: Optional[str] = None
    expected_impact_label: Optional[str] = None
    difficulty: Optional[str] = None
    priority_label: Optional[str] = None
    possible_risk: Optional[str] = None
    # Phase 14 Standardized Fields
    recommendation: Optional[str] = None
    reason: Optional[str] = None
    supporting_finding: Optional[str] = None
    priority_level: Optional[str] = None
    decision_status: Optional[str] = None


class DecisionRecordSchema(BaseModel):
    id: str
    analysis_id: str
    recommendation_id: str
    action_title: str
    decision_status: str
    stakeholder: Optional[str] = None
    notes_rationale: Optional[str] = None
    target_date: Optional[str] = None
    expected_impact_dollars: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionCreate(BaseModel):
    recommendation_id: str
    action_title: str
    decision_status: str  # Accepted, Rejected, Deferred, Under Review
    stakeholder: Optional[str] = "Decision Maker"
    notes_rationale: Optional[str] = ""
    target_date: Optional[str] = None
    expected_impact_dollars: Optional[float] = 0.0


# -------------------------------------------------------------
# Simulation & What-If Engine Schemas
# -------------------------------------------------------------
class SimulationRequest(BaseModel):
    analysis_id: str
    price_change_pct: float = Field(0.0, description="Percentage change in baseline price (-100 to +500%)")
    volume_change_pct: float = Field(0.0, description="Percentage change in sales volume (-100 to +500%)")
    discount_adjustment_pct: float = Field(0.0, description="Discount rate reduction/increase points")
    churn_mitigation_pct: float = Field(0.0, description="Reduction in churn/loss rate percentage")
    operational_efficiency_pct: float = Field(0.0, description="Cost reduction percentage (0 to 100%)")
    intervention_type: Optional[str] = Field(None, description="Selected intervention type label")
    parameter_type: Optional[str] = Field("percentage", description="'percentage' or 'percentage_points'")
    notes: Optional[str] = Field(None, description="Assumptions or rationale notes")


class SimulationOutcome(BaseModel):
    baseline_revenue: float
    simulated_revenue: float
    revenue_delta: float
    revenue_delta_pct: float
    baseline_profit: float
    simulated_profit: float
    profit_delta: float
    profit_delta_pct: float
    baseline_margin_pct: float = 0.0
    simulated_margin_pct: float = 0.0
    margin_delta_pct: float = 0.0
    simulation_insights: List[str] = Field(default_factory=list)
    net_economic_value_added: float
    risk_adjusted_return: float
    sensitivity_breakdown: Dict[str, float]
    recommendation_impact_overlap: List[str]
    sensitivity_table: Optional[List[Dict[str, Any]]] = None
    assumptions_statement: Optional[str] = None
    supported_interventions: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# Full Pipeline Analysis Run Schemas
# -------------------------------------------------------------
class AnalysisRunRequest(BaseModel):
    dataset_id: str
    target_column: Optional[str] = None
    date_column: Optional[str] = None
    analysis_name: Optional[str] = None


class AnalysisRunResponse(BaseModel):
    id: str
    dataset_id: str
    target_column: Optional[str]
    date_column: Optional[str]
    status: str
    execution_time_ms: float
    created_at: datetime
    analysis_name: Optional[str] = None
    dataset_version: Optional[str] = None
    completed_at: Optional[datetime] = None

    data_quality: DataQualityReport
    business_health: BusinessHealthOverview
    diagnostics: DiagnosticReport
    root_cause: RootCauseReport
    risks_opportunities: RisksAndOpportunitiesReport
    evidence_chains: List[EvidenceChain]
    recommendations: List[RecommendationItem]
    decisions: List[DecisionRecordSchema] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Automatic Visualization Schemas (Phase 11)
# -------------------------------------------------------------
class ChartSpecification(BaseModel):
    chart_type: str  # "bar", "line", "pie", "scatter", "kpi", "none"
    title: str
    description: str
    x_axis_field: Optional[str] = None
    y_axis_field: Optional[str] = None
    series_name: Optional[str] = None
    formatting: Dict[str, Any] = Field(default_factory=dict)
    data: List[Dict[str, Any]] = Field(default_factory=list)
    kpi_value: Optional[float] = None
    kpi_label: Optional[str] = None
    available: bool = True
    empty_reason: Optional[str] = None


# -------------------------------------------------------------
# Advanced Findings Schemas (Phase 12)
# -------------------------------------------------------------
class TrendFinding(BaseModel):
    metric: str
    direction: str  # "increasing", "decreasing", "stable"
    growth_pct: float
    highest_period: Optional[str] = None
    highest_value: Optional[float] = None
    lowest_period: Optional[str] = None
    lowest_value: Optional[float] = None
    summary_statement: str
    periods_analyzed: int


class AnomalyFinding(BaseModel):
    metric: str
    period_or_record: str
    observed_value: float
    expected_value: float
    deviation: float
    deviation_pct: float
    method: str  # "IQR", "Z-Score", "Rolling Deviation"
    severity: str  # "High", "Medium", "Low"
    statement: str


class SegmentComparisonFinding(BaseModel):
    dimension: str
    top_segment: str
    top_segment_value: float
    bottom_segment: str
    bottom_segment_value: float
    metric: str
    spread_pct: float
    associated_pattern: Optional[str] = None
    statement: str


class AdvancedFindingsReport(BaseModel):
    trends: List[TrendFinding] = Field(default_factory=list)
    anomalies: List[AnomalyFinding] = Field(default_factory=list)
    segment_comparisons: List[SegmentComparisonFinding] = Field(default_factory=list)
    summary: str
    has_date_dimension: bool = False
    empty_reason: Optional[str] = None


# -------------------------------------------------------------
# Scenario Comparison Schemas (Phase 13)
# -------------------------------------------------------------
class ScenarioComparisonItem(BaseModel):
    id: Optional[str] = None
    name: str
    revenue: float
    profit: float
    profit_margin_pct: float
    incremental_value: float  # Labeled Incremental Value / Incremental Economic Value
    risk_adjusted_return: float
    revenue_delta: float
    profit_delta: float
    parameters: Dict[str, Any] = Field(default_factory=dict)
    intervention_summary: Optional[str] = None
    notes: Optional[str] = None


class ScenarioComparisonReport(BaseModel):
    scenarios: List[ScenarioComparisonItem] = Field(default_factory=list)
    comparison_insights: List[str] = Field(default_factory=list)
    best_profit_scenario: Optional[str] = None
    best_revenue_scenario: Optional[str] = None
    best_margin_scenario: Optional[str] = None


class SaveScenarioRequest(BaseModel):
    analysis_id: str
    name: str
    parameters: Dict[str, Any]
    projected_outcomes: Optional[Dict[str, Any]] = None


class ScenarioUpdateRequest(BaseModel):
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    projected_outcomes: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Forecasting Schemas (Phase 16)
# -------------------------------------------------------------
class HistoricalPoint(BaseModel):
    period: str
    value: float


class ForecastPoint(BaseModel):
    period: str
    value: float
    lower_bound: float
    upper_bound: float


class ForecastValidationMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float


class ForecastModelResult(BaseModel):
    model_name: str
    model_type: str  # linear, moving_average, exponential_smoothing
    parameters: Dict[str, Any] = Field(default_factory=dict)
    validation_metrics: ForecastValidationMetrics
    forecast_points: List[ForecastPoint] = Field(default_factory=list)
    is_recommended: bool = False
    description: str


class ForecastReport(BaseModel):
    is_available: bool
    reason: Optional[str] = None
    metric_name: Optional[str] = None
    frequency: Optional[str] = None
    horizon_periods: int = 3
    historical_series: List[HistoricalPoint] = Field(default_factory=list)
    models: List[ForecastModelResult] = Field(default_factory=list)
    recommended_model: Optional[str] = None
    trajectory_narrative: Optional[str] = None
    disclaimer: str = "Forecasts represent deterministic statistical extrapolations and do not account for external market shifts or operational disruptions."


class ForecastRequest(BaseModel):
    metric_col: Optional[str] = None
    date_col: Optional[str] = None
    horizon: Optional[int] = 3
    model_type: Optional[str] = None


# -------------------------------------------------------------
# Stored Analyses Schemas (History & Management)
# -------------------------------------------------------------
class StoredAnalysisSummary(BaseModel):
    id: str
    analysis_name: str
    dataset_id: str
    dataset_name: str
    dataset_version: Optional[str] = None
    target_column: Optional[str] = None
    date_column: Optional[str] = None
    status: str
    execution_time_ms: int
    health_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRenameRequest(BaseModel):
    analysis_name: str


# -------------------------------------------------------------
# KPI Goal Tracking Schemas
# -------------------------------------------------------------
class KpiGoalCreate(BaseModel):
    dataset_id: str
    analysis_id: Optional[str] = None
    metric: str
    target_type: str = "absolute"  # absolute, percentage_growth
    target_value: float
    notes: Optional[str] = None


class KpiGoalUpdate(BaseModel):
    target_value: Optional[float] = None
    notes: Optional[str] = None
    target_type: Optional[str] = None


class KpiGoalResponse(BaseModel):
    id: str
    dataset_id: str
    analysis_id: Optional[str] = None
    metric: str
    target_type: str
    target_value: float
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    progress_pct: float = 0.0
    status: str = "Below Target"
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Drill-Down Analysis Schemas
# -------------------------------------------------------------
class DrillDownRequest(BaseModel):
    dimension: str
    metric: Optional[str] = None
    aggregation: Optional[str] = "sum"  # sum, mean, count
    parent_filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10


class DrillDownSegment(BaseModel):
    dimension_value: str
    metric_value: float
    share_pct: float
    record_count: int
    variance_from_mean_pct: Optional[float] = None


class DrillDownResponse(BaseModel):
    dimension: str
    metric: str
    total_value: float
    parent_filters: Dict[str, Any] = Field(default_factory=dict)
    segments: List[DrillDownSegment] = Field(default_factory=list)
    next_suggested_dimensions: List[str] = Field(default_factory=list)
    echarts_spec: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# Ask Your Data Schemas
# -------------------------------------------------------------
class AskDataRequest(BaseModel):
    query: str


class AskDataParsedIntent(BaseModel):
    intent: str
    metric: Optional[str] = None
    dimension: Optional[str] = None
    aggregation: Optional[str] = "sum"
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = "desc"
    limit: Optional[int] = 10
    time_granularity: Optional[str] = None


class AskDataResponse(BaseModel):
    query: str
    understood: bool
    answer_text: str
    metric_value: Optional[float] = None
    table_data: Optional[List[Dict[str, Any]]] = None
    echarts_spec: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    suggested_followups: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# Forecast vs Actual Schemas
# -------------------------------------------------------------
class ForecastCompareItem(BaseModel):
    period: str
    actual: float
    forecast: float
    variance: float
    variance_pct: float
    in_confidence_interval: bool


class ForecastCompareResponse(BaseModel):
    metric: str
    model_name: str
    horizon: int
    comparison: List[ForecastCompareItem] = Field(default_factory=list)
    accuracy_summary: Dict[str, Any] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    echarts_spec: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# Decision Impact Matrix Schemas
# -------------------------------------------------------------
class DecisionImpactItem(BaseModel):
    recommendation_id: str
    action_title: str
    expected_impact_dollars: float
    impact_score: float
    effort_score: float
    implementation_effort: str
    timeframe: str
    quadrant: str
    supporting_finding: str


class DecisionImpactMatrixResponse(BaseModel):
    items: List[DecisionImpactItem] = Field(default_factory=list)
    quadrant_counts: Dict[str, int] = Field(default_factory=dict)
    echarts_spec: Dict[str, Any] = Field(default_factory=dict)
    executive_summary: str


# -------------------------------------------------------------
# "Why This Result?" Explanation Schemas
# -------------------------------------------------------------
class WhyThisResultResponse(BaseModel):
    result_type: str
    result_id: str
    title: str
    plain_english_summary: str
    primary_driver: str
    supporting_evidence: List[str] = Field(default_factory=list)
    methodology_applied: str
    underlying_formulas_or_logic: str
    data_inputs_used: List[str] = Field(default_factory=list)
    limitations_and_assumptions: List[str] = Field(default_factory=list)
    causation_disclaimer: str = "Correlation and deterministic associations do not prove business causation. External market and organizational factors must be considered."



