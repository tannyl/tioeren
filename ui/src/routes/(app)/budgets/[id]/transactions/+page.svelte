<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { _, locale } from '$lib/i18n';
	import { listTransactions, createTransaction } from '$lib/api/transactions';
	import { listContainers } from '$lib/api/containers';
	import type { Transaction } from '$lib/api/transactions';
	import type { Container } from '$lib/api/containers';
	import CategorizationModal from '$lib/components/CategorizationModal.svelte';
	import TransactionModal from '$lib/components/TransactionModal.svelte';
	import SkeletonList from '$lib/components/SkeletonList.svelte';
	import { addToast } from '$lib/stores/toast.svelte';
	import { formatDate } from '$lib/utils/dateFormat';

	// Get budget ID from route params
	let budgetId: string = $derived($page.params.id as string);

	// State
	let transactions = $state<Transaction[]>([]);
	let containers = $state<Container[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let error = $state<string | null>(null);
	let nextCursor = $state<string | null>(null);
	let hasMore = $state(true);

	// Filters
	let selectedContainerId = $state<string>('');
	let selectedStatus = $state<string>('');
	let dateFrom = $state<string>('');
	let dateTo = $state<string>('');

	// Modal state
	let showCategorizationModal = $state(false);
	let selectedTransaction = $state<Transaction | undefined>(undefined);
	let showTransactionModal = $state(false);

	// Intersection observer for infinite scroll
	let sentinelElement = $state<HTMLElement | null>(null);
	let observer: IntersectionObserver | null = null;

	// Reload data when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadContainers();
		loadTransactions();
	});

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}
	});

	// Reactively setup intersection observer when sentinel is available
	$effect(() => {
		if (sentinelElement && !loading) {
			setupIntersectionObserver();
		}

		// Cleanup on re-run or unmount
		return () => {
			if (observer) {
				observer.disconnect();
				observer = null;
			}
		};
	});

	async function loadContainers() {
		try {
			containers = await listContainers(budgetId);
		} catch (err) {
			console.error('Failed to load containers:', err);
		}
	}

	async function loadTransactions(isLoadMore: boolean = false) {
		try {
			if (isLoadMore) {
				loadingMore = true;
			} else {
				loading = true;
				transactions = [];
				nextCursor = null;
				hasMore = true;
			}
			error = null;

			const params: any = {};
			if (selectedContainerId) params.container_id = selectedContainerId;
			if (selectedStatus) params.status = selectedStatus;
			if (dateFrom) params.date_from = dateFrom;
			if (dateTo) params.date_to = dateTo;
			if (isLoadMore && nextCursor) params.cursor = nextCursor;

			const result = await listTransactions(budgetId, params);

			if (isLoadMore) {
				transactions = [...transactions, ...result.data];
			} else {
				transactions = result.data;
			}

			nextCursor = result.next_cursor;
			hasMore = result.next_cursor !== null;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
			loadingMore = false;
		}
	}

	function setupIntersectionObserver() {
		observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				if (entry.isIntersecting && hasMore && !loadingMore && !loading) {
					loadTransactions(true);
				}
			},
			{ rootMargin: '200px' }
		);

		if (sentinelElement) {
			observer.observe(sentinelElement);
		}
	}

	function handleClearFilters() {
		selectedContainerId = '';
		selectedStatus = '';
		dateFrom = '';
		dateTo = '';
		loadTransactions();
	}

	function handleFilterChange() {
		loadTransactions();
	}

	function handleTransactionClick(transaction: Transaction) {
		selectedTransaction = transaction;
		showCategorizationModal = true;
	}

	function handleCategorizationSave() {
		// Reload transactions to see updated status
		loadTransactions();
	}

	async function handleTransactionSave(data: any) {
		await createTransaction(budgetId, data);
		addToast($_('toast.createSuccess'), 'success');
		loadTransactions();
	}

	function handleTransactionKeydown(e: KeyboardEvent, transaction: Transaction) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleTransactionClick(transaction);
		}
	}

	function formatCurrency(amountInOre: number): string {
		const amount = Math.abs(amountInOre / 100);
		return amount.toLocaleString('da-DK', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'uncategorized':
				return 'warning';
			case 'pending_confirmation':
				return 'accent';
			case 'pending_receipt':
				return 'purple';
			case 'categorized':
				return 'positive';
			default:
				return 'accent';
		}
	}

	// Group transactions by date
	let groupedTransactions = $derived.by(() => {
		const groups = new Map<string, Transaction[]>();

		for (const transaction of transactions) {
			const dateKey = transaction.date;
			if (!groups.has(dateKey)) {
				groups.set(dateKey, []);
			}
			groups.get(dateKey)!.push(transaction);
		}

		return Array.from(groups.entries()).sort((a, b) => {
			return new Date(b[0]).getTime() - new Date(a[0]).getTime();
		});
	});
</script>

<div class="page">
	<div class="container">
		<header class="page-header">
			<h1>{$_('transaction.list.title')}</h1>
			<button type="button" class="btn-primary" onclick={() => showTransactionModal = true}>
				{$_('transaction.list.add')}
			</button>
		</header>

		<div class="filters-bar">
			<div class="filters">
				<div class="filter-group">
					<label for="container-filter">{$_('transaction.filter.container')}</label>
					<select
						id="container-filter"
						bind:value={selectedContainerId}
						onchange={handleFilterChange}
					>
						<option value="">{$_('transaction.filter.allContainers')}</option>
						{#each containers as container (container.id)}
							<option value={container.id}>{container.name}</option>
						{/each}
					</select>
				</div>

				<div class="filter-group">
					<label for="status-filter">{$_('transaction.filter.status')}</label>
					<select id="status-filter" bind:value={selectedStatus} onchange={handleFilterChange}>
						<option value="">{$_('transaction.filter.allStatuses')}</option>
						<option value="uncategorized">{$_('transaction.status.uncategorized')}</option>
						<option value="pending_confirmation"
							>{$_('transaction.status.pending_confirmation')}</option
						>
						<option value="pending_receipt">{$_('transaction.status.pending_receipt')}</option>
						<option value="categorized">{$_('transaction.status.categorized')}</option>
					</select>
				</div>

				<div class="filter-group">
					<label for="date-from">{$_('transaction.filter.dateFrom')}</label>
					<input
						id="date-from"
						type="date"
						bind:value={dateFrom}
						onchange={handleFilterChange}
					/>
				</div>

				<div class="filter-group">
					<label for="date-to">{$_('transaction.filter.dateTo')}</label>
					<input id="date-to" type="date" bind:value={dateTo} onchange={handleFilterChange} />
				</div>

				<button type="button" class="btn-secondary btn-clear" onclick={handleClearFilters}>
					{$_('transaction.filter.clear')}
				</button>
			</div>
		</div>

		{#if loading}
			<SkeletonList items={5} />
		{:else if error}
			<div class="error-message">
				<p>{error}</p>
			</div>
		{:else if transactions.length === 0}
			<div class="empty-state">
				<p>
					{selectedContainerId || selectedStatus || dateFrom || dateTo
						? $_('transaction.list.noMatch')
						: $_('transaction.list.empty')}
				</p>
			</div>
		{:else}
			<div class="transaction-list">
				{#each groupedTransactions as [date, dateTransactions] (date)}
					<div class="date-group">
						<div class="date-header">
							{formatDate(date, $locale)}
						</div>
						<div class="transactions">
							{#each dateTransactions as transaction (transaction.id)}
								<div
									class="transaction-card"
									role="button"
									tabindex="0"
									onclick={() => handleTransactionClick(transaction)}
									onkeydown={(e) => handleTransactionKeydown(e, transaction)}
								>
									<div class="transaction-main">
										<div class="transaction-info">
											<div class="transaction-description">{transaction.description}</div>
											{#if transaction.container_name}
												<div class="transaction-container">{transaction.container_name}</div>
											{/if}
										</div>
										<div class="transaction-amount" class:negative={transaction.amount < 0}>
											{transaction.amount < 0 ? '-' : '+'}
											{formatCurrency(transaction.amount)} kr
										</div>
									</div>
									<div class="transaction-footer">
										<span class="status-badge" data-status={getStatusColor(transaction.status)}>
											{$_(`transaction.status.${transaction.status}`)}
										</span>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			<div class="scroll-sentinel" bind:this={sentinelElement}>
				{#if loadingMore}
					<div class="loading-more">
						<p>{$_('transaction.list.loadMore')}</p>
					</div>
				{:else if !hasMore}
					<div class="no-more">
						<p>{$_('transaction.list.noMore')}</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<CategorizationModal
	bind:show={showCategorizationModal}
	transaction={selectedTransaction}
	{budgetId}
	onSave={handleCategorizationSave}
/>

<TransactionModal
	bind:show={showTransactionModal}
	{budgetId}
	{accounts}
	onSave={handleTransactionSave}
/>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.container {
		min-height: 60vh;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-xl);
		gap: var(--spacing-md);
	}

	h1 {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.filters-bar {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-lg);
		margin-bottom: var(--spacing-lg);
	}

	.filters {
		display: flex;
		gap: var(--spacing-md);
		align-items: flex-end;
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
		flex: 1;
		min-width: 150px;
	}

	.filter-group label {
		font-size: var(--font-size-sm);
		font-weight: 500;
		color: var(--text-secondary);
	}

	select,
	input[type='date'] {
		padding: var(--spacing-sm) var(--spacing-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		color: var(--text-primary);
		background: var(--bg-page);
		transition: border-color 0.2s;
	}

	select:focus,
	input[type='date']:focus {
		outline: none;
		border-color: var(--accent);
	}

	.btn-primary,
	.btn-secondary {
		padding: var(--spacing-sm) var(--spacing-lg);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
		border: none;
		white-space: nowrap;
	}

	.btn-primary {
		background: var(--accent);
		color: white;
	}

	.btn-secondary {
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
	}

	.btn-primary:hover,
	.btn-secondary:hover {
		opacity: 0.9;
	}

	.btn-clear {
		align-self: flex-end;
	}

	.empty-state {
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
		text-align: center;
	}

	.transaction-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.date-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.date-header {
		position: sticky;
		top: 0;
		background: var(--bg-page);
		padding: var(--spacing-sm) 0;
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		z-index: 10;
	}

	.transactions {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.transaction-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		cursor: pointer;
		transition: all 0.2s;
	}

	.transaction-card:hover {
		border-color: var(--accent);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
	}

	.transaction-main {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--spacing-md);
		margin-bottom: var(--spacing-sm);
	}

	.transaction-info {
		flex: 1;
		min-width: 0;
	}

	.transaction-description {
		font-size: var(--font-size-base);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-xs);
	}

	.transaction-container {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.transaction-amount {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--positive);
		flex-shrink: 0;
	}

	.transaction-amount.negative {
		color: var(--negative);
	}

	.transaction-footer {
		display: flex;
		justify-content: flex-start;
	}

	.status-badge {
		display: inline-block;
		padding: var(--spacing-xs) var(--spacing-sm);
		border-radius: var(--radius-sm);
		font-size: var(--font-size-xs);
		font-weight: 500;
		text-transform: capitalize;
	}

	.status-badge[data-status='warning'] {
		background: rgba(245, 158, 11, 0.1);
		color: var(--warning);
		border: 1px solid var(--warning);
	}

	.status-badge[data-status='accent'] {
		background: rgba(59, 130, 246, 0.1);
		color: var(--accent);
		border: 1px solid var(--accent);
	}

	.status-badge[data-status='purple'] {
		background: rgba(147, 51, 234, 0.1);
		color: #9333ea;
		border: 1px solid #9333ea;
	}

	.status-badge[data-status='positive'] {
		background: rgba(16, 185, 129, 0.1);
		color: var(--positive);
		border: 1px solid var(--positive);
	}

	.scroll-sentinel {
		min-height: 1px;
	}

	.loading-more,
	.no-more {
		text-align: center;
		padding: var(--spacing-lg);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.page-header {
			flex-direction: column;
			align-items: stretch;
		}

		.page-header .btn-primary {
			width: 100%;
		}

		.filters {
			flex-direction: column;
			align-items: stretch;
		}

		.filter-group {
			min-width: auto;
		}

		.btn-clear {
			align-self: stretch;
		}

		.transaction-main {
			flex-direction: column;
			align-items: stretch;
		}

		.transaction-amount {
			text-align: right;
		}
	}
</style>
