<script lang="ts">
	import { onMount } from 'svelte';
	import { _ } from '$lib/i18n';
	import { budgetStore } from '$lib/stores/budget';
	import { goto } from '$app/navigation';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			await budgetStore.initialize();
		} catch (err) {
			error = err instanceof Error ? err.message : $_('common.error');
		} finally {
			loading = false;
		}
	});

	function handleBudgetClick(budgetId: string) {
		goto(`/budgets/${budgetId}`);
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toFixed(2);
	}
</script>

<div class="page">
	<header class="page-header">
		<h1>{$_('budget.list.title')}</h1>
		<a href="/budgets/new" class="btn-primary">
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<line x1="12" y1="5" x2="12" y2="19" />
				<line x1="5" y1="12" x2="19" y2="12" />
			</svg>
			{$_('budget.list.create')}
		</a>
	</header>

	{#if loading}
		<div class="budget-grid">
			<SkeletonCard height="150px" variant="compact" />
			<SkeletonCard height="150px" variant="compact" />
			<SkeletonCard height="150px" variant="compact" />
		</div>
	{:else if error}
		<div class="error-message">
			<p>{error}</p>
		</div>
	{:else if $budgetStore.budgets.length === 0}
		<div class="empty-state">
			<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
				<rect x="2" y="4" width="20" height="16" rx="2" />
				<line x1="2" y1="10" x2="22" y2="10" />
			</svg>
			<h2>{$_('budget.list.empty')}</h2>
			<p>{$_('budget.list.create')}</p>
			<a href="/budgets/new" class="btn-primary">
				{$_('budget.list.create')}
			</a>
		</div>
	{:else}
		<div class="budget-grid">
			{#each $budgetStore.budgets as budget (budget.id)}
				<button class="budget-card" onclick={() => handleBudgetClick(budget.id)}>
					<div class="card-header">
						<h3>{budget.name}</h3>
						<svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<polyline points="9 18 15 12 9 6" />
						</svg>
					</div>
					{#if budget.total_balance !== undefined}
						<div class="balance">
							<span class="balance-label">{$_('budget.list.balance')}</span>
							<span class="balance-amount" class:negative={budget.total_balance < 0}>
								{formatCurrency(budget.total_balance)} kr
							</span>
						</div>
					{/if}
					{#if budget.warning_threshold}
						<div class="warning-threshold">
							<span class="label">{$_('budget.field.warningThreshold')}:</span>
							<span>{formatCurrency(budget.warning_threshold)} kr</span>
						</div>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-xl);
	}

	h1 {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.btn-primary {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-lg);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		text-decoration: none;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.btn-primary:hover {
		opacity: 0.9;
	}

	.error-message {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--negative);
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--spacing-xl) var(--spacing-lg);
		text-align: center;
		min-height: 400px;
	}

	.empty-state svg {
		color: var(--text-secondary);
		margin-bottom: var(--spacing-lg);
	}

	.empty-state h2 {
		font-size: var(--font-size-2xl);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-sm);
	}

	.empty-state p {
		color: var(--text-secondary);
		margin-bottom: var(--spacing-lg);
	}

	.budget-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: var(--spacing-lg);
	}

	.budget-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-lg);
		text-align: left;
		cursor: pointer;
		transition: all 0.2s;
		width: 100%;
	}

	.budget-card:hover {
		border-color: var(--accent);
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
		transform: translateY(-2px);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-md);
	}

	.card-header h3 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
	}

	.chevron {
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.balance {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
		margin-bottom: var(--spacing-md);
	}

	.balance-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.balance-amount {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--positive);
	}

	.balance-amount.negative {
		color: var(--negative);
	}

	.warning-threshold {
		display: flex;
		gap: var(--spacing-xs);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.warning-threshold .label {
		font-weight: 500;
	}

	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.page-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--spacing-md);
		}

		.budget-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
