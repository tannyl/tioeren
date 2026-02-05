/**
 * Forecast API client
 */

import { extractErrorMessage } from './errors';

export interface ForecastProjection {
	month: string;
	start_balance: number;
	expected_income: number;
	expected_expenses: number;
	end_balance: number;
}

export interface LowestPoint {
	month: string;
	balance: number;
}

export interface NextLargeExpense {
	name: string;
	amount: number;
	date: string; // ISO format YYYY-MM-DD
}

export interface ForecastData {
	projections: ForecastProjection[];
	lowest_point: LowestPoint; // Always returned by backend
	next_large_expense: NextLargeExpense | null; // Optional - only if large expense in next 3 months
}

/**
 * Get forecast data for a budget
 */
export async function getForecast(budgetId: string, months: number = 12): Promise<ForecastData> {
	const response = await fetch(`/api/budgets/${budgetId}/forecast?months=${months}`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}
