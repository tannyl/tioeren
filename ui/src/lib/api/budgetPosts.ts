/**
 * Budget Post API client
 */

import { extractErrorMessage } from './errors';

export type BudgetPostType = 'fixed' | 'ceiling';
export type BudgetPostDirection = 'income' | 'expense' | 'transfer';
export type CounterpartyType = 'external' | 'account';

export type RecurrenceType =
  | 'once'
  | 'daily'
  | 'weekly'
  | 'monthly_fixed'
  | 'monthly_relative'
  | 'monthly_bank_day'
  | 'yearly'
  | 'yearly_bank_day'
  | 'period_once'
  | 'period_monthly'
  | 'period_yearly';

export type RelativePosition = 'first' | 'second' | 'third' | 'fourth' | 'last';

export interface RecurrencePattern {
	type: RecurrenceType;
	interval?: number; // Default 1, every N days/weeks/months/years
	weekday?: number; // 0=Monday, 6=Sunday
	day_of_month?: number; // 1-31
	relative_position?: RelativePosition;
	month?: number; // 1-12 for yearly
	months?: number[]; // Array of months 1-12 for period types
	bank_day_adjustment?: 'none' | 'next' | 'previous';
	bank_day_keep_in_month?: boolean; // Default true - when true, adjustment stays in same month
	bank_day_number?: number; // 1-10 for bank day types
	bank_day_from_end?: boolean; // true = from end, false = from start
}

export interface AmountPattern {
	id?: string;
	budget_post_id?: string;
	amount: number; // In øre
	start_date: string; // ISO date (YYYY-MM-DD)
	end_date: string | null; // ISO date or null for indefinite
	recurrence_pattern: RecurrencePattern | null;
	account_ids: string[] | null; // NORMAL account UUIDs for this pattern
	created_at?: string;
	updated_at?: string;
}

export interface BudgetPost {
	id: string;
	budget_id: string;
	direction: BudgetPostDirection;
	category_id: string | null;
	category_name: string | null;
	type: BudgetPostType;
	accumulate: boolean;
	counterparty_type: CounterpartyType | null;
	counterparty_account_id: string | null;
	transfer_from_account_id: string | null;
	transfer_to_account_id: string | null;
	amount_patterns: AmountPattern[];
	created_at: string;
	updated_at: string;
}

export interface BudgetPostListResponse {
	data: BudgetPost[];
	next_cursor: string | null;
}

export interface BudgetPostCreateRequest {
	direction: BudgetPostDirection;
	category_id: string | null;
	type: BudgetPostType;
	accumulate?: boolean;
	counterparty_type: CounterpartyType | null;
	counterparty_account_id: string | null;
	transfer_from_account_id: string | null;
	transfer_to_account_id: string | null;
	amount_patterns: Omit<AmountPattern, 'id' | 'budget_post_id' | 'created_at' | 'updated_at'>[];
}

export interface BudgetPostUpdateRequest {
	type?: BudgetPostType;
	accumulate?: boolean;
	counterparty_type?: CounterpartyType | null;
	counterparty_account_id?: string | null;
	transfer_from_account_id?: string | null;
	transfer_to_account_id?: string | null;
	amount_patterns?: Omit<AmountPattern, 'id' | 'budget_post_id' | 'created_at' | 'updated_at'>[];
}

/**
 * List all budget posts for a budget
 */
export async function listBudgetPosts(budgetId: string): Promise<BudgetPost[]> {
	const response = await fetch(`/api/budgets/${budgetId}/budget-posts`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	const result: BudgetPostListResponse = await response.json();
	return result.data;
}

/**
 * Get a single budget post
 */
export async function getBudgetPost(budgetId: string, postId: string): Promise<BudgetPost> {
	const response = await fetch(`/api/budgets/${budgetId}/budget-posts/${postId}`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Create a new budget post
 */
export async function createBudgetPost(
	budgetId: string,
	data: BudgetPostCreateRequest
): Promise<BudgetPost> {
	const response = await fetch(`/api/budgets/${budgetId}/budget-posts`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data),
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Update an existing budget post
 */
export async function updateBudgetPost(
	budgetId: string,
	postId: string,
	data: BudgetPostUpdateRequest
): Promise<BudgetPost> {
	const response = await fetch(`/api/budgets/${budgetId}/budget-posts/${postId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data),
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Delete a budget post
 */
export async function deleteBudgetPost(budgetId: string, postId: string): Promise<void> {
	const response = await fetch(`/api/budgets/${budgetId}/budget-posts/${postId}`, {
		method: 'DELETE',
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}
}

export interface PreviewOccurrence {
	pattern_id: string;
	date: string;
	amount: number;
}

/**
 * Preview occurrences for amount patterns within a date range
 */
export async function previewOccurrences(
	budgetId: string,
	patterns: Record<string, Omit<AmountPattern, 'id' | 'budget_post_id' | 'created_at' | 'updated_at'>>,
	start_date: string,
	end_date: string
): Promise<PreviewOccurrence[]> {
	const response = await fetch(
		`/api/budgets/${budgetId}/budget-posts/preview-occurrences`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				amount_patterns: patterns,
				from_date: start_date,
				to_date: end_date
			}),
			credentials: 'include'
		}
	);

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	const result = await response.json();
	return result.occurrences;
}
