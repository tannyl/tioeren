# Development Workflow Protocol

This defines the workflow for implementing Tiøren features using the Task tool with specialized subagents.

## Available Subagents

| Subagent | Purpose | When to Use |
|----------|---------|-------------|
| `backend-implementer` | FastAPI/PostgreSQL code | Tasks with Type: backend |
| `frontend-implementer` | Svelte/CSS code | Tasks with Type: frontend |
| `reviewer` | Code review | After every implementation task |
| `qa-browser-tester` | Browser testing via Playwright MCP | QA tasks |

## On Session Start

1. Read `WORKFLOW-STATE.md` - understand current progress
2. Read `TODO.md` - find the next task to work on
3. Resume from incomplete task or start next available task

## For Each Task

1. **Announce:** "Starting TASK-XXX: [title]"
2. **Delegate implementation** using the Task tool:
   - `backend` tasks -> use `backend-implementer` subagent
   - `frontend` tasks -> use `frontend-implementer` subagent
   - `infrastructure` tasks -> handle directly in main context
   - `both` tasks -> run backend-implementer first, then frontend-implementer
   - `qa` tasks -> use `qa-browser-tester` subagent (or general-purpose with qa-browser-tester instructions)
3. **Wait for completion** and review the output
4. **Run review** using the Task tool with `reviewer` subagent
5. **Announce review result**

## On APPROVED Review

1. Update `TODO.md` - mark task complete
2. Update `WORKFLOW-STATE.md` - add to history, update progress
3. Create git commit with message: `feat(scope): TASK-XXX description`
4. Proceed to next task

## On REJECTED or MINOR_FIXES_NEEDED Review

1. Show the issues to the user
2. Use the appropriate implementer subagent to fix issues
3. Run review again
4. **Maximum 3 attempts** - after 3 failed reviews:
   - Stop immediately
   - Update `WORKFLOW-STATE.md` - mark task as blocked
   - Ask user for guidance
   - Do NOT proceed to dependent tasks

## On Phase Completion

1. Summarize what was built in this phase
2. Ask: "Phase X complete. Continue to Phase Y?"
3. Wait for user confirmation before proceeding

## QA Task Workflow

For QA browser testing tasks:
1. Ensure services are running (db, backend, frontend)
2. Launch qa-browser-tester subagent (or general-purpose with qa-browser-tester instructions)
3. If PASS -> mark complete, next task
4. If FAIL -> log bugs in WORKFLOW-STATE.md "Bug Log" section, fix with appropriate implementer, review, retest

## Rules

- **NEVER** skip the review step
- **NEVER** proceed if a dependency task is not completed and approved
- **ALWAYS** update `WORKFLOW-STATE.md` after each action
- **ALWAYS** create a git commit after each approved task
- **ALWAYS** stop and ask user after 3 failed review attempts
- **NEVER** use heredoc syntax for Python inline scripts - use `python3 -c '...'` instead
- **NEVER** use Bash with cat/heredoc/echo to create files - use the Write tool instead

## Cleanup After Workflow

After completing a task or QA test, clean up temporary files:
- Delete screenshots: `rm -f .playwright-mcp/*.png`
- Close browser: Use `browser_close` tool
- Stop any background processes started during the task

## Starting the Workflow

To begin or resume development:

```
Start the development workflow
```

Or to resume from a specific point:

```
Resume workflow from TASK-XXX
```
