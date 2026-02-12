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

## Budget Post Enhancements (Spec Updated 2026-02-12)

> SPEC.md opdateret med revideret kategori/budgetpost-model: kategoriens navn er budgetpostens identitet (1:1 relation per periode), uforanderlig kategori-binding, retnings-validering mod hierarki, og UI-flow med type-valg.

- [x] **TASK-052**: Budget Post - Recurrence occurrence expansion
  - Description: Implement logic to expand recurrence patterns into concrete expected occurrences per period. E.g., "50 kr every Friday" generates 4-5 occurrences per month. Must handle weekend-postpone option. Required for accurate forecast and deviation tracking.
  - Type: backend
  - Dependencies: TASK-054

- [x] **TASK-053**: Budget Post - Account binding UI
  - Description: Add from/to account selection to BudgetPostModal. Database already has from_account_ids/to_account_ids JSONB fields. UI should allow selecting which accounts a budget post applies to (determines "retning": indtægt/udgift/overførsel). For transfers, both from and to can be set - auto-categorized based on account purpose.
  - Type: frontend
  - Dependencies: TASK-046

- [x] **TASK-054**: Budget Post - New recurrence model (date-based + period-based)
  - Description: Implement the new recurrence model from spec. Date-based: once, every N days, every N weeks (on weekday), every N months (day or relative), every N years - all with interval [N] parameter and weekend-postpone option. Period-based: once in specific months [jan, feb, ...], or yearly recurrence in specific months every [N] years.
  - Type: both
  - Dependencies: TASK-046

- [x] **TASK-055**: Budget Post - Beløbsmønstre (amount patterns)
  - Description: Implement beløbsmønster model - multiple amount patterns per budget post. Each pattern has: amount (øre), start_date, end_date (optional), recurrence. Enables seasonal variation (el-regning) and salary increases.
  - Type: both
  - Dependencies: TASK-054

- [x] **TASK-059**: Revised category/budget post model
  - Description: Align implementation with revised SPEC for category/budget post relationship. Changes:
    **Backend:**
    1. Remove `name` field from BudgetPost model and schemas (category name is the identity)
    2. Add `period_year` (int) and `period_month` (int) fields to BudgetPost
    3. Add UNIQUE constraint: `(category_id, period_year, period_month)`
    4. Make `category_id` immutable (validate in update endpoint that category_id cannot be changed)
    5. Add direction validation: account bindings must match root category (expense under Udgift, income under Indtægt)
    6. Update BudgetPost schemas: remove name, add period_year/period_month, remove category_id from update
    7. Alembic migration for DB changes
    **Frontend:**
    1. Remove name input from BudgetPostModal
    2. Add direction type selector (Indtægt/Udgift/Overførsel) as first step - controls which account fields are shown
    3. Filter category picker based on selected type (only categories under matching system root)
    4. Indtægt: show only "to accounts" field. Udgift: show only "from accounts" field. Overførsel: exactly 1 from + 1 to.
    5. Display budget post name as category name in lists and overviews
  - Type: both
  - Dependencies: TASK-055
  - Spec reference: SPEC.md section 3 (Budgetpost) and section 5 (Kategori)

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
