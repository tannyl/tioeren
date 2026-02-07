# Tiøren - Task List

Post-MVP backlog. For completed MVP tasks, see [docs/MVP-HISTORY.md](docs/MVP-HISTORY.md).

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed
- `[!]` - Blocked

---

## High Priority

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

- [ ] **SEC-001**: Static Analysis (SAST)
  - Description: Run Semgrep on api/ and ui/src/ to find hardcoded secrets, injection patterns, etc.
  - Type: security
  - Dependencies: TASK-044

- [ ] **SEC-002**: Dependency Scan (SCA)
  - Description: Run pip-audit and npm audit for known CVEs in dependencies.
  - Type: security
  - Dependencies: TASK-044

- [ ] **SEC-003**: Authentication Testing
  - Description: Test unauthenticated access, invalid sessions, login failures.
  - Type: security
  - Dependencies: TASK-044

- [ ] **SEC-004**: Authorization (BOLA/IDOR)
  - Description: Test cross-user resource access - User A accessing User B's budgets/transactions.
  - Type: security
  - Dependencies: TASK-044

- [ ] **SEC-005**: Input Validation (Injection)
  - Description: Test SQL injection and XSS payloads on API endpoints.
  - Type: security
  - Dependencies: TASK-044

- [ ] **SEC-006**: API Security & Business Logic
  - Description: Test CORS, rate limiting, sensitive data exposure, error handling.
  - Type: security
  - Dependencies: TASK-044

---

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

## Critical Bugs

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
