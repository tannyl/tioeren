/**
 * Budget Post API client
 */

import { extractErrorMessage } from './errors';

export type BudgetPostType = 'fixed' | 'ceiling' | 'rolling';

export type RecurrenceType =
  | 'once'
  | 'daily'
  | 'weekly'
  | 'monthly_fixed'
  | 'monthly_relative'
  | 'yearly'
  | 'period_once'
  | 'period_yearly';

export type RelativePosition = 'first' | 'last';

export interface RecurrencePattern {
	type: RecurrenceType;
	interval?: number; // Default 1, every N days/weeks/months/years
	weekday?: number; // 0=Monday, 6=Sunday
	day_of_month?: number; // 1-31
	relative_position?: RelativePosition;
	month?: number; // 1-12 for yearly
	months?: number[]; // Array of months 1-12 for period types
	date?: string; // ISO date for 'once'
	postpone_weekend?: boolean;
}

export interface AmountPattern {
	id?: string;
	budget_post_id?: string;
	amount: number; // In øre
	start_date: string; // ISO date (YYYY-MM-DD)
	end_date: string | null; // ISO date or null for indefinite
	recurrence_pattern: RecurrencePattern | null;
	created_at?: string;
	updated_at?: string;
}

export interface BudgetPost {
	id: string;
	budget_id: string;
	category_id: string;
	name: string;
	type: BudgetPostType;
	from_account_ids: string[] | null;
	to_account_ids: string[] | null;
	amount_patterns: AmountPattern[];
	created_at: string;
	updated_at: string;
}

export interface BudgetPostListResponse {
	data: BudgetPost[];
	next_cursor: string | null;
}

export interface BudgetPostCreateRequest {
	category_id: string;
	name: string;
	type: BudgetPostType;
	from_account_ids?: string[] | null;
	to_account_ids?: string[] | null;
	amount_patterns: Omit<AmountPattern, 'id' | 'budget_post_id' | 'created_at' | 'updated_at'>[];
}

export interface BudgetPostUpdateRequest {
	category_id?: string;
	name?: string;
	type?: BudgetPostType;
	from_account_ids?: string[] | null;
	to_account_ids?: string[] | null;
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
