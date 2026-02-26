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
