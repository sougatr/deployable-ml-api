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

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(PlatformCoreTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
