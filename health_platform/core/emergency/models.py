"""
Emergency Department (ED / ER) & Triage Domain Models.
Implements Manchester / Emergency Severity Index (ESI) Triage protocols,
Resuscitation and Code Red intervention tracking, and ER-to-IPD admission pipelines.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ESITriageLevel(str, Enum):
    LEVEL_1_RED = "LEVEL_1_RED"           # Resuscitation: Immediate life-saving intervention needed
    LEVEL_2_ORANGE = "LEVEL_2_ORANGE"     # Emergent: High-risk, severe pain, altered mental status
    LEVEL_3_YELLOW = "LEVEL_3_YELLOW"     # Urgent: Multiple resources required, stable vitals
    LEVEL_4_GREEN = "LEVEL_4_GREEN"       # Less Urgent: One resource required
    LEVEL_5_BLUE = "LEVEL_5_BLUE"         # Non-urgent: No acute resources required

class ERBayType(str, Enum):
    RESUSCITATION_BAY = "RESUSCITATION_BAY"
    TRAUMA_BAY = "TRAUMA_BAY"
    ACUTE_BAY = "ACUTE_BAY"
    OBSERVATION_BAY = "OBSERVATION_BAY"

class ERBayStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"

class ERDispositionType(str, Enum):
    ADMIT_TO_ICU = "ADMIT_TO_ICU"
    ADMIT_TO_IPD_WARD = "ADMIT_TO_IPD_WARD"
    DISCHARGE_HOME = "DISCHARGE_HOME"
    TRANSFER_EXTERNAL = "TRANSFER_EXTERNAL"
    EXPIRED = "EXPIRED"

class ERCaseStatus(str, Enum):
    TRIAGED = "TRIAGED"
    RESUSCITATION_ACTIVE = "RESUSCITATION_ACTIVE"
    STABILIZED = "STABILIZED"
    DISPOSED = "DISPOSED"

class ERBay(BaseModel):
    bay_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    bay_number: str # e.g. "RESUS-01", "TRAUMA-01", "ACUTE-02"
    bay_type: ERBayType
    status: ERBayStatus = ERBayStatus.AVAILABLE
    current_case_id: Optional[uuid.UUID] = None
    current_patient_name: Optional[str] = None
    current_triage_level: Optional[ESITriageLevel] = None

class TriageAssessmentInput(BaseModel):
    mpi_id: uuid.UUID
    chief_complaint: str
    triage_level: ESITriageLevel
    gcs_score: int = Field(ge=3, le=15, default=15) # Glasgow Coma Scale (3-15)
    systolic_bp: float = 120.0
    diastolic_bp: float = 80.0
    heart_rate: float = 80.0
    respiratory_rate: float = 18.0
    spo2: float = 98.0
    temperature: float = 98.6
    pain_score: int = Field(ge=0, le=10, default=0)
    mode_of_arrival: str = "WALK_IN" # WALK_IN, AMBULANCE_ALS, AMBULANCE_BLS, POLICE
    triage_nurse_name: str
    allocated_bay_id: Optional[uuid.UUID] = None

class ResuscitationInterventionInput(BaseModel):
    case_id: uuid.UUID
    intervention_type: str # e.g. "DEFIBRILLATION", "INTUBATION", "IV_FLUID_BOLUS", "EMERGENCY_MEDICATION", "POCUS_EFAST"
    details: str # e.g. "200J Biphasic shock delivered for VF", "Endotracheal tube 7.5mm placed at 22cm mark"
    medications_given: Optional[str] = None # e.g. "Inj Adrenaline 1mg IV push, Inj Amiodarone 300mg"
    clinician_name: str
    gcs_post: Optional[int] = None
    vitals_post: Optional[str] = None

class ResuscitationIntervention(BaseModel):
    intervention_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    case_id: uuid.UUID
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    intervention_type: str
    details: str
    medications_given: Optional[str] = None
    clinician_name: str
    gcs_post: Optional[int] = None
    vitals_post: Optional[str] = None

class ERDispositionInput(BaseModel):
    case_id: uuid.UUID
    disposition_type: ERDispositionType
    target_bed_id: Optional[uuid.UUID] = None # When transferring to ICU / IPD Bed Hub
    final_er_diagnosis: str
    discharge_or_transfer_notes: str
    attending_er_physician: str
    physician_reg_no: str

class ERCaseRecord(BaseModel):
    case_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    encounter_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    case_number: str # e.g. "ER-2026-1001"
    mpi_id: uuid.UUID
    patient_name: str
    patient_uhid: str
    arrived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chief_complaint: str
    triage_level: ESITriageLevel
    gcs_score: int
    systolic_bp: float
    diastolic_bp: float
    heart_rate: float
    respiratory_rate: float
    spo2: float
    temperature: float
    pain_score: int
    mode_of_arrival: str
    triage_nurse_name: str
    allocated_bay_id: uuid.UUID
    allocated_bay_number: str
    status: ERCaseStatus = ERCaseStatus.TRIAGED
    
    interventions: List[ResuscitationIntervention] = Field(default_factory=list)
    
    # Disposition details
    disposition: Optional[ERDispositionType] = None
    disposition_at: Optional[datetime] = None
    target_ipd_admission_id: Optional[uuid.UUID] = None
    final_er_diagnosis: Optional[str] = None
    er_physician_signature: Optional[str] = None
    
    triage_charge_item_id: Optional[uuid.UUID] = None
    total_er_charges: float = 0.0
