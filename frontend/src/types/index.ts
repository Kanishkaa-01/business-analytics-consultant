export interface ColumnMetadata {
  name: string;
  dtype: string;
  inferred_type: 'numeric' | 'categorical' | 'datetime' | 'text' | 'identifier';
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: any[];
  min_val?: number | string | null;
  max_val?: number | string | null;
  mean_val?: number | null;
  median_val?: number | null;
  std_val?: number | null;
}

export interface DatasetSummary {
  id: string;
  name: string;
  filename: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  is_sample: boolean;
  created_at: string;
}

export interface DatasetDetail extends DatasetSummary {
  file_hash: string;
  schema_metadata: {
    file_type?: 'structured_dataset' | 'document';
    format?: 'csv' | 'xlsx' | 'pdf' | 'docx';
    title?: string;
    author?: string;
    page_count?: number;
    section_count?: number;
    paragraph_count?: number;
    heading_count?: number;
    table_count?: number;
    evidence_count?: number;
    structured_metrics?: Record<string, any>;
    columns: ColumnMetadata[];
    numeric_candidates: string[];
    datetime_candidates: string[];
    categorical_candidates: string[];
    suggested_target?: string;
    suggested_date?: string;
  };
  preview_rows: Record<string, any>[];
}

export interface SourceLocation {
  page_number?: number | null;
  heading_or_section?: string | null;
  sheet_name?: string | null;
  column_name?: string | null;
  row_index?: number | null;
  bbox?: number[] | null;
}

export interface NormalizedEvidenceItem {
  id: string;
  source_id: string;
  source_filename: string;
  source_type: 'csv' | 'xlsx' | 'pdf' | 'docx';
  evidence_type: 'structured_quantitative' | 'documentary_textual';
  content: string;
  metric_name?: string | null;
  metric_value?: number | null;
  unit?: string | null;
  temporal_period?: string | null;
  entity_segment?: string | null;
  location: SourceLocation;
  confidence_score: number;
  reliability_metadata: Record<string, any>;
}

export interface ExtractedTable {
  table_index: number;
  location: SourceLocation;
  caption?: string | null;
  headers: string[];
  rows: any[][];
  row_count: number;
  col_count: number;
}

export interface ExtractedDocument {
  dataset_id: string;
  filename: string;
  format: 'pdf' | 'docx' | 'csv' | 'xlsx';
  title?: string | null;
  author?: string | null;
  page_or_section_count: number;
  metadata: Record<string, any>;
  paragraphs: Array<{ text: string; page?: number; section?: string; bbox?: number[] }>;
  headings: Array<{ text: string; level: number; page?: number }>;
  tables: ExtractedTable[];
  evidence_items: NormalizedEvidenceItem[];
  structured_metrics_found: Record<string, any>;
}

export interface QualityIssue {
  severity: 'Critical' | 'Warning' | 'Info';
  dimension: 'Completeness' | 'Validity' | 'Uniqueness' | 'Consistency' | 'Distribution';
  column?: string | null;
  description: string;
  affected_rows: number;
  percentage: number;
  recommendation: string;
}

export interface ColumnQualityMetric {
  column: string;
  completeness_score: number;
  validity_score: number;
  outlier_count: number;
  outlier_percentage: number;
  skewness?: number | null;
}

export interface DataQualityReport {
  overall_quality_score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  total_records: number;
  duplicate_rows: number;
  completeness_ratio: number;
  validity_ratio: number;
  consistency_ratio: number;
  issues: QualityIssue[];
  column_metrics: ColumnQualityMetric[];
  reliability_assessment: string;
}

export interface KpiMetric {
  name: string;
  current_value: number;
  target_or_baseline?: number | null;
  variance_pct?: number | null;
  unit: string;
  trend: 'improving' | 'deteriorating' | 'stable';
  status: 'healthy' | 'warning' | 'critical';
  interpretation: string;
}

export interface OverviewMetrics {
  total_revenue?: number | null;
  total_profit?: number | null;
  profit_margin_pct?: number | null;
  transactions_count?: number | null;
  average_order_value?: number | null;
  unique_customers?: number | null;
  growth_rate_pct?: number | null;
  average_discount_pct?: number | null;
}

export interface BusinessHealthOverview {
  overall_health_score: number;
  overall_status: 'Strong' | 'Stable' | 'Vulnerable' | 'Distressed';
  executive_summary: string;
  kpis: KpiMetric[];
  vital_signs: Record<string, any>;
  overview_metrics?: OverviewMetrics;
  timeline_series?: Array<{
    period: string;
    metric_sum: number;
    metric_mean: number;
    count: number;
  }>;
  health_breakdown?: Array<{
    component: string;
    metric_name: string;
    raw_value: number;
    unit: string;
    trend_direction: string;
    normalized_score: number;
    weight_pct: number;
    weighted_score: number;
    status: string;
  }>;
  primary_pressure?: {
    component: string;
    metric_name?: string;
    score: number;
    raw_value?: number;
    unit?: string;
    impact: string;
    description: string;
  };
  health_methodology?: string;
}

export interface VarianceBreakdownItem {
  dimension: string;
  segment: string;
  baseline_value: number;
  actual_value: number;
  variance: number;
  variance_pct: number;
  contribution_share_pct: number;
  direction: 'Drag' | 'Lift';
}

export interface SegmentDiagnostic {
  dimension: string;
  underperforming_segments: Array<{
    segment: string;
    variance: number;
    variance_pct: number;
    share_pct: number;
  }>;
  overperforming_segments: Array<{
    segment: string;
    variance: number;
    variance_pct: number;
    share_pct: number;
  }>;
  dispersion_gini_or_cv: number;
}

export interface FindingItem {
  title: string;
  type: 'Problem' | 'Opportunity';
  metric: string;
  observed_value: string;
  comparison: string;
  difference: string;
  possible_reason: string;
  recommended_action: string;
}

export interface DiagnosticReport {
  focal_metric: string;
  total_variance: number;
  variance_pct: number;
  variance_breakdown: VarianceBreakdownItem[];
  segment_diagnostics: SegmentDiagnostic[];
  anomalies_detected: Array<{
    type: string;
    count: number;
    sample_impact: number;
    description: string;
    focal_record_info: Record<string, string>;
  }>;
  diagnostic_narrative: string;
  findings?: FindingItem[];
}

export interface FactorContribution {
  factor_name: string;
  factor_type: string;
  attribution_percentage: number;
  statistical_significance_p_value: number;
  correlation_or_coef: number;
  direction: string;
  evidence_statement: string;
}

export interface ParetoItem {
  entity: string;
  loss_or_impact: number;
  contribution_percentage?: number;
  cumulative_percentage: number;
  is_vital_few: boolean;
}

export interface RootCauseReport {
  primary_root_cause: string;
  secondary_root_causes: string[];
  factor_contributions: FactorContribution[];
  pareto_breakdown: ParetoItem[];
  causal_tree_structure: Record<string, any>;
  statistical_confidence_level: number;
  methodology_notes: string;
  possible_reasons_summary?: string;
  causation_disclaimer?: string;
}

export interface RiskItem {
  id: string;
  title: string;
  category: string;
  severity: 'High' | 'Medium' | 'Low';
  probability_pct: number;
  estimated_financial_exposure: number;
  root_cause_ref: string;
  early_warning_signals: string[];
  mitigation_window_days: number;
}

export interface OpportunityItem {
  id: string;
  title: string;
  category: string;
  potential_value_gain: number;
  feasibility: 'High' | 'Medium' | 'Complex';
  confidence_level_pct: number;
  target_segment: string;
  strategic_rationale: string;
}

export interface RisksAndOpportunitiesReport {
  total_exposure_at_risk: number;
  total_opportunity_upside: number;
  risk_profile_rating: string;
  risks: RiskItem[];
  opportunities: OpportunityItem[];
}

export interface EvidenceNode {
  stage: string;
  detail: string;
  metric_or_statistic: string;
  data_support: string;
}

export interface EvidenceChain {
  id: string;
  title: string;
  target_metric: string;
  observed_phenomenon: string;
  diagnostic_pathway: string[];
  underlying_mechanism: string;
  statistical_proof: string;
  associated_recommendation_id: string;
  nodes: EvidenceNode[];
  disclaimer?: string;
}

export interface RecommendationItem {
  id: string;
  title: string;
  urgency: string;
  category: string;
  mechanism_of_action: string;
  rationale: string;
  prerequisites: string[];
  expected_financial_impact: number;
  implementation_effort: 'Low' | 'Medium' | 'High';
  confidence_score_pct: number;
  impact_score: number;
  confidence_score: number;
  ease_score: number;
  priority_score: number;
  priority_tier: string;
  tradeoffs_and_risks: string;
  status: string;
  what_to_do?: string;
  why?: string;
  evidence?: string;
  expected_impact_label?: string;
  difficulty?: string;
  priority_label?: string;
  possible_risk?: string;
  // Phase 14 Standardized Fields
  recommendation?: string;
  reason?: string;
  supporting_finding?: string;
  priority_level?: string;
  decision_status?: string;
}

export interface DecisionRecord {
  id: string;
  analysis_id: string;
  recommendation_id: string;
  action_title: string;
  decision_status: 'Accepted' | 'Rejected' | 'Deferred' | 'Under Review';
  stakeholder?: string;
  notes_rationale?: string;
  target_date?: string;
  expected_impact_dollars: number;
  created_at: string;
  updated_at: string;
}

export interface SimulationRequest {
  analysis_id: string;
  price_change_pct: number;
  volume_change_pct?: number;
  discount_adjustment_pct: number;
  churn_mitigation_pct: number;
  operational_efficiency_pct: number;
  intervention_type?: string;
  parameter_type?: 'percentage' | 'percentage_points';
  notes?: string;
}

export interface SimulationOutcome {
  baseline_revenue: number;
  simulated_revenue: number;
  revenue_delta: number;
  revenue_delta_pct: number;
  baseline_profit: number;
  simulated_profit: number;
  profit_delta: number;
  profit_delta_pct: number;
  baseline_margin_pct?: number;
  simulated_margin_pct?: number;
  margin_delta_pct?: number;
  simulation_insights?: string[];
  net_economic_value_added: number;
  risk_adjusted_return: number;
  sensitivity_breakdown: Record<string, number>;
  recommendation_impact_overlap: string[];
  sensitivity_table?: Array<{
    lever: string;
    step: string;
    revenue_impact: number;
    profit_impact: number;
    is_supported: boolean;
  }>;
  assumptions_statement?: string;
  supported_interventions?: string[];
}

export interface AnalysisRunResponse {
  id: string;
  dataset_id: string;
  target_column: string;
  date_column?: string | null;
  status: string;
  execution_time_ms: number;
  created_at: string;
  data_quality: DataQualityReport;
  business_health: BusinessHealthOverview;
  diagnostics: DiagnosticReport;
  root_cause: RootCauseReport;
  risks_opportunities: RisksAndOpportunitiesReport;
  evidence_chains: EvidenceChain[];
  recommendations: RecommendationItem[];
  decisions: DecisionRecord[];
}

export interface ChartSpecification {
  chart_type: 'bar' | 'line' | 'pie' | 'scatter' | 'kpi' | 'none';
  title: string;
  description: string;
  x_axis_field?: string;
  y_axis_field?: string;
  series_name?: string;
  formatting?: Record<string, any>;
  data?: Array<Record<string, any>>;
  kpi_value?: number;
  kpi_label?: string;
  available: boolean;
  empty_reason?: string;
}

export interface TrendFinding {
  metric: string;
  direction: 'increasing' | 'decreasing' | 'stable';
  growth_pct: number;
  highest_period?: string;
  highest_value?: number;
  lowest_period?: string;
  lowest_value?: number;
  summary_statement: string;
  periods_analyzed: number;
}

export interface AnomalyFinding {
  metric: string;
  period_or_record: string;
  observed_value: number;
  expected_value: number;
  deviation: number;
  deviation_pct: number;
  method: string;
  severity: 'High' | 'Medium' | 'Low';
  statement: string;
}

export interface SegmentComparisonFinding {
  dimension: string;
  top_segment: string;
  top_segment_value: number;
  bottom_segment: string;
  bottom_segment_value: number;
  metric: string;
  spread_pct: number;
  associated_pattern?: string;
  statement: string;
}

export interface AdvancedFindingsReport {
  trends: TrendFinding[];
  anomalies: AnomalyFinding[];
  segment_comparisons: SegmentComparisonFinding[];
  summary: string;
  has_date_dimension: boolean;
  empty_reason?: string;
}

export interface ScenarioComparisonItem {
  id?: string;
  name: string;
  revenue: number;
  profit: number;
  profit_margin_pct: number;
  incremental_value: number;
  risk_adjusted_return: number;
  revenue_delta: number;
  profit_delta: number;
  parameters: Record<string, any>;
  intervention_summary?: string;
  notes?: string;
}

export interface ScenarioComparisonReport {
  scenarios: ScenarioComparisonItem[];
  comparison_insights: string[];
  best_profit_scenario?: string;
  best_revenue_scenario?: string;
  best_margin_scenario?: string;
}

// -------------------------------------------------------------
// Forecasting Interfaces (Phase 16)
// -------------------------------------------------------------
export interface HistoricalPoint {
  period: string;
  value: number;
}

export interface ForecastPoint {
  period: string;
  value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastValidationMetrics {
  mae: number;
  rmse: number;
  mape: number;
}

export interface ForecastModelResult {
  model_name: string;
  model_type: 'linear' | 'moving_average' | 'exponential_smoothing';
  parameters: Record<string, any>;
  validation_metrics: ForecastValidationMetrics;
  forecast_points: ForecastPoint[];
  is_recommended: boolean;
  description: string;
}

export interface ForecastReport {
  is_available: boolean;
  reason?: string;
  metric_name?: string;
  frequency?: string;
  horizon_periods: number;
  historical_series: HistoricalPoint[];
  models: ForecastModelResult[];
  recommended_model?: string;
  trajectory_narrative?: string;
  disclaimer: string;
}

export interface ForecastRequest {
  metric_col?: string;
  date_col?: string;
  horizon?: number;
  model_type?: string;
}

// -------------------------------------------------------------
// Stored Analyses (History & Management)
// -------------------------------------------------------------
export interface StoredAnalysisSummary {
  id: string;
  analysis_name: string;
  dataset_id: string;
  dataset_name: string;
  dataset_version?: string | null;
  target_column?: string | null;
  date_column?: string | null;
  status: string;
  execution_time_ms: number;
  health_score?: number | null;
  created_at: string;
  completed_at?: string | null;
}

export interface PaginatedStoredAnalysesResponse {
  items: StoredAnalysisSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// -------------------------------------------------------------
// KPI Goal Tracking
// -------------------------------------------------------------
export interface KpiGoalResponse {
  id: string;
  dataset_id: string;
  analysis_id?: string | null;
  metric: string;
  target_type: 'absolute' | 'percentage_growth';
  target_value: number;
  baseline_value?: number | null;
  current_value?: number | null;
  progress_pct: number;
  status: 'On Track' | 'Near Target' | 'Below Target' | 'Target Achieved' | string;
  notes?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface KpiGoalCreate {
  dataset_id: string;
  analysis_id?: string | null;
  metric: string;
  target_type?: 'absolute' | 'percentage_growth';
  target_value: number;
  notes?: string | null;
}

// -------------------------------------------------------------
// Drill-Down Analysis
// -------------------------------------------------------------
export interface DrillDownSegment {
  dimension_value: string;
  metric_value: number;
  share_pct: number;
  record_count: number;
  variance_from_mean_pct?: number | null;
}

export interface DrillDownResponse {
  dimension: string;
  metric: string;
  total_value: number;
  parent_filters: Record<string, any>;
  segments: DrillDownSegment[];
  next_suggested_dimensions: string[];
  echarts_spec: Record<string, any>;
}

// -------------------------------------------------------------
// Ask Your Data
// -------------------------------------------------------------
export interface AskDataResponse {
  query: string;
  understood: boolean;
  answer_text: string;
  metric_value?: number | null;
  table_data?: Record<string, any>[] | null;
  echarts_spec?: Record<string, any> | null;
  explanation?: string | null;
  suggested_followups: string[];
}

// -------------------------------------------------------------
// Forecast vs Actual
// -------------------------------------------------------------
export interface ForecastCompareItem {
  period: string;
  actual: number;
  forecast: number;
  variance: number;
  variance_pct: number;
  in_confidence_interval: boolean;
}

export interface ForecastCompareResponse {
  metric: string;
  model_name: string;
  horizon: number;
  comparison: ForecastCompareItem[];
  accuracy_summary: Record<string, any>;
  insights: string[];
  echarts_spec: Record<string, any>;
}

// -------------------------------------------------------------
// Decision Impact Matrix
// -------------------------------------------------------------
export interface DecisionImpactItem {
  recommendation_id: string;
  action_title: string;
  expected_impact_dollars: number;
  impact_score: number;
  effort_score: number;
  implementation_effort: string;
  timeframe: string;
  quadrant: 'Quick Wins' | 'Strategic Bets' | 'Fill-ins' | 'Re-evaluate';
  supporting_finding: string;
}

export interface DecisionImpactMatrixResponse {
  items: DecisionImpactItem[];
  quadrant_counts: Record<string, number>;
  echarts_spec: Record<string, any>;
  executive_summary: string;
}

// -------------------------------------------------------------
// "Why This Result?" Explanations
// -------------------------------------------------------------
export interface WhyThisResultResponse {
  result_type: string;
  result_id: string;
  title: string;
  plain_english_summary: string;
  primary_driver: string;
  supporting_evidence: string[];
  methodology_applied: string;
  underlying_formulas_or_logic: string;
  data_inputs_used: string[];
  limitations_and_assumptions: string[];
  causation_disclaimer: string;
}


