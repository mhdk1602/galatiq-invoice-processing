from pathlib import Path
from .base_agent import BaseAgent
from ..models import Invoice, LineItem
from ..parsers import pre_parse_invoice
from ..llm_client import get_llm_client
from ..config import FRAUD_KEYWORDS
from ..guardrails import validate_file_input, validate_invoice_constraints, sanitize_llm_input


class IngestionAgent(BaseAgent):
    def __init__(self, use_llm: bool = True):
        super().__init__("IngestionAgent")
        self.use_llm = use_llm
        self._client = None
    
    def _get_client(self):
        if self._client is None and self.use_llm:
            self._client = get_llm_client()
        return self._client
    
    def _detect_fraud(self, text: str) -> list[str]:
        indicators = []
        lower = text.lower()
        for kw in FRAUD_KEYWORDS:
            if kw in lower:
                indicators.append(f"Contains '{kw}'")
        if 'yesterday' in lower or 'immediate' in lower:
            indicators.append("Unrealistic urgency")
        return indicators
    
    def process(self, file_path: str) -> tuple[Invoice, list[str]]:
        self.log(f"Processing: {file_path}")
        
        valid, msg = validate_file_input(file_path)
        if not valid:
            raise ValueError(f"Input validation failed: {msg}")
        
        notes = []
        basic, content, fmt = pre_parse_invoice(file_path)
        notes.append(f"Format: {fmt}")
        
        fraud = self._detect_fraud(content)
        if fraud:
            self.log(f"Fraud indicators: {len(fraud)}", "WARNING")
            notes.extend([f"FRAUD: {f}" for f in fraud])
        
        if self.use_llm and self._get_client():
            try:
                self.log("Using LLM extraction...")
                sanitized = sanitize_llm_input(content)
                llm = self._get_client().extract_invoice(sanitized)
                def parse_num(val, as_int=False):
                    if val is None: return 0
                    if isinstance(val, (int, float)): return int(val) if as_int else float(val)
                    val = str(val).replace(',', '').replace('$', '').strip()
                    return int(float(val)) if as_int else float(val) if val else 0
                items = [LineItem(i.get('item_name', ''), parse_num(i.get('quantity'), True), parse_num(i.get('unit_price')))
                         for i in llm.get('items', [])]
                total = llm.get('total') or basic.total
                if isinstance(total, str):
                    total = float(total.replace(',', '').replace('$', '')) if total else 0
                invoice = Invoice(
                    llm.get('invoice_number') or basic.invoice_number,
                    llm.get('vendor') or basic.vendor,
                    llm.get('date') or basic.date,
                    llm.get('due_date') or basic.due_date,
                    items or basic.line_items,
                    basic.subtotal, basic.tax,
                    float(total) if total else basic.total,
                    'USD', basic.payment_terms, content, file_path
                )
                if llm.get('fraud_indicators'):
                    notes.extend([f"LLM FRAUD: {f}" for f in llm['fraud_indicators']])
            except Exception as e:
                self.log(f"LLM failed: {e}, using basic parse", "WARNING")
                invoice = basic
        else:
            invoice = basic
        
        violations = validate_invoice_constraints(invoice)
        if violations:
            notes.extend([f"CONSTRAINT: {v}" for v in violations])
            self.log(f"Constraint violations: {len(violations)}", "WARNING")
        
        self.log(f"Extracted: {invoice.invoice_number} from {invoice.vendor}, ${invoice.total:,.2f}")
        return invoice, notes
