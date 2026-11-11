from typing import Dict, Any, List, Optional
from app.models.schemas import DecisionImpactItem, DecisionImpactMatrixResponse


class DecisionImpactEngine:
    """
    Deterministic Decision Impact Matrix Engine.
    Maps managerial recommendations onto an Effort vs. Business Impact quadrant matrix.
    """

    @classmethod
    def generate_impact_matrix(cls, recommendations: List[Dict[str, Any]]) -> DecisionImpactMatrixResponse:
        """
        Calculates deterministic coordinates and quadrant assignments for recommendations.
        """
        items: List[DecisionImpactItem] = []
        quadrant_counts = {
            "Quick Wins": 0,
            "Strategic Bets": 0,
            "Fill-ins": 0,
            "Re-evaluate": 0
        }

        effort_map = {
            "low": 2.5,
            "medium": 5.0,
            "high": 8.0
        }

        for idx, rec in enumerate(recommendations or []):
            rec_id = str(rec.get("id") or rec.get("recommendation_id") or f"REC-{idx+1}")
            action_title = str(rec.get("title") or rec.get("action_title") or f"Action {idx+1}")
            
            # Dollar impact
            dollar_impact = float(
                rec.get("expected_financial_impact") or
                rec.get("expected_impact_dollars") or
                rec.get("financial_impact") or
                0.0
            )

            # Impact score (1 to 10)
            raw_impact = rec.get("impact_score")
            if raw_impact is not None and float(raw_impact) > 0:
                impact_score = min(10.0, max(1.0, float(raw_impact)))
            else:
                # Deterministic scale based on priority tier and financial impact
                tier = str(rec.get("priority_tier", "")).upper()
                if tier == "TIER 1" or tier == "CRITICAL":
                    impact_score = 8.5
                elif tier == "TIER 2" or tier == "HIGH":
                    impact_score = 7.0
                elif tier == "TIER 3" or tier == "MEDIUM":
                    impact_score = 5.5
                else:
                    impact_score = 4.0 if dollar_impact < 5000 else 6.5

            # Effort score (1 to 10)
            raw_effort_str = str(rec.get("implementation_effort") or "Medium").strip().lower()
            effort_score = effort_map.get(raw_effort_str, 5.0)
            effort_display = raw_effort_str.capitalize()

            # Quadrant allocation
            if effort_score < 5.0 and impact_score >= 5.0:
                quadrant = "Quick Wins"
            elif effort_score >= 5.0 and impact_score >= 5.0:
                quadrant = "Strategic Bets"
            elif effort_score < 5.0 and impact_score < 5.0:
                quadrant = "Fill-ins"
            else:
                quadrant = "Re-evaluate"

            quadrant_counts[quadrant] += 1

            timeframe = str(rec.get("timeframe") or rec.get("urgency") or "Medium-term")
            finding_text = str(rec.get("rationale") or rec.get("mechanism_of_action") or "Empirical variance reduction")

            items.append(DecisionImpactItem(
                recommendation_id=rec_id,
                action_title=action_title,
                expected_impact_dollars=round(dollar_impact, 2),
                impact_score=round(impact_score, 1),
                effort_score=round(effort_score, 1),
                implementation_effort=effort_display,
                timeframe=timeframe,
                quadrant=quadrant,
                supporting_finding=finding_text
            ))

        # ECharts specification: 2D Scatter with MarkAreas
        scatter_data = []
        for item in items:
            color = "#10B981" if item.quadrant == "Quick Wins" else \
                    "#3B82F6" if item.quadrant == "Strategic Bets" else \
                    "#F59E0B" if item.quadrant == "Fill-ins" else "#EF4444"
            scatter_data.append({
                "name": item.action_title,
                "value": [item.effort_score, item.impact_score],
                "itemStyle": {"color": color},
                "symbolSize": 18,
                "quadrant": item.quadrant,
                "impact_dollars": item.expected_impact_dollars,
                "effort": item.implementation_effort
            })

        echarts_spec = {
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}<br/>Quadrant: {c}<br/>Effort: {d}"
            },
            "grid": {"left": "8%", "right": "8%", "bottom": "12%", "top": "12%"},
            "xAxis": {
                "type": "value",
                "min": 0,
                "max": 10,
                "name": "Implementation Effort (Low → High)",
                "nameLocation": "middle",
                "nameGap": 30,
                "splitLine": {"lineStyle": {"type": "dashed", "color": "#E2E8F0"}}
            },
            "yAxis": {
                "type": "value",
                "min": 0,
                "max": 10,
                "name": "Business Impact (Low → High)",
                "nameLocation": "middle",
                "nameGap": 30,
                "splitLine": {"lineStyle": {"type": "dashed", "color": "#E2E8F0"}}
            },
            "series": [
                {
                    "type": "scatter",
                    "data": scatter_data,
                    "markLine": {
                        "silent": True,
                        "lineStyle": {"color": "#94A3B8", "type": "solid", "width": 1.5},
                        "data": [{"xAxis": 5.0}, {"yAxis": 5.0}]
                    }
                }
            ]
        }

        # Executive narrative synthesis
        quick_wins = quadrant_counts.get("Quick Wins", 0)
        strat_bets = quadrant_counts.get("Strategic Bets", 0)
        total_recs = len(items)

        summary_parts = []
        if quick_wins > 0:
            summary_parts.append(f"{quick_wins} Quick Win{'s' if quick_wins > 1 else ''} yielding rapid ROI with low implementation complexity")
        if strat_bets > 0:
            summary_parts.append(f"{strat_bets} Strategic Bet{'s' if strat_bets > 1 else ''} delivering high organizational transformation requiring structured execution")
        
        if summary_parts:
            exec_summary = f"Portfolio analysis across {total_recs} recommendations identified " + " and ".join(summary_parts) + "."
        else:
            exec_summary = f"Evaluated {total_recs} managerial recommendations across implementation effort and expected business impact."

        return DecisionImpactMatrixResponse(
            items=items,
            quadrant_counts=quadrant_counts,
            echarts_spec=echarts_spec,
            executive_summary=exec_summary
        )
