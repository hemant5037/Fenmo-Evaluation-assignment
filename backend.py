"""
Expense Tracker API - Flask backend with SQLite persistence.

Handles retries via idempotency keys. Uses integer paise for money to avoid
floating-point precision errors.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
CORS(app)
DATABASE = 'expenses.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
        )
        has_expenses = cursor.fetchone() is not None
        needs_migration = False
        if has_expenses:
            cursor.execute('PRAGMA table_info(expenses)')
            columns = [c[1] for c in cursor.fetchall()]
            if 'amount' in columns and 'amount_paise' not in columns:
                needs_migration = True
                cursor.execute('ALTER TABLE expenses RENAME TO expenses_old')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_paise INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idempotency_key TEXT PRIMARY KEY,
                expense_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (expense_id) REFERENCES expenses(id)
            )
        ''')
        if needs_migration:
            cursor.execute('''
                INSERT INTO expenses (id, amount_paise, category, description, date, created_at)
                SELECT id, CAST(ROUND(amount * 100) AS INTEGER), category,
                       COALESCE(description, ''), date, created_at
                FROM expenses_old
            ''')
            cursor.execute('DROP TABLE expenses_old')
        conn.commit()


def _parse_amount(value):
    """Parse amount to paise (integer). Rejects negative and invalid values."""
    if value is None:
        return None, 'Amount is required'
    try:
        # Support both string and number input
        if isinstance(value, (int, float)):
            dec = Decimal(str(value))
        else:
            dec = Decimal(str(value).strip())
        if dec < 0:
            return None, 'Amount must be non-negative'
        # Round to 2 decimal places, then convert to paise
        dec = dec.quantize(Decimal('0.01'))
        paise = int(dec * 100)
        return paise, None
    except (InvalidOperation, ValueError, TypeError):
        return None, 'Amount must be a valid number'


def _row_to_expense(row):
    """Convert DB row to API response object. Amount in rupees."""
    return {
        'id': row['id'],
        'amount': row['amount_paise'] / 100,
        'category': row['category'],
        'description': row['description'],
        'date': row['date'],
        'created_at': row['created_at'],
    }


def _get_idempotency_key():
    """Get idempotency key from header or derive from request body for retries."""
    key = request.headers.get('Idempotency-Key')
    if key:
        return key.strip()
    # Fallback: hash of request body for identical retries (e.g. page reload resubmit)
    body = request.get_data(as_text=True)
    if body:
        return hashlib.sha256(body.encode()).hexdigest()
    return None


@app.route('/expenses', methods=['POST'])
def create_expense():
    # When deployed (e.g. via gunicorn), __main__ doesn't run.
    # Ensure tables exist before handling requests.
    init_db()
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    amount_raw = data.get('amount')
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()
    date = (data.get('date') or '').strip()

    # Validation
    amount_paise, amount_err = _parse_amount(amount_raw)
    if amount_err:
        return jsonify({'error': amount_err}), 400
    if not category:
        return jsonify({'error': 'Category is required'}), 400
    if not date:
        return jsonify({'error': 'Date is required'}), 400
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Date must be in YYYY-MM-DD format'}), 400

    idempotency_key = _get_idempotency_key()
    created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    with get_db() as conn:
        cursor = conn.cursor()
        if idempotency_key:
            cursor.execute(
                'SELECT expense_id FROM idempotency_keys WHERE idempotency_key = ?',
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    'SELECT * FROM expenses WHERE id = ?',
                    (existing['expense_id'],)
                )
                row = cursor.fetchone()
                if row:
                    return jsonify(_row_to_expense(row)), 201

        cursor.execute(
            '''INSERT INTO expenses (amount_paise, category, description, date, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (amount_paise, category, description, date, created_at)
        )
        expense_id = cursor.lastrowid
        if idempotency_key:
            cursor.execute(
                'INSERT OR REPLACE INTO idempotency_keys (idempotency_key, expense_id, created_at) VALUES (?, ?, ?)',
                (idempotency_key, expense_id, created_at)
            )
        conn.commit()

        cursor.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        return jsonify(_row_to_expense(row)), 201


@app.route('/expenses', methods=['GET'])
def get_expenses():
    init_db()
    category = request.args.get('category', '').strip()
    sort = request.args.get('sort', '').strip()

    query = 'SELECT * FROM expenses'
    params = []
    if category:
        query += ' WHERE category = ?'
        params.append(category)
    if sort == 'date_asc':
        query += ' ORDER BY date ASC, created_at ASC'
    else:
        query += ' ORDER BY date DESC, created_at DESC'  # default newest first

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return jsonify([_row_to_expense(r) for r in rows])


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
