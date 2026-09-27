import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BedStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    CLEANING = "CLEANING"

class WardType(str, Enum):
    ICU = "ICU"
    DELUXE_PRIVATE = "DELUXE_PRIVATE"
    SEMI_PRIVATE = "SEMI_PRIVATE"
    GENERAL_WARD = "GENERAL_WARD"
    DAYCARE = "DAYCARE"

class Bed(BaseModel):
    bed_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    bed_number: str
    ward_name: str
    ward_type: WardType
    floor: str
    daily_rate: float
    tariff_code: str
    status: BedStatus = BedStatus.AVAILABLE
    current_admission_id: Optional[uuid.UUID] = None
    current_patient_name: Optional[str] = None
    current_patient_uhid: Optional[str] = None
    admitted_at: Optional[datetime] = None

class IPDAdmissionInput(BaseModel):
    mpi_id: uuid.UUID
    bed_id: uuid.UUID
    admitting_doctor_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    admitting_doctor_name: str = "Dr. Anup Khatri"
    admitting_diagnosis_icd10: str = "M23.30"
    admitting_diagnosis_display: str = "Tear of medial meniscus of knee (Status Post Root Repair)"
    admission_reason: str = "Post-operative orthopedic care, rehabilitation & observation"
    patient_co_pay_ratio: float = 1.0

class IPDAdmission(BaseModel):
    admission_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    bed_id: uuid.UUID
    ward_name: str
    bed_number: str
    admitting_doctor_name: str
    admitting_diagnosis_icd10: str
    admitting_diagnosis_display: str
    admission_reason: str
    status: str = "ADMITTED" # ADMITTED, DISCHARGED
    admitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    discharged_at: Optional[datetime] = None
    days_stayed: int = 0
    total_room_charges: float = 0.0
    patient_co_pay_ratio: float = 1.0

class NurseChartEntryInput(BaseModel):
    admission_id: uuid.UUID
    systolic_bp: float = 120.0
    diastolic_bp: float = 80.0
    heart_rate: float = 76.0
    temperature: float = 98.6
    spo2: float = 99.0
    respiratory_rate: float = 16.0
    nursing_notes: str = "Patient comfortable. Surgical dressing clean and dry. No complaints of severe pain."
    recorded_by: str = "Nurse Priya Nair (RN, IPD)"

class NurseChartEntry(BaseModel):
    chart_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    admission_id: uuid.UUID
    systolic_bp: float
    diastolic_bp: float
    heart_rate: float
    temperature: float
    spo2: float
    respiratory_rate: float
    nursing_notes: str
    recorded_by: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DoctorRoundInput(BaseModel):
    admission_id: uuid.UUID
    doctor_name: str = "Dr. Anup Khatri"
    round_notes: str = "Patient examined on morning rounds. Knee joint swelling significantly subsided. Active toe movements good."
    clinical_assessment: str = "Post-operative recovery on track. Safe for progressive ambulation."
    plan_adjustments: str = "Continue Tab Ezorb Forte. Initiate bedside quadriceps strengthening and gentle knee flexion."

class DoctorRound(BaseModel):
    round_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    admission_id: uuid.UUID
    doctor_name: str
    round_notes: str
    clinical_assessment: str
    plan_adjustments: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DischargeInput(BaseModel):
    admission_id: uuid.UUID
    condition_at_discharge: str = "Clinically stable, ambulating with support, surgical site dry and healing well."
    hospital_course: str = "Admitted for post-operative monitoring and initiation of physical therapy after Right Medial Meniscus Root repair. Uneventful in-hospital stay with excellent pain control and wound healing."
    final_diagnosis_icd10: str = "M23.30"
    final_diagnosis_display: str = "Tear of medial meniscus of knee (Status Post Root Repair)"
    discharge_medications: str = "Tab Ezorb Forte 0-1-0 x 90 days; Tab Paracetamol 650mg SOS for mild discomfort"
    follow_up_advice: str = "Non-Weight Bearing (NWB) x 10 days, progressing to Partial Weight Bearing (PWB). Suture removal in 2 weeks. OPD follow-up in 2 months with Dr. Anup Khatri."
    doctor_signature: str = "Dr. Anup Khatri, MBBS, DNB-Ortho (MMC-2006010368)"

class DischargeSummary(BaseModel):
    summary_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    admission_id: uuid.UUID
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    patient_name: str
    patient_uhid: str
    ward_name: str
    bed_number: str
    admitted_at: datetime
    discharged_at: datetime
    days_stayed: int
    daily_rate: float
    total_room_charges: float
    condition_at_discharge: str
    hospital_course: str
    final_diagnosis_icd10: str
    final_diagnosis_display: str
    discharge_medications: str
    follow_up_advice: str
    doctor_signature: str
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
