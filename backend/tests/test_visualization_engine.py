import pandas as pd
import numpy as np
from app.engines.visualization_engine import VisualizationEngine
from app.models.schemas import ChartSpecification


def test_categorical_to_bar():
    df = pd.DataFrame({
        "region": ["East", "West", "Central", "South", "North", "Midwest", "Pacific", "Mountain"],
        "revenue": [100.0, 150.0, 80.0, 95.0, 110.0, 75.0, 140.0, 85.0]
    })
    spec = VisualizationEngine.select_and_generate_chart(df, target_col="revenue", dimension_col="region")
    assert spec.available is True
    assert spec.chart_type == "bar"
    assert len(spec.data) == 8
    assert spec.x_axis_field == "category"
    assert spec.y_axis_field == "value"


def test_time_series_to_line():
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "sales": [500.0, 620.0, 480.0, 700.0]
    })
    spec = VisualizationEngine.select_and_generate_chart(df, target_col="sales", date_col="date")
    assert spec.available is True
    assert spec.chart_type == "line"
    assert len(spec.data) == 4
    assert spec.x_axis_field == "period"
    assert spec.y_axis_field == "value"


def test_composition_to_pie():
    df = pd.DataFrame({
        "channel": ["Online", "In-Store", "Wholesale"],
        "sales": [400.0, 350.0, 250.0]
    })
    spec = VisualizationEngine.select_and_generate_chart(
        df, target_col="sales", dimension_col="channel", is_part_to_whole=True
    )
    assert spec.available is True
    assert spec.chart_type == "pie"
    assert len(spec.data) == 3
    assert spec.x_axis_field == "name"
    assert spec.y_axis_field == "value"


def test_numeric_relationship_to_scatter():
    df = pd.DataFrame({
        "price": [10.0, 15.0, 20.0, 25.0, 30.0],
        "quantity": [100.0, 85.0, 70.0, 60.0, 40.0]
    })
    spec = VisualizationEngine.select_and_generate_chart(
        df, target_col="price", second_numeric_col="quantity"
    )
    assert spec.available is True
    assert spec.chart_type == "scatter"
    assert len(spec.data) == 5
    assert spec.x_axis_field == "price"
    assert spec.y_axis_field == "quantity"


def test_single_kpi():
    df = pd.DataFrame({
        "profit": [1000.0, 2000.0, 1500.0]
    })
    spec = VisualizationEngine.select_and_generate_chart(
        df, target_col="profit", is_single_kpi=True
    )
    assert spec.available is True
    assert spec.chart_type == "kpi"
    assert spec.kpi_value == 4500.0


def test_empty_dataset():
    df = pd.DataFrame()
    spec = VisualizationEngine.select_and_generate_chart(df)
    assert spec.available is False
    assert spec.chart_type == "none"
    assert "not available" in spec.empty_reason.lower()


def test_missing_columns_and_unsupported_structure():
    df = pd.DataFrame({"text_only": ["abc", "def", "ghi"]})
    spec = VisualizationEngine.select_and_generate_chart(df, target_col="missing_metric")
    assert spec.available is False
    assert spec.chart_type == "none"
    assert spec.empty_reason == "Visualization not available for this analysis."


def test_many_categories_avoids_pie():
    # 10 categories: even if is_part_to_whole is requested, should default to bar
    df = pd.DataFrame({
        "category": [f"Cat_{i}" for i in range(10)],
        "revenue": [float(i * 10 + 5) for i in range(10)]
    })
    spec = VisualizationEngine.select_and_generate_chart(
        df, target_col="revenue", dimension_col="category", is_part_to_whole=True
    )
    assert spec.available is True
    assert spec.chart_type == "bar"
