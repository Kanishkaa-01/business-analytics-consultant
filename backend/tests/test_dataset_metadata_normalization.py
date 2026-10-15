import io
import json
import datetime
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_ingestion import IngestionService, normalize_metadata_for_json

client = TestClient(app)


def test_normalize_primitive_types():
    """Verify that normalize_metadata_for_json handles all target types correctly."""
    # 1. Timestamps and datetimes
    ts = pd.Timestamp("2021-05-15 14:30:00")
    dt = datetime.datetime(2021, 5, 15, 14, 30, 0)
    d = datetime.date(2021, 5, 15)
    assert normalize_metadata_for_json(ts) == "2021-05-15T14:30:00"
    assert normalize_metadata_for_json(dt) == "2021-05-15T14:30:00"
    assert normalize_metadata_for_json(d) == "2021-05-15"

    # 2. Numpy integers and floats
    np_i64 = np.int64(12345)
    np_i32 = np.int32(42)
    assert normalize_metadata_for_json(np_i64) == 12345
    assert isinstance(normalize_metadata_for_json(np_i64), int)
    assert normalize_metadata_for_json(np_i32) == 42
    assert isinstance(normalize_metadata_for_json(np_i32), int)

    np_f64 = np.float64(99.95)
    np_f32 = np.float32(12.5)
    assert normalize_metadata_for_json(np_f64) == 99.95
    assert isinstance(normalize_metadata_for_json(np_f64), float)
    assert normalize_metadata_for_json(np_f32) == 12.5
    assert isinstance(normalize_metadata_for_json(np_f32), float)

    # 3. Numpy and Python booleans
    np_b_true = np.bool_(True)
    np_b_false = np.bool_(False)
    assert normalize_metadata_for_json(np_b_true) is True
    assert isinstance(normalize_metadata_for_json(np_b_true), bool)
    assert normalize_metadata_for_json(np_b_false) is False
    assert isinstance(normalize_metadata_for_json(np_b_false), bool)

    # 4. Missing / NaN / NaT values convert to None
    assert normalize_metadata_for_json(pd.NaT) is None
    assert normalize_metadata_for_json(pd.NA) is None
    assert normalize_metadata_for_json(np.nan) is None
    assert normalize_metadata_for_json(float("nan")) is None
    assert normalize_metadata_for_json(float("inf")) is None
    assert normalize_metadata_for_json(float("-inf")) is None
    assert normalize_metadata_for_json(None) is None


def test_normalize_nested_complex_structures():
    """Verify that deeply nested structures are recursively normalized and JSON-serializable."""
    complex_data = {
        "dataset_name": "Retail Data",
        "created": pd.Timestamp("2023-01-01 10:00:00"),
        "metrics": {
            "total_count": np.int64(100),
            "ratio": np.float64(0.85),
            "is_valid": np.bool_(True),
            "invalid_val": np.nan,
            "missing_dt": pd.NaT,
            "pandas_na": pd.NA,
        },
        "sample_vector": np.array([1, 2, 3], dtype=np.int64),
        "dates_list": [
            pd.Timestamp("2023-01-02 00:00:00"),
            pd.Timestamp("2023-01-03 00:00:00"),
            pd.NaT
        ],
        "sub_series": pd.Series([10.5, np.nan, 20.5])
    }

    normalized = IngestionService.normalize_for_json(complex_data)

    # Must be 100% JSON serializable
    json_str = json.dumps(normalized)
    assert isinstance(json_str, str)

    parsed = json.loads(json_str)
    assert parsed["created"] == "2023-01-01T10:00:00"
    assert parsed["metrics"]["total_count"] == 100
    assert parsed["metrics"]["is_valid"] is True
    assert parsed["metrics"]["invalid_val"] is None
    assert parsed["metrics"]["missing_dt"] is None
    assert parsed["metrics"]["pandas_na"] is None
    assert parsed["sample_vector"] == [1, 2, 3]
    assert parsed["dates_list"] == ["2023-01-02T00:00:00", "2023-01-03T00:00:00", None]
    assert parsed["sub_series"] == [10.5, None, 20.5]


def test_extract_schema_metadata_with_timestamps():
    """Verify extract_schema_metadata produces clean, JSON-serializable metadata with ISO dates."""
    df = pd.DataFrame({
        "InvoiceNo": ["536365", "536366", "536367"],
        "InvoiceDate": [
            pd.Timestamp("2010-12-01 08:26:00"),
            pd.Timestamp("2010-12-01 08:28:00"),
            pd.NaT
        ],
        "UnitPrice": [2.55, 3.39, 4.00],
        "Quantity": [6, 12, 2]
    })

    meta = IngestionService.extract_schema_metadata(df)

    # Confirm json.dumps succeeds
    json_str = json.dumps(meta)
    assert isinstance(json_str, str)

    # Inspect InvoiceDate column metadata
    date_col = next(c for c in meta["columns"] if c["name"] == "InvoiceDate")
    assert date_col["inferred_type"] == "datetime"
    assert date_col["min_val"] == "2010-12-01T08:26:00"
    assert date_col["max_val"] == "2010-12-01T08:28:00"
    assert isinstance(date_col["sample_values"], list)
    assert len(date_col["sample_values"]) == 2
    assert all(isinstance(v, str) for v in date_col["sample_values"])

    # Inspect UnitPrice column metadata
    price_col = next(c for c in meta["columns"] if c["name"] == "UnitPrice")
    assert price_col["inferred_type"] == "numeric"
    assert isinstance(price_col["min_val"], (int, float))
    assert isinstance(price_col["mean_val"], (int, float))
    assert isinstance(price_col["null_percentage"], (int, float))


def test_upload_excel_dataset_with_invoicedate_succeeds():
    """
    Simulates real-world UCI Online Retail excel upload.
    Verifies that db.commit() does NOT fail with:
    TypeError: Object of type Timestamp is not JSON serializable.
    """
    df = pd.DataFrame({
        "InvoiceNo": [536365, 536365, 536366, 536367, 536368, 536369],
        "StockCode": ["85123A", "71053", "84406B", "84029G", "84029E", "22752"],
        "Description": [
            "WHITE HANGING HEART T-LIGHT HOLDER",
            "WHITE METAL LANTERN",
            "CREAM CUPID HEARTS COAT HANGER",
            "KNITTED UNION FLAG HOT WATER BOTTLE",
            "RED WOOLLY HOTTIE WHITE HEART.",
            "SET 7 BABUSHKA NESTING BOXES"
        ],
        "Quantity": [6, 6, 8, 6, 6, 2],
        "InvoiceDate": [
            pd.Timestamp("2010-12-01 08:26:00"),
            pd.Timestamp("2010-12-01 08:26:00"),
            pd.Timestamp("2010-12-01 08:28:00"),
            pd.Timestamp("2010-12-01 08:34:00"),
            pd.Timestamp("2010-12-01 08:34:00"),
            pd.Timestamp("2010-12-01 08:35:00")
        ],
        "UnitPrice": [2.55, 3.39, 2.75, 3.39, 3.39, 7.65],
        "CustomerID": [17850.0, 17850.0, 17850.0, 13047.0, 13047.0, np.nan],
        "Country": [
            "United Kingdom", "United Kingdom", "United Kingdom",
            "United Kingdom", "United Kingdom", "United Kingdom"
        ]
    })

    # Save to Excel in-memory buffer
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    # 1. Upload via POST /api/datasets/upload
    files = {"file": ("Online_Retail_Sample.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/datasets/upload", files=files)

    assert res.status_code == 200, f"Upload failed: {res.text}"
    data = res.json()
    assert "id" in data
    dataset_id = data["id"]
    assert data["row_count"] == 6
    assert data["column_count"] == 8

    # Verify schema metadata contains clean ISO strings
    meta = data["schema_metadata"]
    inv_col = next(c for c in meta["columns"] if c["name"] == "InvoiceDate")
    assert inv_col["inferred_type"] == "datetime"
    assert inv_col["min_val"] == "2010-12-01T08:26:00"
    assert inv_col["max_val"] == "2010-12-01T08:35:00"
    assert all(isinstance(v, str) for v in inv_col["sample_values"])

    # Verify preview rows are JSON-serializable
    assert len(data["preview_rows"]) == 6
    assert data["preview_rows"][0]["InvoiceDate"] == "2010-12-01T08:26:00"

    # 2. Retrieve dataset via GET /api/datasets/{dataset_id}
    get_res = client.get(f"/api/datasets/{dataset_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == dataset_id
    assert json.dumps(retrieved["schema_metadata"]) is not None
    assert json.dumps(retrieved["preview_rows"]) is not None

    # 3. Clean up dataset
    del_res = client.delete(f"/api/datasets/{dataset_id}")
    assert del_res.status_code == 200
