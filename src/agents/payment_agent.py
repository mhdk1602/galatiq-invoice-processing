import uuid
from datetime import datetime
from .base_agent import BaseAgent
from ..models import Invoice, ApprovalDecision, PaymentResult
from ..database import record_invoice


class PaymentAgent(BaseAgent):
    def __init__(self):
        super().__init__("PaymentAgent")
    
    def _mock_payment(self, vendor: str, amount: float, invoice_num: str) -> dict:
        txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        print(f"\n[PAYMENT] {txn_id} | ${amount:,.2f} to {vendor}\n")
        return {"status": "success", "transaction_id": txn_id}
    
    def process(self, invoice: Invoice, decision: ApprovalDecision) -> PaymentResult:
        if not decision.approved:
            self.log(f"Rejected: {invoice.invoice_number}")
            print(f"\n[REJECTED] {invoice.invoice_number} | {decision.reasoning[:100]}...\n")
            record_invoice(invoice.invoice_number, invoice.vendor, invoice.total, "rejected")
            return PaymentResult(False, None, f"Rejected: {decision.reasoning[:200]}", datetime.now())
        
        self.log(f"Processing payment: ${invoice.total:,.2f} to {invoice.vendor}")
        result = self._mock_payment(invoice.vendor, invoice.total, invoice.invoice_number)
        record_invoice(invoice.invoice_number, invoice.vendor, invoice.total, "paid")
        return PaymentResult(True, result["transaction_id"], f"Paid ${invoice.total:,.2f} to {invoice.vendor}", datetime.now())
