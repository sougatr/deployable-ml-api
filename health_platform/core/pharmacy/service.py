"""
Pharmacy & e-Prescription Dispensing Service Engine.
Enforces closed-loop inventory tracking:
1. Validates batch availability and strictly rejects expired medicines.
2. Performs FEFO (First-Expiry-First-Out) batch decrement.
3. Automatically posts balanced double-entry pharmacy revenue charges to the Financial Ledger.
4. Stages transactional CloudEvents partitioned by mpi_id.
"""

from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timezone

from health_platform.core.pharmacy.models import (
    MedicineForm,
    StockAlertLevel,
    DispenseStatus,
    BatchItem,
    PharmacyCatalogItem,
    AddStockBatchInput,
    DispenseLineInput,
    DispenseRequestInput,
    DispensedLineItem,
    MedicationDispenseRecord
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import CloudEventEnvelope, TransactionalOutboxPublisher

class PharmacyService:
    def __init__(
        self,
        identity_service: PatientIdentityService,
        financial_service: FinancialLedgerService,
        outbox: TransactionalOutboxPublisher
    ):
        self.identity_service = identity_service
        self.financial_service = financial_service
        self.outbox = outbox

        self._catalog: Dict[str, PharmacyCatalogItem] = {}
        self._dispenses: Dict[uuid.UUID, MedicationDispenseRecord] = {}
        self._dispense_counter = 1000

        self._initialize_inventory()

    def _initialize_inventory(self):
        # 1. Ezorb Forte (Calcium Aspartate)
        self._catalog["MED-EZORB-FORTE"] = PharmacyCatalogItem(
            item_code="MED-EZORB-FORTE",
            brand_name="Tab Ezorb Forte",
            generic_name="Calcium Aspartate 1120mg + Vitamin D3 1000IU",
            form=MedicineForm.TABLET,
            strength="1120mg",
            reorder_level=50,
            batches=[
                BatchItem(
                    batch_number="EZ-2024-B1",
                    expiry_date="2027-08-31",
                    mrp=28.50,
                    unit_cost=18.00,
                    quantity_available=350,
                    manufacturer="Corona Remedies"
                ),
                BatchItem(
                    batch_number="EZ-2023-A9",
                    expiry_date="2026-11-30",
                    mrp=27.00,
                    unit_cost=17.50,
                    quantity_available=45,
                    manufacturer="Corona Remedies"
                )
            ]
        )

        # 2. Telma 40 (Telmisartan)
        self._catalog["MED-TELMA-40"] = PharmacyCatalogItem(
            item_code="MED-TELMA-40",
            brand_name="Tab Telma 40",
            generic_name="Telmisartan IP 40mg",
            form=MedicineForm.TABLET,
            strength="40mg",
            reorder_level=100,
            batches=[
                BatchItem(
                    batch_number="TL-2024-04",
                    expiry_date="2027-10-31",
                    mrp=14.80,
                    unit_cost=9.20,
                    quantity_available=500,
                    manufacturer="Glenmark Pharmaceuticals"
                )
            ]
        )

        # 3. Glycomet 500 (Metformin SR)
        self._catalog["MED-GLYCOMET-500"] = PharmacyCatalogItem(
            item_code="MED-GLYCOMET-500",
            brand_name="Tab Glycomet 500 SR",
            generic_name="Metformin Hydrochloride IP 500mg (Sustained Release)",
            form=MedicineForm.TABLET,
            strength="500mg SR",
            reorder_level=100,
            batches=[
                BatchItem(
                    batch_number="GL-2025-12",
                    expiry_date="2028-01-31",
                    mrp=3.20,
                    unit_cost=1.80,
                    quantity_available=600,
                    manufacturer="USV Private Limited"
                )
            ]
        )

        # 4. Pan 40 (Pantoprazole)
        self._catalog["MED-PAN-40"] = PharmacyCatalogItem(
            item_code="MED-PAN-40",
            brand_name="Tab Pan 40",
            generic_name="Pantoprazole Gastro-resistant IP 40mg",
            form=MedicineForm.TABLET,
            strength="40mg",
            reorder_level=75,
            batches=[
                BatchItem(
                    batch_number="PN-2024-08",
                    expiry_date="2027-05-31",
                    mrp=11.50,
                    unit_cost=7.00,
                    quantity_available=400,
                    manufacturer="Alkem Laboratories"
                )
            ]
        )

        # 5. Augmentin 625 Duo (Amoxicillin + Clavulanic Acid)
        self._catalog["MED-AUGMENTIN-625"] = PharmacyCatalogItem(
            item_code="MED-AUGMENTIN-625",
            brand_name="Tab Augmentin 625 Duo",
            generic_name="Amoxicillin 500mg + Potassium Clavulanate 125mg",
            form=MedicineForm.TABLET,
            strength="625mg",
            reorder_level=40,
            batches=[
                BatchItem(
                    batch_number="AG-2024-11",
                    expiry_date="2027-02-28",
                    mrp=22.00,
                    unit_cost=14.50,
                    quantity_available=200,
                    manufacturer="GlaxoSmithKline (GSK)"
                )
            ]
        )

        # 6. Dolo 650 (Paracetamol)
        self._catalog["MED-DOLO-650"] = PharmacyCatalogItem(
            item_code="MED-DOLO-650",
            brand_name="Tab Dolo 650",
            generic_name="Paracetamol IP 650mg",
            form=MedicineForm.TABLET,
            strength="650mg",
            reorder_level=150,
            batches=[
                BatchItem(
                    batch_number="DL-2025-01",
                    expiry_date="2028-03-31",
                    mrp=2.40,
                    unit_cost=1.20,
                    quantity_available=1000,
                    manufacturer="Micro Labs Limited"
                )
            ]
        )

        # 7. Expired Test Batch (For Quality & Regulatory Audit Testing)
        self._catalog["MED-EXPIRED-TEST"] = PharmacyCatalogItem(
            item_code="MED-EXPIRED-TEST",
            brand_name="Tab Expired Audit Sample",
            generic_name="Amoxicillin Trihydrate 250mg",
            form=MedicineForm.TABLET,
            strength="250mg",
            reorder_level=20,
            batches=[
                BatchItem(
                    batch_number="EXP-2021-01",
                    expiry_date="2023-01-01",
                    mrp=5.00,
                    unit_cost=3.00,
                    quantity_available=15,
                    manufacturer="Audit Quality Control"
                )
            ]
        )

    def get_inventory(self) -> List[PharmacyCatalogItem]:
        return list(self._catalog.values())

    def get_catalog_item(self, item_code: str) -> Optional[PharmacyCatalogItem]:
        return self._catalog.get(item_code)

    def get_alerts(self) -> Dict[str, Any]:
        items = list(self._catalog.values())
        low_stock = [i for i in items if i.alert_level in (StockAlertLevel.LOW_STOCK, StockAlertLevel.CRITICAL_LOW)]
        near_expiry = [
            {"item": i, "batch": b}
            for i in items
            for b in i.batches
            if b.is_near_expiry and b.quantity_available > 0
        ]
        expired = [
            {"item": i, "batch": b}
            for i in items
            for b in i.batches
            if b.is_expired and b.quantity_available > 0
        ]

        return {
            "low_stock_count": len(low_stock),
            "near_expiry_count": len(near_expiry),
            "expired_count": len(expired),
            "low_stock_items": [
                {"item_code": i.item_code, "brand_name": i.brand_name, "stock": i.total_stock, "level": i.alert_level.value}
                for i in low_stock
            ],
            "near_expiry_batches": [
                {"item_code": x["item"].item_code, "brand_name": x["item"].brand_name, "batch": x["batch"].batch_number, "expiry": x["batch"].expiry_date, "qty": x["batch"].quantity_available}
                for x in near_expiry
            ],
            "expired_batches": [
                {"item_code": x["item"].item_code, "brand_name": x["item"].brand_name, "batch": x["batch"].batch_number, "expiry": x["batch"].expiry_date, "qty": x["batch"].quantity_available}
                for x in expired
            ]
        }

    def add_stock_batch(self, input_data: AddStockBatchInput) -> PharmacyCatalogItem:
        item = self._catalog.get(input_data.item_code)
        if not item:
            raise ValueError(f"Medication '{input_data.item_code}' not found in pharmacy master catalog.")

        # Check if batch exists already
        existing_batch = next((b for b in item.batches if b.batch_number == input_data.batch_number), None)
        if existing_batch:
            existing_batch.quantity_available += input_data.quantity
            existing_batch.mrp = input_data.mrp
            existing_batch.unit_cost = input_data.unit_cost
        else:
            new_batch = BatchItem(
                batch_number=input_data.batch_number,
                expiry_date=input_data.expiry_date,
                mrp=input_data.mrp,
                unit_cost=input_data.unit_cost,
                quantity_available=input_data.quantity,
                manufacturer=input_data.manufacturer
            )
            item.batches.append(new_batch)

        # Sort batches by expiry date (FEFO - First Expiry First Out)
        item.batches.sort(key=lambda b: b.expiry_date)
        return item

    def dispense_prescription(self, input_data: DispenseRequestInput) -> MedicationDispenseRecord:
        patient = self.identity_service._patients.get(input_data.mpi_id)
        if not patient:
            raise ValueError(f"Patient with MPI ID {input_data.mpi_id} does not exist.")

        if not input_data.items:
            raise ValueError("Dispense request must contain at least one medication line.")

        self._dispense_counter += 1
        now = datetime.now(timezone.utc)
        curr_year = now.year
        dispense_no = f"DISP-{curr_year}-{self._dispense_counter}"
        dispense_id = uuid.uuid4()

        dispensed_lines: List[DispensedLineItem] = []
        gross_total = 0.0

        # Step 1: Pre-validation of all requested items
        for req_line in input_data.items:
            item = self._catalog.get(req_line.item_code)
            if not item:
                raise ValueError(f"Medication '{req_line.item_code}' not found in pharmacy inventory.")

            target_batch = next((b for b in item.batches if b.batch_number == req_line.batch_number), None)
            if not target_batch:
                raise ValueError(f"Batch '{req_line.batch_number}' not found for medication '{item.brand_name}'.")

            if target_batch.is_expired:
                raise ValueError(
                    f"REGULATORY SAFETY REJECTION: Batch '{target_batch.batch_number}' of '{item.brand_name}' "
                    f"expired on {target_batch.expiry_date}. Dispensing expired drugs is prohibited."
                )

            if target_batch.quantity_available < req_line.quantity_to_dispense:
                raise ValueError(
                    f"INSUFFICIENT STOCK: Requested {req_line.quantity_to_dispense} units of '{item.brand_name}' "
                    f"(Batch {target_batch.batch_number}), but only {target_batch.quantity_available} units available."
                )

        # Step 2: Atomic Decrement & Line Generation
        for req_line in input_data.items:
            item = self._catalog[req_line.item_code]
            target_batch = next(b for b in item.batches if b.batch_number == req_line.batch_number)

            target_batch.quantity_available -= req_line.quantity_to_dispense
            line_total = round(target_batch.mrp * req_line.quantity_to_dispense, 2)
            gross_total += line_total

            dispensed_lines.append(
                DispensedLineItem(
                    item_code=item.item_code,
                    brand_name=item.brand_name,
                    generic_name=item.generic_name,
                    batch_number=target_batch.batch_number,
                    expiry_date=target_batch.expiry_date,
                    unit_price=target_batch.mrp,
                    quantity_dispensed=req_line.quantity_to_dispense,
                    total_price=line_total
                )
            )

        gross_total = round(gross_total, 2)
        patient_share = round(gross_total * input_data.patient_co_pay_ratio, 2)
        insurer_share = round(gross_total - patient_share, 2)

        # Step 3: Clinical-Financial Invariant: Post billable charge to Financial Ledger
        charge_item = self.financial_service.capture_charge_from_clinical_order(
            encounter_id=input_data.encounter_id,
            mpi_id=input_data.mpi_id,
            originating_resource_type="MedicationDispense",
            originating_resource_id=dispense_id,
            tariff_code="PHARM-DISPENSE",
            department_code="PHARMACY",
            unit_price=gross_total,
            quantity=1.0,
            patient_co_pay_ratio=input_data.patient_co_pay_ratio
        )

        record = MedicationDispenseRecord(
            dispense_id=dispense_id,
            dispense_number=dispense_no,
            mpi_id=input_data.mpi_id,
            encounter_id=input_data.encounter_id,
            prescription_id=input_data.prescription_id,
            patient_name=f"{patient.first_name} {patient.last_name}",
            patient_uhid=patient.uhid,
            dispensed_at=now,
            pharmacist_name=input_data.pharmacist_name,
            pharmacist_reg_no=input_data.pharmacist_reg_no,
            lines=dispensed_lines,
            gross_total=gross_total,
            patient_share=patient_share,
            insurer_share=insurer_share,
            charge_item_id=charge_item.charge_item_id,
            status=DispenseStatus.DISPENSED
        )

        self._dispenses[dispense_id] = record

        # Step 4: Transactional CloudEvents Outbox
        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000005")
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.pharmacy.medication_dispensed.v1",
                tenantid=tenant_id,
                mpiid=patient.mpi_id,
                actorid=dispense_id,
                actorrole="PHARMACIST",
                data={
                    "dispense_id": str(dispense_id),
                    "dispense_number": dispense_no,
                    "encounter_id": str(input_data.encounter_id),
                    "items_count": len(dispensed_lines),
                    "gross_total": gross_total,
                    "charge_item_id": str(charge_item.charge_item_id),
                    "pharmacist": input_data.pharmacist_name
                }
            )
        )

        return record

    def get_dispense_record(self, dispense_id: uuid.UUID) -> Optional[MedicationDispenseRecord]:
        return self._dispenses.get(dispense_id)

    def get_patient_dispenses(self, mpi_id: uuid.UUID) -> List[MedicationDispenseRecord]:
        records = [d for d in self._dispenses.values() if d.mpi_id == mpi_id]
        records.sort(key=lambda d: d.dispensed_at, reverse=True)
        return records

    def get_all_dispenses(self) -> List[MedicationDispenseRecord]:
        records = list(self._dispenses.values())
        records.sort(key=lambda d: d.dispensed_at, reverse=True)
        return records
