import uuid
from datetime import date
from health_platform.core.identity.models import (
    PatientRegistrationRequest,
    GenderEnum
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.interop.abdm_m1_m2 import ABDMGatewayBridge
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.clinical.service import ClinicalEncounterService
from health_platform.core.clinical.models import (
    ConsultationInput,
    ConditionInput,
    VitalSignInput,
    PrescriptionItemInput,
    DiagnosticOrderInput
)

def test_abdm_method_a_aadhaar_otp_linking():
    identity_svc = PatientIdentityService()
    abdm_bridge = ABDMGatewayBridge(identity_service=identity_svc)

    # 1. Register a patient without ABHA initially
    patient = identity_svc.resolve_or_create_patient(
        PatientRegistrationRequest(
            first_name="Ananya",
            last_name="Deshmukh",
            dob=date(1994, 7, 10),
            gender=GenderEnum.FEMALE,
            primary_phone="+919876543210"
        )
    )
    assert patient.patient_record.abha_number is None

    # 2. Method A: Generate Aadhaar OTP
    otp_res = abdm_bridge.generate_aadhaar_otp("9876 5432 1012")
    assert otp_res["status"] == "OTP_SENT"
    txn_id = otp_res["txn_id"]

    # 3. Verify Aadhaar OTP (Sandbox OTP: 123456)
    profile = abdm_bridge.verify_aadhaar_otp(
        txn_id=txn_id,
        otp="123456",
        preferred_abha_address="ananya.deshmukh@abdm"
    )
    assert profile.is_kyc_verified is True
    assert profile.abha_address == "ananya.deshmukh@abdm"
    assert profile.abha_number.startswith("14-")

    # 4. Link ABHA to Patient MPI
    linked = abdm_bridge.link_abha_profile_to_mpi(patient.mpi_id, profile)
    assert linked is True

    # 5. Confirm patient record now reflects the linked ABHA
    updated_rec = identity_svc._patients[patient.mpi_id]
    assert updated_rec.abha_number == profile.abha_number
    assert updated_rec.abha_address == "ananya.deshmukh@abdm"

def test_abdm_method_b_existing_abha_address_mobile_otp():
    identity_svc = PatientIdentityService()
    abdm_bridge = ABDMGatewayBridge(identity_service=identity_svc)

    # 1. Register a patient
    patient = identity_svc.resolve_or_create_patient(
        PatientRegistrationRequest(
            first_name="Vikram",
            last_name="Malhotra",
            dob=date(1986, 3, 25),
            gender=GenderEnum.MALE,
            primary_phone="+919123456789"
        )
    )

    # 2. Method B: Search existing ABHA Address and trigger Mobile OTP
    otp_res = abdm_bridge.search_and_send_abha_otp("vikram.malhotra@abdm")
    assert otp_res["status"] == "OTP_SENT"
    txn_id = otp_res["txn_id"]

    # 3. Verify Mobile OTP (Sandbox OTP: 654321)
    profile = abdm_bridge.verify_abha_mobile_otp(txn_id=txn_id, otp="654321")
    assert profile.abha_address == "vikram.malhotra@abdm"
    assert profile.abha_number.startswith("14-")

    # 4. Link to MPI
    abdm_bridge.link_abha_profile_to_mpi(patient.mpi_id, profile)
    updated_rec = identity_svc._patients[patient.mpi_id]
    assert updated_rec.abha_address == "vikram.malhotra@abdm"

def test_opd_consultation_flow_with_orders_billing_and_abdm_hip():
    identity_svc = PatientIdentityService()
    fin_svc = FinancialLedgerService()
    outbox = TransactionalOutboxPublisher()
    abdm_bridge = ABDMGatewayBridge(identity_service=identity_svc)
    clinical_svc = ClinicalEncounterService(
        identity_service=identity_svc,
        financial_service=fin_svc,
        abdm_bridge=abdm_bridge,
        outbox=outbox
    )

    # 1. Register Patient with ABHA Address
    patient = identity_svc.resolve_or_create_patient(
        PatientRegistrationRequest(
            first_name="Sunil",
            last_name="Gupte",
            dob=date(1978, 12, 5),
            gender=GenderEnum.MALE,
            primary_phone="+919822001122"
        )
    )
    # Link ABHA
    abdm_bridge.link_abha_profile_to_mpi(
        patient.mpi_id,
        abdm_bridge.verify_abha_mobile_otp(
            abdm_bridge.search_and_send_abha_otp("sunil.gupte@abdm")["txn_id"],
            "654321"
        )
    )

    practitioner_id = uuid.uuid4()
    facility_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # 2. Start OPD Encounter
    encounter_id = clinical_svc.start_opd_encounter(
        mpi_id=patient.mpi_id,
        practitioner_id=practitioner_id,
        facility_id=facility_id,
        tenant_id=tenant_id
    )
    assert encounter_id is not None

    # 3. Clinician Conducts Consultation
    consult_input = ConsultationInput(
        encounter_id=encounter_id,
        practitioner_id=practitioner_id,
        chief_complaint="Elevated blood sugar and morning headaches",
        clinical_narrative="Diagnosed with uncomplicated Type 2 Diabetes. Prescribed Metformin and ordered HbA1c.",
        vitals=[
            VitalSignInput(
                code_loinc="8480-6",
                display="Systolic Blood Pressure",
                value=134.0,
                unit="mm[Hg]",
                interpretation="HIGH"
            )
        ],
        diagnoses=[
            ConditionInput(
                code_icd10="E11.9",
                code_snomed="73211009",
                display="Type 2 Diabetes Mellitus without complications"
            )
        ],
        orders=[
            DiagnosticOrderInput(
                category="LABORATORY",
                code_loinc_or_snomed="4548-4",
                display="Hemoglobin A1c (HbA1c) Panel",
                tariff_code="LAB-BIO-042",
                department_code="BIOCHEMISTRY",
                unit_price=650.00,
                priority="ROUTINE"
            )
        ],
        prescriptions=[
            PrescriptionItemInput(
                brand_name="Glycomet 500",
                generic_name="Metformin Hydrochloride 500mg",
                dosage_form="TABLET",
                timing="1-0-1",
                duration_days=60,
                instructions="Take with or immediately after meals"
            )
        ],
        consultation_fee=500.00,
        patient_co_pay_ratio=0.20, # 20% patient co-pay, 80% insurer
        doctor_digital_signature="SIG-RSA-DR-RAO-9021"
    )

    result = clinical_svc.complete_consultation(consult_input)

    # 4. Verify Clinical Outcome
    assert result.status == "COMPLETED"
    assert result.diagnoses_recorded == 1
    assert result.orders_placed == 1
    assert result.prescriptions_issued == 1

    # 5. Verify Financial Ledger & Invariant
    # Total = ₹500 (consult) + ₹650 (lab order) = ₹1150.00
    assert result.total_charges_posted == 1150.00
    assert result.patient_share_payable == 230.00 # 20% of 1150
    assert result.insurer_share_payable == 920.00 # 80% of 1150
    assert result.trial_balance_status == "BALANCED"
    assert fin_svc.get_trial_balance_discrepancy() == 0.00

    # 6. Verify ABDM Milestone 2 HIP Care Context Auto-Linking
    assert result.abdm_care_context_linked is True
    assert result.care_context_id.startswith("CARE-CTX-")
    care_contexts = abdm_bridge.get_patient_care_contexts(patient.mpi_id)
    assert len(care_contexts) == 1
    assert "Type 2 Diabetes" in care_contexts[0]["display"]

    # 7. Verify Transactional Outbox Partitioning on mpi_id
    pending_events = outbox.get_pending_events()
    assert len(pending_events) >= 4 # EncounterStarted, NoteSigned, OrderPlaced, PrescriptionIssued
    for ev in pending_events:
        assert ev["partition_key"] == str(patient.mpi_id)

def test_opd_consultation_optionality_without_abha():
    """Confirms patient care executes with 100% success even if patient opts out of ABHA."""
    identity_svc = PatientIdentityService()
    fin_svc = FinancialLedgerService()
    outbox = TransactionalOutboxPublisher()
    abdm_bridge = ABDMGatewayBridge(identity_service=identity_svc)
    clinical_svc = ClinicalEncounterService(
        identity_service=identity_svc,
        financial_service=fin_svc,
        abdm_bridge=abdm_bridge,
        outbox=outbox
    )

    # Register pure self-pay patient without ABHA
    patient = identity_svc.resolve_or_create_patient(
        PatientRegistrationRequest(
            first_name="Deepak",
            last_name="Joshi",
            dob=date(1991, 4, 18),
            gender=GenderEnum.MALE,
            primary_phone="+919777888999"
        )
    )

    enc_id = clinical_svc.start_opd_encounter(
        mpi_id=patient.mpi_id,
        practitioner_id=uuid.uuid4(),
        facility_id=uuid.uuid4(),
        tenant_id=uuid.uuid4()
    )

    res = clinical_svc.complete_consultation(
        ConsultationInput(
            encounter_id=enc_id,
            practitioner_id=uuid.uuid4(),
            chief_complaint="Seasonal allergic rhinitis",
            clinical_narrative="Prescribed antihistamines. No diagnostic tests needed.",
            diagnoses=[
                ConditionInput(
                    code_icd10="J30.2",
                    display="Other seasonal allergic rhinitis"
                )
            ],
            orders=[],
            prescriptions=[
                PrescriptionItemInput(
                    brand_name="Allegra 120",
                    generic_name="Fexofenadine 120mg",
                    timing="0-0-1",
                    duration_days=10
                )
            ],
            consultation_fee=400.00,
            patient_co_pay_ratio=1.0,
            doctor_digital_signature="SIG-RSA-DR-SMITH-11"
        )
    )

    assert res.status == "COMPLETED"
    assert res.total_charges_posted == 400.00
    assert res.abdm_care_context_linked is False # Gracefully skipped because patient has no ABHA
    assert fin_svc.get_trial_balance_discrepancy() == 0.00
