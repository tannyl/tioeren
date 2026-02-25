<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { listContainers, createContainer, updateContainer, deleteContainer } from '$lib/api/containers';
	import type { Container } from '$lib/api/containers';
	import ContainerModal from '$lib/components/ContainerModal.svelte';
	import { addToast } from '$lib/stores/toast.svelte';

	let budgetId: string = $derived($page.params.id as string);
	let containers = $state<Container[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showModal = $state(false);
	let editingContainer = $state<Container | undefined>(undefined);
	let containerToDelete = $state<string | null>(null);

	// Computed state: filter cashboxes only
	let cashboxes = $derived(containers.filter(c => c.type === 'cashbox'));

	// Computed state: total available (sum of all cashbox balances)
	let totalAvailable = $derived(
		cashboxes.reduce((sum, c) => sum + c.current_balance, 0)
	);

	// Reload containers when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadContainers();
	});

	async function loadContainers() {
		try {
			loading = true;
			error = null;
			containers = await listContainers(budgetId);
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

	function handleAdd() {
		editingContainer = undefined;
		showModal = true;
	}

	function handleEdit(container: Container) {
		editingContainer = container;
		showModal = true;
	}

	async function handleSave(data: any) {
		try {
			if (editingContainer) {
				await updateContainer(budgetId, editingContainer.id, data);
				addToast($_('toast.updateSuccess'), 'success');
			} else {
				await createContainer(budgetId, data);
				addToast($_('toast.createSuccess'), 'success');
			}
			await loadContainers();
		} catch (err) {
			throw err;
		}
	}

	function handleShowDelete(containerId: string) {
		containerToDelete = containerId;
	}

	function handleCancelDelete() {
		containerToDelete = null;
	}

	async function handleDelete() {
		if (!containerToDelete) return;

		try {
			await deleteContainer(budgetId, containerToDelete);
			await loadContainers();
			addToast($_('toast.deleteSuccess'), 'success');
			containerToDelete = null;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
		}
	}

	function formatBankInfo(container: Container): string | null {
		const parts: string[] = [];

		if (container.bank_name) {
			parts.push(container.bank_name);
		}

		if (container.bank_reg_number && container.bank_account_number) {
			parts.push(`${container.bank_reg_number}-${container.bank_account_number}`);
		} else if (container.bank_account_number) {
			parts.push(container.bank_account_number);
		}

		return parts.length > 0 ? parts.join(' • ') : null;
	}
</script>

<div class="page">
	<div class="container-wrapper">
		<header class="page-header">
			<h1>{$_('pengekasser.title')}</h1>
			<button type="button" class="btn-primary" onclick={handleAdd}>
				{$_('pengekasser.add')}
			</button>
		</header>

		{#if loading}
			<div class="loading">
				<p>{$_('common.loading')}</p>
			</div>
		{:else if error}
			<div class="error-message">
				<p>{error}</p>
			</div>
		{:else}
			<!-- Available Balance Summary -->
			<section class="card summary-card">
				<div class="summary-label">{$_('pengekasser.available')}</div>
				<div class="summary-amount" class:negative={totalAvailable < 0}>
					{formatCurrency(totalAvailable)} kr
				</div>
			</section>

			<!-- Cashbox List -->
			{#if cashboxes.length === 0}
				<div class="placeholder">
					<p>{$_('pengekasser.empty')}</p>
				</div>
			{:else}
				<div class="cashbox-list">
					{#each cashboxes as container (container.id)}
						<div class="cashbox-card">
							<div class="cashbox-header">
								<div class="cashbox-name">{container.name}</div>
								<div class="cashbox-balance" class:negative={container.current_balance < 0}>
									{formatCurrency(container.current_balance)} kr
								</div>
							</div>

							{#if formatBankInfo(container)}
								<div class="cashbox-bank">
									<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<line x1="12" y1="1" x2="12" y2="23"></line>
										<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
									</svg>
									<span>{$_('pengekasser.bank')}: {formatBankInfo(container)}</span>
								</div>
							{/if}

							{#if container.overdraft_limit !== null}
								<div class="cashbox-overdraft">
									{$_('pengekasser.overdraft')}: {formatCurrency(Math.abs(container.overdraft_limit))} kr
								</div>
							{/if}

							<div class="cashbox-actions">
								<button
									type="button"
									class="btn-icon"
									onclick={() => handleEdit(container)}
									title={$_('common.edit')}
								>
									<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
										<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
									</svg>
									<span class="btn-label">{$_('common.edit')}</span>
								</button>

								{#if containerToDelete === container.id}
									<div class="delete-confirm-inline">
										<button
											type="button"
											class="btn-icon btn-danger"
											onclick={handleDelete}
											title={$_('common.confirm')}
										>
											<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<polyline points="20 6 9 17 4 12" />
											</svg>
											<span class="btn-label">{$_('common.yes')}</span>
										</button>
										<button
											type="button"
											class="btn-icon"
											onclick={handleCancelDelete}
											title={$_('common.cancel')}
										>
											<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
												<line x1="18" y1="6" x2="6" y2="18" />
												<line x1="6" y1="6" x2="18" y2="18" />
											</svg>
											<span class="btn-label">{$_('common.cancel')}</span>
										</button>
									</div>
								{:else}
									<button
										type="button"
										class="btn-icon btn-danger"
										onclick={() => handleShowDelete(container.id)}
										title={$_('common.delete')}
									>
										<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<polyline points="3 6 5 6 21 6" />
											<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
										</svg>
										<span class="btn-label">{$_('common.delete')}</span>
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>

<ContainerModal
	bind:show={showModal}
	container={editingContainer}
	{budgetId}
	presetType="cashbox"
	onSave={handleSave}
/>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.container-wrapper {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--spacing-md);
	}

	h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
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

	.placeholder {
		padding: var(--spacing-xl);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		text-align: center;
		color: var(--text-secondary);
	}

	/* Summary Card */
	.card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	.summary-card {
		text-align: center;
	}

	.summary-label {
		font-size: var(--font-size-base);
		color: var(--text-secondary);
		margin-bottom: var(--spacing-sm);
	}

	.summary-amount {
		font-size: 3rem;
		font-weight: 700;
		color: var(--positive);
	}

	.summary-amount.negative {
		color: var(--negative);
	}

	/* Cashbox List */
	.cashbox-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.cashbox-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-lg);
		transition: border-color 0.2s;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.cashbox-card:hover {
		border-color: var(--accent);
	}

	.cashbox-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--spacing-md);
	}

	.cashbox-name {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
	}

	.cashbox-balance {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.cashbox-balance.negative {
		color: var(--negative);
	}

	.cashbox-bank {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.cashbox-bank svg {
		flex-shrink: 0;
	}

	.cashbox-overdraft {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.cashbox-actions {
		display: flex;
		gap: var(--spacing-sm);
		margin-top: var(--spacing-sm);
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border);
	}

	.delete-confirm-inline {
		display: flex;
		gap: var(--spacing-sm);
	}

	/* Buttons */
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

	.btn-icon {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		padding: var(--spacing-xs) var(--spacing-sm);
		background: none;
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		transition: all 0.2s;
	}

	.btn-icon:hover {
		background: var(--bg-page);
		color: var(--text-primary);
		border-color: var(--text-secondary);
	}

	.btn-icon.btn-danger {
		color: var(--negative);
		border-color: var(--negative);
	}

	.btn-icon.btn-danger:hover {
		background: rgba(239, 68, 68, 0.1);
		border-color: var(--negative);
	}

	.btn-label {
		white-space: nowrap;
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.page-header {
			flex-direction: column;
			align-items: stretch;
		}

		.btn-primary {
			width: 100%;
		}

		.summary-amount {
			font-size: 2rem;
		}

		.cashbox-card {
			padding: var(--spacing-md);
		}

		.cashbox-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--spacing-sm);
		}

		.cashbox-actions {
			flex-direction: column;
		}

		.btn-icon {
			justify-content: center;
			padding: var(--spacing-sm) var(--spacing-md);
		}

		.delete-confirm-inline {
			flex-direction: column;
		}
	}
</style>
