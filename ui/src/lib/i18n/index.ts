import { browser } from '$app/environment';
import { init, register, locale, getLocaleFromNavigator } from 'svelte-i18n';

const defaultLocale = 'da';

register('da', () => import('./locales/da.json'));
register('en', () => import('./locales/en.json'));

init({
	fallbackLocale: defaultLocale,
	initialLocale: browser ? getLocaleFromNavigator() ?? defaultLocale : defaultLocale
});

// Re-export for convenient imports
export { locale, t, _, isLoading } from 'svelte-i18n';
