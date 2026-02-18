# Expense Tracker

A minimal full-stack personal finance tool for recording and reviewing expenses. Built for production-like quality under realistic conditions (unreliable networks, refreshes, retries).

## Quick Start

```bash
# Backend
cd /path/to/project
python3 -m venv venv
source venv/bin/activate   # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python backend.py

# Frontend (in another terminal)
cd frontend
npm install
npm start
```

Open http://localhost:3000. The frontend proxies API requests to the backend (port 5000).

## Features

- **Create expenses**: Amount (₹), category, description, date
- **View list**: Table of all expenses
- **Filter by category**: Dropdown to show specific categories
- **Sort by date**: Newest first (default) or oldest first
- **Total**: Sum of currently visible expenses (e.g. "Total: ₹X")

## API

| Method | Endpoint   | Description                                    |
|--------|------------|------------------------------------------------|
| POST   | /expenses  | Create expense. Body: `amount`, `category`, `description`, `date` |
| GET    | /expenses  | List expenses. Query: `category`, `sort=date_desc` or `sort=date_asc` |

## Persistence

**SQLite** is used for persistence because:

- No separate server or setup
- ACID transactions for data integrity
- Suitable for single-user / small deployments
- Easy to migrate to PostgreSQL later if needed

Data is stored in `expenses.db` in the project root. Amounts are stored as **integer paise** (1 ₹ = 100 paise) to avoid floating-point precision issues with money.

## Key Design Decisions

1. **Idempotency for POST**  
   Duplicate requests (retries, double-clicks, page reloads) are handled by hashing the request body. Same body → same response, no duplicate rows. Optional `Idempotency-Key` header is also supported.

2. **Money as integers**  
   Amounts are stored in paise to prevent rounding errors (e.g. 0.1 + 0.2 ≠ 0.3 with floats). API accepts and returns rupees; conversion happens at the boundary.

3. **Server-side filter and sort**  
   GET supports `category` and `sort` query params so filtering and sorting scale with large datasets. Frontend uses these params instead of client-side filtering.

4. **Validation**  
   Basic validation: non-negative amounts, required fields, valid date format (YYYY-MM-DD).

## Trade-offs (Timebox)

- **No summary view**: Total per category was not implemented to keep scope small.
- **Simple tests**: Integration tests for the API only; no frontend or E2E tests.
- **Minimal UI**: No rich animations or advanced UX; focus on correctness and clarity.
- **No auth**: Assumes single-user or internal use; no login/session handling.

## Intentionally Omitted

- User authentication and multi-tenancy
- Edit or delete expenses
- Pagination (assumes small datasets)
- CSV/export
- Mobile-specific UI

## Tests

```bash
source venv/bin/activate
pytest test_backend.py -v
```

## Project Structure

```
.
├── backend.py        # Flask API
├── test_backend.py   # API tests
├── requirements.txt
├── expenses.db       # SQLite DB (created on first run)
└── frontend/         # React app
    ├── src/
    │   ├── App.js
    │   ├── App.css
    │   └── index.js
    └── package.json
```
