#!/usr/bin/env python3
"""
Web Application for Invoice Assessment
Provides a simple interface to upload invoice files and run the assessment pipeline.
"""
import os
import sys
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.agents import InvoiceOrchestrator
from src.models import InvoiceStatus, ValidationIssueType
from src.config import ALLOWED_EXTENSIONS, MAX_INPUT_SIZE
from src.database import init_database

# Initialize FastAPI app
app = FastAPI(
    title="Invoice Assessment System",
    description="Upload invoices for automated assessment and processing",
    version="1.0.0"
)

# Create uploads directory for temporary file storage
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def serialize_result(result) -> dict:
    """Convert ProcessingResult to JSON-serializable dict."""
    data = {
        "status": result.status.value,
        "error_message": result.error_message,
        "processing_logs": result.processing_logs,
    }
    
    if result.invoice:
        inv = result.invoice
        data["invoice"] = {
            "invoice_number": inv.invoice_number,
            "vendor": inv.vendor,
            "date": inv.date,
            "due_date": inv.due_date,
            "total": inv.total,
            "currency": inv.currency,
            "payment_terms": inv.payment_terms,
            "notes": inv.notes,
            "line_items": [
                {
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "amount": item.amount
                }
                for item in inv.line_items
            ]
        }
    
    if result.validation_result:
        val = result.validation_result
        data["validation"] = {
            "is_valid": val.is_valid,
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "item": issue.item_name,
                    "message": issue.message,
                    "severity": issue.severity
                }
                for issue in val.issues
            ],
            "warnings": val.warnings,
            "inventory_checks": val.inventory_checks
        }
    
    if result.approval_decision:
        dec = result.approval_decision
        confidence = dec.confidence
        if isinstance(confidence, str):
            confidence = float(confidence) if confidence else 0.5
        data["approval"] = {
            "approved": dec.approved,
            "reasoning": dec.reasoning,
            "risk_factors": dec.risk_factors,
            "confidence": confidence,
            "requires_review": dec.requires_review
        }
    
    if result.payment_result:
        pay = result.payment_result
        data["payment"] = {
            "success": pay.success,
            "transaction_id": pay.transaction_id,
            "message": pay.message,
            "timestamp": pay.timestamp.isoformat() if pay.timestamp else None
        }
    
    return data


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main upload page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/assess")
async def assess_invoice(
    file: UploadFile = File(...),
    use_llm: bool = True
):
    """
    Upload and assess an invoice file.
    
    Supports: .txt, .pdf, .json, .csv, .xml
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    contents = await file.read()
    if len(contents) > MAX_INPUT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_INPUT_SIZE // 1024}KB"
        )
    
    # Save file temporarily
    file_id = str(uuid.uuid4())[:8]
    temp_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    try:
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # Process the invoice
        orchestrator = InvoiceOrchestrator(use_llm=use_llm)
        result = orchestrator.process(str(temp_path))
        
        # Serialize result
        response_data = serialize_result(result)
        response_data["filename"] = file.filename
        response_data["processed_at"] = datetime.now().isoformat()
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/sample-invoices")
async def list_sample_invoices():
    """List available sample invoices for testing."""
    invoices_dir = Path(__file__).parent / "data" / "invoices"
    if not invoices_dir.exists():
        return {"invoices": []}
    
    invoices = []
    for f in sorted(invoices_dir.iterdir()):
        if f.suffix.lower() in ALLOWED_EXTENSIONS:
            invoices.append({
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "type": f.suffix.lower()
            })
    
    return {"invoices": invoices}


@app.post("/api/assess-sample/{filename}")
async def assess_sample_invoice(filename: str, use_llm: bool = True):
    """Assess a sample invoice by filename."""
    invoices_dir = Path(__file__).parent / "data" / "invoices"
    file_path = invoices_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample invoice not found: {filename}")
    
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type")
    
    try:
        orchestrator = InvoiceOrchestrator(use_llm=use_llm)
        result = orchestrator.process(str(file_path))
        
        response_data = serialize_result(result)
        response_data["filename"] = filename
        response_data["processed_at"] = datetime.now().isoformat()
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_database()
    print("Database initialized.")
    print(f"Upload directory: {UPLOAD_DIR}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"\n{'='*60}")
    print(f"Invoice Assessment System")
    print(f"{'='*60}")
    print(f"Open your browser at: http://localhost:{port}")
    print(f"{'='*60}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
