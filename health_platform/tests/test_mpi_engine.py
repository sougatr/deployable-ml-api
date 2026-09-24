import uuid
from datetime import date
from health_platform.core.identity.models import (
    PatientRegistrationRequest,
    IdentifierInput,
    IdentifierType,
    GenderEnum,
    FamilyLinkRequest,
    FamilyRelationshipType,
    MergeRequest
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.identity.mpi_engine import FellegiSunterMPIEngine
from health_platform.core.common.exceptions import DuplicateIdentityCandidateException

def test_patient_registration_and_uhid_generation():
    service = PatientIdentityService()
    req = PatientRegistrationRequest(
        first_name="Ramesh",
        last_name="Sharma",
        dob=date(1982, 5, 14),
        gender=GenderEnum.MALE,
        primary_phone="+919876543210",
        postal_code="560038"
    )
    res = service.resolve_or_create_patient(req)
    assert res.is_newly_created is True
    assert res.uhid.startswith("MED-")
    assert res.mpi_id is not None
    assert res.patient_record.first_name == "Ramesh"

def test_deterministic_match_via_abha():
    service = PatientIdentityService()
    # Register Patient 1 with ABHA
    req1 = PatientRegistrationRequest(
        first_name="Pooja",
        last_name="Verma",
        dob=date(1990, 8, 22),
        gender=GenderEnum.FEMALE,
        primary_phone="+919123456789",
        identifiers=[
            IdentifierInput(
                id_type=IdentifierType.ABHA_NUMBER,
                id_value="14-9912-3841-0012",
                is_verified=True
            )
        ]
    )
    res1 = service.resolve_or_create_patient(req1)

    # Presentation at another desk with different phone but matching verified ABHA
    req2 = PatientRegistrationRequest(
        first_name="Pooja",
        last_name="Verma",
        dob=date(1990, 8, 22),
        gender=GenderEnum.FEMALE,
        primary_phone="+919999988888", # Different phone
        identifiers=[
            IdentifierInput(
                id_type=IdentifierType.ABHA_NUMBER,
                id_value="14-9912-3841-0012",
                is_verified=True
            )
        ]
    )
    res2 = service.resolve_or_create_patient(req2)
    assert res2.is_newly_created is False
    assert res2.mpi_id == res1.mpi_id
    assert res2.uhid == res1.uhid

def test_probabilistic_duplicate_detection_and_transposition():
    service = PatientIdentityService()
    # Register existing patient: Rajesh Kumar, DOB 12-Apr-1985
    req1 = PatientRegistrationRequest(
        first_name="Rajesh",
        last_name="Kumar",
        dob=date(1985, 4, 12),
        gender=GenderEnum.MALE,
        primary_phone="+919876500000",
        postal_code="560001"
    )
    res1 = service.resolve_or_create_patient(req1)

    # Incoming candidate with transposed DOB (12/04 -> 04/12) and minor spelling variant
    req2 = PatientRegistrationRequest(
        first_name="Rajeshe", # Jaro-Winkler high match
        last_name="Kumar",
        dob=date(1985, 12, 4), # Transposed month and day!
        gender=GenderEnum.MALE,
        primary_phone="+919876500000",
        postal_code="560001"
    )

    duplicate_caught = False
    try:
        service.resolve_or_create_patient(req2)
    except DuplicateIdentityCandidateException as exc:
        duplicate_caught = True
        candidates = exc.candidate_matches
        assert len(candidates) == 1
        assert candidates[0]["mpi_id"] == str(res1.mpi_id)
        assert candidates[0]["confidence_score"] >= FellegiSunterMPIEngine.THRESHOLD_HIGH_CONFIDENCE

    assert duplicate_caught is True

def test_family_graph_multiple_profiles_one_phone():
    service = PatientIdentityService()
    # Parent
    parent_req = PatientRegistrationRequest(
        first_name="Amit",
        last_name="Patel",
        dob=date(1980, 2, 10),
        gender=GenderEnum.MALE,
        primary_phone="+919811122233"
    )
    parent_res = service.resolve_or_create_patient(parent_req)

    # Child sharing same phone, distinct demographics -> Allowed override for family creation
    child_req = PatientRegistrationRequest(
        first_name="Aarav",
        last_name="Patel",
        dob=date(2018, 9, 15),
        gender=GenderEnum.MALE,
        primary_phone="+919811122233"
    )
    child_res = service.resolve_or_create_patient(child_req, allow_duplicate_override=True)
    assert child_res.mpi_id != parent_res.mpi_id

    # Create Family Relationship edge
    family_link = FamilyLinkRequest(
        account_holder_phone="+919811122233",
        source_mpi_id=parent_res.mpi_id,
        target_mpi_id=child_res.mpi_id,
        relationship_type=FamilyRelationshipType.PARENT_OF,
        authorization_scope="FULL_ACCESS"
    )
    assert service.manage_family_link(family_link) is True

def test_merge_governance():
    service = PatientIdentityService()
    p1 = service.resolve_or_create_patient(PatientRegistrationRequest(
        first_name="Suresh", last_name="Menon", dob=date(1975, 1, 1),
        gender=GenderEnum.MALE, primary_phone="+919000011111"
    ))
    p2 = service.resolve_or_create_patient(PatientRegistrationRequest(
        first_name="Suresh", last_name="Menon", dob=date(1975, 1, 1),
        gender=GenderEnum.MALE, primary_phone="+919000022222"
    ), allow_duplicate_override=True)

    merge_res = service.execute_merge(MergeRequest(
        deprecated_mpi_id=p2.mpi_id,
        surviving_mpi_id=p1.mpi_id,
        merge_reason="Confirmed duplicate registrations across facilities",
        authorized_by_user_id=uuid.uuid4()
    ))
    assert merge_res["status"] == "MERGED"
    assert merge_res["surviving_mpi_id"] == p1.mpi_id
