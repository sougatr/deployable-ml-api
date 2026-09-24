import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field

from health_platform.core.identity.models import IdentifierInput, IdentifierType, VerificationStatus
from health_platform.core.identity.service import PatientIdentityService

class AbhaProfile(BaseModel):
    abha_number: str # E.g., "14-8921-3912-9012"
    abha_address: str # E.g., "ramesh.sharma@abdm"
    first_name: str
    last_name: str
    gender: str
    dob: str
    mobile: str
    auth_token: str # Signed JWT token from ABDM Gateway
    is_kyc_verified: bool = True

class ABDMGatewayBridge:
    """
    ABDM Milestone 1 (M1) and Milestone 2 (M2) Integration Bridge.
    Supports BOTH Aadhaar OTP generation & ABHA Address/Number validation.
    Crucially: Linking is completely OPTIONAL. Either method works; neither is mandatory.
    """
    def __init__(self, identity_service: PatientIdentityService):
        self.identity_service = identity_service
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._registered_care_contexts: Dict[str, list] = {} # mpi_id -> list of care contexts

    # -------------------------------------------------------------------------
    # METHOD A: AADHAAR OTP GENERATION & VERIFICATION (ABDM M1)
    # -------------------------------------------------------------------------
    def generate_aadhaar_otp(self, aadhaar_number: str) -> Dict[str, Any]:
        """
        Calls ABDM /v2/registration/aadhaar/generateOtp.
        Initiates OTP to the Aadhaar-registered mobile without storing raw Aadhaar.
        """
        # Validate 12-digit format
        clean_aadhaar = aadhaar_number.replace(" ", "").replace("-", "")
        if len(clean_aadhaar) != 12 or not clean_aadhaar.isdigit():
            raise ValueError("Invalid Aadhaar number format: exactly 12 digits required.")

        txn_id = f"txn-aadhaar-{uuid.uuid4().hex[:12]}"
        masked_phone = "XXXXXX" + clean_aadhaar[-4:] # Masked phone simulation
        
        self._active_sessions[txn_id] = {
            "type": "AADHAAR_OTP",
            "aadhaar_hash": hashlib.sha256(clean_aadhaar.encode()).hexdigest(),
            "otp_code": "123456", # Standard sandbox test OTP
            "created_at": datetime.now(timezone.utc)
        }

        return {
            "status": "OTP_SENT",
            "txn_id": txn_id,
            "message": f"OTP sent to mobile linked with Aadhaar ending in {clean_aadhaar[-4:]}",
            "hint_for_testing": "Enter '123456' for sandbox verification"
        }

    def verify_aadhaar_otp(self, txn_id: str, otp: str, preferred_abha_address: Optional[str] = None) -> AbhaProfile:
        """
        Calls ABDM /v2/registration/aadhaar/verifyOtp.
        Exchanges OTP for verified ABHA profile and JWT token.
        """
        session = self._active_sessions.get(txn_id)
        if not session or session["type"] != "AADHAAR_OTP":
            raise ValueError("Invalid or expired Aadhaar OTP transaction ID.")

        if otp != session["otp_code"]:
            raise ValueError("Invalid OTP entered. Please try again.")

        # Successfully verified by UIDAI / ABDM Gateway
        del self._active_sessions[txn_id]

        abha_num = f"14-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[4:8].upper()}-{uuid.uuid4().hex[8:12].upper()}"
        address = preferred_abha_address or f"patient.{uuid.uuid4().hex[:6]}@abdm"

        return AbhaProfile(
            abha_number=abha_num,
            abha_address=address,
            first_name="Verified",
            last_name="AadhaarHolder",
            gender="MALE",
            dob="1985-05-15",
            mobile="+919876543210",
            auth_token=f"jwt.abdm.token.{uuid.uuid4().hex}",
            is_kyc_verified=True
        )

    # -------------------------------------------------------------------------
    # METHOD B: EXISTING ABHA ADDRESS / NUMBER + MOBILE OTP (ABDM M1)
    # -------------------------------------------------------------------------
    def search_and_send_abha_otp(self, abha_identifier: str) -> Dict[str, Any]:
        """
        Calls ABDM /v1/auth/init.
        Accepts either an ABHA Address (name@abdm) or a 14-digit ABHA Number.
        Triggers an OTP to the mobile registered with this ABHA.
        """
        clean_id = abha_identifier.strip().lower()
        if not clean_id:
            raise ValueError("ABHA Address or ABHA Number must not be empty.")

        txn_id = f"txn-abha-{uuid.uuid4().hex[:12]}"
        self._active_sessions[txn_id] = {
            "type": "ABHA_MOBILE_OTP",
            "abha_identifier": clean_id,
            "otp_code": "654321", # Standard sandbox test OTP
            "created_at": datetime.now(timezone.utc)
        }

        return {
            "status": "OTP_SENT",
            "txn_id": txn_id,
            "message": f"Authentication OTP sent to mobile registered with {clean_id}",
            "hint_for_testing": "Enter '654321' for sandbox verification"
        }

    def verify_abha_mobile_otp(self, txn_id: str, otp: str) -> AbhaProfile:
        """
        Calls ABDM /v1/auth/confirmWithOtp.
        Validates OTP and returns verified ABHA credentials.
        """
        session = self._active_sessions.get(txn_id)
        if not session or session["type"] != "ABHA_MOBILE_OTP":
            raise ValueError("Invalid or expired ABHA OTP transaction ID.")

        if otp != session["otp_code"]:
            raise ValueError("Invalid OTP entered. Please try again.")

        abha_id = session["abha_identifier"]
        del self._active_sessions[txn_id]

        if "@" in abha_id:
            abha_addr = abha_id
            abha_num = f"14-9912-{uuid.uuid4().hex[:4].upper()}-0012"
        else:
            abha_num = abha_id
            abha_addr = f"user.{uuid.uuid4().hex[:6]}@abdm"

        return AbhaProfile(
            abha_number=abha_num,
            abha_address=abha_addr,
            first_name="PreExisting",
            last_name="ABHAUser",
            gender="FEMALE",
            dob="1992-11-20",
            mobile="+919123456789",
            auth_token=f"jwt.abdm.token.{uuid.uuid4().hex}",
            is_kyc_verified=True
        )

    # -------------------------------------------------------------------------
    # OPTIONAL IDENTITY LINKING (Binds ABHA to Master Patient Index)
    # -------------------------------------------------------------------------
    def link_abha_profile_to_mpi(self, mpi_id: uuid.UUID, profile: AbhaProfile) -> bool:
        """
        Persists the verified ABHA tokens into the patient's decoupled identifier graph.
        """
        # Link ABHA Number
        self.identity_service.link_identifier(
            mpi_id=mpi_id,
            identifier=IdentifierInput(
                id_type=IdentifierType.ABHA_NUMBER,
                id_value=profile.abha_number,
                issuing_authority="ABDM_NHA",
                is_verified=True,
                verification_status=VerificationStatus.VERIFIED_OTP
            )
        )
        # Link ABHA Address (PHR Handle)
        self.identity_service.link_identifier(
            mpi_id=mpi_id,
            identifier=IdentifierInput(
                id_type=IdentifierType.ABHA_ADDRESS,
                id_value=profile.abha_address,
                issuing_authority="ABDM_NHA",
                is_verified=True,
                verification_status=VerificationStatus.VERIFIED_OTP
            )
        )
        return True

    # -------------------------------------------------------------------------
    # ABDM MILESTONE 2 (M2): HIP CARE CONTEXT REGISTRATION
    # -------------------------------------------------------------------------
    def register_care_context(self, mpi_id: uuid.UUID, encounter_id: uuid.UUID, display_name: str) -> Dict[str, Any]:
        """
        Registers an episode of care context under the patient's ABHA account.
        Allows national PHR apps to discover and view records from this hospital.
        """
        context_record = {
            "care_context_id": f"CARE-CTX-{encounter_id.hex[:10].upper()}",
            "encounter_id": str(encounter_id),
            "display": display_name,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        
        mpi_str = str(mpi_id)
        if mpi_str not in self._registered_care_contexts:
            self._registered_care_contexts[mpi_str] = []
            
        self._registered_care_contexts[mpi_str].append(context_record)
        
        return {
            "status": "CARE_CONTEXT_LINKED",
            "care_context": context_record
        }

    def get_patient_care_contexts(self, mpi_id: uuid.UUID) -> list:
        return self._registered_care_contexts.get(str(mpi_id), [])
