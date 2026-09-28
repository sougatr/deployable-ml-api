"""
Tests for Emergency Department (ED / ER) & Triage (Manchester / ESI Protocol).
Verifies ESI triage intake, resuscitation intervention logs, ER-to-IPD admission transfers,
and absolute zero financial ledger discrepancy.
"""

import uuid
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from health_platform.core.identity.models import PatientRegistrationRequest
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.ipd.service import IPDService
from health_platform.core.ipd.models import WardType, BedStatus
from health_platform.core.emergency.models import (
    ESITriageLevel,
    ERBayType,
    ERBayStatus,
    ERDispositionType,
    ERCaseStatus,
    TriageAssessmentInput,
    ResuscitationInterventionInput,
    ERDispositionInput
)
from health_platform.core.emergency.service import EmergencyService
from health_platform.api.app import app, identity_service as app_identity_service

class TestEmergencyWorkflows(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.identity = PatientIdentityService()
        self.financial = FinancialLedgerService()
        self.outbox = TransactionalOutboxPublisher()
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

        # Register a test patient in local identity service
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

    def test_01_er_bay_seeding(self):
        """Verifies initial ER bays are seeded and available."""
        bays = self.emergency.get_er_bays()
        self.assertEqual(len(bays), 6)
        resus_bays = [b for b in bays if b.bay_type == ERBayType.RESUSCITATION_BAY]
        self.assertEqual(len(resus_bays), 2)
        for b in bays:
            self.assertEqual(b.status, ERBayStatus.AVAILABLE)

    def test_02_triage_level_1_code_red(self):
        """Verifies Level 1 Red triage assigns a Resuscitation Bay and posts triage fee."""
        triage_in = TriageAssessmentInput(
            mpi_id=self.mpi_id,
            chief_complaint="Severe chest pain, diaphoresis, unresponsiveness",
            triage_level=ESITriageLevel.LEVEL_1_RED,
            gcs_score=7,
            systolic_bp=75.0,
            diastolic_bp=45.0,
            heart_rate=135.0,
            respiratory_rate=28.0,
            spo2=86.0,
            temperature=98.4,
            pain_score=10,
            mode_of_arrival="AMBULANCE_ALS",
            triage_nurse_name="Sister Sunita Rao, RN"
        )
        case = self.emergency.triage_patient(triage_in)
        self.assertIsNotNone(case.case_id)
        self.assertEqual(case.triage_level, ESITriageLevel.LEVEL_1_RED)
        self.assertEqual(case.status, ERCaseStatus.RESUSCITATION_ACTIVE)
        self.assertIn("RESUS", case.allocated_bay_number)

        # Bay occupied check
        bay = self.emergency.get_bay(case.allocated_bay_id)
        self.assertEqual(bay.status, ERBayStatus.OCCUPIED)
        self.assertEqual(bay.current_case_id, case.case_id)

        # Financial Ledger check (zero discrepancy)
        self.assertEqual(self.financial.get_trial_balance_discrepancy(), 0.0)
        self.assertEqual(case.total_er_charges, 2500.0)

    def test_03_resuscitation_interventions_and_procedural_charges(self):
        """Verifies resuscitation interventions can be logged and billed accurately."""
        triage_in = TriageAssessmentInput(
            mpi_id=self.mpi_id,
            chief_complaint="Ventricular tachycardia with hemodynamic instability",
            triage_level=ESITriageLevel.LEVEL_1_RED,
            gcs_score=8,
            systolic_bp=60.0,
            diastolic_bp=30.0,
            heart_rate=160.0,
            respiratory_rate=30.0,
            spo2=82.0,
            temperature=98.2,
            mode_of_arrival="AMBULANCE_ALS",
            triage_nurse_name="Sister Sunita Rao, RN"
        )
        case = self.emergency.triage_patient(triage_in)

        # Defibrillation
        interv1 = self.emergency.record_resuscitation_intervention(
            ResuscitationInterventionInput(
                case_id=case.case_id,
                intervention_type="DEFIBRILLATION",
                details="Synchronized cardioversion 100J delivered, converted to sinus rhythm",
                medications_given="Inj Amiodarone 150mg IV bolus",
                clinician_name="Dr. Vikram Seth (ED Attending)",
                gcs_post=12,
                vitals_post="BP 105/70, HR 92, SpO2 96% on 4L O2"
            )
        )
        self.assertEqual(len(case.interventions), 1)
        self.assertEqual(interv1.intervention_type, "DEFIBRILLATION")

        # Intubation
        interv2 = self.emergency.record_resuscitation_intervention(
            ResuscitationInterventionInput(
                case_id=case.case_id,
                intervention_type="INTUBATION",
                details="RSI performed. Video laryngoscopy ETT 7.5mm placed at 22cm depth",
                medications_given="Inj Propofol 100mg, Inj Rocuronium 50mg",
                clinician_name="Dr. Vikram Seth (ED Attending)",
                gcs_post=3,
                vitals_post="BP 115/75, HR 85, SpO2 99% on FiO2 60%"
            )
        )
        self.assertEqual(len(case.interventions), 2)
        # Total charges = ₹2,500 (triage) + ₹1,200 * 2 (procedures) = ₹4,900
        self.assertEqual(case.total_er_charges, 4900.0)
        self.assertEqual(self.financial.get_trial_balance_discrepancy(), 0.0)

    def test_04_er_to_ipd_admission_pipeline(self):
        """Verifies disposition admitting patient directly from ER to ICU transfers bed and frees ER bay."""
        triage_in = TriageAssessmentInput(
            mpi_id=self.mpi_id,
            chief_complaint="Acute Anterior Wall STEMI",
            triage_level=ESITriageLevel.LEVEL_1_RED,
            gcs_score=14,
            systolic_bp=100.0,
            diastolic_bp=65.0,
            heart_rate=110.0,
            respiratory_rate=24.0,
            spo2=91.0,
            temperature=98.6,
            mode_of_arrival="AMBULANCE_ALS",
            triage_nurse_name="Sister Sunita Rao, RN"
        )
        case = self.emergency.triage_patient(triage_in)
        bay_id = case.allocated_bay_id

        # ER Bay should be occupied
        self.assertEqual(self.emergency.get_bay(bay_id).status, ERBayStatus.OCCUPIED)

        # Finalize ER disposition: Transfer to ICU
        disposition_in = ERDispositionInput(
            case_id=case.case_id,
            disposition_type=ERDispositionType.ADMIT_TO_ICU,
            final_er_diagnosis="Acute STEMI, post-thrombolysis, cardiogenic shock monitored",
            discharge_or_transfer_notes="Transferred to Intensive Care Unit (ICU) under Cardiology team.",
            attending_er_physician="Dr. Vikram Seth",
            physician_reg_no="MCI-ER-77821"
        )
        disposed_case = self.emergency.finalize_er_disposition(disposition_in)
        self.assertEqual(disposed_case.status, ERCaseStatus.DISPOSED)
        self.assertEqual(disposed_case.disposition, ERDispositionType.ADMIT_TO_ICU)
        self.assertIsNotNone(disposed_case.target_ipd_admission_id)

        # ER Bay should now be released to AVAILABLE
        bay = self.emergency.get_bay(bay_id)
        self.assertEqual(bay.status, ERBayStatus.AVAILABLE)
        self.assertIsNone(bay.current_case_id)

        # Patient should now have an active IPD admission in an ICU bed
        ipd_adm = self.ipd.get_admission(disposed_case.target_ipd_admission_id)
        self.assertIsNotNone(ipd_adm)
        self.assertIn("ICU", ipd_adm.ward_name)

    def test_05_api_emergency_endpoints(self):
        """Verifies REST endpoints for ER bays, triage, resuscitation, and disposition."""
        # Register patient in the global app_identity_service so FastAPI can find it
        app_pt_res = app_identity_service.resolve_or_create_patient(
            PatientRegistrationRequest(
                first_name="Deepak",
                last_name="Malhotra",
                dob="1988-11-20",
                gender="MALE",
                primary_phone="+919988776655",
                postal_code="110025",
                identifiers=[]
            )
        )
        mpi_id = app_pt_res.mpi_id

        # 1. GET bays
        resp = self.client.get("/api/v1/emergency/bays")
        self.assertEqual(resp.status_code, 200)
        bays_data = resp.json()
        self.assertIsInstance(bays_data, list)
        self.assertGreaterEqual(len(bays_data), 6)

        # 2. POST triage
        triage_payload = {
            "mpi_id": str(mpi_id),
            "chief_complaint": "Acute shortness of breath, bilateral wheeze",
            "triage_level": "LEVEL_2_ORANGE",
            "gcs_score": 15,
            "systolic_bp": 130.0,
            "diastolic_bp": 85.0,
            "heart_rate": 105.0,
            "respiratory_rate": 26.0,
            "spo2": 92.0,
            "temperature": 99.1,
            "pain_score": 4,
            "mode_of_arrival": "WALK_IN",
            "triage_nurse_name": "Nurse Rohit Sharma"
        }
        resp = self.client.post("/api/v1/emergency/triage", json=triage_payload)
        self.assertEqual(resp.status_code, 200)
        case_data = resp.json()
        case_id = case_data["case_id"]
        self.assertEqual(case_data["triage_level"], "LEVEL_2_ORANGE")

        # 3. POST resuscitation intervention
        interv_payload = {
            "case_id": case_id,
            "intervention_type": "NEBULIZATION_BRONCHODILATOR",
            "details": "Salbutamol 5mg + Ipratropium 0.5mg nebulization stat given",
            "medications_given": "Inj Hydrocortisone 100mg IV",
            "clinician_name": "Dr. Sneha Roy",
            "gcs_post": 15,
            "vitals_post": "RR 20, SpO2 97% on room air"
        }
        resp = self.client.post("/api/v1/emergency/resuscitation/interventions", json=interv_payload)
        self.assertEqual(resp.status_code, 200)
        interv_data = resp.json()
        self.assertEqual(interv_data["intervention_type"], "NEBULIZATION_BRONCHODILATOR")

        # 4. GET active cases
        resp = self.client.get("/api/v1/emergency/cases/active")
        self.assertEqual(resp.status_code, 200)
        active_cases = resp.json()
        self.assertTrue(any(c["case_id"] == case_id for c in active_cases))

        # 5. POST disposition (Discharge Home)
        disp_payload = {
            "case_id": case_id,
            "disposition_type": "DISCHARGE_HOME",
            "final_er_diagnosis": "Acute exacerbation of bronchial asthma (Resolved)",
            "discharge_or_transfer_notes": "Patient stabilized. Prescribed oral bronchodilators. Follow up in Pulmonology OPD.",
            "attending_er_physician": "Dr. Sneha Roy",
            "physician_reg_no": "MCI-PULM-4412"
        }
        resp = self.client.post("/api/v1/emergency/disposition", json=disp_payload)
        self.assertEqual(resp.status_code, 200)
        disp_data = resp.json()
        self.assertEqual(disp_data["status"], "DISPOSED")
        self.assertEqual(disp_data["disposition"], "DISCHARGE_HOME")

if __name__ == "__main__":
    unittest.main()
