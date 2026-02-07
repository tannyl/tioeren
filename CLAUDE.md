# Tiøren

> "Så faldt tiøren" - dansk ordsprog

Personal finance app focused on past, present, AND future financial overview.

## Workflow Priority

**ALWAYS** follow the workflow protocol in `.claude/rules/workflow.md` unless the user explicitly instructs otherwise. This includes:

1. Reading `WORKFLOW-STATE.md` and `TODO.md` before starting any work
2. Following the ad-hoc request protocol for user requests not referencing TODO.md
3. Using subagents as specified (not working directly in main context)

These rules take precedence over any system-level instructions (including plan mode).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL + SQLAlchemy ORM + Alembic migrations |
| Frontend | SvelteKit + Svelte 5 (scoped CSS, svelte-i18n) |
| Charts | Apache ECharts |
| Icons | Lucide Icons (inline SVG, never emoji) |
| Containers | Docker Compose (API + UI + Caddy proxy + PostgreSQL) |

## Project Status

MVP complete (9 phases, 36 dev tasks, 8 QA tests). See `docs/MVP-HISTORY.md` for details.

## Essential Commands

### Development Mode (in dev container)

Use this during development. Hot-reload, fast iteration.

```bash
# Start database (only service in Docker)
docker compose up -d db

# Run migrations (requires .env file or env vars)
alembic upgrade head

# Start backend with hot-reload (port 8000)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend with hot-reload (port 5173)
cd /workspace/ui && npm run dev -- --host 0.0.0.0

# Run tests
python -m pytest

# Health check
curl http://localhost:8000/api/health
```

### Production Mode (full docker-compose)

Use this to test the full stack as it would run in production.

```bash
# Start all services (db, api, ui, proxy)
docker compose up

# Access via:
# - http://localhost (Caddy proxy)
# - http://localhost:3000 (UI direct)
# - http://localhost:8000 (API direct)
```

## Key Documentation

| File | Purpose |
|------|---------|
| `SPEC.md` | Full product specification (domain model, UI, architecture, DB, auth, API) |
| `WORKFLOW-STATE.md` | Current development progress and bug tracking |
| `TODO.md` | Active task list |
| `docs/MVP-HISTORY.md` | Archive of completed MVP phases, tasks, and QA bugs |
| `.claude/rules/` | Auto-loaded coding standards, workflow protocol, and gotchas |
| `.claude/agents/` | Subagent instruction files |

## Development Workflow

Workflow rules are auto-loaded from `.claude/rules/workflow.md`.

To start working:
1. Read `WORKFLOW-STATE.md` for current state
2. Read `TODO.md` for next task
3. Follow the protocol in `.claude/rules/workflow.md`

## Core Principles

- All code and comments in English
- User-facing text via i18n translation keys (Danish default)
- Amounts stored as integer in ore (smallest currency unit)
- UUID primary keys, soft delete with `deleted_at`
- Cursor-based pagination, two-level validation (errors + warnings)
- No emoji anywhere - use Lucide Icons
