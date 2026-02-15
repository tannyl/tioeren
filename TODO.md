# Tiøren - Task List

Post-MVP backlog. For completed tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## High Priority

- [x] **TASK-080**: Fix security agent to test production scope, not dev environment
  - Description: pip-audit scans entire dev container (108 packages) instead of declared dependencies. Split requirements.txt into prod/dev, fix pip-audit to use `-r requirements.txt`, add production impact context to npm audit reporting.
  - Type: infrastructure
  - Dependencies: none

- [ ] **TASK-047**: Implement rate limiting
  - Description: Add rate limiting using slowapi: login 5/min per IP, general API 100/min per user. Return HTTP 429 with Retry-After header.
  - Type: backend
  - Dependencies: none

## Budget Post Rebuild (Spec Updated 2026-02-13)

> SPEC.md rewritten: active/archived budget post split (separate tables), two-level account binding model (counterparty on post, accounts on patterns), transfers without categories, amount occurrences for archived periods, transactions bind to patterns/occurrences (not posts).

- [x] **TASK-065**: Frontend - Budget post UI rebuild
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

- [x] **TASK-067**: Restructure amount pattern editor UI + backend validation
  - Description: Restructure pattern editor in BudgetPostModal:
    1. Replace 8-option recurrence dropdown with two toggles (pattern basis: period/date, repeats: yes/no)
    2. Move account selection right after amount field
    3. Remove redundant `date` field from `once` type - use `start_date` as occurrence date
    4. Remove `months` from `period_once` - use `start_date` year+month
    5. Enforce `end_date = null` for non-repeating types (once, period_once)
    6. Add "Validation Philosophy" to coding-standards.md
    7. Update SPEC.md recurrence pattern section
    8. Update backend schema validation and occurrence expansion
    9. Update all related tests
  - Type: both
  - Dependencies: TASK-065

- [x] **TASK-068**: Add `period_monthly` recurrence type
  - Description: Add monthly frequency for period-based repeating patterns. Currently period+repeats only supports yearly (select specific months). Add frequency toggle (Monthly/Yearly) so users can choose "every month from start onwards" without manual month selection.
  - Type: both
  - Dependencies: TASK-067

- [x] **TASK-070**: Bank day utility + bank_day_adjustment
  - Description: Bank day infrastructure and date adjustment overhaul:
    1. Create `api/utils/bank_days.py` with country-extensible `HolidayCalendar` pattern (ABC base + `DanishHolidayCalendar`). Registry dict maps country codes to calendar classes.
    2. Utility functions: `is_bank_day(date, country)`, `next_bank_day(date, country)`, `previous_bank_day(date, country)`, `nth_bank_day_in_month(year, month, n, from_end, country)`. All default `country="DK"`.
    3. Danish holidays computed algorithmically: Nytårsdag, Skærtorsdag, Langfredag, Påskedag, 2. Påskedag, Kristi Himmelfartsdag, Pinsedag, 2. Pinsedag, Grundlovsdag, Juledag, 2. Juledag.
    4. Replace `postpone_weekend: bool` with `bank_day_adjustment: "none" | "next" | "previous"` in RecurrencePattern schema.
    5. Period boundary rule: adjustment must stay within same month. If `next` would cross month end, use `previous` instead (and vice versa).
    6. Update occurrence expansion in `budget_post_service.py` to use new bank day utilities.
    7. Alembic data migration: existing `postpone_weekend: true` → `bank_day_adjustment: "next"`.
    8. Frontend: replace postpone_weekend checkbox with 3-option selector ("Ingen justering" / "Næste bankdag" / "Forrige bankdag"). Hide selector when recurrence type is `monthly_bank_day` or `yearly_bank_day`.
    9. Update SPEC.md recurrence pattern section.
    10. Comprehensive tests for bank day utilities + adjusted occurrence expansion.
  - Type: both
  - Dependencies: TASK-068

- [x] **TASK-071**: Expand relative weekday positions (1st-4th + last)
  - Description: Extend relative weekday support for monthly and yearly patterns:
    1. Expand `RelativePosition` enum: `first | second | third | fourth | last`.
    2. Update `_get_nth_weekday()` in budget_post_service to handle 2nd/3rd/4th occurrences.
    3. Update schema validation for `monthly_relative` and `yearly` (relative mode).
    4. Frontend: expand position dropdown from 2 options (Første/Sidste) to 5 (Første/Anden/Tredje/Fjerde/Sidste).
    5. Update SPEC.md and tests.
  - Type: both
  - Dependencies: TASK-068

- [x] **TASK-072**: Monthly and yearly bank day recurrence types
  - Description: Add bank day as third sub-type for monthly and yearly patterns:
    1. New recurrence types: `monthly_bank_day` and `yearly_bank_day`.
    2. New schema fields: `bank_day_number: int` (1-10, which bank day), `bank_day_from_end: bool` (false=from month start, true=from month end).
    3. `monthly_bank_day` requires: `bank_day_number` + `bank_day_from_end`. Optional: `interval`.
    4. `yearly_bank_day` requires: `bank_day_number` + `bank_day_from_end` + `month`. Optional: `interval`.
    5. `bank_day_adjustment` is irrelevant for these types — ignore/hide in UI, skip in backend expansion.
    6. Occurrence expansion uses `nth_bank_day_in_month()` from TASK-070 utility.
    7. Frontend: add "Bankdag" as third type option for monthly (alongside "Fast dag"/"Relativ ugedag") and yearly. When selected, show bank day number input + direction selector (fra start/fra slut).
    8. Update SPEC.md, TypeScript types, i18n keys, and tests.
  - Type: both
  - Dependencies: TASK-070

- [x] **TASK-073**: Bank day adjustment - support crossing month boundaries
  - Description: Add `bank_day_keep_in_month` boolean to RecurrencePattern. When true (default, current behavior), adjustment clamps to same month. When false, adjustment allows crossing month boundaries. Checkbox in UI when adjustment is active.
  - Type: both
  - Dependencies: TASK-070

## Budget Post UX Improvements

- [x] **TASK-074**: Fix spacing between empty state and "Tilføj mønster" button
  - Description: In BudgetPostModal, when no amount patterns exist, the "Tilføj mønster" button sits flush against the "Ingen beløbsmønstre endnu" info box with no visual spacing. When patterns DO exist, `.patterns-list` has `margin-bottom: var(--spacing-md)` which provides proper spacing, but `.info-message` (line ~1870) has no margin-bottom.
    **Fix:** Add `margin-bottom: var(--spacing-md)` to the `.info-message` CSS rule in BudgetPostModal.svelte.
  - Files: `ui/src/lib/components/BudgetPostModal.svelte` (CSS only, ~1 line)
  - Type: frontend
  - Dependencies: none

- [x] **TASK-079**: Use full month names in pattern editor dropdowns
  - Description: Month dropdown selects in the pattern editor use abbreviated i18n keys (`months.jan` etc.) but should show full month names (januar, februar, marts...). The yearly period month chip buttons are fine with abbreviations.
    **Fix:** Replace the `monthLabels` derived array (lines 654-667) and the `monthKey` lookups (lines 537, 585) with `formatMonth()` from `dateFormat.ts`. Create two derived arrays:
    - `monthLabelsFull` using `formatMonth(n, $locale, 'long')` for `<select>` dropdowns
    - `monthLabelsShort` using `formatMonth(n, $locale, 'short')` for chip buttons
    **Dropdowns to update (use full names):**
    1. `period_once` month select (~line 1015)
    2. Period repeating start period month select (~line 1044)
    3. Period repeating end period month select (~line 1079)
    4. Date-based `yearly` month select (~line 1410)
    **Keep abbreviations:**
    - Period yearly month chip buttons (~line 1120)
    **Also:** Remove `months.*` keys from `da.json` and `en.json` since `formatMonth()` via `Intl.DateTimeFormat` provides locale-correct month names without needing i18n keys.
  - Files:
    - `ui/src/lib/components/BudgetPostModal.svelte` (replace monthLabels, update selects and display functions)
    - `ui/src/lib/i18n/locales/da.json` (remove `months` section)
    - `ui/src/lib/i18n/locales/en.json` (remove `months` section)
  - Type: frontend
  - Dependencies: TASK-077

- [x] **TASK-082**: Ret weekly n>1 gentagelsestekst (fjern parentes)
  - Description: Weekly med interval>1 viser "Gentages hver {n}. uge ({weekday})" med parentes om ugedagen. Skal ændres til "Gentages {weekday} hver {n}. uge" (f.eks. "Gentages tirsdag hver 2. uge").
    **Fix:** Opdater `weeklyN` i18n-nøgle i da.json og en.json.
  - Files:
    - `ui/src/lib/i18n/locales/da.json` (ændr `weeklyN`)
    - `ui/src/lib/i18n/locales/en.json` (ændr `weeklyN`)
  - Type: frontend
  - Dependencies: none

- [x] **TASK-083**: Bankdagsjustering som separat sætning med keep_in_month info
  - Description: Bankdagsjusteringsteksten på pattern-kort tilføjes som komma-suffix og mangler info om "hold inden for måneden". Rettes til:
    1. Alle primære gentagelsestekster afsluttes med `.`
    2. Bankdagsjustering tilføjes som separat sætning med mellemrum
    3. Teksten afspejler om "hold inden for måneden" er slået til
    Nye tekster:
    - next: "Justeres efter behov til næste bankdag."
    - next + keep_in_month: "Justeres efter behov til næste eller nærmeste bankdag inden for samme måned."
    - previous: "Justeres efter behov til forrige bankdag."
    - previous + keep_in_month: "Justeres efter behov til forrige eller nærmeste bankdag inden for samme måned."
  - Files:
    - `ui/src/lib/i18n/locales/da.json` (fjern `bankDayAdjusted`, tilføj 4 nye nøgler)
    - `ui/src/lib/i18n/locales/en.json` (tilsvarende)
    - `ui/src/lib/components/BudgetPostModal.svelte` (opdater `formatPatternRecurrence()` linje 624-641)
  - Type: frontend
  - Dependencies: TASK-082

- [x] **TASK-081**: Refine pattern card description texts
  - Description: Refine TASK-076 natural language descriptions based on user feedback:
    1. Add "Gentages" prefix to all repeating patterns ("Gentages hver dag", "Gentages den 15. hver måned")
    2. One-time patterns show "Gentages ikke" instead of date/period info
    3. Bank day descriptions use natural language ("den første bankdag", "den sidste bankdag", "den 2. sidste bankdag") instead of "(fra start/slut)"
    4. Period yearly month lists use `Intl.ListFormat` for proper conjunction ("januar, marts og juni")
    5. Pattern card meta dates adapt by type: once shows just date, period-based shows month+year, date-based keeps full date range
    Add `formatList()` utility to `dateFormat.ts` using `Intl.ListFormat`.
  - Files:
    - `ui/src/lib/utils/dateFormat.ts` (add `formatList()`)
    - `ui/src/lib/components/BudgetPostModal.svelte` (update `formatPatternRecurrence()` and `.pattern-meta` template)
    - `ui/src/lib/i18n/locales/da.json` (update description keys)
    - `ui/src/lib/i18n/locales/en.json` (update English equivalents)
  - Type: frontend
  - Dependencies: TASK-076

- [x] **TASK-075**: Pattern editor as sub-view within budget post modal
  - Description: The pattern editor form (lines 904-1548 of BudgetPostModal.svelte) currently appears inline below the "Tilføj mønster" button, making the modal very long and forcing users to scroll. The pattern editor should instead **take over the modal content area** when active.
    **Solution (step-based sub-view):**
    1. Add state `activeView: 'main' | 'pattern-editor'` (default: `'main'`).
    2. "Tilføj mønster" / edit icon → set `activeView = 'pattern-editor'` (replaces `showPatternForm = true`).
    3. When `activeView === 'pattern-editor'`: hide main form content (direction, counterparty, category, pattern list), show only the pattern editor form.
    4. Add back-button at top: arrow-left icon + "Tilbage til budgetpost". Click → `activeView = 'main'`, cancel pattern.
    5. Modal header title changes to "Tilføj mønster" / "Rediger mønster" when in editor view.
    6. Modal footer save/cancel buttons hidden when in editor view (pattern has its own save/cancel).
    7. On modal close, reset `activeView = 'main'`.
  - Files:
    - `ui/src/lib/components/BudgetPostModal.svelte` (restructure template with `{#if activeView}` blocks, update handlers)
    - `ui/src/lib/i18n/locales/da.json` (add `budgetPosts.backToBudgetPost`: "Tilbage til budgetpost")
    - `ui/src/lib/i18n/locales/en.json` (add English equivalent)
  - Type: frontend
  - Dependencies: TASK-076

- [x] **TASK-076**: Rewrite pattern card descriptions as natural language sentences
  - Description: Pattern cards display technical labels like "Månedlig (fast dag) (Dag 15)" and "Ugentlig (Mandag)". These should be natural Danish sentences describing what happens, e.g. "Den 15. hver måned" or "Hver mandag".
    **Solution:** Rewrite `formatPatternRecurrence()` (lines 526-596 of BudgetPostModal.svelte) to produce human-readable descriptions:
    - `once`: "Engangsbetaling {date}" (e.g. "Engangsbetaling 15. feb 2025")
    - `daily`: "Hver dag" / "Hver {n}. dag"
    - `weekly`: "Hver {weekday}" / "Hver {n}. {weekday}" (e.g. "Hver mandag")
    - `monthly_fixed`: "Den {day}. hver måned" / "Den {day}. hver {n}. måned"
    - `monthly_relative`: "{Position} {weekday} hver måned" (e.g. "Første mandag hver måned")
    - `monthly_bank_day`: "{N}. bankdag hver måned (fra start/slut)"
    - `yearly`: "Den {day}. {month} hvert år" / "{Position} {weekday} i {month} hvert år"
    - `yearly_bank_day`: "{N}. bankdag i {month} hvert år (fra start/slut)"
    - `period_once`: "{Month} {year}" (e.g. "Jun 2025")
    - `period_monthly`: "Hver måned" / "Hver {n}. måned"
    - `period_yearly`: "{Month1}, {Month2}, ... hvert år"
    Also append bank day adjustment info when relevant (e.g. ", justeret til næste bankdag").
    Also format dates in `.pattern-meta` using `toLocaleDateString('da-DK', ...)` instead of raw ISO strings.
    Keep existing `budgetPosts.recurrence.*` label keys for the editor form toggles. Add new `budgetPosts.recurrence.description.*` keys for card display.
  - Files:
    - `ui/src/lib/components/BudgetPostModal.svelte` (rewrite `formatPatternRecurrence()`, update `.pattern-meta` date display)
    - `ui/src/lib/i18n/locales/da.json` (add `budgetPosts.recurrence.description.*` keys)
    - `ui/src/lib/i18n/locales/en.json` (add English equivalents)
  - Type: frontend
  - Dependencies: TASK-077

- [x] **TASK-077**: Create locale-aware date formatting utility
  - Description: Dates are displayed inconsistently: raw ISO strings (YYYY-MM-DD) in pattern cards, hardcoded `'da-DK'` in other components. Danish convention is "15. feb 2025" or "15/02/2025". Formatting should be centralized and driven by the active svelte-i18n locale.
    **Solution:**
    1. Create `ui/src/lib/utils/dateFormat.ts` with functions using `Intl.DateTimeFormat`:
       - `formatDate(isoString, locale)` -> full date ("15. februar 2025")
       - `formatDateShort(isoString, locale)` -> short ("15. feb 2025")
       - `formatDateCompact(isoString, locale)` -> numeric ("15/02/2025")
       - `formatMonth(monthNumber, locale, format?)` -> month name
       - `formatMonthYear(isoString, locale)` -> "februar 2025"
    2. Map i18n locale codes to Intl locales: `'da'` -> `'da-DK'`, `'en'` -> `'en-GB'`.
    3. Usage: `import { locale } from '$lib/i18n'` then `formatDateShort(dateStr, $locale ?? 'da')`.
    4. Migrate all existing hardcoded `'da-DK'` calls across components.
  - Files:
    - `ui/src/lib/utils/dateFormat.ts` (NEW - utility module)
    - `ui/src/lib/components/BudgetPostModal.svelte` (replace raw ISO strings)
    - `ui/src/lib/components/CategorizationModal.svelte` (replace hardcoded 'da-DK')
    - `ui/src/routes/(app)/budgets/[id]/+page.svelte` (replace hardcoded 'da-DK')
    - `ui/src/routes/(app)/budgets/[id]/transactions/+page.svelte` (replace hardcoded 'da-DK')
    - `ui/src/routes/(app)/budgets/[id]/forecast/+page.svelte` (replace hardcoded formatMonth/formatDate)
  - Type: frontend
  - Dependencies: TASK-074

- [x] **TASK-078**: Add occurrence timeline chart to BudgetPostModal
  - Description: Add an ECharts visualization in the budget post modal showing when the post's patterns produce occurrences over a navigable time window. Helps users understand what their patterns mean in practice. Must work for BOTH new (unsaved) posts and existing posts with local changes.
    **Solution:**
    1. **New preview API endpoint** (backend): Create `POST /api/budgets/{budget_id}/budget-posts/preview-occurrences` that accepts amount patterns in the request body and returns computed occurrences without needing a saved post.
       - Request body: `{ amount_patterns: AmountPatternCreate[], from_date: str, to_date: str }`
       - Response: `{ occurrences: [{ date: str, amount: int }] }` (same format as existing endpoint)
       - Create `expand_patterns_from_data()` in `budget_post_service.py` that reuses `_expand_recurrence_pattern()`. Refactor existing `expand_amount_patterns_to_occurrences()` to delegate to this function.
       - Reusable for future "what-if" scenarios (e.g. forecast with proposed changes).
    2. **Frontend API wrapper**: Add `previewOccurrences(budgetId, patterns, fromDate, toDate)` to `ui/src/lib/api/budgetPosts.ts`.
    3. **Chart component**: Create `ui/src/lib/components/OccurrenceTimeline.svelte`:
       - Props: `budgetId: string`, `patterns: AmountPattern[]` (current local patterns from the form)
       - 3-month sliding window starting from current month
       - Navigation: "Forrige" / "Næste" buttons + range label ("Feb 2026 - Apr 2026")
       - ECharts bar chart: X=dates, Y=amount in kr, bars colored with `--accent`
       - Tooltip with date + formatted amount. Loading spinner, empty state.
       - Height: 200px (compact for modal). Reactively re-fetches when patterns change (debounced).
    4. **Integration**: Render between "Beløbsmønstre" heading and pattern list. Pass current local `amountPatterns` array as prop.
    5. Follow ECharts patterns from `forecast/+page.svelte` (init, dispose, resize, CSS variable theming).
  - Files:
    - `api/services/budget_post_service.py` (add `expand_patterns_from_data()`, refactor existing function)
    - `api/schemas/budget_post.py` (add `PreviewOccurrencesRequest` schema)
    - `api/routes/budget_posts.py` (add `POST .../preview-occurrences` endpoint)
    - `tests/test_budget_post_occurrences.py` (add tests for preview endpoint)
    - `ui/src/lib/api/budgetPosts.ts` (add `previewOccurrences()` + types)
    - `ui/src/lib/components/OccurrenceTimeline.svelte` (NEW - chart component)
    - `ui/src/lib/components/BudgetPostModal.svelte` (import + render timeline)
    - `ui/src/lib/i18n/locales/da.json` (add `budgetPosts.timeline.*` keys)
    - `ui/src/lib/i18n/locales/en.json` (add English equivalents)
  - Type: both
  - Dependencies: TASK-075

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

- [x] **BUG-019**: Pattern editor uses same error message for missing amount and missing start date
  - Severity: LOW
  - Type: frontend

- [x] **BUG-020**: Pattern editor allows saving without selecting accounts (should be required for income/expense)
  - Severity: MEDIUM
  - Type: frontend

- [x] **BUG-021**: Saving budget post with incomplete pattern shows "[object Object]" error
  - Severity: MEDIUM
  - Type: frontend

- [x] **BUG-022**: Amount field integer overflow causes traceback leak (no upper bound on amount in Pydantic schema)
  - Severity: HIGH
  - Type: backend

- [x] **TASK-069**: Remove "Hver N." hints from interval fields in pattern editor
  - Description: The pattern editor shows "Hver 1." (or "Hver N.") as form hints below interval inputs for period-based and daily recurrence types. This doesn't provide useful information. Remove these hint spans.
  - Type: frontend
  - Dependencies: none

- [ ] **BUG-023**: Editing period_yearly pattern does not restore start period from start_date
  - Severity: LOW
  - Type: frontend
  - Note: When editing a `period_yearly` pattern, `patternPeriodYear`/`patternPeriodMonth` default to current date instead of extracting from the saved `start_date`. `period_monthly` and `period_once` correctly extract start period.

- [x] **BUG-024**: Occurrence timeline chart skips a day at DST transition (March 29)
  - Severity: MEDIUM
  - Type: frontend
  - Note: JavaScript millisecond-based day offset calculation (`Math.floor(ms / 86400000)`) breaks when DST starts (March 29, 2026 in Denmark). The day after DST has only 23 hours, causing `Math.floor(56.958) = 56` instead of 57. Two dates map to the same chart position, creating a visible gap. Fix: use `Date.UTC()` for DST-safe calendar day arithmetic.
