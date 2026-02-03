import json
from .base_agent import BaseAgent
from ..models import Invoice, ValidationResult, ApprovalDecision, ValidationIssueType
from ..llm_client import get_llm_client
from ..config import HIGH_VALUE_THRESHOLD, FRAUD_KEYWORDS


class ApprovalAgent(BaseAgent):
    def __init__(self, use_llm: bool = True):
        super().__init__("ApprovalAgent")
        self.use_llm = use_llm
        self._client = None
    
    def _get_client(self):
        if self._client is None and self.use_llm:
            self._client = get_llm_client()
        return self._client
    
    def _assess_risk(self, invoice: Invoice, validation: ValidationResult) -> tuple[str, list[str]]:
        factors, score = [], 0
        
        if invoice.total > HIGH_VALUE_THRESHOLD:
            factors.append(f"High value: ${invoice.total:,.2f}")
            score += 2
        
        errors = sum(1 for i in validation.issues if i.severity == "error")
        if errors:
            factors.append(f"{errors} validation errors")
            score += errors * 3
        
        fraud = [i for i in validation.issues if i.issue_type == ValidationIssueType.FRAUD_INDICATOR]
        if fraud:
            factors.extend([f"Fraud: {i.message}" for i in fraud])
            score += len(fraud) * 5
        
        if invoice.raw_text:
            for kw in FRAUD_KEYWORDS:
                if kw in invoice.raw_text.lower():
                    factors.append(f"Suspicious keyword: '{kw}'")
                    score += 2
        
        level = "CRITICAL" if score >= 10 else "HIGH" if score >= 5 else "MEDIUM" if score >= 2 else "LOW"
        return level, factors
    
    def process(self, invoice: Invoice, validation: ValidationResult) -> ApprovalDecision:
        self.log(f"Evaluating: {invoice.invoice_number} (${invoice.total:,.2f})")
        
        risk_level, factors = self._assess_risk(invoice, validation)
        self.log(f"Risk: {risk_level}")
        for f in factors:
            self.log(f"  - {f}")
        
        fraud = [i for i in validation.issues if i.issue_type == ValidationIssueType.FRAUD_INDICATOR]
        if fraud:
            return ApprovalDecision(False, f"Auto-reject: fraud - {fraud[0].message}", factors, 1.0, True)
        
        neg = [i for i in validation.issues if i.issue_type == ValidationIssueType.NEGATIVE_QUANTITY]
        if neg:
            return ApprovalDecision(False, "Auto-reject: negative quantities", factors, 1.0, False)
        
        if risk_level == "LOW" and invoice.total < 1000 and validation.is_valid:
            return ApprovalDecision(True, "Auto-approve: low risk, small amount", factors, 0.95, False)
        
        if risk_level == "CRITICAL":
            return ApprovalDecision(False, "Hold: critical risk requires manual review", factors, 0.5, True)
        
        if self.use_llm and self._get_client():
            try:
                self.log("Using LLM reasoning with reflection...")
                invoice_data = {"invoice_number": invoice.invoice_number, "vendor": invoice.vendor,
                               "total": invoice.total, "items": [{"name": i.item_name, "qty": i.quantity} for i in invoice.line_items]}
                issues_data = [{"type": i.issue_type.value, "msg": i.message} for i in validation.issues]
                context = f"Risk: {risk_level}, Factors: {factors}"
                
                result = self._get_client().analyze_approval(invoice_data, issues_data, context)
                decision = result.get('final_decision', {})
                
                return ApprovalDecision(
                    decision.get('approved', False),
                    f"Assessment: {result.get('initial_assessment', 'N/A')}\nCritique: {result.get('critique', 'N/A')}\nDecision: {decision.get('reasoning', 'N/A')}",
                    result.get('risk_factors', factors),
                    decision.get('confidence', 0.5),
                    decision.get('requires_human_review', False)
                )
            except Exception as e:
                self.log(f"LLM failed: {e}", "ERROR")
        
        approved = validation.is_valid and risk_level in ["LOW", "MEDIUM"]
        return ApprovalDecision(approved, f"Rule-based: valid={validation.is_valid}, risk={risk_level}",
                               factors, 0.7 if approved else 0.3, risk_level in ["HIGH", "CRITICAL"])
