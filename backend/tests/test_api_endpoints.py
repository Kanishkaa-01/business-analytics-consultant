import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "database_dialect" in data


def test_seed_and_list_datasets():
    # Seed sample datasets
    seed_res = client.post("/api/datasets/seed-samples")
    assert seed_res.status_code == 200
    samples = seed_res.json()
    assert len(samples) >= 3

    # List datasets
    list_res = client.get("/api/datasets")
    assert list_res.status_code == 200
    datasets = list_res.json()
    assert len(datasets) >= 3

    # Retrieve first dataset
    ds_id = datasets[0]["id"]
    get_res = client.get(f"/api/datasets/{ds_id}")
    assert get_res.status_code == 200
    ds_detail = get_res.json()
    assert "schema_metadata" in ds_detail
    assert "preview_rows" in ds_detail


def test_end_to_end_analysis_pipeline():
    # 1. Seed
    client.post("/api/datasets/seed-samples")
    datasets = client.get("/api/datasets").json()
    retail_ds = next(d for d in datasets if d["filename"] == "retail_ecommerce_q3.csv")

    # 2. Run Analysis Pipeline
    run_res = client.post("/api/analysis/run", json={
        "dataset_id": retail_ds["id"],
        "target_column": "net_revenue",
        "date_column": "transaction_date"
    })
    assert run_res.status_code == 200
    analysis = run_res.json()
    assert analysis["status"] == "completed"
    assert analysis["data_quality"]["overall_quality_score"] > 0
    assert analysis["business_health"]["overall_health_score"] > 0
    assert len(analysis["diagnostics"]["variance_breakdown"]) > 0
    assert len(analysis["root_cause"]["factor_contributions"]) > 0
    assert len(analysis["recommendations"]) > 0
    assert len(analysis["evidence_chains"]) > 0

    analysis_id = analysis["id"]

    # 3. Test Human Decision Recording
    rec_id = analysis["recommendations"][0]["id"]
    action_title = analysis["recommendations"][0]["title"]
    dec_res = client.post(f"/api/decisions/{analysis_id}", json={
        "recommendation_id": rec_id,
        "action_title": action_title,
        "decision_status": "Accepted",
        "stakeholder": "Chief Commercial Officer",
        "notes_rationale": "Prioritize operational turnaround in Q4 budget allocation.",
        "target_date": "2026-11-15",
        "expected_impact_dollars": 45000.0
    })
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["decision_status"] == "Accepted"

    # 4. Test What-If Simulation
    sim_res = client.post("/api/simulation/simulate", json={
        "analysis_id": analysis_id,
        "price_change_pct": 3.0,
        "discount_adjustment_pct": 10.0,
        "churn_mitigation_pct": 5.0,
        "operational_efficiency_pct": 4.0
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["simulated_profit"] > 0
    assert "net_economic_value_added" in sim_data
    assert "supported_interventions" in sim_data

    # 4b. Test Save Scenario with Intervention Parameters
    save_res = client.post("/api/simulation/save-scenario", json={
        "analysis_id": analysis_id,
        "name": "Q4 Price Hike",
        "parameters": {
            "intervention_type": "Price Change",
            "change_percentage": 5.0,
            "parameter_type": "percentage",
            "notes": "Testing 5% price expansion with volume held constant."
        }
    })
    assert save_res.status_code == 200
    save_data = save_res.json()
    scenario_id = save_data["scenario_id"]
    assert save_data["parameters"]["price_change_pct"] == 5.0
    assert save_data["parameters"]["intervention_type"] == "Price Change"
    assert save_data["projected_outcomes"]["simulated_revenue"] > 0

    # 4c. Test Update Scenario
    update_res = client.put(f"/api/simulation/scenario/{scenario_id}", json={
        "name": "Q4 Price Hike Revised",
        "parameters": {
            "intervention_type": "Price Change",
            "change_percentage": 8.0,
            "parameter_type": "percentage",
            "notes": "Updated to 8% expansion."
        }
    })
    assert update_res.status_code == 200
    up_data = update_res.json()
    assert up_data["name"] == "Q4 Price Hike Revised"
    assert up_data["parameters"]["price_change_pct"] == 8.0

    # 4d. Test Compare Scenarios
    compare_res = client.get(f"/api/simulation/{analysis_id}/compare")
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert len(comp_data["scenarios"]) >= 2
    assert comp_data["scenarios"][0]["name"] == "Baseline"
    assert comp_data["scenarios"][0]["incremental_value"] == 0.0

    # 4e. Test Input Rejection for Invalid Values
    inv_res = client.post("/api/simulation/save-scenario", json={
        "analysis_id": analysis_id,
        "name": "Invalid Price Drop",
        "parameters": {
            "intervention_type": "Price Change",
            "change_percentage": -120.0
        }
    })
    assert inv_res.status_code == 400

    # 5. Test Export Dossier
    export_res = client.get(f"/api/export/{analysis_id}/dossier")
    assert export_res.status_code == 200
    dossier = export_res.json()
    assert "four_core_questions" in dossier
    assert len(dossier["four_core_questions"]["question_4_what_action_to_consider"]["recorded_management_decisions"]) >= 1

    # 6. Test Printable HTML Report
    html_res = client.get(f"/api/export/{analysis_id}/print-report")
    assert html_res.status_code == 200
    assert "Executive Business Decision Report" in html_res.text


def test_document_extraction_api():
    # 1. Seed datasets and documents
    client.post("/api/datasets/seed-samples")
    datasets = client.get("/api/datasets").json()
    pdf_ds = next(d for d in datasets if d["filename"].endswith(".pdf"))
    docx_ds = next(d for d in datasets if d["filename"].endswith(".docx"))

    # 2. Test Extracted Document Endpoint (Preserved Document Processing)
    pdf_ext_res = client.get(f"/api/datasets/{pdf_ds['id']}/extracted")
    assert pdf_ext_res.status_code == 200
    pdf_doc = pdf_ext_res.json()
    assert pdf_doc["format"] == "pdf"
    assert len(pdf_doc["paragraphs"]) > 0

    docx_ext_res = client.get(f"/api/datasets/{docx_ds['id']}/extracted")
    assert docx_ext_res.status_code == 200
    docx_doc = docx_ext_res.json()
    assert docx_doc["format"] == "docx"
    assert len(docx_doc["headings"]) > 0

    # 3. Verify Cross-Source Diagnosis API is completely removed (returns 404 or 405 Method Not Allowed)
    cross_res = client.post("/api/datasets/cross-source-diagnose", json={
        "dataset_ids": [pdf_ds["id"], docx_ds["id"]]
    })
    assert cross_res.status_code in [404, 405]
