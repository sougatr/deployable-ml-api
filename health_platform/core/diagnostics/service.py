"""
Diagnostic Laboratory & Radiology Information System (LIS/RIS) Service Engine.
Enforces the Clinical-Financial Invariant: Every diagnostic order is an originating
clinical resource posting charges to the double-entry Financial Ledger with zero discrepancy.
"""

from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timezone
import random

from health_platform.core.diagnostics.models import (
    DiagnosticCategory,
    DiagnosticModality,
    SpecimenType,
    DiagnosticStatus,
    AbnormalFlag,
    LabParameterDefinition,
    DiagnosticCatalogItem,
    LabParameterResult,
    DiagnosticOrderInput,
    SpecimenCollectionInput,
    LabResultEntryInput,
    RadiologyReportEntryInput,
    VerificationInput,
    DiagnosticOrder
)
from health_platform.core.identity.service import PatientIdentityService
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.events.envelope import CloudEventEnvelope, TransactionalOutboxPublisher

class DiagnosticsService:
    def __init__(
        self,
        identity_service: PatientIdentityService,
        financial_service: FinancialLedgerService,
        outbox: TransactionalOutboxPublisher
    ):
        self.identity_service = identity_service
        self.financial_service = financial_service
        self.outbox = outbox

        self._catalog: Dict[str, DiagnosticCatalogItem] = {}
        self._orders: Dict[uuid.UUID, DiagnosticOrder] = {}
        self._sample_counter = 1000
        self._accession_counter = 5000

        self._initialize_catalog()

    def _initialize_catalog(self):
        # 1. Glycated Hemoglobin (HbA1c)
        self._catalog["LAB-BIO-042"] = DiagnosticCatalogItem(
            item_code="LAB-BIO-042",
            item_name="HbA1c Glycated Hemoglobin Panel",
            category=DiagnosticCategory.LABORATORY,
            modality=DiagnosticModality.BIOCHEMISTRY,
            standard_code="4548-4",
            standard_coding_system="http://loinc.org",
            specimen_type=SpecimenType.WHOLE_BLOOD_EDTA,
            standard_turnaround_hrs=2,
            base_tariff=650.0,
            parameters=[
                LabParameterDefinition(
                    parameter_code="HBA1C",
                    parameter_name="HbA1c (Glycated Hemoglobin)",
                    loinc_code="4548-4",
                    unit="%",
                    reference_low=4.0,
                    reference_high=5.6,
                    critical_high=10.0
                ),
                LabParameterDefinition(
                    parameter_code="EAG",
                    parameter_name="Estimated Average Glucose (eAG)",
                    loinc_code="27353-2",
                    unit="mg/dL",
                    reference_low=70.0,
                    reference_high=114.0,
                    critical_high=240.0
                )
            ]
        )

        # 2. Complete Blood Count (CBC)
        self._catalog["LAB-HEM-001"] = DiagnosticCatalogItem(
            item_code="LAB-HEM-001",
            item_name="Complete Blood Count with Differential (CBC)",
            category=DiagnosticCategory.LABORATORY,
            modality=DiagnosticModality.HEMATOLOGY,
            standard_code="58410-2",
            standard_coding_system="http://loinc.org",
            specimen_type=SpecimenType.WHOLE_BLOOD_EDTA,
            standard_turnaround_hrs=2,
            base_tariff=450.0,
            parameters=[
                LabParameterDefinition(
                    parameter_code="HB",
                    parameter_name="Hemoglobin",
                    loinc_code="718-7",
                    unit="g/dL",
                    reference_low=12.0,
                    reference_high=16.0,
                    critical_low=7.0,
                    critical_high=20.0
                ),
                LabParameterDefinition(
                    parameter_code="TLC",
                    parameter_name="Total Leukocyte Count (WBC)",
                    loinc_code="6690-2",
                    unit="cells/mcL",
                    reference_low=4000.0,
                    reference_high=11000.0,
                    critical_low=2000.0,
                    critical_high=30000.0
                ),
                LabParameterDefinition(
                    parameter_code="PLT",
                    parameter_name="Platelet Count",
                    loinc_code="777-3",
                    unit="x10^3/mcL",
                    reference_low=150.0,
                    reference_high=450.0,
                    critical_low=50.0
                ),
                LabParameterDefinition(
                    parameter_code="PCV",
                    parameter_name="Packed Cell Volume (Hematocrit)",
                    loinc_code="4544-3",
                    unit="%",
                    reference_low=36.0,
                    reference_high=48.0,
                    critical_low=20.0
                )
            ]
        )

        # 3. Renal Function Test (RFT)
        self._catalog["LAB-BIO-010"] = DiagnosticCatalogItem(
            item_code="LAB-BIO-010",
            item_name="Renal Function Test / Kidney Panel (RFT)",
            category=DiagnosticCategory.LABORATORY,
            modality=DiagnosticModality.BIOCHEMISTRY,
            standard_code="24362-6",
            standard_coding_system="http://loinc.org",
            specimen_type=SpecimenType.SERUM_PLAIN,
            standard_turnaround_hrs=3,
            base_tariff=750.0,
            parameters=[
                LabParameterDefinition(
                    parameter_code="CREAT",
                    parameter_name="Serum Creatinine",
                    loinc_code="2160-0",
                    unit="mg/dL",
                    reference_low=0.6,
                    reference_high=1.2,
                    critical_high=3.5
                ),
                LabParameterDefinition(
                    parameter_code="BUN",
                    parameter_name="Blood Urea Nitrogen",
                    loinc_code="3094-0",
                    unit="mg/dL",
                    reference_low=7.0,
                    reference_high=20.0,
                    critical_high=60.0
                ),
                LabParameterDefinition(
                    parameter_code="NA",
                    parameter_name="Serum Sodium",
                    loinc_code="2951-2",
                    unit="mEq/L",
                    reference_low=135.0,
                    reference_high=145.0,
                    critical_low=120.0,
                    critical_high=160.0
                ),
                LabParameterDefinition(
                    parameter_code="K",
                    parameter_name="Serum Potassium",
                    loinc_code="2823-3",
                    unit="mEq/L",
                    reference_low=3.5,
                    reference_high=5.0,
                    critical_low=2.8,
                    critical_high=6.2
                )
            ]
        )

        # 4. Standard Chest X-Ray PA View (Radiology)
        self._catalog["RAD-XRAY-001"] = DiagnosticCatalogItem(
            item_code="RAD-XRAY-001",
            item_name="Chest X-Ray Posteroanterior (PA) View",
            category=DiagnosticCategory.RADIOLOGY,
            modality=DiagnosticModality.XRAY,
            standard_code="168731009",
            standard_coding_system="http://snomed.info/sct",
            specimen_type=SpecimenType.NOT_APPLICABLE,
            standard_turnaround_hrs=1,
            base_tariff=850.0,
            parameters=[]
        )

        # 5. MRI Knee Joint Right (Radiology)
        self._catalog["RAD-MRI-002"] = DiagnosticCatalogItem(
            item_code="RAD-MRI-002",
            item_name="MRI Right Knee Joint with 3D Reconstruction",
            category=DiagnosticCategory.RADIOLOGY,
            modality=DiagnosticModality.MRI,
            standard_code="241042008",
            standard_coding_system="http://snomed.info/sct",
            specimen_type=SpecimenType.NOT_APPLICABLE,
            standard_turnaround_hrs=4,
            base_tariff=6500.0,
            parameters=[]
        )

        # 6. Ultrasound Whole Abdomen (Radiology)
        self._catalog["RAD-USG-001"] = DiagnosticCatalogItem(
            item_code="RAD-USG-001",
            item_name="Ultrasound Whole Abdomen & Pelvis",
            category=DiagnosticCategory.RADIOLOGY,
            modality=DiagnosticModality.ULTRASOUND,
            standard_code="241058004",
            standard_coding_system="http://snomed.info/sct",
            specimen_type=SpecimenType.NOT_APPLICABLE,
            standard_turnaround_hrs=2,
            base_tariff=1400.0,
            parameters=[]
        )

    def get_catalog(self) -> List[DiagnosticCatalogItem]:
        return list(self._catalog.values())

    def get_catalog_item(self, item_code: str) -> Optional[DiagnosticCatalogItem]:
        return self._catalog.get(item_code)

    def create_order(self, input_data: DiagnosticOrderInput) -> DiagnosticOrder:
        catalog_item = self.get_catalog_item(input_data.item_code)
        if not catalog_item:
            raise ValueError(f"Diagnostic catalog item '{input_data.item_code}' not found.")

        patient = self.identity_service._patients.get(input_data.mpi_id)
        if not patient:
            raise ValueError(f"Patient with MPI ID {input_data.mpi_id} does not exist.")

        order_id = uuid.uuid4()

        # Enforce Clinical-Financial Invariant:
        # Create an originating financial charge item for this diagnostic investigation
        dept = "LABORATORY" if catalog_item.category == DiagnosticCategory.LABORATORY else "RADIOLOGY"
        charge_item = self.financial_service.capture_charge_from_clinical_order(
            encounter_id=input_data.encounter_id,
            mpi_id=input_data.mpi_id,
            originating_resource_type="ServiceRequest",
            originating_resource_id=order_id,
            tariff_code=catalog_item.item_code,
            department_code=dept,
            unit_price=catalog_item.base_tariff,
            quantity=1.0,
            patient_co_pay_ratio=0.8
        )

        order = DiagnosticOrder(
            order_id=order_id,
            mpi_id=input_data.mpi_id,
            encounter_id=input_data.encounter_id,
            item_code=catalog_item.item_code,
            item_name=catalog_item.item_name,
            category=catalog_item.category,
            modality=catalog_item.modality,
            standard_code=catalog_item.standard_code,
            standard_coding_system=catalog_item.standard_coding_system,
            tariff_amount=catalog_item.base_tariff,
            ordering_doctor_name=input_data.ordering_doctor_name,
            clinical_history=input_data.clinical_history or "Routine investigation",
            is_stat=input_data.is_stat,
            status=DiagnosticStatus.ORDERED,
            specimen_type=catalog_item.specimen_type,
            charge_item_id=charge_item.charge_item_id
        )

        self._orders[order_id] = order

        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000004")
        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.diagnostics.order_created.v1",
                tenantid=tenant_id,
                mpiid=patient.mpi_id,
                actorid=input_data.encounter_id,
                actorrole="DOCTOR",
                data={
                    "order_id": str(order_id),
                    "item_code": catalog_item.item_code,
                    "item_name": catalog_item.item_name,
                    "category": catalog_item.category.value,
                    "modality": catalog_item.modality.value,
                    "standard_code": catalog_item.standard_code,
                    "tariff": catalog_item.base_tariff,
                    "charge_item_id": str(charge_item.charge_item_id)
                }
            )
        )

        return order

    def collect_specimen(self, input_data: SpecimenCollectionInput) -> DiagnosticOrder:
        order = self._orders.get(input_data.order_id)
        if not order:
            raise ValueError(f"Diagnostic order {input_data.order_id} not found.")

        if order.status not in (DiagnosticStatus.ORDERED, DiagnosticStatus.ANALYSIS_IN_PROGRESS):
            raise ValueError(f"Cannot collect specimen for order with status '{order.status}'.")

        self._sample_counter += 1
        self._accession_counter += 1
        now = datetime.now(timezone.utc)
        curr_year = now.year

        mod_code = order.modality.value[:3].upper()
        sample_barcode = f"SMP-{mod_code}-{curr_year}-{self._sample_counter}"
        accession_no = f"ACC-{curr_year}-{self._accession_counter}"

        order.sample_barcode = sample_barcode
        order.accession_number = accession_no
        order.collected_at = now
        order.collected_by = input_data.phlebotomist_name
        order.status = DiagnosticStatus.SAMPLE_COLLECTED

        patient = self.identity_service._patients.get(order.mpi_id)
        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000004")

        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.diagnostics.specimen_collected.v1",
                tenantid=tenant_id,
                mpiid=order.mpi_id,
                actorid=order.order_id,
                actorrole="PHLEBOTOMIST",
                data={
                    "order_id": str(order.order_id),
                    "sample_barcode": sample_barcode,
                    "accession_number": accession_no,
                    "specimen_type": order.specimen_type.value,
                    "collected_by": input_data.phlebotomist_name
                }
            )
        )

        return order

    def enter_lab_results(self, input_data: LabResultEntryInput) -> DiagnosticOrder:
        order = self._orders.get(input_data.order_id)
        if not order:
            raise ValueError(f"Diagnostic order {input_data.order_id} not found.")

        catalog_item = self.get_catalog_item(order.item_code)
        if not catalog_item:
            raise ValueError(f"Catalog item {order.item_code} missing.")

        param_defs = {p.parameter_code: p for p in catalog_item.parameters}
        results: List[LabParameterResult] = []

        for p_code, val in input_data.parameter_results.items():
            p_def = param_defs.get(p_code)
            if not p_def:
                continue

            flag = AbnormalFlag.NORMAL
            ref_display = f"{p_def.reference_low} - {p_def.reference_high} {p_def.unit}"

            if p_def.critical_high is not None and val >= p_def.critical_high:
                flag = AbnormalFlag.CRITICAL_HIGH
            elif p_def.critical_low is not None and val <= p_def.critical_low:
                flag = AbnormalFlag.CRITICAL_LOW
            elif p_def.reference_high is not None and val > p_def.reference_high:
                flag = AbnormalFlag.HIGH
            elif p_def.reference_low is not None and val < p_def.reference_low:
                flag = AbnormalFlag.LOW

            results.append(
                LabParameterResult(
                    parameter_code=p_def.parameter_code,
                    parameter_name=p_def.parameter_name,
                    loinc_code=p_def.loinc_code,
                    measured_value=f"{val:.2f}" if isinstance(val, float) else str(val),
                    unit=p_def.unit,
                    reference_range_display=ref_display,
                    flag=flag
                )
            )

        order.lab_results = results
        order.status = DiagnosticStatus.RESULTED
        return order

    def enter_radiology_report(self, input_data: RadiologyReportEntryInput) -> DiagnosticOrder:
        order = self._orders.get(input_data.order_id)
        if not order:
            raise ValueError(f"Diagnostic order {input_data.order_id} not found.")

        order.radiology_technique = input_data.technique
        order.radiology_findings = input_data.findings
        order.radiology_impression = input_data.impression
        order.status = DiagnosticStatus.RESULTED
        return order

    def verify_and_publish_report(self, input_data: VerificationInput) -> DiagnosticOrder:
        order = self._orders.get(input_data.order_id)
        if not order:
            raise ValueError(f"Diagnostic order {input_data.order_id} not found.")

        if order.status not in (DiagnosticStatus.RESULTED, DiagnosticStatus.ANALYSIS_IN_PROGRESS):
            raise ValueError(f"Cannot verify order in status '{order.status}'. Results must be entered first.")

        now = datetime.now(timezone.utc)
        order.verified_by = f"{input_data.verifier_name} ({input_data.verifier_qualification})"
        order.verifier_registration_no = input_data.verifier_registration_no
        order.verified_at = now
        order.verifier_comments = input_data.clinical_comments
        order.status = DiagnosticStatus.VERIFIED

        patient = self.identity_service._patients.get(order.mpi_id)
        tenant_id = getattr(patient, "tenant_id", None) or getattr(patient, "facility_tenant_id", None) or uuid.UUID("00000000-0000-0000-0000-000000000004")

        self.outbox.stage_event(
            CloudEventEnvelope(
                type="health.diagnostics.report_published.v1",
                tenantid=tenant_id,
                mpiid=order.mpi_id,
                actorid=order.order_id,
                actorrole="PATHOLOGIST_OR_RADIOLOGIST",
                data={
                    "order_id": str(order.order_id),
                    "accession_number": order.accession_number,
                    "item_code": order.item_code,
                    "item_name": order.item_name,
                    "standard_code": order.standard_code,
                    "verified_by": order.verified_by,
                    "verified_at": now.isoformat()
                }
            )
        )

        return order

    def get_order(self, order_id: uuid.UUID) -> Optional[DiagnosticOrder]:
        return self._orders.get(order_id)

    def get_worklist(self, category: Optional[DiagnosticCategory] = None) -> List[DiagnosticOrder]:
        orders = list(self._orders.values())
        if category:
            orders = [o for o in orders if o.category == category]
        # Sort newest first
        orders.sort(key=lambda o: o.ordered_at, reverse=True)
        return orders

    def get_patient_orders(self, mpi_id: uuid.UUID) -> List[DiagnosticOrder]:
        orders = [o for o in self._orders.values() if o.mpi_id == mpi_id]
        orders.sort(key=lambda o: o.ordered_at, reverse=True)
        return orders
