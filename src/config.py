import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_PATH = PROJECT_ROOT / "inventory.db"

XAI_API_KEY = os.getenv("XAI_API_KEY")  # Set via: export XAI_API_KEY=your_key
XAI_MODEL = "grok-4-1-fast-reasoning"

HIGH_VALUE_THRESHOLD = 10000
FRAUD_KEYWORDS = ["urgent", "immediate", "wire transfer", "penalty", "penalties"]
