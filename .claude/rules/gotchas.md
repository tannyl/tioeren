# Known Pitfalls and Gotchas

Lessons learned from MVP development and QA. These are auto-loaded to prevent re-encountering known issues.

## SQLAlchemy Enum Case Mismatch (BUG-005)

When defining SQLAlchemy Enum columns with `native_enum=True`:
- MUST include `values_callable=lambda x: [e.value for e in x]`
- Without it: SQLAlchemy sends `UNCATEGORIZED`, PostgreSQL expects `uncategorized`
- Affects: AccountPurpose, AccountDatasource, TransactionStatus, BudgetPostType

## svelte-i18n Blank Screen (BUG-008)

- `$_()` throws if called before locale initialization completes
- In root layout, the `$isLoading` check fires before locale is ready
- Fix: hardcode loading text (e.g., "Indlæser...") instead of using `$_()`

## Dashboard API Field Names (BUG-009, BUG-010)

- API returns `pending_count` (not `pending_transactions_count`)
- API returns `purpose` on accounts (not `currency`)
- Always verify TypeScript interfaces match actual API response shape

## Error Messages Need Translation (BUG-006)

- API error messages arrive as i18n keys (e.g., `error.unexpectedServerError`)
- Frontend must wrap them with `$_()` or `get(_)()` before displaying
- Check all `catch` blocks and error display code

## Non-JSON API Responses (BUG-003)

- Backend can return plain text tracebacks on unhandled 500 errors
- Frontend fetch wrappers must handle non-JSON responses gracefully
- Check Content-Type before calling `response.json()`
