/**
 * Transaction API client
 */

import { extractErrorMessage } from './errors';

export interface Transaction {
	id: string;
	container_id: string;
	container_name?: string | null;
	date: string; // ISO date
	amount: number; // In øre (smallest unit)
	description: string;
	status: 'uncategorized' | 'pending_confirmation' | 'pending_receipt' | 'categorized';
	is_internal_transfer: boolean;
	created_at: string;
	updated_at: string;
}

export interface TransactionListParams {
	container_id?: string;
	status?: string;
	date_from?: string;
	date_to?: string;
	cursor?: string;
	limit?: number;
}

export interface TransactionListResponse {
	data: Transaction[];
	next_cursor: string | null;
}

export interface TransactionCreateRequest {
	container_id: string;
	date: string; // ISO date string YYYY-MM-DD
	amount: number; // In øre (smallest unit)
	description: string;
	is_internal_transfer?: boolean;
	counterpart_container_id?: string;
}

/**
 * List transactions for a budget with optional filters
 */
export async function listTransactions(
	budgetId: string,
	params?: TransactionListParams
): Promise<TransactionListResponse> {
	const queryParams = new URLSearchParams();

	if (params?.container_id) queryParams.set('container_id', params.container_id);
	if (params?.status) queryParams.set('status', params.status);
	if (params?.date_from) queryParams.set('date_from', params.date_from);
	if (params?.date_to) queryParams.set('date_to', params.date_to);
	if (params?.cursor) queryParams.set('cursor', params.cursor);
	if (params?.limit) queryParams.set('limit', params.limit.toString());

	const url = `/api/budgets/${budgetId}/transactions${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

	const response = await fetch(url, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

/**
 * Create a new transaction
 */
export async function createTransaction(
	budgetId: string,
	data: TransactionCreateRequest
): Promise<Transaction> {
	const response = await fetch(`/api/budgets/${budgetId}/transactions`, {
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
