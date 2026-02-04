# Galatiq Case: Invoice Processing Automation

A multi-agent system that automates end-to-end invoice processing with LLM-powered extraction, validation, approval, and payment workflows.

## Quick Start

```bash
# 1. Clone and navigate to the project
cd galatiq-case-invoices

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your API key
cp .env.example .env
# Edit .env and add your xAI API key

# 4. Initialize the database
python main.py --init-db

# 5. Launch the web interface
python web_app.py
# Open http://localhost:8080 in your browser
```

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Command Line](#command-line)
  - [API Endpoints](#api-endpoints)
- [Workflow Demo](#workflow-demo)
- [Sample Invoices](#sample-invoices)
- [Configuration](#configuration)

---

## Overview

### Background

Acme Corp is a PE-backed manufacturing firm losing **$2M/year** on manual invoice processing. Invoices arrive via email as PDFs in messy formats with frequent errors. Staff manually extract data, validate against a legacy inventory database (inconsistent), obtain VP approval (via email chains), and process payment.

**Current pain points:**
- 30% error rate
- 5-day processing delays
- Frustrated stakeholders

### Solution

This system automates the four-stage invoice processing workflow:

| Stage | Description | Agent |
|-------|-------------|-------|
| **1. Ingestion** | Extract structured data from invoices (PDF, TXT, JSON, CSV, XML) | `IngestionAgent` |
| **2. Validation** | Verify against inventory database, flag mismatches | `ValidationAgent` |
| **3. Approval** | VP-level review with LLM reasoning and reflection | `ApprovalAgent` |
| **4. Payment** | Process payment or log rejection | `PaymentAgent` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Invoice Assessment System                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     │
│   │  Web UI  │───▶│  FastAPI     │───▶│  Orchestrator    │     │
│   │ (Upload) │    │  /api/assess │    │                  │     │
│   └──────────┘    └──────────────┘    └────────┬─────────┘     │
│                                                │               │
│         ┌──────────────────────────────────────┼───────────┐   │
│         │                                      ▼           │   │
│         │   ┌─────────────┐    ┌─────────────────────┐     │   │
│         │   │  Ingestion  │───▶│  Invoice + LineItems│     │   │
│         │   │    Agent    │    └─────────────────────┘     │   │
│         │   └─────────────┘              │                 │   │
│         │         │                      ▼                 │   │
│         │         │         ┌─────────────────────┐        │   │
│         │         │         │    Validation       │        │   │
│         │         │         │      Agent          │        │   │
│         │         │         └─────────┬───────────┘        │   │
│         │         │                   │                    │   │
│         │   ┌─────▼─────┐            │                    │   │
│         │   │   Grok    │◀───────────┤                    │   │
│         │   │   LLM     │            │                    │   │
│         │   └───────────┘            ▼                    │   │
│         │         │         ┌─────────────────────┐        │   │
│         │         │         │    Approval         │        │   │
│         │         └────────▶│      Agent          │        │   │
│         │                   └─────────┬───────────┘        │   │
│         │                             │                    │   │
│         │                             ▼                    │   │
│         │                   ┌─────────────────────┐        │   │
│         │                   │    Payment          │        │   │
│         │                   │      Agent          │        │   │
│         │                   └─────────────────────┘        │   │
│         │                                                  │   │
│         └──────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    SQLite Database                       │  │
│   │  • inventory (items, stock, prices)                     │  │
│   │  • vendors (approved status, risk scores)               │  │
│   │  • processed_invoices (audit trail)                     │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.10+
- xAI API key (get one at https://console.x.ai/)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `.env` and add your xAI API key:

```env
XAI_API_KEY=xai-your-api-key-here
```

### Initialize Database

```bash
python main.py --init-db
```

This creates `inventory.db` with sample data:

| Item | Stock | Unit Price |
|------|-------|------------|
| WidgetA | 15 | $250.00 |
| WidgetB | 10 | $500.00 |
| GadgetX | 5 | $750.00 |
| FakeItem | 0 | $1,000.00 |

---

## Usage

### Web Interface

The recommended way to interact with the system:

```bash
python web_app.py
```

Open **http://localhost:8080** in your browser.

**Features:**
- 📄 Drag-and-drop file upload
- 🔄 Toggle LLM-enhanced vs rule-based processing
- 📋 Quick-select sample invoices
- 📊 Visual results with validation issues, approval reasoning, and payment status

### Command Line

For scripting and automation:

```bash
# Process a single invoice
python main.py --invoice_path=data/invoices/invoice_1001.txt

# Process without LLM (faster, rule-based only)
python main.py --invoice_path=data/invoices/invoice_1001.txt --no-llm

# Initialize database only
python main.py --init-db
```

### API Endpoints

The web app exposes a REST API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `POST` | `/api/assess` | Upload and assess an invoice file |
| `GET` | `/api/sample-invoices` | List available sample invoices |
| `POST` | `/api/assess-sample/{filename}` | Assess a sample invoice |
| `GET` | `/api/health` | Health check |

**Example: Upload and assess**

```bash
curl -X POST -F "file=@invoice.pdf" "http://localhost:8080/api/assess"
```

**Example: Assess without LLM**

```bash
curl -X POST "http://localhost:8080/api/assess-sample/invoice_1001.txt?use_llm=false"
```

---

## Workflow Demo

### Scenario 1: Valid Invoice → Payment Success

**Invoice:** `invoice_1001.txt` (Widgets Inc., $5,000)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTION  │────▶│ VALIDATION  │────▶│  APPROVAL   │────▶│   PAYMENT   │
│             │     │             │     │             │     │             │
│ ✓ Extracted │     │ ✓ Stock OK  │     │ ✓ Approved  │     │ ✓ Success   │
│   2 items   │     │ ✓ Vendor OK │     │   Conf: 70% │     │ TXN-XXXXXX  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Try it:**
```bash
python main.py --invoice_path=data/invoices/invoice_1001.txt
```

### Scenario 2: Insufficient Stock → Rejection

**Invoice:** `invoice_1002.txt` (Gadgets Co., requests 20× GadgetX but only 5 in stock)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTION  │────▶│ VALIDATION  │────▶│  APPROVAL   │────▶│   PAYMENT   │
│             │     │             │     │             │     │             │
│ ✓ Extracted │     │ ✗ Stock:    │     │ ✗ Rejected  │     │ ✗ Skipped   │
│             │     │   need 20,  │     │   HIGH RISK │     │             │
│             │     │   have 5    │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Try it:**
```bash
python main.py --invoice_path=data/invoices/invoice_1002.txt
```

### Scenario 3: Fraudulent Invoice → Flagged

**Invoice:** `invoice_1003.txt` (references FakeItem with 0 stock, suspicious vendor)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTION  │────▶│ VALIDATION  │────▶│  APPROVAL   │────▶│   PAYMENT   │
│             │     │             │     │             │     │             │
│ ⚠ Fraud     │     │ ✗ Zero      │     │ ✗ Rejected  │     │ ✗ Blocked   │
│   keywords  │     │   stock     │     │   FRAUD     │     │             │
│   detected  │     │   item      │     │   DETECTED  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Try it:**
```bash
python main.py --invoice_path=data/invoices/invoice_1003.txt
```

### Scenario 4: Unknown Item → Validation Error

**Invoice:** `invoice_1008.txt` (references SuperGizmo, MegaSprocket - not in database)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTION  │────▶│ VALIDATION  │────▶│  APPROVAL   │────▶│   PAYMENT   │
│             │     │             │     │             │     │             │
│ ✓ Extracted │     │ ✗ Items     │     │ ✗ Rejected  │     │ ✗ Skipped   │
│             │     │   not found │     │   UNKNOWN   │     │             │
│             │     │   in DB     │     │   PRODUCTS  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Sample Invoices

The `data/invoices/` directory contains test invoices covering various scenarios:

| Invoice | Format | Scenario | Expected Result |
|---------|--------|----------|-----------------|
| `invoice_1001.txt` | TXT | Normal order, stock available | ✓ PAID |
| `invoice_1002.txt` | TXT | Quantity exceeds stock | ✗ REJECTED |
| `invoice_1003.txt` | TXT | Fraudulent (zero-stock item) | ✗ REJECTED |
| `invoice_1004.json` | JSON | Clean JSON format | ✓ PAID |
| `invoice_1005.json` | JSON | High-value ($15K+) | Requires scrutiny |
| `invoice_1006.csv` | CSV | CSV format test | ✓ PAID |
| `invoice_1008.txt` | TXT | Unknown items | ✗ REJECTED |
| `invoice_1009.json` | JSON | Negative quantity | ✗ REJECTED |
| `invoice_1011.pdf` | PDF | PDF extraction test | Varies |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `XAI_API_KEY` | xAI API key for Grok LLM | Required |
| `XAI_MODEL` | Grok model to use | `grok-4-1-fast-reasoning` |
| `PORT` | Web server port | `8080` |

### Business Rules

Configured in `src/config.py`:

| Setting | Value | Description |
|---------|-------|-------------|
| `HIGH_VALUE_THRESHOLD` | $10,000 | Invoices above this require extra scrutiny |
| `MAX_INVOICE_AMOUNT` | $500,000 | Maximum allowed invoice amount |
| `MIN_CONFIDENCE_THRESHOLD` | 0.6 | Minimum LLM confidence for auto-approval |
| `BLOCKED_VENDORS` | List | Vendors automatically rejected |
| `FRAUD_KEYWORDS` | List | Triggers fraud detection |

---

## Tech Stack

- **LLM**: xAI Grok (via xai-sdk)
- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite
- **PDF Parsing**: pdfplumber
- **Frontend**: Vanilla HTML/CSS/JS

---

## License

MIT
