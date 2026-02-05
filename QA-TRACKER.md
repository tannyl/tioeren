# QA Test Tracker

## Service Status
- Database: Running (port 5432)
- Backend: Running (port 8000)
- Frontend: Running (port 5173)

## Test Results

| Test | Description | Status | Bugs Found |
|------|-------------|--------|------------|
| QA-001 | Landing page | PASSED | Minor: missing favicon, noisy 401 console logs, English tagline |
| QA-002 | Registration | PASSED | BUG-001 (fixed), BUG-002 (fixed), BUG-003 (fixed), BUG-004 (low, deferred) |
| QA-003 | Logout/Login | PASSED | - |
| QA-004 | Budget creation | PASSED | BUG-005 (fixed), BUG-006 (fixed) |
| QA-005 | Account management | PASSED | - |
| QA-006 | Transaction creation | FAILED | BUG-007 (critical) |
| QA-007 | Dashboard data | PENDING | - |
| QA-008 | Forecast | PENDING | - |

## Bug Log

### BUG-001: Database tables missing - migrations not run
- **Test:** QA-002
- **Severity:** CRITICAL
- **Type:** infrastructure
- **Description:** The PostgreSQL database has no tables. `SELECT FROM users` fails with `UndefinedTable: relation "users" does not exist`. Alembic migrations need to be run.
- **Fix status:** FIXED (migrations re-run from scratch)

### BUG-002: Backend returns raw Python traceback on 500 errors
- **Test:** QA-002
- **Severity:** HIGH
- **Type:** backend
- **Description:** When an unhandled exception occurs, FastAPI returns the full Python traceback as plain text instead of a JSON error response. Leaks file paths, SQL queries, and internal details. Should return `{"detail": "Internal server error"}`.
- **Fix status:** FIXED

### BUG-003: Frontend doesn't handle non-JSON API responses
- **Test:** QA-002
- **Severity:** MINOR
- **Type:** frontend
- **Description:** When the API returns non-JSON (e.g., a traceback), the frontend shows `Unexpected token 'T', "Traceback "... is not valid JSON` instead of a user-friendly error message.
- **Fix status:** FIXED

### BUG-004: Sidebar navigation links contain empty budget IDs
- **Test:** QA-002
- **Severity:** LOW
- **Type:** frontend
- **Description:** On the /budgets list page (no budget selected), sidebar renders links with empty budget IDs like `/budgets//transactions`. Should hide or disable budget-specific nav when no budget context.
- **Fix status:** DEFERRED (non-blocking)

### BUG-005: Dashboard endpoint 500 error - enum case mismatch
- **Test:** QA-004
- **Severity:** CRITICAL
- **Type:** backend
- **Description:** `GET /api/budgets/{id}/dashboard` returns 500 Internal Server Error. Root cause: SQLAlchemy `Enum` columns for `TransactionStatus`, `AccountPurpose`, and `AccountDatasource` are missing `values_callable=lambda x: [e.value for e in x]`. Without it, SQLAlchemy sends uppercase enum names (e.g., `UNCATEGORIZED`) but PostgreSQL expects lowercase values (e.g., `uncategorized`). The `BudgetPostType` model has the correct `values_callable` but the other three don't.
- **Fix:** Add `values_callable` parameter to all three enum columns in `api/models/account.py` and `api/models/transaction.py`.
- **Fix status:** FIXED

### BUG-006: Untranslated error messages displayed to users
- **Test:** QA-004
- **Severity:** LOW
- **Type:** frontend
- **Description:** Error messages from API are i18n translation keys (e.g., `error.unexpectedServerError`) but components displayed them raw without translating via `$_()`. The translation keys existed in `da.json` but were never looked up.
- **Fix:** Wrapped `err.message` with `$_()` / `get(_)()` in all 14 error handling locations across 10 files.
- **Fix status:** FIXED

### BUG-007: Transaction creation button is a stub - no form/modal implemented
- **Test:** QA-006
- **Severity:** CRITICAL
- **Type:** frontend
- **Description:** The "Tilføj transaktion" button on the transactions page only logs to console (`console.log('Add transaction')`). No transaction creation modal or form exists. The backend `POST /api/budgets/{id}/transactions` endpoint works, but the frontend never calls it. Missing: `createTransaction` API client function, transaction creation modal component, button wiring.
- **Fix:** Implement transaction creation modal with date, amount, description, account selector fields. Add `createTransaction` to API client. Wire button to show modal.
- **Fix status:** IN PROGRESS
