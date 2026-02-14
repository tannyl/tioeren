# Tiøren - Task List

Post-MVP backlog. For completed tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## High Priority

- [ ] **TASK-047**: Implement rate limiting
  - Description: Add rate limiting using slowapi: login 5/min per IP, general API 100/min per user. Return HTTP 429 with Retry-After header.
  - Type: backend
  - Dependencies: none

## Budget Post Rebuild (Spec Updated 2026-02-13)

> SPEC.md rewritten: active/archived budget post split (separate tables), two-level account binding model (counterparty on post, accounts on patterns), transfers without categories, amount occurrences for archived periods, transactions bind to patterns/occurrences (not posts).

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

- [ ] **TASK-036**: CSV transaction import
  - Description: Upload CSV from bank, map columns, detect duplicates, import transactions. Save mapping as reusable profile per account.
  - Type: both
  - Dependencies: none

- [ ] **TASK-037**: Auto-categorization rules engine
  - Description: Create Rule model and UI. Match transactions by description/amount/date patterns. Support auto, confirm, and receipt-required modes. Priority-ordered rule execution.
  - Type: both
  - Dependencies: none

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

- [ ] **BUG-017**: GET archived-budget-posts year param allows integer overflow (500 + traceback leak)
  - Severity: MEDIUM
  - Type: backend

- [ ] **BUG-018**: Archive endpoint allows future period archiving (e.g. 2099-12)
  - Severity: LOW
  - Type: backend
