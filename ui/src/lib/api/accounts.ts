/**
 * Account API client
 */

export interface Account {
	id: string;
	budget_id: string;
	name: string;
	purpose: 'normal' | 'savings' | 'loan';
	datasource: 'bank' | 'credit' | 'cash' | 'virtual';
	starting_balance: number;
	current_balance?: number;
	currency: string;
	can_go_negative: boolean;
	needs_coverage: boolean;
	created_at: string;
	updated_at: string;
}

export interface AccountCreateRequest {
	name: string;
	purpose: 'normal' | 'savings' | 'loan';
	datasource: 'bank' | 'credit' | 'cash' | 'virtual';
	starting_balance: number;
	currency?: string;
	can_go_negative?: boolean;
	needs_coverage?: boolean;
}

export interface AccountUpdateRequest {
	name?: string;
	purpose?: 'normal' | 'savings' | 'loan';
	datasource?: 'bank' | 'credit' | 'cash' | 'virtual';
	starting_balance?: number;
	currency?: string;
	can_go_negative?: boolean;
	needs_coverage?: boolean;
}

export interface ApiError {
	detail: string;
}

/**
 * List all accounts for a budget
 */
export async function listAccounts(budgetId: string): Promise<Account[]> {
	const response = await fetch(`/api/budgets/${budgetId}/accounts`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to list accounts');
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
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to get account');
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
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to create account');
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
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to update account');
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
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to delete account');
	}
}
