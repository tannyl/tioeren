/**
 * Budget Post API client
 */

import { extractErrorMessage } from './errors';

export type BudgetPostType = 'fixed' | 'ceiling' | 'rolling';

export interface RecurrencePattern {
	type: 'monthly' | 'quarterly' | 'yearly' | 'once';
	day?: number; // Day of month (1-31)
	months?: number[]; // Months for quarterly/yearly (1-12)
	date?: string; // ISO date string for 'once' type
}

export interface BudgetPost {
	id: string;
	budget_id: string;
	category_id: string;
	name: string;
	type: BudgetPostType;
	amount_min: number; // In øre
	amount_max: number | null; // In øre
	from_account_ids: string[] | null;
	to_account_ids: string[] | null;
	recurrence_pattern: RecurrencePattern | null;
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
	amount_min: number; // In øre
	amount_max?: number | null; // In øre
	from_account_ids?: string[] | null;
	to_account_ids?: string[] | null;
	recurrence_pattern?: RecurrencePattern | null;
}

export interface BudgetPostUpdateRequest {
	category_id?: string;
	name?: string;
	type?: BudgetPostType;
	amount_min?: number; // In øre
	amount_max?: number | null; // In øre
	from_account_ids?: string[] | null;
	to_account_ids?: string[] | null;
	recurrence_pattern?: RecurrencePattern | null;
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
