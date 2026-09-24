import uuid
from health_platform.core.financial.models import ChargeItemModel, JournalEntry, LedgerLineItem
from health_platform.core.financial.service import FinancialLedgerService
from health_platform.core.common.exceptions import UnanchoredChargeError, ImbalancedLedgerError
from health_platform.core.events.envelope import CloudEventEnvelope, TransactionalOutboxPublisher

def test_unanchored_charge_rejection():
    """CSG-1: Verifies that an unanchored charge without a clinical order origin throws an error."""
    error_caught = False
    try:
        ChargeItemModel(
            encounter_id=uuid.uuid4(),
            mpi_id=uuid.uuid4(),
            originating_resource_type="",
            originating_resource_id=None, # Missing!
            tariff_code="LAB-BIO-042",
            department_code="BIOCHEMISTRY",
            unit_price=650.0,
            gross_amount=650.0,
            net_amount=650.0,
            patient_share=650.0
        )
    except Exception:
        error_caught = True
    assert error_caught is True

def test_imbalanced_ledger_rejection():
    """CSG-3: Verifies that an imbalanced journal entry (Debits != Credits) is rejected."""
    imbalanced_caught = False
    try:
        JournalEntry(
            encounter_id=uuid.uuid4(),
            entry_type="CORRUPT_CHARGE",
            narration="Test imbalanced line items",
            lines=[
                LedgerLineItem(account_code="1200-AR-PATIENT", debit_amount=500.0, credit_amount=0.0),
                LedgerLineItem(account_code="4001-REV-OPD", debit_amount=0.0, credit_amount=400.0) # Imbalance of ₹100!
            ]
        )
    except ImbalancedLedgerError:
        imbalanced_caught = True
    assert imbalanced_caught is True

def test_end_to_end_charge_capture_and_trial_balance():
    ledger = FinancialLedgerService()
    encounter_id = uuid.uuid4()
    mpi_id = uuid.uuid4()
    order_id = uuid.uuid4()

    # 1. Clinician signs an investigation order: ₹650.00 with 20% patient co-pay
    charge = ledger.capture_charge_from_clinical_order(
        encounter_id=encounter_id,
        mpi_id=mpi_id,
        originating_resource_type="ServiceRequest",
        originating_resource_id=order_id,
        tariff_code="LAB-BIO-042",
        department_code="BIOCHEMISTRY",
        unit_price=650.00,
        quantity=1.0,
        patient_co_pay_ratio=0.20 # Patient pays ₹130.00, Insurer pays ₹520.00
    )

    assert charge.gross_amount == 650.00
    assert charge.patient_share == 130.00
    assert charge.insurer_share == 520.00

    # 2. Verify double-entry balance: Net trial balance discrepancy MUST be ₹0.00
    assert ledger.get_trial_balance_discrepancy() == 0.00

    # 3. Patient pays ₹130.00 co-pay via UPI
    payment_journal = ledger.record_patient_payment(
        encounter_id=encounter_id,
        mpi_id=mpi_id,
        amount=130.00,
        payment_method="UPI"
    )
    assert payment_journal.entry_type == "PAYMENT_RECEIVED"

    # Net balance across all asset, liability, and revenue accounts remains balanced
    assert ledger.get_trial_balance_discrepancy() == 0.00

def test_transactional_outbox_partitioning():
    outbox = TransactionalOutboxPublisher()
    patient_mpi = uuid.uuid4()
    tenant_id = uuid.uuid4()

    event = CloudEventEnvelope(
        type="health.financial.charge_captured.v1",
        tenantid=tenant_id,
        mpiid=patient_mpi,
        data={
            "tariff_code": "LAB-BIO-042",
            "net_amount": 650.00
        }
    )

    event_id = outbox.stage_event(event)
    pending = outbox.get_pending_events()
    assert len(pending) == 1
    # Check that partition key is strictly the patient's mpi_id
    assert pending[0]["partition_key"] == str(patient_mpi)
    assert pending[0]["status"] == "PENDING"

    outbox.mark_published(event_id)
    assert len(outbox.get_pending_events()) == 0
