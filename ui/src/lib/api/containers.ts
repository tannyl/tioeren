/**
 * Container API client
 */

import { extractErrorMessage } from './errors';

export type ContainerType = 'cashbox' | 'piggybank' | 'debt';

export interface Container {
	id: string;
	budget_id: string;
	name: string;
	type: ContainerType;
	starting_balance: number;
	bank_name: string | null;
	bank_account_name: string | null;
	bank_reg_number: string | null;
	bank_account_number: string | null;
	overdraft_limit: number | null;
	locked: boolean | null;
	credit_limit: number | null;
	allow_withdrawals: boolean | null;
	interest_rate: number | null;
	interest_frequency: string | null;
	required_payment: number | null;
	current_balance: number;
	created_at: string;
	updated_at: string;
}

export interface ContainerCreateRequest {
	name: string;
	type: ContainerType;
	starting_balance: number;
	bank_name?: string | null;
	bank_account_name?: string | null;
	bank_reg_number?: string | null;
	bank_account_number?: string | null;
	overdraft_limit?: number | null;
	locked?: boolean | null;
	credit_limit?: number | null;
	allow_withdrawals?: boolean | null;
	interest_rate?: number | null;
	interest_frequency?: string | null;
	required_payment?: number | null;
}

export interface ContainerUpdateRequest {
	name?: string;
	type?: ContainerType;
	starting_balance?: number;
	bank_name?: string | null;
	bank_account_name?: string | null;
	bank_reg_number?: string | null;
	bank_account_number?: string | null;
	overdraft_limit?: number | null;
	locked?: boolean | null;
	credit_limit?: number | null;
	allow_withdrawals?: boolean | null;
	interest_rate?: number | null;
	interest_frequency?: string | null;
	required_payment?: number | null;
}

/**
 * List all containers for a budget
 */
export async function listContainers(budgetId: string): Promise<Container[]> {
	const response = await fetch(`/api/budgets/${budgetId}/containers`, {
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
 * Get a single container by ID
 */
export async function getContainer(budgetId: string, containerId: string): Promise<Container> {
	const response = await fetch(`/api/budgets/${budgetId}/containers/${containerId}`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Create a new container
 */
export async function createContainer(
	budgetId: string,
	data: ContainerCreateRequest
): Promise<Container> {
	const response = await fetch(`/api/budgets/${budgetId}/containers`, {
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
 * Update an existing container
 */
export async function updateContainer(
	budgetId: string,
	containerId: string,
	data: ContainerUpdateRequest
): Promise<Container> {
	const response = await fetch(`/api/budgets/${budgetId}/containers/${containerId}`, {
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
 * Delete a container
 */
export async function deleteContainer(budgetId: string, containerId: string): Promise<void> {
	const response = await fetch(`/api/budgets/${budgetId}/containers/${containerId}`, {
		method: 'DELETE',
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}
}
