from datetime import datetime
from .base_agent import BaseAgent
from .ingestion_agent import IngestionAgent
from .validation_agent import ValidationAgent
from .approval_agent import ApprovalAgent
from .payment_agent import PaymentAgent
from ..models import ProcessingResult, InvoiceStatus
from ..database import init_database


class InvoiceOrchestrator(BaseAgent):
    def __init__(self, use_llm: bool = True):
        super().__init__("Orchestrator")
        self.ingestion = IngestionAgent(use_llm)
        self.validation = ValidationAgent()
        self.approval = ApprovalAgent(use_llm)
        self.payment = PaymentAgent()
        init_database()
    
    def process(self, file_path: str) -> ProcessingResult:
        start = datetime.now()
        self.log(f"Processing: {file_path}")
        result = ProcessingResult(invoice=None, status=InvoiceStatus.PENDING)
        
        try:
            print("\n" + "="*50 + " INGESTION " + "="*50)
            invoice, notes = self.ingestion.process(file_path)
            result.invoice = invoice
            
            print("\n" + "="*50 + " VALIDATION " + "="*49)
            validation = self.validation.process(invoice)
            result.validation_result = validation
            result.status = InvoiceStatus.VALIDATED if validation.is_valid else InvoiceStatus.VALIDATION_FAILED
            
            print("\n" + "="*50 + " APPROVAL " + "="*50)
            decision = self.approval.process(invoice, validation)
            result.approval_decision = decision
            result.status = InvoiceStatus.APPROVED if decision.approved else InvoiceStatus.REJECTED
            
            print("\n" + "="*50 + " PAYMENT " + "="*51)
            payment = self.payment.process(invoice, decision)
            result.payment_result = payment
            result.status = InvoiceStatus.PAID if payment.success else (InvoiceStatus.PAYMENT_FAILED if decision.approved else InvoiceStatus.REJECTED)
            
        except Exception as e:
            result.error_message = str(e)
            result.status = InvoiceStatus.VALIDATION_FAILED
            self.log(f"Error: {e}", "ERROR")
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"\n{'='*111}\nRESULT: {result.status.value.upper()} | Time: {elapsed:.1f}s\n{'='*111}")
        return result
