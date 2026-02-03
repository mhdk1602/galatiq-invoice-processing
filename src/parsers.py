import csv
import json
import re
from pathlib import Path
from .models import Invoice, LineItem


def parse_invoice_file(file_path: str) -> tuple[str, str]:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        txt_path = path.with_suffix('.txt')
        if txt_path.exists():
            return txt_path.read_text(), 'txt'
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join(p.extract_text() or '' for p in pdf.pages), 'pdf'
        except ImportError:
            return f"[PDF: {file_path}]", 'pdf'
    return path.read_text(), suffix.lstrip('.')


def parse_json_invoice(content: str, source: str = None) -> Invoice:
    data = json.loads(content)
    vendor = data.get('vendor', '')
    if isinstance(vendor, dict):
        vendor = vendor.get('name', '')
    items = [LineItem(i.get('item', i.get('item_name', '')), i.get('quantity', 0), i.get('unit_price', 0))
             for i in data.get('line_items', data.get('items', []))]
    return Invoice(data.get('invoice_number', 'UNKNOWN'), vendor, data.get('date'), data.get('due_date'),
                   items, data.get('subtotal'), data.get('tax_amount', data.get('tax')), data.get('total', 0),
                   data.get('currency', 'USD'), data.get('payment_terms'), content, source)


def parse_csv_invoice(content: str, source: str = None) -> Invoice:
    data, items, current = {}, [], {}
    for row in csv.reader(content.strip().split('\n')):
        if len(row) < 2: continue
        field, value = row[0].strip(), row[1].strip()
        if field == 'item':
            if current: items.append(current)
            current = {'name': value}
        elif field == 'quantity': current['qty'] = int(value) if value else 0
        elif field == 'unit_price': current['price'] = float(value) if value else 0
        else: data[field] = value
    if current: items.append(current)
    line_items = [LineItem(i['name'], i.get('qty', 0), i.get('price', 0)) for i in items]
    return Invoice(data.get('invoice_number', 'UNKNOWN'), data.get('vendor', ''), data.get('date'),
                   data.get('due_date'), line_items, None, float(data.get('tax', 0)) if data.get('tax') else 0,
                   float(data.get('total', 0)) if data.get('total') else 0, 'USD', data.get('payment_terms'), content, source)


def parse_text_invoice(content: str, source: str = None) -> Invoice:
    inv_match = re.search(r'(?:invoice\s*(?:#|number)?:?\s*)([A-Z]*-?\d+)', content, re.I)
    invoice_number = inv_match.group(1) if inv_match else 'UNKNOWN'
    if invoice_number.isdigit(): invoice_number = f'INV-{invoice_number}'
    
    vendor_match = re.search(r'(?:vendor|vndr|from):?\s*([^\n]+)', content, re.I)
    vendor = vendor_match.group(1).strip() if vendor_match else 'Unknown'
    
    date_match = re.search(r'(?:^date|^dt):?\s*(\S+)', content, re.I | re.M)
    due_match = re.search(r'(?:due\s*(?:date)?):?\s*(\S+)', content, re.I)
    total_match = re.search(r'(?:total|amount):?\s*\$?([\d,]+\.?\d*)', content, re.I)
    
    items = []
    for pattern in [r'([A-Za-z]\w+)\s+qty:?\s*(\d+)\s+.*?\$?([\d,]+\.?\d*)',
                    r'([A-Za-z]\w+)\s+x?(\d+)\s+\$?([\d,]+\.?\d*)\s*(?:each|ea)?']:
        for m in re.findall(pattern, content, re.I):
            if m[0].lower() not in ['total', 'subtotal', 'tax', 'amount']:
                items.append(LineItem(m[0], int(m[1]), float(m[2].replace(',', ''))))
    
    return Invoice(invoice_number, vendor, date_match.group(1) if date_match else None,
                   due_match.group(1) if due_match else None, items, None, None,
                   float(total_match.group(1).replace(',', '')) if total_match else 0, 'USD', None, content, source)


def pre_parse_invoice(file_path: str) -> tuple[Invoice, str, str]:
    content, fmt = parse_invoice_file(file_path)
    if fmt == 'json': return parse_json_invoice(content, file_path), content, fmt
    if fmt == 'csv': return parse_csv_invoice(content, file_path), content, fmt
    return parse_text_invoice(content, file_path), content, fmt
