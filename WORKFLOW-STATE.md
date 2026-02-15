# Workflow State

This file tracks the current state of the development workflow across sessions.

## Current

- **Active task:** None
- **Phase:** Post-MVP Development
- **Last completed:** TASK-078 (Add occurrence timeline chart to BudgetPostModal)
- **Review attempts for current task:** 0

### TASK-068 Progress

Plan: `/root/.claude/plans/functional-strolling-creek.md`

| Step | Description | Status |
|------|-------------|--------|
| 1. Docs | Update SPEC.md | Done |
| 2. Backend | Schema, service, tests | Done (343 tests pass) |
| 3. Frontend | Types, i18n, component | Done |
| 4. Review | reviewer subagent | APPROVED |
| 5. QA | Browser testing | PASS |
| 6. Security | Security testing | PASS |
| 7. Commit | Code + docs | Done (71f5915) |

### TASK-067 Progress (completed)

Plan: `/root/.claude/plans/federated-stirring-muffin.md`

| Step | Description | Status |
|------|-------------|--------|
| 1. Docs | Update SPEC.md + coding-standards.md | Done |
| 2. Backend | Schema, service, tests | Done (75 tests pass) |
| 3. Frontend | Types, i18n, component restructure | Done |
| 4. Review backend | reviewer subagent | APPROVED |
| 5. Review frontend | reviewer subagent | APPROVED (after fixes) |
| 6. QA | Browser testing | PASS |
| 7. Security | Security testing | PASS |
| 8. Commit | Code + docs | Done (195fb17) |

**Key changes made so far:**
- `coding-standards.md`: Added "Validation Philosophy" section
- `SPEC.md`: Rewrote gentagelsesmønstre section (two-axis: period/date x repeats/once)
- `api/schemas/budget_post.py`: Removed `date` field from RecurrencePattern, removed `months` requirement from `period_once`, added end_date null validation for non-repeating types
- `api/services/budget_post_service.py`: Handle `once` and `period_once` in caller using `start_date`, removed from `_expand_recurrence_pattern`
- `tests/test_recurrence_pattern.py`: Rewrote once/period_once tests
- `tests/test_budget_post_occurrences.py`: Rewrote once/period_once expansion tests

### Recent SPEC Changes (2026-02-13)

Major budget post model rebuild:
- **Active/archived split**: Separate tables (`budget_posts` for active, `archived_budget_posts` for snapshots)
- **Active posts have NO period**: Only one active post per category, forward-looking
- **Two-level account binding**: Counterparty on budget post (EXTERNAL/loan/savings), accounts on amount patterns (NORMAL)
- **Transfers without categories**: Direction field (income/expense/transfer), transfers have no category
- **Amount occurrences**: Archived posts store concrete `amount_occurrences` instead of patterns
- **Transaction binding**: Transactions bind to amount patterns (active) or amount occurrences (archived), not budget posts directly
- **Open questions**: Archiving process timing, post-archive transaction handling, accumulation carry-over

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| MVP (Phases 1-9) | Complete | 36/36 dev + 8/8 QA |
| Post-MVP | In progress | 8 tasks + 2 bug fixes |
| MVP Compliance Review | Complete | 7 new tasks added (TASK-045 to TASK-051) |

For detailed history, see `docs/MVP-HISTORY.md`.

## Task History

| Task | Status | Review Result | Completed | Commit |
|------|--------|---------------|-----------|--------|
| TASK-042 | Complete | APPROVED | 2026-02-05 | 4865843 |
| QA-009 | Complete | PASS | 2026-02-05 | - |
| QA-010 | Complete | PASS | 2026-02-06 | f6f2e7f |
| BUG-004 | Complete | APPROVED | 2026-02-06 | cdfb6d1 |
| BUG-005 | Complete | N/A (infrastructure) | 2026-02-06 | 3972bf4 |
| TASK-043 | Complete | APPROVED | 2026-02-07 | a6f38f8 |
| BUG-006 | Complete | APPROVED | 2026-02-07 | 9f10dd8 |
| TASK-044 | Complete | N/A (infrastructure) | 2026-02-07 | c34c8a2 |
| SEC-001 | Complete | PASS | 2026-02-07 | - |
| SEC-002 | Complete | 6 vulns (dev deps) | 2026-02-07 | - |
| SEC-003 | Complete | 1 MEDIUM, 3 LOW | 2026-02-07 | - |
| SEC-004 | Complete | PASS | 2026-02-07 | - |
| SEC-005 | Complete | PASS | 2026-02-07 | - |
| SEC-006 | Complete | 2 HIGH, 5 MED, 1 LOW | 2026-02-07 | - |
| BUG-007 | Complete | APPROVED | 2026-02-07 | - |
| BUG-008 | Complete | APPROVED | 2026-02-07 | - |
| BUG-009 | Complete | APPROVED | 2026-02-08 | - |
| MVP Review | Complete | N/A | 2026-02-08 | - |
| TASK-045 | Complete | APPROVED | 2026-02-08 | 37ce3fa |
| TASK-046 | Complete | APPROVED | 2026-02-08 | 816b2c3 |
| TASK-054 | Complete | APPROVED | 2026-02-11 | f2c5f35 |
| TASK-053 | Complete | APPROVED | 2026-02-11 | fb79d0c |
| TASK-052 | Complete | APPROVED | 2026-02-11 | a8ecba0 |
| TASK-055 | Complete | APPROVED | 2026-02-12 | 9257a4f |
| TASK-059 | Complete | APPROVED | 2026-02-12 | 83fa1f6 |
| TASK-060 | Complete | APPROVED | 2026-02-12 | 3a224f5 |
| TASK-061 | Complete | APPROVED | 2026-02-14 | b7d7b01 |
| TASK-062 | Complete | APPROVED | 2026-02-14 | 33bd940 |
| TASK-063 | Complete | APPROVED | 2026-02-14 | 178c849 |
| TASK-064 | Complete | APPROVED | 2026-02-14 | b2a2a2c |
| TASK-065 | Complete | APPROVED | 2026-02-14 | b99aec8 |
| BUG-019 | Complete | APPROVED | 2026-02-14 | 9c27de2 |
| BUG-020 | Complete | APPROVED | 2026-02-14 | 9c27de2 |
| BUG-021 | Complete | APPROVED | 2026-02-14 | 9c27de2 |
| TASK-067 | Complete | APPROVED | 2026-02-14 | 195fb17 |
| BUG-022 | Complete | APPROVED | 2026-02-14 | a2caf47 |
| TASK-068 | Complete | APPROVED | 2026-02-14 | 71f5915 |
| TASK-069 | Complete | APPROVED | 2026-02-14 | 3b516fb |
| TASK-070 | Complete | APPROVED | 2026-02-14 | 9ed957d |
| TASK-071 | Complete | APPROVED | 2026-02-14 | a2cca06 |
| TASK-072 | Complete | APPROVED | 2026-02-15 | faa0774 |
| TASK-073 | Complete | APPROVED | 2026-02-15 | ef35f2c |
| TASK-074 | Complete | APPROVED | 2026-02-15 | a5fb9fd |
| TASK-077 | Complete | APPROVED | 2026-02-15 | 22374a6 |
| TASK-080 | Complete | N/A (infrastructure) | 2026-02-15 | 27cefcd |
| TASK-076 | Complete | APPROVED | 2026-02-15 | a0d671d |
| TASK-081 | Complete | APPROVED | 2026-02-15 | 957e7ab |
| TASK-082 | Complete | APPROVED | 2026-02-15 | 3efaebd |
| TASK-083 | Complete | APPROVED | 2026-02-15 | 3efaebd |
| TASK-079 | Complete | APPROVED | 2026-02-15 | 5cd12a2 |
| TASK-075 | Complete | APPROVED | 2026-02-15 | 507f34e |
| TASK-078 | Complete | APPROVED | 2026-02-15 | 12527b8 |

## Blocked Tasks

None currently blocked.

## Bug Log

| Bug ID | Severity | Type | Description | Status |
|--------|----------|------|-------------|--------|
| BUG-017 | MEDIUM | backend | GET archived-budget-posts year param allows integer overflow -> 500 + traceback leak | OPEN |
| BUG-018 | LOW | backend | Archive endpoint allows future period archiving (e.g. 2099-12) | OPEN |
| BUG-019 | LOW | frontend | Pattern editor uses same error message for missing amount and missing start date | FIXED |
| BUG-020 | MEDIUM | frontend | Pattern editor allows saving without selecting accounts (income/expense) | FIXED |
| BUG-021 | MEDIUM | frontend | Saving budget post with incomplete pattern shows "[object Object]" error | FIXED |
| BUG-022 | HIGH | backend | Amount field integer overflow causes traceback leak (no upper bound on amount) | FIXED |
| BUG-023 | LOW | frontend | Editing period_yearly pattern does not restore start period from start_date | OPEN |

## Session Log

| Session | Started | Ended | Tasks Completed |
|---------|---------|-------|-----------------|

---

## How to Use

1. **On session start:** Read this file to understand current state
2. **During work:** Update "Active task" and "Review attempts"
3. **On task completion:** Add to Task History, update Progress Summary
4. **On bug found:** Add to Bug Log with severity and type
5. **On session end:** Add entry to Session Log

## Review Failure Protocol

If a task fails review 3 times:
1. Update "Review attempts" to 3
2. Add task to "Blocked Tasks" with reason
3. Stop and ask user for guidance
4. Do NOT proceed to dependent tasks
