"""
Patient / Client Portal Domain Models.
Defines patient-facing health records, AI medical interpretations,
medication guides, and personalized diet, exercise, and recovery roadmaps.
"""

from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DiseaseProfileItem(BaseModel):
    condition_name: str
    icd10_code: str
    source: str # "OPD Consultation", "Inpatient Admission", "Emergency Department"
    diagnosed_at: datetime
    status: str # "Active", "Healing / Stabilized", "Resolved"
    severity_level: str # "Mild", "Moderate", "High Acuity", "Critical"
    plain_english_summary: str
    what_causes_it: str
    what_to_expect: str

class LabParameterVisual(BaseModel):
    parameter_name: str
    measured_value: float
    unit: str
    reference_interval: str
    status: str # "NORMAL", "ELEVATED", "LOW", "CRITICAL"
    interpretation: str

class PatientLabReportAI(BaseModel):
    order_id: uuid.UUID
    test_name: str
    category: str # "LABORATORY", "RADIOLOGY"
    reported_at: datetime
    status: str
    patient_plain_explanation: str
    ai_clinical_takeaway: str
    is_abnormal: bool
    has_critical_findings: bool
    parameters: List[LabParameterVisual] = Field(default_factory=list)
    radiology_findings: Optional[str] = None
    radiology_impression: Optional[str] = None
    radiologist_or_pathologist: Optional[str] = None

class PatientMedicationAI(BaseModel):
    drug_name: str
    dosage: str
    frequency: str
    duration: str
    route: str = "Oral"
    purpose_ai: str
    timing_advice: str
    food_instructions: str
    key_precautions: str
    side_effects_to_watch: List[str] = Field(default_factory=list)
    dispensed: bool = False
    dispense_details: Optional[str] = None

class RecoveryMilestone(BaseModel):
    phase: str
    title: str
    focus_points: List[str] = Field(default_factory=list)
    expected_mobility: str

class DietFoodRecommendation(BaseModel):
    food_item: str
    category: str # "Superfood / Beneficial" or "Limit / Avoid"
    rationale: str

class ExerciseRoutineItem(BaseModel):
    exercise_name: str
    target_muscle_or_joint: str
    repetitions_and_sets: str
    instructions: str
    safety_precaution: str

class HealthRecommendationsAI(BaseModel):
    prognosis_overview: str
    estimated_recovery_timeline: str
    prognosis_milestones: List[RecoveryMilestone] = Field(default_factory=list)
    dietary_guidelines: List[DietFoodRecommendation] = Field(default_factory=list)
    hydration_target: str
    exercise_routine: List[ExerciseRoutineItem] = Field(default_factory=list)
    strict_activity_restrictions: List[str] = Field(default_factory=list)
    red_flag_warning_signs: List[str] = Field(default_factory=list)
    next_follow_up_advice: str

class PatientPortalSummary(BaseModel):
    mpi_id: uuid.UUID
    uhid: str
    full_name: str
    age: int
    gender: str
    phone: str
    abha_id: Optional[str] = None
    last_visit_date: Optional[datetime] = None
    current_care_setting: str # "Outpatient (Home)", "Inpatient (Room 401)", "Emergency"
    disease_profiles: List[DiseaseProfileItem] = Field(default_factory=list)
    lab_and_scan_reports: List[PatientLabReportAI] = Field(default_factory=list)
    active_prescriptions: List[PatientMedicationAI] = Field(default_factory=list)
    ai_recommendations: HealthRecommendationsAI
    vital_trends_summary: Dict[str, Any] = Field(default_factory=dict)

class PatientAIQueryInput(BaseModel):
    mpi_id: uuid.UUID
    question: str

class PatientAIQueryResponse(BaseModel):
    mpi_id: uuid.UUID
    question: str
    answer: str
    referenced_conditions: List[str] = Field(default_factory=list)
    referenced_medications: List[str] = Field(default_factory=list)
    safety_disclaimer: str = (
        "Medical Disclaimer: This AI interpretation is for educational and self-care support. "
        "It does not replace professional clinical evaluation. For sudden acute symptoms, "
        "contact your physician or visit Emergency immediately."
    )
