# Workflow State

This file tracks the current state of the development workflow across sessions.

## Current

- **Active task:** QA-006
- **Phase:** 9 - QA Browser Testing (In Progress)
- **Last completed:** QA-005
- **Review attempts for current task:** 0

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| 1. Infrastructure | Complete | 5/5 |
| 2. Authentication | Complete | 8/8 |
| 3. Core Domain Models | Complete | 6/6 |
| 4. Budget and Account APIs | Complete | 5/5 |
| 5. Transactions | Complete | 4/4 |
| 6. Dashboard | Complete | 2/2 |
| 7. Forecast | Complete | 3/3 |
| 8. Integration | Complete | 3/3 |
| 9. QA Browser Testing | In Progress | 5/8 |

**Total:** 36/36 dev tasks completed, 5/8 QA tasks completed

## Task History

| Task | Status | Review Result | Completed | Commit |
|------|--------|---------------|-----------|--------|
| TASK-001 | Done | APPROVED | Yes | e0f72d9 |
| TASK-002 | Done | APPROVED | Yes | 704c58e |
| TASK-002b | Done | APPROVED | Yes | 976b9fa |
| TASK-003 | Done | APPROVED | Yes | 28e1b98 |
| TASK-004 | Done | APPROVED | Yes | fb34896 |
| TASK-005 | Done | APPROVED | Yes | 9d63319 |
| TASK-006 | Done | APPROVED | Yes | fbf501c |
| TASK-007 | Done | APPROVED | Yes | 851d033 |
| TASK-008 | Done | APPROVED | Yes | d0ee901 |
| TASK-009 | Done | APPROVED | Yes | eed02e4 |
| TASK-010 | Done | APPROVED | Yes | ceb7f06 |
| TASK-011 | Done | APPROVED | Yes | 48303f0 |
| TASK-012 | Done | APPROVED | Yes | 3ad4818 |
| TASK-013 | Done | APPROVED | Yes | ba15e0f |
| TASK-014 | Done | APPROVED | Yes | 4635f56 |
| TASK-015 | Done | APPROVED | Yes | 6f9a8e2 |
| TASK-016 | Done | APPROVED | Yes | 40f0914 |
| TASK-017 | Done | APPROVED | Yes | da3699d |
| TASK-018 | Done | APPROVED | Yes | 1e469b1, 5675847 |
| TASK-019 | Done | APPROVED | Yes | 8ffaee2 |
| TASK-020 | Done | APPROVED | Yes | d74f06b |
| TASK-021 | Done | APPROVED | Yes | f26d71b, a23534b |
| TASK-022 | Done | APPROVED | Yes | ccddfd2 |
| TASK-023 | Done | APPROVED | Yes | a3ffe7a |
| TASK-024 | Done | APPROVED | Yes | 18edaec |
| TASK-025 | Done | APPROVED | Yes | b97c066 |
| TASK-026 | Done | APPROVED | Yes | 46a39f4 |
| TASK-027 | Done | APPROVED | Yes | b4a40b8 |
| TASK-028 | Done | APPROVED | Yes | 6ad4e1f |
| TASK-029 | Done | APPROVED | Yes | 5fb1727 |
| TASK-030 | Done | APPROVED | Yes | 99d9cff |
| TASK-031 | Done | APPROVED | Yes | 8b9cada |
| TASK-032 | Done | APPROVED | Yes | d3ea18c |
| TASK-033 | Done | APPROVED | Yes | c7cd9ab |
| TASK-034 | Done | APPROVED | Yes | ef2d03f |
| TASK-035 | Done | APPROVED | Yes | dc426db |

## Blocked Tasks

None currently blocked.

## Session Log

| Session | Started | Ended | Tasks Completed |
|---------|---------|-------|-----------------|
| - | - | - | - |

---

## Phase 9: QA Browser Testing Protocol

### Infrastructure Setup (before any QA task)

1. Start database: `docker compose up -d db`
2. Start backend: `DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" SECRET_KEY="test-secret-key" DEBUG=true TESTING=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
3. Run migrations: `DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" alembic upgrade head`
4. Start frontend: `cd /workspace/ui && npm run dev -- --host 0.0.0.0` (port 5173, proxies /api to backend)
5. Verify: `curl http://localhost:8000/api/health` returns `{"status": "ok"}`

### Agent Mapping for QA Tasks

| Task Type | Agent (subagent_type) | Description |
|-----------|----------------------|-------------|
| `qa` (browser test) | `general-purpose` | Tests app in browser via Playwright MCP. Give it the task from TODO.md and tell it to follow the instructions in `.claude/agents/qa-browser-tester.md` |
| `frontend` (fix) | `frontend-implementer` | Fixes frontend bugs found during QA |
| `backend` (fix) | `backend-implementer` | Fixes backend bugs found during QA |
| `review` | `reviewer` | Reviews code fixes before commit |

### QA Task Workflow Cycle

```
1. Launch general-purpose agent → browser test via Playwright MCP
   - Agent navigates the app, interacts with UI, checks console
   - Returns: PASS (no bugs) or FAIL (list of bugs with details)

2. If PASS → mark task [x] in TODO.md, update QA-TRACKER.md, next task

3. If FAIL → log bugs in QA-TRACKER.md, then for each bug:
   a. Launch frontend-implementer and/or backend-implementer to fix
   b. Launch reviewer to review fixes
   c. If APPROVED → commit fixes: fix(qa): QA-XXX description
   d. If REJECTED → re-fix (max 3 attempts, then ask user)
   e. Re-launch general-purpose agent to retest
```

### Bug Tracking

Detailed bug tracking is in `QA-TRACKER.md` in the workspace root.

---

## How to Use

1. **On session start:** Read this file and `QA-TRACKER.md` to understand current state
2. **During work:** Update "Active task" and "Review attempts"
3. **On task completion:** Add to Task History, update Progress Summary, update QA-TRACKER.md
4. **On session end:** Add entry to Session Log

## Review Failure Protocol

If a task fails review 3 times:
1. Update "Review attempts" to 3
2. Add task to "Blocked Tasks" with reason
3. Stop and ask user for guidance
4. Do NOT proceed to dependent tasks
