/**
 * Dashboard API client
 */

import type { ContainerType } from './containers';
import { extractErrorMessage } from './errors';

export interface DashboardData {
	available_balance: number;
	containers: ContainerBalance[];
	month_summary: MonthSummary;
	pending_count: number;
	fixed_expenses: FixedExpense[];
}

export interface ContainerBalance {
	id: string;
	name: string;
	balance: number;
	type: ContainerType;
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
	date: string;
	status: 'paid' | 'pending' | 'overdue';
}

/**
 * Get dashboard data for a budget
 */
export async function getDashboard(budgetId: string): Promise<DashboardData> {
	const response = await fetch(`/api/budgets/${budgetId}/dashboard`, {
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}
