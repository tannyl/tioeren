# QA Test Tracker

## Service Status
- Database: Running (port 5432)
- Backend: Running (port 8000)
- Frontend: Running (port 5173)

## Test Results

| Test | Description | Status | Bugs Found |
|------|-------------|--------|------------|
| QA-001 | Landing page | PASSED | Minor: missing favicon, noisy 401 console logs, English tagline |
| QA-002 | Registration | FAILED | BUG-001, BUG-002, BUG-003 |
| QA-003 | Logout/Login | PENDING | - |
| QA-004 | Budget creation | PENDING | - |
| QA-005 | Account management | PENDING | - |
| QA-006 | Transaction creation | PENDING | - |
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
