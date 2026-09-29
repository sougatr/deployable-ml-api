"""
Tests for Patient / Client Dashboard & AI Health Portal (Pod 9).
Verifies longitudinal EHR aggregation, AI medical interpretations of conditions,
lab/scan reports, medication guides, personalized diet & exercise plans,
and interactive AI companion queries.
"""

import uuid
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.interop.abdm_m1_m2 import ABDMGatewayBridge
from health_platform.core.clinical.service import ClinicalEncounterService
from health_platform.core.clinical.models import (
    ConsultationInput,
    ConditionInput,
    PrescriptionItemInput,
    VitalSignInput
)
from health_platform.core.diagnostics.service import DiagnosticsService
from health_platform.core.diagnostics.models import (
    DiagnosticOrderInput,
    RadiologyReportEntryInput,
    VerificationInput
)
from health_platform.core.pharmacy.service import PharmacyService
from health_platform.core.ipd.service import IPDService
from health_platform.core.ipd.models import IPDAdmissionInput, WardType, BedStatus
from health_platform.core.emergency.service import EmergencyService
from health_platform.core.patient_portal.service import PatientPortalService
from health_platform.core.patient_portal.models import PatientAIQueryInput
from health_platform.api.app import app, identity_service as app_identity_service

class TestPatientPortal(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.identity = PatientIdentityService()
        self.financial = FinancialLedgerService()
        self.outbox = TransactionalOutboxPublisher()
        self.abdm = ABDMGatewayBridge(identity_service=self.identity)

        self.clinical = ClinicalEncounterService(
            identity_service=self.identity,
            financial_service=self.financial,
            abdm_bridge=self.abdm,
            outbox=self.outbox
        )
        self.diagnostics = DiagnosticsService(
            identity_service=self.identity,
            financial_service=self.financial,
            outbox=self.outbox
        )
        self.pharmacy = PharmacyService(
            identity_service=self.identity,
            financial_service=self.financial,
            outbox=self.outbox
        )
        self.ipd = IPDService(
            identity_service=self.identity,
            financial_service=self.financial,
            outbox=self.outbox
        )
        self.emergency = EmergencyService(
            identity_service=self.identity,
            financial_service=self.financial,
            ipd_service=self.ipd,
            outbox=self.outbox
        )
        self.portal = PatientPortalService(
            identity_service=self.identity,
            clinical_service=self.clinical,
            diagnostics_service=self.diagnostics,
            pharmacy_service=self.pharmacy,
            ipd_service=self.ipd,
            emergency_service=self.emergency
        )

        # Register Orthopedic Patient
        self.patient_res = self.identity.resolve_or_create_patient(
            PatientRegistrationRequest(
                first_name="Ramesh",
                last_name="Verma",
                dob="1982-04-12",
                gender="MALE",
                primary_phone="+919876543210",
                postal_code="110001",
                identifiers=[]
            )
        )
        self.mpi_id = self.patient_res.mpi_id

    def test_01_patient_portal_summary_orthopedic(self):
        """Verifies full synthesis of disease profile, MRI report, prescription guide, and recovery plan."""
        # 1. Inpatient admission for Meniscus Root Repair
        beds = self.ipd.get_bed_matrix()
        bed = [b for b in beds if b.status == BedStatus.AVAILABLE and b.ward_type == WardType.DELUXE_PRIVATE][0]
        adm = self.ipd.admit_patient(
            IPDAdmissionInput(
                mpi_id=self.mpi_id,
                bed_id=bed.bed_id,
                admitting_doctor_name="Dr. Anup Khatri (MS Ortho)",
                admitting_diagnosis_icd10="M23.30",
                admitting_diagnosis_display="Tear of medial meniscus of knee (Status Post Root Repair)",
                admission_reason="Post-operative orthopedic care, rehabilitation & observation"
            )
        )

        # 2. Diagnostic MRI Knee Order and Verification
        order = self.diagnostics.create_order(
            DiagnosticOrderInput(
                encounter_id=adm.encounter_id,
                mpi_id=self.mpi_id,
                item_code="RAD-MRI-002",
                ordering_doctor_name="Dr. Anup Khatri",
                clinical_history="Post-operative status check, posterior horn root repair evaluation"
            )
        )
        self.diagnostics.enter_radiology_report(
            RadiologyReportEntryInput(
                order_id=order.order_id,
                radiologist_name="Dr. Alok Sen (MD Radiodiagnosis)",
                clinical_indication="Post-op root repair status",
                technique="Multi-planar 3T Knee MRI",
                findings="Properly seated suture anchor at the medial meniscal root. Intact ACL and PCL. Minimal joint effusion.",
                impression="Normal post-operative appearance of repaired medial meniscal root with good anchor fixation."
            )
        )
        self.diagnostics.verify_and_publish_report(
            VerificationInput(
                order_id=order.order_id,
                verifier_name="Dr. Alok Sen",
                verifier_qualification="MD Radiodiagnosis",
                verifier_registration_no="DMC-RAD-88120"
            )
        )

        # 3. Clinical OPD Note with Prescriptions
        enc_id = self.clinical.start_opd_encounter(
            mpi_id=self.mpi_id,
            practitioner_id=uuid.uuid4(),
            facility_id=uuid.uuid4(),
            tenant_id=uuid.uuid4()
        )
        self.clinical.complete_consultation(
            ConsultationInput(
                encounter_id=enc_id,
                practitioner_id=uuid.uuid4(),
                chief_complaint="Post-op review: Knee stiffness in the morning",
                clinical_narrative="Surgical incision healing well. No active drainage. Passive flexion to 70 degrees.",
                diagnoses=[
                    ConditionInput(
                        code_icd10="M23.30",
                        display="Tear of medial meniscus of knee (Status Post Repair)"
                    )
                ],
                vitals=[
                    VitalSignInput(
                        code_loinc="8480-6",
                        display="Systolic Blood Pressure",
                        value=122.0,
                        unit="mm[Hg]"
                    )
                ],
                prescriptions=[
                    PrescriptionItemInput(
                        brand_name="Hifenac-P",
                        generic_name="Aceclofenac 100mg + Paracetamol 325mg",
                        dosage_form="TABLET",
                        timing="1-0-1",
                        duration_days=5,
                        instructions="Take with food twice daily"
                    ),
                    PrescriptionItemInput(
                        brand_name="Pan-40",
                        generic_name="Pantoprazole 40mg",
                        dosage_form="CAPSULE",
                        timing="1-0-0",
                        duration_days=5,
                        instructions="Take 30 mins before breakfast"
                    )
                ],
                orders=[],
                doctor_digital_signature="Dr. Anup Khatri (MCI-18290)"
            )
        )

        # 4. Fetch Portal Summary
        summary = self.portal.get_patient_portal_summary(self.mpi_id)
        self.assertEqual(summary.full_name, "Ramesh Verma")
        self.assertIn("Inpatient", summary.current_care_setting)

        # Verify Disease Profile & AI Interpretation
        self.assertGreaterEqual(len(summary.disease_profiles), 1)
        profile = summary.disease_profiles[0]
        self.assertIn("meniscus", profile.condition_name.lower())
        self.assertIn("cartilage", profile.plain_english_summary.lower())
        self.assertEqual(profile.severity_level, "Moderate")

        # Verify Lab & Scan Reports with AI Takeaway
        self.assertGreaterEqual(len(summary.lab_and_scan_reports), 1)
        scan = summary.lab_and_scan_reports[0]
        self.assertIn("MRI", scan.test_name)
        self.assertIn("Radiology Impression", scan.ai_clinical_takeaway)
        self.assertIsNotNone(scan.radiology_findings)

        # Verify Prescriptions with Food & Timing Advice
        self.assertGreaterEqual(len(summary.active_prescriptions), 2)
        aceclofenac = [m for m in summary.active_prescriptions if "aceclofenac" in m.drug_name.lower()][0]
        self.assertIn("anti-inflammatory", aceclofenac.purpose_ai.lower())
        self.assertIn("AFTER food", aceclofenac.food_instructions)

        panto = [m for m in summary.active_prescriptions if "pantoprazole" in m.drug_name.lower()][0]
        self.assertIn("EMPTY stomach", panto.food_instructions)

        # Verify AI Health Recommendations (Prognosis, Diet, Exercises, Red Flags)
        recs = summary.ai_recommendations
        self.assertIn("6 to 12 weeks", recs.prognosis_overview)
        self.assertGreaterEqual(len(recs.prognosis_milestones), 3)

        # Check Diet Recommendations
        food_items = [d.food_item.lower() for d in recs.dietary_guidelines]
        self.assertTrue(any("turmeric" in f for f in food_items))
        self.assertTrue(any("omega-3" in f for f in food_items))

        # Check Exercises
        ex_names = [e.exercise_name.lower() for e in recs.exercise_routine]
        self.assertTrue(any("quad" in e for e in ex_names))
        self.assertTrue(any("ankle" in e for e in ex_names))

        # Check Red Flags
        self.assertTrue(any("dvt" in r.lower() or "calf" in r.lower() for r in recs.red_flag_warning_signs))

    def test_02_patient_ai_query_assistant(self):
        """Verifies interactive patient AI queries on medication interactions, morning stiffness, and exercises."""
        # Ask about coffee with morning medications
        q1 = PatientAIQueryInput(
            mpi_id=self.mpi_id,
            question="Can I drink coffee with my morning medicines?"
        )
        res1 = self.portal.answer_patient_ai_query(q1)
        self.assertIn("Ramesh Verma", res1.answer)
        self.assertIn("Pantoprazole", res1.answer)
        self.assertIn("30 minutes BEFORE", res1.answer)

        # Ask about morning stiffness
        q2 = PatientAIQueryInput(
            mpi_id=self.mpi_id,
            question="Why is my knee so stiff in the morning and what can I do?"
        )
        res2 = self.portal.answer_patient_ai_query(q2)
        self.assertIn("Ankle Pumps", res2.answer)
        self.assertIn("Quad Sets", res2.answer)

        # Ask about exercises to avoid
        q3 = PatientAIQueryInput(
            mpi_id=self.mpi_id,
            question="What exercises should I strictly avoid this week?"
        )
        res3 = self.portal.answer_patient_ai_query(q3)
        self.assertIn("squats", res3.answer.lower())
        self.assertIn("avoid", res3.answer.lower())

    def test_03_portal_api_endpoints(self):
        """Verifies REST endpoints for patient portal summary and AI queries."""
        # Register a patient in app_identity_service
        app_res = app_identity_service.resolve_or_create_patient(
            PatientRegistrationRequest(
                first_name="Pooja",
                last_name="Sharma",
                dob="1990-08-15",
                gender="FEMALE",
                primary_phone="+919876543299",
                postal_code="110016",
                identifiers=[]
            )
        )
        mpi_id = app_res.mpi_id

        # 1. GET /api/v1/portal/patients/{mpi_id}/summary
        resp = self.client.get(f"/api/v1/portal/patients/{mpi_id}/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["full_name"], "Pooja Sharma")
        self.assertIn("disease_profiles", data)
        self.assertIn("ai_recommendations", data)

        # 2. POST /api/v1/portal/ai-query
        resp = self.client.post("/api/v1/portal/ai-query", json={
            "mpi_id": str(mpi_id),
            "question": "What foods should I eat to recover faster?"
        })
        self.assertEqual(resp.status_code, 200)
        ai_resp = resp.json()
        self.assertIn("Pooja Sharma", ai_resp["answer"])
        self.assertIn("safety_disclaimer", ai_resp)

    def test_04_portal_self_entry_and_auto_seed_ehr(self):
        """Verifies self-entry typing for diagnoses, labs, meds, and hospital EHR auto-seeding."""
        app_res = app_identity_service.resolve_or_create_patient(
            PatientRegistrationRequest(
                first_name="Anindita",
                last_name="Ray",
                dob="1992-06-20",
                gender="FEMALE",
                primary_phone="+919876500000",
                postal_code="700001",
                identifiers=[]
            )
        )
        mpi_id = app_res.mpi_id

        # 1. Test GET /api/v1/patients/search
        resp = self.client.get("/api/v1/patients/search?q=Anindita")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()
        self.assertTrue(len(results) >= 1)
        self.assertTrue(any(p["first_name"] == "Anindita" for p in results))

        # 2. Self-Entry Condition
        resp = self.client.post(f"/api/v1/portal/patients/{mpi_id}/self-entry/condition", json={
            "condition_name": "Post-Op Right Knee Meniscus Root Repair",
            "icd10_code": "M23.30",
            "severity_level": "Moderate",
            "notes": "Mild morning stiffness, pain score 2/10 when mobilizing."
        })
        self.assertEqual(resp.status_code, 200)
        item = resp.json()
        self.assertEqual(item["condition_name"], "Post-Op Right Knee Meniscus Root Repair")
        self.assertIn("meniscus", item["plain_english_summary"].lower())

        # 3. Self-Entry Lab Report
        resp = self.client.post(f"/api/v1/portal/patients/{mpi_id}/self-entry/lab", json={
            "test_name": "Serum C-Reactive Protein (CRP)",
            "category": "LABORATORY",
            "measured_value": 3.2,
            "unit": "mg/L",
            "reference_interval": "0.0 - 5.0 mg/L",
            "status": "NORMAL",
            "impression": "Normal inflammatory marker level indicating good healing."
        })
        self.assertEqual(resp.status_code, 200)
        lab_item = resp.json()
        self.assertEqual(lab_item["test_name"], "Serum C-Reactive Protein (CRP)")
        self.assertEqual(lab_item["parameters"][0]["measured_value"], 3.2)

        # 4. Self-Entry Medication
        resp = self.client.post(f"/api/v1/portal/patients/{mpi_id}/self-entry/medication", json={
            "drug_name": "Tab Aceclofenac 100mg + Paracetamol 325mg",
            "dosage": "1 Tab",
            "frequency": "1-0-1",
            "duration": "5 Days",
            "instructions": "Strictly post meals with full glass of water"
        })
        self.assertEqual(resp.status_code, 200)
        med_item = resp.json()
        self.assertIn("Aceclofenac", med_item["drug_name"])
        self.assertIn("anti-inflammatory", med_item["purpose_ai"].lower())

        # 5. Auto-Seed EHR
        resp = self.client.post(f"/api/v1/portal/patients/{mpi_id}/auto-seed-ehr")
        self.assertEqual(resp.status_code, 200)
        seed_res = resp.json()
        self.assertEqual(seed_res["status"], "success")

        # 6. Verify Summary reflects both self-entered and seeded EHR records
        resp = self.client.get(f"/api/v1/portal/patients/{mpi_id}/summary")
        self.assertEqual(resp.status_code, 200)
        summary = resp.json()
        self.assertTrue(len(summary["disease_profiles"]) >= 1)
        self.assertTrue(len(summary["lab_and_scan_reports"]) >= 1)
        self.assertTrue(len(summary["active_prescriptions"]) >= 1)

if __name__ == "__main__":
    unittest.main()
