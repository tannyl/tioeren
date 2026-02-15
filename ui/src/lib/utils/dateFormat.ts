/**
 * Locale-aware date formatting utilities for Tiøren
 *
 * All functions accept the locale from svelte-i18n's $locale store (string | null | undefined)
 * and map it to Intl.DateTimeFormat locale codes.
 */

const LOCALE_MAP: Record<string, string> = {
	da: 'da-DK',
	en: 'en-GB'
};

/**
 * Resolve locale code to Intl.DateTimeFormat locale, defaulting to 'da-DK'
 */
function resolveLocale(locale: string | null | undefined): string {
	if (!locale) return 'da-DK';
	return LOCALE_MAP[locale] || 'da-DK';
}

/**
 * Parse ISO date string (YYYY-MM-DD or YYYY-MM) to Date object.
 * CRITICAL: Appends T00:00:00 to YYYY-MM-DD strings to avoid timezone shift.
 */
function parseDate(isoString: string): Date {
	// Handle YYYY-MM format (month-only)
	if (/^\d{4}-\d{2}$/.test(isoString)) {
		const [year, month] = isoString.split('-');
		return new Date(parseInt(year), parseInt(month) - 1, 1);
	}

	// Handle YYYY-MM-DD format
	if (/^\d{4}-\d{2}-\d{2}$/.test(isoString)) {
		return new Date(isoString + 'T00:00:00');
	}

	// Fallback for other formats
	return new Date(isoString);
}

/**
 * Format date as "15. februar 2025" (da-DK)
 */
export function formatDate(isoString: string, locale: string | null | undefined): string {
	const date = parseDate(isoString);
	return date.toLocaleDateString(resolveLocale(locale), {
		day: 'numeric',
		month: 'long',
		year: 'numeric'
	});
}

/**
 * Format date as "15. feb 2025" (da-DK)
 */
export function formatDateShort(isoString: string, locale: string | null | undefined): string {
	const date = parseDate(isoString);
	return date.toLocaleDateString(resolveLocale(locale), {
		day: 'numeric',
		month: 'short',
		year: 'numeric'
	});
}

/**
 * Format date as "15/02/2025" (da-DK)
 */
export function formatDateCompact(isoString: string, locale: string | null | undefined): string {
	const date = parseDate(isoString);
	return date.toLocaleDateString(resolveLocale(locale), {
		day: '2-digit',
		month: '2-digit',
		year: 'numeric'
	});
}

/**
 * Format month number (1-12) as "februar" or "feb" (da-DK)
 * Creates synthetic date to leverage Intl.DateTimeFormat
 */
export function formatMonth(
	monthNum: number,
	locale: string | null | undefined,
	format: 'long' | 'short' | 'narrow' = 'long'
): string {
	const date = new Date(2000, monthNum - 1, 1);
	return date.toLocaleDateString(resolveLocale(locale), { month: format });
}

/**
 * Format YYYY-MM string as "februar 2025" (da-DK)
 */
export function formatMonthYear(isoString: string, locale: string | null | undefined): string {
	const date = parseDate(isoString);
	return date.toLocaleDateString(resolveLocale(locale), {
		month: 'long',
		year: 'numeric'
	});
}

/**
 * Format YYYY-MM string as "feb 25" (da-DK)
 */
export function formatMonthYearShort(isoString: string, locale: string | null | undefined): string {
	const date = parseDate(isoString);
	return date.toLocaleDateString(resolveLocale(locale), {
		month: 'short',
		year: '2-digit'
	});
}
