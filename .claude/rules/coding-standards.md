# Coding Standards

## Language

- All code, comments, variable names, function names in **English**
- Commit messages in English: `feat(scope): description`
- User-facing text via i18n translation keys only (never hardcoded Danish in components)
- Backend API responses use English; all translation happens in frontend

## Database Conventions

- UUID primary keys (UUIDv7 preferred, UUIDv4 fallback)
- Amounts stored as **integer in ore** (smallest currency unit): 1234.56 kr = 123456
- Column name: `amount`, type: BIGINT
- Soft delete with `deleted_at` timestamp on main entities
- Audit fields: `created_at`, `updated_at`, `created_by`, `updated_by`
- Split allocations use remainder model: fixed amounts + one `is_remainder = true`

## API Conventions

- RESTful JSON API at `/api/*` prefix
- Cursor-based pagination (base64-encoded cursor, `next_cursor` in response)
- Two-level validation: `errors[]` (blocking) and `warnings[]` (advisory)
- HTTP 429 with `Retry-After` header for rate limiting

## Frontend Conventions

- No emoji anywhere - use Lucide Icons (inline SVG)
- CSS custom properties for theming (`--bg-page`, `--text-primary`, `--positive`, `--negative`, etc.)
- Scoped CSS within Svelte components (default behavior)
- Desktop-first responsive design, breakpoint at 768px
- Desktop: sidebar navigation, Mobile: bottom navigation bar

## Project Specification

For domain model, UI wireframes, architecture, and detailed specifications, read `SPEC.md`.
