<script lang="ts">
	import { _ } from '$lib/i18n';
	import { budgetStore } from '$lib/stores/budget';
	import { goto } from '$app/navigation';

	let { compact = false }: { compact?: boolean } = $props();

	let isOpen = $state(false);

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	function selectBudget(budget: typeof $budgetStore.currentBudget) {
		if (budget) {
			budgetStore.setCurrentBudget(budget);
			// Navigate to the budget's dashboard (will be implemented later)
			goto(`/budgets/${budget.id}`);
		}
		isOpen = false;
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.budget-selector')) {
			isOpen = false;
		}
	}
</script>

<svelte:document onclick={handleClickOutside} />

<div class="budget-selector" class:compact>
	<button class="selector-button" onclick={toggleDropdown} aria-expanded={isOpen}>
		<span class="budget-name">
			{$budgetStore.currentBudget?.name || $_('budget.list.title')}
		</span>
		<svg
			class="chevron"
			class:open={isOpen}
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
		>
			<polyline points="6 9 12 15 18 9" />
		</svg>
	</button>

	{#if isOpen && $budgetStore.budgets.length > 0}
		<div class="dropdown">
			{#each $budgetStore.budgets as budget (budget.id)}
				<button
					class="dropdown-item"
					class:active={$budgetStore.currentBudget?.id === budget.id}
					onclick={() => selectBudget(budget)}
				>
					<span class="item-name">{budget.name}</span>
					{#if budget.total_balance !== undefined}
						<span class="item-balance" class:negative={budget.total_balance < 0}>
							{(budget.total_balance / 100).toFixed(2)} kr
						</span>
					{/if}
				</button>
			{/each}

			<div class="dropdown-divider"></div>

			<a href="/budgets" class="dropdown-item" onclick={() => (isOpen = false)}>
				{$_('budget.list.title')}
			</a>
			<a href="/budgets/new" class="dropdown-item" onclick={() => (isOpen = false)}>
				{$_('budget.list.create')}
			</a>
		</div>
	{/if}
</div>

<style>
	.budget-selector {
		position: relative;
	}

	.selector-button {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: all 0.2s;
		min-width: 200px;
	}

	.compact .selector-button {
		min-width: 150px;
		padding: var(--spacing-xs) var(--spacing-sm);
		font-size: var(--font-size-sm);
	}

	.selector-button:hover {
		border-color: var(--accent);
	}

	.budget-name {
		flex: 1;
		text-align: left;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.chevron {
		flex-shrink: 0;
		transition: transform 0.2s;
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	.dropdown {
		position: absolute;
		top: calc(100% + var(--spacing-xs));
		left: 0;
		right: 0;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
		z-index: 1000;
		max-height: 400px;
		overflow-y: auto;
	}

	.dropdown-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md);
		background: none;
		border: none;
		color: var(--text-primary);
		font-size: var(--font-size-base);
		text-align: left;
		text-decoration: none;
		cursor: pointer;
		transition: background 0.2s;
	}

	.dropdown-item:hover {
		background: var(--bg-page);
	}

	.dropdown-item.active {
		background: var(--bg-page);
		color: var(--accent);
		font-weight: 500;
	}

	.item-name {
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.item-balance {
		flex-shrink: 0;
		font-size: var(--font-size-sm);
		color: var(--positive);
		font-weight: 500;
		margin-left: var(--spacing-sm);
	}

	.item-balance.negative {
		color: var(--negative);
	}

	.dropdown-divider {
		height: 1px;
		background: var(--border);
		margin: var(--spacing-xs) 0;
	}
</style>
