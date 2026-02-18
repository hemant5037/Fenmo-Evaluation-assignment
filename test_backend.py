"""
Basic integration tests for the Expense Tracker API.
Run with: pytest test_backend.py -v
"""

import os
import tempfile

import pytest

import backend as backend_mod
from backend import app, init_db, _parse_amount


@pytest.fixture
def client():
    """Use a temporary database for tests."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    original_db = backend_mod.DATABASE
    backend_mod.DATABASE = db_path

    try:
        init_db()
        with app.test_client() as c:
            yield c
    finally:
        backend_mod.DATABASE = original_db
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_create_and_get_expense(client):
    """POST creates expense, GET returns it."""
    payload = {
        'amount': 150.50,
        'category': 'Food',
        'description': 'Lunch',
        'date': '2025-02-18',
    }
    r = client.post(
        '/expenses',
        json=payload,
        content_type='application/json',
    )
    assert r.status_code == 201
    data = r.get_json()
    assert 'id' in data
    assert data['amount'] == 150.50
    assert data['category'] == 'Food'
    assert data['description'] == 'Lunch'
    assert data['date'] == '2025-02-18'

    r2 = client.get('/expenses')
    assert r2.status_code == 200
    expenses = r2.get_json()
    assert len(expenses) == 1
    assert expenses[0]['amount'] == 150.50


def test_idempotency(client):
    """Identical POST retries return same expense without duplicating."""
    payload = {
        'amount': 99.99,
        'category': 'Transport',
        'description': 'Bus fare',
        'date': '2025-02-18',
    }
    r1 = client.post('/expenses', json=payload, content_type='application/json')
    assert r1.status_code == 201
    id1 = r1.get_json()['id']

    r2 = client.post('/expenses', json=payload, content_type='application/json')
    assert r2.status_code == 201
    id2 = r2.get_json()['id']
    assert id1 == id2

    r3 = client.get('/expenses')
    expenses = r3.get_json()
    assert len(expenses) == 1


def test_filter_by_category(client):
    """GET with category param filters results."""
    for cat, amt in [('Food', 10), ('Transport', 20), ('Food', 30)]:
        client.post('/expenses', json={
            'amount': amt, 'category': cat, 'description': 'x', 'date': '2025-02-18',
        }, content_type='application/json')

    r = client.get('/expenses?category=Food')
    assert r.status_code == 200
    expenses = r.get_json()
    assert len(expenses) == 2
    assert all(e['category'] == 'Food' for e in expenses)


def test_sort_date_desc(client):
    """GET with sort=date_desc returns newest first."""
    for date in ['2025-02-16', '2025-02-18', '2025-02-17']:
        client.post('/expenses', json={
            'amount': 1, 'category': 'X', 'description': 'x', 'date': date,
        }, content_type='application/json')

    r = client.get('/expenses?sort=date_desc')
    assert r.status_code == 200
    expenses = r.get_json()
    assert expenses[0]['date'] == '2025-02-18'
    assert expenses[1]['date'] == '2025-02-17'
    assert expenses[2]['date'] == '2025-02-16'


def test_validation_negative_amount(client):
    """POST rejects negative amount."""
    r = client.post('/expenses', json={
        'amount': -50,
        'category': 'Food',
        'description': 'x',
        'date': '2025-02-18',
    }, content_type='application/json')
    assert r.status_code == 400
    assert 'non-negative' in r.get_json().get('error', '').lower()


def test_validation_missing_date(client):
    """POST rejects missing date."""
    r = client.post('/expenses', json={
        'amount': 10,
        'category': 'Food',
        'description': 'x',
        'date': '',
    }, content_type='application/json')
    assert r.status_code == 400


def test_parse_amount():
    """Unit test for amount parsing."""
    assert _parse_amount(100)[0] == 10000
    assert _parse_amount(99.99)[0] == 9999
    assert _parse_amount('50.50')[0] == 5050
    assert _parse_amount(-1)[1] is not None
    assert _parse_amount(None)[1] is not None
    assert _parse_amount('abc')[1] is not None
