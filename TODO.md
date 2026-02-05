# Tiøren MVP - Task List

This file tracks all development tasks for the Tiøren MVP. Tasks are executed sequentially with dependencies respected.

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked (see WORKFLOW-STATE.md)

---

## Phase 1: Infrastructure

- [x] **TASK-001**: Initialize backend project
  - Description: Create FastAPI project with directory structure (api/models, api/schemas, api/routes, api/services, api/deps, api/utils). Set up pyproject.toml and requirements.txt.
  - Type: backend
  - Dependencies: none
  - Acceptance: `python -m pytest` runs without import errors, basic health endpoint works

- [x] **TASK-002**: Initialize frontend project
  - Description: Create Svelte project in ui/ directory with SvelteKit. Set up directory structure (lib/components, lib/stores, lib/api, routes). Configure CSS custom properties for theming.
  - Type: frontend
  - Dependencies: none
  - Acceptance: `npm run dev` starts development server, base layout renders

- [x] **TASK-002b**: Set up i18n translation system
  - Description: Install/configure i18n for Svelte (svelte-i18n or lightweight custom). Create translation file structure in ui/src/lib/i18n/. Add Danish locale (da.json) with common keys. Create helper function for translations.
  - Type: frontend
  - Dependencies: TASK-002
  - Acceptance: Translation function returns Danish text, locale structure ready for future languages

- [x] **TASK-003**: Set up Docker Compose
  - Description: Create docker-compose.yml with services: api (FastAPI), ui (Nginx serving built Svelte), db (PostgreSQL), proxy (Caddy for reverse proxy). Configure networking and volumes.
  - Type: infrastructure
  - Dependencies: TASK-001, TASK-002
  - Acceptance: `docker compose up` starts all services, API reachable at /api/*, UI at /

- [x] **TASK-004**: Configure Alembic migrations
  - Description: Initialize Alembic for PostgreSQL, configure alembic.ini and env.py. Create initial empty migration to verify setup.
  - Type: backend
  - Dependencies: TASK-001
  - Acceptance: `alembic upgrade head` runs successfully, `alembic revision` creates new migration files

---

## Phase 2: Authentication

- [x] **TASK-005**: Implement User model and migration
  - Description: Create User SQLAlchemy model with fields: id (UUID), email (unique), password_hash, email_verified (bool), created_at, updated_at, deleted_at. Create Alembic migration.
  - Type: backend
  - Dependencies: TASK-004
  - Acceptance: Migration runs, User model can be imported and instantiated

- [x] **TASK-006**: Implement password hashing service
  - Description: Create auth service using passlib with bcrypt. Functions: hash_password(plain) -> hash, verify_password(plain, hash) -> bool. Password requirements: min 12 chars, max 128 chars.
  - Type: backend
  - Dependencies: TASK-005
  - Acceptance: Unit tests for hash/verify pass, password requirements enforced

- [x] **TASK-007**: Implement session management
  - Description: Create Session model (id UUID, user_id FK, created_at, expires_at, last_activity). Service: create_session, validate_session, invalidate_session, invalidate_all_user_sessions. 30-day sliding expiration.
  - Type: backend
  - Dependencies: TASK-005
  - Acceptance: Session CRUD tests pass, expiration logic works

- [x] **TASK-008**: Implement registration endpoint
  - Description: POST /api/auth/register - accepts email, password. Validates input, creates user, creates session. Returns session token. Email verification stubbed for MVP.
  - Type: backend
  - Dependencies: TASK-006, TASK-007
  - Acceptance: Can register user via API, returns valid session, duplicate email returns 409

- [x] **TASK-009**: Implement login endpoint
  - Description: POST /api/auth/login - accepts email, password. Verifies credentials, creates session. Returns session in HttpOnly, Secure, SameSite=Strict cookie.
  - Type: backend
  - Dependencies: TASK-007
  - Acceptance: Valid credentials return session cookie, invalid credentials return 401

- [x] **TASK-010**: Implement logout endpoint
  - Description: POST /api/auth/logout - invalidates current session, clears cookie.
  - Type: backend
  - Dependencies: TASK-007
  - Acceptance: After logout, session is invalid, cookie is cleared

- [x] **TASK-011**: Create auth middleware
  - Description: FastAPI dependency for route protection. Extracts session from cookie, validates, attaches user to request. Returns 401 if no valid session.
  - Type: backend
  - Dependencies: TASK-007
  - Acceptance: Protected routes return 401 without session, 200 with valid session

- [x] **TASK-012**: Create login/register UI pages
  - Description: Svelte pages for /login and /register. Forms with validation, error display, redirect on success. Use CSS custom properties for styling.
  - Type: frontend
  - Dependencies: TASK-008, TASK-009
  - Acceptance: Can register and login through UI, errors displayed properly, redirects work

---

## Phase 3: Core Domain Models

- [x] **TASK-013**: Implement Budget model and migration
  - Description: Budget model: id (UUID), name, owner_id (User FK), warning_threshold (integer, øre), created_at, updated_at, deleted_at, created_by, updated_by. Migration.
  - Type: backend
  - Dependencies: TASK-005
  - Acceptance: Migration runs, Budget model works with relationships

- [x] **TASK-014**: Implement Account model and migration
  - Description: Account model: id (UUID), budget_id (FK), name, purpose (enum: normal/savings/loan), datasource (enum: bank/credit/cash/virtual), currency (default DKK), starting_balance (øre), can_go_negative (bool), needs_coverage (bool), timestamps, soft delete.
  - Type: backend
  - Dependencies: TASK-013
  - Acceptance: Migration runs, Account linked to Budget, enums work

- [x] **TASK-015**: Implement Category model and migration
  - Description: Category model: id (UUID), budget_id (FK), name, parent_id (self-referential FK, nullable), is_system (bool for Income/Expense), display_order (int), timestamps, soft delete. Hierarchical categories.
  - Type: backend
  - Dependencies: TASK-013
  - Acceptance: Migration runs, hierarchical queries work, system categories protected

- [x] **TASK-016**: Implement Transaction model and migration
  - Description: Transaction model: id (UUID), account_id (FK), date, amount (øre), description, status (enum: uncategorized/pending_confirmation/pending_receipt/categorized), is_internal_transfer (bool), counterpart_transaction_id (self-ref FK), external_id, import_hash, timestamps.
  - Type: backend
  - Dependencies: TASK-014
  - Acceptance: Migration runs, Transaction linked to Account, status enum works

- [x] **TASK-017**: Implement BudgetPost model and migration
  - Description: BudgetPost model: id (UUID), budget_id (FK), category_id (FK), name, type (enum: fixed/ceiling/rolling), amount_min (øre), amount_max (øre), from_account_ids (JSON array), to_account_ids (JSON array), recurrence pattern (JSON), timestamps, soft delete.
  - Type: backend
  - Dependencies: TASK-015
  - Acceptance: Migration runs, BudgetPost linked to Category, JSON fields work

- [x] **TASK-018**: Implement TransactionAllocation model and migration
  - Description: Junction table: id (UUID), transaction_id (FK), budget_post_id (FK), amount (øre), is_remainder (bool), timestamps. Unique constraint on transaction_id + budget_post_id.
  - Type: backend
  - Dependencies: TASK-016, TASK-017
  - Acceptance: Migration runs, allocation with remainder logic works, validation prevents over-allocation

---

## Phase 4: Budget and Account APIs

- [x] **TASK-019**: Implement Budget CRUD endpoints
  - Description: GET /api/budgets (list with cursor pagination), POST /api/budgets (create), GET /api/budgets/{id}, PUT /api/budgets/{id}, DELETE /api/budgets/{id} (soft delete). Auto-create default categories (Indtægt, Udgift with subcategories) on budget creation.
  - Type: backend
  - Dependencies: TASK-013, TASK-015, TASK-011
  - Acceptance: All CRUD operations work, auth required, default categories created

- [x] **TASK-020**: Implement Account CRUD endpoints
  - Description: GET /api/budgets/{id}/accounts, POST, PUT, DELETE. Validate purpose/datasource combinations. Duplicate check within budget.
  - Type: backend
  - Dependencies: TASK-014, TASK-019
  - Acceptance: Account CRUD works, validation enforced, linked to budget

- [x] **TASK-021**: Implement Category endpoints
  - Description: GET /api/budgets/{id}/categories (returns tree), POST, PUT, DELETE. Prevent deletion of system categories. Support reordering.
  - Type: backend
  - Dependencies: TASK-015, TASK-019
  - Acceptance: Category tree returned correctly, system categories protected

- [x] **TASK-022**: Create Budget management UI
  - Description: Pages: /budgets (list), /budgets/new (create form), /budgets/{id}/settings (edit). Budget selector in header. List shows name and total balance.
  - Type: frontend
  - Dependencies: TASK-019
  - Acceptance: Can create, view, edit budgets through UI

- [x] **TASK-023**: Create Account management UI
  - Description: Account list within budget settings. Add/edit account modal with form for all fields. Shows current balance per account.
  - Type: frontend
  - Dependencies: TASK-020
  - Acceptance: Can add, edit, view accounts through UI

---

## Phase 5: Transactions

- [x] **TASK-024**: Implement Transaction endpoints
  - Description: GET /api/budgets/{id}/transactions with cursor pagination and filters (account, category, date range, status). POST for manual creation. PUT for updates. Support internal transfers (creates two linked transactions).
  - Type: backend
  - Dependencies: TASK-016, TASK-019
  - Acceptance: Transaction listing with filters works, manual creation works, internal transfers create paired transactions

- [x] **TASK-025**: Implement allocation endpoint
  - Description: POST /api/transactions/{id}/allocate - body contains array of {budget_post_id, amount, is_remainder}. Validates sum doesn't exceed transaction amount. Remainder calculated automatically.
  - Type: backend
  - Dependencies: TASK-018, TASK-024
  - Acceptance: Can allocate transaction to multiple budget posts, remainder logic works, validation prevents over-allocation

- [x] **TASK-026**: Create Transaction list UI
  - Description: /budgets/{id}/transactions page. List grouped by date. Filters for account, category, date range. Infinite scroll pagination. Shows description, amount, category badge.
  - Type: frontend
  - Dependencies: TASK-024
  - Acceptance: Transaction list renders with grouping, filters work, pagination loads more

- [x] **TASK-027**: Create Transaction categorization modal
  - Description: Modal for categorizing uncategorized transactions. Shows transaction details. Category/budget post selector (searchable). Split interface for multiple allocations. Checkbox to create rule for future matches.
  - Type: frontend
  - Dependencies: TASK-025, TASK-026
  - Acceptance: Can categorize transactions, split allocations work, modal closes on save

---

## Phase 6: Dashboard

- [x] **TASK-028**: Implement Dashboard data endpoint
  - Description: GET /api/budgets/{id}/dashboard - returns: available_balance (sum of normal accounts), month_summary (income, expenses, net), pending_count (uncategorized transactions), fixed_expenses (list with status: paid/pending/overdue).
  - Type: backend
  - Dependencies: TASK-024, TASK-017
  - Acceptance: Dashboard endpoint returns all required aggregations, calculations correct

- [x] **TASK-029**: Create Dashboard UI
  - Description: Main dashboard page at /budgets/{id}. Cards: Available Balance (large number), Month Summary (income/expenses/net), Pending Transactions (count with link), Fixed Expenses Checklist (with status indicators).
  - Type: frontend
  - Dependencies: TASK-028
  - Acceptance: Dashboard displays all data, responsive layout, clicking pending navigates to uncategorized

---

## Phase 7: Forecast

- [x] **TASK-030**: Implement Forecast calculation service
  - Description: Service that projects balance N periods (months) forward. Uses budget posts with recurrence patterns to generate expected transactions. Calculates running balance. Identifies lowest point and large upcoming expenses.
  - Type: backend
  - Dependencies: TASK-017
  - Acceptance: Forecast calculation matches expected results for test scenarios with various recurrence patterns

- [x] **TASK-031**: Implement Forecast endpoint
  - Description: GET /api/budgets/{id}/forecast?months=N (default 12). Returns array of monthly projections: {month, start_balance, expected_income, expected_expenses, end_balance}, plus lowest_point and next_large_expense.
  - Type: backend
  - Dependencies: TASK-030
  - Acceptance: Forecast endpoint returns correct projections, handles edge cases

- [x] **TASK-032**: Create Forecast UI with chart
  - Description: /budgets/{id}/forecast page. ECharts line chart showing balance over time. Time range selector (3/6/12 months). Info cards for lowest point and next large expense. Monthly breakdown table below chart.
  - Type: frontend
  - Dependencies: TASK-031
  - Acceptance: Chart renders correctly, time range changes update view, table shows monthly details

---

## Phase 8: Integration and Polish

- [ ] **TASK-033**: Implement Navigation and routing
  - Description: Main navigation component. Desktop: sidebar with links (Dashboard, Transactions, Forecast, Budget settings). Mobile: bottom bar with icons. Budget selector in header. Route protection (redirect to /login if not authenticated).
  - Type: frontend
  - Dependencies: TASK-029, TASK-032
  - Acceptance: All navigation works, responsive behavior correct, unauthenticated users redirected

- [ ] **TASK-034**: Implement Error handling and loading states
  - Description: Global error boundary component. Loading skeleton components for lists and cards. Toast notification system for action feedback (success, error). API error handling with user-friendly messages.
  - Type: frontend
  - Dependencies: TASK-033
  - Acceptance: Errors caught and displayed gracefully, loading states shown during fetches, toasts appear for actions

- [ ] **TASK-035**: End-to-end testing
  - Description: Write E2E tests for critical user flows: 1) Register new user, 2) Login, 3) Create budget with accounts, 4) Add manual transaction, 5) Categorize transaction, 6) View dashboard, 7) View forecast.
  - Type: both
  - Dependencies: TASK-034
  - Acceptance: All E2E tests pass, cover the main happy paths

---

## Notes

- Each task should be implemented by the appropriate subagent (backend-implementer or frontend-implementer)
- After each task, the reviewer subagent must approve before proceeding
- If review fails 3 times, stop and ask for human guidance
- Create a git commit after each approved task
