import React, { useState, useEffect, useRef } from 'react';
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
import { DataUpload } from './components/stages/DataUpload';
import { DataQuality } from './components/stages/DataQuality';
import { BusinessOverview } from './components/stages/BusinessOverview';
import { Findings } from './components/stages/Findings';
import { PossibleReasons } from './components/stages/PossibleReasons';
import { Recommendations } from './components/stages/Recommendations';
import { Evidence } from './components/stages/Evidence';
import { WhatIfAnalysis } from './components/stages/WhatIfAnalysis';
import { DecisionNotes } from './components/stages/DecisionNotes';
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

const VALID_STAGES: WorkflowStage[] = [
  'data',
  'quality',
  'overview',
  'findings',
  'reasons',
  'recommendations',
  'evidence',
  'whatif',
  'decisions',
];

interface ParsedRoute {
  viewMode: ViewMode;
  stage: WorkflowStage;
  analysisId?: string;
  datasetId?: string;
}

const parseRouteFromLocation = (): ParsedRoute => {
  if (typeof window === 'undefined') {
    return { viewMode: 'home', stage: 'data' };
  }
  const pathname = window.location.pathname.toLowerCase();
  const searchParams = new URLSearchParams(window.location.search);
  const analysisId = searchParams.get('analysisId') || undefined;
  const datasetId = searchParams.get('datasetId') || undefined;

  if (pathname === '/' || pathname === '/home' || pathname === '') {
    return { viewMode: 'home', stage: 'data', analysisId, datasetId };
  }
  if (pathname === '/history' || pathname === '/analyses' || pathname === '/stored-analyses') {
    return { viewMode: 'history', stage: 'data', analysisId, datasetId };
  }
  if (pathname === '/ask-data' || pathname === '/ask_data') {
    return { viewMode: 'ask_data', stage: 'data', analysisId, datasetId };
  }
  if (pathname === '/kpi-goals' || pathname === '/kpi_goals') {
    return { viewMode: 'kpi_goals', stage: 'data', analysisId, datasetId };
  }
  if (pathname === '/explore-details' || pathname === '/explore_details') {
    return { viewMode: 'explore_details', stage: 'data', analysisId, datasetId };
  }

  if (pathname.startsWith('/workspace')) {
    const parts = pathname.split('/').filter(Boolean);
    const stageCandidate = parts[1] as WorkflowStage;
    if (stageCandidate && VALID_STAGES.includes(stageCandidate)) {
      return { viewMode: 'workspace', stage: stageCandidate, analysisId, datasetId };
    }
    return { viewMode: 'workspace', stage: 'data', analysisId, datasetId };
  }

  const directCandidate = pathname.replace(/^\//, '') as WorkflowStage;
  if (VALID_STAGES.includes(directCandidate)) {
    return { viewMode: 'workspace', stage: directCandidate, analysisId, datasetId };
  }

  return { viewMode: 'home', stage: 'data', analysisId, datasetId };
};

const getPathFor = (
  view: ViewMode,
  stage: WorkflowStage,
  analysisId?: string,
  datasetId?: string
): string => {
  let path = '/';
  if (view === 'home') {
    path = '/';
  } else if (view === 'history') {
    path = '/history';
  } else if (view === 'ask_data') {
    path = '/ask-data';
  } else if (view === 'kpi_goals') {
    path = '/kpi-goals';
  } else if (view === 'explore_details') {
    path = '/explore-details';
  } else if (view === 'workspace') {
    path = `/workspace/${stage}`;
  }

  const params = new URLSearchParams();
  if (analysisId) {
    params.set('analysisId', analysisId);
  } else if (datasetId) {
    params.set('datasetId', datasetId);
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
};

export const App: React.FC = () => {
  const [dbDialect, setDbDialect] = useState<string>('database');
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetDetail | null>(null);
  const [targetCol, setTargetCol] = useState<string>('');
  const [dateCol, setDateCol] = useState<string>('');
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisRunResponse | null>(null);

  // Initialize from URL / route
  const [currentStage, setCurrentStage] = useState<WorkflowStage>(() => parseRouteFromLocation().stage);
  const [viewMode, setViewMode] = useState<ViewMode>(() => parseRouteFromLocation().viewMode);

  // Scroll and history tracking
  const mainScrollRef = useRef<HTMLElement | null>(null);
  const homeScrollRef = useRef<HTMLElement | null>(null);
  const hasInternalNavigationRef = useRef<boolean>(false);

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

  // Central Navigation Dispatcher
  const navigateTo = (
    newView: ViewMode,
    newStage: WorkflowStage = 'data',
    replace: boolean = false,
    overrideAnalysisId?: string,
    overrideDatasetId?: string
  ) => {
    hasInternalNavigationRef.current = true;

    if (newView === viewMode && (newView !== 'workspace' || newStage === currentStage)) {
      return;
    }

    const currentDepth = window.history.state?.depth ?? 0;
    const nextDepth = replace ? currentDepth : currentDepth + 1;
    const stateObj = {
      appNav: true,
      viewMode: newView,
      currentStage: newStage,
      depth: nextDepth,
    };

    const targetUrl = getPathFor(
      newView,
      newStage,
      overrideAnalysisId !== undefined ? overrideAnalysisId : activeAnalysis?.id,
      overrideDatasetId !== undefined ? overrideDatasetId : selectedDataset?.id
    );

    if (replace) {
      window.history.replaceState(stateObj, '', targetUrl);
    } else {
      window.history.pushState(stateObj, '', targetUrl);
    }

    setViewMode(newView);
    setCurrentStage(newStage);
  };

  // Back Navigation Handler for In-App Back links
  const handleBackToWorkspace = () => {
    if (hasInternalNavigationRef.current && (window.history.state?.depth ?? 0) > 0) {
      window.history.back();
    } else {
      // Sensible default fallback for fresh sessions or deep links
      if (activeAnalysis) {
        navigateTo('workspace', 'overview');
      } else {
        navigateTo('workspace', 'data');
      }
    }
  };

  // 1. History initialization on mount & browser popstate listener
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const initialRoute = parseRouteFromLocation();
    const currentState = window.history.state;
    if (!currentState || !currentState.appNav) {
      if (initialRoute.viewMode === 'home') {
        window.history.replaceState(
          { appNav: true, viewMode: 'home', currentStage: 'data', depth: 0 },
          '',
          '/'
        );
      } else {
        // Deep-link direct entry:
        // Set entry 0 to Home so that pressing browser Back lands on Home rather than exiting the application
        window.history.replaceState(
          { appNav: true, viewMode: 'home', currentStage: 'data', depth: 0 },
          '',
          '/'
        );
        window.history.pushState(
          {
            appNav: true,
            viewMode: initialRoute.viewMode,
            currentStage: initialRoute.stage,
            depth: 1,
          },
          '',
          window.location.pathname + window.location.search
        );
      }
    }

    const handlePopState = (event: PopStateEvent) => {
      const state = event.state;
      if (state && state.appNav) {
        setViewMode(state.viewMode);
        setCurrentStage(state.currentStage || 'data');
      } else {
        const parsed = parseRouteFromLocation();
        setViewMode(parsed.viewMode);
        setCurrentStage(parsed.stage);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // 2. Scroll reset on navigation (strictly on viewMode or currentStage changes)
  useEffect(() => {
    if (mainScrollRef.current) {
      mainScrollRef.current.scrollTop = 0;
    }
    if (homeScrollRef.current) {
      homeScrollRef.current.scrollTop = 0;
    }
    window.scrollTo(0, 0);
    if (document.documentElement) {
      document.documentElement.scrollTop = 0;
    }
    if (document.body) {
      document.body.scrollTop = 0;
    }
  }, [viewMode, currentStage]);

  // 3. Initial Load: check health and load datasets / deep link analysis
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

      const parsed = parseRouteFromLocation();
      if (parsed.analysisId) {
        try {
          const loadedAnalysis = await api.getAnalysis(parsed.analysisId);
          setActiveAnalysis(loadedAnalysis);
          if (loadedAnalysis.dataset_id) {
            const dsDetail = await api.getDataset(loadedAnalysis.dataset_id).catch(() => null);
            if (dsDetail) {
              setSelectedDataset(dsDetail);
              setTargetCol(loadedAnalysis.target_column || dsDetail.schema_metadata.suggested_target || '');
              setDateCol(loadedAnalysis.date_column || dsDetail.schema_metadata.suggested_date || '');
            }
          }
          if (parsed.viewMode === 'workspace' && parsed.stage) {
            setCurrentStage(parsed.stage);
          } else if (parsed.viewMode) {
            setViewMode(parsed.viewMode);
          }
          return;
        } catch (err) {
          console.warn('Failed to load deep link analysis:', err);
        }
      }

      const targetDatasetId = parsed.datasetId || (dsList.length > 0 ? dsList[0].id : null);
      if (targetDatasetId) {
        await loadDatasetDetail(targetDatasetId, false);
      }

      // If deep link requested an analysis stage but no analysis is active, fall back gracefully to 'data'
      if (parsed.viewMode === 'workspace' && parsed.stage !== 'data') {
        setCurrentStage('data');
        window.history.replaceState(
          { appNav: true, viewMode: 'workspace', currentStage: 'data', depth: 0 },
          '',
          '/workspace/data'
        );
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
        navigateTo('workspace', 'data', false, undefined, detail.id);
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
      // Workflow: Data Upload -> Data Quality (Stage 1)
      navigateTo('workspace', 'quality', false, res.id, selectedDataset.id);
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
    navigateTo('explore_details');
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
      navigateTo('workspace', 'overview', false, analysisData.id, analysisData.dataset_id);
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
        onOpenStoredAnalyses={() => navigateTo('history')}
        onGoHome={() => navigateTo('home')}
        currentView={viewMode}
      />

      {/* Primary Layout Router: Home (full width, no sidebar) vs Workspace/Tools/History (with sidebar) */}
      {viewMode === 'home' ? (
        <main ref={homeScrollRef} className="flex-1 min-h-0 overflow-y-auto w-full">
          <HomePage
            onOpenUploadModal={() => setIsUploadingModalOpen(true)}
            onSeedSamples={handleSeedSamples}
            isSeeding={isSeeding}
            onSelectAnalysis={handleSelectStoredAnalysis}
            onOpenStoredAnalyses={() => navigateTo('history')}
          />
        </main>
      ) : (
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Left Persistent Workspace Sidebar (Visible on Stored Analyses, Workspace stages, and Interactive tools) */}
          <WorkspaceSidebar
            currentStage={currentStage}
            onSelectStage={(stage) => {
              navigateTo('workspace', stage);
            }}
            hasAnalysis={activeAnalysis !== null}
            activeView={viewMode}
            onSelectTool={(tool) => navigateTo(tool)}
            onOpenStoredAnalyses={() => navigateTo('history')}
            onGoHome={() => navigateTo('home')}
            onOpenUploadModal={() => setIsUploadingModalOpen(true)}
            onSeedSamples={handleSeedSamples}
            isSeeding={isSeeding}
          />

          {/* Main Stage / Tool Content Area */}
          <main
            ref={mainScrollRef}
            className="flex-1 min-w-0 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 max-w-7xl mx-auto w-full"
          >
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

            {/* Compact Workspace Context Bar (Visually secondary, contextual to workspace & tools) */}
            {selectedDataset && viewMode !== 'history' && (
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

            {/* Stored Analyses Page */}
            {viewMode === 'history' && (
              <StoredAnalysesPage
                onSelectAnalysis={handleSelectStoredAnalysis}
                onBackToWorkspace={handleBackToWorkspace}
              />
            )}

            {/* Dedicated Interactive Tool Pages */}
            {viewMode === 'ask_data' && (
              <AskYourDataPage
                datasetId={selectedDataset?.id}
                datasetName={selectedDataset?.name}
                onBackToWorkspace={handleBackToWorkspace}
              />
            )}

            {viewMode === 'kpi_goals' && (
              <KpiGoalsPage
                analysisId={activeAnalysis?.id}
                datasetId={selectedDataset?.id}
                datasetName={selectedDataset?.name}
                onBackToWorkspace={handleBackToWorkspace}
              />
            )}

            {viewMode === 'explore_details' && (
              <ExploreDetailsPage
                analysisId={activeAnalysis?.id}
                datasetName={selectedDataset?.name}
                targetMetric={activeAnalysis?.target_column || targetCol}
                availableDimensions={selectedDataset?.schema_metadata.categorical_candidates || []}
                initialDimension={drillModal.initialDimension}
                onBackToWorkspace={handleBackToWorkspace}
              />
            )}

            {/* Standard 9-Stage Analysis Workflow */}
            {viewMode === 'workspace' && (
              <>
                {/* 1. Data Upload */}
                {currentStage === 'data' && (
                  <DataUpload
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
                  <DataQuality
                    report={activeAnalysis.data_quality}
                    onNavigateNext={() => navigateTo('workspace', 'overview')}
                  />
                )}

                {/* 3. Business Overview ("What is happening?") */}
                {currentStage === 'overview' && activeAnalysis && (
                  <BusinessOverview
                    health={activeAnalysis.business_health}
                    onNavigateNext={() => navigateTo('workspace', 'findings')}
                    analysisId={activeAnalysis.id}
                    datasetId={selectedDataset?.id}
                    findings={activeAnalysis.diagnostics?.findings || []}
                    onOpenWhyResult={handleOpenWhyResult}
                    onOpenDrillDown={handleOpenDrillDown}
                  />
                )}

                {/* 4. Findings ("What needs attention?") */}
                {currentStage === 'findings' && activeAnalysis && (
                  <Findings
                    diagnostic={activeAnalysis.diagnostics}
                    analysisId={activeAnalysis.id}
                    onNavigateNext={() => navigateTo('workspace', 'reasons')}
                    onOpenDrillDown={handleOpenDrillDown}
                  />
                )}

                {/* 5. Possible Reasons ("Why might it be happening?") */}
                {currentStage === 'reasons' && activeAnalysis && (
                  <PossibleReasons
                    rootCause={activeAnalysis.root_cause}
                    onNavigateNext={() => navigateTo('workspace', 'recommendations')}
                  />
                )}

                {/* 6. Recommendations ("What could we do?") */}
                {currentStage === 'recommendations' && activeAnalysis && (
                  <Recommendations
                    recommendations={activeAnalysis.recommendations}
                    decisions={activeAnalysis.decisions}
                    onOpenDecisionModal={handleOpenDecisionModal}
                    onNavigateNext={() => navigateTo('workspace', 'evidence')}
                    analysisId={activeAnalysis.id}
                    onOpenWhyResult={handleOpenWhyResult}
                  />
                )}

                {/* 7. Evidence ("How do we know?") */}
                {currentStage === 'evidence' && activeAnalysis && (
                  <Evidence
                    chains={activeAnalysis.evidence_chains}
                    onSelectRecommendation={() => {
                      navigateTo('workspace', 'recommendations');
                    }}
                    onNavigateNext={() => navigateTo('workspace', 'whatif')}
                  />
                )}

                {/* 8. What-If Analysis ("What happens if we change something?") */}
                {currentStage === 'whatif' && activeAnalysis && (
                  <WhatIfAnalysis
                    analysis={activeAnalysis}
                    onNavigateNext={() => navigateTo('workspace', 'decisions')}
                  />
                )}

                {/* 9. Decision Notes */}
                {currentStage === 'decisions' && activeAnalysis && (
                  <DecisionNotes
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
          navigateTo('workspace', 'data', false, undefined, ds.id);
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
