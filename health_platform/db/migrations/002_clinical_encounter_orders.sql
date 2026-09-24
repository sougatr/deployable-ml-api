-- ============================================================================
-- MIGRATION 002: CLINICAL ENCOUNTER, CONDITIONS, OBSERVATIONS & ORDERS SCHEMA
-- ============================================================================

-- 1. Facility & Department Master
CREATE TABLE IF NOT EXISTS facility_master (
    facility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    hfr_id VARCHAR(50), -- ABDM Health Facility Registry ID
    name VARCHAR(200) NOT NULL,
    classification VARCHAR(50) NOT NULL, -- CLINIC, GENERAL_HOSPITAL, TERTIARY
    address JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Practitioner Master
CREATE TABLE IF NOT EXISTS practitioner_master (
    practitioner_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hpr_id VARCHAR(50), -- ABDM Healthcare Professional Registry ID
    nmc_registration_number VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    specialty_code VARCHAR(50) NOT NULL, -- SNOMED-CT specialty
    specialty_display VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Encounter Table (Episode of Care Context)
CREATE TABLE IF NOT EXISTS encounter (
    encounter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    facility_id UUID NOT NULL REFERENCES facility_master(facility_id),
    attending_practitioner_id UUID NOT NULL REFERENCES practitioner_master(practitioner_id),
    class VARCHAR(30) NOT NULL, -- AMBULATORY, INPATIENT, EMERGENCY, VIRTUAL, HOME_HEALTH
    status VARCHAR(30) NOT NULL DEFAULT 'IN_PROGRESS', -- PLANNED, ARRIVED, TRIAGED, IN_PROGRESS, DISCHARGED, CANCELLED
    priority VARCHAR(20) NOT NULL DEFAULT 'ROUTINE', -- ROUTINE, URGENT, STAT
    period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_end TIMESTAMPTZ,
    admission_details JSONB, -- Room, Bed, Ward, Source
    discharge_details JSONB, -- Disposition, Summary Ref
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_encounter_mpi ON encounter(mpi_id);
CREATE INDEX IF NOT EXISTS idx_encounter_tenant ON encounter(tenant_id, status);

-- 4. Condition / Problem List
CREATE TABLE IF NOT EXISTS condition (
    condition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    clinical_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, RESOLVED
    verification_status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED', -- PROVISIONAL, DIFFERENTIAL, CONFIRMED
    code_snomed VARCHAR(50),
    code_icd10 VARCHAR(50) NOT NULL,
    display VARCHAR(255) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorder_id UUID NOT NULL REFERENCES practitioner_master(practitioner_id)
);

CREATE INDEX IF NOT EXISTS idx_condition_mpi ON condition(mpi_id);

-- 5. Observation & Vitals
CREATE TABLE IF NOT EXISTS observation (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    status VARCHAR(20) NOT NULL DEFAULT 'FINAL', -- PRELIMINARY, FINAL, AMENDED
    code_loinc VARCHAR(50) NOT NULL,
    display VARCHAR(255) NOT NULL,
    effective_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    value_quantity NUMERIC(10, 3),
    value_unit VARCHAR(30), -- UCUM unit (e.g. 'mm[Hg]', '%', 'mg/dL')
    value_string TEXT,
    reference_range_low NUMERIC(10, 3),
    reference_range_high NUMERIC(10, 3),
    interpretation VARCHAR(20) -- LOW, NORMAL, HIGH, CRITICAL_LOW, CRITICAL_HIGH
);

CREATE INDEX IF NOT EXISTS idx_observation_mpi_code ON observation(mpi_id, code_loinc);

-- 6. Service Requests (Clinical Diagnostic, Therapeutic & Procedural Orders)
CREATE TABLE IF NOT EXISTS service_request (
    service_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_group_id UUID NOT NULL,
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    category VARCHAR(30) NOT NULL, -- LABORATORY, RADIOLOGY, PROCEDURE, CONSULTATION
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', -- DRAFT, ACTIVE, ON_HOLD, COMPLETED, REVOKED
    intent VARCHAR(20) NOT NULL DEFAULT 'ORDER',
    priority VARCHAR(20) NOT NULL DEFAULT 'ROUTINE', -- ROUTINE, URGENT, STAT
    code VARCHAR(50) NOT NULL, -- LOINC or SNOMED
    display VARCHAR(255) NOT NULL,
    tariff_code VARCHAR(50) NOT NULL, -- Hospital Tariff Master Code
    estimated_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    requester_id UUID NOT NULL REFERENCES practitioner_master(practitioner_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_service_request_encounter ON service_request(encounter_id);
CREATE INDEX IF NOT EXISTS idx_service_request_mpi ON service_request(mpi_id);
