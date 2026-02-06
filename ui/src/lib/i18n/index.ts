import { init, register, locale } from 'svelte-i18n';

const defaultLocale = 'da';

register('da', () => import('./locales/da.json'));
register('en', () => import('./locales/en.json'));

init({
	fallbackLocale: defaultLocale,
	initialLocale: defaultLocale
});

// Re-export for convenient imports
export { locale, t, _, isLoading } from 'svelte-i18n';
