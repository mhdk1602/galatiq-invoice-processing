import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed, use system env vars

PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_PATH = PROJECT_ROOT / "inventory.db"

XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = "grok-4-1-fast-reasoning"

HIGH_VALUE_THRESHOLD = 10000
FRAUD_KEYWORDS = ["urgent", "immediate", "wire transfer", "penalty", "penalties"]

MAX_INVOICE_AMOUNT = 500000
MAX_ITEMS_PER_INVOICE = 50
MAX_INPUT_SIZE = 1024 * 1024
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.json', '.csv', '.xml'}
BLOCKED_VENDORS = ["Fraudster LLC", "Scam Corp", "Fake Industries"]
MIN_CONFIDENCE_THRESHOLD = 0.6
