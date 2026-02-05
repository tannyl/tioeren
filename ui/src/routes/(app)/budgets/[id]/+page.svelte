<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { _ } from '$lib/i18n';
	import { getDashboard } from '$lib/api/dashboard';
	import type { DashboardData, FixedExpense } from '$lib/api/dashboard';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';

	let budgetId: string = $derived($page.params.id as string);
	let dashboard = $state<DashboardData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		await loadDashboard();
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

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' });
	}

	function handlePendingClick() {
		goto(`/budgets/${budgetId}/transactions?status=uncategorized`);
	}

	function getStatusIcon(status: string): string {
		switch (status) {
			case 'paid':
				return 'M20 6 9 17l-5-5'; // Check icon
			case 'pending':
				return 'M12 6v6l4 2'; // Clock icon
			case 'overdue':
				return 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z M12 9v4 M12 17h.01'; // Alert triangle
			default:
				return '';
		}
	}

	function getStatusClass(status: string): string {
		switch (status) {
			case 'paid':
				return 'status-paid';
			case 'pending':
				return 'status-pending';
			case 'overdue':
				return 'status-overdue';
			default:
				return '';
		}
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
				{#if dashboard.accounts.length > 0}
					<div class="account-list">
						{#each dashboard.accounts as account}
							<div class="account-item">
								<span class="account-name">{account.name}</span>
								<span class="account-balance" class:negative={account.balance < 0}>
									{formatCurrency(account.balance)} kr
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

			<!-- Fixed Expenses Card -->
			<section class="card expenses-card">
				<h2 class="card-title">{$_('dashboard.fixedExpenses.title')}</h2>
				{#if dashboard.fixed_expenses.length === 0}
					<div class="placeholder">
						<p>{$_('dashboard.fixedExpenses.empty')}</p>
					</div>
				{:else}
					<div class="expenses-list">
						{#each dashboard.fixed_expenses as expense}
							<div class="expense-item {getStatusClass(expense.status)}">
								<div class="expense-status">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d={getStatusIcon(expense.status)} />
									</svg>
								</div>
								<div class="expense-info">
									<div class="expense-name">{expense.name}</div>
									<div class="expense-date">{formatDate(expense.expected_date)}</div>
								</div>
								<div class="expense-amount">
									<div class="expense-expected">
										{formatCurrency(Math.abs(expense.expected_amount))} kr
									</div>
									{#if expense.actual_amount !== undefined && expense.actual_amount !== null}
										<div class="expense-actual">
											({formatCurrency(Math.abs(expense.actual_amount))} kr)
										</div>
									{/if}
								</div>
								<div class="expense-status-label">
									{$_(`dashboard.fixedExpenses.status.${expense.status}`)}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</section>
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

	.account-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		max-width: 600px;
		margin: 0 auto;
	}

	.account-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
	}

	.account-name {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.account-balance {
		color: var(--text-primary);
		font-weight: 600;
		font-size: var(--font-size-base);
	}

	.account-balance.negative {
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

	/* Fixed Expenses Card */
	.expenses-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.expense-item {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		padding: var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
		border-left: 3px solid transparent;
	}

	.expense-item.status-paid {
		border-left-color: var(--positive);
	}

	.expense-item.status-pending {
		border-left-color: var(--text-secondary);
	}

	.expense-item.status-overdue {
		border-left-color: var(--negative);
	}

	.expense-status {
		flex-shrink: 0;
	}

	.expense-status svg {
		display: block;
	}

	.status-paid .expense-status {
		color: var(--positive);
	}

	.status-pending .expense-status {
		color: var(--text-secondary);
	}

	.status-overdue .expense-status {
		color: var(--negative);
	}

	.expense-info {
		flex: 1;
		min-width: 0;
	}

	.expense-name {
		font-weight: 500;
		color: var(--text-primary);
		margin-bottom: var(--spacing-xs);
	}

	.expense-date {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.expense-amount {
		text-align: right;
		flex-shrink: 0;
	}

	.expense-expected {
		font-weight: 600;
		color: var(--text-primary);
	}

	.expense-actual {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-top: var(--spacing-xs);
	}

	.expense-status-label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		padding: var(--spacing-xs) var(--spacing-sm);
		border-radius: var(--radius-sm);
		flex-shrink: 0;
	}

	.status-paid .expense-status-label {
		background: rgba(16, 185, 129, 0.1);
		color: var(--positive);
	}

	.status-pending .expense-status-label {
		background: rgba(107, 114, 128, 0.1);
		color: var(--text-secondary);
	}

	.status-overdue .expense-status-label {
		background: rgba(239, 68, 68, 0.1);
		color: var(--negative);
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

		.expense-item {
			flex-wrap: wrap;
		}

		.expense-status-label {
			width: 100%;
			text-align: center;
			margin-top: var(--spacing-xs);
		}
	}
</style>
