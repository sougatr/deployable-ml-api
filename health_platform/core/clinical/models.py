import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ConditionInput(BaseModel):
    code_icd10: str = Field(..., example="I10", description="ICD-10 clinical diagnosis code")
    code_snomed: Optional[str] = Field(None, example="38341003", description="SNOMED-CT concept ID")
    display: str = Field(..., example="Essential (primary) hypertension")
    clinical_status: str = "ACTIVE"
    verification_status: str = "CONFIRMED"

class VitalSignInput(BaseModel):
    code_loinc: str = Field(..., example="8480-6", description="LOINC code for observation")
    display: str = Field(..., example="Systolic Blood Pressure")
    value: float = Field(..., example=138.0)
    unit: str = Field(..., example="mm[Hg]", description="UCUM standard unit")
    interpretation: Optional[str] = Field("HIGH", example="HIGH")

class PrescriptionItemInput(BaseModel):
    brand_name: str = Field(..., example="Telma 40")
    generic_name: str = Field(..., example="Telmisartan 40mg")
    dosage_form: str = Field("TABLET", example="TABLET")
    timing: str = Field("1-0-0", example="1-0-0", description="Daily timing pattern (Morning-Afternoon-Night)")
    duration_days: int = Field(30, ge=1, example=30)
    instructions: Optional[str] = Field("Take 1 tablet every morning after breakfast", example="Take after breakfast")

class DiagnosticOrderInput(BaseModel):
    category: str = Field("LABORATORY", example="LABORATORY")
    code_loinc_or_snomed: str = Field(..., example="4548-4")
    display: str = Field(..., example="HbA1c Blood Test")
    tariff_code: str = Field(..., example="LAB-BIO-042")
    department_code: str = Field("BIOCHEMISTRY", example="BIOCHEMISTRY")
    unit_price: float = Field(..., ge=0.0, example=650.00)
    priority: str = Field("ROUTINE", example="ROUTINE")

class ConsultationInput(BaseModel):
    encounter_id: uuid.UUID
    practitioner_id: uuid.UUID
    chief_complaint: str = Field(..., example="Persistent headache and fatigue for 2 weeks")
    clinical_narrative: str = Field(..., example="Patient presented with mild elevated BP. No chest pain or dyspnea.")
    vitals: List[VitalSignInput] = Field(default_factory=list)
    diagnoses: List[ConditionInput] = Field(default_factory=list)
    orders: List[DiagnosticOrderInput] = Field(default_factory=list)
    prescriptions: List[PrescriptionItemInput] = Field(default_factory=list)
    consultation_fee: float = Field(500.00, ge=0.0)
    consultation_tariff_code: str = Field("CON-OPD-GEN", example="CON-OPD-GEN")
    patient_co_pay_ratio: float = Field(1.0, ge=0.0, le=1.0, description="1.0 = Self-pay, 0.2 = 20% co-pay")
    doctor_digital_signature: str = Field(..., example="SIG-SHA256-DR-ANAND-8812")

class ConsultationResult(BaseModel):
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    status: str
    diagnoses_recorded: int
    orders_placed: int
    prescriptions_issued: int
    total_charges_posted: float
    patient_share_payable: float
    insurer_share_payable: float
    trial_balance_status: str
    abdm_care_context_linked: bool
    care_context_id: Optional[str] = None
    completed_at: datetime
