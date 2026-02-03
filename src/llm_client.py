import json
import re
from typing import Optional
from xai_sdk import Client
from xai_sdk.chat import system, user
from .config import XAI_API_KEY, XAI_MODEL


class GrokClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.client = Client(api_key=api_key or XAI_API_KEY)
        self.model = model or XAI_MODEL
    
    def chat(self, messages: list[dict]) -> str:
        xai_messages = [system(m['content']) if m.get('role') == 'system' else user(m['content']) for m in messages]
        return self.client.chat.create(model=self.model, messages=xai_messages).sample().content
    
    def chat_json(self, messages: list[dict]) -> dict:
        if messages[0].get('role') == 'system':
            messages[0]['content'] += "\n\nRespond ONLY with valid JSON."
        response = self.chat(messages)
        try:
            cleaned = response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('```')[1].lstrip('json')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(match.group()) if match else {}
    
    def extract_invoice(self, text: str) -> dict:
        return self.chat_json([
            {"role": "system", "content": "Extract invoice data as JSON: invoice_number, vendor, date, due_date, items (list of {item_name, quantity, unit_price}), total, fraud_indicators (list)."},
            {"role": "user", "content": text}
        ])
    
    def analyze_approval(self, invoice_data: dict, issues: list, context: str) -> dict:
        return self.chat_json([
            {"role": "system", "content": "Analyze invoice for approval. Use reflection: 1) initial_assessment, 2) critique your assessment, 3) final_decision with {approved, confidence, reasoning, requires_human_review}."},
            {"role": "user", "content": f"Invoice: {json.dumps(invoice_data)}\nIssues: {json.dumps(issues)}\nContext: {context}"}
        ])


_client: Optional[GrokClient] = None

def get_llm_client() -> GrokClient:
    global _client
    if _client is None:
        _client = GrokClient()
    return _client
