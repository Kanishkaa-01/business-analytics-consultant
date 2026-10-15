import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

from app.models.schemas import (
    ForecastReport,
    ForecastModelResult,
    ForecastValidationMetrics,
    ForecastPoint,
    HistoricalPoint,
    ForecastCompareResponse,
    ForecastCompareItem,
)


class ForecastingEngine:
    """
    Phase 16: Deterministic, Explainable Forecasting Engine.
    Provides Moving Average, Linear Trend (OLS), and Simple Exponential Smoothing.
    Strictly deterministic calculations, transparent confidence bands, and graceful fallbacks.
    """

    @staticmethod
    def _detect_date_column(df: pd.DataFrame, explicit_date_col: Optional[str] = None) -> Optional[str]:
        """Detect parseable date/time column."""
        if explicit_date_col and explicit_date_col in df.columns:
            return explicit_date_col

        # Check existing datetime dtypes
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col

        # Check common date keywords in column names
        date_keywords = ["date", "period", "time", "month", "year", "timestamp", "quarter", "day"]
        for col in df.columns:
            low = col.lower()
            if any(k in low for k in date_keywords):
                # Verify that it can be parsed as datetime
                try:
                    sample = df[col].dropna().head(10)
                    if not sample.empty:
                        parsed = pd.to_datetime(sample, format="mixed", errors="coerce")
                        if parsed.notna().sum() >= len(sample) * 0.7:
                            return col
                except Exception:
                    pass

        # Try parsing any object/string column with reasonable cardinality
        for col in df.select_dtypes(include=["object", "string"]).columns:
            try:
                sample = df[col].dropna().head(10)
                if not sample.empty:
                    parsed = pd.to_datetime(sample, format="mixed", errors="coerce")
                    if parsed.notna().sum() >= len(sample) * 0.8:
                        return col
            except Exception:
                pass

        return None

    @staticmethod
    def _calculate_validation_metrics(actual: List[float], predicted: List[float]) -> ForecastValidationMetrics:
        """Computes MAE, RMSE, and MAPE between actual and predicted vectors."""
        if not actual or not predicted or len(actual) != len(predicted):
            return ForecastValidationMetrics(mae=0.0, rmse=0.0, mape=0.0)

        n = len(actual)
        errors = [a - p for a, p in zip(actual, predicted)]
        abs_errors = [abs(e) for e in errors]
        sq_errors = [e ** 2 for e in errors]

        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(sq_errors) / n)

        # MAPE calculation (guarding against division by zero)
        pct_errors = []
        for a, p in zip(actual, predicted):
            if abs(a) > 1e-6:
                pct_errors.append(abs((a - p) / a) * 100.0)
            else:
                pct_errors.append(0.0)
        mape = sum(pct_errors) / n if pct_errors else 0.0

        return ForecastValidationMetrics(
            mae=round(mae, 2),
            rmse=round(rmse, 2),
            mape=round(mape, 2)
        )

    @classmethod
    def generate_forecast(
        cls,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None,
        horizon: int = 3,
        selected_model_type: Optional[str] = None
    ) -> ForecastReport:
        """
        Main entry point for Phase 16 Forecasting.
        Suitability detection, deterministic model execution, validation, and explainable reporting.
        """
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return ForecastReport(
                is_available=False,
                reason="Forecasting is not available because the dataset is empty."
            )

        # 1. Detect target numeric column
        from app.services.data_ingestion import IngestionService

        # If target is estimated_transaction_value and not yet present, derive it
        if target_col == "estimated_transaction_value" and "estimated_transaction_value" not in df.columns:
            qty_col = next((c for c in df.columns if c.lower() == "quantity"), None)
            price_col = next((c for c in df.columns if c.lower() in ["unitprice", "unit_price", "price"]), None)
            if qty_col and price_col:
                df = df.copy()
                df["estimated_transaction_value"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) * pd.to_numeric(df[price_col], errors="coerce").fillna(0)

        if not target_col or target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            # Check if we can derive estimated_transaction_value
            qty_col = next((c for c in df.columns if c.lower() == "quantity"), None)
            price_col = next((c for c in df.columns if c.lower() in ["unitprice", "unit_price", "price"]), None)
            if qty_col and price_col and "estimated_transaction_value" not in df.columns:
                df = df.copy()
                df["estimated_transaction_value"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) * pd.to_numeric(df[price_col], errors="coerce").fillna(0)
                target_col = "estimated_transaction_value"
            else:
                num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not IngestionService.is_identifier_column(c, df[c])]
                if not num_cols:
                    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                if not num_cols:
                    return ForecastReport(
                        is_available=False,
                        reason="Forecasting is not available because no numeric metric was found."
                    )
                priority_names = ["estimated_transaction_value", "revenue", "sales", "total_amount", "amount", "turnover", "gmv", "quantity"]
                target_col = next((c for p in priority_names for c in num_cols if p in c.lower()), num_cols[0])

        metric_label = target_col.replace('_', ' ').title()

        # 2. Detect date column
        detected_date_col = cls._detect_date_column(df, date_col)
        if not detected_date_col:
            return ForecastReport(
                is_available=False,
                metric_name=metric_label,
                reason="Forecasting is not available for this dataset because no time dimension was detected."
            )

        # 3. Clean and parse date series
        try:
            df_time = df[[detected_date_col, target_col]].dropna().copy()
            df_time[detected_date_col] = pd.to_datetime(df_time[detected_date_col], format="mixed", errors="coerce")
            df_time = df_time.dropna(subset=[detected_date_col])
        except Exception:
            return ForecastReport(
                is_available=False,
                metric_name=metric_label,
                reason="Could not parse historical date values in the detected time column."
            )

        if df_time.empty:
            return ForecastReport(
                is_available=False,
                metric_name=metric_label,
                reason="No valid historical date observations found."
            )

        # 4. Frequency detection and aggregation
        # Fast aggregation using PeriodIndex (avoids sorting 500k+ rows or full string conversions)
        period_series = df_time[detected_date_col].dt.to_period("M")
        unique_months = period_series.nunique()

        if unique_months >= 6:
            frequency = "monthly"
            dt_fmt = "%Y-%m"
            offset = pd.DateOffset(months=1)
            grouped = df_time.groupby(period_series)[target_col].sum().reset_index()
            grouped = grouped.sort_values(by=detected_date_col)
            periods = [str(p) for p in grouped[detected_date_col]]
        else:
            frequency = "daily"
            dt_fmt = "%Y-%m-%d"
            offset = pd.DateOffset(days=1)
            day_series = df_time[detected_date_col].dt.to_period("D")
            grouped = df_time.groupby(day_series)[target_col].sum().reset_index()
            grouped = grouped.sort_values(by=detected_date_col)
            periods = [str(p) for p in grouped[detected_date_col]]

        y_values = [float(v) for v in grouped[target_col]]
        n = len(y_values)

        # Constraint check: minimum 6 observations required
        if n < 6:
            return ForecastReport(
                is_available=False,
                metric_name=metric_label,
                reason=f"Not enough historical data points for reliable forecasting (at least 6 periods required; found {n})."
            )

        historical_series = [
            HistoricalPoint(period=str(p), value=round(val, 2))
            for p, val in zip(periods, y_values)
        ]

        # 5. Generate future period labels
        horizon = max(1, min(12, int(horizon or 3)))
        last_dt = pd.to_datetime(periods[-1])
        future_periods: List[str] = []
        curr_dt = last_dt
        for _ in range(horizon):
            curr_dt = curr_dt + offset
            future_periods.append(curr_dt.strftime(dt_fmt))

        # 6. Train/Test Holdout Split for Deterministic Validation
        # Use last k periods for testing (at least 2, at most 3)
        k_test = max(2, min(3, n // 3))
        train_y = y_values[:-k_test]
        test_y = y_values[-k_test:]
        n_train = len(train_y)

        # -------------------------------------------------------------
        # Model 1: Linear Trend (OLS Regression)
        # -------------------------------------------------------------
        # Validation fit
        t_train = np.arange(n_train)
        slope_v, intercept_v, _, _, _ = stats.linregress(t_train, train_y)
        test_pred_linear = [float(intercept_v + slope_v * (n_train + i)) for i in range(k_test)]
        val_metrics_linear = cls._calculate_validation_metrics(test_y, test_pred_linear)

        # Full fit
        t_full = np.arange(n)
        slope_f, intercept_f, r_val, p_val, std_err = stats.linregress(t_full, y_values)
        r_squared = round(float(r_val ** 2), 3) if not math.isnan(r_val) else 0.0

        # Residual standard error
        residuals_lin = [y_values[i] - (intercept_f + slope_f * i) for i in range(n)]
        s_e = math.sqrt(sum(r ** 2 for r in residuals_lin) / max(1, n - 2))
        t_mean = float(np.mean(t_full))
        ss_t = sum((ti - t_mean) ** 2 for ti in t_full)

        forecast_points_linear: List[ForecastPoint] = []
        for h_step in range(horizon):
            t_future = n + h_step
            y_hat = intercept_f + slope_f * t_future
            leverage = 1.0 + (1.0 / n) + ((t_future - t_mean) ** 2 / max(1e-6, ss_t))
            margin = 1.96 * s_e * math.sqrt(leverage)
            lower_b = max(0.0, round(y_hat - margin, 2)) if min(y_values) >= 0 else round(y_hat - margin, 2)
            upper_b = round(y_hat + margin, 2)
            forecast_points_linear.append(ForecastPoint(
                period=future_periods[h_step],
                value=round(y_hat, 2),
                lower_bound=lower_b,
                upper_bound=upper_b
            ))

        linear_model = ForecastModelResult(
            model_name="Linear Trend (OLS)",
            model_type="linear",
            parameters={
                "slope": round(float(slope_f), 2),
                "intercept": round(float(intercept_f), 2),
                "r_squared": r_squared,
                "residual_std_error": round(float(s_e), 2)
            },
            validation_metrics=val_metrics_linear,
            forecast_points=forecast_points_linear,
            description=f"Fits an Ordinary Least Squares linear trend line (R² = {r_squared:.2f}, Slope = {slope_f:+,.2f}/period)."
        )

        # -------------------------------------------------------------
        # Model 2: Moving Average (Window = 3)
        # -------------------------------------------------------------
        window = min(3, n - 1)
        # Validation fit
        test_pred_ma: List[float] = []
        sim_buffer = list(train_y)
        for _ in range(k_test):
            next_val = float(np.mean(sim_buffer[-window:]))
            test_pred_ma.append(next_val)
            sim_buffer.append(next_val)
        val_metrics_ma = cls._calculate_validation_metrics(test_y, test_pred_ma)

        # Historical residuals for MA confidence band
        ma_residuals = []
        for i in range(window, n):
            pred_hist = float(np.mean(y_values[i - window:i]))
            ma_residuals.append(y_values[i] - pred_hist)
        s_ma = float(np.std(ma_residuals)) if ma_residuals else (s_e or 1.0)

        # Full forecast
        forecast_points_ma: List[ForecastPoint] = []
        full_buffer = list(y_values)
        for h_step in range(horizon):
            next_ma = float(np.mean(full_buffer[-window:]))
            full_buffer.append(next_ma)
            margin = 1.96 * s_ma * math.sqrt(h_step + 1)
            lower_b = max(0.0, round(next_ma - margin, 2)) if min(y_values) >= 0 else round(next_ma - margin, 2)
            upper_b = round(next_ma + margin, 2)
            forecast_points_ma.append(ForecastPoint(
                period=future_periods[h_step],
                value=round(next_ma, 2),
                lower_bound=lower_b,
                upper_bound=upper_b
            ))

        ma_model = ForecastModelResult(
            model_name=f"Moving Average ({window}-Period)",
            model_type="moving_average",
            parameters={
                "window_size": window,
                "residual_std_dev": round(s_ma, 2)
            },
            validation_metrics=val_metrics_ma,
            forecast_points=forecast_points_ma,
            description=f"Computes rolling {window}-period simple moving average with widening confidence interval."
        )

        # -------------------------------------------------------------
        # Model 3: Simple Exponential Smoothing (Alpha = 0.3)
        # -------------------------------------------------------------
        alpha = 0.3
        # Validation fit
        level_v = train_y[0]
        for v in train_y[1:]:
            level_v = alpha * v + (1.0 - alpha) * level_v
        test_pred_ses = [level_v for _ in range(k_test)]
        val_metrics_ses = cls._calculate_validation_metrics(test_y, test_pred_ses)

        # Full fit
        level_f = y_values[0]
        ses_fitted = [level_f]
        for v in y_values[1:]:
            level_f = alpha * v + (1.0 - alpha) * level_f
            ses_fitted.append(level_f)

        ses_residuals = [y - f for y, f in zip(y_values, ses_fitted)]
        s_ses = float(np.std(ses_residuals)) if ses_residuals else (s_e or 1.0)

        forecast_points_ses: List[ForecastPoint] = []
        for h_step in range(horizon):
            margin = 1.96 * s_ses * math.sqrt(1.0 + h_step * (alpha ** 2))
            lower_b = max(0.0, round(level_f - margin, 2)) if min(y_values) >= 0 else round(level_f - margin, 2)
            upper_b = round(level_f + margin, 2)
            forecast_points_ses.append(ForecastPoint(
                period=future_periods[h_step],
                value=round(level_f, 2),
                lower_bound=lower_b,
                upper_bound=upper_b
            ))

        ses_model = ForecastModelResult(
            model_name="Exponential Smoothing (α=0.3)",
            model_type="exponential_smoothing",
            parameters={
                "alpha": alpha,
                "final_level": round(level_f, 2),
                "residual_std_dev": round(s_ses, 2)
            },
            validation_metrics=val_metrics_ses,
            forecast_points=forecast_points_ses,
            description="Applies recursive exponential weighting (α=0.3) giving recent observations higher priority."
        )

        models = [linear_model, ma_model, ses_model]

        # 7. Model Selection (Lowest MAPE, tie-break by RMSE)
        models_sorted = sorted(models, key=lambda m: (m.validation_metrics.mape, m.validation_metrics.rmse))
        best_model = models_sorted[0]
        for m in models:
            m.is_recommended = (m.model_type == best_model.model_type)

        # 8. Trajectory Narrative
        last_hist_val = y_values[-1]
        rec_final_proj = best_model.forecast_points[-1].value
        proj_delta = rec_final_proj - last_hist_val
        proj_pct = round((proj_delta / max(1.0, abs(last_hist_val))) * 100, 1) if last_hist_val != 0 else 0.0
        direction_word = "grow" if proj_delta > 0 else "decline" if proj_delta < 0 else "remain stable"

        narrative = (
            f"Based on the recommended {best_model.model_name} (Holdout MAPE: {best_model.validation_metrics.mape:.1f}%), "
            f"{metric_label} is projected to {direction_word} by {abs(proj_pct):.1f}% over the next {horizon} {frequency} periods "
            f"(from ${last_hist_val:,.2f} to ${rec_final_proj:,.2f}). "
            f"Confidence bounds widen across the horizon, with the final period expected between "
            f"${best_model.forecast_points[-1].lower_bound:,.2f} and ${best_model.forecast_points[-1].upper_bound:,.2f}."
        )

        return ForecastReport(
            is_available=True,
            metric_name=metric_label,
            frequency=frequency,
            horizon_periods=horizon,
            historical_series=historical_series,
            models=models,
            recommended_model=best_model.model_type,
            trajectory_narrative=narrative
        )

    @classmethod
    def compare_forecast_vs_actual(
        cls,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None,
        horizon: int = 3,
        model_type: Optional[str] = None
    ) -> ForecastCompareResponse:
        """
        Holdout backtesting: evaluates deterministic statistical forecasts against
        empirical actuals for the final holdout periods.
        """
        # First generate standard forecast
        rep = cls.generate_forecast(df, target_col, date_col, horizon, model_type)
        if not rep.is_available or not rep.historical_series:
            return ForecastCompareResponse(
                metric=target_col or "Metric",
                model_name=model_type or "Linear Trend",
                horizon=horizon,
                comparison=[],
                accuracy_summary={"error": rep.reason or "Historical series unavailable."},
                insights=["Insufficient historical periods to perform holdout comparison."],
                echarts_spec={}
            )

        hist = rep.historical_series
        n = len(hist)
        k_test = max(2, min(horizon, n // 3))
        
        train_pts = hist[:-k_test]
        test_pts = hist[-k_test:]

        train_y = [p.value for p in train_pts]
        test_y = [p.value for p in test_pts]
        n_train = len(train_y)

        # Fit selected model
        m_type = model_type or rep.recommended_model or "linear"
        if m_type == "moving_average":
            model_name = "Moving Average (3-Period)"
            k_ma = min(3, n_train)
            ma_val = sum(train_y[-k_ma:]) / k_ma
            preds = [ma_val for _ in range(k_test)]
            residuals = [y - ma_val for y in train_y[-k_ma:]]
            std_err = float(np.std(residuals)) if residuals else 1.0
        elif m_type == "exponential_smoothing":
            model_name = "Exponential Smoothing (α=0.3)"
            alpha = 0.3
            lvl = train_y[0]
            for v in train_y[1:]:
                lvl = alpha * v + (1.0 - alpha) * lvl
            preds = [lvl for _ in range(k_test)]
            std_err = float(np.std(train_y)) * 0.5 if len(train_y) > 1 else 1.0
        else:
            model_name = "Linear Trend (OLS)"
            m_type = "linear"
            t_train = np.arange(n_train)
            slope, intercept, _, _, _ = stats.linregress(t_train, train_y)
            preds = [float(intercept + slope * (n_train + i)) for i in range(k_test)]
            residuals = [train_y[i] - (intercept + slope * i) for i in range(n_train)]
            std_err = float(np.std(residuals)) if residuals else 1.0

        # Build comparison items
        comparison_items: List[ForecastCompareItem] = []
        errors = []
        pct_errors = []
        within_ci_count = 0

        for i, t_pt in enumerate(test_pts):
            act_val = t_pt.value
            pred_val = round(preds[i], 2)
            margin = 1.96 * std_err * math.sqrt(1.0 + (i * 0.1))
            lb = max(0.0, pred_val - margin) if min(train_y) >= 0 else pred_val - margin
            ub = pred_val + margin

            variance = round(act_val - pred_val, 2)
            var_pct = round((variance / pred_val * 100), 2) if pred_val != 0 else 0.0
            in_ci = (lb <= act_val <= ub)
            if in_ci:
                within_ci_count += 1

            errors.append(abs(variance))
            if abs(act_val) > 1e-6:
                pct_errors.append(abs(variance / act_val) * 100)

            comparison_items.append(ForecastCompareItem(
                period=t_pt.period,
                actual=act_val,
                forecast=pred_val,
                variance=variance,
                variance_pct=var_pct,
                in_confidence_interval=in_ci
            ))

        mae = round(sum(errors) / len(errors), 2) if errors else 0.0
        mape = round(sum(pct_errors) / len(pct_errors), 1) if pct_errors else 0.0
        ci_pct = round((within_ci_count / len(test_pts)) * 100, 1) if test_pts else 0.0

        # Insights
        insights = [
            f"Tested on {k_test} periods using {model_name}. "
            f"Average forecast error: {mape:.1f}%. "
            f"{ci_pct:.0f}% of actual values were within the forecast uncertainty band."
        ]
        avg_var = sum([item.variance for item in comparison_items]) / len(comparison_items)
        if avg_var > 0:
            insights.append(f"Actual realization outperformed model projections by an average of ${avg_var:,.2f} per period.")
        elif avg_var < 0:
            insights.append(f"Actual realization trended below model projections by an average of ${abs(avg_var):,.2f} per period.")
        else:
            insights.append("Actual realization matched model projections exactly on average.")

        # ECharts specification
        all_periods = [p.period for p in hist]
        hist_actuals = [p.value for p in hist]
        
        # Forecast series for chart (None for train periods, then predicted)
        chart_forecast = [None] * (n - k_test) + [round(p, 2) for p in preds]

        echarts_spec = {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Actual", "Forecast"]},
            "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "12%", "containLabel": True},
            "xAxis": {"type": "category", "data": all_periods, "axisLabel": {"rotate": 25 if len(all_periods) > 6 else 0}},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": "Actual",
                    "type": "line",
                    "data": hist_actuals,
                    "itemStyle": {"color": "#3B82F6"},
                    "lineStyle": {"width": 3}
                },
                {
                    "name": "Forecast",
                    "type": "line",
                    "data": chart_forecast,
                    "itemStyle": {"color": "#F59E0B"},
                    "lineStyle": {"type": "dashed", "width": 3}
                }
            ]
        }

        return ForecastCompareResponse(
            metric=rep.metric_name or "Metric",
            model_name=model_name,
            horizon=k_test,
            comparison=comparison_items,
            accuracy_summary={
                "mae": mae,
                "mape": mape,
                "within_ci_percentage": ci_pct,
                "total_holdout_periods": k_test
            },
            insights=insights,
            echarts_spec=echarts_spec
        )

