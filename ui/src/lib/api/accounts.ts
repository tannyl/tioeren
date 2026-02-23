/**
 * Account API client
 */

import { extractErrorMessage } from './errors';

export interface Account {
	id: string;
	budget_id: string;
	name: string;
	purpose: 'normal' | 'savings' | 'loan' | 'kassekredit';
	datasource: 'bank' | 'cash' | 'virtual';
	starting_balance: number;
	current_balance: number;
	currency: string;
	credit_limit: number | null;
	locked: boolean;
	created_at: string;
	updated_at: string;
}

export interface AccountCreateRequest {
	name: string;
	purpose: 'normal' | 'savings' | 'loan' | 'kassekredit';
	datasource: 'bank' | 'cash' | 'virtual';
	starting_balance: number;
	currency?: string;
	credit_limit?: number | null;
	locked?: boolean;
}

export interface AccountUpdateRequest {
	name?: string;
	purpose?: 'normal' | 'savings' | 'loan' | 'kassekredit';
	datasource?: 'bank' | 'cash' | 'virtual';
	starting_balance?: number;
	currency?: string;
	credit_limit?: number | null;
	locked?: boolean;
}

/**
 * List all accounts for a budget
 */
export async function listAccounts(budgetId: string): Promise<Account[]> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts`, {
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
 * Get a single account by ID
 */
export async function getAccount(budgetId: string, accountId: string): Promise<Account> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts/${accountId}`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Create a new account
 */
export async function createAccount(
	budgetId: string,
	data: AccountCreateRequest
): Promise<Account> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts`, {
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
 * Update an existing account
 */
export async function updateAccount(
	budgetId: string,
	accountId: string,
	data: AccountUpdateRequest
): Promise<Account> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts/${accountId}`, {
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
 * Delete an account
 */
export async function deleteAccount(budgetId: string, accountId: string): Promise<void> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts/${accountId}`, {
		method: 'DELETE',
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}
}
