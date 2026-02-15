<script lang="ts">
	import { onMount } from 'svelte';
	import { _, locale } from '$lib/i18n';
	import type { Transaction } from '$lib/api/transactions';
	import type { Category, BudgetPost } from '$lib/api/categories';
	import { getCategories } from '$lib/api/categories';
	import { allocateTransaction } from '$lib/api/allocations';
	import { formatDate } from '$lib/utils/dateFormat';

	let {
		show = $bindable(false),
		transaction,
		budgetId,
		onSave
	}: {
		show?: boolean;
		transaction?: Transaction;
		budgetId: string;
		onSave: () => void;
	} = $props();

	interface Allocation {
		id: string;
		budgetPostId: string;
		budgetPostName: string;
		amount: string;
		isRemainder: boolean;
	}

	let categories = $state<Category[]>([]);
	let allocations = $state<Allocation[]>([]);
	let searchQuery = $state('');
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let createRule = $state(false);
	let expandedCategories = $state<Set<string>>(new Set());

	// Load categories when modal opens
	$effect(() => {
		if (show && categories.length === 0) {
			loadCategories();
		}
	});

	// Reset state when modal closes
	$effect(() => {
		if (!show) {
			allocations = [];
			searchQuery = '';
			error = null;
			createRule = false;
			expandedCategories = new Set();
		}
	});

	async function loadCategories() {
		loading = true;
		try {
			const loadedCategories = await getCategories(budgetId);
			categories = loadedCategories;
			// Initialize expanded categories directly
			expandedCategories = new Set(loadedCategories.map(cat => cat.id));
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	function handleClose() {
		show = false;
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	function toggleCategory(categoryId: string) {
		if (expandedCategories.has(categoryId)) {
			expandedCategories.delete(categoryId);
		} else {
			expandedCategories.add(categoryId);
		}
		// No self-assignment needed in Svelte 5
	}

	function addAllocation(budgetPost: BudgetPost) {
		const existing = allocations.find((a) => a.budgetPostId === budgetPost.id);
		if (existing) return; // Already added

		const newAllocation: Allocation = {
			id: crypto.randomUUID(),
			budgetPostId: budgetPost.id,
			budgetPostName: budgetPost.name,
			amount: '',
			isRemainder: allocations.length === 0 // First one is remainder by default
		};
		allocations = [...allocations, newAllocation];
	}

	function removeAllocation(id: string) {
		allocations = allocations.filter((a) => a.id !== id);
		// If we removed the remainder, make the first one remainder
		if (allocations.length > 0 && !allocations.some((a) => a.isRemainder)) {
			allocations[0].isRemainder = true;
		}
	}

	function setRemainder(id: string) {
		allocations = allocations.map((a) => ({
			...a,
			isRemainder: a.id === id
		}));
	}

	function calculateTotal(): number {
		return allocations
			.filter((a) => !a.isRemainder)
			.reduce((sum, a) => sum + (parseFloat(a.amount) || 0), 0);
	}

	function calculateRemaining(): number {
		if (!transaction) return 0;
		const transactionAmount = Math.abs(transaction.amount / 100);
		return transactionAmount - calculateTotal();
	}

	function validateAllocations(): string | null {
		if (allocations.length === 0) {
			return $_('categorization.errors.selectBudgetPost');
		}

		if (!transaction) return null;

		const total = calculateTotal();
		const remaining = calculateRemaining();
		const transactionAmount = Math.abs(transaction.amount / 100);

		// If there's a remainder allocation, remaining must be >= 0
		if (allocations.some((a) => a.isRemainder) && remaining < 0) {
			return $_('categorization.errors.exceedsAmount');
		}

		// If no remainder, total must equal transaction amount
		if (!allocations.some((a) => a.isRemainder) && Math.abs(total - transactionAmount) > 0.01) {
			return $_('categorization.errors.exceedsAmount');
		}

		return null;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;

		const validationError = validateAllocations();
		if (validationError) {
			error = validationError;
			return;
		}

		if (!transaction) return;

		saving = true;

		try {
			const allocationRequests = allocations.map((a) => {
				const amountInOre = a.isRemainder
					? Math.round(calculateRemaining() * 100)
					: Math.round(parseFloat(a.amount) * 100);

				return {
					budget_post_id: a.budgetPostId,
					amount_ore: amountInOre,
					is_remainder: a.isRemainder
				};
			});

			await allocateTransaction(budgetId, transaction.id, {
				allocations: allocationRequests
			});

			show = false;
			onSave();
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			saving = false;
		}
	}

	function handleClear() {
		allocations = [];
	}

	function formatCurrency(amountInOre: number): string {
		const amount = Math.abs(amountInOre / 100);
		return amount.toLocaleString('da-DK', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	// Flatten categories and budget posts for searching
	function getAllBudgetPosts(cats: Category[]): Array<{ post: BudgetPost; category: Category }> {
		const result: Array<{ post: BudgetPost; category: Category }> = [];

		function traverse(cat: Category) {
			cat.budget_posts.forEach((post) => {
				result.push({ post, category: cat });
			});
			cat.children.forEach(traverse);
		}

		cats.forEach(traverse);
		return result;
	}

	let filteredBudgetPosts = $derived.by(() => {
		if (!searchQuery.trim()) return [];
		const query = searchQuery.toLowerCase();
		return getAllBudgetPosts(categories).filter((item) =>
			item.post.name.toLowerCase().includes(query)
		);
	});

	let showSearchResults = $derived(searchQuery.trim().length > 0);
</script>

{#if show && transaction}
	<div class="modal-backdrop" onclick={handleBackdropClick} role="presentation">
		<div class="modal" role="dialog" aria-modal="true">
			<div class="modal-header">
				<h2>{$_('categorization.title')}</h2>
				<button
					class="close-button"
					onclick={handleClose}
					type="button"
					aria-label={$_('common.close')}
				>
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="18" y1="6" x2="6" y2="18" />
						<line x1="6" y1="6" x2="18" y2="18" />
					</svg>
				</button>
			</div>

			<form onsubmit={handleSubmit}>
				<div class="modal-body">
					<!-- Transaction Details -->
					<div class="transaction-details">
						<div class="transaction-header">
							<div class="transaction-info">
								<div class="transaction-description">{transaction.description}</div>
								<div class="transaction-meta">
									{formatDate(transaction.date, $locale)}
									{#if transaction.account_name}
										• {transaction.account_name}
									{/if}
								</div>
							</div>
							<div class="transaction-amount" class:negative={transaction.amount < 0}>
								{transaction.amount < 0 ? '-' : '+'}
								{formatCurrency(transaction.amount)} kr
							</div>
						</div>
					</div>

					<!-- Budget Post Selector -->
					<div class="selector-section">
						<label for="search">{$_('categorization.selectBudgetPost')}</label>
						<input
							id="search"
							type="text"
							bind:value={searchQuery}
							placeholder={$_('categorization.search')}
							disabled={loading || saving}
						/>

						{#if loading}
							<div class="loading-state">
								<p>{$_('common.loading')}</p>
							</div>
						{:else if showSearchResults}
							<div class="search-results">
								{#if filteredBudgetPosts.length === 0}
									<div class="empty-results">
										<p>{$_('transaction.list.noMatch')}</p>
									</div>
								{:else}
									{#each filteredBudgetPosts as { post, category } (post.id)}
										<button
											type="button"
											class="budget-post-item"
											onclick={() => addAllocation(post)}
											disabled={allocations.some((a) => a.budgetPostId === post.id)}
										>
											<span class="post-name">{post.name}</span>
											<span class="post-category">{category.name}</span>
										</button>
									{/each}
								{/if}
							</div>
						{:else}
							<div class="category-tree">
								{#each categories as category (category.id)}
									<div class="category">
										<button
											type="button"
											class="category-header"
											onclick={() => toggleCategory(category.id)}
										>
											<svg
												width="16"
												height="16"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												class:expanded={expandedCategories.has(category.id)}
											>
												<polyline points="9 18 15 12 9 6"></polyline>
											</svg>
											<span>{category.name}</span>
										</button>

										{#if expandedCategories.has(category.id)}
											<div class="budget-posts">
												{#each category.budget_posts as post (post.id)}
													<button
														type="button"
														class="budget-post-item"
														onclick={() => addAllocation(post)}
														disabled={allocations.some((a) => a.budgetPostId === post.id)}
													>
														{post.name}
													</button>
												{/each}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Allocations -->
					{#if allocations.length > 0}
						<div class="allocations-section">
							<h3>{$_('categorization.allocation.title')}</h3>

							<div class="allocations-list">
								{#each allocations as allocation (allocation.id)}
									<div class="allocation-item">
										<div class="allocation-header">
											<span class="allocation-name">{allocation.budgetPostName}</span>
											<button
												type="button"
												class="remove-button"
												onclick={() => removeAllocation(allocation.id)}
												aria-label={$_('common.delete')}
											>
												<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
													<line x1="18" y1="6" x2="6" y2="18" />
													<line x1="6" y1="6" x2="18" y2="18" />
												</svg>
											</button>
										</div>
										<div class="allocation-input">
											{#if allocation.isRemainder}
												<div class="remainder-display">
													<span>{$_('categorization.allocation.remainder')}</span>
													<span class="remainder-amount">
														{calculateRemaining().toFixed(2)} kr
													</span>
												</div>
											{:else}
												<input
													type="number"
													step="0.01"
													bind:value={allocation.amount}
													placeholder="0.00"
													disabled={saving}
												/>
												<button
													type="button"
													class="btn-text"
													onclick={() => setRemainder(allocation.id)}
													disabled={saving}
												>
													{$_('categorization.allocation.remainder')}
												</button>
											{/if}
										</div>
									</div>
								{/each}
							</div>

							<div class="allocation-summary">
								<div class="summary-row">
									<span>{$_('categorization.allocation.total')}</span>
									<span class="summary-value">{calculateTotal().toFixed(2)} kr</span>
								</div>
								<div class="summary-row">
									<span>{$_('categorization.allocation.remaining')}</span>
									<span class="summary-value" class:negative={calculateRemaining() < 0}>
										{calculateRemaining().toFixed(2)} kr
									</span>
								</div>
							</div>
						</div>
					{/if}

					<!-- Rule Creation Placeholder -->
					<div class="rule-section">
						<label class="checkbox-label">
							<input type="checkbox" bind:checked={createRule} disabled={saving} />
							<span>{$_('categorization.rule.create')}</span>
						</label>
					</div>

					{#if error}
						<div class="error-message">
							{error}
						</div>
					{/if}
				</div>

				<div class="modal-footer">
					{#if allocations.length > 0}
						<button
							type="button"
							class="btn-text"
							onclick={handleClear}
							disabled={saving}
						>
							{$_('categorization.actions.clear')}
						</button>
					{/if}
					<div class="footer-actions">
						<button type="button" class="btn-secondary" onclick={handleClose} disabled={saving}>
							{$_('categorization.actions.cancel')}
						</button>
						<button type="submit" class="btn-primary" disabled={saving || allocations.length === 0}>
							{saving ? $_('common.loading') : $_('categorization.actions.save')}
						</button>
					</div>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: var(--spacing-md);
	}

	.modal {
		background: var(--bg-card);
		border-radius: var(--radius-lg);
		max-width: 700px;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-bottom: 1px solid var(--border);
	}

	.modal-header h2 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.close-button {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: var(--spacing-xs);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-md);
		transition: all 0.2s;
	}

	.close-button:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.modal-body {
		padding: var(--spacing-xl);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.transaction-details {
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-lg);
	}

	.transaction-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--spacing-md);
	}

	.transaction-info {
		flex: 1;
		min-width: 0;
	}

	.transaction-description {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-xs);
	}

	.transaction-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.transaction-amount {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--positive);
		flex-shrink: 0;
	}

	.transaction-amount.negative {
		color: var(--negative);
	}

	.selector-section {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	label {
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
	}

	input[type='text'],
	input[type='number'] {
		padding: var(--spacing-sm) var(--spacing-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		color: var(--text-primary);
		background: var(--bg-page);
		transition: border-color 0.2s;
	}

	input[type='text']:focus,
	input[type='number']:focus {
		outline: none;
		border-color: var(--accent);
	}

	input[type='text']:disabled,
	input[type='number']:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.loading-state,
	.empty-results {
		text-align: center;
		padding: var(--spacing-lg);
		color: var(--text-secondary);
	}

	.search-results,
	.category-tree {
		max-height: 300px;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-page);
	}

	.category {
		border-bottom: 1px solid var(--border);
	}

	.category:last-child {
		border-bottom: none;
	}

	.category-header {
		width: 100%;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-md);
		background: none;
		border: none;
		cursor: pointer;
		color: var(--text-primary);
		font-weight: 600;
		font-size: var(--font-size-base);
		text-align: left;
		transition: background 0.2s;
	}

	.category-header:hover {
		background: var(--bg-card);
	}

	.category-header svg {
		transition: transform 0.2s;
	}

	.category-header svg.expanded {
		transform: rotate(90deg);
	}

	.budget-posts {
		display: flex;
		flex-direction: column;
	}

	.budget-post-item {
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md) var(--spacing-sm) var(--spacing-xl);
		background: none;
		border: none;
		cursor: pointer;
		color: var(--text-primary);
		font-size: var(--font-size-base);
		text-align: left;
		transition: background 0.2s;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.budget-post-item:hover:not(:disabled) {
		background: var(--bg-card);
	}

	.budget-post-item:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.post-category {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.allocations-section {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.allocations-section h3 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.allocations-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.allocation-item {
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
	}

	.allocation-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-sm);
	}

	.allocation-name {
		font-weight: 500;
		color: var(--text-primary);
	}

	.remove-button {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: var(--spacing-xs);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		transition: all 0.2s;
	}

	.remove-button:hover {
		background: var(--bg-card);
		color: var(--negative);
	}

	.allocation-input {
		display: flex;
		gap: var(--spacing-sm);
		align-items: center;
	}

	.allocation-input input {
		flex: 1;
	}

	.remainder-display {
		flex: 1;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-sm);
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid var(--accent);
		border-radius: var(--radius-md);
	}

	.remainder-amount {
		font-weight: 600;
		color: var(--accent);
	}

	.btn-text {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		font-size: var(--font-size-sm);
		font-weight: 500;
		padding: var(--spacing-xs) var(--spacing-sm);
		border-radius: var(--radius-sm);
		transition: background 0.2s;
	}

	.btn-text:hover:not(:disabled) {
		background: rgba(59, 130, 246, 0.1);
	}

	.btn-text:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.allocation-summary {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
		padding: var(--spacing-md);
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.summary-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: var(--font-size-base);
	}

	.summary-value {
		font-weight: 600;
		color: var(--text-primary);
	}

	.summary-value.negative {
		color: var(--negative);
	}

	.rule-section {
		padding: var(--spacing-md);
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		cursor: pointer;
		flex-direction: row;
	}

	.checkbox-label input[type='checkbox'] {
		cursor: pointer;
		width: 20px;
		height: 20px;
	}

	.checkbox-label span {
		font-weight: normal;
	}

	.error-message {
		padding: var(--spacing-sm) var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
		font-size: var(--font-size-sm);
	}

	.modal-footer {
		display: flex;
		gap: var(--spacing-md);
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-top: 1px solid var(--border);
	}

	.footer-actions {
		display: flex;
		gap: var(--spacing-md);
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

	.btn-primary:disabled,
	.btn-secondary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary:hover:not(:disabled),
	.btn-secondary:hover:not(:disabled) {
		opacity: 0.9;
	}

	@media (max-width: 768px) {
		.modal {
			max-width: 100%;
			max-height: 100vh;
			border-radius: 0;
		}

		.modal-body {
			padding: var(--spacing-lg);
		}

		.transaction-header {
			flex-direction: column;
			align-items: stretch;
		}

		.transaction-amount {
			text-align: right;
		}

		.modal-footer {
			flex-direction: column;
			align-items: stretch;
			padding: var(--spacing-lg);
		}

		.footer-actions {
			flex-direction: column-reverse;
		}

		.btn-primary,
		.btn-secondary,
		.btn-text {
			width: 100%;
		}
	}
</style>
