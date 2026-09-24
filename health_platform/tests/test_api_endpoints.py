from fastapi.testclient import TestClient
import uuid
from health_platform.api.app import app

client = TestClient(app)

def test_api_root_serves_web_app():
    res = client.get("/")
    assert res.status_code == 200
    assert "HealthOS Core" in res.text
    assert "Patient-Centric Hospital Operating Platform" in res.text

def test_api_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["trial_balance_discrepancy"] == 0.0

def test_api_patient_registration_and_duplicate_handling():
    # 1. Register a patient
    payload = {
        "first_name": "Siddharth",
        "last_name": "Rao",
        "dob": "1988-06-18",
        "gender": "MALE",
        "primary_phone": "+919844011223",
        "postal_code": "560025",
        "identifiers": []
    }
    res1 = client.post("/api/v1/identity/resolve", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_newly_created"] is True
    assert data1["uhid"].startswith("MED-")
    mpi_id = data1["mpi_id"]

    # 2. Candidate with transposed month/day (18/06 -> 06/18) and same phone -> 409 Conflict
    payload_dup = {
        "first_name": "Siddhartha",
        "last_name": "Rao",
        "dob": "1988-06-18",
        "gender": "MALE",
        "primary_phone": "+919844011223",
        "postal_code": "560025",
        "identifiers": []
    }
    res_dup = client.post("/api/v1/identity/resolve", json=payload_dup)
    assert res_dup.status_code == 409
    assert "candidate_matches" in res_dup.json()["detail"]

def test_api_charge_capture_and_payment():
    encounter_id = str(uuid.uuid4())
    mpi_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())

    # 1. Capture clinical order charge
    charge_req = {
        "encounter_id": encounter_id,
        "mpi_id": mpi_id,
        "originating_resource_type": "ServiceRequest",
        "originating_resource_id": order_id,
        "tariff_code": "LAB-BIO-042",
        "department_code": "BIOCHEMISTRY",
        "unit_price": 750.00,
        "quantity": 1.0,
        "patient_co_pay_ratio": 0.20 # 20% patient co-pay = ₹150.00, 80% insurer = ₹600.00
    }
    res_charge = client.post("/api/v1/billing/charges/capture", json=charge_req)
    assert res_charge.status_code == 200
    data_charge = res_charge.json()
    assert data_charge["patient_share"] == 150.00
    assert data_charge["insurer_share"] == 600.00
    assert data_charge["trial_balance_status"] == "BALANCED"

    # 2. Patient pays ₹150.00 via UPI
    pay_req = {
        "encounter_id": encounter_id,
        "mpi_id": mpi_id,
        "amount": 150.00,
        "payment_method": "UPI"
    }
    res_pay = client.post("/api/v1/billing/payments", json=pay_req)
    assert res_pay.status_code == 200
    assert res_pay.json()["trial_balance_discrepancy"] == 0.0
