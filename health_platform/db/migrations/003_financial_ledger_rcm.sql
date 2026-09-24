-- ============================================================================
-- MIGRATION 003: FINANCIAL LEDGER, RCM, AND CLINICAL-FINANCIAL INVARIANT
-- ============================================================================

-- 1. Hospital Tariff Master
CREATE TABLE IF NOT EXISTS tariff_master (
    tariff_code VARCHAR(50) PRIMARY KEY,
    category VARCHAR(50) NOT NULL, -- CONSULTATION, INVESTIGATION_LAB, INVESTIGATION_RAD, BED, PHARMACY, OT
    description VARCHAR(255) NOT NULL,
    base_price NUMERIC(12, 2) NOT NULL,
    hsn_sac_code VARCHAR(20),
    gst_rate_percent NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Charge Item Table (THE CLINICAL-FINANCIAL INVARIANT ENFORCER)
-- Every row MUST link to an originating clinical entity.
CREATE TABLE IF NOT EXISTS charge_item (
    charge_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    status VARCHAR(20) NOT NULL DEFAULT 'BILLABLE', -- PLANNED, BILLABLE, BILLED, CANCELLED
    
    -- Immutable Clinical Origin Linkage
    originating_resource_type VARCHAR(50) NOT NULL, -- ServiceRequest, MedicationDispense, Procedure, BedStay
    originating_resource_id UUID NOT NULL,
    
    tariff_code VARCHAR(50) NOT NULL REFERENCES tariff_master(tariff_code),
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1.00,
    unit_price NUMERIC(12, 2) NOT NULL,
    gross_amount NUMERIC(12, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    net_amount NUMERIC(12, 2) NOT NULL,
    
    -- Multi-Payer Split
    patient_share NUMERIC(12, 2) NOT NULL,
    insurer_share NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    coverage_id UUID,
    
    service_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Invariant constraints
    CONSTRAINT chk_positive_net_amount CHECK (net_amount >= 0),
    CONSTRAINT chk_payer_split_balance CHECK (ROUND(patient_share + insurer_share, 2) = ROUND(net_amount, 2))
);

CREATE INDEX IF NOT EXISTS idx_charge_item_encounter ON charge_item(encounter_id);
CREATE INDEX IF NOT EXISTS idx_charge_item_origin ON charge_item(originating_resource_type, originating_resource_id);

-- 3. Double-Entry Accounting: Journal Headers
CREATE TABLE IF NOT EXISTS financial_ledger_journal (
    journal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    entry_type VARCHAR(30) NOT NULL, -- CHARGE_POSTED, PAYMENT_RECEIVED, DISCOUNT_APPLIED, WRITE_OFF
    narration TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Double-Entry Accounting: Balanced Journal Lines
CREATE TABLE IF NOT EXISTS financial_ledger_entry (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES financial_ledger_journal(journal_id) ON DELETE CASCADE,
    account_code VARCHAR(50) NOT NULL, -- '1200-AR-PATIENT', '1201-AR-INSURER', '4001-REV-OPD', '1001-CASH'
    debit_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    credit_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    
    CONSTRAINT chk_entry_positive_amounts CHECK (debit_amount >= 0 AND credit_amount >= 0),
    CONSTRAINT chk_entry_exclusive_amounts CHECK ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
);

CREATE INDEX IF NOT EXISTS idx_ledger_entry_journal ON financial_ledger_entry(journal_id);
CREATE INDEX IF NOT EXISTS idx_ledger_entry_account ON financial_ledger_entry(account_code);

-- 5. Invoices Table
CREATE TABLE IF NOT EXISTS invoice (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) NOT NULL UNIQUE, -- E.g. INV-2026-BLR-001092
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    status VARCHAR(20) NOT NULL DEFAULT 'ISSUED', -- DRAFT, ISSUED, PAID, CANCELLED
    gross_total NUMERIC(12, 2) NOT NULL,
    discount_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    net_payable NUMERIC(12, 2) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Payments Table
CREATE TABLE IF NOT EXISTS payment_receipt (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number VARCHAR(50) NOT NULL UNIQUE,
    invoice_id UUID NOT NULL REFERENCES invoice(invoice_id),
    encounter_id UUID NOT NULL REFERENCES encounter(encounter_id),
    mpi_id UUID NOT NULL REFERENCES patient_master(mpi_id),
    amount NUMERIC(12, 2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL, -- CASH, UPI, CARD, NETBANKING, INSURER_DIRECT
    gateway_transaction_ref VARCHAR(100),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Transactional Outbox Table (Zero Dual-Write Failure Guarantee)
CREATE TABLE IF NOT EXISTS outbox_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(50) NOT NULL, -- IDENTITY, ENCOUNTER, ORDER, FINANCIAL, CLAIMS
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    partition_key VARCHAR(100) NOT NULL, -- Deterministic mpi_id
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, PUBLISHED, FAILED
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending ON outbox_event(status, created_at) WHERE status = 'PENDING';
