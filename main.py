#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.agents import InvoiceOrchestrator
from src.models import InvoiceStatus


def main():
    parser = argparse.ArgumentParser(description="Invoice Processing Automation")
    parser.add_argument('--invoice_path', type=str)
    parser.add_argument('--no-llm', action='store_true')
    parser.add_argument('--init-db', action='store_true')
    args = parser.parse_args()
    
    if args.init_db:
        from src.database import init_database
        init_database()
        print("Database initialized.")
        if not args.invoice_path: return
    
    if not args.invoice_path:
        parser.print_help()
        return
    
    print(f"\n{'='*111}")
    print(f"INVOICE PROCESSING SYSTEM | LLM: {'ON' if not args.no_llm else 'OFF'}")
    print(f"{'='*111}")
    
    result = InvoiceOrchestrator(use_llm=not args.no_llm).process(args.invoice_path)
    
    if result.invoice:
        print(f"\nInvoice: {result.invoice.invoice_number}")
        print(f"Vendor: {result.invoice.vendor}")
        print(f"Amount: ${result.invoice.total:,.2f}")
        print(f"Items: {len(result.invoice.line_items)}")
    
    if result.validation_result:
        errors = sum(1 for i in result.validation_result.issues if i.severity == "error")
        print(f"\nValidation: {'PASS' if result.validation_result.is_valid else 'FAIL'} ({errors} errors)")
        for issue in result.validation_result.issues:
            print(f"  [{issue.severity}] {issue.message}")
    
    if result.approval_decision:
        conf = result.approval_decision.confidence
        if isinstance(conf, str): conf = float(conf) if conf else 0.5
        print(f"\nApproval: {'YES' if result.approval_decision.approved else 'NO'} ({conf:.0%})")
    
    if result.payment_result:
        if result.payment_result.success:
            print(f"\nPayment: SUCCESS | TXN: {result.payment_result.transaction_id}")
        else:
            print(f"\nPayment: {result.payment_result.message[:80]}")
    
    return {"status": result.status.value, "paid": result.status == InvoiceStatus.PAID}


if __name__ == "__main__":
    main()
