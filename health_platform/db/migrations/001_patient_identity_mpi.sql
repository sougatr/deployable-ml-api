-- ============================================================================
-- MIGRATION 001: PATIENT IDENTITY & MASTER PATIENT INDEX (MPI) SCHEMA
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "fuzzystrmatch";

-- Multi-Tenant Context Helper Function (Row-Level Security)
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
$$ LANGUAGE SQL STABLE;

-- 1. Patient Master Table (Core Internal Identity)
CREATE TABLE IF NOT EXISTS patient_master (
    mpi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uhid VARCHAR(16) NOT NULL UNIQUE, -- Public Luhn-mod-36 human-readable display ID
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, MERGED, SUSPENDED, DECEASED
    merged_into_mpi_id UUID REFERENCES patient_master(mpi_id),
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    phonetic_first_name VARCHAR(10), -- Metaphone / Soundex
    phonetic_last_name VARCHAR(10),
    dob DATE NOT NULL,
    dob_is_estimated BOOLEAN NOT NULL DEFAULT FALSE,
    gender VARCHAR(10) NOT NULL, -- MALE, FEMALE, OTHER, UNKNOWN
    blood_group VARCHAR(5),
    primary_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_patient_phonetics ON patient_master(phonetic_first_name, gender);
CREATE INDEX IF NOT EXISTS idx_patient_dob ON patient_master(dob);
CREATE INDEX IF NOT EXISTS idx_patient_uhid ON patient_master(uhid);

-- 2. Decoupled Identifiers Table (Mobile, MRN, ABHA, National IDs)
CREATE TABLE IF NOT EXISTS patient_identifier (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id) ON DELETE CASCADE,
    id_type VARCHAR(30) NOT NULL, -- MOBILE, MRN, ABHA_NUMBER, ABHA_ADDRESS, AADHAAR_VAULT_TOKEN, PASSPORT, INS_MEMBER_ID
    id_value_hash VARCHAR(64) NOT NULL, -- SHA-256 for deterministic O(1) indexed lookups
    id_value_encrypted BYTEA NOT NULL, -- Encrypted raw value
    issuing_authority VARCHAR(100), -- E.g., 'ABDM', 'HOSPITAL_TENANT_BLR_01', 'UIDAI'
    facility_tenant_id UUID, -- Scoped if MRN; NULL if global platform identifier
    verification_status VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED', -- VERIFIED_OTP, VERIFIED_BIOMETRIC, MANUAL_VERIFIED, UNVERIFIED
    verified_at TIMESTAMPTZ,
    is_primary_contact BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_identifier_type_value_tenant UNIQUE (id_type, id_value_hash, facility_tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_identifier_hash ON patient_identifier(id_type, id_value_hash);
CREATE INDEX IF NOT EXISTS idx_identifier_mpi ON patient_identifier(mpi_id);

-- 3. Family & Custodial Graph Edges
CREATE TABLE IF NOT EXISTS patient_relationship (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_holder_phone VARCHAR(15) NOT NULL, -- Authenticated mobile number (E.164)
    source_mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id) ON DELETE CASCADE,
    target_mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL, -- SELF, PARENT_OF, CHILD_OF, SPOUSE_OF, LEGAL_GUARDIAN_OF, SIBLING_OF
    authorization_scope VARCHAR(50) NOT NULL DEFAULT 'FULL_ACCESS', -- FULL_ACCESS, EMERGENCY_ONLY, VIEW_ONLY
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_family_relationship UNIQUE (source_mpi_id, target_mpi_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_family_account_phone ON patient_relationship(account_holder_phone);

-- 4. MPI Merge & Split Audit Ledger (Append-Only)
CREATE TABLE IF NOT EXISTS mpi_merge_audit_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deprecated_mpi_id UUID NOT NULL,
    surviving_mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    merge_reason VARCHAR(100) NOT NULL,
    initiated_by_user_id UUID NOT NULL,
    approved_by_him_lead UUID NOT NULL,
    probabilistic_score NUMERIC(5,4),
    cryptographic_snapshot_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Potential Duplicate Review Worklist (HIM Department)
CREATE TABLE IF NOT EXISTS mpi_match_candidate (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    candidate_mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    composite_weight NUMERIC(6, 2) NOT NULL,
    matched_rules JSONB NOT NULL,
    review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, CONFIRMED_MERGE, DISMISSED_FALSE_POSITIVE
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_candidate_pair UNIQUE (source_mpi_id, candidate_mpi_id)
);
