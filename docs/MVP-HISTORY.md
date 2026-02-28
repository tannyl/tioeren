# Tiøren - Development History

This document archives completed development work.

## MVP Summary

- **Development tasks:** 36/36 completed
- **QA browser tests:** 8/8 passed
- **Bugs found during QA:** 11 (all fixed)

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
2. Migrations: `DATABASE_URL="postgresql://tioeren:tioeren@localhost:5432/tioeren" alembic upgrade head`
3. Backend: `DATABASE_URL="postgresql://tioeren:tioeren@localhost:5432/tioeren" SECRET_KEY="test-secret-key" DEBUG=true TESTING=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
4. Frontend: `cd /workspace/ui && npm run dev -- --host 0.0.0.0`
5. Verify: `curl http://localhost:8000/api/health`

### QA Agent Mapping

| Task Type | Agent | Description |
|-----------|-------|-------------|
| qa (browser test) | general-purpose | Tests via Playwright MCP, follows qa-browser-tester.md |
| frontend (fix) | frontend-implementer | Fixes frontend bugs |
| backend (fix) | backend-implementer | Fixes backend bugs |
| review | reviewer | Reviews code fixes |

---

## Post-MVP Development History

Completed after MVP, during post-MVP backlog work.

### Post-MVP Task History

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-042 | Fix tioren -> tioeren transliteration | 2026-02-05 | 4865843 |
| QA-009 | Verify app functionality after rename | 2026-02-05 | - |
| QA-010 | Fix auth errors (server error + English messages) | 2026-02-06 | f6f2e7f |
| TASK-043 | Remove landing page, redirect to login | 2026-02-07 | a6f38f8 |
| TASK-044 | Implement security testing agent | 2026-02-07 | c34c8a2 |
| TASK-045 | Budget Post API - Backend CRUD | 2026-02-08 | 37ce3fa |
| TASK-046 | Budget Post UI - Frontend management | 2026-02-08 | 816b2c3 |

### Budget Post Enhancement Tasks (Superseded by TASK-061+)

These implemented the original period-based model, later replaced by the active/archived split model.

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-052 | Recurrence occurrence expansion | 2026-02-11 | a8ecba0 |
| TASK-053 | Account binding UI | 2026-02-11 | fb79d0c |
| TASK-054 | New recurrence model (date-based + period-based) | 2026-02-11 | f2c5f35 |
| TASK-055 | Amount patterns (beloebsmoenstre) | 2026-02-12 | 9257a4f |
| TASK-059 | Revised category/budget post model | 2026-02-12 | 83fa1f6 |
| TASK-060 | Derive budget post period from amount patterns | 2026-02-12 | 3a224f5 |

### Budget Post Rebuild Tasks (Backend)

New active/archived split model per updated SPEC.md (2026-02-13).

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-061 | Backend - New budget post data model | 2026-02-14 | b7d7b01 |
| TASK-062 | Backend - Budget post service and schemas rebuild | 2026-02-14 | 33bd940 |
| TASK-063 | Backend - Transaction allocation to patterns/occurrences | 2026-02-14 | 178c849 |
| TASK-064 | Backend - Forecast service update | 2026-02-14 | b2a2a2c |

### Security Audit Results

Full codebase security audit (2026-02-07).

| Task | Description | Result |
|------|-------------|--------|
| SEC-001 | Static Analysis (SAST) - Semgrep | PASS - 826 rules, 0 findings |
| SEC-002 | Dependency Scan (SCA) - pip-audit + npm audit | 6 vulns (2 moderate, 4 low) - dev-time deps only |
| SEC-003 | Authentication Testing | 1 MEDIUM (no rate limiting), 3 LOW |
| SEC-004 | Authorization (BOLA/IDOR) | PASS - 18/18 tests passed |
| SEC-005 | Input Validation (Injection) | PASS - parameterized queries + auto-escaping |
| SEC-006 | API Security & Business Logic | 8 findings (2 HIGH, 5 MEDIUM, 1 LOW) |

### Post-MVP Bug Fixes

| Bug | Severity | Description | Fixed |
|-----|----------|-------------|-------|
| BUG-004 | LOW | Sidebar nav links contain empty budget IDs | 2026-02-06 |
| BUG-005 | LOW | Root path shows useless page for logged-in users | 2026-02-06 |
| BUG-006 | CRITICAL | Infinite loop when clicking transaction | 2026-02-07 |
| BUG-007 | MEDIUM | Budget dropdown doesn't update dashboard | 2026-02-07 |
| BUG-008 | LOW | Budget dropdown shows "Indlaeser..." after creating budget | 2026-02-07 |
| BUG-009 | MEDIUM | Transactions/Settings don't update when switching budgets | 2026-02-08 |
| BUG-011 | MEDIUM | Category grouping collision on list page | FIXED |
| BUG-013 | HIGH | Budget Post creation fails silently | NOT_REPRODUCED |
| BUG-014 | MEDIUM | Initial route load returns 404 | NOT_REPRODUCED |
| BUG-015 | MEDIUM | Cannot create budget post with 0 kr minimum | FIXED |
| BUG-016 | LOW | Generic error for duplicate budget post constraint | FIXED |
| BUG-019 | LOW | Pattern editor same error for missing amount/start date | 2026-02-14 |
| BUG-020 | MEDIUM | Pattern editor allows saving without accounts | 2026-02-14 |
| BUG-021 | MEDIUM | Incomplete pattern shows "[object Object]" error | 2026-02-14 |
| BUG-022 | HIGH | Amount field integer overflow causes traceback leak | 2026-02-14 |
| BUG-024 | MEDIUM | Timeline chart skips day at DST transition | 2026-02-15 |

### Budget Post UI Rebuild (Frontend)

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-065 | Frontend - Budget post UI rebuild | 2026-02-14 | b99aec8 |
| TASK-067 | Restructure amount pattern editor + backend validation | 2026-02-14 | 195fb17 |
| TASK-068 | Add period_monthly recurrence type | 2026-02-14 | 71f5915 |
| TASK-069 | Remove "Hver N." hints from interval fields | 2026-02-14 | 3b516fb |
| TASK-070 | Bank day utility + bank_day_adjustment | 2026-02-14 | 9ed957d |
| TASK-071 | Expand relative weekday positions (1st-4th + last) | 2026-02-14 | a2cca06 |
| TASK-072 | Monthly/yearly bank day recurrence types | 2026-02-15 | faa0774 |
| TASK-073 | Bank day adjustment - crossing month boundaries | 2026-02-15 | ef35f2c |

### Budget Post UX Improvements

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-074 | Fix spacing between empty state and button | 2026-02-15 | a5fb9fd |
| TASK-075 | Pattern editor as sub-view in modal | 2026-02-15 | 507f34e |
| TASK-076 | Natural language pattern descriptions | 2026-02-15 | a0d671d |
| TASK-077 | Locale-aware date formatting utility | 2026-02-15 | 22374a6 |
| TASK-078 | Occurrence timeline chart in modal | 2026-02-15 | 12527b8 |
| TASK-079 | Full month names in pattern dropdowns | 2026-02-15 | 5cd12a2 |
| TASK-080 | Fix security agent scope | 2026-02-15 | 27cefcd |
| TASK-081 | Refine pattern card descriptions | 2026-02-15 | 957e7ab |
| TASK-082 | Fix weekly n>1 description text | 2026-02-15 | 3efaebd |
| TASK-083 | Bank day adjustment as separate sentence | 2026-02-15 | 3efaebd |
| TASK-084 | Non-bank-days API endpoint | 2026-02-17 | a226228 |
| TASK-085 | Integrate OccurrenceTimeline with API | 2026-02-17 | 96eb522 |
| TASK-086 | Remove unused dependencies | 2026-02-17 | a574900 |

### OccurrenceTimeline Chart Improvements

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-087 | OccurrenceTimeline i18n - remove hardcoded Danish locale | 2026-02-17 | 2c07777 |
| TASK-088 | Fix axis text blinking on chart navigation | 2026-02-17 | 2c07777 |
| TASK-089 | Y-axis range - adapt to visible window | 2026-02-17 | 2c07777 |
| TASK-090 | Fix bar height animation asymmetry | 2026-02-17 | 2c07777 |
| TASK-091 | Logarithmic Y-axis for large value ranges | 2026-02-17 | 2c07777 |
| TASK-092 | Dynamic pattern color generation | 2026-02-17 | 2c07777 |
| TASK-093 | Archive completed tasks | 2026-02-17 | - |
| TASK-094 | Auto-fill today's date for new date-based patterns | 2026-02-17 | 1beebcb |
| BUG-025 | Recurrence dates shift (interval > 1 phase bug) | 2026-02-17 | 1beebcb |
| BUG-026 | Y-axis max resets to 10 during loading | 2026-02-17 | 1beebcb |
| BUG-027-030 | Chart animation/opacity/fade-in fixes | 2026-02-18 | 338f55f |
| BUG-031 | Pattern colors unstable across dialog | 2026-02-22 | 02be741 |

### Bank Day & Pattern UX

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-095 | Bank day accumulation option | 2026-02-19 | f2f35e2 |
| TASK-096 | Pattern color indicators on cards | 2026-02-19 | d9a8b44 |
| TASK-097-099 | Clickable pattern/budget post cards + remove back button | 2026-02-19 | 562b72a |
| TASK-106 | Clone amount pattern button | 2026-02-22 | bfdfe26 |

### Category → category_path Refactoring

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-100 | Opdater SPEC.md med ny category_path model | 2026-02-19 | aef5e26 |
| TASK-101 | Backend - Fjern Category, tilføj category_path | 2026-02-19 | 2d12a71 |
| TASK-102 | Backend - Opdater tests for category_path | 2026-02-19 | a6d58b4 |
| TASK-103 | Frontend - Budgetpost-trævisning og kategoriseringsmodal | 2026-02-19 | 9ce40aa |
| TASK-104 | Frontend - Kategori-sti input med autocomplete | 2026-02-19 | 190eceb |
| TASK-105 | Frontend - Breadcrumb chip input til kategori-sti | 2026-02-20 | 53e5fce |

### Budget Post & Account Model Redesign

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-107 | Opdater SPEC.md med ny konto- og budgetpost-model | 2026-02-22 | 7685ade |
| TASK-108 | Backend - Opdater Account model og enum | 2026-02-22 | f0d2259 |
| TASK-109 | Backend - Opdater BudgetPost model | 2026-02-22 | 8a242c6 |
| TASK-110 | Backend - Opdater AmountPattern kontobinding | 2026-02-22 | 746e03e |
| TASK-111 | Backend - Opdater tests for ny model | 2026-02-22 | efb07c3 |
| TASK-112 | Frontend - Opdater BudgetPostModal | 2026-02-23 | 654872e |
| TASK-113 | Frontend - Opdater kontotyper og account forms | 2026-02-23 | dce926c |
| TASK-114 | Frontend - Opdater budget post list visning | 2026-02-22 | cb4437c |

### Credit Limit & Kontobinding Rettelser

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-115 | Backend - credit_limit fortegnskonvention | 2026-02-23 | efbf843 |
| TASK-116 | Frontend - credit_limit checkbox UX | 2026-02-23 | b65b534 |
| TASK-117 | Backend + SPEC - kontobinding gensidig eksklusivitet | 2026-02-23 | dd23ffb |
| TASK-118 | Frontend - kontobinding segment control | 2026-02-23 | 3cf6522 |

### Container Model Redesign

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-119 | Update SPEC.md with container model | 2026-02-24 | 2831a21 |
| TASK-120-125 | Backend - migration + model + services + tests | 2026-02-25 | 716d487 |
| TASK-126-130,132 | Frontend - API client + modals + pages | 2026-02-25 | 70838d7 |
| TASK-131,133-135 | Frontend - Navigation + container list pages | 2026-02-25 | 2d9d6e3 |

### Remove BudgetPostType & Accumulate Restriction

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-136-137 | Remove BudgetPostType backend + frontend | 2026-02-26 | f03508c |
| TASK-138-139 | Restrict accumulate to expense direction | 2026-02-26 | 3ca6c7d |

### Container Binding & Hierarchy

| Task | Description | Completed | Commit |
|------|-------------|-----------|--------|
| TASK-140 | Strict container_ids on amount patterns | 2026-02-27 | 34c2f7f |
| TASK-141 | Tre-delt beholder-vælger i BudgetPostModal | 2026-02-27 | 0c63eb2 |
| TASK-142 | Rename "beholdere" → "pengebeholdere" | 2026-02-27 | bddb65b |
| TASK-143 | Update SPEC.md with container inheritance rules | 2026-02-27 | c78c477 |
| TASK-144 | Backend - hierarchy-aware container validation | 2026-02-27 | 9337503 |
| TASK-145 | Frontend - parent-aware container selection | 2026-02-27 | 8252856 |
| TASK-146 | Pattern card container display + snapshot sync | 2026-02-28 | b766a05 |

### Post-OccurrenceTimeline Bug Fixes

| Bug | Severity | Description | Commit |
|-----|----------|-------------|--------|
| BUG-037 | MEDIUM | Container-pattern UX: orphaned refs + missing guard | e1ae08f |
| BUG-038 | MEDIUM | Null container_ids on legacy patterns + English error | b021720 |
| BUG-039 | LOW | via_container_id validation error hardcoded English | 21092cd |
| BUG-040 | MEDIUM | via_container_id not cleared on mode switch | 21092cd |
