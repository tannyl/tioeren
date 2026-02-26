<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { _, locale } from '$lib/i18n';
	import { getDashboard } from '$lib/api/dashboard';
	import type { DashboardData } from '$lib/api/dashboard';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';

	let budgetId: string = $derived($page.params.id as string);
	let dashboard = $state<DashboardData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Reload dashboard when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadDashboard();
	});

	async function loadDashboard() {
		try {
			loading = true;
			error = null;
			dashboard = await getDashboard(budgetId);
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toLocaleString('da-DK', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function handlePendingClick() {
		goto(`/budgets/${budgetId}/transactions?status=uncategorized`);
	}
</script>

<div class="page">
	{#if loading}
		<div class="dashboard">
			<SkeletonCard height="250px" />
			<div class="two-column">
				<SkeletonCard height="180px" variant="compact" />
				<SkeletonCard height="180px" variant="compact" />
			</div>
			<SkeletonCard height="300px" />
		</div>
	{:else if error}
		<div class="error-message">
			<p>{error}</p>
		</div>
	{:else if dashboard}
		<div class="dashboard">
			<!-- Available Balance Card -->
			<section class="card balance-card">
				<h2 class="card-title">{$_('dashboard.availableBalance')}</h2>
				<div class="balance-amount" class:negative={dashboard.available_balance < 0}>
					{formatCurrency(dashboard.available_balance)} kr
				</div>
				{#if dashboard.containers.length > 0}
					<div class="container-list">
						{#each dashboard.containers as container}
							<div class="container-item">
								<span class="container-name">{container.name}</span>
								<span class="container-balance" class:negative={container.balance < 0}>
									{formatCurrency(container.balance)} kr
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<!-- Month Summary and Pending Cards -->
			<div class="two-column">
				<!-- Month Summary Card -->
				<section class="card summary-card">
					<h2 class="card-title">{$_('dashboard.monthSummary.title')}</h2>
					<div class="summary-content">
						<div class="summary-item">
							<span class="summary-label">{$_('dashboard.monthSummary.income')}</span>
							<span class="summary-value positive">
								+{formatCurrency(dashboard.month_summary.income)} kr
							</span>
						</div>
						<div class="summary-item">
							<span class="summary-label">{$_('dashboard.monthSummary.expenses')}</span>
							<span class="summary-value negative">
								-{formatCurrency(Math.abs(dashboard.month_summary.expenses))} kr
							</span>
						</div>
						<div class="summary-divider"></div>
						<div class="summary-item">
							<span class="summary-label">{$_('dashboard.monthSummary.net')}</span>
							<span
								class="summary-value net"
								class:positive={dashboard.month_summary.net >= 0}
								class:negative={dashboard.month_summary.net < 0}
							>
								{dashboard.month_summary.net >= 0 ? '+' : ''}{formatCurrency(
									dashboard.month_summary.net
								)} kr
							</span>
						</div>
					</div>
				</section>

				<!-- Pending Transactions Card -->
				<section class="card pending-card">
					<h2 class="card-title">{$_('dashboard.pending.title')}</h2>
					<div class="pending-content">
						<div class="pending-count">{dashboard.pending_count}</div>
						<div class="pending-label">{$_('dashboard.pending.transactions')}</div>
						<button class="btn-primary" onclick={handlePendingClick}>
							{$_('dashboard.pending.handle')}
						</button>
					</div>
				</section>
			</div>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.loading {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
	}

	.error-message {
		padding: var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
	}

	.dashboard {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	.card-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-lg);
	}

	/* Balance Card */
	.balance-card {
		text-align: center;
	}

	.balance-amount {
		font-size: 3rem;
		font-weight: 700;
		color: var(--positive);
		margin-bottom: var(--spacing-lg);
	}

	.balance-amount.negative {
		color: var(--negative);
	}

	.container-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		max-width: 600px;
		margin: 0 auto;
	}

	.container-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
	}

	.container-name {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.container-balance {
		color: var(--text-primary);
		font-weight: 600;
		font-size: var(--font-size-base);
	}

	.container-balance.negative {
		color: var(--negative);
	}

	/* Two Column Layout */
	.two-column {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--spacing-lg);
	}

	/* Month Summary Card */
	.summary-content {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.summary-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.summary-label {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
	}

	.summary-value {
		font-size: var(--font-size-xl);
		font-weight: 700;
	}

	.summary-value.positive {
		color: var(--positive);
	}

	.summary-value.negative {
		color: var(--negative);
	}

	.summary-value.net {
		font-size: var(--font-size-2xl);
	}

	.summary-divider {
		height: 1px;
		background: var(--border);
		margin: var(--spacing-sm) 0;
	}

	/* Pending Card */
	.pending-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--spacing-md);
		padding: var(--spacing-md) 0;
	}

	.pending-count {
		font-size: 3rem;
		font-weight: 700;
		color: var(--accent);
	}

	.pending-label {
		color: var(--text-secondary);
		font-size: var(--font-size-base);
	}

	.btn-primary {
		padding: var(--spacing-sm) var(--spacing-lg);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.btn-primary:hover {
		opacity: 0.9;
	}

	.placeholder {
		padding: var(--spacing-lg);
		text-align: center;
		color: var(--text-secondary);
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.card {
			padding: var(--spacing-lg);
		}

		.balance-amount {
			font-size: 2rem;
		}

		.two-column {
			grid-template-columns: 1fr;
		}

		.summary-value {
			font-size: var(--font-size-lg);
		}

		.summary-value.net {
			font-size: var(--font-size-xl);
		}

		.pending-count {
			font-size: 2rem;
		}

	}
</style>
