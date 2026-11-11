from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from app.services.semantic_metrics import SemanticMetricDetector
from app.services.data_ingestion import IngestionService
from app.services.temporal_helper import TemporalHelper


class DatasetCapabilities(BaseModel):
    domain: str
    domain_label: str
    entity_label: str
    date_col: Optional[str] = None
    has_valid_dates: bool = False
    numeric_columns: List[str] = Field(default_factory=list)
    categorical_columns: List[str] = Field(default_factory=list)
    identifier_columns: List[str] = Field(default_factory=list)
    metric_units: Dict[str, str] = Field(default_factory=dict)
    primary_metric: Optional[str] = None
    primary_category: Optional[str] = None
    
    # Page 1: Business Overview capabilities
    can_calculate_health_score: bool = False
    health_score_unsupported_reason: Optional[str] = None
    overview_chart_type: str = "none"  # "time_series", "category_comparison", "distribution", "scatter", "none"
    
    # Page 2: Possible Reasons / Contribution capabilities
    has_valid_contribution_baseline: bool = False
    contribution_unsupported_reason: Optional[str] = None
    reasons_alternative_type: str = "limitation"  # "category_comparison", "metric_distribution", "descriptive_insights", "limitation"
    
    # Page 3: What-If Analysis capabilities
    can_simulate_scenarios: bool = False
    supported_scenarios: List[str] = Field(default_factory=list)
    scenario_unsupported_reason: Optional[str] = None
    
    # Page 3: Forecasting capabilities
    can_forecast: bool = False
    forecast_unsupported_reason: Optional[str] = None
    forecast_alternative_type: str = "none"  # "category_comparison", "distribution", "none"
    
    analytical_limitations: List[str] = Field(default_factory=list)


class DatasetCapabilityAssessor:
    """
    Centralized, deterministic capability assessment layer shared across:
    - Business Overview (health score calculation, timeline vs alternative charts)
    - Possible Reasons (contribution analysis validity vs category comparison / distribution)
    - What-If Analysis (domain-specific scenario levers and forecast validation)
    """

    @classmethod
    def assess_capabilities(
        cls,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None
    ) -> DatasetCapabilities:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return DatasetCapabilities(
                domain="general",
                domain_label="General Analytics",
                entity_label="Records",
                has_valid_dates=False,
                can_calculate_health_score=False,
                health_score_unsupported_reason="Dataset is empty.",
                has_valid_contribution_baseline=False,
                contribution_unsupported_reason="Dataset is empty.",
                can_simulate_scenarios=False,
                scenario_unsupported_reason="Dataset is empty.",
                can_forecast=False,
                forecast_unsupported_reason="Dataset is empty.",
                analytical_limitations=["Empty dataset provided."]
            )

        total_rows = len(df)
        cols = list(df.columns)

        # 1. Date Detection & Temporal Validation
        # Strict exclusion of durations, counters, and epoch bounds
        detected_date = SemanticMetricDetector._detect_date_column(df, explicit_col=date_col)
        has_valid_dates = False
        unique_periods_count = 0
        if detected_date and detected_date in df.columns:
            try:
                date_s = pd.to_datetime(df[detected_date], format="mixed", errors="coerce").dropna()
                if len(date_s) >= 2:
                    valid_years = date_s.dt.year
                    if len(valid_years) > 0 and 1980 <= valid_years.min() and valid_years.max() <= 2060:
                        has_valid_dates = True
                        unique_periods_count = int(date_s.dt.to_period("M").nunique())
                        if unique_periods_count < 2:
                            unique_periods_count = int(date_s.dt.to_period("D").nunique())
            except Exception:
                has_valid_dates = False

        # 2. Column Categorization
        identifier_cols = []
        numeric_cols = []
        categorical_cols = []
        metric_units = {}

        for col in cols:
            series = df[col]
            if IngestionService.is_identifier_column(col, series):
                identifier_cols.append(col)
                continue

            if pd.api.types.is_numeric_dtype(series):
                numeric_cols.append(col)
                metric_units[col] = SemanticMetricDetector.infer_column_unit(col, series)
            else:
                nu = int(series.nunique())
                if 2 <= nu <= 60:
                    categorical_cols.append(col)

        # 3. Domain Detection (with Financial domain support)
        domain_info = SemanticMetricDetector.detect_domain(df)
        domain = domain_info["domain"]
        domain_label = domain_info["domain_label"]
        entity_label = domain_info["entity_label"]

        # Check for financial domain if classified as general or retail
        if domain in ["general", "retail"]:
            fin_keywords = ["balance", "interest_rate", "loan", "deposit", "credit", "asset", "liability", "principal", "portfolio", "euribor", "cons.price.idx"]
            cols_lower = [str(c).strip().lower() for c in cols]
            fin_matches = sum(1 for c in cols_lower if any(k in c for k in fin_keywords))
            if fin_matches >= 2:
                domain = "financial"
                domain_label = "Banking & Financial Services"
                entity_label = "Transactions / Accounts"

        # 4. Primary Metric & Primary Category Selection
        primary_metric = None
        if target_col and target_col in df.columns and pd.api.types.is_numeric_dtype(df[target_col]):
            primary_metric = target_col
        elif numeric_cols:
            # Pick domain-optimal or highest-variance numeric column
            detected = SemanticMetricDetector.detect_metrics(df)
            if detected.get("primary_metric") and detected["primary_metric"] in numeric_cols:
                primary_metric = detected["primary_metric"]
            else:
                primary_metric = numeric_cols[0]

        primary_category = None
        if categorical_cols:
            # Prefer standard dimension names
            pref_cats = ["department", "category", "sub_category", "segment", "jobrole", "facility", "plant", "type", "region", "status"]
            for pref in pref_cats:
                match = next((c for c in categorical_cols if pref in str(c).lower()), None)
                if match:
                    primary_category = match
                    break
            if not primary_category:
                primary_category = categorical_cols[0]

        # 5. Page 1: Health Score & Overview Visualization Capabilities
        # Health score strictly requires chronological dates to evaluate dynamic performance trajectories
        can_calculate_health_score = bool(has_valid_dates and total_rows >= 10 and primary_metric)
        health_score_reason = None
        if not can_calculate_health_score:
            if not has_valid_dates:
                health_score_reason = "Health score unavailable for this dataset: lacks chronological timestamps to evaluate dynamic trajectories."
            else:
                health_score_reason = "Health score unavailable for this dataset: insufficient observations or missing performance metrics."

        if has_valid_dates:
            overview_chart_type = "time_series"
        elif primary_category and primary_metric:
            overview_chart_type = "category_comparison"
        elif len(numeric_cols) >= 2:
            overview_chart_type = "scatter"
        elif primary_metric:
            overview_chart_type = "distribution"
        else:
            overview_chart_type = "none"

        # 6. Page 2: Contribution / Pareto Capabilities
        # Valid contribution requires:
        # - An additive numeric metric with loss/drag or baseline variance (e.g. negative profit, scrap cost, downtime, defect count, attrition)
        # - At least one categorical column with >= 2 distinct groups
        has_valid_contribution = False
        contribution_reason = None
        reasons_alt_type = "limitation"

        if categorical_cols and primary_metric:
            # Check if metric has negative values or domain loss characteristics
            s = df[primary_metric].dropna()
            has_losses = (s < 0).any()
            is_loss_metric = any(k in str(primary_metric).lower() for k in ["loss", "scrap", "defect", "downtime", "cost", "attrition", "churn", "error", "delay"])
            # If dataset has dates, variance from baseline can form a valid contribution
            if has_valid_dates or has_losses or is_loss_metric:
                has_valid_contribution = True
            else:
                # Undated positive volume or general metric: Pareto is artificial; use Category Comparison
                has_valid_contribution = False
                contribution_reason = "Contribution analysis requires an additive loss, variance, or drag metric with baseline targets."
                reasons_alt_type = "category_comparison"
        elif primary_metric:
            has_valid_contribution = False
            contribution_reason = "Dataset lacks categorical dimensions to segment factor contributions."
            reasons_alt_type = "metric_distribution"
        else:
            has_valid_contribution = False
            contribution_reason = "No numerical performance metrics or categorical dimensions found."
            reasons_alt_type = "limitation"

        # 7. Page 3: What-If Scenario Simulation Capabilities
        supported_scenarios = []
        can_simulate_scenarios = False
        scenario_reason = None

        cols_lower = [str(col).lower() for col in df.columns]
        def has_col_kw(keywords: List[str]) -> bool:
            return any(any(kw in col for col in cols_lower) for kw in keywords)

        if domain == "retail":
            if has_col_kw(["sales", "revenue", "price", "amount"]):
                supported_scenarios.extend(["Price Change", "Sales Volume Change"])
            if has_col_kw(["cost", "profit", "cogs"]):
                supported_scenarios.append("Operating Cost Reduction")
            if has_col_kw(["discount", "rebate", "markdown"]):
                supported_scenarios.append("Discount Change")
        elif domain == "workforce":
            if has_col_kw(["attrition", "churn", "left", "turnover"]):
                supported_scenarios.append("Attrition Reduction")
            if has_col_kw(["satisfaction", "engagement"]):
                supported_scenarios.append("Satisfaction Improvement")
            if has_col_kw(["training", "development"]):
                supported_scenarios.append("Training & Skill Development")
        elif domain == "manufacturing":
            if has_col_kw(["defect", "scrap", "error"]):
                supported_scenarios.append("Defect Rate Reduction")
            if has_col_kw(["downtime", "idle"]):
                supported_scenarios.append("Downtime Reduction")
            if has_col_kw(["cycle_time", "lead_time"]):
                supported_scenarios.append("Cycle Time Optimization")
        elif domain == "saas":
            if has_col_kw(["churn", "retention"]):
                supported_scenarios.append("Churn Rate Reduction")
            if has_col_kw(["expansion", "arpu", "upsell", "arr"]):
                supported_scenarios.append("Account Expansion / ARPU Uplift")
        elif domain == "financial":
            if has_col_kw(["balance", "loan", "deposit", "volume"]):
                supported_scenarios.append("Asset Volume Growth")
            if has_col_kw(["interest", "fee", "rate"]):
                supported_scenarios.append("Fee / Interest Optimization")
        elif domain == "general":
            if primary_metric:
                supported_scenarios.append(f"{primary_metric.replace('_', ' ').title()} Adjustment")

        if supported_scenarios:
            can_simulate_scenarios = True
        else:
            can_simulate_scenarios = False
            scenario_reason = "What-If scenario simulation is unavailable for this dataset because required decision levers and controllable outcome variables were not detected."

        # 8. Page 3: Forecasting Capabilities
        can_forecast = bool(has_valid_dates and unique_periods_count >= 6 and primary_metric)
        forecast_reason = None
        if not can_forecast:
            if not has_valid_dates:
                forecast_reason = "Forecasting requires sequential time series data with a recognized chronological date field."
            elif unique_periods_count < 6:
                forecast_reason = f"Insufficient historical periods for reliable forecasting (at least 6 periods required; found {unique_periods_count})."
            else:
                forecast_reason = "No continuous numeric metric found for time-series projection."

        if not can_forecast:
            if primary_category and primary_metric:
                forecast_alt_type = "category_comparison"
            elif primary_metric:
                forecast_alt_type = "distribution"
            else:
                forecast_alt_type = "none"
        else:
            forecast_alt_type = "none"

        # 9. Analytical Limitations Summary
        analytical_limitations = []
        if not has_valid_dates:
            analytical_limitations.append("Chronological timestamps are absent; temporal trends and multi-period forecasting are unsupported.")
        if not can_calculate_health_score:
            analytical_limitations.append("Composite health score is unavailable due to lack of dynamic historical baselines.")
        if not has_valid_contribution:
            analytical_limitations.append("Contribution Pareto analysis is unavailable; displaying descriptive category comparison or distribution instead.")
        if not can_simulate_scenarios:
            analytical_limitations.append("Scenario simulation is unsupported due to absence of controllable operational levers.")

        return DatasetCapabilities(
            domain=domain,
            domain_label=domain_label,
            entity_label=entity_label,
            date_col=detected_date if has_valid_dates else None,
            has_valid_dates=has_valid_dates,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            identifier_columns=identifier_cols,
            metric_units=metric_units,
            primary_metric=primary_metric,
            primary_category=primary_category,
            can_calculate_health_score=can_calculate_health_score,
            health_score_unsupported_reason=health_score_reason,
            overview_chart_type=overview_chart_type,
            has_valid_contribution_baseline=has_valid_contribution,
            contribution_unsupported_reason=contribution_reason,
            reasons_alternative_type=reasons_alt_type,
            can_simulate_scenarios=can_simulate_scenarios,
            supported_scenarios=supported_scenarios,
            scenario_unsupported_reason=scenario_reason,
            can_forecast=can_forecast,
            forecast_unsupported_reason=forecast_reason,
            forecast_alternative_type=forecast_alt_type,
            analytical_limitations=analytical_limitations
        )
