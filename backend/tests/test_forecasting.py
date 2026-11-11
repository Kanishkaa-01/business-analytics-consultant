import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.engines.forecasting_engine import ForecastingEngine
from app.models.schemas import ForecastReport


@pytest.fixture
def monthly_sales_df():
    """Generates 12 months of deterministic sales data."""
    dates = pd.date_range(start="2025-01-01", periods=12, freq="MS")
    # Linear upward trend: 10000 + 1000 * i
    sales = [10000.0 + 1000.0 * i + (50.0 if i % 2 == 0 else -50.0) for i in range(12)]
    return pd.DataFrame({
        "order_date": dates,
        "revenue": sales,
        "region": ["North", "South"] * 6
    })


@pytest.fixture
def short_sales_df():
    """Generates only 4 periods of data (< 6 observations threshold)."""
    dates = pd.date_range(start="2025-01-01", periods=4, freq="MS")
    return pd.DataFrame({
        "order_date": dates,
        "revenue": [1000.0, 1100.0, 1200.0, 1300.0]
    })


@pytest.fixture
def non_temporal_df():
    """Generates dataset with no date or time columns."""
    return pd.DataFrame({
        "category": ["A", "B", "C", "D", "E", "F", "G"],
        "revenue": [100.0, 200.0, 150.0, 300.0, 250.0, 400.0, 350.0]
    })


def test_forecasting_suitability_no_date(non_temporal_df):
    """Forecasting must gracefully disable when no date column is present."""
    rep = ForecastingEngine.generate_forecast(non_temporal_df, target_col="revenue")
    assert rep.is_available is False
    assert "no time dimension" in rep.reason.lower()


def test_forecasting_suitability_short_history(short_sales_df):
    """Forecasting must gracefully disable when fewer than 6 observations exist."""
    rep = ForecastingEngine.generate_forecast(short_sales_df, target_col="revenue", date_col="order_date")
    assert rep.is_available is False
    assert "at least 6 periods required" in rep.reason.lower()


def test_forecasting_models_and_validation(monthly_sales_df):
    """Forecasting executes Linear Trend, Moving Average, and Exponential Smoothing with validation metrics."""
    rep = ForecastingEngine.generate_forecast(
        monthly_sales_df,
        target_col="revenue",
        date_col="order_date",
        horizon=3
    )

    assert rep.is_available is True
    assert len(rep.historical_series) == 12
    assert rep.horizon_periods == 3
    assert len(rep.models) == 3

    model_types = {m.model_type for m in rep.models}
    assert model_types == {"linear", "moving_average", "exponential_smoothing"}

    # Exactly one recommended model
    recommended = [m for m in rep.models if m.is_recommended]
    assert len(recommended) == 1
    assert rep.recommended_model == recommended[0].model_type

    # Verify linear model specifics
    linear_m = next(m for m in rep.models if m.model_type == "linear")
    assert len(linear_m.forecast_points) == 3
    assert linear_m.parameters["slope"] > 0
    assert linear_m.validation_metrics.mape >= 0.0

    # Bounds must surround predicted value
    for pt in linear_m.forecast_points:
        assert pt.lower_bound <= pt.value <= pt.upper_bound

    # Trajectory narrative must be populated
    assert rep.trajectory_narrative is not None
    assert "projected" in rep.trajectory_narrative.lower()


def test_forecasting_determinism(monthly_sales_df):
    """Calling forecast twice with same inputs must produce exact identical numbers."""
    rep1 = ForecastingEngine.generate_forecast(monthly_sales_df, target_col="revenue", horizon=4)
    rep2 = ForecastingEngine.generate_forecast(monthly_sales_df, target_col="revenue", horizon=4)

    assert rep1.is_available == rep2.is_available
    assert rep1.recommended_model == rep2.recommended_model
    for m1, m2 in zip(rep1.models, rep2.models):
        assert m1.model_type == m2.model_type
        assert m1.validation_metrics.mape == m2.validation_metrics.mape
        for p1, p2 in zip(m1.forecast_points, m2.forecast_points):
            assert p1.value == p2.value
            assert p1.lower_bound == p2.lower_bound
            assert p1.upper_bound == p2.upper_bound
