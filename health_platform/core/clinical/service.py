import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from health_platform.core.clinical.models import (
    ConsultationInput,
    ConsultationResult
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.interop.abdm_m1_m2 import ABDMGatewayBridge
from health_platform.core.events.envelope import CloudEventEnvelope, TransactionalOutboxPublisher
from health_platform.core.common.exceptions import ClinicalSafetyViolation

class EncounterState:
    def __init__(self, encounter_id: uuid.UUID, mpi_id: uuid.UUID, practitioner_id: uuid.UUID, facility_id: uuid.UUID, tenant_id: uuid.UUID):
        self.encounter_id = encounter_id
        self.mpi_id = mpi_id
        self.practitioner_id = practitioner_id
        self.facility_id = facility_id
        self.tenant_id = tenant_id
        self.status = "IN_PROGRESS"
        self.started_at = datetime.now(timezone.utc)
        self.completed_at = None

class ClinicalEncounterService:
    """
    Orchestrates the Clinician Outpatient (OPD) Consultation Workflow (Pod 2).
    Connects Clinical Documentation -> Orders -> Real-Time Financial Ledger -> ABDM HIP Care Contexts.
    """
    def __init__(
        self,
        identity_service: PatientIdentityService,
        financial_service: FinancialLedgerService,
        abdm_bridge: ABDMGatewayBridge,
        outbox: TransactionalOutboxPublisher
    ):
        self.identity_service = identity_service
        self.financial_service = financial_service
        self.abdm_bridge = abdm_bridge
        self.outbox = outbox
        self._encounters: Dict[uuid.UUID, EncounterState] = {}
        self._clinical_notes: Dict[uuid.UUID, Dict[str, Any]] = {}
        self._active_orders: Dict[uuid.UUID, List[Dict[str, Any]]] = {}

    def start_opd_encounter(
        self,
        mpi_id: uuid.UUID,
        practitioner_id: uuid.UUID,
        facility_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> uuid.UUID:
        """Starts an active outpatient encounter context when a patient checks in."""
        if mpi_id not in self.identity_service._patients:
            raise ValueError(f"Patient with MPI {mpi_id} does not exist.")

        enc_id = uuid.uuid4()
        enc = EncounterState(
            encounter_id=enc_id,
            mpi_id=mpi_id,
            practitioner_id=practitioner_id,
            facility_id=facility_id,
            tenant_id=tenant_id
        )
        self._encounters[enc_id] = enc

        # Stage EncounterStarted event
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.encounter.started.v1",
                tenantid=tenant_id,
                mpiid=mpi_id,
                actorid=practitioner_id,
                actorrole="DOCTOR",
                data={
                    "encounter_id": str(enc_id),
                    "facility_id": str(facility_id),
                    "encounter_class": "AMBULATORY"
                }
            )
        )
        return enc_id

    def complete_consultation(self, req: ConsultationInput) -> ConsultationResult:
        """
        Finalizes doctor consultation: saves SOAP notes, issues e-prescriptions,
        places diagnostic orders, posts charges atomically to the financial ledger,
        and pushes ABDM M2 Care Contexts if ABHA is linked.
        """
        enc = self._encounters.get(req.encounter_id)
        if not enc or enc.status != "IN_PROGRESS":
            raise ValueError(f"Encounter {req.encounter_id} is not an active in-progress visit.")

        mpi_id = enc.mpi_id
        tenant_id = enc.tenant_id

        # 1. Store Final Signed Clinical Note
        note_id = uuid.uuid4()
        self._clinical_notes[note_id] = {
            "encounter_id": req.encounter_id,
            "mpi_id": mpi_id,
            "chief_complaint": req.chief_complaint,
            "narrative": req.clinical_narrative,
            "diagnoses": [d.model_dump() for d in req.diagnoses],
            "vitals": [v.model_dump() for v in req.vitals],
            "doctor_signature": req.doctor_digital_signature,
            "signed_at": datetime.now(timezone.utc)
        }

        # Stage ClinicalNoteSigned event
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.clinical.note_signed.v1",
                tenantid=tenant_id,
                mpiid=mpi_id,
                actorid=req.practitioner_id,
                actorrole="DOCTOR",
                data={
                    "note_id": str(note_id),
                    "encounter_id": str(req.encounter_id),
                    "icd10_codes": [d.code_icd10 for d in req.diagnoses]
                }
            )
        )

        total_charges = 0.0
        patient_payable = 0.0
        insurer_payable = 0.0

        # 2. Financial Ledger Posting: Doctor Consultation Fee (Clinical-Financial Invariant)
        if req.consultation_fee > 0:
            consult_charge = self.financial_service.capture_charge_from_clinical_order(
                encounter_id=req.encounter_id,
                mpi_id=mpi_id,
                originating_resource_type="ClinicalConsultation",
                originating_resource_id=note_id,
                tariff_code=req.consultation_tariff_code,
                department_code="OPD_CONSULT",
                unit_price=req.consultation_fee,
                quantity=1.0,
                patient_co_pay_ratio=req.patient_co_pay_ratio
            )
            total_charges += consult_charge.gross_amount
            patient_payable += consult_charge.patient_share
            insurer_payable += consult_charge.insurer_share

        # 3. Process Diagnostic Orders & Auto-Post Investigation Charges
        placed_order_ids = []
        for order_in in req.orders:
            order_id = uuid.uuid4()
            placed_order_ids.append(order_id)
            
            # Post billable charge linked strictly to order_id
            order_charge = self.financial_service.capture_charge_from_clinical_order(
                encounter_id=req.encounter_id,
                mpi_id=mpi_id,
                originating_resource_type="ServiceRequest",
                originating_resource_id=order_id,
                tariff_code=order_in.tariff_code,
                department_code=order_in.department_code,
                unit_price=order_in.unit_price,
                quantity=1.0,
                patient_co_pay_ratio=req.patient_co_pay_ratio
            )
            total_charges += order_charge.gross_amount
            patient_payable += order_charge.patient_share
            insurer_payable += order_charge.insurer_share

            # Stage OrderPlaced event
            self.outbox.stage_event(
                CloudEventEnvelope(
                    type="health.order.placed.v1",
                    tenantid=tenant_id,
                    mpiid=mpi_id,
                    data={
                        "service_request_id": str(order_id),
                        "encounter_id": str(req.encounter_id),
                        "code": order_in.code_loinc_or_snomed,
                        "display": order_in.display
                    }
                )
            )

        # 4. Process E-Prescriptions
        if req.prescriptions:
            rx_id = uuid.uuid4()
            self.outbox.stage_event(
                CloudEventEnvelope(
                    type="health.medication.prescription_issued.v1",
                    tenantid=tenant_id,
                    mpiid=mpi_id,
                    data={
                        "prescription_id": str(rx_id),
                        "encounter_id": str(req.encounter_id),
                        "medications": [p.model_dump() for p in req.prescriptions]
                    }
                )
            )

        # 5. ABDM Milestone 2 Care Context Auto-Linking (if patient has ABHA)
        patient_rec = self.identity_service._patients.get(mpi_id)
        abdm_linked = False
        care_context_id = None
        if patient_rec and (patient_rec.abha_number or patient_rec.abha_address):
            diag_summary = ", ".join(d.display for d in req.diagnoses) if req.diagnoses else "General Checkup"
            care_res = self.abdm_bridge.register_care_context(
                mpi_id=mpi_id,
                encounter_id=req.encounter_id,
                display_name=f"OPD Consult: {diag_summary}"
            )
            abdm_linked = True
            care_context_id = care_res["care_context"]["care_context_id"]

        # 6. Mark Encounter Completed
        now = datetime.now(timezone.utc)
        enc.status = "COMPLETED"
        enc.completed_at = now

        return ConsultationResult(
            encounter_id=req.encounter_id,
            mpi_id=mpi_id,
            status="COMPLETED",
            diagnoses_recorded=len(req.diagnoses),
            orders_placed=len(req.orders),
            prescriptions_issued=len(req.prescriptions),
            total_charges_posted=round(total_charges, 2),
            patient_share_payable=round(patient_payable, 2),
            insurer_share_payable=round(insurer_payable, 2),
            trial_balance_status="BALANCED" if self.financial_service.get_trial_balance_discrepancy() == 0.0 else "IMBALANCED",
            abdm_care_context_linked=abdm_linked,
            care_context_id=care_context_id,
            completed_at=now
        )
