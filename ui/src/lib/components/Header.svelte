<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { budgetStore } from '$lib/stores/budget';
	import { onMount } from 'svelte';

	// Use auto-subscribing $budgetStore pattern
	let budgets = $derived($budgetStore.budgets);
	let loading = $derived($budgetStore.loading);
	let currentBudgetId = $derived($page.params.id || '');
	let currentBudget = $derived(budgets.find((b) => b.id === currentBudgetId));
	let dropdownOpen = $state(false);

	onMount(async () => {
		// Initialize store if not already done
		if (budgets.length === 0 && !loading) {
			await budgetStore.initialize();
		}
	});

	function toggleDropdown() {
		dropdownOpen = !dropdownOpen;
	}

	function selectBudget(budgetId: string) {
		dropdownOpen = false;

		// Update store's current budget
		const budget = budgets.find((b) => b.id === budgetId);
		if (budget) {
			budgetStore.setCurrentBudget(budget);
		}

		// Get current path to preserve section
		const currentPath = $page.url.pathname;
		const pathSegments = currentPath.split('/').filter(Boolean);

		// Check if we're on a budget sub-page (e.g., /budgets/:id/transactions)
		if (pathSegments.length >= 3 && pathSegments[0] === 'budgets') {
			// Replace the budget ID but keep the section
			const section = pathSegments.slice(2).join('/');
			goto(`/budgets/${budgetId}/${section}`);
		} else {
			// Navigate to dashboard (main budget page)
			goto(`/budgets/${budgetId}`);
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && dropdownOpen) {
			dropdownOpen = false;
		}
	}

	function handleDropdownItemKeydown(event: KeyboardEvent, budgetId: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			selectBudget(budgetId);
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.budget-selector')) {
			dropdownOpen = false;
		}
	}

	async function handleLogout() {
		try {
			await fetch('/api/auth/logout', {
				method: 'POST',
				credentials: 'include'
			});
			goto('/login');
		} catch (err) {
			console.error('Logout failed:', err);
		}
	}

	$effect(() => {
		if (dropdownOpen) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});
</script>

<header class="header">
	<div class="header-content">
		<!-- Logo/Brand -->
		<div class="brand">
			<a href="/budgets">{$_('app.name')}</a>
		</div>

		<!-- Budget Selector -->
		{#if currentBudgetId}
			<div class="budget-selector">
				<button
					class="budget-selector-button"
					onclick={toggleDropdown}
					onkeydown={handleKeydown}
					aria-haspopup="listbox"
					aria-expanded={dropdownOpen}
				>
					<span class="budget-name">
						{currentBudget?.name || $_('common.loading')}
					</span>
					<span class="chevron">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="m6 9 6 6 6-6" />
						</svg>
					</span>
				</button>

				{#if dropdownOpen}
					<div class="dropdown" role="listbox">
						{#if loading}
							<div class="dropdown-item loading">{$_('common.loading')}</div>
						{:else if budgets.length === 0}
							<div class="dropdown-item empty">{$_('budget.list.empty')}</div>
						{:else}
							{#each budgets as budget}
								<button
									class="dropdown-item"
									class:active={budget.id === currentBudgetId}
									onclick={() => selectBudget(budget.id)}
									onkeydown={(e) => handleDropdownItemKeydown(e, budget.id)}
									role="option"
									aria-selected={budget.id === currentBudgetId}
								>
									{budget.name}
								</button>
							{/each}
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- User Actions -->
		<div class="actions">
			<button class="action-button" onclick={handleLogout}>
				<span class="action-icon">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
						<polyline points="16 17 21 12 16 7" />
						<line x1="21" x2="9" y1="12" y2="12" />
					</svg>
				</span>
				<span class="action-label">{$_('auth.logout')}</span>
			</button>
		</div>
	</div>
</header>

<style>
	.header {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 60px;
		background: var(--bg-card);
		border-bottom: 1px solid var(--border);
		z-index: 100;
	}

	.header-content {
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--spacing-xl);
		max-width: 100%;
	}

	.brand a {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--accent);
		text-decoration: none;
	}

	/* Budget Selector */
	.budget-selector {
		position: relative;
		flex: 1;
		max-width: 400px;
		margin: 0 var(--spacing-xl);
	}

	.budget-selector-button {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: border-color 0.2s;
	}

	.budget-selector-button:hover {
		border-color: var(--accent);
	}

	.budget-selector-button:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	.budget-name {
		flex: 1;
		text-align: left;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.chevron {
		display: flex;
		align-items: center;
		color: var(--text-secondary);
	}

	.dropdown {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
		max-height: 300px;
		overflow-y: auto;
		z-index: 200;
	}

	.dropdown-item {
		width: 100%;
		display: block;
		padding: var(--spacing-md);
		text-align: left;
		border: none;
		background: transparent;
		color: var(--text-primary);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: background 0.2s;
	}

	.dropdown-item:hover {
		background: var(--bg-page);
	}

	.dropdown-item:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: -2px;
	}

	.dropdown-item.active {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		color: var(--accent);
		font-weight: 500;
	}

	.dropdown-item.loading,
	.dropdown-item.empty {
		color: var(--text-secondary);
		cursor: default;
	}

	/* Actions */
	.actions {
		display: flex;
		gap: var(--spacing-sm);
	}

	.action-button {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: all 0.2s;
	}

	.action-button:hover {
		background: var(--bg-page);
		border-color: var(--accent);
		color: var(--accent);
	}

	.action-icon {
		display: flex;
		align-items: center;
	}

	.action-label {
		display: none;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.header-content {
			padding: 0 var(--spacing-md);
		}

		.brand a {
			font-size: var(--font-size-lg);
		}

		.budget-selector {
			margin: 0 var(--spacing-md);
			max-width: none;
		}

		.action-label {
			display: none;
		}
	}

	@media (min-width: 769px) {
		.action-label {
			display: inline;
		}
	}
</style>
