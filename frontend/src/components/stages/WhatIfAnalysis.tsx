import React, { useState, useEffect } from 'react';
import {
  Sliders,
  DollarSign,
  TrendingUp,
  Percent,
  RotateCcw,
  Save,
  ArrowRight,
  Lightbulb,
  Trash2,
  Scale,
  Edit3,
  PlusCircle,
  AlertCircle,
  CheckCircle2,
  X,
  FileText
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import {
  AnalysisRunResponse,
  SimulationOutcome,
  ScenarioComparisonReport,
} from '../../types';
import { api } from '../../services/api';
import { SimulationChart } from '../charts/SimulationChart';
import { ForecastVsActual } from '../analysis/ForecastVsActual';
import { buildComparisonChartOption } from '../../utils/scenarioChartOptions';

interface Props {
  analysis: AnalysisRunResponse;
  onNavigateNext: () => void;
}

export const WhatIfAnalysis: React.FC<Props> = ({ analysis, onNavigateNext }) => {
  // 4 Core Levers (Live Exploratory Sliders)
  const [priceChange, setPriceChange] = useState<number>(0);
  const [discountAdjust, setDiscountAdjust] = useState<number>(0);
  const [churnMitigation, setChurnMitigation] = useState<number>(0);
  const [opsEfficiency, setOpsEfficiency] = useState<number>(0);

  const [simulationOutcome, setSimulationOutcome] = useState<SimulationOutcome | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // Dedicated Create / Edit Scenario Form State
  const [formName, setFormName] = useState<string>('');
  const [formInterventionType, setFormInterventionType] = useState<string>('Price Change');
  const [formChangeValue, setFormChangeValue] = useState<number | string>(5.0);
  const [formParameterType, setFormParameterType] = useState<'percentage' | 'percentage_points'>('percentage');
  const [formNotes, setFormNotes] = useState<string>('');
  const [editingScenarioId, setEditingScenarioId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [isSubmittingForm, setIsSubmittingForm] = useState<boolean>(false);

  const [savedScenarios, setSavedScenarios] = useState<any[]>([]);
  const [comparisonReport, setComparisonReport] = useState<ScenarioComparisonReport | null>(null);
  const [isLoadingComparison, setIsLoadingComparison] = useState<boolean>(false);

  const triggerSimulation = async (
    pChange: number,
    dAdjust: number,
    cMit: number,
    oEff: number
  ) => {
    setIsSimulating(true);
    try {
      const outcome = await api.runSimulation({
        analysis_id: analysis.id,
        price_change_pct: pChange,
        discount_adjustment_pct: dAdjust,
        churn_mitigation_pct: cMit,
        operational_efficiency_pct: oEff,
      });
      setSimulationOutcome(outcome);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  const loadScenariosAndComparison = async () => {
    setIsLoadingComparison(true);
    try {
      const [scList, comp] = await Promise.all([
        api.listSavedScenarios(analysis.id).catch(() => []),
        api.compareScenarios(analysis.id).catch(() => null),
      ]);
      setSavedScenarios(scList);
      setComparisonReport(comp);
    } catch (e) {
      console.error('Failed to load scenarios or comparison:', e);
    } finally {
      setIsLoadingComparison(false);
    }
  };

  useEffect(() => {
    triggerSimulation(priceChange, discountAdjust, churnMitigation, opsEfficiency);
  }, [priceChange, discountAdjust, churnMitigation, opsEfficiency]);

  useEffect(() => {
    loadScenariosAndComparison();
  }, [analysis.id]);

  const handleResetLevers = () => {
    setPriceChange(0);
    setDiscountAdjust(0);
    setChurnMitigation(0);
    setOpsEfficiency(0);
  };

  const sensitivity = simulationOutcome?.sensitivity_breakdown || {};
  const hasDiscount = simulationOutcome?.supported_interventions
    ? simulationOutcome.supported_interventions.includes('Discount Change')
    : 'discount_recapture_per_pct' in sensitivity;
  const hasRetention = 'churn_mitigation_per_pct' in sensitivity;
  const hasCost = simulationOutcome?.supported_interventions
    ? simulationOutcome.supported_interventions.includes('Operating Cost Reduction')
    : 'operational_efficiency_per_pct' in sensitivity;

  const validateForm = (): string | null => {
    if (!formName.trim()) {
      return 'Scenario name is required.';
    }
    const val = Number(formChangeValue);
    if (isNaN(val) || formChangeValue === '') {
      return 'Change parameter must be a valid number.';
    }

    if (formInterventionType === 'Price Change') {
      if (val < -100) return 'Price change percentage cannot be less than -100% (prices cannot be negative).';
      if (val > 500) return 'Price change percentage cannot exceed +500%.';
    } else if (formInterventionType === 'Sales Volume Change') {
      if (val < -100) return 'Sales volume change percentage cannot be less than -100% (sales volume cannot be negative).';
      if (val > 500) return 'Sales volume change percentage cannot exceed +500%.';
    } else if (formInterventionType === 'Operating Cost Reduction') {
      if (!hasCost) return 'Operating Cost Reduction is unsupported: dataset lacks required cost or profit metrics.';
      if (val < 0) return 'Operating cost reduction percentage cannot be negative (must be >= 0%).';
      if (val > 100) return 'Operating cost reduction percentage cannot exceed 100% (costs cannot be reduced below zero).';
    } else if (formInterventionType === 'Discount Change') {
      if (!hasDiscount) return 'Discount Change is unsupported: dataset lacks valid discount data.';
      if (formParameterType === 'percentage') {
        if (val < -100 || val > 100) return 'Discount percentage change must be between -100% and +100%.';
      } else {
        if (val < 0) return 'Percentage points discount reduction cannot be negative.';
        if (val > 100) return 'Percentage points discount reduction cannot exceed 100 pp.';
      }
    }
    return null;
  };

  const handleSaveOrUpdateScenario = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    const err = validateForm();
    if (err) {
      setFormError(err);
      return;
    }

    const val = Number(formChangeValue);
    const params: Record<string, any> = {
      intervention_type: formInterventionType,
      change_percentage: val,
      parameter_type: formParameterType,
      notes: formNotes.trim(),
      price_change_pct: 0,
      volume_change_pct: 0,
      operational_efficiency_pct: 0,
      discount_adjustment_pct: 0,
      churn_mitigation_pct: 0,
    };

    if (formInterventionType === 'Price Change') {
      params.price_change_pct = val;
    } else if (formInterventionType === 'Sales Volume Change') {
      params.volume_change_pct = val;
    } else if (formInterventionType === 'Operating Cost Reduction') {
      params.operational_efficiency_pct = val;
    } else if (formInterventionType === 'Discount Change') {
      params.discount_adjustment_pct = val;
    }

    setIsSubmittingForm(true);
    try {
      if (editingScenarioId) {
        await api.updateScenario(editingScenarioId, {
          name: formName.trim(),
          parameters: params,
        });
        setFormSuccess(`Scenario "${formName.trim()}" successfully updated.`);
        setEditingScenarioId(null);
      } else {
        await api.saveScenario(
          analysis.id,
          formName.trim(),
          params
        );
        setFormSuccess(`Scenario "${formName.trim()}" successfully created and evaluated.`);
      }
      setFormName('');
      setFormNotes('');
      setFormChangeValue(5.0);
      await loadScenariosAndComparison();
    } catch (apiErr: any) {
      setFormError(apiErr.message || 'Failed to save scenario.');
    } finally {
      setIsSubmittingForm(false);
    }
  };

  const handleEditScenario = (sc: any) => {
    setEditingScenarioId(sc.id || null);
    setFormName(sc.name || '');
    const p = sc.parameters || {};
    if (p.intervention_type) {
      setFormInterventionType(p.intervention_type);
      setFormChangeValue(p.change_percentage ?? p.change_pct ?? 0);
      setFormParameterType(p.parameter_type || 'percentage');
    } else if (p.price_change_pct && p.price_change_pct !== 0) {
      setFormInterventionType('Price Change');
      setFormChangeValue(p.price_change_pct);
      setFormParameterType('percentage');
    } else if (p.volume_change_pct && p.volume_change_pct !== 0) {
      setFormInterventionType('Sales Volume Change');
      setFormChangeValue(p.volume_change_pct);
      setFormParameterType('percentage');
    } else if (p.operational_efficiency_pct && p.operational_efficiency_pct !== 0) {
      setFormInterventionType('Operating Cost Reduction');
      setFormChangeValue(p.operational_efficiency_pct);
      setFormParameterType('percentage');
    } else if (p.discount_adjustment_pct && p.discount_adjustment_pct !== 0) {
      setFormInterventionType('Discount Change');
      setFormChangeValue(p.discount_adjustment_pct);
      setFormParameterType(p.parameter_type || 'percentage');
    } else {
      setFormInterventionType('Price Change');
      setFormChangeValue(0);
      setFormParameterType('percentage');
    }
    setFormNotes(p.notes || sc.notes || '');
    setFormError(null);
    setFormSuccess(null);
  };

  const handleCancelEdit = () => {
    setEditingScenarioId(null);
    setFormName('');
    setFormNotes('');
    setFormChangeValue(5.0);
    setFormError(null);
    setFormSuccess(null);
  };

  const handleDeleteScenario = async (scId: string) => {
    try {
      await api.deleteScenario(scId);
      if (editingScenarioId === scId) {
        handleCancelEdit();
      }
      await loadScenariosAndComparison();
    } catch (err) {
      console.error('Failed to delete scenario:', err);
    }
  };

  const handleLoadScenario = (sc: any) => {
    const p = sc.parameters || {};
    setPriceChange(p.price_change_pct || 0);
    setDiscountAdjust(p.discount_adjustment_pct || 0);
    setChurnMitigation(p.churn_mitigation_pct || 0);
    setOpsEfficiency(p.operational_efficiency_pct || 0);
  };

  // Helpers to detect intent vs parameter mismatches
  const isNameSuggestingReduction = (name: string): boolean => {
    if (!name) return false;
    const lower = name.toLowerCase();
    return ['reduct', 'cut', 'decreas', 'lower', 'drop', 'discount'].some((k) => lower.includes(k));
  };

  const isNameSuggestingIncrease = (name: string): boolean => {
    if (!name) return false;
    const lower = name.toLowerCase();
    return ['increas', 'hike', 'growth', 'raise', 'expand'].some((k) => lower.includes(k));
  };

  // ECharts Option for Scenario Comparison (via centralized deterministic builder)
  const getComparisonChartOption = () => {
    return buildComparisonChartOption(comparisonReport);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Scenario Simulator & Sensitivity Engine
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Adjust the 4 decision levers below to test expected revenue, net profit, and profit margin changes in real-time.
          </p>
        </div>

        <button
          onClick={handleResetLevers}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors shrink-0"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset All Levers</span>
        </button>
      </div>

      {/* Simulator 4 Levers Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Sliders className="w-4 h-4 text-blue-600" />
            4 Strategic Decision Levers
          </h3>
          <span className="text-xs text-slate-500">Real-time deterministic calculations</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Lever 1: Price Change */}
          <div className="space-y-2 p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800">1. Price Change</span>
              <span className="font-mono font-extrabold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {priceChange > 0 ? '+' : ''}{priceChange}%
              </span>
            </div>
            <input
              type="range"
              min="-30"
              max="30"
              step="1"
              value={priceChange}
              onChange={(e) => setPriceChange(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>-30%</span>
              <span className="text-slate-400 font-medium">Standard range (-30% to +30%)</span>
              <span>+30%</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Estimated price scenario assuming quantity remains unchanged.
            </div>
          </div>

          {/* Lever 2: Discount Change */}
          <div className={`space-y-2 p-4 rounded-xl border border-slate-200/80 ${hasDiscount ? 'bg-slate-50' : 'bg-slate-100/60 opacity-70'}`}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800">2. Discount Change</span>
              <span className={`font-mono font-extrabold px-2 py-0.5 rounded border ${hasDiscount ? 'text-blue-700 bg-blue-50 border-blue-200' : 'text-slate-400 bg-slate-200 border-slate-300'}`}>
                {hasDiscount ? `${discountAdjust > 0 ? '+' : ''}${discountAdjust}%` : 'Unavailable'}
              </span>
            </div>
            <input
              type="range"
              min="-20"
              max="20"
              step="1"
              value={hasDiscount ? discountAdjust : 0}
              onChange={(e) => hasDiscount && setDiscountAdjust(Number(e.target.value))}
              disabled={!hasDiscount}
              className={`w-full accent-blue-600 ${hasDiscount ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>-20%</span>
              <span className="text-slate-400 font-medium">Standard range (-20% to +20%)</span>
              <span>+20%</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {hasDiscount ? 'Directly recovers bottom-line profit.' : 'Unavailable: Requires a Discount column in the uploaded dataset.'}
            </div>
          </div>

          {/* Lever 3: Customer Retention */}
          <div className={`space-y-2 p-4 rounded-xl border border-slate-200/80 ${hasRetention ? 'bg-slate-50' : 'bg-slate-100/60 opacity-70'}`}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800">3. Customer Retention</span>
              <span className={`font-mono font-extrabold px-2 py-0.5 rounded border ${hasRetention ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-400 bg-slate-200 border-slate-300'}`}>
                {hasRetention ? `+${churnMitigation}%` : 'Unavailable'}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="25"
              step="1"
              value={hasRetention ? churnMitigation : 0}
              onChange={(e) => hasRetention && setChurnMitigation(Number(e.target.value))}
              disabled={!hasRetention}
              className={`w-full accent-emerald-600 ${hasRetention ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0% (No change)</span>
              <span className="text-slate-400 font-medium">Standard range (0% to +25%)</span>
              <span>+25%</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {hasRetention ? 'Protects recurring revenue and margin from customer loss.' : 'Unavailable: Requires customer churn data in the uploaded dataset.'}
            </div>
          </div>

          {/* Lever 4: Cost Efficiency */}
          <div className={`space-y-2 p-4 rounded-xl border border-slate-200/80 ${hasCost ? 'bg-slate-50' : 'bg-slate-100/60 opacity-70'}`}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-800">4. Cost Efficiency</span>
              <span className={`font-mono font-extrabold px-2 py-0.5 rounded border ${hasCost ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-400 bg-slate-200 border-slate-300'}`}>
                {hasCost ? `+${opsEfficiency}%` : 'Unavailable'}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="15"
              step="1"
              value={hasCost ? opsEfficiency : 0}
              onChange={(e) => hasCost && setOpsEfficiency(Number(e.target.value))}
              disabled={!hasCost}
              className={`w-full accent-emerald-600 ${hasCost ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0% (No change)</span>
              <span className="text-slate-400 font-medium">Standard range (0% to +15%)</span>
              <span>+15%</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {hasCost ? 'Reduces baseline operating costs directly.' : 'Unavailable: Requires Cost data in the uploaded dataset.'}
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Projected Outcome Cards */}
      {simulationOutcome && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Revenue Impact */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
              <span>Simulated Revenue</span>
              <DollarSign className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-2xl font-black text-slate-900">
              ${simulationOutcome.simulated_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`font-bold ${simulationOutcome.revenue_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
              >
                {simulationOutcome.revenue_delta >= 0 ? '+' : ''}
                ${simulationOutcome.revenue_delta.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-slate-400">
                ({simulationOutcome.revenue_delta_pct >= 0 ? '+' : ''}
                {simulationOutcome.revenue_delta_pct.toFixed(1)}%)
              </span>
            </div>
          </div>

          {/* Net Profit Impact */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
              <span>Simulated Net Profit</span>
              <TrendingUp className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-black text-slate-900">
              ${simulationOutcome.simulated_profit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`font-bold ${simulationOutcome.profit_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
              >
                {simulationOutcome.profit_delta >= 0 ? '+' : ''}
                ${simulationOutcome.profit_delta.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-slate-400">
                ({simulationOutcome.profit_delta_pct >= 0 ? '+' : ''}
                {simulationOutcome.profit_delta_pct.toFixed(1)}%)
              </span>
            </div>
          </div>

          {/* Profit Margin */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
              <span>Simulated Profit Margin</span>
              <Percent className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-black text-slate-900">
              {simulationOutcome.simulated_margin_pct?.toFixed(2) || '0.00'}%
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`font-bold ${(simulationOutcome.margin_delta_pct || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
              >
                {(simulationOutcome.margin_delta_pct || 0) >= 0 ? '+' : ''}
                {simulationOutcome.margin_delta_pct?.toFixed(2) || '0.00'}%
              </span>
              <span className="text-slate-400">
                (Baseline: {simulationOutcome.baseline_margin_pct?.toFixed(2) || '0.00'}%)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Financial Comparison Charts */}
      <div className="space-y-4">
        {/* Keep the three comparison charts together at full available width. */}
        {simulationOutcome && (
          <div className="w-full min-w-0 rounded-xl">
            <SimulationChart outcome={simulationOutcome} />
          </div>
        )}

        {/* 1% Lever Sensitivity Breakdown — compact full-width section below charts */}
        <div className="bg-white p-4 sm:p-5 rounded-xl border border-blue-100 shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Percent className="w-4 h-4 text-blue-600" />
              1% Lever Sensitivity Breakdown
            </h3>
            <p className="text-xs text-slate-500">
              Estimated financial impact of a 1% change in each supported lever.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(min(100%,220px),1fr))] gap-3 text-xs">
            {sensitivity.price_sensitivity_per_pct !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 min-w-0">
                <div className="text-[11px] text-slate-500 font-semibold">1% Price Shift</div>
                <div className="font-extrabold text-slate-900 mt-1 break-words">
                  ${Number(sensitivity.price_sensitivity_per_pct || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            )}
            {sensitivity.discount_recapture_per_pct !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 min-w-0">
                <div className="text-[11px] text-slate-500 font-semibold">1% Discount Control</div>
                <div className="font-extrabold text-slate-900 mt-1 break-words">
                  ${Number(sensitivity.discount_recapture_per_pct || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            )}
            {sensitivity.churn_mitigation_per_pct !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 min-w-0">
                <div className="text-[11px] text-slate-500 font-semibold">1% Customer Retention</div>
                <div className="font-extrabold text-slate-900 mt-1 break-words">
                  ${Number(sensitivity.churn_mitigation_per_pct || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            )}
            {sensitivity.operational_efficiency_per_pct !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 min-w-0">
                <div className="text-[11px] text-slate-500 font-semibold">1% Overhead Efficiency</div>
                <div className="font-extrabold text-slate-900 mt-1 break-words">
                  ${Number(sensitivity.operational_efficiency_per_pct || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            )}
            {Object.keys(sensitivity).length === 0 && (
              <div className="sm:col-span-2 lg:col-span-4 text-slate-400 italic text-[11px] p-3 bg-slate-50 rounded-lg border border-slate-100">
                No active levers supported for this dataset.
              </div>
            )}
          </div>

          {simulationOutcome?.assumptions_statement && (
            <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed italic">
              
              {simulationOutcome.assumptions_statement}
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit Scenario Form Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
          <div className="flex items-center gap-2">
            {editingScenarioId ? (
              <Edit3 className="w-5 h-5 text-amber-600" />
            ) : (
              <PlusCircle className="w-5 h-5 text-blue-600" />
            )}
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                {editingScenarioId ? 'Edit Scenario Intervention' : 'Create & Compare Scenario'}
              </h3>
              <p className="text-xs text-slate-500">
                Configure deterministic business interventions to benchmark against the baseline.
              </p>
            </div>
          </div>
          {editingScenarioId && (
            <button
              onClick={handleCancelEdit}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Cancel Edit</span>
            </button>
          )}
        </div>

        {formError && (
          <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{formError}</span>
          </div>
        )}

        {formSuccess && (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{formSuccess}</span>
          </div>
        )}

        <form onSubmit={handleSaveOrUpdateScenario} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Scenario Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 block">
                Scenario Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g., Q4 Moderate Growth Plan"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-hidden bg-white"
              />
            </div>

            {/* Intervention Type */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 block">
                Intervention Type <span className="text-rose-500">*</span>
              </label>
              <select
                value={formInterventionType}
                onChange={(e) => {
                  setFormInterventionType(e.target.value);
                  setFormError(null);
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-hidden bg-white"
              >
                <option value="Price Change">Price Change</option>
                <option value="Sales Volume Change">Sales Volume Change</option>
                <option value="Operating Cost Reduction" disabled={!hasCost}>
                  Operating Cost Reduction {!hasCost ? '(Requires Cost Data)' : ''}
                </option>
                <option value="Discount Change" disabled={!hasDiscount}>
                  Discount Change {!hasDiscount ? '(Requires Discount Data)' : ''}
                </option>
              </select>
            </div>

            {/* Change Parameter & Type */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 block">
                  {formInterventionType === 'Operating Cost Reduction'
                    ? 'Cost Reduction (%)'
                    : formInterventionType === 'Discount Change'
                      ? `Discount Change (${formParameterType === 'percentage' ? '%' : 'pp'})`
                      : 'Change Percentage (%)'}{' '}
                  <span className="text-rose-500">*</span>
                </label>
                {formInterventionType === 'Discount Change' && (
                  <div className="flex items-center gap-1 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setFormParameterType('percentage')}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold cursor-pointer ${formParameterType === 'percentage'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                    >
                      %
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormParameterType('percentage_points')}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold cursor-pointer ${formParameterType === 'percentage_points'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                    >
                      pp
                    </button>
                  </div>
                )}
              </div>
              <input
                type="number"
                step="0.1"
                placeholder={formInterventionType === 'Operating Cost Reduction' ? 'e.g., 5.0' : 'e.g., +5.0 or -2.5'}
                value={formChangeValue}
                onChange={(e) => setFormChangeValue(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 outline-hidden bg-white"
              />

              {/* Quick sign selectors for Price and Volume changes */}
              {(formInterventionType === 'Price Change' || formInterventionType === 'Sales Volume Change') && (
                <div className="flex items-center gap-1.5 pt-0.5">
                  <span className="text-[10px] text-slate-500 font-medium">Quick Sign:</span>
                  <button
                    type="button"
                    onClick={() => {
                      const num = Number(formChangeValue);
                      if (!isNaN(num) && num !== 0) setFormChangeValue(Math.abs(num));
                    }}
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors cursor-pointer ${
                      Number(formChangeValue) > 0
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    + Increase
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const num = Number(formChangeValue);
                      if (!isNaN(num) && num !== 0) setFormChangeValue(-Math.abs(num));
                    }}
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors cursor-pointer ${
                      Number(formChangeValue) < 0
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    - Reduction / Cut
                  </button>
                </div>
              )}

              {/* Intent Mismatch Advisory */}
              {formInterventionType === 'Price Change' && Number(formChangeValue) > 0 && isNameSuggestingReduction(formName) && (
                <div className="flex items-center justify-between p-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 mt-1">
                  <div className="flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Scenario name suggests a reduction, but <b>+{formChangeValue}%</b> is an increase.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormChangeValue(-Math.abs(Number(formChangeValue)))}
                    className="ml-2 px-2 py-0.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-[10px] font-bold cursor-pointer transition-colors shrink-0"
                  >
                    Switch to -{Math.abs(Number(formChangeValue))}%
                  </button>
                </div>
              )}
              {formInterventionType === 'Price Change' && Number(formChangeValue) < 0 && isNameSuggestingIncrease(formName) && (
                <div className="flex items-center justify-between p-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 mt-1">
                  <div className="flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Scenario name suggests an increase, but <b>{formChangeValue}%</b> is a reduction.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormChangeValue(Math.abs(Number(formChangeValue)))}
                    className="ml-2 px-2 py-0.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-bold cursor-pointer transition-colors shrink-0"
                  >
                    Switch to +{Math.abs(Number(formChangeValue))}%
                  </button>
                </div>
              )}

              <div className="text-[10px] text-slate-400">
                {formInterventionType === 'Price Change' && 'Range: -100% to +500%. Affects revenue without changing quantity.'}
                {formInterventionType === 'Sales Volume Change' && 'Range: -100% to +500%. Scales revenue and variable costs.'}
                {formInterventionType === 'Operating Cost Reduction' && 'Range: 0% to 100%. Lowers costs directly; revenue is unchanged.'}
                {formInterventionType === 'Discount Change' &&
                  (formParameterType === 'percentage'
                    ? 'Range: -100% to +100%. Relative change in existing discount rate.'
                    : 'Range: 0 to 100 pp. Direct percentage-point reduction in discount rate.')}
              </div>
            </div>
          </div>

          {/* Assumptions & Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">
              Assumptions & Notes <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <textarea
              rows={2}
              placeholder="Record business context, elasticity assumptions, or constraints for this intervention..."
              value={formNotes}
              onChange={(e) => setFormNotes(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 outline-hidden bg-white resize-none"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={!formName.trim() || isSubmittingForm}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-colors shadow-xs cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>
                  {isSubmittingForm
                    ? 'Evaluating...'
                    : editingScenarioId
                      ? 'Update & Re-evaluate Scenario'
                      : 'Save & Evaluate Scenario'}
                </span>
              </button>

              {editingScenarioId && (
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="px-3 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              )}
            </div>

            {savedScenarios.length > 0 && (
              <div className="hidden sm:flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-semibold">Saved:</span>
                <div className="flex gap-1.5 overflow-x-auto max-w-sm">
                  {savedScenarios.map((sc, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleEditScenario(sc)}
                      title={`Click to edit "${sc.name || sc.scenario_name}"`}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors truncate max-w-[140px] cursor-pointer ${editingScenarioId === sc.id
                          ? 'bg-blue-100 text-blue-800 font-bold border border-blue-300'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                        }`}
                    >
                      {sc.name || sc.scenario_name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Phase 13: Scenario Comparison Section */}
      {comparisonReport && (
        <div className="space-y-5">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900 uppercase tracking-wider">
                <Scale className="w-4 h-4 text-blue-600" />
                <span>Scenario Comparison Table</span>
              </div>
              <span className="text-xs text-slate-500">
                {comparisonReport.scenarios.length} scenarios evaluated
              </span>
            </div>

            {/* Comparison Table */}
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Scenario</th>
                    <th className="py-2.5 px-3">Intervention & Notes</th>
                    <th className="py-2.5 px-3">Revenue</th>
                    <th className="py-2.5 px-3">Net Profit</th>
                    <th className="py-2.5 px-3">Profit Margin %</th>
                    <th className="py-2.5 px-3">Incremental Value</th>
                    <th className="py-2.5 px-3">Risk-Adjusted Return</th>
                    <th className="py-2.5 px-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {comparisonReport.scenarios.map((sc, idx) => {
                    const isBase = sc.id === 'baseline';
                    return (
                      <tr key={idx} className={isBase ? 'bg-slate-50/70 font-semibold' : 'hover:bg-slate-50/70'}>
                        <td className="py-2.5 px-3 font-bold text-slate-900">
                          {sc.name} {isBase && <span className="text-[10px] text-slate-400 font-normal">(Default 0%)</span>}
                        </td>
                        <td className="py-2.5 px-3">
                          {isBase ? (
                            <span className="text-[11px] text-slate-400 italic">Baseline (no change)</span>
                          ) : (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                  (Number(sc.parameters?.price_change_pct) < 0 || Number(sc.parameters?.change_percentage) < 0 || Number(sc.parameters?.volume_change_pct) < 0)
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-blue-50 text-blue-700 border-blue-200'
                                }`}>
                                  {sc.intervention_summary || sc.parameters?.intervention_type || 'Custom'}
                                </span>
                                {isNameSuggestingReduction(sc.name) && (Number(sc.parameters?.change_percentage) > 0 || Number(sc.parameters?.price_change_pct) > 0) && (
                                  <span
                                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-100 text-amber-800 border border-amber-300"
                                    title="Scenario name mentions reduction, but parameters specify a positive increase (+). Click Edit to adjust to negative."
                                  >
                                    <AlertCircle className="w-2.5 h-2.5 text-amber-600" />
                                    <span>Param: +{sc.parameters?.change_percentage ?? sc.parameters?.price_change_pct}%</span>
                                  </span>
                                )}
                              </div>
                              {(sc.notes || sc.parameters?.notes) && (
                                <div className="text-[11px] text-slate-500 italic max-w-xs truncate" title={sc.notes || sc.parameters?.notes}>
                                  "{sc.notes || sc.parameters?.notes}"
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          ${sc.revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          {!isBase && (
                            <span className={`text-[10px] ml-1 ${sc.revenue_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              ({sc.revenue_delta >= 0 ? '+' : ''}${sc.revenue_delta.toLocaleString()})
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                          ${sc.profit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          {!isBase && (
                            <span className={`text-[10px] ml-1 ${sc.profit_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                              ({sc.profit_delta >= 0 ? '+' : ''}${sc.profit_delta.toLocaleString()})
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {sc.profit_margin_pct.toFixed(2)}%
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-emerald-600">
                          ${sc.incremental_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          ${sc.risk_adjusted_return.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {!isBase && (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleEditScenario(sc)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 rounded text-[10px] font-semibold transition-colors cursor-pointer"
                                title="Edit Scenario Parameters"
                              >
                                <Edit3 className="w-3 h-3" />
                                <span>Edit</span>
                              </button>
                              <button
                                onClick={() => sc.id && handleDeleteScenario(sc.id)}
                                className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors cursor-pointer"
                                title="Delete Scenario"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Simulation Insights */}
            {comparisonReport.comparison_insights && comparisonReport.comparison_insights.length > 0 && (
              <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900 uppercase">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
                  <span>Simulation Insights</span>
                </div>
                <ul className="list-disc list-inside text-xs text-blue-800 space-y-1">
                  {comparisonReport.comparison_insights.map((ins, i) => (
                    <li key={i}>{ins}</li>
                  ))}
                </ul>
                <div className="text-[11px] text-slate-500 pt-1 italic">
                  Note: Scenario simulation ≠ approved decision. Record binding management notes in Decision Notes.
                </div>
              </div>
            )}

            {/* Side-by-side Visual Comparison Chart */}
            {comparisonReport.scenarios.length > 1 ? (
              <div className="pt-4 border-t border-slate-100">
                <div className="w-full bg-slate-50/50 p-4 rounded-xl border border-slate-200 shadow-xs">
                  <ReactECharts
                    option={getComparisonChartOption()}
                    notMerge={true}
                    lazyUpdate={true}
                    style={{ height: 380, width: '100%', minHeight: 380 }}
                  />
                </div>
              </div>
            ) : (
              <div className="pt-4 border-t border-slate-100">
                <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center space-y-2">
                  <Scale className="w-8 h-8 text-slate-400 stroke-1" />
                  <div className="text-xs font-semibold text-slate-700">Financial Comparison Chart Ready</div>
                  <p className="text-[11px] text-slate-500 max-w-sm">
                    Save at least one intervention scenario above to compare Revenue, Net Profit, and Profit Margins side-by-side against the baseline.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Forecast vs Actual Holdout Validation */}
      {analysis?.id && (
        <ForecastVsActual analysisId={analysis.id} />
      )}

      {/* Navigation Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
        <div>
          <div className="text-xs text-blue-300 font-bold uppercase">Next Stage</div>
          <div className="text-sm font-semibold">Record Management Decisions in Decision Notes</div>
        </div>
        <button
          onClick={onNavigateNext}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <span>View Decision Notes</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export { WhatIfAnalysis as Stage7_WhatIfAnalysis };

