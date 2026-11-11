import React from 'react';
import {
  UploadCloud,
  ShieldCheck,
  BarChart3,
  Search,
  HelpCircle,
  CheckSquare,
  FileCheck2,
  Sliders,
  FileText
} from 'lucide-react';

export type WorkflowStage =
  | 'data'
  | 'quality'
  | 'overview'
  | 'findings'
  | 'reasons'
  | 'recommendations'
  | 'evidence'
  | 'whatif'
  | 'decisions';

interface StageMeta {
  key: WorkflowStage;
  label: string;
  icon: React.ElementType;
}

export const WORKFLOW_STAGES: StageMeta[] = [
  {
    key: 'data',
    label: 'Data Upload',
    icon: UploadCloud
  },
  {
    key: 'quality',
    label: 'Data Quality',
    icon: ShieldCheck
  },
  {
    key: 'overview',
    label: 'Business Overview',
    icon: BarChart3
  },
  {
    key: 'findings',
    label: 'Findings',
    icon: Search
  },
  {
    key: 'reasons',
    label: 'Possible Reasons',
    icon: HelpCircle
  },
  {
    key: 'recommendations',
    label: 'Recommendations',
    icon: CheckSquare
  },
  {
    key: 'evidence',
    label: 'Evidence',
    icon: FileCheck2
  },
  {
    key: 'whatif',
    label: 'What-If Analysis',
    icon: Sliders
  },
  {
    key: 'decisions',
    label: 'Decision Notes',
    icon: FileText
  }
];

interface Props {
  currentStage: WorkflowStage;
  onSelectStage: (stage: WorkflowStage) => void;
  hasAnalysis: boolean;
}

export const WorkflowStepper: React.FC<Props> = ({
  currentStage,
  onSelectStage,
  hasAnalysis,
}) => {
  return (
    <div className="bg-white border-b border-slate-200 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-1.5 overflow-x-auto py-2.5 scrollbar-none" aria-label="Workflow Navigation">
          {WORKFLOW_STAGES.map((s) => {
            const Icon = s.icon;
            const isActive = currentStage === s.key;
            const isClickable = s.key === 'data' || hasAnalysis;

            return (
              <button
                key={s.key}
                disabled={!isClickable}
                onClick={() => onSelectStage(s.key)}
                className={`group flex items-center gap-2.5 px-3 py-2 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-xs border border-blue-200 ring-1 ring-blue-500/10'
                    : isClickable
                    ? 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    : 'text-slate-400 cursor-not-allowed opacity-50'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : isClickable
                      ? 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                      : 'bg-slate-100 text-slate-400'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="text-left">
                  <div className="leading-tight font-bold">{s.label}</div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};
