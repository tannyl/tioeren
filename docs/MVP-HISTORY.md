# Tiøren MVP - Development History

This document archives the completed MVP development work (Phases 1-9).

## Completion Summary

- **Development tasks:** 36/36 completed
- **QA browser tests:** 8/8 passed
- **Bugs found during QA:** 11 (10 fixed, 1 deferred)
- **Deferred:** BUG-004 (sidebar nav links with empty budget IDs when no budget selected)

## Phase Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| 1. Infrastructure | Project setup, Docker, Alembic | 5 |
| 2. Authentication | User model, sessions, login/register | 8 |
| 3. Core Domain Models | Budget, Account, Category, Transaction, BudgetPost, Allocation | 6 |
| 4. Budget and Account APIs | CRUD endpoints + UI | 5 |
| 5. Transactions | Transaction endpoints + categorization UI | 4 |
| 6. Dashboard | Dashboard API + UI | 2 |
| 7. Forecast | Forecast calculation + chart UI | 3 |
| 8. Integration | Navigation, error handling, E2E tests | 3 |
| 9. QA Browser Testing | 8 browser tests via Playwright | 8 |

## Task History

| Task | Status | Review Result | Commit |
|------|--------|---------------|--------|
| TASK-001: Initialize backend project | Done | APPROVED | e0f72d9 |
| TASK-002: Initialize frontend project | Done | APPROVED | 704c58e |
| TASK-002b: Set up i18n translation system | Done | APPROVED | 976b9fa |
| TASK-003: Set up Docker Compose | Done | APPROVED | 28e1b98 |
| TASK-004: Configure Alembic migrations | Done | APPROVED | fb34896 |
| TASK-005: Implement User model and migration | Done | APPROVED | 9d63319 |
| TASK-006: Implement password hashing service | Done | APPROVED | fbf501c |
| TASK-007: Implement session management | Done | APPROVED | 851d033 |
| TASK-008: Implement registration endpoint | Done | APPROVED | d0ee901 |
| TASK-009: Implement login endpoint | Done | APPROVED | eed02e4 |
| TASK-010: Implement logout endpoint | Done | APPROVED | ceb7f06 |
| TASK-011: Create auth middleware | Done | APPROVED | 48303f0 |
| TASK-012: Create login/register UI pages | Done | APPROVED | 3ad4818 |
| TASK-013: Implement Budget model and migration | Done | APPROVED | ba15e0f |
| TASK-014: Implement Account model and migration | Done | APPROVED | 4635f56 |
| TASK-015: Implement Category model and migration | Done | APPROVED | 6f9a8e2 |
| TASK-016: Implement Transaction model and migration | Done | APPROVED | 40f0914 |
| TASK-017: Implement BudgetPost model and migration | Done | APPROVED | da3699d |
| TASK-018: Implement TransactionAllocation model and migration | Done | APPROVED | 1e469b1, 5675847 |
| TASK-019: Implement Budget CRUD endpoints | Done | APPROVED | 8ffaee2 |
| TASK-020: Implement Account CRUD endpoints | Done | APPROVED | d74f06b |
| TASK-021: Implement Category endpoints | Done | APPROVED | f26d71b, a23534b |
| TASK-022: Create Budget management UI | Done | APPROVED | ccddfd2 |
| TASK-023: Create Account management UI | Done | APPROVED | a3ffe7a |
| TASK-024: Implement Transaction endpoints | Done | APPROVED | 18edaec |
| TASK-025: Implement allocation endpoint | Done | APPROVED | b97c066 |
| TASK-026: Create Transaction list UI | Done | APPROVED | 46a39f4 |
| TASK-027: Create Transaction categorization modal | Done | APPROVED | b4a40b8 |
| TASK-028: Implement Dashboard data endpoint | Done | APPROVED | 6ad4e1f |
| TASK-029: Create Dashboard UI | Done | APPROVED | 5fb1727 |
| TASK-030: Implement Forecast calculation service | Done | APPROVED | 99d9cff |
| TASK-031: Implement Forecast endpoint | Done | APPROVED | 8b9cada |
| TASK-032: Create Forecast UI with chart | Done | APPROVED | d3ea18c |
| TASK-033: Implement Navigation and routing | Done | APPROVED | c7cd9ab |
| TASK-034: Implement Error handling and loading states | Done | APPROVED | ef2d03f |
| TASK-035: End-to-end testing | Done | APPROVED | dc426db |

## QA Test Results

| Test | Description | Result | Bugs Found |
|------|-------------|--------|------------|
| QA-001 | Landing page | PASSED | Minor: missing favicon, noisy 401 console logs, English tagline |
| QA-002 | Registration | PASSED | BUG-001 (fixed), BUG-002 (fixed), BUG-003 (fixed), BUG-004 (deferred) |
| QA-003 | Logout/Login | PASSED | - |
| QA-004 | Budget creation | PASSED | BUG-005 (fixed), BUG-006 (fixed) |
| QA-005 | Account management | PASSED | - |
| QA-006 | Transaction creation | PASSED | BUG-007 (fixed), BUG-008 (fixed) |
| QA-007 | Dashboard data | PASSED | BUG-009 (fixed), BUG-010 (fixed), BUG-011 (fixed) |
| QA-008 | Forecast | PASSED | - |

## QA Bug Log

### BUG-001: Database tables missing - migrations not run
- **Test:** QA-002 | **Severity:** CRITICAL | **Type:** infrastructure
- **Description:** PostgreSQL had no tables. Alembic migrations needed to be run.
- **Status:** FIXED (migrations re-run from scratch)

### BUG-002: Backend returns raw Python traceback on 500 errors
- **Test:** QA-002 | **Severity:** HIGH | **Type:** backend
- **Description:** Unhandled exceptions returned full Python traceback as plain text, leaking file paths and SQL queries.
- **Status:** FIXED

### BUG-003: Frontend doesn't handle non-JSON API responses
- **Test:** QA-002 | **Severity:** MINOR | **Type:** frontend
- **Description:** When API returns non-JSON (e.g., traceback), frontend showed raw JSON parse error.
- **Status:** FIXED

### BUG-004: Sidebar navigation links contain empty budget IDs
- **Test:** QA-002 | **Severity:** LOW | **Type:** frontend
- **Description:** On /budgets list page, sidebar renders links like `/budgets//transactions`.
- **Status:** DEFERRED (non-blocking)

### BUG-005: Dashboard endpoint 500 error - enum case mismatch
- **Test:** QA-004 | **Severity:** CRITICAL | **Type:** backend
- **Description:** SQLAlchemy Enum columns missing `values_callable=lambda x: [e.value for e in x]`. Sent uppercase names but PostgreSQL expected lowercase.
- **Status:** FIXED

### BUG-006: Untranslated error messages displayed to users
- **Test:** QA-004 | **Severity:** LOW | **Type:** frontend
- **Description:** Error messages displayed as raw i18n keys instead of translated text. Fixed in 14 locations across 10 files.
- **Status:** FIXED

### BUG-007: Transaction creation button is a stub
- **Test:** QA-006 | **Severity:** CRITICAL | **Type:** frontend
- **Description:** "Tilfoej transaktion" button only logged to console. No modal/form existed.
- **Status:** FIXED (full modal implemented)

### BUG-008: i18n initialization race condition causes blank screen
- **Test:** QA-006 | **Severity:** BLOCKER | **Type:** frontend
- **Description:** Root layout called `$_()` before locale initialized, causing blank white screen.
- **Status:** FIXED (hardcode loading text)

### BUG-009: Dashboard pending count not displayed - field name mismatch
- **Test:** QA-007 | **Severity:** MINOR | **Type:** frontend
- **Description:** TypeScript interface used `pending_transactions_count` but API returns `pending_count`.
- **Status:** FIXED

### BUG-010: Dashboard account shows literal `{account.currency}`
- **Test:** QA-007 | **Severity:** MINOR | **Type:** frontend
- **Description:** API returns `purpose` not `currency`. TypeScript interface had wrong field.
- **Status:** FIXED

### BUG-011: Empty fixed expenses shows "Loading..." instead of empty state
- **Test:** QA-007 | **Severity:** MINOR | **Type:** frontend
- **Description:** When no fixed expenses exist, showed loading text instead of empty state.
- **Status:** FIXED

## QA Infrastructure

### Service Startup Commands
1. Database: `docker compose up -d db`
2. Migrations: `DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" alembic upgrade head`
3. Backend: `DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" SECRET_KEY="test-secret-key" DEBUG=true TESTING=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
4. Frontend: `cd /workspace/ui && npm run dev -- --host 0.0.0.0`
5. Verify: `curl http://localhost:8000/api/health`

### QA Agent Mapping

| Task Type | Agent | Description |
|-----------|-------|-------------|
| qa (browser test) | general-purpose | Tests via Playwright MCP, follows qa-browser-tester.md |
| frontend (fix) | frontend-implementer | Fixes frontend bugs |
| backend (fix) | backend-implementer | Fixes backend bugs |
| review | reviewer | Reviews code fixes |
