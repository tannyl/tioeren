---
paths:
  - "api/**"
  - "alembic/**"
  - "tests/**"
---

# Backend Conventions

## SQLAlchemy Enums

CRITICAL: When using `Enum(PythonEnum, native_enum=True)`, MUST add:

```python
values_callable=lambda x: [e.value for e in x]
```

Without this, SQLAlchemy sends uppercase names (e.g., `UNCATEGORIZED`) but PostgreSQL expects lowercase values (e.g., `uncategorized`).

## Session-Based Auth

- Session-ID in HttpOnly, Secure, SameSite=Strict cookie
- Session data stored in PostgreSQL
- 30-day sliding expiration
- On logout/password change: invalidate all user sessions

## Testing

- Use pytest for all backend tests
- Run: `python -m pytest`
- Tests live in `tests/` directory at project root
