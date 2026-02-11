# Workflow State

This file tracks the current state of the development workflow across sessions.

## Current

- **Active task:** None
- **Phase:** Post-MVP Development
- **Last completed:** TASK-054 (New recurrence model)
- **Review attempts for current task:** 0

### Recent SPEC Changes (2026-02-11)

Updated budget post model:
- Removed "løbende" type → merged into "loft" with akkumuler option
- Added "beløbsmønster" concept (1+ patterns per budget post)
- New recurrence model: date-based vs period-based
- Clarified "retning" (indtægt/udgift) vs "type" (fast/loft)

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| MVP (Phases 1-9) | Complete | 36/36 dev + 8/8 QA |
| Post-MVP | In progress | 4 tasks + 2 bug fixes |
| MVP Compliance Review | Complete | 7 new tasks added (TASK-045 to TASK-051) |

For detailed MVP history, see `docs/MVP-HISTORY.md`.

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
| TASK-054 | Complete | APPROVED | 2026-02-11 | - |

## Blocked Tasks

None currently blocked.

## Bug Log

Track bugs found during development and QA here. For MVP bugs, see `docs/MVP-HISTORY.md`.

| Bug ID | Severity | Type | Description | Status |
|--------|----------|------|-------------|--------|
| BUG-013 | HIGH | both | Budget Post creation fails silently for ceiling/rolling types | NOT_REPRODUCED |
| BUG-014 | MEDIUM | frontend | Initial route load returns 404 | NOT_REPRODUCED |
| BUG-015 | MEDIUM | frontend | Cannot create budget post with 0 kr minimum (falsy check) | FIXED |
| BUG-004 | LOW | frontend | Sidebar nav links contain empty budget IDs when no budget selected | FIXED |
| BUG-005 | LOW | frontend | Root path shows useless page for logged-in users + English text | FIXED |
| BUG-006 | CRITICAL | frontend | Infinite loop when clicking transaction - $effect circular dependency | FIXED |
| BUG-007 | MEDIUM | frontend | Budget dropdown doesn't update dashboard or stay on current page | FIXED |
| BUG-008 | LOW | frontend | Budget dropdown shows "Indlæser..." after creating new budget | FIXED |
| BUG-009 | MEDIUM | frontend | Transactions/Settings don't update when switching budgets | FIXED |

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
