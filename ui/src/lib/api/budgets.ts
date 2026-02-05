/**
 * Budget API client
 */

import { extractErrorMessage } from './errors';

export interface Budget {
	id: string;
	name: string;
	warning_threshold: number;
	created_at: string;
	updated_at: string;
	total_balance?: number;
}

export interface BudgetCreateRequest {
	name: string;
	warning_threshold?: number;
}

export interface BudgetUpdateRequest {
	name?: string;
	warning_threshold?: number | null;
}

/**
 * List all budgets for the current user
 */
export async function listBudgets(): Promise<Budget[]> {
	const response = await fetch('/api/budgets', {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	const result = await response.json();
	return result.data;
}

/**
 * Get a single budget by ID
 */
export async function getBudget(id: string): Promise<Budget> {
	const response = await fetch(`/api/budgets/${id}`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Create a new budget
 */
export async function createBudget(data: BudgetCreateRequest): Promise<Budget> {
	const response = await fetch('/api/budgets', {
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
 * Update an existing budget
 */
export async function updateBudget(id: string, data: BudgetUpdateRequest): Promise<Budget> {
	const response = await fetch(`/api/budgets/${id}`, {
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
 * Delete a budget
 */
export async function deleteBudget(id: string): Promise<void> {
	const response = await fetch(`/api/budgets/${id}`, {
		method: 'DELETE',
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}
}
