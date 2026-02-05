---
paths:
  - "ui/**"
---

# Frontend Conventions

## Svelte 5 Runes

This project uses Svelte 5 with runes:
- State: `$state`, `$derived`, `$props`, `$bindable`, `$effect`
- Event handlers: `onclick=`, `onsubmit=` (NOT `on:click`, `on:submit`)
- Components use `{#snippet}` blocks, not slots

## Internationalization (i18n)

- **NEVER** hardcode user-facing text in components
- **ALWAYS** use translation keys: `{$_('section.key')}`
- Add new keys to `ui/src/lib/i18n/locales/da.json`
- Group keys by feature/page (common, dashboard, auth, transactions, etc.)
- Backend API returns English; all translation happens in frontend

```svelte
<!-- WRONG -->
<button>Gem</button>

<!-- CORRECT -->
<button>{$_('common.save')}</button>
```

## svelte-i18n Race Condition

CRITICAL: Cannot call `$_()` before locale is initialized. In root layout loading state,
hardcode text (e.g., "Indlæser...") instead of using the translation function.
Otherwise you get a blank white screen.

## Amount Display

- All amounts stored in ore (integer) in the database
- Frontend converts: display = amount / 100 (DKK), submit = amount * 100 (ore)

## Directory Structure

```
ui/src/
├── lib/
│   ├── components/   # Reusable components
│   ├── stores/       # Svelte stores
│   ├── api/          # API client functions
│   └── i18n/         # Translation files and setup
│       └── locales/
│           └── da.json  # Danish translations
└── routes/           # SvelteKit page components
```
