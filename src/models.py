from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    PAYMENT_FAILED = "payment_failed"


class ValidationIssueType(str, Enum):
    ITEM_NOT_FOUND = "item_not_found"
    INSUFFICIENT_STOCK = "insufficient_stock"
    ZERO_STOCK = "zero_stock"
    NEGATIVE_QUANTITY = "negative_quantity"
    MISSING_DATA = "missing_data"
    FRAUD_INDICATOR = "fraud_indicator"
    INVALID_DATE = "invalid_date"
    DATA_INTEGRITY = "data_integrity"


@dataclass
class LineItem:
    item_name: str
    quantity: int
    unit_price: float
    amount: Optional[float] = None
    
    def __post_init__(self):
        if self.amount is None:
            self.amount = self.quantity * self.unit_price


@dataclass
class Invoice:
    invoice_number: str
    vendor: str
    date: Optional[str] = None
    due_date: Optional[str] = None
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float = 0.0
    currency: str = "USD"
    payment_terms: Optional[str] = None
    raw_text: Optional[str] = None
    source_file: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ValidationIssue:
    issue_type: ValidationIssueType
    item_name: Optional[str]
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    inventory_checks: dict = field(default_factory=dict)


@dataclass
class ApprovalDecision:
    approved: bool
    reasoning: str
    risk_factors: list[str] = field(default_factory=list)
    confidence: float = 1.0
    requires_review: bool = False


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    message: str = ""
    timestamp: Optional[datetime] = None


@dataclass
class ProcessingResult:
    invoice: Invoice
    status: InvoiceStatus
    validation_result: Optional[ValidationResult] = None
    approval_decision: Optional[ApprovalDecision] = None
    payment_result: Optional[PaymentResult] = None
    error_message: Optional[str] = None
    processing_logs: list[str] = field(default_factory=list)
