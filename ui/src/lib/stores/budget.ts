/**
 * Budget state store
 */

import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { Budget } from '$lib/api/budgets';
import { listBudgets } from '$lib/api/budgets';

interface BudgetState {
	currentBudget: Budget | null;
	budgets: Budget[];
	loading: boolean;
	initialized: boolean;
}

const STORAGE_KEY = 'tioeren_current_budget_id';

function createBudgetStore() {
	const { subscribe, set, update } = writable<BudgetState>({
		currentBudget: null,
		budgets: [],
		loading: false,
		initialized: false
	});

	return {
		subscribe,

		/**
		 * Load all budgets and restore current budget from localStorage
		 */
		async initialize() {
			update((state) => ({ ...state, loading: true }));
			try {
				const budgets = await listBudgets();

				// Try to restore current budget from localStorage
				let currentBudget: Budget | null = null;
				if (browser) {
					const savedId = localStorage.getItem(STORAGE_KEY);
					if (savedId) {
						currentBudget = budgets.find((b) => b.id === savedId) || null;
					}
				}

				// If no saved budget or not found, use first budget
				if (!currentBudget && budgets.length > 0) {
					currentBudget = budgets[0];
				}

				set({ currentBudget, budgets, loading: false, initialized: true });
			} catch (error) {
				console.error('Failed to initialize budgets:', error);
				set({ currentBudget: null, budgets: [], loading: false, initialized: true });
			}
		},

		/**
		 * Refresh budgets list
		 */
		async refresh() {
			update((state) => ({ ...state, loading: true }));
			try {
				const budgets = await listBudgets();
				update((state) => {
					// Preserve current budget if it still exists
					const currentBudget =
						state.currentBudget && budgets.find((b) => b.id === state.currentBudget!.id)
							? budgets.find((b) => b.id === state.currentBudget!.id)!
							: budgets[0] || null;
					return { ...state, budgets, currentBudget, loading: false };
				});
			} catch (error) {
				console.error('Failed to refresh budgets:', error);
				update((state) => ({ ...state, loading: false }));
			}
		},

		/**
		 * Set the current budget
		 */
		setCurrentBudget(budget: Budget) {
			update((state) => ({ ...state, currentBudget: budget }));
			if (browser) {
				localStorage.setItem(STORAGE_KEY, budget.id);
			}
		},

		/**
		 * Add a new budget to the list and set it as current
		 */
		addBudget(budget: Budget) {
			update((state) => ({
				...state,
				budgets: [...state.budgets, budget],
				currentBudget: budget
			}));
			if (browser) {
				localStorage.setItem(STORAGE_KEY, budget.id);
			}
		},

		/**
		 * Update an existing budget in the list
		 */
		updateBudget(budget: Budget) {
			update((state) => ({
				...state,
				budgets: state.budgets.map((b) => (b.id === budget.id ? budget : b)),
				currentBudget: state.currentBudget?.id === budget.id ? budget : state.currentBudget
			}));
		},

		/**
		 * Remove a budget from the list
		 */
		removeBudget(budgetId: string) {
			update((state) => {
				const budgets = state.budgets.filter((b) => b.id !== budgetId);
				let currentBudget = state.currentBudget;

				// If deleted budget was current, switch to first available
				if (currentBudget?.id === budgetId) {
					currentBudget = budgets[0] || null;
					if (browser && currentBudget) {
						localStorage.setItem(STORAGE_KEY, currentBudget.id);
					} else if (browser) {
						localStorage.removeItem(STORAGE_KEY);
					}
				}

				return { ...state, budgets, currentBudget };
			});
		},

		/**
		 * Clear the store
		 */
		clear() {
			set({ currentBudget: null, budgets: [], loading: false, initialized: false });
			if (browser) {
				localStorage.removeItem(STORAGE_KEY);
			}
		}
	};
}

export const budgetStore = createBudgetStore();
