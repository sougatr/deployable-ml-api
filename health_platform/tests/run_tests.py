import sys
import unittest
from health_platform.tests.test_mpi_engine import (
    test_patient_registration_and_uhid_generation,
    test_deterministic_match_via_abha,
    test_probabilistic_duplicate_detection_and_transposition,
    test_family_graph_multiple_profiles_one_phone,
    test_merge_governance
)
from health_platform.tests.test_clinical_financial_invariant import (
    test_unanchored_charge_rejection,
    test_imbalanced_ledger_rejection,
    test_end_to_end_charge_capture_and_trial_balance,
    test_transactional_outbox_partitioning
)
from health_platform.tests.test_api_endpoints import (
    test_api_root_serves_web_app,
    test_api_health_check,
    test_api_patient_registration_and_duplicate_handling,
    test_api_charge_capture_and_payment
)
from health_platform.tests.test_abdm_and_clinical_consultation import (
    test_abdm_method_a_aadhaar_otp_linking,
    test_abdm_method_b_existing_abha_address_mobile_otp,
    test_opd_consultation_flow_with_orders_billing_and_abdm_hip,
    test_opd_consultation_optionality_without_abha
)
from health_platform.tests.test_document_parser import TestClinicalDocumentParser
from health_platform.tests.test_ipd_workflows import TestIPDWorkflows
from health_platform.tests.test_diagnostics_workflows import TestDiagnosticsWorkflows
from health_platform.tests.test_pharmacy_workflows import TestPharmacyWorkflows
from health_platform.tests.test_emergency_workflows import TestEmergencyWorkflows
from health_platform.tests.test_patient_portal import TestPatientPortal
from health_platform.tests.test_wearables import TestWearablesAndRecoveryIoT

class PlatformCoreTestSuite(unittest.TestCase):
    # Identity & MPI Tests
    def test_01_patient_registration_and_uhid(self):
        test_patient_registration_and_uhid_generation()

    def test_02_deterministic_match_via_abha(self):
        test_deterministic_match_via_abha()

    def test_03_probabilistic_duplicate_transposition(self):
        test_probabilistic_duplicate_detection_and_transposition()

    def test_04_family_graph_multiple_profiles(self):
        test_family_graph_multiple_profiles_one_phone()

    def test_05_merge_governance(self):
        test_merge_governance()

    # Financial & Clinical Invariant Tests
    def test_06_unanchored_charge_rejection(self):
        test_unanchored_charge_rejection()

    def test_07_imbalanced_ledger_rejection(self):
        test_imbalanced_ledger_rejection()

    def test_08_end_to_end_charge_and_ledger(self):
        test_end_to_end_charge_capture_and_trial_balance()

    def test_09_transactional_outbox_partitioning(self):
        test_transactional_outbox_partitioning()

    # ABDM Milestone 1 & 2 Interoperability Tests
    def test_10_abdm_method_a_aadhaar_otp(self):
        test_abdm_method_a_aadhaar_otp_linking()

    def test_11_abdm_method_b_abha_address_mobile_otp(self):
        test_abdm_method_b_existing_abha_address_mobile_otp()

    # Clinician OPD Consultation Flow Tests (Pod 2)
    def test_12_opd_consultation_with_orders_billing_abdm(self):
        test_opd_consultation_flow_with_orders_billing_and_abdm_hip()

    def test_13_opd_consultation_optionality_without_abha(self):
        test_opd_consultation_optionality_without_abha()

    # API Integration Tests
    def test_14_api_root_serves_web_app(self):
        test_api_root_serves_web_app()

    def test_15_api_health_check(self):
        test_api_health_check()

    def test_16_api_patient_registration_and_duplicates(self):
        test_api_patient_registration_and_duplicate_handling()

    def test_17_api_charge_capture_and_payment(self):
        test_api_charge_capture_and_payment()

    # Document & Prescription Parsing Tests
    def test_18_document_parser_clinical_extraction(self):
        t = TestClinicalDocumentParser()
        t.test_parse_handwritten_clinical_text()

    def test_19_api_document_parse_endpoint(self):
        t = TestClinicalDocumentParser()
        t.test_api_parse_document_endpoint()

    def test_20_document_parser_fever_and_antibiotics(self):
        t = TestClinicalDocumentParser()
        t.test_parse_fever_and_antibiotic_prescription()

    def test_21_document_parser_image_simulation(self):
        t = TestClinicalDocumentParser()
        t.test_vision_ocr_simulation_for_scanned_image()

    def test_22_document_parser_orthopaedic_prescription(self):
        t = TestClinicalDocumentParser()
        t.test_parse_orthopaedic_prescription()

    # Inpatient (IPD) & Bed Management Workflow Tests
    def test_23_ipd_bed_matrix_and_admissions(self):
        t = TestIPDWorkflows()
        t.setUp()
        t.test_01_bed_matrix_initialization()
        t.test_02_patient_admission_and_bed_occupancy()

    def test_24_ipd_nursing_and_doctor_rounds(self):
        t = TestIPDWorkflows()
        t.setUp()
        t.test_03_nurse_charting_and_doctor_rounds()

    def test_25_ipd_discharge_and_room_charge_accrual(self):
        t = TestIPDWorkflows()
        t.setUp()
        t.test_04_patient_discharge_and_room_charge_accrual()
    def test_26_ipd_api_endpoints(self):
        t = TestIPDWorkflows()
        t.setUp()
        t.test_05_api_ipd_endpoints()

    # Diagnostic Laboratory & Radiology (LIS/RIS) Tests
    def test_27_diagnostics_catalog_and_coding(self):
        t = TestDiagnosticsWorkflows()
        t.setUp()
        t.test_01_catalog_standard_coding()

    def test_28_diagnostics_lab_workflow_and_flags(self):
        t = TestDiagnosticsWorkflows()
        t.setUp()
        t.test_02_lab_order_specimen_collection_and_flags()
        t.test_03_critical_value_alert_flagging()

    def test_29_diagnostics_radiology_workflow(self):
        t = TestDiagnosticsWorkflows()
        t.setUp()
        t.test_04_radiology_mri_reporting_workflow()

    def test_30_diagnostics_api_endpoints(self):
        t = TestDiagnosticsWorkflows()
        t.setUp()
        t.test_05_api_diagnostics_endpoints()

    # Pharmacy & e-Prescription Dispensing (Closed-Loop Inventory) Tests
    def test_31_pharmacy_inventory_and_alerts(self):
        t = TestPharmacyWorkflows()
        t.setUp()
        t.test_01_inventory_initialization_and_alerts()

    def test_32_pharmacy_closed_loop_dispensing(self):
        t = TestPharmacyWorkflows()
        t.setUp()
        t.test_02_successful_dispense_and_stock_decrement()

    def test_33_pharmacy_expired_and_stock_safety(self):
        t = TestPharmacyWorkflows()
        t.setUp()
        t.test_03_rejection_of_expired_medication_batch()
        t.test_04_rejection_of_insufficient_stock()
        t.test_05_restock_batch()

    def test_34_pharmacy_api_endpoints(self):
        t = TestPharmacyWorkflows()
        t.setUp()
        t.test_06_api_pharmacy_endpoints()

    # Emergency Department & Triage (Manchester / ESI Protocol) Tests
    def test_35_emergency_bay_and_triage(self):
        t = TestEmergencyWorkflows()
        t.setUp()
        t.test_01_er_bay_seeding()
        t.test_02_triage_level_1_code_red()

    def test_36_emergency_resuscitation_interventions(self):
        t = TestEmergencyWorkflows()
        t.setUp()
        t.test_03_resuscitation_interventions_and_procedural_charges()

    def test_37_emergency_to_ipd_admission_pipeline(self):
        t = TestEmergencyWorkflows()
        t.setUp()
        t.test_04_er_to_ipd_admission_pipeline()

    def test_38_emergency_api_endpoints(self):
        t = TestEmergencyWorkflows()
        t.setUp()
        t.test_05_api_emergency_endpoints()

    # Patient / Client Portal & AI Health Companion Tests (Pod 9)
    def test_39_patient_portal_ehr_synthesis_and_ai_translations(self):
        t = TestPatientPortal()
        t.setUp()
        t.test_01_patient_portal_summary_orthopedic()

    def test_40_patient_portal_ai_query_assistant(self):
        t = TestPatientPortal()
        t.setUp()
        t.test_02_patient_ai_query_assistant()

    def test_41_patient_portal_api_endpoints(self):
        t = TestPatientPortal()
        t.setUp()
        t.test_03_portal_api_endpoints()

    # Wearables, WHOOP, 40Hz Gamma Cap, Sleep & Gym Strength Tests (Pod 10)
    def test_42_wearable_devices_and_discovery(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_01_device_connection_and_discovery()

    def test_43_whoop_recovery_and_sleep_architecture(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_02_whoop_telemetry_and_sleep_architecture()

    def test_44_gamma_40hz_neuromodulation_cap(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_03_gamma_40hz_neuromodulation_cap()

    def test_45_step_pacing_and_surgical_ceiling_alert(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_04_step_pacing_and_surgical_ceiling_alert()

    def test_46_adaptive_gym_strength_and_workout_logging(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_05_adaptive_gym_strength_training_recommendations()
        t.test_06_gym_workout_logging()

    def test_47_ai_companion_wearables_and_api(self):
        t = TestWearablesAndRecoveryIoT()
        t.setUpClass()
        t.test_07_ai_companion_wearable_queries()
        t.test_08_api_wearables_endpoints()

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(PlatformCoreTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

