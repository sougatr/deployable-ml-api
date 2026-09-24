import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from health_platform.core.common.models import Money
from health_platform.core.common.exceptions import UnanchoredChargeError, ImbalancedLedgerError

class ChargeItemModel(BaseModel):
    charge_item_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    encounter_id: uuid.UUID
    mpi_id: uuid.UUID
    status: str = "BILLABLE" # PLANNED, BILLABLE, BILLED, CANCELLED
    
    # Non-negotiable Clinical Origin Linkage
    originating_resource_type: str # ServiceRequest, MedicationDispense, Procedure, BedStay
    originating_resource_id: uuid.UUID
    
    tariff_code: str
    department_code: str
    quantity: float = 1.0
    unit_price: float
    gross_amount: float
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    net_amount: float
    
    # Multi-Payer Split
    patient_share: float
    insurer_share: float = 0.0
    coverage_id: Optional[uuid.UUID] = None
    
    posted_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_clinical_origin_and_split(self):
        if not self.originating_resource_id or not self.originating_resource_type:
            raise UnanchoredChargeError(
                "Violation of Clinical-Financial Invariant: Every charge item MUST maintain an immutable link to its originating clinical activity."
            )
        if round(self.patient_share + self.insurer_share, 2) != round(self.net_amount, 2):
            raise ValueError(
                f"Payer split mismatch: Patient share ({self.patient_share}) + Insurer share ({self.insurer_share}) != Net amount ({self.net_amount})"
            )
        return self

class LedgerLineItem(BaseModel):
    account_code: str # E.g. '1200-AR-PATIENT', '4001-REV-BIOCHEMISTRY'
    debit_amount: float = 0.0
    credit_amount: float = 0.0

    @model_validator(mode="after")
    def validate_amounts(self):
        if self.debit_amount < 0 or self.credit_amount < 0:
            raise ValueError("Ledger line amounts must be non-negative.")
        if (self.debit_amount > 0 and self.credit_amount > 0) or (self.debit_amount == 0 and self.credit_amount == 0):
            raise ValueError("Ledger line must be exclusively a debit OR a credit.")
        return self

class JournalEntry(BaseModel):
    journal_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    encounter_id: uuid.UUID
    entry_type: str # CHARGE_POSTED, PAYMENT_RECEIVED, ADJUSTMENT
    narration: str
    lines: List[LedgerLineItem]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_double_entry_balance(self):
        total_debits = round(sum(l.debit_amount for l in self.lines), 2)
        total_credits = round(sum(l.credit_amount for l in self.lines), 2)
        if total_debits != total_credits:
            raise ImbalancedLedgerError(
                f"Double-Entry Invariant Failure: Debits (₹{total_debits}) != Credits (₹{total_credits})"
            )
        return self
