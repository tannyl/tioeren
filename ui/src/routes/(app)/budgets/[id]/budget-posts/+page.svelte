<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import {
		listBudgetPosts,
		createBudgetPost,
		updateBudgetPost,
		deleteBudgetPost
	} from '$lib/api/budgetPosts';
	import { listContainers } from '$lib/api/containers';
	import type { BudgetPost } from '$lib/api/budgetPosts';
	import type { Container } from '$lib/api/containers';
	import BudgetPostModal from '$lib/components/BudgetPostModal.svelte';
	import SkeletonList from '$lib/components/SkeletonList.svelte';
	import { addToast } from '$lib/stores/toast.svelte';
	import { buildCategoryTree, type CategoryTreeNode } from '$lib/utils/categoryTree';

	// Get budget ID from route params
	let budgetId: string = $derived($page.params.id as string);

	// State
	let budgetPosts = $state<BudgetPost[]>([]);
	let containers = $state<Container[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Modal state
	let showModal = $state(false);
	let editingPost = $state<BudgetPost | undefined>(undefined);
	let postToDelete = $state<string | null>(null);

	// Reload data when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadData();
	});

	async function loadData() {
		try {
			loading = true;
			error = null;
			const [postsData, containersData] = await Promise.all([
				listBudgetPosts(budgetId),
				listContainers(budgetId)
			]);
			budgetPosts = postsData;
			containers = containersData;
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

	function formatPatternSummary(post: BudgetPost): string {
		if (!post.amount_patterns || post.amount_patterns.length === 0) {
			return '-';
		}

		// If single pattern, show the amount
		if (post.amount_patterns.length === 1) {
			return `${formatCurrency(post.amount_patterns[0].amount)} kr`;
		}

		// Multiple patterns, show count
		return $_('budgetPosts.patternCountPlural', { values: { count: post.amount_patterns.length } });
	}

	function getPostDisplayLabel(post: BudgetPost): string {
		if (post.direction === 'transfer') {
			// Find container names
			const fromContainer = containers.find(c => c.id === post.transfer_from_container_id);
			const toContainer = containers.find(c => c.id === post.transfer_to_container_id);
			const fromName = fromContainer?.name || '?';
			const toName = toContainer?.name || '?';
			return `${fromName} → ${toName}`;
		} else {
			// income or expense - show category name
			return post.category_name || $_('budgetPosts.noCategory');
		}
	}

	// Group budget posts by direction with tree structure
	let groupedPosts = $derived.by(() => {
		const incomePosts = budgetPosts.filter(p => p.direction === 'income');
		const expensePosts = budgetPosts.filter(p => p.direction === 'expense');
		const transferPosts = budgetPosts.filter(p => p.direction === 'transfer');

		const groups = [];

		if (incomePosts.length > 0) {
			groups.push({
				direction: 'income',
				label: $_('budgetPosts.direction.income'),
				tree: buildCategoryTree(incomePosts),
				flatPosts: []
			});
		}

		if (expensePosts.length > 0) {
			groups.push({
				direction: 'expense',
				label: $_('budgetPosts.direction.expense'),
				tree: buildCategoryTree(expensePosts),
				flatPosts: []
			});
		}

		if (transferPosts.length > 0) {
			groups.push({
				direction: 'transfer',
				label: $_('budgetPosts.direction.transfer'),
				tree: [],  // No tree for transfers (they have no category_path)
				flatPosts: transferPosts  // Render flat
			});
		}

		return groups;
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
				{#each groupedPosts as group (group.direction)}
					<div class="direction-group">
						<h2 class="direction-header">{group.label}</h2>
						<div class="posts-list">
							{#snippet renderTreeNode(node: CategoryTreeNode)}
								{#if node.post}
									<!-- Leaf node with actual post -->
									<div
										class="post-card"
										style:margin-left="{node.depth * 24}px"
										onclick={() => handleEdit(node.post!)}
										role="button"
										tabindex="0"
										onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleEdit(node.post!); } }}
									>
										<div class="post-main">
											<div class="post-info">
												<div class="post-label">
													{getPostDisplayLabel(node.post)}
												</div>
												<div class="post-meta">
													{#if node.post.accumulate}
														<span class="post-accumulate" title={$_('budgetPosts.accumulate')}>
															<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
																<polyline points="9 18 15 12 9 6" />
															</svg>
														</span>
													{/if}
													{#if node.post.container_ids && node.post.container_ids.length > 0}
														<span class="post-accounts">
															{node.post.container_ids
																.map(id => containers.find(c => c.id === id)?.name)
																.filter(Boolean)
																.join(', ')}
														</span>
													{/if}
												</div>
												{#if node.post.via_container_id}
													<div class="post-via">
														{$_('budgetPosts.viaAccount.prefix')} {containers.find(c => c.id === node.post!.via_container_id)?.name || '?'}
													</div>
												{/if}
											</div>
											<div class="post-amount">
												{formatPatternSummary(node.post)}
											</div>
										</div>
										<div class="post-actions">
											{#if postToDelete === node.post.id}
												<div class="delete-confirm-inline">
													<button
														type="button"
														class="btn-icon btn-danger"
														onclick={(e) => { e.stopPropagation(); handleDelete(); }}
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
														onclick={(e) => { e.stopPropagation(); handleCancelDelete(); }}
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
													onclick={(e) => { e.stopPropagation(); handleShowDelete(node.post!.id); }}
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
								{:else}
									<!-- Group header node -->
									<div class="category-group-header" style:margin-left="{node.depth * 24}px">
										<h3>{node.name}</h3>
									</div>
								{/if}
								{#each node.children as child}
									{@render renderTreeNode(child)}
								{/each}
							{/snippet}

							{#snippet renderFlatPost(post: BudgetPost)}
								<div
									class="post-card"
									onclick={() => handleEdit(post)}
									role="button"
									tabindex="0"
									onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleEdit(post); } }}
								>
									<div class="post-main">
										<div class="post-info">
											<div class="post-label">
												{getPostDisplayLabel(post)}
											</div>
											<div class="post-meta">
												{#if post.accumulate}
													<span class="post-accumulate" title={$_('budgetPosts.accumulate')}>
														<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
															<polyline points="9 18 15 12 9 6" />
														</svg>
													</span>
												{/if}
												{#if post.container_ids && post.container_ids.length > 0}
													<span class="post-accounts">
														{post.container_ids
															.map(id => containers.find(c => c.id === id)?.name)
															.filter(Boolean)
															.join(', ')}
													</span>
												{/if}
											</div>
											{#if post.via_container_id}
												<div class="post-via">
													{$_('budgetPosts.viaAccount.prefix')} {containers.find(c => c.id === post.via_container_id)?.name || '?'}
												</div>
											{/if}
										</div>
										<div class="post-amount">
											{formatPatternSummary(post)}
										</div>
									</div>
									<div class="post-actions">
										{#if postToDelete === post.id}
											<div class="delete-confirm-inline">
												<button
													type="button"
													class="btn-icon btn-danger"
													onclick={(e) => { e.stopPropagation(); handleDelete(); }}
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
													onclick={(e) => { e.stopPropagation(); handleCancelDelete(); }}
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
												onclick={(e) => { e.stopPropagation(); handleShowDelete(post.id); }}
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
							{/snippet}

							<!-- Render tree nodes for income/expense -->
							{#each group.tree as node}
								{@render renderTreeNode(node)}
							{/each}

							<!-- Render flat posts for transfers -->
							{#each group.flatPosts as post (post.id)}
								{@render renderFlatPost(post)}
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
	{budgetId}
	budgetPost={editingPost}
	existingPosts={budgetPosts}
	{containers}
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

	.direction-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.direction-header {
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
		cursor: pointer;
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

	.post-label {
		font-size: var(--font-size-base);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-xs);
	}

	.post-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.post-accumulate {
		display: inline-flex;
		align-items: center;
		color: var(--accent);
	}

	.post-accounts {
		font-size: var(--font-size-xs);
		color: var(--text-secondary);
	}

	.post-via {
		font-size: var(--font-size-xs);
		color: var(--text-secondary);
		font-style: italic;
		margin-top: var(--spacing-xs);
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

	.category-group-header {
		padding: var(--spacing-sm) var(--spacing-md);
		margin-bottom: var(--spacing-xs);
	}

	.category-group-header h3 {
		font-size: var(--font-size-base);
		font-weight: 600;
		color: var(--text-secondary);
		margin: 0;
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
