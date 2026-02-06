# Tiøren - Task List

Post-MVP backlog. For completed MVP tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## High Priority

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

- [ ] **TASK-036**: CSV transaction import
  - Description: Upload CSV from bank, map columns, detect duplicates, import transactions. Save mapping as reusable profile per account.
  - Type: both
  - Dependencies: none

- [ ] **TASK-037**: Auto-categorization rules engine
  - Description: Create Rule model and UI. Match transactions by description/amount/date patterns. Support auto, confirm, and receipt-required modes. Priority-ordered rule execution.
  - Type: both
  - Dependencies: none

## Medium Priority

- [ ] **TASK-038**: Shared budgets
  - Description: Budget sharing with owner/member roles. Email invitation flow with 7-day token. Members get full edit access; only owners manage membership and deletion.
  - Type: both
  - Dependencies: none

## Low Priority

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

## Deferred Bugs

- [ ] **BUG-004**: Sidebar navigation links contain empty budget IDs
  - Severity: LOW
  - Description: On /budgets list page (no budget selected), sidebar renders links like `/budgets//transactions`. Should hide or disable budget-specific nav when no budget context.
  - Type: frontend
