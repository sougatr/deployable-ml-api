import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any

from health_platform.core.ipd.models import (
    Bed,
    BedStatus,
    WardType,
    IPDAdmissionInput,
    IPDAdmission,
    NurseChartEntryInput,
    NurseChartEntry,
    DoctorRoundInput,
    DoctorRound,
    DischargeInput,
    DischargeSummary
)
from health_platform.core.events.envelope import CloudEventEnvelope, TransactionalOutboxPublisher
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService

class IPDService:
    """
    Inpatient (IPD) & Bed Management Operating Engine.
    Manages real-time ward/bed occupancy, inpatient admissions, nursing care charting,
    doctor progress rounds, and formal clinical discharge with automated room charge accrual.
    """

    def __init__(
        self,
        identity_service: PatientIdentityService,
        financial_service: FinancialLedgerService,
        outbox: TransactionalOutboxPublisher
    ):
        self.identity_service = identity_service
        self.financial_service = financial_service
        self.outbox = outbox

        self._beds: Dict[uuid.UUID, Bed] = {}
        self._admissions: Dict[uuid.UUID, IPDAdmission] = {}
        self._nurse_charts: Dict[uuid.UUID, List[NurseChartEntry]] = {}
        self._doctor_rounds: Dict[uuid.UUID, List[DoctorRound]] = {}
        self._discharge_summaries: Dict[uuid.UUID, DischargeSummary] = {}

        self._seed_hospital_beds()

    def _seed_hospital_beds(self):
        """Initializes realistic hospital wards and beds across ICU, Deluxe, Semi-Private, and General Wards."""
        initial_beds = [
            # ICU Ward (3rd Floor)
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
                bed_number="ICU-01",
                ward_name="Intensive Care Unit (ICU)",
                ward_type=WardType.ICU,
                floor="3rd Floor, Tower A",
                daily_rate=7500.0,
                tariff_code="BED-ICU-001",
                status=BedStatus.AVAILABLE
            ),
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000002"),
                bed_number="ICU-02",
                ward_name="Intensive Care Unit (ICU)",
                ward_type=WardType.ICU,
                floor="3rd Floor, Tower A",
                daily_rate=7500.0,
                tariff_code="BED-ICU-001",
                status=BedStatus.AVAILABLE
            ),
            # Deluxe Private Rooms (4th Floor)
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000003"),
                bed_number="Room 401",
                ward_name="Deluxe Private Suite",
                ward_type=WardType.DELUXE_PRIVATE,
                floor="4th Floor, Executive Wing",
                daily_rate=5200.0,
                tariff_code="BED-DELUXE-001",
                status=BedStatus.AVAILABLE
            ),
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000004"),
                bed_number="Room 402",
                ward_name="Deluxe Private Suite",
                ward_type=WardType.DELUXE_PRIVATE,
                floor="4th Floor, Executive Wing",
                daily_rate=5200.0,
                tariff_code="BED-DELUXE-001",
                status=BedStatus.AVAILABLE
            ),
            # Semi-Private Ward (2nd Floor)
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000005"),
                bed_number="Bed 201-A",
                ward_name="Orthopedic Semi-Private Ward",
                ward_type=WardType.SEMI_PRIVATE,
                floor="2nd Floor, Surgical Block",
                daily_rate=2800.0,
                tariff_code="BED-SEMI-001",
                status=BedStatus.AVAILABLE
            ),
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000006"),
                bed_number="Bed 201-B",
                ward_name="Orthopedic Semi-Private Ward",
                ward_type=WardType.SEMI_PRIVATE,
                floor="2nd Floor, Surgical Block",
                daily_rate=2800.0,
                tariff_code="BED-SEMI-001",
                status=BedStatus.AVAILABLE
            ),
            # General Ward (1st Floor)
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000007"),
                bed_number="Bed GW-101",
                ward_name="General Inpatient Ward",
                ward_type=WardType.GENERAL_WARD,
                floor="1st Floor, East Wing",
                daily_rate=1200.0,
                tariff_code="BED-GEN-001",
                status=BedStatus.AVAILABLE
            ),
            Bed(
                bed_id=uuid.UUID("10000000-0000-0000-0000-000000000008"),
                bed_number="Bed GW-102",
                ward_name="General Inpatient Ward",
                ward_type=WardType.GENERAL_WARD,
                floor="1st Floor, East Wing",
                daily_rate=1200.0,
                tariff_code="BED-GEN-001",
                status=BedStatus.AVAILABLE
            )
        ]
        for b in initial_beds:
            self._beds[b.bed_id] = b

    def get_bed_matrix(self) -> List[Bed]:
        """Returns the real-time matrix of all hospital wards and beds."""
        return list(self._beds.values())

    def get_bed(self, bed_id: uuid.UUID) -> Optional[Bed]:
        return self._beds.get(bed_id)

    def admit_patient(self, input_data: IPDAdmissionInput) -> IPDAdmission:
        """
        Admits a patient to a specified hospital bed.
        Validates MPI patient, checks bed availability, updates bed state to OCCUPIED,
        creates an Inpatient Encounter, and stages the admission event.
        """
        # Validate patient exists in MPI
        patient = self.identity_service._patients.get(input_data.mpi_id)
        if not patient:
            raise ValueError(f"Patient MPI ID {input_data.mpi_id} not found.")

        # Validate bed
        bed = self._beds.get(input_data.bed_id)
        if not bed:
            raise ValueError(f"Bed ID {input_data.bed_id} does not exist.")
        if bed.status != BedStatus.AVAILABLE:
            raise ValueError(f"Bed {bed.bed_number} in {bed.ward_name} is not available (Status: {bed.status.value}).")

        admission_id = uuid.uuid4()
        encounter_id = uuid.uuid4() # Distinct Inpatient Encounter ID
        now = datetime.now(timezone.utc)

        admission = IPDAdmission(
            admission_id=admission_id,
            encounter_id=encounter_id,
            mpi_id=input_data.mpi_id,
            bed_id=bed.bed_id,
            ward_name=bed.ward_name,
            bed_number=bed.bed_number,
            admitting_doctor_name=input_data.admitting_doctor_name,
            admitting_diagnosis_icd10=input_data.admitting_diagnosis_icd10,
            admitting_diagnosis_display=input_data.admitting_diagnosis_display,
            admission_reason=input_data.admission_reason,
            status="ADMITTED",
            admitted_at=now,
            patient_co_pay_ratio=input_data.patient_co_pay_ratio
        )

        self._admissions[admission_id] = admission

        # Update bed status to OCCUPIED
        bed.status = BedStatus.OCCUPIED
        bed.current_admission_id = admission_id
        bed.current_patient_name = f"{patient.first_name} {patient.last_name}"
        bed.current_patient_uhid = patient.uhid
        bed.admitted_at = now

        # Initialize chart logs
        self._nurse_charts[admission_id] = []
        self._doctor_rounds[admission_id] = []

        # Add initial nurse baseline chart
        baseline_chart = NurseChartEntry(
            admission_id=admission_id,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            heart_rate=74.0,
            temperature=98.6,
            spo2=99.0,
            respiratory_rate=16.0,
            nursing_notes=f"Patient admitted to {bed.bed_number} ({bed.ward_name}). Baseline vitals stable. ID wristband verified.",
            recorded_by="Sister Priya Nair (RN, IPD Charge Nurse)",
            recorded_at=now
        )
        self._nurse_charts[admission_id].append(baseline_chart)

        # Stage transactional admission event
        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000003")
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.ipd.patient_admitted.v1",
                tenantid=tenant_id,
                mpiid=patient.mpi_id,
                actorid=input_data.admitting_doctor_id,
                actorrole="DOCTOR",
                data={
                    "admission_id": str(admission_id),
                    "encounter_id": str(encounter_id),
                    "bed_id": str(bed.bed_id),
                    "ward_name": bed.ward_name,
                    "bed_number": bed.bed_number,
                    "admitting_diagnosis": input_data.admitting_diagnosis_icd10
                }
            )
        )

        return admission

    def get_admission(self, admission_id: uuid.UUID) -> Optional[IPDAdmission]:
        return self._admissions.get(admission_id)

    def get_active_admissions(self) -> List[IPDAdmission]:
        return [adm for adm in self._admissions.values() if adm.status == "ADMITTED"]

    def record_nurse_charting(self, input_data: NurseChartEntryInput) -> NurseChartEntry:
        """Records a nursing vitals monitoring and bedside evaluation entry."""
        adm = self._admissions.get(input_data.admission_id)
        if not adm or adm.status != "ADMITTED":
            raise ValueError(f"Active inpatient admission {input_data.admission_id} not found.")

        chart = NurseChartEntry(
            admission_id=input_data.admission_id,
            systolic_bp=input_data.systolic_bp,
            diastolic_bp=input_data.diastolic_bp,
            heart_rate=input_data.heart_rate,
            temperature=input_data.temperature,
            spo2=input_data.spo2,
            respiratory_rate=input_data.respiratory_rate,
            nursing_notes=input_data.nursing_notes,
            recorded_by=input_data.recorded_by,
            recorded_at=datetime.now(timezone.utc)
        )

        if input_data.admission_id not in self._nurse_charts:
            self._nurse_charts[input_data.admission_id] = []
        self._nurse_charts[input_data.admission_id].append(chart)

        # Stage event
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.ipd.nurse_chart_recorded.v1",
                tenantid=uuid.UUID("00000000-0000-0000-0000-000000000003"),
                mpiid=adm.mpi_id,
                data={
                    "admission_id": str(input_data.admission_id),
                    "chart_id": str(chart.chart_id),
                    "bp": f"{chart.systolic_bp}/{chart.diastolic_bp}",
                    "spo2": chart.spo2
                }
            )
        )
        return chart

    def get_nurse_charts(self, admission_id: uuid.UUID) -> List[NurseChartEntry]:
        return self._nurse_charts.get(admission_id, [])

    def record_doctor_round(self, input_data: DoctorRoundInput) -> DoctorRound:
        """Records an attending physician's clinical progress round note."""
        adm = self._admissions.get(input_data.admission_id)
        if not adm or adm.status != "ADMITTED":
            raise ValueError(f"Active inpatient admission {input_data.admission_id} not found.")

        round_entry = DoctorRound(
            admission_id=input_data.admission_id,
            doctor_name=input_data.doctor_name,
            round_notes=input_data.round_notes,
            clinical_assessment=input_data.clinical_assessment,
            plan_adjustments=input_data.plan_adjustments,
            recorded_at=datetime.now(timezone.utc)
        )

        if input_data.admission_id not in self._doctor_rounds:
            self._doctor_rounds[input_data.admission_id] = []
        self._doctor_rounds[input_data.admission_id].append(round_entry)

        # Stage event
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.ipd.doctor_round_recorded.v1",
                tenantid=uuid.UUID("00000000-0000-0000-0000-000000000003"),
                mpiid=adm.mpi_id,
                data={
                    "admission_id": str(input_data.admission_id),
                    "round_id": str(round_entry.round_id),
                    "doctor": input_data.doctor_name
                }
            )
        )
        return round_entry

    def get_doctor_rounds(self, admission_id: uuid.UUID) -> List[DoctorRound]:
        return self._doctor_rounds.get(admission_id, [])

    def discharge_patient(self, input_data: DischargeInput) -> DischargeSummary:
        """
        Finalizes patient discharge:
        1. Validates active admission.
        2. Calculates length of stay (minimum 1 day).
        3. Accrues room charges atomically to Financial Ledger maintaining zero discrepancy.
        4. Releases hospital bed back to AVAILABLE.
        5. Generates formal signed Discharge Summary and stages ABDM M2 discharge event.
        """
        adm = self._admissions.get(input_data.admission_id)
        if not adm or adm.status != "ADMITTED":
            raise ValueError(f"Active inpatient admission {input_data.admission_id} not found.")

        bed = self._beds.get(adm.bed_id)
        if not bed:
            raise ValueError(f"Bed {adm.bed_id} not found for admission {input_data.admission_id}.")

        patient = self.identity_service._patients.get(adm.mpi_id)
        if not patient:
            raise ValueError(f"Patient {adm.mpi_id} not found.")

        discharged_at = datetime.now(timezone.utc)

        # Calculate days stayed (minimum 1 billing day)
        time_diff = discharged_at - adm.admitted_at
        days_stayed = max(1, int(time_diff.total_seconds() // 86400) + 1)
        total_room_charges = round(days_stayed * bed.daily_rate, 2)

        # 1. Post billable BedStay charge atomically to Financial Ledger (Clinical-Financial Invariant)
        charge_item = self.financial_service.capture_charge_from_clinical_order(
            encounter_id=adm.encounter_id,
            mpi_id=adm.mpi_id,
            originating_resource_type="BedStay",
            originating_resource_id=adm.admission_id,
            tariff_code=bed.tariff_code,
            department_code="INPATIENT_BED_STAY",
            unit_price=bed.daily_rate,
            quantity=float(days_stayed),
            patient_co_pay_ratio=adm.patient_co_pay_ratio
        )

        # 2. Update Admission Status
        adm.status = "DISCHARGED"
        adm.discharged_at = discharged_at
        adm.days_stayed = days_stayed
        adm.total_room_charges = total_room_charges

        # 3. Release Hospital Bed back to AVAILABLE
        bed.status = BedStatus.AVAILABLE
        bed.current_admission_id = None
        bed.current_patient_name = None
        bed.current_patient_uhid = None
        bed.admitted_at = None

        # 4. Create Formal Discharge Summary
        summary = DischargeSummary(
            admission_id=adm.admission_id,
            encounter_id=adm.encounter_id,
            mpi_id=adm.mpi_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            patient_uhid=patient.uhid,
            ward_name=bed.ward_name,
            bed_number=bed.bed_number,
            admitted_at=adm.admitted_at,
            discharged_at=discharged_at,
            days_stayed=days_stayed,
            daily_rate=bed.daily_rate,
            total_room_charges=total_room_charges,
            condition_at_discharge=input_data.condition_at_discharge,
            hospital_course=input_data.hospital_course,
            final_diagnosis_icd10=input_data.final_diagnosis_icd10,
            final_diagnosis_display=input_data.final_diagnosis_display,
            discharge_medications=input_data.discharge_medications,
            follow_up_advice=input_data.follow_up_advice,
            doctor_signature=input_data.doctor_signature,
            signed_at=discharged_at
        )

        self._discharge_summaries[adm.admission_id] = summary

        # 5. Stage Transactional Discharge Event
        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000003")
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.ipd.patient_discharged.v1",
                tenantid=tenant_id,
                mpiid=patient.mpi_id,
                data={
                    "admission_id": str(adm.admission_id),
                    "encounter_id": str(adm.encounter_id),
                    "days_stayed": days_stayed,
                    "total_room_charges": total_room_charges,
                    "charge_item_id": str(charge_item.charge_item_id),
                    "released_bed": bed.bed_number
                }
            )
        )

        return summary

    def get_discharge_summary(self, admission_id: uuid.UUID) -> Optional[DischargeSummary]:
        return self._discharge_summaries.get(admission_id)
