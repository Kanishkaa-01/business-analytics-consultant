import pandas as pd
import numpy as np
from app.services.quality_profiler import QualityProfiler


def test_quality_profiler_clean_dataset():
    df = pd.DataFrame({
        "revenue": [100.0, 150.0, 120.0, 130.0, 140.0, 160.0, 110.0, 125.0, 135.0, 145.0, 155.0],
        "category": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B", "A"],
        "region": ["North", "South", "North", "South", "North", "South", "North", "South", "North", "South", "North"]
    })
    report = QualityProfiler.audit_dataset(df)
    assert report.total_records == 11
    assert report.duplicate_rows == 0
    assert report.completeness_ratio == 1.0
    assert report.overall_quality_score >= 85.0
    assert report.grade in ["A", "B"]


def test_quality_profiler_detects_flaws():
    df = pd.DataFrame({
        "sales": [100.0, -50.0, None, 200.0, 150.0, 10000.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        "region": ["North", "South", "North", "South", "North", "South", "North", "South", "North", "South", "North"]
    })
    report = QualityProfiler.audit_dataset(df)
    assert report.completeness_ratio < 1.0
    # Should detect negative sales and outlier
    validity_issues = [i for i in report.issues if i.dimension in ["Validity", "Distribution"]]
    assert len(validity_issues) >= 1
