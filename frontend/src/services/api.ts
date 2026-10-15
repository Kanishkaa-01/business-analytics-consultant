import {
  DatasetSummary,
  DatasetDetail,
  AnalysisRunResponse,
  DecisionRecord,
  SimulationRequest,
  SimulationOutcome,
  ExtractedDocument,
  ChartSpecification,
  AdvancedFindingsReport,
  ScenarioComparisonReport,
  ForecastReport,
  ForecastRequest,
  StoredAnalysisSummary,
  KpiGoalResponse,
  KpiGoalCreate,
  DrillDownResponse,
  AskDataResponse,
  ForecastCompareResponse,
  DecisionImpactMatrixResponse,
  WhyThisResultResponse,
} from '../types';

const API_BASE = '/api';

export const api = {
  async getHealth(): Promise<{ status: string; database_dialect: string }> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Backend health check failed');
    return res.json();
  },

  async listDatasets(): Promise<DatasetSummary[]> {
    const res = await fetch(`${API_BASE}/datasets`);
    if (!res.ok) throw new Error('Failed to fetch datasets');
    return res.json();
  },

  async getDataset(id: string): Promise<DatasetDetail> {
    const res = await fetch(`${API_BASE}/datasets/${id}`);
    if (!res.ok) throw new Error(`Failed to load dataset ${id}`);
    return res.json();
  },

  async getExtractedDocument(id: string): Promise<ExtractedDocument> {
    const res = await fetch(`${API_BASE}/datasets/${id}/extracted`);
    if (!res.ok) throw new Error(`Failed to extract document ${id}`);
    return res.json();
  },

  async uploadDataset(file: File): Promise<DatasetDetail> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async seedSamples(): Promise<DatasetSummary[]> {
    const res = await fetch(`${API_BASE}/datasets/seed-samples`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to seed sample datasets');
    return res.json();
  },

  async deleteDataset(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/datasets/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete dataset');
  },

  async runAnalysis(
    datasetId: string,
    targetColumn?: string,
    dateColumn?: string
  ): Promise<AnalysisRunResponse> {
    const res = await fetch(`${API_BASE}/analysis/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_id: datasetId,
        target_column: targetColumn || null,
        date_column: dateColumn || null,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(err.detail || 'Analysis execution error');
    }
    return res.json();
  },

  async getAnalysis(analysisId: string): Promise<AnalysisRunResponse> {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}`);
    if (!res.ok) throw new Error(`Failed to retrieve analysis ${analysisId}`);
    return res.json();
  },

  async recordDecision(
    analysisId: string,
    payload: {
      recommendation_id: string;
      action_title: string;
      decision_status: string;
      stakeholder?: string;
      notes_rationale?: string;
      target_date?: string;
      expected_impact_dollars?: number;
    }
  ): Promise<DecisionRecord> {
    const res = await fetch(`${API_BASE}/decisions/${analysisId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to record decision');
    return res.json();
  },

  async updateDecision(
    decisionId: string,
    payload: {
      decision_status: string;
      stakeholder?: string;
      notes_rationale?: string;
      target_date?: string;
      expected_impact_dollars?: number;
    }
  ): Promise<DecisionRecord> {
    const res = await fetch(`${API_BASE}/decisions/${decisionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to update decision');
    return res.json();
  },

  async runSimulation(req: SimulationRequest): Promise<SimulationOutcome> {
    const res = await fetch(`${API_BASE}/simulation/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error('Failed to run simulation');
    return res.json();
  },

  async saveScenario(
    analysisId: string,
    name: string,
    parameters: any,
    projectedOutcomes?: any
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/simulation/save-scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: analysisId,
        name,
        parameters,
        projected_outcomes: projectedOutcomes,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to save scenario' }));
      throw new Error(err.detail || 'Failed to save scenario');
    }
    return res.json();
  },

  async updateScenario(
    scenarioId: string,
    payload: {
      name?: string;
      parameters?: any;
      projected_outcomes?: any;
    }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/simulation/scenario/${scenarioId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update scenario' }));
      throw new Error(err.detail || 'Failed to update scenario');
    }
    return res.json();
  },

  async listSavedScenarios(analysisId: string): Promise<any[]> {
    const res = await fetch(`${API_BASE}/simulation/${analysisId}/scenarios`);
    if (!res.ok) throw new Error('Failed to list scenarios');
    return res.json();
  },

  async getDossier(analysisId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/export/${analysisId}/dossier`);
    if (!res.ok) throw new Error('Failed to fetch dossier');
    return res.json();
  },

  async getVisualization(
    analysisId: string,
    params?: {
      dimension_col?: string;
      second_numeric_col?: string;
      is_part_to_whole?: boolean;
      is_single_kpi?: boolean;
    }
  ): Promise<ChartSpecification> {
    const query = new URLSearchParams();
    if (params?.dimension_col) query.append('dimension_col', params.dimension_col);
    if (params?.second_numeric_col) query.append('second_numeric_col', params.second_numeric_col);
    if (params?.is_part_to_whole) query.append('is_part_to_whole', 'true');
    if (params?.is_single_kpi) query.append('is_single_kpi', 'true');

    const res = await fetch(`${API_BASE}/analysis/${analysisId}/visualization?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to retrieve visualization');
    return res.json();
  },

  async getAdvancedFindings(analysisId: string): Promise<AdvancedFindingsReport> {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/advanced-findings`);
    if (!res.ok) throw new Error('Failed to retrieve advanced findings');
    return res.json();
  },

  async deleteScenario(scenarioId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/simulation/scenario/${scenarioId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete scenario');
  },

  async compareScenarios(analysisId: string): Promise<ScenarioComparisonReport> {
    const res = await fetch(`${API_BASE}/simulation/${analysisId}/compare`);
    if (!res.ok) throw new Error('Failed to retrieve scenario comparison');
    return res.json();
  },

  async getForecast(analysisId: string, payload?: ForecastRequest): Promise<ForecastReport> {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) throw new Error('Failed to retrieve forecast');
    return res.json();
  },

  async listStoredAnalyses(search?: string): Promise<StoredAnalysisSummary[]> {
    const url = search ? `${API_BASE}/analyses?search=${encodeURIComponent(search)}` : `${API_BASE}/analyses`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch stored analyses');
    return res.json();
  },

  async renameAnalysis(analysisId: string, analysisName: string): Promise<StoredAnalysisSummary> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/rename`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_name: analysisName }),
    });
    if (!res.ok) throw new Error('Failed to rename analysis');
    return res.json();
  },

  async deleteAnalysis(analysisId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete analysis');
  },

  async askData(datasetId: string, query: string): Promise<AskDataResponse> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Ask Your Data query failed' }));
      throw new Error(err.detail || 'Ask Your Data query failed');
    }
    return res.json();
  },

  async getSuggestedQuestions(datasetId: string): Promise<string[]> {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/suggested-questions`);
    if (!res.ok) throw new Error('Failed to fetch suggested questions');
    return res.json();
  },

  async drillDown(
    analysisId: string,
    payload: {
      dimension: string;
      metric?: string;
      aggregation?: string;
      parent_filters?: Record<string, any>;
      limit?: number;
    }
  ): Promise<DrillDownResponse> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/drill-down`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Drill-down request failed' }));
      throw new Error(err.detail || 'Drill-down request failed');
    }
    return res.json();
  },

  async getForecastVsActual(analysisId: string, payload?: ForecastRequest): Promise<ForecastCompareResponse> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/forecast-vs-actual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) throw new Error('Failed to retrieve forecast vs actual comparison');
    return res.json();
  },

  async getDecisionImpactMatrix(analysisId: string): Promise<DecisionImpactMatrixResponse> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/decision-impact`);
    if (!res.ok) throw new Error('Failed to retrieve decision impact matrix');
    return res.json();
  },

  async getWhyThisResult(
    analysisId: string,
    resultType: string,
    resultId: string
  ): Promise<WhyThisResultResponse> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/explanations/${encodeURIComponent(resultType)}/${encodeURIComponent(resultId)}`);
    if (!res.ok) throw new Error('Failed to retrieve result explanation');
    return res.json();
  },

  async listGoals(analysisId: string): Promise<KpiGoalResponse[]> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/goals`);
    if (!res.ok) throw new Error('Failed to retrieve KPI goals');
    return res.json();
  },

  async createGoal(analysisId: string, payload: KpiGoalCreate): Promise<KpiGoalResponse> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create goal' }));
      throw new Error(err.detail || 'Failed to create goal');
    }
    return res.json();
  },

  async deleteGoal(analysisId: string, goalId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/analyses/${analysisId}/goals/${goalId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete goal');
  },
};

