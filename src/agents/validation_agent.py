from .base_agent import BaseAgent
from ..models import Invoice, ValidationResult, ValidationIssue, ValidationIssueType
from ..database import check_stock, get_vendor_info


class ValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("ValidationAgent")
    
    def process(self, invoice: Invoice) -> ValidationResult:
        self.log(f"Validating: {invoice.invoice_number}")
        issues, warnings = [], []
        
        if not invoice.invoice_number or invoice.invoice_number == 'UNKNOWN':
            issues.append(ValidationIssue(ValidationIssueType.MISSING_DATA, None, "Missing invoice number"))
        if not invoice.vendor or invoice.vendor in ['Unknown', 'Unknown Vendor']:
            issues.append(ValidationIssue(ValidationIssueType.MISSING_DATA, None, "Missing vendor"))
        if invoice.due_date and invoice.due_date.lower() in ['yesterday', 'today', 'immediate']:
            issues.append(ValidationIssue(ValidationIssueType.INVALID_DATE, None, f"Invalid due date: {invoice.due_date}", "warning"))
        
        vendor = get_vendor_info(invoice.vendor)
        if vendor and not vendor.get('is_approved'):
            issues.append(ValidationIssue(ValidationIssueType.FRAUD_INDICATOR, None,
                          f"Vendor '{invoice.vendor}' not approved (risk: {vendor.get('risk_score', 0)})"))
        elif not vendor:
            warnings.append(f"Vendor '{invoice.vendor}' not in database")
        
        inventory_checks = {}
        for item in invoice.line_items:
            if item.quantity < 0:
                issues.append(ValidationIssue(ValidationIssueType.NEGATIVE_QUANTITY, item.item_name,
                              f"Negative quantity ({item.quantity}) for {item.item_name}"))
            
            result = check_stock(item.item_name, item.quantity)
            inventory_checks[item.item_name] = result
            
            if not result['available']:
                reason = result['reason']
                if reason == 'item_not_found':
                    issues.append(ValidationIssue(ValidationIssueType.ITEM_NOT_FOUND, item.item_name,
                                  f"'{item.item_name}' not in inventory"))
                elif reason == 'zero_stock':
                    issues.append(ValidationIssue(ValidationIssueType.ZERO_STOCK, item.item_name,
                                  f"'{item.item_name}' has zero stock"))
                elif reason == 'insufficient_stock':
                    issues.append(ValidationIssue(ValidationIssueType.INSUFFICIENT_STOCK, item.item_name,
                                  f"'{item.item_name}': need {item.quantity}, have {result['in_stock']}"))
            else:
                self.log(f"  OK {item.item_name}: {item.quantity}/{result['in_stock']}")
        
        errors = [i for i in issues if i.severity == "error"]
        self.log(f"Result: {'PASS' if not errors else 'FAIL'} ({len(errors)} errors, {len(warnings)} warnings)")
        return ValidationResult(len(errors) == 0, issues, warnings, inventory_checks)
