"""
Emergency Department (ED / ER) & Triage Service.
Orchestrates Emergency Severity Index (ESI) Triage, Resuscitation & Code Red tracking,
and seamless ER-to-IPD admission transfers with zero clinical-financial discrepancy.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from health_platform.core.events.envelope import CloudEventEnvelope
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
from health_platform.core.ipd.models import IPDAdmissionInput, WardType, BedStatus

class EmergencyService:
    def __init__(self, identity_service, financial_service, ipd_service=None, outbox=None):
        self.identity_service = identity_service
        self.financial_service = financial_service
        self.ipd_service = ipd_service
        self.outbox = outbox

        self._bays: Dict[uuid.UUID, ERBay] = {}
        self._cases: Dict[uuid.UUID, ERCaseRecord] = {}
        self._case_counter: int = 1000

        self._seed_er_bays()

    def _seed_er_bays(self):
        """Initializes 6 standard Emergency Department bays."""
        initial_bays = [
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000001"),
                bay_number="RESUS-01 (Code Red)",
                bay_type=ERBayType.RESUSCITATION_BAY,
                status=ERBayStatus.AVAILABLE
            ),
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000002"),
                bay_number="RESUS-02 (Code Red)",
                bay_type=ERBayType.RESUSCITATION_BAY,
                status=ERBayStatus.AVAILABLE
            ),
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000003"),
                bay_number="TRAUMA-01",
                bay_type=ERBayType.TRAUMA_BAY,
                status=ERBayStatus.AVAILABLE
            ),
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000004"),
                bay_number="ACUTE-01",
                bay_type=ERBayType.ACUTE_BAY,
                status=ERBayStatus.AVAILABLE
            ),
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000005"),
                bay_number="ACUTE-02",
                bay_type=ERBayType.ACUTE_BAY,
                status=ERBayStatus.AVAILABLE
            ),
            ERBay(
                bay_id=uuid.UUID("20000000-0000-0000-0000-000000000006"),
                bay_number="OBS-01",
                bay_type=ERBayType.OBSERVATION_BAY,
                status=ERBayStatus.AVAILABLE
            ),
        ]
        for b in initial_bays:
            self._bays[b.bay_id] = b

    def get_er_bays(self) -> List[ERBay]:
        """Returns all Emergency Department bays."""
        return list(self._bays.values())

    def get_bay(self, bay_id: uuid.UUID) -> Optional[ERBay]:
        return self._bays.get(bay_id)

    def get_active_cases(self) -> List[ERCaseRecord]:
        """Returns all currently active (non-disposed) ER cases."""
        return [c for c in self._cases.values() if c.status != ERCaseStatus.DISPOSED]

    def get_all_cases(self) -> List[ERCaseRecord]:
        return list(self._cases.values())

    def get_case(self, case_id: uuid.UUID) -> Optional[ERCaseRecord]:
        return self._cases.get(case_id)

    def triage_patient(self, input_data: TriageAssessmentInput) -> ERCaseRecord:
        """
        Performs Manchester / ESI Emergency Triage intake.
        Allocates an ER Bay, posts triage fee to the Financial Ledger,
        and stages the triage event.
        """
        # 1. Validate patient in MPI
        patient = self.identity_service._patients.get(input_data.mpi_id)
        if not patient:
            raise ValueError(f"Patient MPI ID {input_data.mpi_id} not found.")

        # 2. Allocate ER Bay
        bay: Optional[ERBay] = None
        if input_data.allocated_bay_id:
            bay = self._bays.get(input_data.allocated_bay_id)
            if not bay:
                raise ValueError(f"Bay ID {input_data.allocated_bay_id} not found.")
            if bay.status != ERBayStatus.AVAILABLE:
                raise ValueError(f"Bay {bay.bay_number} is currently {bay.status.value}.")
        else:
            # Automatic bay routing based on clinical acuity
            if input_data.triage_level == ESITriageLevel.LEVEL_1_RED:
                priorities = [ERBayType.RESUSCITATION_BAY, ERBayType.TRAUMA_BAY, ERBayType.ACUTE_BAY]
            elif input_data.triage_level == ESITriageLevel.LEVEL_2_ORANGE:
                priorities = [ERBayType.TRAUMA_BAY, ERBayType.ACUTE_BAY, ERBayType.RESUSCITATION_BAY]
            else:
                priorities = [ERBayType.ACUTE_BAY, ERBayType.OBSERVATION_BAY, ERBayType.TRAUMA_BAY]

            for p_type in priorities:
                for b in self._bays.values():
                    if b.status == ERBayStatus.AVAILABLE and b.bay_type == p_type:
                        bay = b
                        break
                if bay:
                    break

            if not bay:
                # Any available bay fallback
                for b in self._bays.values():
                    if b.status == ERBayStatus.AVAILABLE:
                        bay = b
                        break

            if not bay:
                raise ValueError("All Emergency Department bays are occupied. Activate Surge Disaster Protocol.")

        case_id = uuid.uuid4()
        encounter_id = uuid.uuid4()
        self._case_counter += 1
        case_number = f"ER-2026-{self._case_counter}"
        patient_name = f"{patient.first_name} {patient.last_name}"

        # 3. Post Clinical-Financial Triage Charge
        if input_data.triage_level == ESITriageLevel.LEVEL_1_RED:
            unit_price = 2500.0
            tariff_code = "EMERG-RESUS-001"
        elif input_data.triage_level == ESITriageLevel.LEVEL_2_ORANGE:
            unit_price = 1500.0
            tariff_code = "EMERG-EMERGENT-002"
        else:
            unit_price = 1000.0
            tariff_code = "EMERG-TRIAGE-003"

        charge_item = self.financial_service.capture_charge_from_clinical_order(
            encounter_id=encounter_id,
            mpi_id=patient.mpi_id,
            originating_resource_type="EmergencyEncounter",
            originating_resource_id=case_id,
            tariff_code=tariff_code,
            department_code="EMERGENCY",
            unit_price=unit_price,
            quantity=1.0,
            patient_co_pay_ratio=1.0
        )

        # 4. Occupy ER Bay
        bay.status = ERBayStatus.OCCUPIED
        bay.current_case_id = case_id
        bay.current_patient_name = patient_name
        bay.current_triage_level = input_data.triage_level

        initial_status = (
            ERCaseStatus.RESUSCITATION_ACTIVE
            if input_data.triage_level == ESITriageLevel.LEVEL_1_RED
            else ERCaseStatus.TRIAGED
        )

        record = ERCaseRecord(
            case_id=case_id,
            encounter_id=encounter_id,
            case_number=case_number,
            mpi_id=patient.mpi_id,
            patient_name=patient_name,
            patient_uhid=patient.uhid,
            arrived_at=datetime.now(timezone.utc),
            chief_complaint=input_data.chief_complaint,
            triage_level=input_data.triage_level,
            gcs_score=input_data.gcs_score,
            systolic_bp=input_data.systolic_bp,
            diastolic_bp=input_data.diastolic_bp,
            heart_rate=input_data.heart_rate,
            respiratory_rate=input_data.respiratory_rate,
            spo2=input_data.spo2,
            temperature=input_data.temperature,
            pain_score=input_data.pain_score,
            mode_of_arrival=input_data.mode_of_arrival,
            triage_nurse_name=input_data.triage_nurse_name,
            allocated_bay_id=bay.bay_id,
            allocated_bay_number=bay.bay_number,
            status=initial_status,
            triage_charge_item_id=charge_item.charge_item_id,
            total_er_charges=unit_price
        )

        self._cases[case_id] = record

        # 5. Stage CloudEvent
        if self.outbox:
            tenant_id = (
                getattr(patient, "tenant_id", None)
                or getattr(patient, "facility_tenant_id", None)
                or uuid.UUID("00000000-0000-0000-0000-000000000006")
            )
            self.outbox.stage_event(
                CloudEventEnvelope(
                    type="health.emergency.patient_triaged.v1",
                    tenantid=tenant_id,
                    mpiid=patient.mpi_id,
                    actorid=uuid.uuid4(),
                    actorrole="NURSE",
                    data={
                        "case_id": str(case_id),
                        "case_number": case_number,
                        "triage_level": input_data.triage_level.value,
                        "bay_number": bay.bay_number,
                        "chief_complaint": input_data.chief_complaint,
                        "charge_amount": unit_price
                    }
                )
            )

        return record

    def record_resuscitation_intervention(
        self, input_data: ResuscitationInterventionInput
    ) -> ResuscitationIntervention:
        """
        Logs a critical resuscitation intervention (defibrillation, intubation, meds, etc.),
        updates case status to RESUSCITATION_ACTIVE, captures procedural charge, and stages event.
        """
        case = self._cases.get(input_data.case_id)
        if not case:
            raise ValueError(f"ER Case ID {input_data.case_id} not found.")

        if case.status == ERCaseStatus.DISPOSED:
            raise ValueError(f"Cannot record resuscitation on disposed ER Case {case.case_number}.")

        intervention = ResuscitationIntervention(
            intervention_id=uuid.uuid4(),
            case_id=case.case_id,
            recorded_at=datetime.now(timezone.utc),
            intervention_type=input_data.intervention_type,
            details=input_data.details,
            medications_given=input_data.medications_given,
            clinician_name=input_data.clinician_name,
            gcs_post=input_data.gcs_post,
            vitals_post=input_data.vitals_post
        )

        case.interventions.append(intervention)
        case.status = ERCaseStatus.RESUSCITATION_ACTIVE

        # Post procedural charge (e.g. ₹1,200.00 resuscitation procedural fee)
        proc_charge = 1200.0
        tariff_code = f"EMERG-PROC-{input_data.intervention_type[:12].upper()}"
        self.financial_service.capture_charge_from_clinical_order(
            encounter_id=case.encounter_id,
            mpi_id=case.mpi_id,
            originating_resource_type="ResuscitationLog",
            originating_resource_id=intervention.intervention_id,
            tariff_code=tariff_code,
            department_code="EMERGENCY_RESUS",
            unit_price=proc_charge,
            quantity=1.0,
            patient_co_pay_ratio=1.0
        )
        case.total_er_charges += proc_charge

        if self.outbox:
            patient = self.identity_service._patients.get(case.mpi_id)
            tenant_id = (
                getattr(patient, "tenant_id", None)
                or getattr(patient, "facility_tenant_id", None)
                or uuid.UUID("00000000-0000-0000-0000-000000000006")
            )
            self.outbox.stage_event(
                CloudEventEnvelope(
                    type="health.emergency.resuscitation_performed.v1",
                    tenantid=tenant_id,
                    mpiid=case.mpi_id,
                    actorid=uuid.uuid4(),
                    actorrole="DOCTOR",
                    data={
                        "case_id": str(case.case_id),
                        "intervention_id": str(intervention.intervention_id),
                        "intervention_type": input_data.intervention_type,
                        "clinician_name": input_data.clinician_name,
                        "details": input_data.details
                    }
                )
            )

        return intervention

    def finalize_er_disposition(self, input_data: ERDispositionInput) -> ERCaseRecord:
        """
        Finalizes ER disposition:
        - Discharge Home, External Transfer, or Direct ER-to-IPD/ICU Admission.
        - If admitted to ICU or Ward, automatically invokes IPDService.admit_patient with target bed.
        - Releases ER Bay back to AVAILABLE state.
        - Stages disposition CloudEvent.
        """
        case = self._cases.get(input_data.case_id)
        if not case:
            raise ValueError(f"ER Case ID {input_data.case_id} not found.")

        if case.status == ERCaseStatus.DISPOSED:
            raise ValueError(f"ER Case {case.case_number} has already been disposed.")

        target_admission_id: Optional[uuid.UUID] = None

        # ER-to-IPD admission pipeline
        if input_data.disposition_type in [
            ERDispositionType.ADMIT_TO_ICU,
            ERDispositionType.ADMIT_TO_IPD_WARD
        ]:
            if not self.ipd_service:
                raise ValueError("IPD Service not configured. Cannot process ER-to-IPD transfer.")

            target_bed_id = input_data.target_bed_id
            if not target_bed_id:
                # Auto-find matching available bed in IPD
                beds = self.ipd_service.get_bed_matrix()
                if input_data.disposition_type == ERDispositionType.ADMIT_TO_ICU:
                    matching = [b for b in beds if b.ward_type == WardType.ICU and b.status == BedStatus.AVAILABLE]
                else:
                    matching = [b for b in beds if b.ward_type != WardType.ICU and b.status == BedStatus.AVAILABLE]

                if not matching:
                    raise ValueError(
                        f"No available beds in {input_data.disposition_type.value} to complete ER transfer."
                    )
                target_bed_id = matching[0].bed_id

            ipd_adm = self.ipd_service.admit_patient(
                IPDAdmissionInput(
                    mpi_id=case.mpi_id,
                    bed_id=target_bed_id,
                    admitting_doctor_name=input_data.attending_er_physician,
                    admitting_diagnosis_icd10="R57.9",
                    admitting_diagnosis_display=input_data.final_er_diagnosis,
                    admission_reason=f"ER Transfer: {input_data.discharge_or_transfer_notes}",
                    patient_co_pay_ratio=1.0
                )
            )
            target_admission_id = ipd_adm.admission_id

        # Release ER Bay
        bay = self._bays.get(case.allocated_bay_id)
        if bay:
            bay.status = ERBayStatus.AVAILABLE
            bay.current_case_id = None
            bay.current_patient_name = None
            bay.current_triage_level = None

        # Update Case record
        case.status = ERCaseStatus.DISPOSED
        case.disposition = input_data.disposition_type
        case.disposition_at = datetime.now(timezone.utc)
        case.final_er_diagnosis = input_data.final_er_diagnosis
        case.target_ipd_admission_id = target_admission_id
        case.er_physician_signature = f"{input_data.attending_er_physician} ({input_data.physician_reg_no})"

        if self.outbox:
            patient = self.identity_service._patients.get(case.mpi_id)
            tenant_id = (
                getattr(patient, "tenant_id", None)
                or getattr(patient, "facility_tenant_id", None)
                or uuid.UUID("00000000-0000-0000-0000-000000000006")
            )
            self.outbox.stage_event(
                CloudEventEnvelope(
                    type="health.emergency.disposition_finalized.v1",
                    tenantid=tenant_id,
                    mpiid=case.mpi_id,
                    actorid=uuid.uuid4(),
                    actorrole="DOCTOR",
                    data={
                        "case_id": str(case.case_id),
                        "case_number": case.case_number,
                        "disposition": input_data.disposition_type.value,
                        "target_ipd_admission_id": str(target_admission_id) if target_admission_id else None,
                        "attending_physician": input_data.attending_er_physician
                    }
                )
            )

        return case
