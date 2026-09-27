import unittest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.ipd.models import (
    BedStatus,
    WardType,
    IPDAdmissionInput,
    NurseChartEntryInput,
    DoctorRoundInput,
    DischargeInput
)
from health_platform.core.ipd.service import IPDService
from health_platform.api.app import app

client = TestClient(app)

class TestIPDWorkflows(unittest.TestCase):
    def setUp(self):
        self.identity = PatientIdentityService()
        self.financial = FinancialLedgerService()
        self.outbox = TransactionalOutboxPublisher()
        self.ipd = IPDService(
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

    def test_01_bed_matrix_initialization(self):
        beds = self.ipd.get_bed_matrix()
        self.assertEqual(len(beds), 8)
        self.assertTrue(all(b.status == BedStatus.AVAILABLE for b in beds))
        icu_beds = [b for b in beds if b.ward_type == WardType.ICU]
        self.assertEqual(len(icu_beds), 2)
        self.assertEqual(icu_beds[0].daily_rate, 7500.0)

    def test_02_patient_admission_and_bed_occupancy(self):
        beds = self.ipd.get_bed_matrix()
        target_bed = beds[0]

        adm = self.ipd.admit_patient(
            IPDAdmissionInput(
                mpi_id=self.mpi_id,
                bed_id=target_bed.bed_id,
                admitting_doctor_name="Dr. Anup Khatri",
                admitting_diagnosis_icd10="M23.30",
                admitting_diagnosis_display="Tear of medial meniscus of knee (Status Post Root Repair)",
                admission_reason="Post-operative rehabilitation and observation"
            )
        )

        self.assertIsNotNone(adm.admission_id)
        self.assertEqual(adm.status, "ADMITTED")

        # Verify bed is OCCUPIED
        updated_bed = self.ipd.get_bed(target_bed.bed_id)
        self.assertEqual(updated_bed.status, BedStatus.OCCUPIED)
        self.assertEqual(updated_bed.current_admission_id, adm.admission_id)
        self.assertIn("Anindita Ray", updated_bed.current_patient_name)

        # Verify initial nurse baseline chart
        charts = self.ipd.get_nurse_charts(adm.admission_id)
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0].systolic_bp, 120.0)

        # Verify double admission to same bed is rejected
        with self.assertRaises(ValueError):
            self.ipd.admit_patient(
                IPDAdmissionInput(
                    mpi_id=self.mpi_id,
                    bed_id=target_bed.bed_id,
                    admitting_doctor_name="Dr. Anup Khatri"
                )
            )

    def test_03_nurse_charting_and_doctor_rounds(self):
        beds = self.ipd.get_bed_matrix()
        target_bed = beds[2] # Room 401

        adm = self.ipd.admit_patient(
            IPDAdmissionInput(
                mpi_id=self.mpi_id,
                bed_id=target_bed.bed_id,
                admitting_doctor_name="Dr. Anup Khatri"
            )
        )

        # Log nurse shift chart
        chart = self.ipd.record_nurse_charting(
            NurseChartEntryInput(
                admission_id=adm.admission_id,
                systolic_bp=124.0,
                diastolic_bp=82.0,
                heart_rate=76.0,
                temperature=98.4,
                spo2=99.0,
                respiratory_rate=16.0,
                nursing_notes="Evening vitals normal. Ice pack applied to right knee."
            )
        )
        self.assertIsNotNone(chart.chart_id)
        all_charts = self.ipd.get_nurse_charts(adm.admission_id)
        self.assertEqual(len(all_charts), 2) # Baseline + Evening chart

        # Log doctor progress round
        round_note = self.ipd.record_doctor_round(
            DoctorRoundInput(
                admission_id=adm.admission_id,
                doctor_name="Dr. Anup Khatri",
                round_notes="Morning round. Knee swelling minimal. Pain controlled on oral analgesic.",
                clinical_assessment="Satisfactory post-operative course.",
                plan_adjustments="Step down IV fluids. Continue oral calcium and physiotherapy."
            )
        )
        self.assertIsNotNone(round_note.round_id)
        all_rounds = self.ipd.get_doctor_rounds(adm.admission_id)
        self.assertEqual(len(all_rounds), 1)

    def test_04_patient_discharge_and_room_charge_accrual(self):
        beds = self.ipd.get_bed_matrix()
        target_bed = beds[4] # Bed 201-A (₹2,800/day)

        adm = self.ipd.admit_patient(
            IPDAdmissionInput(
                mpi_id=self.mpi_id,
                bed_id=target_bed.bed_id,
                admitting_doctor_name="Dr. Anup Khatri",
                admitting_diagnosis_icd10="M23.30"
            )
        )

        # Verify bed is occupied
        self.assertEqual(self.ipd.get_bed(target_bed.bed_id).status, BedStatus.OCCUPIED)

        # Discharge patient
        summary = self.ipd.discharge_patient(
            DischargeInput(
                admission_id=adm.admission_id,
                condition_at_discharge="Stable, pain free at rest, mobilizing with crutches",
                hospital_course="Underwent Right Medial Meniscus Root repair. Stable recovery.",
                final_diagnosis_icd10="M23.30",
                final_diagnosis_display="Tear of medial meniscus of knee (Status Post Root Repair)",
                discharge_medications="Tab Ezorb Forte 0-1-0 x 90 days",
                follow_up_advice="NWB x 10 days, OPD review in 2 weeks.",
                doctor_signature="Dr. Anup Khatri (MMC-2006010368)"
            )
        )

        self.assertIsNotNone(summary.summary_id)
        self.assertEqual(summary.days_stayed, 1) # Minimum 1 day billing
        self.assertEqual(summary.total_room_charges, 2800.0)

        # Verify bed is released back to AVAILABLE
        self.assertEqual(self.ipd.get_bed(target_bed.bed_id).status, BedStatus.AVAILABLE)

        # Verify Financial Ledger: room charges posted and trial balance has zero discrepancy!
        discrepancy = self.financial.get_trial_balance_discrepancy()
        self.assertEqual(discrepancy, 0.0)

    def test_05_api_ipd_endpoints(self):
        # 1. Get Beds
        res = client.get("/api/v1/ipd/beds")
        self.assertEqual(res.status_code, 200)
        beds_json = res.json()
        self.assertTrue(len(beds_json) >= 8)

        # Register patient via API
        reg_res = client.post("/api/v1/identity/resolve", json={
            "first_name": "Rohan",
            "last_name": "Mehta",
            "dob": "1985-02-12",
            "gender": "MALE",
            "primary_phone": "+919988776655",
            "postal_code": "400012",
            "identifiers": []
        })
        self.assertEqual(reg_res.status_code, 200)
        mpi_id = reg_res.json()["mpi_id"]
        bed_id = beds_json[6]["bed_id"] # General Ward Bed GW-101

        # 2. Admit via API
        adm_res = client.post("/api/v1/ipd/admit", json={
            "mpi_id": mpi_id,
            "bed_id": bed_id,
            "admitting_doctor_name": "Dr. Anup Khatri",
            "admitting_diagnosis_icd10": "M23.30",
            "admitting_diagnosis_display": "Tear of medial meniscus of knee",
            "admission_reason": "Post-op care"
        })
        self.assertEqual(adm_res.status_code, 200)
        adm_data = adm_res.json()
        admission_id = adm_data["admission_id"]

        # 3. Nurse Charting via API
        chart_res = client.post("/api/v1/ipd/nursing/charts", json={
            "admission_id": admission_id,
            "systolic_bp": 118.0,
            "diastolic_bp": 78.0,
            "heart_rate": 72.0,
            "temperature": 98.4,
            "spo2": 99.0,
            "respiratory_rate": 16.0,
            "nursing_notes": "Vitals stable."
        })
        self.assertEqual(chart_res.status_code, 200)

        # 4. Doctor Round via API
        round_res = client.post("/api/v1/ipd/doctor/rounds", json={
            "admission_id": admission_id,
            "doctor_name": "Dr. Anup Khatri",
            "round_notes": "Normal recovery.",
            "clinical_assessment": "Good progress.",
            "plan_adjustments": "Discharge tomorrow."
        })
        self.assertEqual(round_res.status_code, 200)

        # 5. Discharge via API
        dc_res = client.post("/api/v1/ipd/discharge", json={
            "admission_id": admission_id,
            "condition_at_discharge": "Healed, stable.",
            "hospital_course": "Good.",
            "final_diagnosis_icd10": "M23.30",
            "final_diagnosis_display": "Tear of medial meniscus of knee",
            "discharge_medications": "Tab Ezorb Forte",
            "follow_up_advice": "Rest",
            "doctor_signature": "Dr. Anup Khatri"
        })
        self.assertEqual(dc_res.status_code, 200)
        dc_data = dc_res.json()
        self.assertTrue(dc_data["total_room_charges"] > 0)

if __name__ == "__main__":
    unittest.main()
