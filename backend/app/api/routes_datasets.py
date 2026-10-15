import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Dataset, AnalysisRun
from app.models.schemas import DatasetSummary, DatasetDetail, AskDataRequest, AskDataResponse
from app.models.evidence_model import ExtractedDocument
from app.services.data_ingestion import IngestionService
from app.services.pdf_parser import PDFParser
from app.services.docx_parser import DOCXParser
from app.services.spreadsheet_parser import SpreadsheetParser
from app.engines.ask_data_engine import AskDataEngine

router = APIRouter(prefix="/datasets", tags=["Datasets & Documents"])


@router.post("/upload", response_model=DatasetDetail)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a structured business dataset or business document.
    Supported: CSV, XLSX, PDF, DOCX.
    Computes deterministic SHA-256 hash to guarantee data immutability.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    ext = Path(file.filename).suffix.lower()
    if ext not in IngestionService.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: {', '.join(IngestionService.SUPPORTED_FORMATS)}"
        )

    try:
        dest_path, file_hash, file_size, row_count, col_count, schema_meta = (
            IngestionService.save_and_profile_file(file.file, file.filename)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {str(exc)}")

    # Create dataset record
    dataset_name = Path(file.filename).stem.replace("_", " ").title()
    normalized_meta = IngestionService.normalize_for_json(schema_meta)
    dataset = Dataset(
        name=dataset_name,
        filename=Path(dest_path).name,
        file_path=str(dest_path.resolve()),
        file_size_bytes=file_size,
        file_hash=file_hash,
        row_count=row_count,
        column_count=col_count,
        schema_metadata=normalized_meta,
        is_sample=False
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Get preview rows safely
    preview = []
    if ext in [".csv", ".txt", ".xlsx", ".xls"]:
        df = IngestionService.load_dataframe(dest_path)
        preview = IngestionService.normalize_for_json(df.head(10).to_dict(orient="records"))
    elif ext == ".pdf":
        parsed = PDFParser.parse_pdf(dest_path, dataset.id, dataset.filename)
        if parsed.tables and parsed.tables[0].rows:
            headers = parsed.tables[0].headers
            for r in parsed.tables[0].rows[:5]:
                preview.append({headers[i] if i < len(headers) else f"Col_{i}": val for i, val in enumerate(r)})
    elif ext == ".docx":
        parsed = DOCXParser.parse_docx(dest_path, dataset.id, dataset.filename)
        if parsed.tables and parsed.tables[0].rows:
            headers = parsed.tables[0].headers
            for r in parsed.tables[0].rows[:5]:
                preview.append({headers[i] if i < len(headers) else f"Col_{i}": val for i, val in enumerate(r)})

    return DatasetDetail(
        id=dataset.id,
        name=dataset.name,
        filename=dataset.filename,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        file_size_bytes=dataset.file_size_bytes,
        is_sample=dataset.is_sample,
        created_at=dataset.created_at,
        file_hash=dataset.file_hash,
        schema_metadata=dataset.schema_metadata,
        preview_rows=preview
    )


@router.get("", response_model=List[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)):
    """List all available business datasets and documents in the system."""
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    return datasets


@router.post("/seed-samples", response_model=List[DatasetSummary])
@router.post("/seed-samples/", response_model=List[DatasetSummary], include_in_schema=False)
def seed_sample_datasets(db: Session = Depends(get_db)):
    """Seeds both structured datasets (CSV) and business documents (PDF, DOCX) into the database."""
    samples_dir = Path(__file__).resolve().parent.parent / "sample_data"
    sample_files = [
        ("retail_ecommerce_q3.csv", "Omnichannel Retail & E-Commerce (Q3 Performance)"),
        ("retail_q3_executive_memo.pdf", "Q3 Retail Performance & Commercial Review (Memo)"),
        ("q3_financial_audit_review.docx", "Q3 Financial Audit & Revenue Reconciliation (Docx)"),
        ("b2b_saas_churn.csv", "B2B SaaS Annual Recurring Revenue & Churn"),
        ("manufacturing_supply.csv", "Manufacturing Production & Supply Chain Latency")
    ]

    seeded_records = []
    for filename, display_name in sample_files:
        filepath = samples_dir / filename
        if not filepath.exists():
            continue

        existing = db.query(Dataset).filter(Dataset.filename == filename).first()
        if existing:
            seeded_records.append(existing)
            continue

        ext = filepath.suffix.lower()
        try:
            with open(filepath, "rb") as f:
                dest_path, file_hash, file_size, row_count, col_count, schema_meta = (
                    IngestionService.save_and_profile_file(f, filename)
                )

            dataset = Dataset(
                name=display_name,
                filename=filename,
                file_path=str(dest_path.resolve()),
                file_size_bytes=file_size,
                file_hash=file_hash,
                row_count=row_count,
                column_count=col_count,
                schema_metadata=IngestionService.normalize_for_json(schema_meta),
                is_sample=True
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            seeded_records.append(dataset)
        except Exception:
            continue

    return seeded_records


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed schema and preview rows for a specific dataset or document."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    preview = []
    if file_path.exists():
        ext = file_path.suffix.lower()
        if ext in [".csv", ".txt", ".xlsx", ".xls"]:
            try:
                df = IngestionService.load_dataframe(file_path)
                preview = IngestionService.normalize_for_json(df.head(10).to_dict(orient="records"))
            except Exception:
                preview = []
        elif ext == ".pdf":
            try:
                parsed = PDFParser.parse_pdf(file_path, dataset.id, dataset.filename)
                if parsed.tables and parsed.tables[0].rows:
                    headers = parsed.tables[0].headers
                    for r in parsed.tables[0].rows[:5]:
                        preview.append({headers[i] if i < len(headers) else f"Col_{i}": val for i, val in enumerate(r)})
            except Exception:
                preview = []
        elif ext == ".docx":
            try:
                parsed = DOCXParser.parse_docx(file_path, dataset.id, dataset.filename)
                if parsed.tables and parsed.tables[0].rows:
                    headers = parsed.tables[0].headers
                    for r in parsed.tables[0].rows[:5]:
                        preview.append({headers[i] if i < len(headers) else f"Col_{i}": val for i, val in enumerate(r)})
            except Exception:
                preview = []

    return DatasetDetail(
        id=dataset.id,
        name=dataset.name,
        filename=dataset.filename,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        file_size_bytes=dataset.file_size_bytes,
        is_sample=dataset.is_sample,
        created_at=dataset.created_at,
        file_hash=dataset.file_hash,
        schema_metadata=dataset.schema_metadata or {},
        preview_rows=preview
    )


@router.get("/{dataset_id}/extracted", response_model=ExtractedDocument)
def get_extracted_document(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieve full parsed document representation (pages, sections, tables, normalized evidence)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")

    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return PDFParser.parse_pdf(file_path, dataset.id, dataset.filename)
    elif ext == ".docx":
        return DOCXParser.parse_docx(file_path, dataset.id, dataset.filename)
    elif ext in [".csv", ".txt", ".xlsx", ".xls"]:
        return SpreadsheetParser.parse_spreadsheet(file_path, dataset.id, dataset.filename)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'.")


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Delete a dataset or document and its associated analytical runs."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    db.delete(dataset)
    db.commit()
    return {"status": "success", "message": f"Dataset {dataset_id} removed."}


@router.post("/{dataset_id}/ask", response_model=AskDataResponse)
def ask_question_about_dataset(
    dataset_id: str,
    req: AskDataRequest,
    db: Session = Depends(get_db)
):
    """Answers natural language questions about dataset using deterministic pandas aggregations."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    ext = file_path.suffix.lower()
    if ext in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Ask Your Data supports structured tabular datasets (CSV/XLSX)."
        )

    df = IngestionService.load_dataframe(file_path)
    result = AskDataEngine.answer_question(df, req.query, dataset.schema_metadata)
    return AskDataResponse(**result)


@router.get("/{dataset_id}/suggested-questions", response_model=List[str])
def get_suggested_questions(
    dataset_id: str,
    db: Session = Depends(get_db)
):
    """Dynamically suggests business questions based on dataset schema columns."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    ext = file_path.suffix.lower()
    if ext in [".pdf", ".docx"]:
        return ["What are the key qualitative findings in this document?"]

    df = IngestionService.load_dataframe(file_path)
    return AskDataEngine.generate_suggested_questions(df, dataset.schema_metadata)

