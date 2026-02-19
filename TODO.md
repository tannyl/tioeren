# Tiøren - Task List

Post-MVP backlog. For completed tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## Category → category_path Refactoring

- [~] **TASK-100**: Opdater SPEC.md med ny category_path model
  - Description: Fjern Category-entitet fra spec, tilføj category_path TEXT[] og display_order INTEGER[] til BudgetPost/ArchivedBudgetPost. Opdater alle relaterede sektioner.
  - Type: infrastructure
  - Dependencies: none

- [ ] **TASK-101**: Backend - Fjern Category, tilføj category_path
  - Description: Alembic migration (drop categories, tilføj nye kolonner), slet Category model/schema/service/routes, opdater BudgetPost/ArchivedBudgetPost models, opdater alle services og routes.
  - Type: backend
  - Dependencies: TASK-100

- [ ] **TASK-102**: Backend - Opdater tests for category_path
  - Description: Slet category tests, opdater alle test-fixtures til at bruge category_path i stedet for Category-objekter.
  - Type: backend
  - Dependencies: TASK-101

- [ ] **TASK-103**: Frontend - Budgetpost-trævisning og kategoriseringsmodal
  - Description: Byg hierarkisk træ fra category_path præfikser. Opdater CategorizationModal til at hente budgetposter direkte i stedet for kategorier.
  - Type: frontend
  - Dependencies: TASK-101

- [ ] **TASK-104**: Frontend - Kategori-sti input med autocomplete
  - Description: Erstat category dropdown i BudgetPostModal med tekstfelt med " > " separator og autocomplete fra eksisterende stier.
  - Type: frontend
  - Dependencies: TASK-103

## High Priority

- [ ] **TASK-047**: Implement rate limiting
  - Description: Add rate limiting using slowapi: login 5/min per IP, general API 100/min per user. Return HTTP 429 with Retry-After header.
  - Type: backend
  - Dependencies: none

## OccurrenceTimeline Chart Improvements

- [x] **TASK-087**: OccurrenceTimeline i18n - remove hardcoded Danish locale
  - Description: Remove hardcoded `daLocale` (d3-time-format) and replace with locale-aware formatting from `dateFormat.ts` + `$locale`. Remove `d3-time-format` dependency.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-088**: Fix axis text blinking on chart navigation
  - Description: X and Y axis text fades in/out on navigation because loading opacity dims entire SVG. Move loading opacity to bar content only, keep axes crisp.
  - Type: frontend
  - Dependencies: TASK-087

- [x] **TASK-089**: Y-axis range - adapt to visible window + handle small amounts
  - Description: Y-axis yMax computed from extended 5-month window instead of visible 3 months, and has hardcoded floor of 1000 kr. Fix: compute yMax from visible window only, lower minimum.
  - Type: frontend
  - Dependencies: TASK-088

- [x] **TASK-090**: Fix bar height animation asymmetry
  - Description: When yMax increases (new high bars), existing bars don't shrink smoothly. Use Svelte `tweened` store for yMax to interpolate bidirectionally.
  - Type: frontend
  - Dependencies: TASK-089

- [x] **TASK-091**: Logarithmic Y-axis for large value ranges
  - Description: Auto-switch to `scaleSymlog` when max/min bar value ratio exceeds 20x. Transparent to user, no toggle.
  - Type: frontend
  - Dependencies: TASK-090

- [x] **TASK-092**: Dynamic pattern color generation
  - Description: Replace static 8-color `patternColors` array with HSL golden angle rotation for unlimited distinct colors.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-093**: Archive completed tasks in TODO.md and WORKFLOW-STATE.md
  - Description: Move completed tasks to `docs/MVP-HISTORY.md`. Trim WORKFLOW-STATE task history and stale progress sections.
  - Type: infrastructure
  - Dependencies: none

## Bank Day Improvements

- [x] **TASK-095**: Bank day accumulation option (no deduplication)
  - Description: Add "Ingen deduplikering" checkbox when bank day adjustment is active. When checked, occurrences adjusted to the same bank day are kept (accumulated) instead of deduplicated. Default off (current behavior preserved).
  - Type: both
  - Dependencies: none

## Pattern UX

- [x] **TASK-096**: Pattern color indicators on amount pattern cards
  - Description: Show each pattern's chart color as a vertical stripe on its card in the budget post dialog. Export color map from OccurrenceTimeline via callback, apply as ::before pseudo-element.
  - Type: frontend
  - Dependencies: TASK-092

- [x] **TASK-097**: Remove redundant back button from pattern editor
  - Description: Remove "Tilbage til budgetpost" back button from top of pattern editor sub-view. Cancel button at bottom already provides this functionality.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-098**: Make pattern cards clickable to edit
  - Description: Make entire pattern card clickable to open editor. Remove separate edit button, keep only delete button. Add cursor: pointer and keyboard accessibility.
  - Type: frontend
  - Dependencies: none

- [x] **TASK-099**: Make budget post cards clickable to edit
  - Description: Make entire budget post card clickable to open edit modal. Remove separate edit button, keep only delete button. Add stopPropagation on delete, cursor: pointer, keyboard accessibility.
  - Type: frontend
  - Dependencies: none

## Upcoming Features

- [ ] **TASK-066**: Frontend - Archived budget posts view
  - Description: Create UI for viewing archived budget posts: period history, amount occurrences with expected vs actual, navigate between periods. Read-only.
  - Type: frontend
  - Dependencies: TASK-063

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

- [x] **BUG-025**: Recurrence dates shift when navigating chart (interval > 1 phase bug)
  - Severity: MEDIUM
  - Type: backend

- [x] **BUG-026**: Y-axis max resets to 10 during chart navigation/loading
  - Severity: LOW
  - Type: frontend

- [x] **TASK-094**: Auto-fill today's date for new date-based patterns
  - Type: frontend

- [ ] **BUG-017**: GET archived-budget-posts year param allows integer overflow (500 + traceback leak)
  - Severity: MEDIUM
  - Type: backend

- [ ] **BUG-018**: Archive endpoint allows future period archiving (e.g. 2099-12)
  - Severity: LOW
  - Type: backend

- [ ] **BUG-023**: Editing period_yearly pattern does not restore start period from start_date
  - Severity: LOW
  - Type: frontend
  - Note: When editing a `period_yearly` pattern, `patternPeriodYear`/`patternPeriodMonth` default to current date instead of extracting from the saved `start_date`. `period_monthly` and `period_once` correctly extract start period.

- [x] **BUG-027**: Pattern colors flicker during deletion in OccurrenceTimeline
  - Severity: LOW
  - Type: frontend

- [x] **BUG-028**: Chart animation desync during fast scrolling with slow data loading
  - Severity: LOW
  - Type: frontend

- [x] **BUG-029**: Opacity blinks during scrolling
  - Severity: LOW
  - Type: frontend

- [x] **BUG-030**: New data appears without fade-in
  - Severity: LOW
  - Type: frontend
