from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats
from app.models.schemas import DataQualityReport, QualityIssue, ColumnQualityMetric


class QualityProfiler:
    @staticmethod
    def audit_dataset(df: pd.DataFrame) -> DataQualityReport:
        """
        Conducts a comprehensive, deterministic data quality audit.
        Evaluates completeness, validity, uniqueness, data distribution, and outliers.
        """
        total_rows, total_cols = df.shape
        if total_rows == 0 or total_cols == 0:
            return DataQualityReport(
                overall_quality_score=0.0,
                grade="F",
                total_records=total_rows,
                duplicate_rows=0,
                completeness_ratio=0.0,
                validity_ratio=0.0,
                consistency_ratio=0.0,
                issues=[QualityIssue(
                    severity="Critical",
                    dimension="Completeness",
                    column=None,
                    description="Dataset is empty.",
                    affected_rows=0,
                    percentage=100.0,
                    recommendation="Provide a dataset with non-zero observations."
                )],
                column_metrics=[],
                reliability_assessment="Dataset contains no records. Cannot perform analytics."
            )

        # 1. Uniqueness check
        duplicate_rows = int(df.duplicated().sum())
        uniqueness_ratio = 1.0 - (duplicate_rows / total_rows)

        # 2. Completeness check
        total_cells = total_rows * total_cols
        total_nulls = int(df.isnull().sum().sum())
        completeness_ratio = round(1.0 - (total_nulls / total_cells), 4)

        issues: List[QualityIssue] = []
        column_metrics: List[ColumnQualityMetric] = []

        if duplicate_rows > 0:
            dup_pct = round((duplicate_rows / total_rows) * 100, 2)
            issues.append(QualityIssue(
                severity="Warning" if dup_pct < 5.0 else "Critical",
                dimension="Uniqueness",
                column=None,
                description=f"Detected {duplicate_rows} duplicate record(s) ({dup_pct}% of total records).",
                affected_rows=duplicate_rows,
                percentage=dup_pct,
                recommendation="Deduplicate records or evaluate whether recurring entity IDs represent distinct transactions."
            ))

        validity_scores = []
        consistency_scores = []

        for col in df.columns:
            series = df[col]
            nulls = int(series.isnull().sum())
            comp_score = round(1.0 - (nulls / total_rows), 4)

            outlier_count = 0
            outlier_pct = 0.0
            skew_val = None
            valid_ratio = 1.0

            if comp_score < 0.8:
                null_pct = round((nulls / total_rows) * 100, 2)
                col_low = str(col).lower()
                if any(k in col_low for k in ["customer", "client", "user"]):
                    desc = f"Column '{col}' has {null_pct}% missing values ({nulls} missing entries), which may represent guest or unregistered transactions."
                    recom = f"Isolate unregistered customer records to avoid skewing registered account behavior in downstream analysis."
                else:
                    desc = f"Column '{col}' has {null_pct}% missing values ({nulls} missing entries)."
                    recom = f"Impute or isolate '{col}' to prevent bias in downstream attribution models."

                issues.append(QualityIssue(
                    severity="Critical" if comp_score < 0.5 else "Warning",
                    dimension="Completeness",
                    column=col,
                    description=desc,
                    affected_rows=nulls,
                    percentage=null_pct,
                    recommendation=recom
                ))

            # Check if column is a binary flag (e.g. churned, returned, cancelled, 0/1)
            is_binary = False
            if pd.api.types.is_numeric_dtype(series) or series.dtype == "bool":
                non_null_unique = set(series.dropna().unique())
                if non_null_unique.issubset({0, 1, 0.0, 1.0, True, False}):
                    is_binary = True

            # Numeric validation: outliers, skewness, negative values
            if pd.api.types.is_numeric_dtype(series) and not is_binary:
                clean_s = series.dropna()
                if len(clean_s) >= 5:
                    q25 = float(clean_s.quantile(0.25))
                    q75 = float(clean_s.quantile(0.75))
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr

                    outliers = clean_s[(clean_s < lower_bound) | (clean_s > upper_bound)]
                    outlier_count = int(len(outliers))
                    outlier_pct = round((outlier_count / len(clean_s)) * 100, 2)

                    try:
                        skew_calc = float(stats.skew(clean_s))
                        skew_val = round(skew_calc, 2) if not np.isnan(skew_calc) else None
                    except Exception:
                        skew_val = None

                    # If column is typically non-negative (sales, price, cost, quantity)
                    col_lower = col.lower()
                    if any(term in col_lower for term in ["price", "revenue", "sales", "cost", "quantity", "volume", "amount"]):
                        neg_count = int((clean_s < 0).sum())
                        if neg_count > 0:
                            neg_pct = round((neg_count / len(clean_s)) * 100, 2)
                            valid_ratio = max(0.0, 1.0 - (neg_count / len(clean_s)))

                            if any(k in col_lower for k in ["quantity", "volume", "qty"]):
                                desc = f"Column '{col}' contains {neg_count} negative transaction values ({neg_pct}%), which may represent returns or cancellations."
                                recom = "Verify transaction identifiers (e.g. cancellation prefix 'C') to separate operational returns from data extraction errors."
                            elif any(k in col_lower for k in ["price", "unitprice", "cost"]):
                                desc = f"Column '{col}' contains {neg_count} negative value(s) ({neg_pct}%), unexpected for pricing/cost metrics. May represent accounting corrections or debt adjustments."
                                recom = "Audit upstream extraction for return credits or data sign inversions."
                            else:
                                desc = f"Column '{col}' contains {neg_count} negative value(s) ({neg_pct}%), unexpected for non-negative financial/quantity metric."
                                recom = "Audit upstream extraction for return credits or data sign inversions."

                            issues.append(QualityIssue(
                                severity="Critical" if neg_pct > 5.0 else "Warning",
                                dimension="Validity",
                                column=col,
                                description=desc,
                                affected_rows=neg_count,
                                percentage=neg_pct,
                                recommendation=recom
                            ))

                    if outlier_pct > 5.0:
                        issues.append(QualityIssue(
                            severity="Warning",
                            dimension="Distribution",
                            column=col,
                            description=f"Statistical Outlier concentration in '{col}': {outlier_count} observations ({outlier_pct}%) fall outside the 1.5x IQR boundary. These reflect extreme values or distribution skew rather than confirmed data errors.",
                            affected_rows=outlier_count,
                            percentage=outlier_pct,
                            recommendation="Consider robust statistical measures (e.g. median, winsorization) to mitigate outlier distortion."
                        ))
            elif is_binary:
                # Binary indicator handling: compute event rate instead of IQR outliers
                clean_s = series.dropna().astype(float)
                if len(clean_s) > 0:
                    pos_rate = round((clean_s == 1.0).mean() * 100, 2)
                    outlier_count = 0
                    outlier_pct = 0.0
                    skew_val = None

            # Categorical cardinality validation
            elif series.dtype == "object":
                unique_c = series.nunique()
                if unique_c == total_rows and total_rows > 50:
                    pass  # Likely an identifier
                elif unique_c == 1 and total_rows > 10:
                    issues.append(QualityIssue(
                        severity="Info",
                        dimension="Consistency",
                        column=col,
                        description=f"Column '{col}' has zero variance (constant single value across all rows).",
                        affected_rows=total_rows,
                        percentage=100.0,
                        recommendation="Remove constant column from diagnostic segmentation models as it carries zero variance."
                    ))

            validity_scores.append(valid_ratio)
            consistency_scores.append(1.0 if outlier_pct < 10 else 0.85)

            column_metrics.append(ColumnQualityMetric(
                column=col,
                completeness_score=comp_score,
                validity_score=round(valid_ratio, 4),
                outlier_count=outlier_count,
                outlier_percentage=outlier_pct,
                skewness=skew_val,
            ))

        mean_validity = float(np.mean(validity_scores)) if validity_scores else 1.0
        mean_consistency = float(np.mean(consistency_scores)) if consistency_scores else 1.0

        # Overall deterministic score (0-100)
        overall_score = round(
            (completeness_ratio * 0.40 + mean_validity * 0.30 + uniqueness_ratio * 0.15 + mean_consistency * 0.15) * 100,
            1
        )

        if overall_score >= 90:
            grade = "A"
            reliability = "High data integrity. Statistical findings and attribution models exhibit high analytical confidence."
        elif overall_score >= 80:
            grade = "B"
            reliability = "Good data quality with moderate anomalies. Diagnostic findings are reliable with standard confidence bands."
        elif overall_score >= 70:
            grade = "C"
            reliability = "Acceptable data hygiene, but noticeable missingness or outliers detected. Recommendations should be validated against critical segments."
        elif overall_score >= 60:
            grade = "D"
            reliability = "Sub-optimal data fidelity. Missing records and integrity violations may distort the data distribution and analytical findings."
        else:
            grade = "F"
            reliability = "Severe data quality deficiency. Downstream decision recommendations must be interpreted with extreme caution until cleaned."

        return DataQualityReport(
            overall_quality_score=overall_score,
            grade=grade,
            total_records=total_rows,
            duplicate_rows=duplicate_rows,
            completeness_ratio=round(completeness_ratio, 4),
            validity_ratio=round(mean_validity, 4),
            consistency_ratio=round(mean_consistency, 4),
            issues=issues,
            column_metrics=column_metrics,
            reliability_assessment=reliability
        )
