# Development Workflow Protocol

This defines the workflow for implementing Tiøren features using the Task tool with specialized subagents.

## Quick Reference

| Task Type | Flow |
|-----------|------|
| backend | Implement (subagent) → Review (subagent) → Commit |
| frontend | Implement (subagent) → Review (subagent) → Commit |
| both | Backend impl → Frontend impl → Review → Commit |
| infrastructure | Implement (main context) → Commit |
| qa | QA test (subagent) → Pass/Fail |
| bug fix | QA → Fix → Review → QA → Commit |

## Available Subagents

| Subagent | Purpose | When to Use |
|----------|---------|-------------|
| `backend-implementer` | FastAPI/PostgreSQL code | Tasks with Type: backend |
| `frontend-implementer` | Svelte/CSS code | Tasks with Type: frontend |
| `reviewer` | Code review | After implementation (except infrastructure) |
| `qa-browser-tester` | Browser testing via Playwright MCP | QA tasks and verification |

## On Session Start

1. Read `WORKFLOW-STATE.md` - understand current progress
2. Read `TODO.md` - find the next task to work on
3. Resume from incomplete task or start next available task

## Workflow by Task Type

### New Feature (backend/frontend/both)

1. **Announce**: "Starting TASK-XXX: [title]"
2. **Implement** using Task tool:
   - `backend` → use `backend-implementer`
   - `frontend` → use `frontend-implementer`
   - `both` → backend-implementer first, then frontend-implementer
3. **Review** → use `reviewer` subagent
4. **If APPROVED**: update docs, commit, proceed to QA or next task
5. **If REJECTED**: fix with implementer subagent, re-review (max 3 attempts)
6. **QA** → use `qa-browser-tester` to verify feature works

### Bug Fix

1. **QA first** → confirm and reproduce bug with `qa-browser-tester`
2. **Implement fix** → use appropriate implementer subagent
3. **Review** → use `reviewer` subagent
4. **QA again** → confirm bug is fixed with `qa-browser-tester`
5. If bug still exists → repeat from step 2 (max 3 attempts)

### Infrastructure

Infrastructure tasks are handled directly in main context without subagents:
- Docker/docker-compose configuration
- Devcontainer setup
- Alembic migrations
- Config files (.env, pyproject.toml, package.json, etc.)

No review step required for infrastructure changes.

### QA-Only Task

1. **Verify services are running**:
   - Backend: `curl -s http://localhost:8000/api/health` should return `{"status":"ok"}`
   - Frontend: `curl -s http://localhost:5173` should return HTML
   - If not running, start with commands from CLAUDE.md "Development Mode" section
2. **Run QA** → use `qa-browser-tester` subagent
3. **If PASS** → mark complete, next task
4. **If FAIL** → log bugs in WORKFLOW-STATE.md "Bug Log" section

## After Task Completion

1. Update `TODO.md` - mark task complete with `[x]`
2. Update `WORKFLOW-STATE.md` - add to Task History
3. Create git commit: `feat(scope): description` or `fix(scope): description`
4. Cleanup: `rm -f .playwright-mcp/*.png`, close browser if open
5. Proceed to next task

## Review Failure Protocol

If a task fails review 3 times:
1. Stop immediately
2. Update `WORKFLOW-STATE.md` - mark task as blocked
3. Ask user for guidance
4. Do NOT proceed to dependent tasks

## Main Context Restrictions

**Main context MAY:**
- Read and analyze code (Read, Grep, Glob)
- Test endpoints with curl (investigation)
- Update TODO.md and WORKFLOW-STATE.md
- Create git commits
- Handle infrastructure tasks
- Coordinate and delegate to subagents

**Main context MUST NOT:**
- Edit code in `api/` or `ui/` (delegate to subagents)
- Skip the review step (except for infrastructure)

## Rules

- **NEVER** proceed if a dependency task is not completed
- **ALWAYS** update `WORKFLOW-STATE.md` after each action
- **ALWAYS** create a git commit after each approved task
- **NEVER** use heredoc syntax for Python inline scripts - use `python3 -c '...'` instead
- **NEVER** use Bash with cat/heredoc/echo to create files - use the Write tool instead

## Starting the Workflow

To begin or resume development:

```
Start the development workflow
```

Or to resume from a specific point:

```
Resume workflow from TASK-XXX
```