<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import {
		listBudgetPosts,
		createBudgetPost,
		updateBudgetPost,
		deleteBudgetPost
	} from '$lib/api/budgetPosts';
	import { getCategories } from '$lib/api/categories';
	import { listAccounts } from '$lib/api/accounts';
	import type { BudgetPost } from '$lib/api/budgetPosts';
	import type { Category } from '$lib/api/categories';
	import type { Account } from '$lib/api/accounts';
	import BudgetPostModal from '$lib/components/BudgetPostModal.svelte';
	import SkeletonList from '$lib/components/SkeletonList.svelte';
	import { addToast } from '$lib/stores/toast.svelte';

	// Get budget ID from route params
	let budgetId: string = $derived($page.params.id as string);

	// State
	let budgetPosts = $state<BudgetPost[]>([]);
	let categories = $state<Category[]>([]);
	let accounts = $state<Account[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Modal state
	let showModal = $state(false);
	let editingPost = $state<BudgetPost | undefined>(undefined);
	let postToDelete = $state<string | null>(null);

	// Month labels for recurrence display
	const monthKeys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

	// Reload data when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadData();
	});

	async function loadData() {
		try {
			loading = true;
			error = null;
			const [postsData, categoriesData, accountsData] = await Promise.all([
				listBudgetPosts(budgetId),
				getCategories(budgetId),
				listAccounts(budgetId)
			]);
			budgetPosts = postsData;
			categories = categoriesData;
			accounts = accountsData;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	function handleCreate() {
		editingPost = undefined;
		showModal = true;
	}

	function handleEdit(post: BudgetPost) {
		editingPost = post;
		showModal = true;
	}

	async function handleSave(data: any) {
		try {
			if (editingPost) {
				await updateBudgetPost(budgetId, editingPost.id, data);
				addToast($_('toast.updateSuccess'), 'success');
			} else {
				await createBudgetPost(budgetId, data);
				addToast($_('toast.createSuccess'), 'success');
			}
			await loadData();
		} catch (err) {
			throw err;
		}
	}

	function handleShowDelete(postId: string) {
		postToDelete = postId;
	}

	function handleCancelDelete() {
		postToDelete = null;
	}

	async function handleDelete() {
		if (!postToDelete) return;

		try {
			await deleteBudgetPost(budgetId, postToDelete);
			addToast($_('toast.deleteSuccess'), 'success');
			postToDelete = null;
			await loadData();
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
		}
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toLocaleString('da-DK', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	// Category name is now directly on the post
	function getCategoryName(post: BudgetPost): string {
		return post.category_name || $_('budgetPosts.noCategory');
	}

	function formatPatternSummary(post: BudgetPost): string {
		if (!post.amount_patterns || post.amount_patterns.length === 0) {
			return '-';
		}

		// If single pattern, show the amount
		if (post.amount_patterns.length === 1) {
			return `${formatCurrency(post.amount_patterns[0].amount)} kr`;
		}

		// If multiple patterns, show count
		return post.amount_patterns.length === 1
			? $_('budgetPosts.patternCount', { values: { count: post.amount_patterns.length } })
			: $_('budgetPosts.patternCountPlural', { values: { count: post.amount_patterns.length } });
	}

	// Group budget posts by category
	let groupedPosts = $derived.by(() => {
		const groups = new Map<string, { id: string; name: string; posts: BudgetPost[] }>();

		for (const post of budgetPosts) {
			const categoryId = post.category_id;
			const categoryName = getCategoryName(post);
			if (!groups.has(categoryId)) {
				groups.set(categoryId, { id: categoryId, name: categoryName, posts: [] });
			}
			groups.get(categoryId)!.posts.push(post);
		}

		// Sort groups by category name
		return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name, 'da-DK'));
	});
</script>

<div class="page">
	<div class="container">
		<header class="page-header">
			<h1>{$_('budgetPosts.title')}</h1>
			<button type="button" class="btn-primary" onclick={handleCreate}>
				{$_('budgetPosts.create')}
			</button>
		</header>

		{#if loading}
			<SkeletonList items={5} />
		{:else if error}
			<div class="error-message">
				<p>{error}</p>
			</div>
		{:else if budgetPosts.length === 0}
			<div class="empty-state">
				<p>{$_('budgetPosts.noPosts')}</p>
			</div>
		{:else}
			<div class="posts-container">
				{#each groupedPosts as group (group.id)}
					<div class="category-group">
						<h2 class="category-header">{group.name}</h2>
						<div class="posts-list">
							{#each group.posts as post (post.id)}
								<div class="post-card">
									<div class="post-main">
										<div class="post-info">
											<div class="post-meta">
												<span class="post-type" data-type={post.type}>
													{$_(`budgetPosts.type.${post.type}`)}
												</span>
											</div>
										</div>
										<div class="post-amount">
											{formatPatternSummary(post)}
										</div>
									</div>
									<div class="post-actions">
										<button
											type="button"
											class="btn-icon"
											onclick={() => handleEdit(post)}
											title={$_('common.edit')}
										>
											<svg
												width="20"
												height="20"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
											</svg>
										</button>
										{#if postToDelete === post.id}
											<div class="delete-confirm-inline">
												<button
													type="button"
													class="btn-icon btn-danger"
													onclick={handleDelete}
													title={$_('common.confirm')}
												>
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="2"
													>
														<polyline points="20 6 9 17 4 12" />
													</svg>
												</button>
												<button
													type="button"
													class="btn-icon"
													onclick={handleCancelDelete}
													title={$_('common.cancel')}
												>
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="2"
													>
														<line x1="18" y1="6" x2="6" y2="18" />
														<line x1="6" y1="6" x2="18" y2="18" />
													</svg>
												</button>
											</div>
										{:else}
											<button
												type="button"
												class="btn-icon btn-danger"
												onclick={() => handleShowDelete(post.id)}
												title={$_('common.delete')}
											>
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
												>
													<polyline points="3 6 5 6 21 6" />
													<path
														d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
													/>
												</svg>
											</button>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<BudgetPostModal
	bind:show={showModal}
	budgetPost={editingPost}
	{categories}
	{accounts}
	onSave={handleSave}
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

	.btn-primary {
		padding: var(--spacing-sm) var(--spacing-lg);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
		border: none;
		background: var(--accent);
		color: white;
	}

	.btn-primary:hover {
		opacity: 0.9;
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

	.posts-container {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.category-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.category-header {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		padding-bottom: var(--spacing-xs);
		border-bottom: 2px solid var(--border);
	}

	.posts-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.post-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		transition: border-color 0.2s;
	}

	.post-card:hover {
		border-color: var(--accent);
	}

	.post-main {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--spacing-md);
		flex: 1;
	}

	.post-info {
		flex: 1;
		min-width: 0;
	}

	.post-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.post-type {
		display: inline-block;
		padding: 2px var(--spacing-xs);
		border-radius: var(--radius-sm);
		font-size: var(--font-size-xs);
		font-weight: 500;
		text-transform: uppercase;
	}

	.post-type[data-type='fixed'] {
		background: rgba(59, 130, 246, 0.1);
		color: var(--accent);
	}

	.post-type[data-type='ceiling'] {
		background: rgba(245, 158, 11, 0.1);
		color: var(--warning);
	}

	.post-amount {
		font-size: var(--font-size-lg);
		font-weight: 700;
		color: var(--text-primary);
		flex-shrink: 0;
	}

	.post-actions {
		display: flex;
		gap: var(--spacing-xs);
		flex-shrink: 0;
	}

	.delete-confirm-inline {
		display: flex;
		gap: var(--spacing-xs);
	}

	.btn-icon {
		padding: var(--spacing-xs);
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		border-radius: var(--radius-md);
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.btn-icon:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.btn-icon.btn-danger {
		color: var(--negative);
	}

	.btn-icon.btn-danger:hover {
		background: rgba(239, 68, 68, 0.1);
		color: var(--negative);
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

		.post-card {
			flex-wrap: wrap;
		}

		.post-main {
			flex-direction: column;
			align-items: flex-start;
			width: 100%;
		}

		.post-amount {
			align-self: flex-end;
		}
	}
</style>
