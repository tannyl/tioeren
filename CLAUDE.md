# Tiøren

> "Så faldt tiøren" - dansk ordsprog

Personal finance app focused on past, present, AND future financial overview.

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

```bash
# Database
docker compose up -d db

# Migrations
DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" alembic upgrade head

# Backend (port 8000)
DATABASE_URL="postgresql://tioren:tioren@localhost:5432/tioren" SECRET_KEY="test-secret-key" DEBUG=true uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (port 5173, proxies /api to backend)
cd /workspace/ui && npm run dev -- --host 0.0.0.0

# Tests
python -m pytest

# Health check
curl http://localhost:8000/api/health
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
