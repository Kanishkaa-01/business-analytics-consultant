import React, { useState, useEffect } from 'react';
import {
  Sliders,
  DollarSign,
  TrendingUp,
  ShieldCheck,
  Save,
  CheckCircle2,
  Clock,
  Printer,
  FileCode2,
  BookmarkCheck,
  RotateCcw
} from 'lucide-react';
import {
  AnalysisRunResponse,
  DecisionRecord,
  SimulationOutcome,
  SimulationRequest
} from '../../types';
import { api } from '../../services/api';
import { SimulationChart } from '../charts/SimulationChart';

interface Props {
  analysis: AnalysisRunResponse;
  decisions: DecisionRecord[];
  onDecisionsUpdated: () => void;
}

export const Stage8_DecisionSupport: React.FC<Props> = ({
  analysis,
  decisions,
  onDecisionsUpdated,
}) => {
  // Simulator Levers
  const [priceChange, setPriceChange] = useState<number>(0);
  const [discountAdjust, setDiscountAdjust] = useState<number>(0);
  const [churnMitigation, setChurnMitigation] = useState<number>(0);
  const [opsEfficiency, setOpsEfficiency] = useState<number>(0);

  const [simulationOutcome, setSimulationOutcome] = useState<SimulationOutcome | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [scenarioName, setScenarioName] = useState<string>('');
  const [savedScenarios, setSavedScenarios] = useState<any[]>([]);
  const [isSavingScenario, setIsSavingScenario] = useState<boolean>(false);

  // Run simulation whenever levers shift
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

  useEffect(() => {
    triggerSimulation(priceChange, discountAdjust, churnMitigation, opsEfficiency);
  }, [priceChange, discountAdjust, churnMitigation, opsEfficiency]);

  useEffect(() => {
    api.listSavedScenarios(analysis.id).then(setSavedScenarios).catch(console.error);
  }, [analysis.id]);

  const handleResetLevers = () => {
    setPriceChange(0);
    setDiscountAdjust(0);
    setChurnMitigation(0);
    setOpsEfficiency(0);
  };

  const handleSaveScenario = async () => {
    if (!scenarioName.trim() || !simulationOutcome) return;
    setIsSavingScenario(true);
    try {
      await api.saveScenario(
        analysis.id,
        scenarioName.trim(),
        {
          price_change_pct: priceChange,
          discount_adjustment_pct: discountAdjust,
          churn_mitigation_pct: churnMitigation,
          operational_efficiency_pct: opsEfficiency,
        },
        simulationOutcome
      );
      setScenarioName('');
      const list = await api.listSavedScenarios(analysis.id);
      setSavedScenarios(list);
    } catch (err) {
      console.error('Save scenario error:', err);
    } finally {
      setIsSavingScenario(false);
    }
  };

  const handleLoadScenario = (sc: any) => {
    const p = sc.parameters;
    setPriceChange(p.price_change_pct || 0);
    setDiscountAdjust(p.discount_adjustment_pct || 0);
    setChurnMitigation(p.churn_mitigation_pct || 0);
    setOpsEfficiency(p.operational_efficiency_pct || 0);
  };

  return (
    <div className="space-y-6">
      {/* Research Anchor Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Sliders className="w-3.5 h-3.5" />
            Human-in-the-Loop Decision Support & Interactive Simulator
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Tradeoff Simulation & Management Decision Registry
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Bridge the gap between analytics and executive decisions. Test managerial interventions,
            simulate price elasticity and potential profit recovery, and record binding management decisions with
            traceable rationales.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.open(`/api/export/${analysis.id}/print-report`, '_blank')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white shadow-xs transition-colors"
          >
            <Printer className="w-4 h-4" />
            <span>Print Executive Dossier</span>
          </button>
        </div>
      </div>

      {/* Simulator Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Interactive Control Sliders */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-5 lg:col-span-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-600" />
              Decision Levers
            </h3>
            <button
              onClick={handleResetLevers}
              className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          </div>

          {/* Lever 1: Price Change */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">Base Price Adjustment</span>
              <span className="font-mono font-bold text-blue-600">
                {priceChange > 0 ? `+${priceChange}%` : `${priceChange}%`}
              </span>
            </div>
            <input
              type="range"
              min="-20"
              max="20"
              step="1"
              value={priceChange}
              onChange={(e) => setPriceChange(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-20% (Volume Boost)</span>
              <span>0%</span>
              <span>+20% (Margin Focus)</span>
            </div>
          </div>

          {/* Lever 2: Discount Hardening */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">Discount Floor Enforcement</span>
              <span className="font-mono font-bold text-blue-600">+{discountAdjust}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="25"
              step="1"
              value={discountAdjust}
              onChange={(e) => setDiscountAdjust(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>0% Discretionary</span>
              <span>+25% Algorithmic Floor</span>
            </div>
          </div>

          {/* Lever 3: Churn Mitigation */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">Churn / Account Retention</span>
              <span className="font-mono font-bold text-blue-600">+{churnMitigation}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="40"
              step="5"
              value={churnMitigation}
              onChange={(e) => setChurnMitigation(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>0% Baseline</span>
              <span>+40% Dedicated CSM</span>
            </div>
          </div>

          {/* Lever 4: Cost Efficiency */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">Operational Cost Efficiency</span>
              <span className="font-mono font-bold text-blue-600">+{opsEfficiency}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="15"
              step="1"
              value={opsEfficiency}
              onChange={(e) => setOpsEfficiency(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>0% Status Quo</span>
              <span>+15% Lean Fulfillment</span>
            </div>
          </div>

          {/* Save Scenario Form */}
          <div className="pt-4 border-t border-slate-100 space-y-2">
            <label className="block text-xs font-semibold text-slate-700">
              Save Strategy Scenario
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Scenario Name (e.g., Aggressive Q4)"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                className="flex-1 text-xs border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                onClick={handleSaveScenario}
                disabled={isSavingScenario || !scenarioName.trim()}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
              >
                Save
              </button>
            </div>

            {savedScenarios.length > 0 && (
              <div className="mt-3 space-y-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Saved Scenarios
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {savedScenarios.map((sc) => (
                    <button
                      key={sc.id}
                      onClick={() => handleLoadScenario(sc)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200"
                    >
                      <BookmarkCheck className="w-3 h-3 text-blue-600" />
                      {sc.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Projected Outcomes & Impact Model */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              Simulated Financial Projections & Economic Value Added
            </h3>
            {isSimulating && (
              <span className="text-xs text-blue-600 font-medium animate-pulse">Calculating...</span>
            )}
          </div>

          {simulationOutcome && (
            <>
              {/* Scorecards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                  <div className="text-[10px] font-bold uppercase text-slate-500">Gross Revenue</div>
                  <div className="text-lg font-bold text-slate-900 mt-1">
                    ${simulationOutcome.simulated_revenue.toLocaleString()}
                  </div>
                  <div
                    className={`text-[11px] font-semibold mt-0.5 ${
                      simulationOutcome.revenue_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {simulationOutcome.revenue_delta >= 0 ? '+' : ''}
                    ${simulationOutcome.revenue_delta.toLocaleString()} (
                    {simulationOutcome.revenue_delta_pct > 0 ? '+' : ''}
                    {simulationOutcome.revenue_delta_pct}%)
                  </div>
                </div>

                <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                  <div className="text-[10px] font-bold uppercase text-slate-500">Net Profit</div>
                  <div className="text-lg font-bold text-slate-900 mt-1">
                    ${simulationOutcome.simulated_profit.toLocaleString()}
                  </div>
                  <div
                    className={`text-[11px] font-semibold mt-0.5 ${
                      simulationOutcome.profit_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {simulationOutcome.profit_delta >= 0 ? '+' : ''}
                    ${simulationOutcome.profit_delta.toLocaleString()} (
                    {simulationOutcome.profit_delta_pct > 0 ? '+' : ''}
                    {simulationOutcome.profit_delta_pct}%)
                  </div>
                </div>

                <div className="bg-emerald-50/70 p-3.5 rounded-xl border border-emerald-200">
                  <div className="text-[10px] font-bold uppercase text-emerald-700">Economic Value (EVA)</div>
                  <div className="text-lg font-black text-emerald-900 mt-1">
                    +${simulationOutcome.net_economic_value_added.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-emerald-700 mt-0.5">Incremental Profit Generated</div>
                </div>

                <div className="bg-blue-50/70 p-3.5 rounded-xl border border-blue-200">
                  <div className="text-[10px] font-bold uppercase text-blue-700">Risk-Adjusted Return</div>
                  <div className="text-lg font-black text-blue-900 mt-1">
                    ${simulationOutcome.risk_adjusted_return.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-blue-700 mt-0.5">Execution Risk Discounted</div>
                </div>
              </div>

              {/* Supporting Simulation Chart */}
              <div className="space-y-1">
                <SimulationChart outcome={simulationOutcome} />
              </div>

              {/* Lever Sensitivity & Reinforced Recommendations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
                <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                  <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                    Lever Marginal Sensitivity (per 1% Shift)
                  </div>
                  <div className="space-y-1 text-slate-600 font-mono text-[11px]">
                    <div className="flex justify-between">
                      <span>Price Sensitivity:</span>
                      <span className="font-bold text-slate-900">
                        ${simulationOutcome.sensitivity_breakdown.price_sensitivity_per_pct.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Discount Profit Recovery:</span>
                      <span className="font-bold text-slate-900">
                        ${simulationOutcome.sensitivity_breakdown.discount_recapture_per_pct.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Churn Mitigation:</span>
                      <span className="font-bold text-slate-900">
                        ${simulationOutcome.sensitivity_breakdown.churn_mitigation_per_pct.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Cost Efficiency:</span>
                      <span className="font-bold text-slate-900">
                        ${simulationOutcome.sensitivity_breakdown.operational_efficiency_per_pct.toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                  <div className="font-bold text-slate-800 uppercase tracking-wider text-[11px] text-blue-700">
                    Reinforced Recommendations
                  </div>
                  {simulationOutcome.recommendation_impact_overlap.length === 0 ? (
                    <p className="text-slate-500 italic">Adjust levers to observe reinforcement alignment.</p>
                  ) : (
                    <ul className="space-y-1 text-slate-700">
                      {simulationOutcome.recommendation_impact_overlap.map((recTitle, idx) => (
                        <li key={idx} className="flex items-center gap-1.5 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          <span className="truncate">{recTitle}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Decision Registry Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <BookmarkCheck className="w-4 h-4 text-emerald-600" />
            Executive Decision Registry (Human-in-the-Loop Audit Trail)
          </h3>
          <span className="text-xs text-slate-500">{decisions.length} decisions committed</span>
        </div>

        {decisions.length === 0 ? (
          <div className="p-6 text-center bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600">
            No decisions recorded yet. Return to <b>Stage 8: Action Matrix</b> to formally review and record management decisions.
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 text-[11px] font-bold text-slate-600 uppercase border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Action Title</th>
                  <th className="py-2.5 px-3">Decision Status</th>
                  <th className="py-2.5 px-3">Stakeholder</th>
                  <th className="py-2.5 px-3">Expected Impact</th>
                  <th className="py-2.5 px-3">Target Date</th>
                  <th className="py-2.5 px-3">Justification Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {decisions.map((dec) => (
                  <tr key={dec.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-bold text-slate-900">{dec.action_title}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          dec.decision_status === 'Accepted'
                            ? 'bg-emerald-100 text-emerald-800'
                            : dec.decision_status === 'Rejected'
                            ? 'bg-rose-100 text-rose-800'
                            : dec.decision_status === 'Deferred'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {dec.decision_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-800">{dec.stakeholder}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-emerald-700">
                      ${dec.expected_impact_dollars?.toLocaleString() || 0}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{dec.target_date || '—'}</td>
                    <td className="py-2.5 px-3 text-slate-600 max-w-sm truncate" title={dec.notes_rationale}>
                      {dec.notes_rationale || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
