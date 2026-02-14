# Tiøren - Task List

Post-MVP backlog. For completed MVP tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## 🚨 Critical (MVP Gaps)

- [x] **TASK-045**: Budget Post API - Backend CRUD
  - Description: Create full CRUD API for budget posts. Endpoints: POST/GET/PUT/DELETE at /api/budgets/{id}/budget-posts. Include Pydantic schemas (BudgetPostCreate, BudgetPostUpdate, BudgetPostResponse) and service layer. Support recurrence patterns: monthly (day), quarterly (months + day), yearly (month + day), once (date). Validate amounts, category assignment, account bindings.
  - Type: backend
  - Dependencies: none

- [x] **TASK-046**: Budget Post UI - Frontend management
  - Description: Create budget post management UI. List page showing all budget posts grouped by category. Create/edit modal with: name, type (fast/loft/løbende), amounts (min/max), category selector, recurrence pattern builder (monthly/quarterly/yearly/once with date pickers), optional account bindings. Add "Budgetposter" to navigation. Integrate with existing forecast.
  - Type: frontend
  - Dependencies: TASK-045

---

## High Priority

- [ ] **TASK-047**: Implement rate limiting
  - Description: Add rate limiting using slowapi: login 5/min per IP, general API 100/min per user. Return HTTP 429 with Retry-After header.
  - Type: backend
  - Dependencies: none

- [x] **TASK-044**: Implement security testing agent
  - Description: Create a white-hat security agent that tests for OWASP Top 10 vulnerabilities, auth bypass, injection attacks. Add security step to workflow after QA.
  - Type: infrastructure
  - Dependencies: none

- [x] **TASK-043**: Remove landing page, redirect to login
  - Description: Remove redundant landing page at `/`. Redirect unauthenticated users directly to `/login`. Add project title and tagline to login and register pages.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-042**: Fix tioren → tioeren transliteration
  - Description: Correct transliteration of "Tiøren" from "tioren" to "tioeren" in technical identifiers (container names, DB credentials, package name, localStorage key). Excludes devcontainer volume names.
  - Type: infrastructure
  - Dependencies: none

- [x] **QA-009**: Verify app functionality after rename
  - Description: Full smoke test - login, create budget, add transaction
  - Type: qa
  - Dependencies: TASK-042

- [x] **QA-010**: Ret auth-fejl (serverfejl + engelske beskeder)
  - Description: 1) Undersøg og ret serverfejl ved login/registrering. 2) Oversæt Pydantic valideringsfejl til dansk.
  - Type: qa
  - Dependencies: none

## Security Audit (Full Codebase)

- [x] **SEC-001**: Static Analysis (SAST)
  - Description: Run Semgrep on api/ and ui/src/ to find hardcoded secrets, injection patterns, etc.
  - Type: security
  - Dependencies: TASK-044
  - Result: PASS - 826 security rules, 0 findings

- [x] **SEC-002**: Dependency Scan (SCA)
  - Description: Run pip-audit and npm audit for known CVEs in dependencies.
  - Type: security
  - Dependencies: TASK-044
  - Result: 6 vulnerabilities (2 moderate, 4 low) - dev-time deps, no prod impact

- [x] **SEC-003**: Authentication Testing
  - Description: Test unauthenticated access, invalid sessions, login failures.
  - Type: security
  - Dependencies: TASK-044
  - Result: 1 MEDIUM (no rate limiting), 3 LOW (cookie flags, SECRET_KEY, deps)

- [x] **SEC-004**: Authorization (BOLA/IDOR)
  - Description: Test cross-user resource access - User A accessing User B's budgets/transactions.
  - Type: security
  - Dependencies: TASK-044
  - Result: PASS - All 18 authorization tests passed, no IDOR vulnerabilities

- [x] **SEC-005**: Input Validation (Injection)
  - Description: Test SQL injection and XSS payloads on API endpoints.
  - Type: security
  - Dependencies: TASK-044
  - Result: PASS - SQLAlchemy parameterized queries, Svelte auto-escaping

- [x] **SEC-006**: API Security & Business Logic
  - Description: Test CORS, rate limiting, sensitive data exposure, error handling.
  - Type: security
  - Dependencies: TASK-044
  - Result: 8 findings (2 HIGH, 5 MEDIUM, 1 LOW) - see security report

---

- [ ] **TASK-036**: CSV transaction import
  - Description: Upload CSV from bank, map columns, detect duplicates, import transactions. Save mapping as reusable profile per account.
  - Type: both
  - Dependencies: none

- [ ] **TASK-037**: Auto-categorization rules engine
  - Description: Create Rule model and UI. Match transactions by description/amount/date patterns. Support auto, confirm, and receipt-required modes. Priority-ordered rule execution.
  - Type: both
  - Dependencies: none

## Budget Post Enhancements (Completed - Superseded by TASK-061+)

> These tasks implemented the original period-based model. TASK-061+ replaces this with the new active/archived split model.

- [x] **TASK-052**: Budget Post - Recurrence occurrence expansion
- [x] **TASK-053**: Budget Post - Account binding UI
- [x] **TASK-054**: Budget Post - New recurrence model (date-based + period-based)
- [x] **TASK-055**: Budget Post - Beløbsmønstre (amount patterns)
- [x] **TASK-059**: Revised category/budget post model
- [x] **TASK-060**: Derive budget post period from amount patterns + past-date validation

## Budget Post Rebuild (Spec Updated 2026-02-13)

> SPEC.md rewritten: active/archived budget post split (separate tables), two-level account binding model (counterparty on post, accounts on patterns), transfers without categories, amount occurrences for archived periods, transactions bind to patterns/occurrences (not posts).

- [x] **TASK-061**: Backend - New budget post data model (active/archived split)
  - Description: Rebuild the budget post database model per updated SPEC.md:
    1. Restructure `budget_posts` table: remove `period_year`, `period_month`, `is_archived`, `successor_id`. Add `direction` (enum: income/expense/transfer), `counterparty_type` (enum: external/account), `counterparty_account_id` (FK accounts, nullable), `transfer_from_account_id`, `transfer_to_account_id`, `accumulate` (bool). Make `category_id` nullable (null for transfers).
    2. Create `archived_budget_posts` table: id, budget_id, budget_post_id (nullable FK), period_year, period_month, direction, category_id (nullable), type. UNIQUE(category_id, period_year, period_month) WHERE category_id IS NOT NULL.
    3. Create `amount_occurrences` table: id, archived_budget_post_id (FK CASCADE), date (nullable), amount (BIGINT).
    4. Add `account_ids` (JSONB, nullable) to `amount_patterns` table.
    5. Update UNIQUE constraints: `budget_posts` gets UNIQUE(category_id) WHERE category_id IS NOT NULL, plus UNIQUE(transfer_from_account_id, transfer_to_account_id) WHERE direction='transfer'.
    6. Remove `from_account_ids` and `to_account_ids` JSONB fields from `budget_posts`.
    7. Alembic migration for all DB changes.
    8. Update SQLAlchemy models: BudgetPost, ArchivedBudgetPost (new), AmountPattern, AmountOccurrence (new).
  - Type: backend
  - Dependencies: none

- [ ] **TASK-062**: Backend - Budget post service and schemas rebuild
  - Description: Rebuild service layer and Pydantic schemas for new model:
    1. New schemas: `BudgetPostCreate` (direction, category_id optional, type, counterparty_type, counterparty_account_id, transfer accounts, amount_patterns with account_ids). `BudgetPostUpdate`. `BudgetPostResponse`. `ArchivedBudgetPostResponse`. `AmountOccurrenceResponse`.
    2. New validation logic: direction determines which fields are required/forbidden. Income/expense require category + counterparty. Transfer requires from/to NORMAL accounts. Amount pattern account_ids validation (1+ for EXTERNAL, exactly 1 for loan/savings, null for transfer).
    3. Remove period derivation logic (no periods on active posts).
    4. Remove past-date validation (active posts are forward-looking).
    5. Keep recurrence expansion logic (used for forecast and archiving).
    6. New service functions for archived posts (create snapshot, query by period).
    7. Update all existing budget post CRUD endpoints.
  - Type: backend
  - Dependencies: TASK-061

- [ ] **TASK-063**: Backend - Transaction allocation to patterns/occurrences
  - Description: Update transaction allocation model to bind to amount patterns or amount occurrences instead of budget posts directly:
    1. Add `amount_pattern_id` (FK, nullable) and `amount_occurrence_id` (FK, nullable) to transaction_allocations table.
    2. Add CHECK constraint: exactly one of amount_pattern_id or amount_occurrence_id must be set.
    3. Remove or deprecate direct `budget_post_id` FK on allocations.
    4. Update allocation service and schemas.
    5. Update categorization logic to allocate to patterns.
    6. Alembic migration.
  - Type: backend
  - Dependencies: TASK-062

- [ ] **TASK-064**: Backend - Forecast service update
  - Description: Update forecast service for new model:
    1. Use active budget posts + expand amount patterns for future periods.
    2. Use archived budget posts + amount occurrences for past periods.
    3. Account-level forecast uses pattern account_ids (not post-level from/to).
    4. Handle transfers (post-level accounts, no pattern accounts).
    5. Update forecast API response if needed.
  - Type: backend
  - Dependencies: TASK-062

- [ ] **TASK-065**: Frontend - Budget post UI rebuild
  - Description: Rebuild budget post UI for new model:
    1. Update BudgetPostModal: direction selector (income/expense/transfer) as first step.
    2. Income/expense flow: counterparty selector (EXTERNAL or pick loan/savings account), then category picker (filtered by direction root).
    3. Transfer flow: from-account (NORMAL) + to-account (NORMAL, different) selectors. No category picker.
    4. Amount pattern form: add account_ids selector (NORMAL accounts). If EXTERNAL: multi-select. If loan/savings: single select. If transfer: hidden.
    5. Remove period display from active posts.
    6. Update TypeScript types to match new API.
    7. Update budget post list page: group by direction, show counterparty info.
  - Type: frontend
  - Dependencies: TASK-062

- [ ] **TASK-066**: Frontend - Archived budget posts view
  - Description: Create UI for viewing archived budget posts:
    1. Period history view: select month/year to see archived snapshots.
    2. Show amount occurrences with expected vs actual (matched transactions).
    3. Navigate between periods.
    4. Read-only view (archived posts are immutable).
  - Type: frontend
  - Dependencies: TASK-063

---

## Medium Priority

- [ ] **TASK-048**: Add navigation badge for uncategorized transactions
  - Description: Show badge/count on Transactions nav item when uncategorized transactions exist. Update reactively when transactions are categorized.
  - Type: frontend
  - Dependencies: none

- [ ] **TASK-038**: Shared budgets
  - Description: Budget sharing with owner/member roles. Email invitation flow with 7-day token. Members get full edit access; only owners manage membership and deletion.
  - Type: both
  - Dependencies: none

## Low Priority

- [ ] **TASK-049**: Invalidate all sessions on logout
  - Description: Update logout endpoint to call invalidate_all_user_sessions() instead of only invalidating current session.
  - Type: backend
  - Dependencies: none

- [ ] **TASK-050**: Add per-account balance forecast
  - Description: Extend forecast API and UI to show projected balance per individual account. Answer "Does account X have enough for bills?"
  - Type: both
  - Dependencies: TASK-046

- [ ] **TASK-051**: Add two-level API validation (errors + warnings)
  - Description: Implement response schema with success, data, errors[], warnings[]. Errors block request, warnings are advisory.
  - Type: backend
  - Dependencies: none

- [ ] **TASK-039**: Dark theme
  - Description: Implement dark color scheme using existing CSS custom properties. Add theme toggle in settings. Persist preference.
  - Type: frontend
  - Dependencies: none

- [ ] **TASK-040**: Receipt scanning (OCR + LLM)
  - Description: Upload receipt image, extract line items via OCR + LLM, suggest split-categorization across budget posts.
  - Type: both
  - Dependencies: TASK-037

- [ ] **TASK-041**: API tokens for programmatic access
  - Description: User-created API tokens with optional expiry and scope limits. Token management UI in settings.
  - Type: both
  - Dependencies: none

## Active Bugs

None currently.

## Recently Fixed

- [x] **BUG-009**: Transactions and Settings pages don't update when switching budgets
  - Severity: MEDIUM
  - Description: When switching budgets via header dropdown, only Overblik and Forecast update. Transactions and Settings require manual refresh.
  - Type: frontend
  - Fixed: 2026-02-08 - Added $effect to watch budgetId and reload data

## Fixed Bugs

- [x] **BUG-007**: Budget dropdown doesn't update dashboard or stay on current page
  - Severity: MEDIUM
  - Description: When switching budgets via the header dropdown: 1) On dashboard/overblik page, content doesn't update. 2) On other pages, it redirects to overblik instead of staying on current page with new budget.
  - Type: frontend
  - Fixed: 2026-02-07 - Added $effect for reactive dashboard reload, preserve page section on navigation

- [x] **BUG-008**: Budget dropdown shows "Indlæser..." after creating new budget
  - Severity: LOW
  - Description: After creating a new budget and landing on overblik, the budget dropdown in header constantly shows "Indlæser..." until page is manually reloaded.
  - Type: frontend
  - Fixed: 2026-02-07 - Use budgetStore auto-subscription, call setCurrentBudget on select

## Critical Bugs (Fixed)

- [x] **BUG-006**: Infinite loop when clicking transaction
  - Severity: CRITICAL
  - Description: When clicking on a transaction card to open categorization modal, browser becomes unresponsive due to infinite $effect loop.
  - Type: frontend
  - Fixed: 2026-02-07 - Split $effect into separate load/reset effects, fixed expandedCategories initialization

## Deferred Bugs

- [x] **BUG-005**: Root path (/) shows useless page instead of redirecting
  - Severity: LOW
  - Description: When logged in, navigating to "/" shows a page with only logout option and English text. Should redirect to /budgets instead.
  - Type: frontend
  - Fixed: 2026-02-06 - Simplified redirect logic, removed getLocaleFromNavigator(), cleaned up landing page

- [x] **BUG-004**: Sidebar navigation links contain empty budget IDs
  - Severity: LOW
  - Description: On /budgets list page (no budget selected), sidebar renders links like `/budgets//transactions`. Should hide or disable budget-specific nav when no budget context.
  - Type: frontend
  - Fixed: 2026-02-06 - Added route guard, conditional navigation, auto-redirect
