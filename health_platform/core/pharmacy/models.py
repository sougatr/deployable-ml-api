"""
Pharmacy & e-Prescription Dispensing Domain Models.
Implements closed-loop pharmacy inventory, batch & FEFO expiry tracking,
registered pharmacist verification, and automated billing generation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field

class MedicineForm(str, Enum):
    TABLET = "TABLET"
    CAPSULE = "CAPSULE"
    SYRUP = "SYRUP"
    INJECTION = "INJECTION"
    OINTMENT = "OINTMENT"
    DROPS = "DROPS"
    INHALER = "INHALER"

class StockAlertLevel(str, Enum):
    HEALTHY = "HEALTHY"
    LOW_STOCK = "LOW_STOCK"
    CRITICAL_LOW = "CRITICAL_LOW"
    NEAR_EXPIRY = "NEAR_EXPIRY"
    EXPIRED = "EXPIRED"

class DispenseStatus(str, Enum):
    PENDING = "PENDING"
    DISPENSED = "DISPENSED"
    CANCELLED = "CANCELLED"

class BatchItem(BaseModel):
    batch_number: str
    expiry_date: str # YYYY-MM-DD
    mrp: float # Maximum Retail Price per unit
    unit_cost: float # Acquisition cost per unit
    quantity_available: int
    manufacturer: str

    @property
    def is_expired(self) -> bool:
        try:
            exp = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
            return exp < date.today()
        except Exception:
            return False

    @property
    def is_near_expiry(self) -> bool:
        try:
            exp = datetime.strptime(self.expiry_date, "%Y-%m-%d").date()
            days = (exp - date.today()).days
            return 0 <= days <= 90 # within 90 days
        except Exception:
            return False

class PharmacyCatalogItem(BaseModel):
    item_code: str
    brand_name: str
    generic_name: str
    form: MedicineForm
    strength: str
    reorder_level: int = 50
    batches: List[BatchItem] = Field(default_factory=list)

    @property
    def total_stock(self) -> int:
        return sum(b.quantity_available for b in self.batches)

    @property
    def alert_level(self) -> StockAlertLevel:
        total = self.total_stock
        has_expired = any(b.is_expired and b.quantity_available > 0 for b in self.batches)
        if has_expired:
            return StockAlertLevel.EXPIRED
        has_near_expiry = any(b.is_near_expiry and b.quantity_available > 0 for b in self.batches)
        if total <= 10:
            return StockAlertLevel.CRITICAL_LOW
        if total <= self.reorder_level:
            return StockAlertLevel.LOW_STOCK
        if has_near_expiry:
            return StockAlertLevel.NEAR_EXPIRY
        return StockAlertLevel.HEALTHY

class AddStockBatchInput(BaseModel):
    item_code: str
    batch_number: str
    expiry_date: str
    mrp: float
    unit_cost: float
    quantity: int
    manufacturer: str

class DispenseLineInput(BaseModel):
    item_code: str
    batch_number: str
    quantity_to_dispense: int

class DispenseRequestInput(BaseModel):
    mpi_id: uuid.UUID
    encounter_id: uuid.UUID
    prescription_id: Optional[uuid.UUID] = None
    pharmacist_name: str
    pharmacist_reg_no: str
    items: List[DispenseLineInput]
    patient_co_pay_ratio: float = 0.8 # Standard 80% patient, 20% insurer

class DispensedLineItem(BaseModel):
    item_code: str
    brand_name: str
    generic_name: str
    batch_number: str
    expiry_date: str
    unit_price: float
    quantity_dispensed: int
    total_price: float

class MedicationDispenseRecord(BaseModel):
    dispense_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    dispense_number: str
    mpi_id: uuid.UUID
    encounter_id: uuid.UUID
    prescription_id: Optional[uuid.UUID] = None
    patient_name: str
    patient_uhid: str
    dispensed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pharmacist_name: str
    pharmacist_reg_no: str
    lines: List[DispensedLineItem] = Field(default_factory=list)
    gross_total: float
    patient_share: float
    insurer_share: float
    charge_item_id: Optional[uuid.UUID] = None
    status: DispenseStatus = DispenseStatus.DISPENSED
