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

## Internationalization

- NEVER hardcode user-facing text - use `{$_('section.key')}`
- Add keys to `ui/src/lib/i18n/locales/da.json`
- Cannot call `$_()` before locale init - hardcode loading text

## Amount Display

- Database stores ore (integer). Frontend: display = amount / 100, submit = amount * 100
