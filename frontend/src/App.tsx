import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import {
  DatasetSummary,
  DatasetDetail,
  AnalysisRunResponse,
  DecisionRecord,
  RecommendationItem
} from './types';
import { Header } from './components/Header';
import { WorkflowStage } from './components/workflow/WorkflowStepper';
import { WorkspaceSidebar } from './components/workflow/WorkspaceSidebar';
import { HomePage } from './pages/HomePage';
import { Stage0_DatasetManager } from './components/stages/Stage0_DatasetManager';
import { Stage1_DataQuality } from './components/stages/Stage1_DataQuality';
import { Stage2_BusinessOverview } from './components/stages/Stage2_BusinessOverview';
import { Stage3_Findings } from './components/stages/Stage3_Findings';
import { Stage4_PossibleReasons } from './components/stages/Stage4_PossibleReasons';
import { Stage5_Recommendations } from './components/stages/Stage5_Recommendations';
import { Stage6_EvidenceTrail } from './components/stages/Stage6_EvidenceTrail';
import { Stage7_WhatIfAnalysis } from './components/stages/Stage7_WhatIfAnalysis';
import { Stage8_DecisionNotes } from './components/stages/Stage8_DecisionNotes';
import { DecisionModal } from './components/common/DecisionModal';
import { UploadModal } from './components/common/UploadModal';
import { WhyThisResultModal } from './components/common/WhyThisResultModal';
import { DrillDownModal } from './components/analysis/DrillDownModal';
import { StoredAnalysesPage } from './pages/StoredAnalysesPage';
import { AskYourDataPage } from './pages/AskYourDataPage';
import { KpiGoalsPage } from './pages/KpiGoalsPage';
import { ExploreDetailsPage } from './pages/ExploreDetailsPage';
import { AlertCircle } from 'lucide-react';

export type ViewMode =
  | 'home'
  | 'workspace'
  | 'history'
  | 'ask_data'
  | 'kpi_goals'
  | 'explore_details';

export const App: React.FC = () => {
  const [dbDialect, setDbDialect] = useState<string>('database');
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetDetail | null>(null);
  const [targetCol, setTargetCol] = useState<string>('');
  const [dateCol, setDateCol] = useState<string>('');
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisRunResponse | null>(null);
  const [currentStage, setCurrentStage] = useState<WorkflowStage>('data');

  // Primary View Mode: 'home' | 'workspace' | 'history' | 'ask_data' | 'kpi_goals' | 'explore_details'
  const [viewMode, setViewMode] = useState<ViewMode>('home');

  // Modals & UI states
  const [isSeeding, setIsSeeding] = useState<boolean>(false);
  const [isUploadingModalOpen, setIsUploadingModalOpen] = useState<boolean>(false);
  const [isRunningPipeline, setIsRunningPipeline] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Decision Modal State
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState<boolean>(false);
  const [focalRecommendation, setFocalRecommendation] = useState<RecommendationItem | null>(null);

  // "Why This Result?" Modal State
  const [whyModal, setWhyModal] = useState<{
    isOpen: boolean;
    resultType: string;
    resultId: string;
  }>({
    isOpen: false,
    resultType: 'health_score',
    resultId: 'overall',
  });

  // Drill-Down Modal State
  const [drillModal, setDrillModal] = useState<{
    isOpen: boolean;
    initialDimension?: string;
    targetMetric?: string;
  }>({
    isOpen: false,
    initialDimension: undefined,
    targetMetric: undefined,
  });

  // 1. Initial Load: check health and load datasets
  useEffect(() => {
    initApp();
  }, []);

  const initApp = async () => {
    try {
      const health = await api.getHealth();
      setDbDialect(health.database_dialect);
    } catch (err) {
      console.warn('Backend health check error:', err);
    }

    try {
      let dsList = await api.listDatasets();
      if (dsList.length === 0) {
        setIsSeeding(true);
        dsList = await api.seedSamples();
        setIsSeeding(false);
      }
      setDatasets(dsList);

      if (dsList.length > 0) {
        loadDatasetDetail(dsList[0].id, false);
      }
    } catch (err: any) {
      console.error('Dataset init error:', err);
      setErrorMessage('Could not connect to analytical server. Ensure backend is running.');
    }
  };

  const loadDatasetDetail = async (id: string, switchView = true) => {
    try {
      const detail = await api.getDataset(id);
      setSelectedDataset(detail);
      setTargetCol(detail.schema_metadata.suggested_target || detail.schema_metadata.numeric_candidates[0] || '');
      setDateCol(detail.schema_metadata.suggested_date || '');
      setActiveAnalysis(null);
      setCurrentStage('data');
      if (switchView) {
        setViewMode('workspace');
      }
    } catch (err: any) {
      console.error(err);
      setErrorMessage(`Failed to load dataset: ${err.message}`);
    }
  };

  const handleSeedSamples = async () => {
    setIsSeeding(true);
    setErrorMessage(null);
    try {
      const seeded = await api.seedSamples();
      setDatasets(seeded);
      if (seeded.length > 0) {
        await loadDatasetDetail(seeded[0].id, true);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Seeding failed');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!selectedDataset || !targetCol) return;
    setIsRunningPipeline(true);
    setErrorMessage(null);
    try {
      const res = await api.runAnalysis(selectedDataset.id, targetCol, dateCol);
      setActiveAnalysis(res);
      setViewMode('workspace');
      setCurrentStage('overview');
    } catch (err: any) {
      setErrorMessage(err.message || 'Pipeline execution failed.');
    } finally {
      setIsRunningPipeline(false);
    }
  };

  const handleSaveDecision = async (payload: {
    recommendation_id: string;
    action_title: string;
    decision_status: 'Accepted' | 'Rejected' | 'Deferred' | 'Under Review';
    stakeholder: string;
    notes_rationale: string;
    target_date: string;
    expected_impact_dollars: number;
  }) => {
    if (!activeAnalysis) return;
    try {
      const newDecision = await api.recordDecision(activeAnalysis.id, payload);
      const updatedDecisions = [
        ...activeAnalysis.decisions.filter((d) => d.recommendation_id !== payload.recommendation_id),
        newDecision,
      ];
      setActiveAnalysis({
        ...activeAnalysis,
        decisions: updatedDecisions,
      });
    } catch (err) {
      console.error('Failed to commit decision:', err);
    }
  };

  const handleOpenDecisionModal = (rec: RecommendationItem) => {
    setFocalRecommendation(rec);
    setIsDecisionModalOpen(true);
  };

  const handleOpenWhyResult = (resultType: string, resultId: string) => {
    setWhyModal({
      isOpen: true,
      resultType,
      resultId,
    });
  };

  const handleOpenDrillDown = (dimension?: string, metric?: string) => {
    setDrillModal({
      isOpen: false,
      initialDimension: dimension,
      targetMetric: metric || targetCol,
    });
    setViewMode('explore_details');
  };

  const handleSelectStoredAnalysis = async (analysisId: string) => {
    try {
      setIsRunningPipeline(true);
      const analysisData = await api.getAnalysis(analysisId);
      setActiveAnalysis(analysisData);
      if (analysisData.dataset_id) {
        const dsDetail = await api.getDataset(analysisData.dataset_id).catch(() => null);
        if (dsDetail) {
          setSelectedDataset(dsDetail);
          setTargetCol(analysisData.target_column || dsDetail.schema_metadata.suggested_target || '');
          setDateCol(analysisData.date_column || dsDetail.schema_metadata.suggested_date || '');
        }
      }
      setViewMode('workspace');
      setCurrentStage('overview');
    } catch (err: any) {
      setErrorMessage(`Failed to open analysis: ${err.message}`);
    } finally {
      setIsRunningPipeline(false);
    }
  };

  return (
    <div className="h-screen overflow-hidden bg-slate-50 text-slate-900 flex flex-col antialiased">
      {/* Top Header (Global Product-Level Navigation) */}
      <Header
        dbDialect={dbDialect}
        onOpenUploadModal={() => setIsUploadingModalOpen(true)}
        onSeedSamples={handleSeedSamples}
        isSeeding={isSeeding}
        onOpenStoredAnalyses={() => setViewMode('history')}
        onGoHome={() => setViewMode('home')}
        currentView={viewMode}
      />

      {/* Primary Layout Router: Home vs History vs Workspace Tools */}
      {viewMode === 'home' && (
        <main className="flex-1 min-h-0 overflow-y-auto w-full">
          <HomePage
            onOpenUploadModal={() => setIsUploadingModalOpen(true)}
            onSeedSamples={handleSeedSamples}
            isSeeding={isSeeding}
            onSelectAnalysis={handleSelectStoredAnalysis}
            onOpenStoredAnalyses={() => setViewMode('history')}
          />
        </main>
      )}

      {viewMode === 'history' && (
        <main className="flex-1 min-h-0 overflow-y-auto w-full">
          <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <StoredAnalysesPage
              onSelectAnalysis={handleSelectStoredAnalysis}
              onBackToWorkspace={() => setViewMode(activeAnalysis ? 'workspace' : 'home')}
            />
          </div>
        </main>
      )}

      {viewMode !== 'home' && viewMode !== 'history' && (
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Left Persistent Workspace Sidebar */}
          <WorkspaceSidebar
            currentStage={currentStage}
            onSelectStage={(stage) => {
              setCurrentStage(stage);
              setViewMode('workspace');
            }}
            hasAnalysis={activeAnalysis !== null}
            activeView={viewMode}
            onSelectTool={(tool) => setViewMode(tool)}
            onOpenStoredAnalyses={() => setViewMode('history')}
            onGoHome={() => setViewMode('home')}
            onOpenUploadModal={() => setIsUploadingModalOpen(true)}
            onSeedSamples={handleSeedSamples}
            isSeeding={isSeeding}
          />

          {/* Main Stage / Tool Content Area */}
          <main className="flex-1 min-w-0 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 max-w-7xl mx-auto w-full">
            {errorMessage && (
              <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
                <button
                  onClick={() => setErrorMessage(null)}
                  className="text-rose-600 hover:text-rose-800 font-bold cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Compact Workspace Context Bar (Visually secondary, contextual to workspace) */}
            {selectedDataset && (
              <div className="mb-6 bg-white border border-slate-200/90 rounded-xl px-4 py-2.5 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="font-bold uppercase tracking-wider text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    Analysis Workspace
                  </span>
                  <div className="flex items-center gap-1.5 text-slate-700">
                    <span className="text-slate-400 font-medium">Dataset:</span>
                    <span className="font-bold text-slate-900">{selectedDataset.name}</span>
                  </div>
                  {activeAnalysis?.target_column && (
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <span className="text-slate-400 font-medium">• Primary Metric:</span>
                      <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {activeAnalysis.target_column}
                      </span>
                    </div>
                  )}
                  {activeAnalysis?.business_health?.overall_status && (
                    <div className="flex items-center gap-1.5 text-slate-700">
                      <span className="text-slate-400 font-medium">• Health:</span>
                      <span className="font-bold text-slate-800">
                        {activeAnalysis.business_health.overall_health_score}/100 ({activeAnalysis.business_health.overall_status})
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Dedicated Interactive Tool Pages */}
            {viewMode === 'ask_data' && (
              <AskYourDataPage
                datasetId={selectedDataset?.id}
                datasetName={selectedDataset?.name}
                onBackToWorkspace={() => setViewMode('workspace')}
              />
            )}

            {viewMode === 'kpi_goals' && (
              <KpiGoalsPage
                analysisId={activeAnalysis?.id}
                datasetId={selectedDataset?.id}
                datasetName={selectedDataset?.name}
                onBackToWorkspace={() => setViewMode('workspace')}
              />
            )}

            {viewMode === 'explore_details' && (
              <ExploreDetailsPage
                analysisId={activeAnalysis?.id}
                datasetName={selectedDataset?.name}
                targetMetric={activeAnalysis?.target_column || targetCol}
                availableDimensions={selectedDataset?.schema_metadata.categorical_candidates || []}
                initialDimension={drillModal.initialDimension}
                onBackToWorkspace={() => setViewMode('workspace')}
              />
            )}

            {/* Standard 9-Stage Analysis Workflow */}
            {viewMode === 'workspace' && (
              <>

            {/* 1. Data Upload */}
            {currentStage === 'data' && (
              <Stage0_DatasetManager
                datasets={datasets}
                selectedDataset={selectedDataset}
                onSelectDatasetId={(id) => loadDatasetDetail(id, true)}
                targetCol={targetCol}
                setTargetCol={setTargetCol}
                dateCol={dateCol}
                setDateCol={setDateCol}
                onRunPipeline={handleRunPipeline}
                isRunningPipeline={isRunningPipeline}
              />
            )}

            {/* 2. Data Quality */}
            {currentStage === 'quality' && activeAnalysis && (
              <Stage1_DataQuality report={activeAnalysis.data_quality} />
            )}

            {/* 3. Business Overview ("What is happening?") */}
            {currentStage === 'overview' && activeAnalysis && (
              <Stage2_BusinessOverview
                health={activeAnalysis.business_health}
                onNavigateNext={() => setCurrentStage('findings')}
                analysisId={activeAnalysis.id}
                datasetId={selectedDataset?.id}
                findings={activeAnalysis.diagnostics?.findings || []}
                onOpenWhyResult={handleOpenWhyResult}
                onOpenDrillDown={handleOpenDrillDown}
              />
            )}

            {/* 4. Findings ("What needs attention?") */}
            {currentStage === 'findings' && activeAnalysis && (
              <Stage3_Findings
                diagnostic={activeAnalysis.diagnostics}
                analysisId={activeAnalysis.id}
                onNavigateNext={() => setCurrentStage('reasons')}
                onOpenDrillDown={handleOpenDrillDown}
              />
            )}

            {/* 5. Possible Reasons ("Why might it be happening?") */}
            {currentStage === 'reasons' && activeAnalysis && (
              <Stage4_PossibleReasons
                rootCause={activeAnalysis.root_cause}
                onNavigateNext={() => setCurrentStage('recommendations')}
              />
            )}

            {/* 6. Recommendations ("What could we do?") */}
            {currentStage === 'recommendations' && activeAnalysis && (
              <Stage5_Recommendations
                recommendations={activeAnalysis.recommendations}
                decisions={activeAnalysis.decisions}
                onOpenDecisionModal={handleOpenDecisionModal}
                onNavigateNext={() => setCurrentStage('evidence')}
                analysisId={activeAnalysis.id}
                onOpenWhyResult={handleOpenWhyResult}
              />
            )}

            {/* 7. Evidence ("How do we know?") */}
            {currentStage === 'evidence' && activeAnalysis && (
              <Stage6_EvidenceTrail
                chains={activeAnalysis.evidence_chains}
                onSelectRecommendation={() => {
                  setCurrentStage('recommendations');
                }}
                onNavigateNext={() => setCurrentStage('whatif')}
              />
            )}

            {/* 8. What-If Analysis ("What happens if we change something?") */}
            {currentStage === 'whatif' && activeAnalysis && (
              <Stage7_WhatIfAnalysis
                analysis={activeAnalysis}
                onNavigateNext={() => setCurrentStage('decisions')}
              />
            )}

                {currentStage === 'decisions' && activeAnalysis && (
                  <Stage8_DecisionNotes
                    analysis={activeAnalysis}
                    decisions={activeAnalysis.decisions}
                    recommendations={activeAnalysis.recommendations}
                    onOpenDecisionModal={handleOpenDecisionModal}
                  />
                )}
              </>
            )}
          </main>
        </div>
      )}

      {/* Decision Recording Modal */}
      <DecisionModal
        isOpen={isDecisionModalOpen}
        onClose={() => setIsDecisionModalOpen(false)}
        recommendation={focalRecommendation}
        existingDecision={
          activeAnalysis?.decisions.find(
            (d) => d.recommendation_id === focalRecommendation?.id
          ) || null
        }
        onSaveDecision={handleSaveDecision}
      />

      {/* Upload Dataset/Document Modal */}
      <UploadModal
        isOpen={isUploadingModalOpen}
        onClose={() => setIsUploadingModalOpen(false)}
        onDatasetUploaded={(ds) => {
          setDatasets((prev) => [ds, ...prev]);
          setSelectedDataset(ds);
          setTargetCol(ds.schema_metadata.suggested_target || ds.schema_metadata.numeric_candidates[0] || '');
          setDateCol(ds.schema_metadata.suggested_date || '');
          setActiveAnalysis(null);
          setCurrentStage('data');
          setViewMode('workspace');
        }}
      />

      {/* Deterministic Explanation Modal ("Why This Result?") */}
      {activeAnalysis && (
        <WhyThisResultModal
          isOpen={whyModal.isOpen}
          onClose={() => setWhyModal((prev) => ({ ...prev, isOpen: false }))}
          analysisId={activeAnalysis.id}
          resultType={whyModal.resultType}
          resultId={whyModal.resultId}
        />
      )}

      {/* Interactive Drill-Down Modal */}
      {activeAnalysis && (
        <DrillDownModal
          isOpen={drillModal.isOpen}
          onClose={() => setDrillModal((prev) => ({ ...prev, isOpen: false }))}
          analysisId={activeAnalysis.id}
          initialDimension={drillModal.initialDimension}
          targetMetric={drillModal.targetMetric}
          availableDimensions={selectedDataset?.schema_metadata.categorical_candidates || []}
        />
      )}
    </div>
  );
};

export default App;
