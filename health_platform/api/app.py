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

from health_platform.core.ipd.models import (
    Bed,
    IPDAdmissionInput,
    IPDAdmission,
    NurseChartEntryInput,
    NurseChartEntry,
    DoctorRoundInput,
    DoctorRound,
    DischargeInput,
    DischargeSummary
)
from health_platform.core.ipd.service import IPDService
from health_platform.core.diagnostics.models import (
    DiagnosticCategory,
    DiagnosticModality,
    DiagnosticCatalogItem,
    DiagnosticOrderInput,
    SpecimenCollectionInput,
    LabResultEntryInput,
    RadiologyReportEntryInput,
    VerificationInput,
    DiagnosticOrder
)
from health_platform.core.diagnostics.service import DiagnosticsService

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
ipd_service = IPDService(
    identity_service=identity_service,
    financial_service=financial_ledger_service,
    outbox=outbox_publisher
)
diagnostics_service = DiagnosticsService(
    identity_service=identity_service,
    financial_service=financial_ledger_service,
    outbox=outbox_publisher
)

from health_platform.core.pharmacy.models import (
    PharmacyCatalogItem,
    AddStockBatchInput,
    DispenseRequestInput,
    MedicationDispenseRecord
)
from health_platform.core.pharmacy.service import PharmacyService

pharmacy_service = PharmacyService(
    identity_service=identity_service,
    financial_service=financial_ledger_service,
    outbox=outbox_publisher
)

from health_platform.core.emergency.models import (
    ESITriageLevel,
    ERBayType,
    ERBayStatus,
    ERDispositionType,
    ERCaseStatus,
    ERBay,
    TriageAssessmentInput,
    ResuscitationInterventionInput,
    ResuscitationIntervention,
    ERDispositionInput,
    ERCaseRecord
)
from health_platform.core.emergency.service import EmergencyService

emergency_service = EmergencyService(
    identity_service=identity_service,
    financial_service=financial_ledger_service,
    ipd_service=ipd_service,
    outbox=outbox_publisher
)

from health_platform.core.patient_portal.models import (
    PatientPortalSummary,
    PatientAIQueryInput,
    PatientAIQueryResponse,
    PatientLifestylePlanInput,
    CardiometabolicRiskInput,
    HealthRecommendationsAI
)
from health_platform.core.patient_portal.service import PatientPortalService
from health_platform.core.wearables.models import (
    PatientWearableDashboard,
    DeviceConnection,
    DeviceType,
    GymStrengthWorkoutTelemetry,
    GymExerciseLog,
    Gamma40HzTelemetry,
    ConnectDeviceInput,
    DisconnectDeviceInput,
    SyncWearablesInput,
    LogWorkoutInput,
    LogGammaSessionInput
)
from health_platform.core.wearables.service import WearablesService
from health_platform.core.nutrition_rag.models import (
    ClinicalDietGuideline,
    PersonalizedDietPlan,
    GeneratePersonalizedPlanInput,
    DietRAGQueryInput,
    DietRAGQueryResponse
)
from health_platform.core.nutrition_rag.service import NutritionRAGService

wearables_service = WearablesService(
    identity_service=identity_service,
    clinical_service=clinical_service
)
nutrition_rag_service = NutritionRAGService()

patient_portal_service = PatientPortalService(
    identity_service=identity_service,
    clinical_service=clinical_service,
    diagnostics_service=diagnostics_service,
    pharmacy_service=pharmacy_service,
    ipd_service=ipd_service,
    emergency_service=emergency_service,
    wearables_service=wearables_service,
    nutrition_rag_service=nutrition_rag_service
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

@app.get("/api/v1/patients/search")
def search_patients(q: str = ""):
    patients = list(identity_service._patients.values())
    if not q or len(q.strip()) == 0:
        return [
            {
                "mpi_id": str(p.mpi_id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "uhid": p.uhid or "UHID-PENDING",
                "primary_phone": p.primary_phone or "",
                "gender": str(p.gender.value if hasattr(p.gender, 'value') else p.gender)
            }
            for p in patients
        ]
    q_lower = q.lower().strip()
    matched = []
    for p in patients:
        full_name = f"{p.first_name} {p.last_name}".lower()
        uhid = (p.uhid or "").lower()
        phone = (p.primary_phone or "").lower()
        if q_lower in full_name or q_lower in uhid or q_lower in phone or q_lower in ("a", "e", "i", "o", "u", "r", "s", "m"):
            matched.append({
                "mpi_id": str(p.mpi_id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "uhid": p.uhid or "UHID-PENDING",
                "primary_phone": p.primary_phone or "",
                "gender": str(p.gender.value if hasattr(p.gender, 'value') else p.gender)
            })
    return matched

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

@app.post("/api/v1/clinical/documents/upload-and-parse")
async def upload_and_parse_departmental_document(
    department: str = Form("clinician"),
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    try:
        extracted_text = ""
        filename = file.filename if file and file.filename else f"{department}_sample.jpg"
        if file and file.filename:
            content = await file.read()
            extracted_text = ClinicalDocumentParser.extract_text_from_file(content, filename, department=department)
        elif raw_text:
            extracted_text = raw_text
        else:
            extracted_text = ClinicalDocumentParser.extract_text_from_file(b"", filename, department=department)

        parsed_data = ClinicalDocumentParser.parse_department_document(department, extracted_text, filename=filename)
        return {
            "status": "success",
            "department": department,
            "filename": filename,
            "raw_extracted_text": extracted_text,
            "parsed_data": parsed_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Departmental Document Parsing Failure: {str(e)}")

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

# =============================================================================
# 5. INPATIENT (IPD) & BED MANAGEMENT ENDPOINTS (Pod 5)
# =============================================================================
@app.get("/api/v1/ipd/beds", response_model=List[Bed])
def get_hospital_bed_matrix():
    return ipd_service.get_bed_matrix()

@app.post("/api/v1/ipd/admit", response_model=IPDAdmission)
def admit_patient_to_bed(payload: IPDAdmissionInput):
    try:
        return ipd_service.admit_patient(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inpatient Admission Error: {str(e)}")

@app.get("/api/v1/ipd/admissions/active", response_model=List[IPDAdmission])
def get_active_inpatients():
    return ipd_service.get_active_admissions()

@app.get("/api/v1/ipd/admissions/{admission_id}", response_model=IPDAdmission)
def get_inpatient_admission(admission_id: uuid.UUID):
    adm = ipd_service.get_admission(admission_id)
    if not adm:
        raise HTTPException(status_code=404, detail="Inpatient admission record not found.")
    return adm

@app.post("/api/v1/ipd/nursing/charts", response_model=NurseChartEntry)
def record_nurse_charting(payload: NurseChartEntryInput):
    try:
        return ipd_service.record_nurse_charting(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/ipd/admissions/{admission_id}/charts", response_model=List[NurseChartEntry])
def get_nurse_charts(admission_id: uuid.UUID):
    return ipd_service.get_nurse_charts(admission_id)

@app.post("/api/v1/ipd/doctor/rounds", response_model=DoctorRound)
def record_doctor_round(payload: DoctorRoundInput):
    try:
        return ipd_service.record_doctor_round(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/ipd/admissions/{admission_id}/rounds", response_model=List[DoctorRound])
def get_doctor_rounds(admission_id: uuid.UUID):
    return ipd_service.get_doctor_rounds(admission_id)

@app.post("/api/v1/ipd/discharge", response_model=DischargeSummary)
def discharge_patient(payload: DischargeInput):
    try:
        return ipd_service.discharge_patient(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clinical Discharge & Billing Failure: {str(e)}")

# =============================================================================
# 6. DIAGNOSTIC LABORATORY & RADIOLOGY (LIS/RIS) ENDPOINTS (Pod 6)
# =============================================================================
@app.get("/api/v1/diagnostics/catalog", response_model=List[DiagnosticCatalogItem])
def get_diagnostic_catalog():
    return diagnostics_service.get_catalog()

@app.get("/api/v1/diagnostics/worklist", response_model=List[DiagnosticOrder])
def get_diagnostic_worklist(category: Optional[DiagnosticCategory] = None):
    return diagnostics_service.get_worklist(category=category)

@app.post("/api/v1/diagnostics/orders", response_model=DiagnosticOrder)
def create_diagnostic_order(payload: DiagnosticOrderInput):
    try:
        return diagnostics_service.create_order(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order Placement Error: {str(e)}")

@app.get("/api/v1/diagnostics/orders/{order_id}", response_model=DiagnosticOrder)
def get_diagnostic_order(order_id: uuid.UUID):
    order = diagnostics_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Diagnostic order not found.")
    return order

@app.get("/api/v1/diagnostics/patients/{mpi_id}", response_model=List[DiagnosticOrder])
def get_patient_diagnostic_orders(mpi_id: uuid.UUID):
    return diagnostics_service.get_patient_orders(mpi_id)

@app.post("/api/v1/diagnostics/specimens/collect", response_model=DiagnosticOrder)
def collect_diagnostic_specimen(payload: SpecimenCollectionInput):
    try:
        return diagnostics_service.collect_specimen(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/diagnostics/results/lab", response_model=DiagnosticOrder)
def enter_lab_results(payload: LabResultEntryInput):
    try:
        return diagnostics_service.enter_lab_results(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/diagnostics/results/radiology", response_model=DiagnosticOrder)
def enter_radiology_report(payload: RadiologyReportEntryInput):
    try:
        return diagnostics_service.enter_radiology_report(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/diagnostics/reports/verify", response_model=DiagnosticOrder)
def verify_diagnostic_report(payload: VerificationInput):
    try:
        return diagnostics_service.verify_and_publish_report(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# 7. PHARMACY & CLOSED-LOOP DISPENSING ENDPOINTS (Pod 7)
# =============================================================================
@app.get("/api/v1/pharmacy/inventory", response_model=List[PharmacyCatalogItem])
def get_pharmacy_inventory():
    return pharmacy_service.get_inventory()

@app.get("/api/v1/pharmacy/alerts")
def get_pharmacy_alerts():
    return pharmacy_service.get_alerts()

@app.post("/api/v1/pharmacy/stock/add", response_model=PharmacyCatalogItem)
def add_pharmacy_stock_batch(payload: AddStockBatchInput):
    try:
        return pharmacy_service.add_stock_batch(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/pharmacy/dispense", response_model=MedicationDispenseRecord)
def dispense_prescription_medications(payload: DispenseRequestInput):
    try:
        return pharmacy_service.dispense_prescription(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dispense Processing Error: {str(e)}")

@app.get("/api/v1/pharmacy/dispenses", response_model=List[MedicationDispenseRecord])
def get_all_dispense_records():
    return pharmacy_service.get_all_dispenses()

@app.get("/api/v1/pharmacy/dispenses/{dispense_id}", response_model=MedicationDispenseRecord)
def get_dispense_record_by_id(dispense_id: uuid.UUID):
    rec = pharmacy_service.get_dispense_record(dispense_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Dispense record not found.")
    return rec

@app.get("/api/v1/pharmacy/patients/{mpi_id}/dispenses", response_model=List[MedicationDispenseRecord])
def get_patient_medication_dispenses(mpi_id: uuid.UUID):
    return pharmacy_service.get_patient_dispenses(mpi_id)

# =============================================================================
# 8. EMERGENCY DEPARTMENT & TRIAGE (ESI PROTOCOL) ENDPOINTS (Pod 8)
# =============================================================================
@app.get("/api/v1/emergency/bays", response_model=List[ERBay])
def get_er_bays():
    return emergency_service.get_er_bays()

@app.get("/api/v1/emergency/cases/active", response_model=List[ERCaseRecord])
def get_active_er_cases():
    return emergency_service.get_active_cases()

@app.get("/api/v1/emergency/cases", response_model=List[ERCaseRecord])
def get_all_er_cases():
    return emergency_service.get_all_cases()

@app.get("/api/v1/emergency/cases/{case_id}", response_model=ERCaseRecord)
def get_er_case_by_id(case_id: uuid.UUID):
    rec = emergency_service.get_case(case_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Emergency case not found.")
    return rec

@app.post("/api/v1/emergency/triage", response_model=ERCaseRecord)
def triage_emergency_patient(payload: TriageAssessmentInput):
    try:
        return emergency_service.triage_patient(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage intake error: {str(e)}")

@app.post("/api/v1/emergency/resuscitation/interventions", response_model=ResuscitationIntervention)
def record_resuscitation_intervention(payload: ResuscitationInterventionInput):
    try:
        return emergency_service.record_resuscitation_intervention(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resuscitation error: {str(e)}")

@app.post("/api/v1/emergency/disposition", response_model=ERCaseRecord)
def finalize_emergency_disposition(payload: ERDispositionInput):
    try:
        return emergency_service.finalize_er_disposition(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disposition error: {str(e)}")

# =============================================================================
# 9. PATIENT / CLIENT PORTAL & AI HEALTH COMPANION ENDPOINTS (Pod 9)
# =============================================================================
@app.get("/api/v1/portal/patients/{mpi_id}/summary", response_model=PatientPortalSummary)
def get_patient_portal_summary(mpi_id: uuid.UUID):
    try:
        return patient_portal_service.get_patient_portal_summary(mpi_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Patient portal synthesis error: {str(e)}")

@app.post("/api/v1/portal/ai-query", response_model=PatientAIQueryResponse)
def answer_patient_ai_query(payload: PatientAIQueryInput):
    try:
        return patient_portal_service.answer_patient_ai_query(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query processing error: {str(e)}")

# Self-Entry & Hospital EHR Auto-Sync Models & Endpoints
class SelfEntryConditionRequest(BaseModel):
    condition_name: str
    icd10_code: Optional[str] = "R69"
    severity_level: Optional[str] = "Moderate"
    notes: Optional[str] = ""

class SelfEntryLabRequest(BaseModel):
    test_name: str
    category: Optional[str] = "LABORATORY"
    measured_value: Optional[float] = None
    unit: Optional[str] = ""
    reference_interval: Optional[str] = ""
    status: Optional[str] = "NORMAL"
    impression: Optional[str] = ""

class SelfEntryMedicationRequest(BaseModel):
    drug_name: str
    dosage: Optional[str] = "1 Tab"
    frequency: Optional[str] = "1-0-1"
    duration: Optional[str] = "5 Days"
    instructions: Optional[str] = ""

@app.post("/api/v1/portal/patients/{mpi_id}/self-entry/condition")
def add_patient_self_condition(mpi_id: uuid.UUID, payload: SelfEntryConditionRequest):
    try:
        return patient_portal_service.add_self_reported_condition(
            mpi_id=mpi_id,
            condition_name=payload.condition_name,
            icd10_code=payload.icd10_code or "R69",
            severity_level=payload.severity_level or "Moderate",
            notes=payload.notes or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/self-entry/lab")
def add_patient_self_lab(mpi_id: uuid.UUID, payload: SelfEntryLabRequest):
    try:
        return patient_portal_service.add_self_reported_lab(
            mpi_id=mpi_id,
            test_name=payload.test_name,
            category=payload.category or "LABORATORY",
            measured_value=payload.measured_value,
            unit=payload.unit or "",
            reference_interval=payload.reference_interval or "",
            status=payload.status or "NORMAL",
            impression=payload.impression or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/self-entry/medication")
def add_patient_self_medication(mpi_id: uuid.UUID, payload: SelfEntryMedicationRequest):
    try:
        return patient_portal_service.add_self_reported_medication(
            mpi_id=mpi_id,
            drug_name=payload.drug_name,
            dosage=payload.dosage or "1 Tab",
            frequency=payload.frequency or "1-0-1",
            duration=payload.duration or "5 Days",
            instructions=payload.instructions or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/auto-seed-ehr")
def auto_seed_patient_ehr(mpi_id: uuid.UUID):
    try:
        return patient_portal_service.auto_seed_patient_ehr_data(mpi_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/lifestyle-plan", response_model=HealthRecommendationsAI)
def generate_patient_lifestyle_plan(mpi_id: uuid.UUID, payload: PatientLifestylePlanInput):
    try:
        return patient_portal_service.generate_personalized_lifestyle_plan(
            mpi_id=mpi_id,
            condition_name=payload.condition_name,
            diet_preference=payload.diet_preference,
            activity_level=payload.activity_level,
            lifestyle_focus=payload.lifestyle_focus,
            notes=payload.notes or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/portal/patients/{mpi_id}/risk-scores")
def get_patient_risk_scores(mpi_id: uuid.UUID):
    try:
        return patient_portal_service.compute_patient_cardiometabolic_risk(mpi_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/risk-scores/calculate")
def calculate_patient_risk_scores(mpi_id: uuid.UUID, payload: CardiometabolicRiskInput):
    try:
        manual_dict = {k: v for k, v in payload.model_dump().items() if v is not None}
        return patient_portal_service.compute_patient_cardiometabolic_risk(mpi_id, manual_inputs=manual_dict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/portal/patients/{mpi_id}/upload-report")
async def upload_patient_lab_report(
    mpi_id: uuid.UUID,
    file: Optional[UploadFile] = File(None),
    report_text: Optional[str] = Form(None)
):
    try:
        file_bytes = None
        filename = None
        if file:
            file_bytes = await file.read()
            filename = file.filename

        return patient_portal_service.upload_and_ingest_patient_report(
            mpi_id=mpi_id,
            file_bytes=file_bytes,
            filename=filename,
            report_text=report_text
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# 10. WEARABLES, SLEEP, NEURO-CAP (40HZ) & GYM STRENGTH ENDPOINTS (Pod 10)
# =============================================================================
@app.get("/api/v1/portal/patients/{mpi_id}/wearables", response_model=PatientWearableDashboard)
def get_patient_wearables(mpi_id: uuid.UUID):
    try:
        return wearables_service.sync_patient_wearables(mpi_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wearables telemetry error: {str(e)}")

@app.post("/api/v1/portal/patients/{mpi_id}/wearables/sync", response_model=PatientWearableDashboard)
def sync_patient_wearables(mpi_id: uuid.UUID, payload: Optional[SyncWearablesInput] = None):
    try:
        steps_ovr = payload.step_override if payload else None
        rec_ovr = payload.whoop_recovery_override if payload else None
        return wearables_service.sync_patient_wearables(
            mpi_id=mpi_id,
            step_override=steps_ovr,
            whoop_recovery_override=rec_ovr
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wearables sync error: {str(e)}")

@app.post("/api/v1/portal/wearables/connect", response_model=DeviceConnection)
def connect_wearable_device(payload: ConnectDeviceInput):
    try:
        return wearables_service.connect_device(
            mpi_id=payload.mpi_id,
            device_type=payload.device_type,
            device_name=payload.device_name
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/portal/wearables/disconnect")
def disconnect_wearable_device(payload: DisconnectDeviceInput):
    try:
        success = wearables_service.disconnect_device(payload.mpi_id, payload.device_type)
        return {"status": "DISCONNECTED" if success else "NOT_FOUND", "device_type": payload.device_type.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/portal/wearables/log-workout", response_model=GymStrengthWorkoutTelemetry)
def log_gym_strength_workout(payload: LogWorkoutInput):
    try:
        return wearables_service.log_gym_workout(
            mpi_id=payload.mpi_id,
            workout_name=payload.workout_name,
            exercises=payload.exercises,
            duration_minutes=payload.duration_minutes,
            strain_generated=payload.strain_generated
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workout logging error: {str(e)}")

@app.post("/api/v1/portal/wearables/log-gamma", response_model=Gamma40HzTelemetry)
def log_gamma_session(payload: LogGammaSessionInput):
    try:
        return wearables_service.log_gamma_session(
            mpi_id=payload.mpi_id,
            duration_minutes=payload.duration_minutes,
            protocol=payload.protocol
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gamma session recording error: {str(e)}")

# =============================================================================
# 11. PERSONALIZED DIET PLAN & PUBMED NUTRITION RAG ENDPOINTS (Pod 11)
# =============================================================================
@app.get("/api/v1/nutrition/guidelines", response_model=List[ClinicalDietGuideline])
def get_nutrition_guidelines():
    return nutrition_rag_service.list_all_guidelines()

@app.get("/api/v1/nutrition/guidelines/{condition_key}", response_model=ClinicalDietGuideline)
def get_nutrition_guideline_by_key(condition_key: str):
    guide = nutrition_rag_service.get_guideline(condition_key.upper())
    if not guide:
        raise HTTPException(status_code=404, detail=f"Guideline for '{condition_key}' not found.")
    return guide

@app.post("/api/v1/nutrition/personalized-plan", response_model=PersonalizedDietPlan)
def generate_personalized_nutrition_plan(payload: GeneratePersonalizedPlanInput):
    try:
        return nutrition_rag_service.generate_personalized_diet_plan(
            patient_name=payload.patient_name,
            age=payload.age,
            surgical_case=payload.surgical_case,
            diagnosed_conditions=payload.diagnosed_conditions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diet synthesis error: {str(e)}")

@app.post("/api/v1/nutrition/rag-query", response_model=DietRAGQueryResponse)
def query_nutrition_rag(payload: DietRAGQueryInput):
    try:
        return nutrition_rag_service.query_nutrition_rag(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nutrition RAG query error: {str(e)}")



