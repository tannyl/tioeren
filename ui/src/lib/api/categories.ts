/**
 * Category API client
 */

import { extractErrorMessage } from './errors';

export interface BudgetPost {
	id: string;
	name: string;
	category_id: string;
	amount_min: number;
	amount_max: number | null;
	type: 'fixed' | 'ceiling' | 'rolling';
}

export interface Category {
	id: string;
	name: string;
	parent_id: string | null;
	budget_posts: BudgetPost[];
	children: Category[];
}

export interface CategoryTreeResponse {
	data: Category[];
}

/**
 * Get category tree with budget posts for a budget
 */
export async function getCategories(budgetId: string): Promise<Category[]> {
	const response = await fetch(`/api/budgets/${budgetId}/categories`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	const result: CategoryTreeResponse = await response.json();
	return result.data;
}
