import uuid
from typing import Dict, List, Optional
from health_platform.core.financial.models import ChargeItemModel, JournalEntry, LedgerLineItem
from health_platform.core.common.exceptions import UnanchoredChargeError, ImbalancedLedgerError

class FinancialLedgerService:
    """
    Authoritative Domain Service managing Hospital Charges, Multi-Payer Splits,
    and Append-Only Double-Entry Financial Ledgers.
    """
    def __init__(self):
        self._charges: Dict[uuid.UUID, ChargeItemModel] = {}
        self._journals: List[JournalEntry] = []
        self._account_balances: Dict[str, float] = {} # Account Code -> Net Balance

    def capture_charge_from_clinical_order(
        self,
        encounter_id: uuid.UUID,
        mpi_id: uuid.UUID,
        originating_resource_type: str,
        originating_resource_id: uuid.UUID,
        tariff_code: str,
        department_code: str,
        unit_price: float,
        quantity: float = 1.0,
        patient_co_pay_ratio: float = 1.0, # 1.0 = 100% self-pay, 0.2 = 20% co-pay
        coverage_id: Optional[uuid.UUID] = None
    ) -> ChargeItemModel:
        """
        Captures a billable charge item directly linked to a clinical order or activity,
        and atomically posts balanced double-entry accounting records.
        """
        gross = round(unit_price * quantity, 2)
        net = gross
        patient_share = round(net * patient_co_pay_ratio, 2)
        insurer_share = round(net - patient_share, 2)

        charge = ChargeItemModel(
            encounter_id=encounter_id,
            mpi_id=mpi_id,
            originating_resource_type=originating_resource_type,
            originating_resource_id=originating_resource_id,
            tariff_code=tariff_code,
            department_code=department_code,
            unit_price=unit_price,
            quantity=quantity,
            gross_amount=gross,
            net_amount=net,
            patient_share=patient_share,
            insurer_share=insurer_share,
            coverage_id=coverage_id
        )

        self._charges[charge.charge_item_id] = charge

        # Build balanced double-entry lines
        lines: List[LedgerLineItem] = []
        
        # Debits (Accounts Receivable)
        if patient_share > 0:
            lines.append(LedgerLineItem(account_code="1200-AR-PATIENT", debit_amount=patient_share, credit_amount=0.0))
        if insurer_share > 0:
            lines.append(LedgerLineItem(account_code="1201-AR-INSURER", debit_amount=insurer_share, credit_amount=0.0))

        # Credit (Department Revenue)
        rev_account = f"4001-REV-{department_code.upper()}"
        lines.append(LedgerLineItem(account_code=rev_account, debit_amount=0.0, credit_amount=net))

        journal = JournalEntry(
            encounter_id=encounter_id,
            entry_type="CHARGE_POSTED",
            narration=f"Charge captured from {originating_resource_type} #{originating_resource_id} (Tariff: {tariff_code})",
            lines=lines
        )

        self._journals.append(journal)

        # Update ledger trial balance
        for line in lines:
            curr = self._account_balances.get(line.account_code, 0.0)
            if line.debit_amount > 0:
                self._account_balances[line.account_code] = round(curr + line.debit_amount, 2)
            else:
                self._account_balances[line.account_code] = round(curr - line.credit_amount, 2)

        return charge

    def record_patient_payment(
        self,
        encounter_id: uuid.UUID,
        mpi_id: uuid.UUID,
        amount: float,
        payment_method: str = "UPI"
    ) -> JournalEntry:
        """
        Records a cash or UPI payment from a patient, reducing AR-PATIENT and increasing Cash/Bank.
        """
        lines = [
            LedgerLineItem(account_code=f"1001-{payment_method.upper()}-CLEARING", debit_amount=amount, credit_amount=0.0),
            LedgerLineItem(account_code="1200-AR-PATIENT", debit_amount=0.0, credit_amount=amount)
        ]

        journal = JournalEntry(
            encounter_id=encounter_id,
            entry_type="PAYMENT_RECEIVED",
            narration=f"Patient payment received via {payment_method}",
            lines=lines
        )

        self._journals.append(journal)
        return journal

    def get_trial_balance_discrepancy(self) -> float:
        """Computes the net sum of all ledger balances (must mathematically equal 0.00)."""
        return round(sum(self._account_balances.values()), 2)
