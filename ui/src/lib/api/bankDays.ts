/**
 * Bank Days API client
 */

import { extractErrorMessage } from './errors';

/**
 * Fetch non-bank-days (weekends + holidays) for a date range
 */
export async function fetchNonBankDays(fromDate: string, toDate: string): Promise<string[]> {
	const response = await fetch(
		`/api/bank-days/non-bank-days?from_date=${fromDate}&to_date=${toDate}`,
		{
			credentials: 'include'
		}
	);

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	const result = await response.json();
	return result.dates;
}
