# Development Workflow Protocol

This defines the workflow for implementing Tiøren features using the Task tool with specialized subagents.

## Quick Reference

| Task Type | Flow |
|-----------|------|
| ad-hoc | Check TODO → Add if missing → Determine type → Follow that workflow |
| backend | Implement → Review → QA → **Security** → Commit |
| frontend | Implement → Review → QA → **Security** → Commit |
| both | Backend impl → Frontend impl → Review → QA → **Security** → Commit |
| infrastructure | Implement (main context) → Commit |
| qa | QA test (subagent) → Pass/Fail |
| security | Security test (subagent) → Pass/Report |
| bug fix | QA → Investigate → Fix → Review → QA → **Security** → Commit |

## Available Subagents

| Subagent | Purpose | When to Use |
|----------|---------|-------------|
| `backend-implementer` | FastAPI/PostgreSQL code | Tasks with Type: backend |
| `frontend-implementer` | Svelte/CSS code | Tasks with Type: frontend |
| `reviewer` | Code review | After implementation (except infrastructure) |
| `qa-browser-tester` | Browser testing via Playwright MCP | QA tasks and verification |
| `bug-investigator` | Root cause analysis | After QA finds bug, before implementing fix |
| `security-tester` | OWASP vulnerability testing | Security-only tasks (Type: security) AND after QA passes for code-changing tasks |

## Entry Points

### Resuming from TODO.md

When starting a session or continuing work:

1. **Read `WORKFLOW-STATE.md`** - understand current progress
2. **Read `TODO.md`** - find the next task to work on
3. **Determine task type** from the TODO.md entry's `Type:` field
4. Resume from incomplete task (`[~]`) or start next pending task (`[ ]`)
5. **Follow appropriate workflow** in "Workflow by Task Type" section below

### Handling User Requests (Ad-hoc)

When user reports a problem or requests work WITHOUT referencing TODO.md:

1. **Check TODO.md first** - Is it already documented?
   - If yes: Use existing task/bug ID, update status to `[~]` in progress
   - If no: Add to TODO.md first with new ID (TASK-XXX or BUG-XXX)
2. **Update WORKFLOW-STATE.md** - Set as active task
3. **Determine task type** - Then follow appropriate workflow below

Both paths lead to → **Workflow by Task Type**

## Workflow by Task Type

### New Feature (backend/frontend/both)

1. **Announce**: "Starting TASK-XXX: [title]"
2. **Implement** using Task tool:
   - `backend` → use `backend-implementer`
   - `frontend` → use `frontend-implementer`
   - `both` → backend-implementer first, then frontend-implementer
3. **Review** → use `reviewer` subagent
4. **If REJECTED**: fix with implementer subagent, re-review (max 3 attempts)
5. **QA** → use `qa-browser-tester` to verify feature works
6. **Security** → use `security-tester` after QA passes
7. **If VULNERABILITIES_FOUND**: fix with implementer → re-review → re-QA → re-security
8. **If PASS**: update docs, commit, proceed to next task

### Bug Fix

1. **QA first** → confirm and reproduce bug with `qa-browser-tester`
2. **Investigate** → find root cause with `bug-investigator` subagent
3. **Implement fix** → use appropriate implementer subagent (based on investigator's findings)
4. **Review** → use `reviewer` subagent
5. **QA again** → confirm bug is fixed with `qa-browser-tester`
6. If bug still exists → repeat from step 2 (max 3 attempts)
7. **Security** → use `security-tester` after QA passes
8. **If VULNERABILITIES_FOUND**: fix → re-review → re-QA → re-security

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

### Security-Only Task

Standalone security audits (SEC-* tasks):

1. **Verify services are running** (if dynamic testing needed):
   - Backend: `curl -s http://localhost:8000/api/health` should return `{"status":"ok"}`
   - Frontend: `curl -s http://localhost:5173` should return HTML
   - If not running, start with commands from CLAUDE.md "Development Mode" section
2. **Run security test** → use `security-tester` subagent
3. **If PASS** → mark complete, next task
4. **If VULNERABILITIES_FOUND** → log in WORKFLOW-STATE.md, create fix tasks if needed

## After Task Completion

1. Update `TODO.md` - mark task complete with `[x]`
2. **Commit code changes first**: `feat(scope): description` or `fix(scope): description`
3. **Then update docs with commit hash**:
   - Update `WORKFLOW-STATE.md` - add to Task History with the commit hash from step 2
   - Commit docs: `docs(workflow): update TASK-XXX status`
4. Cleanup: `find /workspace/playwright-mcp -type f -delete`, close browser if open
5. Proceed to next task

**Important**: Never amend a commit to add its own hash - this changes the hash. Always use two separate commits.

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
- **PREFER** running only ONE command per Bash tool call - chained commands (&&, ||, ;) often require manual permission approval
- For independent commands, use multiple parallel Bash tool calls instead of chaining

## Feature Gap Protocol

If a bug fix or task requires functionality not specified in SPEC.md:

1. **Document the gap** - Describe what functionality is missing
2. **Check SPEC.md** - Is it part of the overall vision?
3. **Ask user** - "This fix requires [X] which isn't in SPEC.md. Should I:
   - A) Implement as part of this bug fix
   - B) Create a separate TASK for it first"
4. **After approval** - Proceed with implementation
5. **Add to TODO.md** - If it becomes a separate task

Example: "BUG-004 fix requires route guards. This is not in SPEC.md. Should it be implemented as part of bug fix or as separate TASK?"

## Starting the Workflow

To begin or resume development:

```
Start the development workflow
```

Or to resume from a specific point:

```
Resume workflow from TASK-XXX
```