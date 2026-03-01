# Tiøren - Task List

Post-MVP backlog. For completed tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## High Priority

- [x] **TASK-147**: Reorder navigation menu and rename Forecast to Prognoser
  - Description: 1) Rename "Forecast" to "Prognoser" in i18n files. 2) Reorder nav items: Overblik, Prognoser, Budgetposter, Pengekasser, Sparegrise, Gældsbyrder, Transaktioner, Indstillinger.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-148**: Audit codebase for Danish words in code identifiers
  - Description: Fix coding standards violations - replace Danish key names in i18n JSON files (pengekasser→wallets, sparegrise→piggyBanks, gaeldsbyrder→debts) and search entire codebase for Danish variable/function names.
  - Type: frontend
  - Dependencies: TASK-147

- [ ] **TASK-047**: Implement rate limiting
  - Description: Add rate limiting using slowapi: login 5/min per IP, general API 100/min per user. Return HTTP 429 with Retry-After header.
  - Type: backend
  - Dependencies: none
  - Spec: § Rate limiting

## Upcoming Features

- [ ] **TASK-066**: Frontend - Archived budget posts view
  - Description: Create UI for viewing archived budget posts: period history, amount occurrences with expected vs actual, navigate between periods. Read-only.
  - Type: frontend
  - Dependencies: TASK-063
  - Spec: § Budgetpost (forventning), § Budgetpost-analyse

- [ ] **TASK-036**: CSV transaction import
  - Description: Upload CSV from bank, map columns, detect duplicates, import transactions. Save mapping as reusable profile per account.
  - Type: both
  - Dependencies: none
  - Spec: § Import, § Transaktion (Transaction)

- [ ] **TASK-037**: Auto-categorization rules engine
  - Description: Create Rule model and UI. Match transactions by description/amount/date patterns. Support auto, confirm, and receipt-required modes. Priority-ordered rule execution.
  - Type: both
  - Dependencies: none
  - Spec: § Regel (Rule)

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
  - Spec: § Budget

## Low Priority

- [ ] **TASK-049**: Invalidate all sessions on logout
  - Description: Update logout endpoint to call invalidate_all_user_sessions() instead of only invalidating current session.
  - Type: backend
  - Dependencies: none

- [ ] **TASK-050**: Add per-account balance forecast
  - Description: Extend forecast API and UI to show projected balance per individual account. Answer "Does account X have enough for bills?"
  - Type: both
  - Dependencies: TASK-046
  - Spec: § Forecast-beregning, § Forecast-horisont, § Prognoseberegning for pengekasse-saldo

- [ ] **TASK-051**: Add two-level API validation (errors + warnings)
  - Description: Implement response schema with success, data, errors[], warnings[]. Errors block request, warnings are advisory.
  - Type: backend
  - Dependencies: none
  - Spec: § Validerings-respons

- [ ] **TASK-039**: Dark theme
  - Description: Implement dark color scheme using existing CSS custom properties. Add theme toggle in settings. Persist preference.
  - Type: frontend
  - Dependencies: none
  - Spec: § Farvepalette (forslag)

- [ ] **TASK-040**: Receipt scanning (OCR + LLM)
  - Description: Upload receipt image, extract line items via OCR + LLM, suggest split-categorization across budget posts.
  - Type: both
  - Dependencies: TASK-037
  - Spec: § Kvitteringshåndtering (fremtidig)

- [ ] **TASK-041**: API tokens for programmatic access
  - Description: User-created API tokens with optional expiry and scope limits. Token management UI in settings.
  - Type: both
  - Dependencies: none
  - Spec: § Authentication og sikkerhed

## Active Bugs

- [ ] **BUG-017**: GET archived-budget-posts year param allows integer overflow (500 + traceback leak)
  - Severity: MEDIUM
  - Type: backend
  - Spec: § Validerings-respons

- [ ] **BUG-018**: Archive endpoint allows future period archiving (e.g. 2099-12)
  - Severity: LOW
  - Type: backend

- [ ] **BUG-023**: Editing period_yearly pattern does not restore start period from start_date
  - Severity: LOW
  - Type: frontend
  - Note: When editing a `period_yearly` pattern, `patternPeriodYear`/`patternPeriodMonth` default to current date instead of extracting from the saved `start_date`. `period_monthly` and `period_once` correctly extract start period.

- [ ] **BUG-036**: Transactions page fails to load - ReferenceError: accounts is not defined
  - Severity: CRITICAL
  - Type: frontend
  - Note: Regression from Account→Container migration. `transactions/+page.svelte` still references `accounts` variable (line ~345) which no longer exists after renaming to containers.
