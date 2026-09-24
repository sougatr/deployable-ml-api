import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from health_platform.core.common.models import GenderEnum

class IdentifierType(str, Enum):
    MOBILE = "MOBILE"
    HOSPITAL_MRN = "MRN"
    ABHA_NUMBER = "ABHA_NUMBER"
    ABHA_ADDRESS = "ABHA_ADDRESS"
    AADHAAR_VAULT_TOKEN = "AADHAAR_VAULT_TOKEN"
    INSURANCE_MEMBER_ID = "INS_MEMBER_ID"

class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_OTP = "VERIFIED_OTP"
    VERIFIED_BIOMETRIC = "VERIFIED_BIOMETRIC"
    MANUAL_VERIFIED = "MANUAL_VERIFIED"

class IdentifierInput(BaseModel):
    id_type: IdentifierType
    id_value: str
    issuing_authority: Optional[str] = None
    facility_tenant_id: Optional[uuid.UUID] = None
    is_verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

class PatientRegistrationRequest(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    dob_is_estimated: bool = False
    gender: GenderEnum
    postal_code: Optional[str] = None
    primary_phone: str = Field(..., description="Mobile phone number used for login and OTP transport")
    identifiers: List[IdentifierInput] = Field(default_factory=list)
    facility_tenant_id: Optional[uuid.UUID] = None

class CandidateMatch(BaseModel):
    mpi_id: uuid.UUID
    uhid: str
    first_name: str
    last_name: str
    dob: date
    gender: GenderEnum
    confidence_score: float
    matched_reasons: List[str]

class PatientRecord(BaseModel):
    mpi_id: uuid.UUID
    uhid: str
    status: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    dob: date
    gender: GenderEnum
    primary_phone: Optional[str] = None
    abha_number: Optional[str] = None
    abha_address: Optional[str] = None
    active_mrns: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime

class PatientResolutionResponse(BaseModel):
    mpi_id: uuid.UUID
    uhid: str
    is_newly_created: bool
    potential_duplicates: List[CandidateMatch] = Field(default_factory=list)
    patient_record: Optional[PatientRecord] = None

class FamilyRelationshipType(str, Enum):
    SELF = "SELF"
    PARENT_OF = "PARENT_OF"
    CHILD_OF = "CHILD_OF"
    SPOUSE_OF = "SPOUSE_OF"
    LEGAL_GUARDIAN_OF = "LEGAL_GUARDIAN_OF"

class FamilyLinkRequest(BaseModel):
    account_holder_phone: str
    source_mpi_id: uuid.UUID
    target_mpi_id: uuid.UUID
    relationship_type: FamilyRelationshipType
    authorization_scope: str = "FULL_ACCESS"

class MergeRequest(BaseModel):
    deprecated_mpi_id: uuid.UUID
    surviving_mpi_id: uuid.UUID
    merge_reason: str
    authorized_by_user_id: uuid.UUID

class SplitRequest(BaseModel):
    merged_mpi_id: uuid.UUID
    identifiers_to_detach: List[uuid.UUID]
    encounter_ids_to_reassign: List[uuid.UUID]
    split_reason: str
    authorized_by_user_id: uuid.UUID
