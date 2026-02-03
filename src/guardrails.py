import re
from pathlib import Path
from .config import (
    MAX_INVOICE_AMOUNT, MAX_ITEMS_PER_INVOICE, MAX_INPUT_SIZE,
    ALLOWED_EXTENSIONS, BLOCKED_VENDORS, MIN_CONFIDENCE_THRESHOLD
)


def validate_file_input(file_path: str) -> tuple[bool, str]:
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, f"Blocked file type: {path.suffix}"
    if path.stat().st_size > MAX_INPUT_SIZE:
        return False, f"File exceeds {MAX_INPUT_SIZE // 1024}KB limit"
    return True, "OK"


def validate_invoice_constraints(invoice) -> list[str]:
    violations = []
    if invoice.total > MAX_INVOICE_AMOUNT:
        violations.append(f"Amount ${invoice.total:,.2f} exceeds max ${MAX_INVOICE_AMOUNT:,}")
    if invoice.total < 0:
        violations.append("Negative invoice total")
    if len(invoice.line_items) > MAX_ITEMS_PER_INVOICE:
        violations.append(f"Too many items ({len(invoice.line_items)} > {MAX_ITEMS_PER_INVOICE})")
    if invoice.vendor and invoice.vendor.lower() in [v.lower() for v in BLOCKED_VENDORS]:
        violations.append(f"Blocked vendor: {invoice.vendor}")
    return violations


def sanitize_llm_input(text: str, max_chars: int = 10000) -> str:
    text = text[:max_chars]
    text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
    return text.strip()


def validate_llm_output(response: dict, required_fields: list[str]) -> tuple[bool, str]:
    if not response:
        return False, "Empty LLM response"
    missing = [f for f in required_fields if f not in response]
    if missing:
        return False, f"Missing fields: {missing}"
    return True, "OK"


def check_approval_confidence(confidence: float) -> bool:
    return confidence >= MIN_CONFIDENCE_THRESHOLD
