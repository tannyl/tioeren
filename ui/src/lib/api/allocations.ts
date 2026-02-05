/**
 * Transaction allocation API client
 */

import { extractErrorMessage } from './errors';

export interface AllocationRequest {
	budget_post_id: string;
	amount_ore: number;
	is_remainder: boolean;
}

export interface AllocateTransactionRequest {
	allocations: AllocationRequest[];
}

/**
 * Allocate a transaction to budget posts
 */
export async function allocateTransaction(
	budgetId: string,
	transactionId: string,
	data: AllocateTransactionRequest
): Promise<any> {
	const response = await fetch(
		`/api/budgets/${budgetId}/transactions/${transactionId}/allocate`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data),
			credentials: 'include'
		}
	);

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}
