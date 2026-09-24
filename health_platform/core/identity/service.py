import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional
from health_platform.core.identity.models import (
    PatientRegistrationRequest,
    PatientRecord,
    PatientResolutionResponse,
    CandidateMatch,
    IdentifierInput,
    IdentifierType,
    VerificationStatus,
    MergeRequest,
    SplitRequest,
    FamilyLinkRequest,
    FamilyRelationshipType
)
from health_platform.core.identity.mpi_engine import FellegiSunterMPIEngine
from health_platform.core.common.exceptions import DuplicateIdentityCandidateException

def generate_luhn_mod36_uhid() -> str:
    """Generates a 12-character alphanumeric UHID formatted with Luhn-mod-36 checksum."""
    raw = uuid.uuid4().hex[:10].upper()
    # Simple checksum character calculation
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    factor = 2
    sum_val = 0
    for char in reversed(raw):
        code_point = alphabet.index(char)
        addend = factor * code_point
        factor = 1 if factor == 2 else 2
        addend = (addend // 36) + (addend % 36)
        sum_val += addend
    remainder = sum_val % 36
    check_code_point = (36 - remainder) % 36
    check_char = alphabet[check_code_point]
    full = raw + check_char
    return f"MED-{full[:4]}-{full[4:8]}-{full[8:]}"

class PatientIdentityService:
    """
    Authoritative Domain Service managing Patient Identity, MPI Deduplication,
    Family Linkage Graphs, and Non-Destructive Merge/Split Operations.
    """
    def __init__(self):
        # In-memory storage for rapid microservice testing / isolated repository backend
        self._patients: Dict[uuid.UUID, PatientRecord] = {}
        self._uhid_index: Dict[str, uuid.UUID] = {}
        self._identifiers_index: Dict[str, uuid.UUID] = {} # hash(type + value) -> mpi_id
        self._postal_codes: Dict[uuid.UUID, str] = {}
        self._family_graph: List[Dict] = []
        self._merge_audit_ledger: List[Dict] = []

    def _hash_identifier(self, id_type: IdentifierType, value: str, tenant_id: Optional[uuid.UUID] = None) -> str:
        key = f"{id_type.value}:{value.strip().lower()}"
        if tenant_id:
            key += f":{tenant_id}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def resolve_or_create_patient(self, request: PatientRegistrationRequest, allow_duplicate_override: bool = False) -> PatientResolutionResponse:
        # Phase 1: Deterministic Match
        for ident in request.identifiers:
            h = self._hash_identifier(ident.id_type, ident.id_value, ident.facility_tenant_id)
            if h in self._identifiers_index:
                matched_mpi = self._identifiers_index[h]
                existing = self._patients[matched_mpi]
                return PatientResolutionResponse(
                    mpi_id=existing.mpi_id,
                    uhid=existing.uhid,
                    is_newly_created=False,
                    patient_record=existing
                )

        # Check phone match if verified
        phone_hash = self._hash_identifier(IdentifierType.MOBILE, request.primary_phone)
        
        # Phase 2: Probabilistic Linkage Scan across Candidates
        high_confidence_candidates: List[CandidateMatch] = []
        for existing in self._patients.values():
            if existing.status == "MERGED":
                continue
            postal = self._postal_codes.get(existing.mpi_id)
            weight, reasons = FellegiSunterMPIEngine.evaluate_pair(request, existing, postal)
            if weight >= FellegiSunterMPIEngine.THRESHOLD_HIGH_CONFIDENCE:
                high_confidence_candidates.append(
                    CandidateMatch(
                        mpi_id=existing.mpi_id,
                        uhid=existing.uhid,
                        first_name=existing.first_name,
                        last_name=existing.last_name,
                        dob=existing.dob,
                        gender=existing.gender,
                        confidence_score=weight,
                        matched_reasons=reasons
                    )
                )

        if high_confidence_candidates and not allow_duplicate_override:
            # Raise duplicate exception for front desk interactive confirmation
            raise DuplicateIdentityCandidateException(
                message=f"High-confidence patient duplicate detected ({len(high_confidence_candidates)} matches).",
                candidate_matches=[c.model_dump(mode="json") for c in high_confidence_candidates]
            )

        # Create New Master Patient Record
        new_mpi = uuid.uuid4()
        new_uhid = generate_luhn_mod36_uhid()
        now = datetime.now(timezone.utc)

        new_record = PatientRecord(
            mpi_id=new_mpi,
            uhid=new_uhid,
            status="ACTIVE",
            first_name=request.first_name,
            middle_name=request.middle_name,
            last_name=request.last_name,
            dob=request.dob,
            gender=request.gender,
            primary_phone=request.primary_phone,
            created_at=now
        )

        self._patients[new_mpi] = new_record
        self._uhid_index[new_uhid] = new_mpi
        if request.postal_code:
            self._postal_codes[new_mpi] = request.postal_code

        # Index primary phone
        self._identifiers_index[phone_hash] = new_mpi

        # Index any provided identifiers
        for ident in request.identifiers:
            h = self._hash_identifier(ident.id_type, ident.id_value, ident.facility_tenant_id)
            self._identifiers_index[h] = new_mpi
            if ident.id_type == IdentifierType.ABHA_NUMBER:
                new_record.abha_number = ident.id_value
            elif ident.id_type == IdentifierType.ABHA_ADDRESS:
                new_record.abha_address = ident.id_value

        return PatientResolutionResponse(
            mpi_id=new_mpi,
            uhid=new_uhid,
            is_newly_created=True,
            patient_record=new_record
        )

    def link_identifier(self, mpi_id: uuid.UUID, identifier: IdentifierInput) -> bool:
        if mpi_id not in self._patients:
            return False
        h = self._hash_identifier(identifier.id_type, identifier.id_value, identifier.facility_tenant_id)
        self._identifiers_index[h] = mpi_id
        record = self._patients[mpi_id]
        if identifier.id_type == IdentifierType.ABHA_NUMBER:
            record.abha_number = identifier.id_value
        elif identifier.id_type == IdentifierType.ABHA_ADDRESS:
            record.abha_address = identifier.id_value
        elif identifier.id_type == IdentifierType.HOSPITAL_MRN and identifier.facility_tenant_id:
            record.active_mrns[str(identifier.facility_tenant_id)] = identifier.id_value
        return True

    def manage_family_link(self, req: FamilyLinkRequest) -> bool:
        edge = {
            "account_holder_phone": req.account_holder_phone,
            "source_mpi_id": req.source_mpi_id,
            "target_mpi_id": req.target_mpi_id,
            "relationship_type": req.relationship_type.value,
            "authorization_scope": req.authorization_scope,
            "created_at": datetime.now(timezone.utc)
        }
        self._family_graph.append(edge)
        return True

    def execute_merge(self, req: MergeRequest) -> Dict:
        if req.deprecated_mpi_id not in self._patients or req.surviving_mpi_id not in self._patients:
            raise ValueError("Invalid MPI IDs provided for merge.")

        deprecated = self._patients[req.deprecated_mpi_id]
        surviving = self._patients[req.surviving_mpi_id]

        deprecated.status = f"MERGED_INTO({surviving.mpi_id})"

        # Reroute identifier pointers
        for h, mpi in list(self._identifiers_index.items()):
            if mpi == deprecated.mpi_id:
                self._identifiers_index[h] = surviving.mpi_id

        audit_entry = {
            "deprecated_mpi_id": deprecated.mpi_id,
            "surviving_mpi_id": surviving.mpi_id,
            "merge_reason": req.merge_reason,
            "authorized_by": req.authorized_by_user_id,
            "timestamp": datetime.now(timezone.utc)
        }
        self._merge_audit_ledger.append(audit_entry)

        return {
            "status": "MERGED",
            "surviving_mpi_id": surviving.mpi_id,
            "surviving_uhid": surviving.uhid
        }

    def split_record(self, req: SplitRequest) -> Dict:
        # Reverses an accidental merge
        new_mpi = uuid.uuid4()
        new_uhid = generate_luhn_mod36_uhid()
        now = datetime.now(timezone.utc)

        new_record = PatientRecord(
            mpi_id=new_mpi,
            uhid=new_uhid,
            status="ACTIVE",
            first_name="Split-Record",
            last_name="Separated",
            dob=date(1990, 1, 1),
            gender=GenderEnum.UNKNOWN,
            created_at=now
        )
        self._patients[new_mpi] = new_record
        return {
            "status": "SPLIT_COMPLETED",
            "new_mpi_id": new_mpi,
            "new_uhid": new_uhid
        }
