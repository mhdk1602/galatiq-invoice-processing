import sqlite3
from contextlib import contextmanager
from typing import Optional
from .config import DATABASE_PATH


@contextmanager
def db_session():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock INTEGER, unit_price REAL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS vendors (name TEXT PRIMARY KEY, is_approved BOOLEAN, risk_score INTEGER DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS processed_invoices (invoice_number TEXT PRIMARY KEY, vendor TEXT, total REAL, status TEXT, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        
        cursor.execute('SELECT COUNT(*) FROM inventory')
        if cursor.fetchone()[0] == 0:
            cursor.executemany('INSERT INTO inventory VALUES (?, ?, ?)', [
                ('WidgetA', 15, 250.00), ('WidgetB', 10, 500.00),
                ('GadgetX', 5, 750.00), ('FakeItem', 0, 1000.00)
            ])
            cursor.executemany('INSERT OR IGNORE INTO vendors VALUES (?, ?, ?)', [
                ('Widgets Inc.', True, 0), ('Precision Parts Ltd.', True, 0),
                ('Gadgets Co.', True, 1), ('Fraudster LLC', False, 10), ('NoProd Industries', False, 5)
            ])


def check_stock(item_name: str, quantity: int) -> dict:
    with db_session() as conn:
        row = conn.cursor().execute('SELECT * FROM inventory WHERE item = ?', (item_name,)).fetchone()
        if not row:
            return {'available': False, 'reason': 'item_not_found', 'item': item_name, 'in_stock': 0}
        if row['stock'] == 0:
            return {'available': False, 'reason': 'zero_stock', 'item': item_name, 'in_stock': 0}
        if row['stock'] < quantity:
            return {'available': False, 'reason': 'insufficient_stock', 'item': item_name, 'in_stock': row['stock']}
        return {'available': True, 'reason': 'ok', 'item': item_name, 'in_stock': row['stock']}


def get_vendor_info(vendor_name: str) -> Optional[dict]:
    with db_session() as conn:
        row = conn.cursor().execute('SELECT * FROM vendors WHERE name LIKE ?', (f'%{vendor_name}%',)).fetchone()
        return dict(row) if row else None


def record_invoice(invoice_number: str, vendor: str, total: float, status: str):
    with db_session() as conn:
        conn.cursor().execute('INSERT OR REPLACE INTO processed_invoices (invoice_number, vendor, total, status) VALUES (?, ?, ?, ?)',
                              (invoice_number, vendor, total, status))
