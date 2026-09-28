"""
Unit and Integration Tests for Pharmacy & e-Prescription Dispensing (Closed-Loop Inventory).
Verifies:
1. Inventory tracking and FEFO batch sorting.
2. Low stock and near-expiry / expired alerts.
3. Successful closed-loop prescription dispensing with stock decrements.
4. Regulatory safety rejection of expired medication batches.
5. Stock shortage protection.
6. Clinical-Financial Invariant: Charge capture to ledger with zero trial balance discrepancy.
7. REST API endpoints.
"""

import unittest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.pharmacy.models import (
    DispenseRequestInput,
    DispenseLineInput,
    AddStockBatchInput,
    StockAlertLevel
)
from health_platform.core.pharmacy.service import PharmacyService
from health_platform.api.app import app

client = TestClient(app)

class TestPharmacyWorkflows(unittest.TestCase):
    def setUp(self):
        self.identity = PatientIdentityService()
        self.financial = FinancialLedgerService()
        self.outbox = TransactionalOutboxPublisher()
        self.pharmacy = PharmacyService(
            identity_service=self.identity,
            financial_service=self.financial,
            outbox=self.outbox
        )

        # Register test patient
        self.patient_res = self.identity.resolve_or_create_patient(
            PatientRegistrationRequest(
                first_name="Anindita",
                last_name="Ray",
                dob="1971-07-28",
                gender="FEMALE",
                primary_phone="+918390367199",
                postal_code="400005",
                identifiers=[]
            )
        )
        self.mpi_id = self.patient_res.mpi_id
        self.encounter_id = uuid.uuid4()

    def test_01_inventory_initialization_and_alerts(self):
        inv = self.pharmacy.get_inventory()
        self.assertTrue(len(inv) >= 7)

        ezorb = self.pharmacy.get_catalog_item("MED-EZORB-FORTE")
        self.assertIsNotNone(ezorb)
        self.assertEqual(len(ezorb.batches), 2)
        self.assertEqual(ezorb.total_stock, 395) # 350 + 45

        alerts = self.pharmacy.get_alerts()
        self.assertTrue(alerts["near_expiry_count"] >= 1)
        self.assertTrue(alerts["expired_count"] >= 1)

    def test_02_successful_dispense_and_stock_decrement(self):
        ezorb = self.pharmacy.get_catalog_item("MED-EZORB-FORTE")
        batch = ezorb.batches[0] # EZ-2024-B1
        initial_stock = batch.quantity_available

        dispense_req = DispenseRequestInput(
            mpi_id=self.mpi_id,
            encounter_id=self.encounter_id,
            pharmacist_name="Kavita Deshmukh",
            pharmacist_reg_no="MH-PHARM-20120045",
            items=[
                DispenseLineInput(
                    item_code="MED-EZORB-FORTE",
                    batch_number=batch.batch_number,
                    quantity_to_dispense=30
                ),
                DispenseLineInput(
                    item_code="MED-PAN-40",
                    batch_number="PN-2024-08",
                    quantity_to_dispense=10
                )
            ],
            patient_co_pay_ratio=0.8
        )

        record = self.pharmacy.dispense_prescription(dispense_req)

        self.assertIsNotNone(record.dispense_id)
        self.assertTrue(record.dispense_number.startswith("DISP-"))
        self.assertEqual(len(record.lines), 2)

        # 30 * 28.50 = 855.00; 10 * 11.50 = 115.00 -> Total = 970.00
        self.assertEqual(record.gross_total, 970.00)
        self.assertEqual(record.patient_share, 776.00) # 80%
        self.assertEqual(record.insurer_share, 194.00) # 20%

        # Verify stock was decremented
        updated_ezorb = self.pharmacy.get_catalog_item("MED-EZORB-FORTE")
        updated_batch = next(b for b in updated_ezorb.batches if b.batch_number == batch.batch_number)
        self.assertEqual(updated_batch.quantity_available, initial_stock - 30)

        # Verify Financial Ledger Invariant has zero discrepancy!
        discrepancy = self.financial.get_trial_balance_discrepancy()
        self.assertEqual(discrepancy, 0.0)

    def test_03_rejection_of_expired_medication_batch(self):
        dispense_req = DispenseRequestInput(
            mpi_id=self.mpi_id,
            encounter_id=self.encounter_id,
            pharmacist_name="Kavita Deshmukh",
            pharmacist_reg_no="MH-PHARM-20120045",
            items=[
                DispenseLineInput(
                    item_code="MED-EXPIRED-TEST",
                    batch_number="EXP-2021-01",
                    quantity_to_dispense=5
                )
            ]
        )

        with self.assertRaises(ValueError) as ctx:
            self.pharmacy.dispense_prescription(dispense_req)

        self.assertIn("REGULATORY SAFETY REJECTION", str(ctx.exception))
        self.assertIn("expired", str(ctx.exception))

    def test_04_rejection_of_insufficient_stock(self):
        dispense_req = DispenseRequestInput(
            mpi_id=self.mpi_id,
            encounter_id=self.encounter_id,
            pharmacist_name="Kavita Deshmukh",
            pharmacist_reg_no="MH-PHARM-20120045",
            items=[
                DispenseLineInput(
                    item_code="MED-EZORB-FORTE",
                    batch_number="EZ-2023-A9",
                    quantity_to_dispense=500 # available is only 45
                )
            ]
        )

        with self.assertRaises(ValueError) as ctx:
            self.pharmacy.dispense_prescription(dispense_req)

        self.assertIn("INSUFFICIENT STOCK", str(ctx.exception))

    def test_05_restock_batch(self):
        ezorb = self.pharmacy.get_catalog_item("MED-EZORB-FORTE")
        initial_stock = ezorb.total_stock

        self.pharmacy.add_stock_batch(
            AddStockBatchInput(
                item_code="MED-EZORB-FORTE",
                batch_number="EZ-2025-C3",
                expiry_date="2028-06-30",
                mrp=29.00,
                unit_cost=18.50,
                quantity=200,
                manufacturer="Corona Remedies"
            )
        )

        updated_ezorb = self.pharmacy.get_catalog_item("MED-EZORB-FORTE")
        self.assertEqual(updated_ezorb.total_stock, initial_stock + 200)

    def test_06_api_pharmacy_endpoints(self):
        # 1. Get Inventory
        res = client.get("/api/v1/pharmacy/inventory")
        self.assertEqual(res.status_code, 200)
        inv = res.json()
        self.assertTrue(len(inv) >= 7)

        # 2. Get Alerts
        alert_res = client.get("/api/v1/pharmacy/alerts")
        self.assertEqual(alert_res.status_code, 200)
        alerts = alert_res.json()
        self.assertIn("near_expiry_count", alerts)

        # 3. Register patient
        reg_res = client.post("/api/v1/identity/resolve", json={
            "first_name": "Deepak",
            "last_name": "Chopra",
            "dob": "1965-03-21",
            "gender": "MALE",
            "primary_phone": "+919820011223",
            "postal_code": "400001",
            "identifiers": []
        })
        mpi_id = reg_res.json()["mpi_id"]
        enc_id = str(uuid.uuid4())

        # 4. Dispense via API
        disp_res = client.post("/api/v1/pharmacy/dispense", json={
            "mpi_id": mpi_id,
            "encounter_id": enc_id,
            "pharmacist_name": "Kavita Deshmukh",
            "pharmacist_reg_no": "MH-PHARM-20120045",
            "items": [
                {
                    "item_code": "MED-DOLO-650",
                    "batch_number": "DL-2025-01",
                    "quantity_to_dispense": 20
                }
            ],
            "patient_co_pay_ratio": 0.8
        })
        self.assertEqual(disp_res.status_code, 200)
        disp_data = disp_res.json()
        dispense_id = disp_data["dispense_id"]

        # 5. Fetch Receipt
        rec_res = client.get(f"/api/v1/pharmacy/dispenses/{dispense_id}")
        self.assertEqual(rec_res.status_code, 200)
        self.assertEqual(rec_res.json()["gross_total"], 48.00) # 20 * 2.40
