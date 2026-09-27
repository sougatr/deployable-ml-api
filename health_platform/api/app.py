from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
import uuid
from typing import Dict, Any, Optional, List

from health_platform.core.identity.models import (
    PatientRegistrationRequest,
    PatientResolutionResponse,
    FamilyLinkRequest,
    MergeRequest
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.interop.abdm_m1_m2 import ABDMGatewayBridge, AbhaProfile
from health_platform.core.clinical.models import (
    ConsultationInput,
    ConsultationResult
)
from health_platform.core.clinical.service import ClinicalEncounterService
from health_platform.core.clinical.document_parser import ClinicalDocumentParser
from health_platform.core.events.envelope import TransactionalOutboxPublisher
from health_platform.core.common.exceptions import (
    DuplicateIdentityCandidateException,
    UnanchoredChargeError,
    ImbalancedLedgerError
)

app = FastAPI(
    title="Digital Health & Hospital Operating Platform (Sprint 1 MVP Core)",
    version="1.0.0",
    description="Implements the frozen architectural foundation: 'One Patient. One Identity. One Longitudinal Health Record. One Clinical-Financial Journey. Open to Every Healthcare Network.'"
)

# Core Domain Service Singletons
identity_service = PatientIdentityService()
financial_ledger_service = FinancialLedgerService()
outbox_publisher = TransactionalOutboxPublisher()
abdm_gateway = ABDMGatewayBridge(identity_service=identity_service)
clinical_service = ClinicalEncounterService(
    identity_service=identity_service,
    financial_service=financial_ledger_service,
    abdm_bridge=abdm_gateway,
    outbox=outbox_publisher
)

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_web_app():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Digital Health Operating Platform API Active"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "digital-health-operating-platform-core",
        "trial_balance_discrepancy": financial_ledger_service.get_trial_balance_discrepancy(),
        "pending_outbox_events": len(outbox_publisher.get_pending_events())
    }

# =============================================================================
# 1. IDENTITY & MPI ENDPOINTS (Pod 1)
# =============================================================================
@app.post("/api/v1/identity/resolve", response_model=PatientResolutionResponse)
def resolve_or_register_patient(payload: PatientRegistrationRequest, allow_duplicate_override: bool = False):
    try:
        return identity_service.resolve_or_create_patient(payload, allow_duplicate_override=allow_duplicate_override)
    except DuplicateIdentityCandidateException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "candidate_matches": e.candidate_matches
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/identity/family-link")
def create_family_link(payload: FamilyLinkRequest):
    success = identity_service.manage_family_link(payload)
    return {"status": "success", "linked": success}

@app.post("/api/v1/identity/merge")
def execute_patient_merge(payload: MergeRequest):
    try:
        return identity_service.execute_merge(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# 2. ABDM MILESTONE 1 & 2 INTEROPERABILITY (Pod 4)
# Optional First-Class: Supports BOTH Aadhaar OTP and ABHA Address/Mobile OTP
# =============================================================================
class AadhaarOtpRequest(BaseModel):
    aadhaar_number: str = Field(..., example="987654321012")

class AadhaarVerifyOtpRequest(BaseModel):
    txn_id: str
    otp: str
    preferred_abha_address: Optional[str] = None

class AbhaAddressOtpRequest(BaseModel):
    abha_identifier: str = Field(..., example="ramesh.sharma@abdm")

class AbhaAddressVerifyOtpRequest(BaseModel):
    txn_id: str
    otp: str

class AbhaLinkRequest(BaseModel):
    mpi_id: uuid.UUID
    profile: AbhaProfile

@app.post("/api/v1/interop/abdm/aadhaar/generate-otp")
def generate_aadhaar_otp(payload: AadhaarOtpRequest):
    try:
        return abdm_gateway.generate_aadhaar_otp(payload.aadhaar_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/interop/abdm/aadhaar/verify-otp", response_model=AbhaProfile)
def verify_aadhaar_otp(payload: AadhaarVerifyOtpRequest):
    try:
        return abdm_gateway.verify_aadhaar_otp(payload.txn_id, payload.otp, payload.preferred_abha_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/interop/abdm/address/search-and-otp")
def search_and_send_abha_otp(payload: AbhaAddressOtpRequest):
    try:
        return abdm_gateway.search_and_send_abha_otp(payload.abha_identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/interop/abdm/address/verify-otp", response_model=AbhaProfile)
def verify_abha_mobile_otp(payload: AbhaAddressVerifyOtpRequest):
    try:
        return abdm_gateway.verify_abha_mobile_otp(payload.txn_id, payload.otp)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/interop/abdm/link")
def link_abha_to_patient(payload: AbhaLinkRequest):
    success = abdm_gateway.link_abha_profile_to_mpi(payload.mpi_id, payload.profile)
    return {"status": "success", "linked": success, "mpi_id": payload.mpi_id, "abha_number": payload.profile.abha_number}

@app.get("/api/v1/interop/abdm/care-contexts/{mpi_id}")
def get_abdm_care_contexts(mpi_id: uuid.UUID):
    return {"mpi_id": mpi_id, "care_contexts": abdm_gateway.get_patient_care_contexts(mpi_id)}

# =============================================================================
# 3. CLINICIAN OPD CONSULTATION WORKFLOW (Pod 2)
# =============================================================================
class StartEncounterRequest(BaseModel):
    mpi_id: uuid.UUID
    practitioner_id: uuid.UUID
    facility_id: uuid.UUID
    tenant_id: uuid.UUID

@app.post("/api/v1/clinical/encounters/start-opd")
def start_opd_encounter(payload: StartEncounterRequest):
    try:
        enc_id = clinical_service.start_opd_encounter(
            mpi_id=payload.mpi_id,
            practitioner_id=payload.practitioner_id,
            facility_id=payload.facility_id,
            tenant_id=payload.tenant_id
        )
        return {"status": "success", "encounter_id": enc_id, "mpi_id": payload.mpi_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/v1/clinical/consultations/complete", response_model=ConsultationResult)
def complete_consultation(payload: ConsultationInput):
    try:
        return clinical_service.complete_consultation(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clinical Workflow Failure: {str(e)}")

@app.post("/api/v1/clinical/consultations/parse-document")
async def parse_handwritten_document(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    try:
        extracted_text = ""
        if file and file.filename:
            content = await file.read()
            extracted_text = ClinicalDocumentParser.extract_text_from_file(content, file.filename)
        elif raw_text:
            extracted_text = raw_text
        else:
            # Fallback to sample handwritten clinical case sheet
            extracted_text = ClinicalDocumentParser.extract_text_from_file(b"", "sample_prescription.jpg")

        parsed_columns = ClinicalDocumentParser.parse_clinical_text_to_columns(extracted_text)
        return {
            "status": "success",
            "raw_extracted_text": extracted_text,
            "parsed_columns": parsed_columns,
            "patient_info": parsed_columns.get("patient_info")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document Parsing Failure: {str(e)}")

# =============================================================================
# 4. FINANCIAL LEDGER & RCM (Pod 3)
# =============================================================================
class OrderChargeCaptureRequest(BaseModel):
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    originating_resource_type: str = Field(..., description="Must be ServiceRequest, MedicationDispense, Procedure, or BedStay")
    originating_resource_id: uuid.UUID = Field(..., description="Immutable foreign key linking to clinical origin")
    tariff_code: str
    department_code: str
    unit_price: float
    quantity: float = 1.0
    patient_co_pay_ratio: float = 1.0
    coverage_id: uuid.UUID = None

@app.post("/api/v1/billing/charges/capture")
def capture_clinical_order_charge(payload: OrderChargeCaptureRequest):
    try:
        charge = financial_ledger_service.capture_charge_from_clinical_order(
            encounter_id=payload.encounter_id,
            mpi_id=payload.mpi_id,
            originating_resource_type=payload.originating_resource_type,
            originating_resource_id=payload.originating_resource_id,
            tariff_code=payload.tariff_code,
            department_code=payload.department_code,
            unit_price=payload.unit_price,
            quantity=payload.quantity,
            patient_co_pay_ratio=payload.patient_co_pay_ratio,
            coverage_id=payload.coverage_id
        )
        return {
            "status": "success",
            "charge_item_id": charge.charge_item_id,
            "gross_amount": charge.gross_amount,
            "patient_share": charge.patient_share,
            "insurer_share": charge.insurer_share,
            "trial_balance_status": "BALANCED" if financial_ledger_service.get_trial_balance_discrepancy() == 0.0 else "IMBALANCED"
        }
    except UnanchoredChargeError as e:
        raise HTTPException(status_code=422, detail=f"Clinical Safety Invariant Violation: {str(e)}")
    except ImbalancedLedgerError as e:
        raise HTTPException(status_code=500, detail=f"Financial Ledger Invariant Failure: {str(e)}")

class PaymentRecordRequest(BaseModel):
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    amount: float
    payment_method: str = "UPI"

@app.post("/api/v1/billing/payments")
def record_payment(payload: PaymentRecordRequest):
    journal = financial_ledger_service.record_patient_payment(
        encounter_id=payload.encounter_id,
        mpi_id=payload.mpi_id,
        amount=payload.amount,
        payment_method=payload.payment_method
    )
    return {
        "status": "success",
        "journal_id": journal.journal_id,
        "entry_type": journal.entry_type,
        "trial_balance_discrepancy": financial_ledger_service.get_trial_balance_discrepancy()
    }
