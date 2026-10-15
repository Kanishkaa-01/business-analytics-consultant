import pandas as pd
import numpy as np
from app.engines.advanced_findings import AdvancedFindingsEngine


def test_increasing_trend():
    df = pd.DataFrame({
        "period": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "revenue": [100.0, 115.0, 130.0, 150.0]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue", date_col="period")
    assert report.has_date_dimension is True
    assert len(report.trends) == 1
    trend = report.trends[0]
    assert trend.direction == "increasing"
    assert trend.growth_pct > 0
    assert trend.highest_period == "2025-01-04"
    assert "increasing pattern" in trend.summary_statement


def test_decreasing_trend():
    df = pd.DataFrame({
        "period": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "revenue": [200.0, 175.0, 150.0, 120.0]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue", date_col="period")
    assert len(report.trends) == 1
    trend = report.trends[0]
    assert trend.direction == "decreasing"
    assert trend.growth_pct < 0
    assert "decreasing pattern" in trend.summary_statement


def test_stable_trend():
    df = pd.DataFrame({
        "period": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "revenue": [100.0, 101.0, 99.5, 100.5]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue", date_col="period")
    assert len(report.trends) == 1
    assert report.trends[0].direction == "stable"


def test_anomalies_detected():
    # 20 regular values around 50, and 2 huge outliers
    values = [50.0 + i * 0.5 for i in range(20)] + [500.0, -100.0]
    df = pd.DataFrame({
        "revenue": values
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue")
    assert len(report.anomalies) >= 1
    assert any(a.observed_value == 500.0 for a in report.anomalies)
    assert any("unusually high" in a.statement for a in report.anomalies)


def test_no_anomalies():
    # Uniform values, no outliers
    df = pd.DataFrame({
        "revenue": [100.0, 101.0, 102.0, 99.0, 100.5, 101.5]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue")
    assert len(report.anomalies) == 0


def test_segment_comparisons():
    df = pd.DataFrame({
        "region": ["East", "East", "West", "West", "Central", "Central"],
        "category": ["A", "B", "A", "B", "A", "B"],
        "profit": [1000.0, 1200.0, 400.0, 450.0, 700.0, 750.0],
        "discount": [0.05, 0.06, 0.25, 0.28, 0.12, 0.10]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="profit", dimensions=["region", "category"])
    assert len(report.segment_comparisons) >= 1
    region_comp = next((c for c in report.segment_comparisons if c.dimension == "Region"), None)
    assert region_comp is not None
    assert region_comp.top_segment == "East"
    assert region_comp.bottom_segment == "West"
    assert region_comp.spread_pct > 0
    assert "highest observed" in region_comp.statement


def test_missing_date_column():
    df = pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0]
    })
    report = AdvancedFindingsEngine.analyze(df, target_col="revenue", date_col=None)
    assert report.has_date_dimension is False
    assert len(report.trends) == 0


def test_empty_and_insufficient_data():
    empty_df = pd.DataFrame()
    rep1 = AdvancedFindingsEngine.analyze(empty_df, target_col="revenue")
    assert len(rep1.trends) == 0
    assert len(rep1.anomalies) == 0

    single_row = pd.DataFrame({"revenue": [100.0]})
    rep2 = AdvancedFindingsEngine.analyze(single_row, target_col="revenue")
    assert len(rep2.trends) == 0
    assert "insufficient" in rep2.summary.lower()
