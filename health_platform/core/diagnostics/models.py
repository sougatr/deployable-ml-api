"""
Diagnostic Laboratory & Radiology Information System (LIS/RIS) Domain Models.
Implements LOINC and SNOMED CT coded diagnostic orders, phlebotomy barcode tracking,
parameter reference range flags, and digital signature verifications.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DiagnosticCategory(str, Enum):
    LABORATORY = "LABORATORY"
    RADIOLOGY = "RADIOLOGY"

class DiagnosticModality(str, Enum):
    # Laboratory Disciplines
    BIOCHEMISTRY = "BIOCHEMISTRY"
    HEMATOLOGY = "HEMATOLOGY"
    MICROBIOLOGY = "MICROBIOLOGY"
    HISTOPATHOLOGY = "HISTOPATHOLOGY"
    # Radiology Modalities
    XRAY = "XRAY"
    ULTRASOUND = "ULTRASOUND"
    CT_SCAN = "CT_SCAN"
    MRI = "MRI"
    MAMMOGRAPHY = "MAMMOGRAPHY"

class SpecimenType(str, Enum):
    WHOLE_BLOOD_EDTA = "Whole Blood (EDTA Purple Top)"
    SERUM_PLAIN = "Serum (Plain Red/Gold Top)"
    PLASMA_FLUORIDE = "Fluoride Plasma (Grey Top)"
    PLASMA_CITRATE = "Citrated Plasma (Light Blue Top)"
    SPOT_URINE = "Random Spot Urine (Sterile Container)"
    STOOL = "Stool Specimen"
    TISSUE_BIOPSY = "Formalin Fixed Tissue Biopsy"
    NOT_APPLICABLE = "Not Applicable (Imaging Study)"

class DiagnosticStatus(str, Enum):
    ORDERED = "ORDERED"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
    RESULTED = "RESULTED"
    VERIFIED = "VERIFIED"
    CANCELLED = "CANCELLED"

class AbnormalFlag(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"
    CRITICAL_HIGH = "CRITICAL_HIGH"

class LabParameterDefinition(BaseModel):
    parameter_code: str
    parameter_name: str
    loinc_code: str
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None

class DiagnosticCatalogItem(BaseModel):
    item_code: str
    item_name: str
    category: DiagnosticCategory
    modality: DiagnosticModality
    standard_code: str # LOINC or SNOMED CT
    standard_coding_system: str # "http://loinc.org" or "http://snomed.info/sct"
    specimen_type: SpecimenType
    standard_turnaround_hrs: int
    base_tariff: float
    parameters: List[LabParameterDefinition] = Field(default_factory=list)

class LabParameterResult(BaseModel):
    parameter_code: str
    parameter_name: str
    loinc_code: str
    measured_value: str
    unit: str
    reference_range_display: str
    flag: AbnormalFlag = AbnormalFlag.NORMAL
    interpretation: Optional[str] = None

class DiagnosticOrderInput(BaseModel):
    mpi_id: uuid.UUID
    encounter_id: uuid.UUID
    item_code: str
    ordering_doctor_name: str
    clinical_history: Optional[str] = "Routine investigation"
    fasting_status: Optional[str] = "RANDOM"
    is_stat: bool = False # STAT / Urgent priority

class SpecimenCollectionInput(BaseModel):
    order_id: uuid.UUID
    phlebotomist_name: str
    collection_notes: Optional[str] = None

class LabResultEntryInput(BaseModel):
    order_id: uuid.UUID
    parameter_results: Dict[str, float] # parameter_code -> numerical value or measurement
    technician_notes: Optional[str] = None

class RadiologyReportEntryInput(BaseModel):
    order_id: uuid.UUID
    radiologist_name: str
    clinical_indication: str
    technique: str
    findings: str
    impression: str
    key_image_notes: Optional[str] = None

class VerificationInput(BaseModel):
    order_id: uuid.UUID
    verifier_name: str
    verifier_qualification: str
    verifier_registration_no: str
    clinical_comments: Optional[str] = None

class DiagnosticOrder(BaseModel):
    order_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    mpi_id: uuid.UUID
    encounter_id: uuid.UUID
    item_code: str
    item_name: str
    category: DiagnosticCategory
    modality: DiagnosticModality
    standard_code: str
    standard_coding_system: str
    tariff_amount: float
    ordering_doctor_name: str
    clinical_history: str
    is_stat: bool = False
    status: DiagnosticStatus = DiagnosticStatus.ORDERED
    
    # Specimen & Tracking
    specimen_type: SpecimenType
    sample_barcode: Optional[str] = None
    accession_number: Optional[str] = None
    collected_at: Optional[datetime] = None
    collected_by: Optional[str] = None

    # Results & Reports
    lab_results: List[LabParameterResult] = Field(default_factory=list)
    radiology_findings: Optional[str] = None
    radiology_impression: Optional[str] = None
    radiology_technique: Optional[str] = None
    
    # Sign-off & Verification
    verified_by: Optional[str] = None
    verifier_registration_no: Optional[str] = None
    verified_at: Optional[datetime] = None
    verifier_comments: Optional[str] = None
    
    ordered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    charge_item_id: Optional[uuid.UUID] = None
