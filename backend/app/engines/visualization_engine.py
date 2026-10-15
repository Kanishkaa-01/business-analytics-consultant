from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from app.models.schemas import ChartSpecification


class VisualizationEngine:
    """
    Phase 11: Automatic Visualization Engine
    Deterministically recommends and generates Apache ECharts specifications
    based on the structure and semantics of the analytical data.
    """

    @staticmethod
    def select_and_generate_chart(
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        date_col: Optional[str] = None,
        dimension_col: Optional[str] = None,
        second_numeric_col: Optional[str] = None,
        is_part_to_whole: bool = False,
        is_single_kpi: bool = False,
        custom_title: Optional[str] = None,
    ) -> ChartSpecification:
        """
        Deterministically selects the most appropriate chart type and formats
        the data points for Apache ECharts rendering.
        """
        # 1. Validation: Empty or invalid DataFrame
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return ChartSpecification(
                chart_type="none",
                title="Visualization Unavailable",
                description="The provided dataset contains no records.",
                available=False,
                empty_reason="Visualization not available for this analysis."
            )

        # 2. Single KPI Card
        if is_single_kpi:
            if target_col and target_col in df.columns and pd.api.types.is_numeric_dtype(df[target_col]):
                kpi_val = float(df[target_col].sum())
                return ChartSpecification(
                    chart_type="kpi",
                    title=custom_title or f"Total {target_col.replace('_', ' ').title()}",
                    description=f"Aggregated sum of {target_col}",
                    kpi_value=round(kpi_val, 2),
                    kpi_label=target_col.replace('_', ' ').title(),
                    available=True
                )
            elif len(df.columns) == 1 and pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
                col_name = df.columns[0]
                kpi_val = float(df[col_name].sum())
                return ChartSpecification(
                    chart_type="kpi",
                    title=custom_title or f"Total {col_name.replace('_', ' ').title()}",
                    description=f"Aggregated sum of {col_name}",
                    kpi_value=round(kpi_val, 2),
                    kpi_label=col_name.replace('_', ' ').title(),
                    available=True
                )
            else:
                return ChartSpecification(
                    chart_type="none",
                    title="KPI Unavailable",
                    description="No numeric metric found for single KPI display.",
                    available=False,
                    empty_reason="Visualization not available for this analysis."
                )

        # Infer target column if not provided
        if not target_col or target_col not in df.columns or not pd.api.types.is_numeric_dtype(df[target_col]):
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if not num_cols:
                return ChartSpecification(
                    chart_type="none",
                    title="No Numeric Metrics Found",
                    description="The dataset does not contain numerical columns to visualize.",
                    available=False,
                    empty_reason="Visualization not available for this analysis."
                )
            target_col = num_cols[0]

        # 3. Two numerical variables -> Scatter Chart
        if second_numeric_col and second_numeric_col in df.columns and pd.api.types.is_numeric_dtype(df[second_numeric_col]):
            clean_df = df[[target_col, second_numeric_col]].dropna()
            if len(clean_df) >= 2:
                points = [
                    {"x": round(float(row[target_col]), 2), "y": round(float(row[second_numeric_col]), 2)}
                    for _, row in clean_df.head(200).iterrows()
                ]
                return ChartSpecification(
                    chart_type="scatter",
                    title=custom_title or f"{target_col.replace('_', ' ').title()} vs. {second_numeric_col.replace('_', ' ').title()}",
                    description=f"Observed distribution between {target_col} and {second_numeric_col}.",
                    x_axis_field=target_col,
                    y_axis_field=second_numeric_col,
                    data=points,
                    available=True
                )

        # 4. Time Series -> Line Chart
        if date_col and date_col in df.columns:
            try:
                # Group by date column and aggregate
                temp_df = df[[date_col, target_col]].dropna().copy()
                temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=[date_col])
                if len(temp_df) >= 2:
                    temp_df = temp_df.sort_values(by=date_col)
                    grouped = temp_df.groupby(temp_df[date_col].dt.strftime("%Y-%m-%d"))[target_col].sum().reset_index()
                    data_points = [
                        {"period": row[date_col], "value": round(float(row[target_col]), 2)}
                        for _, row in grouped.iterrows()
                    ]
                    return ChartSpecification(
                        chart_type="line",
                        title=custom_title or f"{target_col.replace('_', ' ').title()} Over Time",
                        description=f"Chronological trajectory of {target_col} across observed periods.",
                        x_axis_field="period",
                        y_axis_field="value",
                        series_name=target_col.replace('_', ' ').title(),
                        data=data_points,
                        available=True
                    )
            except Exception:
                pass

        # 5. Categorical comparison -> Bar or Pie
        # Find dimension column if not specified
        if not dimension_col or dimension_col not in df.columns:
            cat_cols = [
                c for c in df.columns
                if c != target_col and (df[c].dtype == "object" or df[c].nunique() <= 20)
            ]
            dimension_col = cat_cols[0] if cat_cols else None

        if dimension_col and dimension_col in df.columns:
            clean_df = df[[dimension_col, target_col]].dropna()
            grouped = clean_df.groupby(dimension_col)[target_col].sum().reset_index()
            num_categories = len(grouped)

            # Part-to-whole check: pie/donut if small number of categories (2 to 7) and requested or natural composition
            all_non_negative = (grouped[target_col] >= 0).all()
            if is_part_to_whole and 2 <= num_categories <= 7 and all_non_negative:
                data_points = [
                    {"name": str(row[dimension_col]), "value": round(float(row[target_col]), 2)}
                    for _, row in grouped.iterrows()
                ]
                return ChartSpecification(
                    chart_type="pie",
                    title=custom_title or f"{target_col.replace('_', ' ').title()} Composition by {dimension_col.replace('_', ' ').title()}",
                    description=f"Part-to-whole distribution of {target_col} across {dimension_col} segments.",
                    x_axis_field="name",
                    y_axis_field="value",
                    data=data_points,
                    available=True
                )
            else:
                # Default to Bar chart (even if many categories, bar chart is clearer)
                grouped = grouped.sort_values(by=target_col, ascending=False).head(15)
                data_points = [
                    {"category": str(row[dimension_col]), "value": round(float(row[target_col]), 2)}
                    for _, row in grouped.iterrows()
                ]
                return ChartSpecification(
                    chart_type="bar",
                    title=custom_title or f"{target_col.replace('_', ' ').title()} by {dimension_col.replace('_', ' ').title()}",
                    description=f"Comparison of {target_col} across {dimension_col} categories.",
                    x_axis_field="category",
                    y_axis_field="value",
                    series_name=target_col.replace('_', ' ').title(),
                    data=data_points,
                    available=True
                )

        # Fallback if only 1 numeric column exists and no categories
        if target_col in df.columns:
            kpi_val = float(df[target_col].sum())
            return ChartSpecification(
                chart_type="kpi",
                title=custom_title or f"Total {target_col.replace('_', ' ').title()}",
                description=f"Overall aggregated sum of {target_col}",
                kpi_value=round(kpi_val, 2),
                kpi_label=target_col.replace('_', ' ').title(),
                available=True
            )

        return ChartSpecification(
            chart_type="none",
            title="Visualization Not Available",
            description="Unable to map columns into a supported analytical chart type.",
            available=False,
            empty_reason="Visualization not available for this analysis."
        )
