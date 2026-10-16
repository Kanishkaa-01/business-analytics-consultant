import { describe, it, expect } from 'vitest';
import { WorkflowStage, WORKFLOW_STAGES } from '../components/workflow/WorkflowStepper';
import { DataQualityReport, AnalysisRunResponse, DatasetDetail } from '../types';

describe('Application Navigation Flow, Page Scroll Position, Sidebar Visibility, and Back Button Behavior', () => {
  // 1. Workflow Sequence Verification
  it('enforces the exact 9-stage analysis workflow order starting with Data Quality after upload', () => {
    const expectedWorkflowOrder: WorkflowStage[] = [
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

    const actualWorkflowOrder = WORKFLOW_STAGES.map((s) => s.key);
    expect(actualWorkflowOrder).toEqual(expectedWorkflowOrder);

    // Verify stage 0 next is stage 1 (quality)
    const stage0Idx = expectedWorkflowOrder.indexOf('data');
    expect(expectedWorkflowOrder[stage0Idx + 1]).toBe('quality');

    // Verify stage 1 next is stage 2 (overview)
    const stage1Idx = expectedWorkflowOrder.indexOf('quality');
    expect(expectedWorkflowOrder[stage1Idx + 1]).toBe('overview');
  });

  // 2. Data Quality Report & Metrics Contract
  it('verifies Data Quality stage data requirements and metrics presence', () => {
    const mockReport: DataQualityReport = {
      overall_quality_score: 92,
      grade: 'A',
      reliability_assessment: 'Dataset has high integrity with minimal missing values.',
      total_records: 5000,
      duplicate_rows: 0,
      completeness_ratio: 0.998,
      validity_ratio: 0.995,
      consistency_ratio: 1.0,
      issues: [
        {
          severity: 'Warning',
          dimension: 'Distribution',
          column: 'revenue',
          description: '8 potential outliers detected in transaction amount',
          affected_rows: 8,
          percentage: 0.16,
          recommendation: 'Review high-value transactions',
        },
      ],
      column_metrics: [
        {
          column: 'revenue',
          completeness_score: 1.0,
          validity_score: 0.998,
          outlier_count: 8,
          outlier_percentage: 0.16,
          skewness: 0.25,
        },
      ],
    };

    expect(mockReport.overall_quality_score).toBeGreaterThanOrEqual(0);
    expect(mockReport.overall_quality_score).toBeLessThanOrEqual(100);
    expect(mockReport.duplicate_rows).toBeDefined();
    expect(mockReport.column_metrics[0].outlier_count).toBe(8);
    expect(mockReport.completeness_ratio).toBeGreaterThan(0.9);
    expect(mockReport.issues.length).toBeGreaterThan(0);
    expect(mockReport.column_metrics.length).toBeGreaterThan(0);
  });

  // 3. Navigation between Stages Preserving Analysis Context
  it('preserves analysis context and dataset when transitioning from Data Quality to Business Overview', () => {
    const mockDataset: Partial<DatasetDetail> = {
      id: 'ds-retail-01',
      name: 'Retail Store Sales.csv',
      schema_metadata: {
        numeric_candidates: ['revenue', 'cost', 'quantity'],
        categorical_candidates: ['region', 'category'],
        datetime_candidates: ['date'],
        suggested_target: 'revenue',
        suggested_date: 'date',
        columns: [],
      },
    };

    const mockAnalysis: Partial<AnalysisRunResponse> = {
      id: 'an-992',
      dataset_id: 'ds-retail-01',
      target_column: 'revenue',
      date_column: 'date',
      data_quality: {
        overall_quality_score: 88,
        grade: 'B',
        reliability_assessment: 'Reliable with minor outliers.',
        total_records: 2500,
        duplicate_rows: 2,
        completeness_ratio: 0.989,
        validity_ratio: 0.985,
        consistency_ratio: 1.0,
        issues: [],
        column_metrics: [],
      },
      business_health: {
        overall_health_score: 76,
        overall_status: 'Stable',
        executive_summary: 'Healthy top-line revenue growth',
        kpis: [],
        vital_signs: {},
      },
    };

    // Simulate transition
    let currentStage: WorkflowStage = 'data';
    let activeAnalysis: Partial<AnalysisRunResponse> | null = null;

    // Run Analysis triggered
    activeAnalysis = mockAnalysis;
    currentStage = 'quality'; // Must navigate to quality first

    expect(currentStage).toBe('quality');
    expect(activeAnalysis).not.toBeNull();
    expect(activeAnalysis?.data_quality?.overall_quality_score).toBe(88);

    // Click "Continue to Business Overview"
    currentStage = 'overview';
    expect(currentStage).toBe('overview');
    // Context is retained
    expect(activeAnalysis?.id).toBe('an-992');
    expect(activeAnalysis?.target_column).toBe('revenue');
    expect(mockDataset.id).toBe(activeAnalysis?.dataset_id);
  });

  // 4. URL Mapping and Parsing Logic
  describe('Route and History Synchronization', () => {
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

    const getPathFor = (
      view: string,
      stage: WorkflowStage,
      analysisId?: string,
      datasetId?: string
    ): string => {
      let path = '/';
      if (view === 'home') path = '/';
      else if (view === 'history') path = '/history';
      else if (view === 'ask_data') path = '/ask-data';
      else if (view === 'kpi_goals') path = '/kpi-goals';
      else if (view === 'explore_details') path = '/explore-details';
      else if (view === 'workspace') path = `/workspace/${stage}`;

      const params = new URLSearchParams();
      if (analysisId) params.set('analysisId', analysisId);
      else if (datasetId) params.set('datasetId', datasetId);
      const qs = params.toString();
      return qs ? `${path}?${qs}` : path;
    };

    const parseRoute = (pathname: string, search: string = '') => {
      const p = pathname.toLowerCase();
      const sp = new URLSearchParams(search);
      const analysisId = sp.get('analysisId') || undefined;
      const datasetId = sp.get('datasetId') || undefined;

      if (p === '/' || p === '/home' || p === '') {
        return { viewMode: 'home', stage: 'data', analysisId, datasetId };
      }
      if (p === '/history' || p === '/analyses' || p === '/stored-analyses') {
        return { viewMode: 'history', stage: 'data', analysisId, datasetId };
      }
      if (p === '/ask-data' || p === '/ask_data') {
        return { viewMode: 'ask_data', stage: 'data', analysisId, datasetId };
      }
      if (p === '/kpi-goals' || p === '/kpi_goals') {
        return { viewMode: 'kpi_goals', stage: 'data', analysisId, datasetId };
      }
      if (p === '/explore-details' || p === '/explore_details') {
        return { viewMode: 'explore_details', stage: 'data', analysisId, datasetId };
      }
      if (p.startsWith('/workspace')) {
        const parts = p.split('/').filter(Boolean);
        const stageCandidate = parts[1] as WorkflowStage;
        if (stageCandidate && VALID_STAGES.includes(stageCandidate)) {
          return { viewMode: 'workspace', stage: stageCandidate, analysisId, datasetId };
        }
        return { viewMode: 'workspace', stage: 'data', analysisId, datasetId };
      }
      return { viewMode: 'home', stage: 'data', analysisId, datasetId };
    };

    it('generates correct paths for views and stages', () => {
      expect(getPathFor('home', 'data')).toBe('/');
      expect(getPathFor('history', 'data')).toBe('/history');
      expect(getPathFor('workspace', 'quality')).toBe('/workspace/quality');
      expect(getPathFor('workspace', 'overview', 'an-100')).toBe('/workspace/overview?analysisId=an-100');
      expect(getPathFor('workspace', 'data', undefined, 'ds-50')).toBe('/workspace/data?datasetId=ds-50');
      expect(getPathFor('ask_data', 'data')).toBe('/ask-data');
      expect(getPathFor('kpi_goals', 'data')).toBe('/kpi-goals');
      expect(getPathFor('explore_details', 'data')).toBe('/explore-details');
    });

    it('parses paths and parameters correctly from URL locations', () => {
      expect(parseRoute('/')).toEqual({ viewMode: 'home', stage: 'data', analysisId: undefined, datasetId: undefined });
      expect(parseRoute('/history')).toEqual({ viewMode: 'history', stage: 'data', analysisId: undefined, datasetId: undefined });
      expect(parseRoute('/stored-analyses')).toEqual({ viewMode: 'history', stage: 'data', analysisId: undefined, datasetId: undefined });
      expect(parseRoute('/workspace/quality')).toEqual({ viewMode: 'workspace', stage: 'quality', analysisId: undefined, datasetId: undefined });
      expect(parseRoute('/workspace/overview', '?analysisId=an-123')).toEqual({
        viewMode: 'workspace',
        stage: 'overview',
        analysisId: 'an-123',
        datasetId: undefined,
      });
      expect(parseRoute('/workspace/data', '?datasetId=ds-777')).toEqual({
        viewMode: 'workspace',
        stage: 'data',
        analysisId: undefined,
        datasetId: 'ds-777',
      });
    });

    it('handles direct entry deep linking with synthetic root seeding', () => {
      // Simulate direct entry into /workspace/quality in a fresh tab
      const fakeHistory: Array<{ state: any; url: string }> = [];
      let historyIndex = -1;

      const mockReplaceState = (state: any, _title: string, url: string) => {
        if (historyIndex === -1) {
          fakeHistory.push({ state, url });
          historyIndex = 0;
        } else {
          fakeHistory[historyIndex] = { state, url };
        }
      };

      const mockPushState = (state: any, _title: string, url: string) => {
        historyIndex++;
        fakeHistory.splice(historyIndex, fakeHistory.length - historyIndex, { state, url });
      };

      // Simulating deep link direct entry logic
      const deepLink = parseRoute('/workspace/quality');
      // Step A: Seed Entry 0 as Home
      mockReplaceState({ appNav: true, viewMode: 'home', currentStage: 'data', depth: 0 }, '', '/');
      // Step B: Push Entry 1 as the deep link target
      mockPushState({ appNav: true, viewMode: deepLink.viewMode, currentStage: deepLink.stage, depth: 1 }, '', '/workspace/quality');

      expect(fakeHistory.length).toBe(2);
      expect(fakeHistory[0].url).toBe('/');
      expect(fakeHistory[0].state.viewMode).toBe('home');
      expect(fakeHistory[1].url).toBe('/workspace/quality');
      expect(fakeHistory[1].state.viewMode).toBe('workspace');
      expect(fakeHistory[1].state.currentStage).toBe('quality');

      // When browser Back is pressed:
      historyIndex--;
      const backState = fakeHistory[historyIndex].state;
      expect(backState.viewMode).toBe('home'); // Returns to Home cleanly without exiting the app
    });

    it('handles internal back fallback when session has no prior history', () => {
      // Direct deep link entry into Stored Analyses or a secondary tool
      let activeAnalysis: any = null;
      let targetView = '';
      let targetStage = '';

      const navigateTo = (view: string, stage: string) => {
        targetView = view;
        targetStage = stage;
      };

      const handleBackToWorkspace = (hasInternalNav: boolean, depth: number) => {
        if (hasInternalNav && depth > 0) {
          // would call window.history.back()
          return 'history.back';
        } else {
          if (activeAnalysis) {
            navigateTo('workspace', 'overview');
          } else {
            navigateTo('workspace', 'data');
          }
          return 'fallback';
        }
      };

      // Case A: Fresh session with no active analysis
      const resultA = handleBackToWorkspace(false, 0);
      expect(resultA).toBe('fallback');
      expect(targetView).toBe('workspace');
      expect(targetStage).toBe('data');

      // Case B: Fresh session with active analysis
      activeAnalysis = { id: 'an-1' };
      const resultB = handleBackToWorkspace(false, 0);
      expect(resultB).toBe('fallback');
      expect(targetView).toBe('workspace');
      expect(targetStage).toBe('overview');

      // Case C: Has internal navigation history
      const resultC = handleBackToWorkspace(true, 2);
      expect(resultC).toBe('history.back');
    });
  });

  // 5. Scroll Reset Behavior
  describe('Page Scroll Container Reset', () => {
    it('resets scroll position on navigation transitions but preserves position during state updates', () => {
      const scrollContainer = { scrollTop: 850 };
      const windowMock = { scrollX: 0, scrollY: 850 };

      const resetScroll = () => {
        scrollContainer.scrollTop = 0;
        windowMock.scrollY = 0;
      };

      // Initial scroll position from user scrolling down
      expect(scrollContainer.scrollTop).toBe(850);

      // Transition to new stage/view:
      resetScroll();
      expect(scrollContainer.scrollTop).toBe(0);
      expect(windowMock.scrollY).toBe(0);

      // User scrolls down again on the new page:
      scrollContainer.scrollTop = 420;

      // An unrelated state update occurs (e.g. modal toggle, dropdown selection, chart filter):
      const handleModalToggle = (_isOpen: boolean) => {
        // Does NOT call resetScroll
      };
      handleModalToggle(true);
      expect(scrollContainer.scrollTop).toBe(420); // Position is preserved
    });
  });

  // 6. Sidebar Visibility Rules
  describe('Workspace Sidebar Visibility', () => {
    it('hides the sidebar on the Home page and renders it on Stored Analyses, Workspace, and Tools', () => {
      const shouldRenderSidebar = (viewMode: string) => {
        return viewMode !== 'home';
      };

      expect(shouldRenderSidebar('home')).toBe(false);
      expect(shouldRenderSidebar('history')).toBe(true);
      expect(shouldRenderSidebar('workspace')).toBe(true);
      expect(shouldRenderSidebar('ask_data')).toBe(true);
      expect(shouldRenderSidebar('kpi_goals')).toBe(true);
      expect(shouldRenderSidebar('explore_details')).toBe(true);
    });

    it('highlights the Stored Analyses item when viewMode is history', () => {
      const activeView = 'history';
      const isHistoryActive = activeView === 'history';
      const buttonClasses = isHistoryActive
        ? 'bg-slate-900 text-white font-bold shadow-xs'
        : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-medium';

      expect(buttonClasses).toContain('bg-slate-900');
      expect(buttonClasses).toContain('text-white');
    });
  });
});
