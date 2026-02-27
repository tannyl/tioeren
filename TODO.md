# Tiøren - Task List

Post-MVP backlog. For completed tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## Category → category_path Refactoring

- [x] **TASK-100**: Opdater SPEC.md med ny category_path model
  - Description: Fjern Category-entitet fra spec, tilføj category_path TEXT[] og display_order INTEGER[] til BudgetPost/ArchivedBudgetPost. Opdater alle relaterede sektioner.
  - Type: infrastructure
  - Dependencies: none

- [x] **TASK-101**: Backend - Fjern Category, tilføj category_path
  - Description: Alembic migration (drop categories, tilføj nye kolonner), slet Category model/schema/service/routes, opdater BudgetPost/ArchivedBudgetPost models, opdater alle services og routes.
  - Type: backend
  - Dependencies: TASK-100

- [x] **TASK-102**: Backend - Opdater tests for category_path
  - Description: Slet category tests, opdater alle test-fixtures til at bruge category_path i stedet for Category-objekter.
  - Type: backend
  - Dependencies: TASK-101

- [x] **TASK-103**: Frontend - Budgetpost-trævisning og kategoriseringsmodal
  - Description: Byg hierarkisk træ fra category_path præfikser. Opdater CategorizationModal til at hente budgetposter direkte i stedet for kategorier.
  - Type: frontend
  - Dependencies: TASK-101

- [x] **TASK-104**: Frontend - Kategori-sti input med autocomplete
  - Description: Erstat category dropdown i BudgetPostModal med tekstfelt med " > " separator og autocomplete fra eksisterende stier.
  - Type: frontend
  - Dependencies: TASK-103

- [x] **TASK-105**: Frontend - Breadcrumb chip input til kategori-sti
  - Description: Erstat tekst-input med breadcrumb-stil chips. Hvert niveau bliver en visuel chip med pil-form. Tastatur-navigation i autocomplete (op/ned/enter). Level-aware autocomplete (viser kun children af aktuel sti).
  - Type: frontend
  - Dependencies: TASK-104

## Budget Post & Account Model Redesign

- [x] **TASK-107**: Opdater SPEC.md med ny konto- og budgetpost-model
  - Description: Opdater alle sektioner i SPEC.md: 4 kontotyper (tilføj kassekredit), fjern counterparty-koncept, ny kontobinding-model (pulje + subset), via-konto, kreditgrænse erstatter kan_gå_i_minus, fjern kredit-datakilde.
  - Type: infrastructure
  - Dependencies: none

- [x] **TASK-108**: Backend - Opdater Account model og enum
  - Description: Alembic migration: tilføj kassekredit til AccountPurpose enum (4 værdier). Fjern kredit fra AccountDatasource enum (3 værdier). Erstat can_go_negative boolean med credit_limit (BIGINT, nullable, øre). Tilføj locked boolean (default false). Fjern must_be_covered. Opdater Account model, schema, validering.
  - Type: backend
  - Dependencies: TASK-107

- [x] **TASK-109**: Backend - Opdater BudgetPost model (fjern counterparty, tilføj account_ids)
  - Description: Alembic migration: fjern counterparty_type og counterparty_account_id fra budget_posts. Tilføj account_ids (JSONB, UUID array). Tilføj via_account_id (UUID, nullable, FK accounts). Fjern NORMAL-begrænsning på transfer-konti. Opdater model, schema, validering, service.
  - Type: backend
  - Dependencies: TASK-108

- [x] **TASK-110**: Backend - Opdater AmountPattern kontobinding
  - Description: Opdater account_ids på amount_patterns: fjern NORMAL-begrænsning. Tilføj validering at account_ids er subset af budgetpostens account_ids. Opdater schema og service.
  - Type: backend
  - Dependencies: TASK-109

- [x] **TASK-111**: Backend - Opdater tests for ny model
  - Description: Opdater alle test-fixtures og tests der bruger counterparty, kan_gå_i_minus, kredit-datakilde, eller NORMAL-begrænsning. Tilføj tests for nye scenarier (udgift fra opsparing, overførsel normal→opsparing, etc.)
  - Type: backend
  - Dependencies: TASK-110

- [x] **TASK-112**: Frontend - Opdater BudgetPostModal for ny model
  - Description: Fjern counterparty-valg (modpart-dropdown). Tilføj multi-select for konti-pulje (alle kontotyper, maks 1 ikke-normal). Opdater overførsel-flow til alle kontotyper. Tilføj valgfrit via-konto felt. Opdater API-kald.
  - Type: frontend
  - Dependencies: TASK-109

- [x] **TASK-113**: Frontend - Opdater kontotyper og account forms
  - Description: Tilføj kassekredit som kontotype. Erstat kan_gå_i_minus toggle med kreditgrænse-input. Fjern kredit-datakilde. Tilføj låst-toggle (kun for opsparing). Opdater i18n-nøgler.
  - Type: frontend
  - Dependencies: TASK-108

- [x] **TASK-114**: Frontend - Opdater budget post list visning
  - Description: Opdater budgetpost-listen til at vise nye kontobindinger. Overførsler vises mellem alle kontotyper. Tilføj ikon/label for via-konto hvis sat. Fjern gammel counterparty-visning.
  - Type: frontend
  - Dependencies: TASK-112

## Credit Limit & Kontobinding Rettelser

- [x] **TASK-115**: Backend - credit_limit fortegnskonvention
  - Description: credit_limit skal gemmes som negativt tal (gulv-semantik per SPEC). Alembic migration der negerer eksisterende positive værdier. Tilføj `le=0` constraint i AccountCreate/AccountUpdate schema. Defense-in-depth validering i account_service. Ret tests til negative værdier, tilføj test for afvisning af positiv credit_limit.
  - Type: backend
  - Dependencies: none
  - Filer: `api/schemas/account.py`, `api/services/account_service.py`, `tests/test_account_api.py`, ny Alembic migration

- [x] **TASK-116**: Frontend - credit_limit checkbox UX og fortegnskonvention
  - Description: Erstat forvirrende "tom = ingen grænse" med checkbox "Har kreditgrænse". Når unchecked sendes null (ingen grænse). Når checked vises beløb-input. Bruger indtaster positivt beløb, frontend negerer til negativt øre før afsendelse. Ved load fra API negeres tilbage til positivt for display. Default for nye konti: checked med værdi 0. Opdater i18n-nøgler.
  - Type: frontend
  - Dependencies: TASK-115
  - Filer: `ui/src/lib/components/AccountModal.svelte`, `ui/src/lib/i18n/locales/da.json`

- [x] **TASK-117**: Backend + SPEC - kontobinding gensidig eksklusivitet
  - Description: Opdater validering så kontobinding er gensidigt eksklusiv - ENTEN 1+ normale konti ELLER præcis 1 ikke-normal konto (opsparing/lån/kassekredit). Kan ikke blandes. Via-konto kun tilladt når en ikke-normal konto er valgt (ikke med normale konti). Opdater SPEC.md (linje 337-338, 416, 347-360). Tilføj tests for mutual exclusivity og via-konto restriktion.
  - Type: backend
  - Dependencies: none
  - Filer: `api/services/budget_post_service.py` (create ~linje 180-208, update ~linje 497-525), `SPEC.md`, budget post tests

- [x] **TASK-118**: Frontend - kontobinding segment control, via-konto restriktion, mønster-synlighed
  - Description: Redesign kontovalg i BudgetPostModal med to-tilstands segment control ("Normal konti" | "Særlig konto"). Normal-tilstand viser checkboxes for normale konti (multi-select). Særlig-tilstand viser dropdown for én ikke-normal konto. Via-konto kun vist i særlig-tilstand. Mønster-konti på beløbsmønster-editor kun vist når 2+ konti er valgt i puljen. Tilføj i18n-nøgler og CSS for segment control.
  - Type: frontend
  - Dependencies: TASK-117
  - Filer: `ui/src/lib/components/BudgetPostModal.svelte`, `ui/src/lib/i18n/locales/da.json`

## Container Model Redesign

- [x] **TASK-119**: Update SPEC.md with new container model
  - Description: Complete rewrite of Account section to new Container (Beholder) model. Three types (cashbox/pengekasse, piggybank/sparegris, debt/gældsbyrde). Remove datasource, move currency to budget, add bank link, add interest/required-payment for debt, add container behavior rules. Update ALL referencing sections: domain overview, "til rådighed", budget post binding, transfer flows, UI wireframes, navigation, dashboard. Replace all account terminology.
  - Type: infrastructure
  - Dependencies: none

- [x] **TASK-120**: Alembic migration - accounts → containers
  - Description: Destructive migration: rename accounts→containers table, replace account_purpose enum med container_type (cashbox/piggybank/debt), drop datasource enum, drop currency fra containers, tilføj currency til budgets, tilføj nye kolonner (bank_name, bank_account_name, bank_reg_number, bank_account_number, overdraft_limit, allow_withdrawals, interest_rate, interest_frequency, required_payment). Migrer data: normal→cashbox, savings→piggybank, loan/kassekredit→debt. Flyt credit_limit→overdraft_limit for cashbox. Omdøb account_ids→container_ids i budget_posts og amount_patterns. Omdøb account_id→container_id i transactions. Omdøb alle account FK-kolonner i budget_posts.
  - Type: infrastructure
  - Dependencies: TASK-119

- [x] **TASK-121**: Backend - Container model, enum og schemas
  - Description: Opret `api/models/container.py` med ContainerType enum (cashbox/piggybank/debt) og Container klasse med alle nye felter. Opret `api/schemas/container.py` med ContainerCreate/Update/Response med type-specifik Pydantic-validering (type-constraints fra SPEC). Opdater `api/models/__init__.py`. Slet account.py model og schema.
  - Type: backend
  - Dependencies: TASK-120

- [x] **TASK-122**: Backend - Container service og routes
  - Description: Opret `api/services/container_service.py` med CRUD og type-specifik validering. Opret `api/routes/containers.py` med REST endpoints på `/budgets/{budget_id}/containers`. Opdater `api/routes/__init__.py` og `api/main.py`. Tilføj currency felt til Budget model. Omdøb accounts relationship til containers. Slet account_service.py og accounts routes.
  - Type: backend
  - Dependencies: TASK-121

- [x] **TASK-123**: Backend - Opdater budget post model/schemas/service for container-refs
  - Description: Omdøb alle account-referencer i budget post kode: model kolonner/FKs/relationships (account→container), schema felter, service validering (AccountPurpose.NORMAL→ContainerType.CASHBOX). Omdøb account_ids→container_ids i amount_pattern model.
  - Type: backend
  - Dependencies: TASK-121

- [x] **TASK-124**: Backend - Opdater transaction, dashboard og forecast for container-refs
  - Description: Opdater transaction model (account_id→container_id, FK→containers.id). Opdater transaction_service, transaction routes, dashboard schemas (AccountBalance→ContainerBalance), dashboard_service og forecast_service (Account→Container, NORMAL→CASHBOX).
  - Type: backend
  - Dependencies: TASK-121

- [x] **TASK-125**: Backend - Opdater alle tests for container model
  - Description: Opdater ~12 testfiler: omdøb test_account_api.py→test_container_api.py, opdater alle fixtures/assertions. Opdater test_budget_post_validation, test_dashboard, test_forecast_*, test_transaction_*, test_archived_budget_posts, test_amount_*, test_budget_post_occurrence_endpoints. Alle: AccountPurpose→ContainerType, endpoint URLs, fixture data.
  - Type: backend
  - Dependencies: TASK-122, TASK-123, TASK-124

- [x] **TASK-126**: Frontend - Container API client, types og i18n
  - Description: Opret `ui/src/lib/api/containers.ts` med Container interface og CRUD funktioner. Slet accounts.ts. Opdater dashboard.ts (AccountBalance→ContainerBalance), budgetPosts.ts (account_*→container_*), transactions.ts (account_id→container_id). Opdater da.json: erstat account.* nøgler med container.*, tilføj type labels (Pengekasse/Sparegris/Gældsbyrde), tilføj nøgler for nye felter.
  - Type: frontend
  - Dependencies: TASK-122

- [x] **TASK-127**: Frontend - ContainerModal med type-specifikke felter
  - Description: Opret ContainerModal.svelte med type-vælger (pengekasse/sparegris/gældsbyrde). Fælles: navn, startsaldo. Banktilknytning (sammenfoldelig): bank_name, bank_account_name, bank_reg_number, bank_account_number. Pengekasse: overdraft_limit (checkbox + beløb med negering). Sparegris: locked checkbox. Gæld: credit_limit (påkrævet, negering), allow_withdrawals, interest_rate, interest_frequency (dropdown), required_payment. Slet AccountModal.svelte.
  - Type: frontend
  - Dependencies: TASK-126

- [x] **TASK-128**: Frontend - Settings page beholder-håndtering
  - Description: Opdater settings side: Account→Container imports/CRUD, AccountModal→ContainerModal, vis beholdertype labels/badges, tilføj currency felt til budget-indstillinger (nyt budget-felt), fjern per-beholder currency.
  - Type: frontend
  - Dependencies: TASK-127

- [x] **TASK-129**: Frontend - BudgetPostModal beholder-binding opdatering
  - Description: Omdøb alle account_ids→container_ids, via_account_id→via_container_id osv. Account→Container imports. listAccounts→listContainers. Segment control: "Normal konti"→"Pengekasser", "Særlig konto"→"Særlig beholder". Cashbox=multi-select, non-cashbox=single-select. Via-container kun for non-cashbox.
  - Type: frontend
  - Dependencies: TASK-126

- [x] **TASK-130**: Frontend - Dashboard og transaktionssider beholder-opdatering
  - Description: Dashboard: account CSS klasser→container, type labels, grupper "til rådighed" (cashbox). Transaktioner: account filter→container filter. TransactionModal: account→container valg. CategorizationModal: opdater account refs.
  - Type: frontend
  - Dependencies: TASK-126

- [x] **TASK-131**: Frontend - Navigation omstrukturering til 8 punkter
  - Description: Opdater navigation fra 5 til 8 punkter per SPEC: Overblik, Pengekasser, Sparegrise, Gældsbyrder, Budgetposter, Transaktioner, Forecast, Indstillinger. Desktop: sidebar med 8 punkter. Mobil: grupper Pengekasser/Sparegrise/Gæld under "Beholdere" tab eller "Mere"-knap. Opdater i18n nav nøgler.
  - Type: frontend
  - Dependencies: TASK-126

- [x] **TASK-132**: Frontend - Budget API opdatering for currency felt
  - Description: Currency flyttet fra container til budget. Opdater budgets.ts: tilføj currency til Budget/BudgetCreate/BudgetUpdate interfaces. Opdater budget settings form: tilføj currency input. Erstat account.currency med budget.currency.
  - Type: frontend
  - Dependencies: TASK-122

- [x] **TASK-133**: Frontend - Pengekasser (cashbox) listeside
  - Description: Opret route `budgets/[id]/pengekasser/+page.svelte`. Vis alle pengekasse-beholdere med saldo, overtræk-status. "Til rådighed" opsummering (sum af alle pengekasse-saldi). Opret/rediger/slet via ContainerModal (pre-set type=cashbox). Vis banktilknytning hvis til stede.
  - Type: frontend
  - Dependencies: TASK-127, TASK-131

- [x] **TASK-134**: Frontend - Sparegrise (piggybank) listeside
  - Description: Opret route `budgets/[id]/sparegrise/+page.svelte`. Vis alle sparegris-beholdere med saldo, låst-status. Total opsparings-opsummering. Opret/rediger/slet via ContainerModal (pre-set type=piggybank).
  - Type: frontend
  - Dependencies: TASK-127, TASK-131

- [x] **TASK-135**: Frontend - Gældsbyrder (debt) listeside
  - Description: Opret route `budgets/[id]/gaeldsbyrder/+page.svelte`. Vis alle gælds-beholdere med saldo, kreditramme, rente, krævet afdrag. Total gælds-opsummering. Vis lån vs kassekredit (allow_withdrawals flag). Opret/rediger/slet via ContainerModal (pre-set type=debt).
  - Type: frontend
  - Dependencies: TASK-127, TASK-131

## Remove BudgetPostType

- [x] **TASK-136**: Backend - Remove BudgetPostType and fixed_expenses
  - Description: Remove BudgetPostType enum, type column from budget_posts/archived_budget_posts, accumulate-requires-ceiling validation, and fixed_expenses from dashboard. Alembic migration to drop column and enum. Update all tests.
  - Type: backend
  - Dependencies: none

- [x] **TASK-137**: Frontend - Remove type UI and fixed expenses
  - Description: Remove type selector from BudgetPostModal, type badges from budget post list, FixedExpense from dashboard, and related i18n keys. Always show accumulate checkbox.
  - Type: frontend
  - Dependencies: TASK-136

- [x] **TASK-138**: Backend - Restrict accumulate to expense direction
  - Description: Add validation rejecting accumulate=true for income/transfer budget posts. Update schema descriptions. Add tests.
  - Type: backend
  - Dependencies: TASK-136

- [x] **TASK-139**: Frontend - Hide accumulate for non-expense
  - Description: Only show accumulate checkbox when direction is "expense". Reset to false when switching away from expense.
  - Type: frontend
  - Dependencies: TASK-138

## Strict container_ids on Amount Patterns

- [x] **TASK-140**: Strict container_ids on amount patterns (backend + frontend + SPEC)
  - Description: Make container_ids non-nullable for income/expense patterns. Backend: reject null/empty, require non-empty subset of post pool. Frontend: pre-select all containers on new patterns, validate min 1 selected, always send explicit list. Data migration for existing null/empty. Update SPEC.md.
  - Type: both
  - Dependencies: none

- [x] **TASK-141**: Tre-delt beholder-vælger i BudgetPostModal
  - Description: Erstat to-delt segment control (Pengekasser/Særlig beholder) med tre-delt (Pengekasser/Sparegrise/Gældsbyrder). Hver type får sin egen knap og indhold. Backend uændret.
  - Type: frontend
  - Dependencies: none

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

- [x] **TASK-106**: Clone amount pattern button
  - Description: Add a clone button on pattern cards (left of delete) that opens the add-pattern dialog pre-filled with the source pattern's values. Allows quick duplication with optional modifications.
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

- [ ] **BUG-036**: Transactions page fails to load - ReferenceError: accounts is not defined
  - Severity: CRITICAL
  - Type: frontend
  - Note: Regression from Account→Container migration. `transactions/+page.svelte` still references `accounts` variable (line ~345) which no longer exists after renaming to containers.

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

- [x] **BUG-031**: Pattern colors unstable across dialog open/close and view switches
  - Severity: MEDIUM
  - Type: frontend
  - Note: patternIdCounter and patternColorIndices not reset on dialog close. Pattern IDs use unnecessary "pattern-" prefix. Fix: use numeric _clientId as direct color index, reset counter on open, remove patternColorIndices middleman.
