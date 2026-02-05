/**
 * Dashboard API client
 */

import type { Account } from './accounts';

export interface DashboardData {
	available_balance: number;
	accounts: AccountBalance[];
	month_summary: MonthSummary;
	pending_transactions_count: number;
	fixed_expenses: FixedExpense[];
}

export interface AccountBalance {
	id: string;
	name: string;
	balance: number;
	currency: string;
}

export interface MonthSummary {
	income: number;
	expenses: number;
	net: number;
}

export interface FixedExpense {
	id: string;
	name: string;
	expected_amount: number;
	actual_amount?: number;
	expected_date: string;
	status: 'paid' | 'pending' | 'overdue';
}

export interface ApiError {
	detail: string;
}

/**
 * Get dashboard data for a budget
 */
export async function getDashboard(budgetId: string): Promise<DashboardData> {
	const response = await fetch(`/api/budgets/${budgetId}/dashboard`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const error: ApiError = await response.json();
		throw new Error(error.detail || 'Failed to get dashboard data');
	}

	return response.json();
}
