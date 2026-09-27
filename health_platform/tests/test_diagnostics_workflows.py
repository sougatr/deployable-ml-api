"""
Unit and Integration Tests for Diagnostic Laboratory & Radiology Information System (LIS/RIS).
Verifies:
1. Standard LOINC & SNOMED CT coded catalog.
2. Phlebotomy specimen collection with barcode & accession tracking.
3. Automated parameter reference range flagging (NORMAL, HIGH, CRITICAL_HIGH).
4. Consultant Pathologist / Radiologist verification & digital signature.
5. Clinical-Financial Invariant: Originating charge item capture with zero trial balance discrepancy.
6. API endpoint integration.
"""

import unittest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.diagnostics.models import (
    DiagnosticCategory,
    DiagnosticModality,
    DiagnosticStatus,
    AbnormalFlag,
    DiagnosticOrderInput,
    SpecimenCollectionInput,
    LabResultEntryInput,
    RadiologyReportEntryInput,
    VerificationInput
)
from health_platform.core.diagnostics.service import DiagnosticsService
from health_platform.api.app import app

client = TestClient(app)

class TestDiagnosticsWorkflows(unittest.TestCase):
    def setUp(self):
        self.identity = PatientIdentityService()
        self.financial = FinancialLedgerService()
        self.outbox = TransactionalOutboxPublisher()
        self.diagnostics = DiagnosticsService(
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

    def test_01_catalog_standard_coding(self):
        catalog = self.diagnostics.get_catalog()
        self.assertTrue(len(catalog) >= 6)

        # Verify LOINC code for HbA1c
        hba1c_item = self.diagnostics.get_catalog_item("LAB-BIO-042")
        self.assertIsNotNone(hba1c_item)
        self.assertEqual(hba1c_item.standard_code, "4548-4")
        self.assertEqual(hba1c_item.category, DiagnosticCategory.LABORATORY)
        self.assertEqual(len(hba1c_item.parameters), 2)

        # Verify SNOMED CT code for Chest X-Ray
        cxr_item = self.diagnostics.get_catalog_item("RAD-XRAY-001")
        self.assertIsNotNone(cxr_item)
        self.assertEqual(cxr_item.standard_code, "168731009")
        self.assertEqual(cxr_item.category, DiagnosticCategory.RADIOLOGY)

    def test_02_lab_order_specimen_collection_and_flags(self):
        # 1. Order HbA1c
        order = self.diagnostics.create_order(
            DiagnosticOrderInput(
                mpi_id=self.mpi_id,
                encounter_id=self.encounter_id,
                item_code="LAB-BIO-042",
                ordering_doctor_name="Dr. Anup Khatri",
                clinical_history="Pre-op evaluation for knee arthroscopy"
            )
        )
        self.assertIsNotNone(order.order_id)
        self.assertEqual(order.status, DiagnosticStatus.ORDERED)
        self.assertIsNotNone(order.charge_item_id)

        # 2. Specimen Collection by Phlebotomist
        collected_order = self.diagnostics.collect_specimen(
            SpecimenCollectionInput(
                order_id=order.order_id,
                phlebotomist_name="Sunita Sharma, CPT"
            )
        )
        self.assertEqual(collected_order.status, DiagnosticStatus.SAMPLE_COLLECTED)
        self.assertTrue(collected_order.sample_barcode.startswith("SMP-BIO-"))
        self.assertTrue(collected_order.accession_number.startswith("ACC-"))

        # 3. Enter Elevated Lab Results (HbA1c = 7.4% -> HIGH, eAG = 165 mg/dL -> HIGH)
        resulted_order = self.diagnostics.enter_lab_results(
            LabResultEntryInput(
                order_id=order.order_id,
                parameter_results={
                    "HBA1C": 7.4,
                    "EAG": 165.0
                }
            )
        )
        self.assertEqual(resulted_order.status, DiagnosticStatus.RESULTED)
        self.assertEqual(len(resulted_order.lab_results), 2)
        hba1c_res = [r for r in resulted_order.lab_results if r.parameter_code == "HBA1C"][0]
        self.assertEqual(hba1c_res.flag, AbnormalFlag.HIGH)
        self.assertEqual(hba1c_res.measured_value, "7.40")

        # 4. Pathologist Verification & Digital Signature
        verified_order = self.diagnostics.verify_and_publish_report(
            VerificationInput(
                order_id=order.order_id,
                verifier_name="Dr. Rajiv Sethi",
                verifier_qualification="MD (Pathology)",
                verifier_registration_no="MMC-1998040112",
                clinical_comments="Elevated glycated hemoglobin consistent with suboptimally controlled Type 2 Diabetes."
            )
        )
        self.assertEqual(verified_order.status, DiagnosticStatus.VERIFIED)
        self.assertIn("Dr. Rajiv Sethi", verified_order.verified_by)

        # Verify Financial Ledger Invariant has zero discrepancy!
        discrepancy = self.financial.get_trial_balance_discrepancy()
        self.assertEqual(discrepancy, 0.0)

    def test_03_critical_value_alert_flagging(self):
        # Order CBC
        order = self.diagnostics.create_order(
            DiagnosticOrderInput(
                mpi_id=self.mpi_id,
                encounter_id=self.encounter_id,
                item_code="LAB-HEM-001",
                ordering_doctor_name="Dr. Anup Khatri"
            )
        )
        self.diagnostics.collect_specimen(
            SpecimenCollectionInput(
                order_id=order.order_id,
                phlebotomist_name="Sunita Sharma, CPT"
            )
        )
        # Severe Anemia: Hemoglobin = 5.8 g/dL (Critical Low < 7.0)
        res_order = self.diagnostics.enter_lab_results(
            LabResultEntryInput(
                order_id=order.order_id,
                parameter_results={
                    "HB": 5.8,
                    "TLC": 8500.0,
                    "PLT": 250.0,
                    "PCV": 18.0
                }
            )
        )
        hb_res = [r for r in res_order.lab_results if r.parameter_code == "HB"][0]
        self.assertEqual(hb_res.flag, AbnormalFlag.CRITICAL_LOW)

    def test_04_radiology_mri_reporting_workflow(self):
        # Order MRI Right Knee Joint
        order = self.diagnostics.create_order(
            DiagnosticOrderInput(
                mpi_id=self.mpi_id,
                encounter_id=self.encounter_id,
                item_code="RAD-MRI-002",
                ordering_doctor_name="Dr. Anup Khatri",
                clinical_history="Right knee pain and locking sensation after sports twist"
            )
        )
        self.assertEqual(order.category, DiagnosticCategory.RADIOLOGY)
        self.assertEqual(order.tariff_amount, 6500.0)

        # Imaging study conducted
        order = self.diagnostics.collect_specimen(
            SpecimenCollectionInput(
                order_id=order.order_id,
                phlebotomist_name="Ganesh Jadhav (Senior MRI Radiographer)"
            )
        )
        self.assertEqual(order.status, DiagnosticStatus.SAMPLE_COLLECTED)

        # Radiologist Report Entry
        rep_order = self.diagnostics.enter_radiology_report(
            RadiologyReportEntryInput(
                order_id=order.order_id,
                radiologist_name="Dr. Meenakshi Sundaram, DMRD, DNB (Radiodiagnosis)",
                clinical_indication="Right knee trauma, suspected meniscus injury.",
                technique="Multiplanar, multisequence MRI of right knee joint on 3.0 Tesla scanner.",
                findings="Full-thickness radial tear involving posterior horn and root attachment of medial meniscus. Joint effusion present. ACL and PCL intact.",
                impression="Medial meniscus posterior root tear (Type 2). Orthopaedic arthroscopic repair recommended."
            )
        )
        self.assertEqual(rep_order.status, DiagnosticStatus.RESULTED)

        # Radiologist Verification
        verified = self.diagnostics.verify_and_publish_report(
            VerificationInput(
                order_id=order.order_id,
                verifier_name="Dr. Meenakshi Sundaram",
                verifier_qualification="MD (Radiodiagnosis)",
                verifier_registration_no="MMC-2004090881"
            )
        )
        self.assertEqual(verified.status, DiagnosticStatus.VERIFIED)
        self.assertIn("Medial meniscus posterior root tear", verified.radiology_impression)

    def test_05_api_diagnostics_endpoints(self):
        # 1. Catalog
        res = client.get("/api/v1/diagnostics/catalog")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertTrue(len(items) >= 6)

        # 2. Register patient
        reg_res = client.post("/api/v1/identity/resolve", json={
            "first_name": "Pooja",
            "last_name": "Verma",
            "dob": "1992-06-15",
            "gender": "FEMALE",
            "primary_phone": "+919876543210",
            "postal_code": "400050",
            "identifiers": []
        })
        mpi_id = reg_res.json()["mpi_id"]
        enc_id = str(uuid.uuid4())

        # 3. Create Order via API
        ord_res = client.post("/api/v1/diagnostics/orders", json={
            "mpi_id": mpi_id,
            "encounter_id": enc_id,
            "item_code": "LAB-BIO-010",
            "ordering_doctor_name": "Dr. Anup Khatri",
            "clinical_history": "Pre-op kidney function screening"
        })
        self.assertEqual(ord_res.status_code, 200)
        order_data = ord_res.json()
        order_id = order_data["order_id"]

        # 4. Worklist
        wl_res = client.get("/api/v1/diagnostics/worklist")
        self.assertEqual(wl_res.status_code, 200)

        # 5. Collect Specimen
        col_res = client.post("/api/v1/diagnostics/specimens/collect", json={
            "order_id": order_id,
            "phlebotomist_name": "Sunita Sharma, CPT"
        })
        self.assertEqual(col_res.status_code, 200)
        self.assertEqual(col_res.json()["status"], "SAMPLE_COLLECTED")

        # 6. Enter Results
        res_res = client.post("/api/v1/diagnostics/results/lab", json={
            "order_id": order_id,
            "parameter_results": {
                "CREAT": 0.9,
                "BUN": 14.0,
                "NA": 140.0,
                "K": 4.2
            }
        })
        self.assertEqual(res_res.status_code, 200)
        self.assertEqual(res_res.json()["status"], "RESULTED")

        # 7. Verify Report
        ver_res = client.post("/api/v1/diagnostics/reports/verify", json={
            "order_id": order_id,
            "verifier_name": "Dr. Rajiv Sethi",
            "verifier_qualification": "MD (Pathology)",
            "verifier_registration_no": "MMC-1998040112"
        })
        self.assertEqual(ver_res.status_code, 200)
        self.assertEqual(ver_res.json()["status"], "VERIFIED")
