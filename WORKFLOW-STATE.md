# Workflow State

This file tracks the current state of the development workflow across sessions.

## Current

- **Active task:** None
- **Phase:** Credit Limit & Kontobinding Rettelser
- **Last completed:** TASK-114 (Frontend - budget post list display)
- **Upcoming:** TASK-115 + TASK-117 (kan køre parallelt), derefter TASK-116 + TASK-118
- **Review attempts for current task:** 0

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| MVP (Phases 1-9) | Complete | 36/36 dev + 8/8 QA |
| Post-MVP | In progress | 9 tasks + 8 bug fixes |
| MVP Compliance Review | Complete | 7 new tasks added (TASK-045 to TASK-051) |
| Budget Post Rebuild | Complete | 4 backend + 4 frontend tasks |
| Budget Post UX | Complete | 13 tasks |
| Budget Post & Account Model Redesign | Complete | 8 tasks (TASK-107–114) |
| OccurrenceTimeline Improvements | Complete | TASK-087–094, BUG-025–030 |

For detailed history, see `docs/MVP-HISTORY.md`.

## Task History (Recent)

| Task | Status | Review Result | Completed | Commit |
|------|--------|---------------|-----------|--------|
| TASK-079 | Complete | APPROVED | 2026-02-15 | 5cd12a2 |
| TASK-075 | Complete | APPROVED | 2026-02-15 | 507f34e |
| TASK-078 | Complete | APPROVED | 2026-02-15 | 12527b8 |
| BUG-024 | Complete | APPROVED | 2026-02-15 | f6ef47a |
| TASK-086 | Complete | N/A (infrastructure) | 2026-02-17 | a574900 |
| TASK-084 | Complete | APPROVED | 2026-02-17 | a226228 |
| TASK-085 | Complete | APPROVED | 2026-02-17 | 96eb522 |
| TASK-087-092 | Complete | APPROVED | 2026-02-17 | 2c07777 |
| TASK-093 | Complete | N/A (infrastructure) | 2026-02-17 | - |
| BUG-025 | Complete | APPROVED | 2026-02-17 | 1beebcb |
| BUG-026 | Complete | APPROVED | 2026-02-17 | 1beebcb |
| TASK-094 | Complete | APPROVED | 2026-02-17 | 1beebcb |
| BUG-027-030 | Complete | APPROVED | 2026-02-18 | 338f55f |
| TASK-095 | Complete | APPROVED | 2026-02-19 | f2f35e2 |
| TASK-096 | Complete | APPROVED | 2026-02-19 | d9a8b44 |
| TASK-097-099 | Complete | APPROVED | 2026-02-19 | 562b72a |
| TASK-100 | Complete | N/A (infrastructure) | 2026-02-19 | aef5e26 |
| TASK-101 | Complete | APPROVED | 2026-02-19 | 2d12a71 |
| TASK-102 | Complete | N/A (tests) | 2026-02-19 | a6d58b4 |
| TASK-103 | Complete | APPROVED | 2026-02-19 | 9ce40aa |
| TASK-104 | Complete | APPROVED | 2026-02-19 | 190eceb |
| TASK-105 | Complete | APPROVED | 2026-02-20 | 53e5fce |
| BUG-031 | Complete | APPROVED | 2026-02-22 | 02be741 |
| TASK-106 | Complete | APPROVED | 2026-02-22 | bfdfe26 |
| TASK-107 | Complete | N/A (infrastructure) | 2026-02-22 | 7685ade |
| TASK-108 | Complete | APPROVED | 2026-02-22 | f0d2259 |
| TASK-109 | Complete | APPROVED | 2026-02-22 | 8a242c6 |
| TASK-110 | Complete | N/A (infrastructure) | 2026-02-22 | 746e03e |
| TASK-111 | Complete | APPROVED | 2026-02-22 | efb07c3 |
| TASK-112 | Complete | APPROVED | 2026-02-23 | 654872e |
| TASK-113 | Complete | APPROVED | 2026-02-23 | dce926c |
| TASK-114 | Complete | APPROVED | 2026-02-22 | cb4437c |

## Blocked Tasks

None currently blocked.

## Bug Log

| Bug ID | Severity | Type | Description | Status |
|--------|----------|------|-------------|--------|
| BUG-017 | MEDIUM | backend | GET archived-budget-posts year param allows integer overflow -> 500 + traceback leak | OPEN |
| BUG-018 | LOW | backend | Archive endpoint allows future period archiving (e.g. 2099-12) | OPEN |
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
