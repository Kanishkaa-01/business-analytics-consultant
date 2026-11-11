import React, { useState } from 'react';
import {
  UploadCloud,
  ChevronLeft,
  ChevronRight,
  MessageSquareText,
  Layers,
  Target,
  History,
  Home,
  Sparkles,
} from 'lucide-react';
import { WorkflowStage, WORKFLOW_STAGES } from './WorkflowStepper';

export type ActiveWorkspaceView =
  | 'workspace'
  | 'ask_data'
  | 'explore_details'
  | 'kpi_goals'
  | 'history'
  | 'home';

interface Props {
  currentStage: WorkflowStage;
  onSelectStage: (stage: WorkflowStage) => void;
  hasAnalysis: boolean;
  activeView?: ActiveWorkspaceView;
  onSelectTool?: (tool: 'ask_data' | 'explore_details' | 'kpi_goals') => void;
  onOpenStoredAnalyses?: () => void;
  onGoHome?: () => void;
  onOpenUploadModal?: () => void;
  onSeedSamples?: () => void;
  isSeeding?: boolean;
}

export const WorkspaceSidebar: React.FC<Props> = ({
  currentStage,
  onSelectStage,
  hasAnalysis,
  activeView = 'workspace',
  onSelectTool,
  onOpenStoredAnalyses,
  onGoHome,
  onOpenUploadModal,
  onSeedSamples,
  isSeeding = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  return (
    <aside
      className={`h-full overflow-hidden bg-white border-r border-slate-200 transition-all duration-200 flex flex-col shrink-0 select-none ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Sidebar Header & Collapse Toggle */}
      <div className="p-3 border-b border-slate-100 flex items-center justify-between">
        {!isCollapsed && (
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-2">
            Workspace
          </span>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer ${
            isCollapsed ? 'mx-auto' : ''
          }`}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-3 space-y-5">
        {/* SECTION 1: HOME */}
        <div className="px-2">
          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              HOME
            </div>
          )}
          <button
            onClick={onGoHome}
            title={isCollapsed ? 'Home' : undefined}
            className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
              isCollapsed ? 'p-2.5 justify-center' : 'p-2.5'
            } ${
              activeView === 'home'
                ? 'bg-blue-600 text-white font-bold shadow-xs'
                : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-medium'
            }`}
          >
            <Home
              className={`shrink-0 ${isCollapsed ? 'w-5 h-5' : 'w-4 h-4'} ${
                activeView === 'home' ? 'text-white' : 'text-slate-500'
              }`}
            />
            {!isCollapsed && (
              <div className="text-xs font-semibold leading-tight">
                Home
              </div>
            )}
          </button>
        </div>

        {/* SECTION 2: ANALYSIS */}
        <div className="px-2 space-y-1 border-t border-slate-100 pt-3">
          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              ANALYSIS
            </div>
          )}

          <nav className="space-y-0.5">
            {WORKFLOW_STAGES.map((stage) => {
              const Icon = stage.icon;
              const isActive = activeView === 'workspace' && currentStage === stage.key;
              const isDisabled = stage.key !== 'data' && !hasAnalysis;

              return (
                <button
                  key={stage.key}
                  onClick={() => !isDisabled && onSelectStage(stage.key)}
                  disabled={isDisabled}
                  title={isCollapsed ? stage.label : undefined}
                  className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
                    isCollapsed ? 'p-2.5 justify-center' : 'p-2'
                  } ${
                    isActive
                      ? 'bg-blue-600 text-white font-bold shadow-xs'
                      : isDisabled
                      ? 'opacity-35 cursor-not-allowed text-slate-400'
                      : 'text-slate-700 hover:bg-slate-100/80 hover:text-slate-900 font-medium'
                  }`}
                >
                  <Icon
                    className={`shrink-0 ${
                      isCollapsed ? 'w-5 h-5' : 'w-4 h-4'
                    } ${isActive ? 'text-white' : 'text-slate-500'}`}
                  />

                  {!isCollapsed && (
                    <div className="min-w-0 flex-1">
                      <div className="text-xs leading-tight truncate">
                        {stage.label}
                      </div>
                      <div
                        className={`text-[10px] leading-tight truncate mt-0.5 ${
                          isActive ? 'text-blue-100' : 'text-slate-400'
                        }`}
                      >
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* SECTION 3: INTERACTIVE TOOLS */}
        <div className="px-2 space-y-1 border-t border-slate-100 pt-3">
          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              INTERACTIVE TOOLS
            </div>
          )}

          <nav className="space-y-0.5">
            {/* Ask Your Data */}
            <button
              onClick={() => {
                if (hasAnalysis) {
                  onSelectTool?.('ask_data');
                }
              }}
              disabled={!hasAnalysis}
              title={isCollapsed ? 'Ask Your Data' : undefined}
              className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
                isCollapsed ? 'p-2.5 justify-center' : 'p-2'
              } ${
                activeView === 'ask_data'
                  ? 'bg-indigo-600 text-white font-bold shadow-xs'
                  : !hasAnalysis
                  ? 'opacity-35 cursor-not-allowed text-slate-400'
                  : 'text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 font-medium'
              }`}
            >
              <MessageSquareText
                className={`w-4 h-4 shrink-0 ${
                  activeView === 'ask_data' ? 'text-white' : 'text-indigo-600'
                }`}
              />
              {!isCollapsed && (
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold leading-tight">
                    Ask Your Data
                  </div>
                </div>
              )}
            </button>

            {/* Explore Details */}
            <button
              onClick={() => {
                if (hasAnalysis) {
                  onSelectTool?.('explore_details');
                }
              }}
              disabled={!hasAnalysis}
              title={isCollapsed ? 'Explore Details' : undefined}
              className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
                isCollapsed ? 'p-2.5 justify-center' : 'p-2'
              } ${
                activeView === 'explore_details'
                  ? 'bg-purple-600 text-white font-bold shadow-xs'
                  : !hasAnalysis
                  ? 'opacity-35 cursor-not-allowed text-slate-400'
                  : 'text-slate-700 hover:bg-purple-50 hover:text-purple-700 font-medium'
              }`}
            >
              <Layers
                className={`w-4 h-4 shrink-0 ${
                  activeView === 'explore_details' ? 'text-white' : 'text-purple-600'
                }`}
              />
              {!isCollapsed && (
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold leading-tight">
                    Explore Details
                  </div>
                </div>
              )}
            </button>

            {/* KPI Goals */}
            <button
              onClick={() => {
                if (hasAnalysis) {
                  onSelectTool?.('kpi_goals');
                }
              }}
              disabled={!hasAnalysis}
              title={isCollapsed ? 'KPI Goals & Target Tracking' : undefined}
              className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
                isCollapsed ? 'p-2.5 justify-center' : 'p-2'
              } ${
                activeView === 'kpi_goals'
                  ? 'bg-emerald-600 text-white font-bold shadow-xs'
                  : !hasAnalysis
                  ? 'opacity-35 cursor-not-allowed text-slate-400'
                  : 'text-slate-700 hover:bg-emerald-50 hover:text-emerald-700 font-medium'
              }`}
            >
              <Target
                className={`w-4 h-4 shrink-0 ${
                  activeView === 'kpi_goals' ? 'text-white' : 'text-emerald-600'
                }`}
              />
              {!isCollapsed && (
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold leading-tight">
                    KPI Goals
                  </div>
                </div>
              )}
            </button>
          </nav>
        </div>

        {/* SECTION 4: WORKSPACE */}
        <div className="px-2 space-y-1 border-t border-slate-100 pt-3">
          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              WORKSPACE
            </div>
          )}

          <nav className="space-y-0.5">
            <button
              onClick={onOpenStoredAnalyses}
              title={isCollapsed ? 'Stored Analyses' : undefined}
              className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer ${
                isCollapsed ? 'p-2.5 justify-center' : 'p-2'
              } ${
                activeView === 'history'
                  ? 'bg-slate-900 text-white font-bold shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-medium'
              }`}
            >
              <History
                className={`w-4 h-4 shrink-0 ${
                  activeView === 'history' ? 'text-white' : 'text-slate-500'
                }`}
              />
              {!isCollapsed && (
                <div className="text-xs font-semibold leading-tight">
                  Stored Analyses
                </div>
              )}
            </button>
          </nav>
        </div>

        {/* SECTION 5: ACTIONS */}
        <div className="px-2 space-y-1 border-t border-slate-100 pt-3">
          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              ACTIONS
            </div>
          )}

          <nav className="space-y-0.5">
            {/* Upload Dataset */}
            {onOpenUploadModal && (
              <button
                onClick={onOpenUploadModal}
                title={isCollapsed ? 'Upload Dataset' : undefined}
                className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer text-slate-700 hover:bg-blue-50 hover:text-blue-700 font-medium ${
                  isCollapsed ? 'p-2.5 justify-center' : 'p-2'
                }`}
              >
                <UploadCloud className="w-4 h-4 text-blue-600 shrink-0" />
                {!isCollapsed && (
                  <div className="text-xs font-semibold leading-tight">
                    Upload Dataset
                  </div>
                )}
              </button>
            )}

            {/* Load Sample Data */}
            {onSeedSamples && (
              <button
                onClick={onSeedSamples}
                disabled={isSeeding}
                title={isCollapsed ? 'Load Sample Data' : undefined}
                className={`w-full text-left rounded-xl transition-all flex items-center gap-3 cursor-pointer text-slate-700 hover:bg-amber-50 hover:text-amber-700 font-medium disabled:opacity-50 ${
                  isCollapsed ? 'p-2.5 justify-center' : 'p-2'
                }`}
              >
                <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
                {!isCollapsed && (
                  <div className="text-xs font-semibold leading-tight">
                    {isSeeding ? 'Loading Samples...' : 'Load Sample Data'}
                  </div>
                )}
              </button>
            )}

          </nav>
        </div>
      </div>
    </aside>
  );
};
